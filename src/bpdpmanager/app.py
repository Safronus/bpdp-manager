from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from .config import ENV_DATA_DIR
from .services import (
    BackupManager,
    LockStatus,
    ProfileError,
    ProfileManager,
    ThesisService,
)
from .storage import JsonRepository
from .ui import MainWindow
from .ui.welcome_dialog import WelcomeDialog


def _icon_path() -> Path | None:
    """Vrátí cestu k ikoně, pokud byla vygenerovaná, jinak None."""
    candidates = [
        Path(__file__).parent / "resources" / "icons" / "app_icon.png",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _build_repo_for_profile(pm: ProfileManager) -> JsonRepository:
    """Vyrobí JsonRepository pro aktivní profil včetně BackupManageru."""
    data_dir = pm.active_data_dir()
    return JsonRepository(
        path=data_dir / "db.json",
        backup_path=data_dir / "db.json.bak",
        backup_manager=BackupManager(data_dir),
    )


def _confirm_locked(check) -> bool:
    """Standalone varianta lock-warning dialogu (před existencí MainWindow)."""
    info = check.existing
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle("Profil je otevřený jinde")
    msg.setText(
        "Profil je zřejmě otevřený na jiném zařízení nebo uživatelem.\n\n"
        f"Zařízení: {info.hostname if info else '?'}\n"
        f"Uživatel:  {info.username if info else '?'}\n"
        f"Začátek:   {info.started_at.strftime('%d.%m.%Y %H:%M:%S') if info else '?'}\n\n"
        "Pokud víš, že tam aplikace neběží (např. po pádu), můžeš pokračovat. "
        "Jinak je lepší zavřít aplikaci na druhém zařízení a počkat na "
        "synchronizaci, aby si vy a druhé zařízení vzájemně nepřepsali změny."
    )
    btn_ignore = msg.addButton(
        "Otevřít stejně", QMessageBox.ButtonRole.DestructiveRole
    )
    msg.addButton(QMessageBox.StandardButton.Cancel)
    msg.exec()
    return msg.clickedButton() == btn_ignore


def _bootstrap_profile(pm: ProfileManager) -> bool:
    """Zajistí, že je aktivní profil. Vrací False, pokud uživatel zrušil."""
    # 1) Welcome flow, pokud registry je prázdný
    if not pm.has_any_profile():
        welcome = WelcomeDialog(pm)
        if not welcome.exec() or welcome.selected_profile is None:
            return False
        # Welcome už profil vytvořil v registry; otevřeme ho
        result = pm.open(welcome.selected_profile.id)
        if result.status == LockStatus.LOCKED_BY_OTHER:
            if not _confirm_locked(result):
                return False
            pm.open(welcome.selected_profile.id, force=True)
        return True

    # 2) Otevři posledně použitý nebo první v seznamu
    last_id = pm.last_opened_id()
    candidate = pm.get(last_id) if last_id else None
    if candidate is None:
        candidate = pm.all_profiles()[0]

    result = pm.open(candidate.id)
    if result.status == LockStatus.LOCKED_BY_OTHER:
        if not _confirm_locked(result):
            return False
        pm.open(candidate.id, force=True)
    return True


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("BPDPManager")
    app.setApplicationDisplayName("BPDPManager")
    app.setOrganizationName("safronus")
    app.setOrganizationDomain("github.com/Safronus")

    icon_path = _icon_path()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))

    # Pokud je env BPDPMANAGER_DATA_DIR, použij ho přímo a vynech profily
    # (test/power-user mode).
    if os.environ.get(ENV_DATA_DIR):
        pm = None
        repo = JsonRepository()
        service = ThesisService(repo)
    else:
        pm = ProfileManager()
        if not _bootstrap_profile(pm):
            return 0
        repo = _build_repo_for_profile(pm)
        service = ThesisService(repo)

    # Nový (právě vytvořený) profil dostane výchozí obory + šablony.
    service.maybe_seed_defaults()

    # Jednorázová oprava názvů archivních posudků (starší bug — kumulace
    # „_archiv_"). Idempotentní, čisté názvy nechá být.
    try:
        service.repair_review_archive_names()
    except Exception:  # noqa: BLE001
        pass

    window = MainWindow(service, profile_manager=pm)
    if icon_path is not None:
        window.setWindowIcon(QIcon(str(icon_path)))
    window.showMaximized()

    # First-run tutorial — jednou po prvním nastavení profilu.
    if pm is not None and not pm.tutorial_shown:
        from .ui.help_dialog import FirstRunDialog, HelpDialog

        tut = FirstRunDialog(window)
        tut.exec()
        if tut.dont_show_again:
            pm.mark_tutorial_shown()
        if tut.open_full_help:
            HelpDialog(window).exec()

    try:
        rc = app.exec()
    finally:
        if pm is not None:
            pm.close()
    return rc
