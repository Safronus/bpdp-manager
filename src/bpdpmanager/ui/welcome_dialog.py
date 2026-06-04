"""Welcome dialog — první spuštění (žádný profil v registry).

Nabízí 3 cesty:
1) Import dat z legacy ``~/.bpdpmanager/`` (pokud existuje)
2) Vytvořit nový prázdný profil (zeptá se na jméno + složku)
3) Otevřít existující profil ze složky (s db.json)
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ..models import Profile
from ..services import ProfileError, ProfileManager


class WelcomeDialog(QDialog):
    """Welcome dialog. Po úspěšném dokončení je v ``ProfileManager`` první profil."""

    def __init__(self, pm: ProfileManager, parent=None) -> None:
        super().__init__(parent)
        self.pm = pm
        self.selected_profile: Profile | None = None

        self.setWindowTitle("Vítejte v BPDPManager")
        self.setMinimumWidth(620)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(14)

        # Nadpis
        title = QLabel("Vítejte v BPDPManager 👋")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        outer.addWidget(title)
        desc = QLabel(
            "Aplikace si potřebuje vybrat, kde má uložená data. "
            "Můžeš mít víc datových profilů (např. osobní, sdílený…) "
            "a kdykoli mezi nimi přepínat."
        )
        desc.setWordWrap(True)
        outer.addWidget(desc)

        # Legacy detekce
        if pm.has_legacy_data():
            legacy_box = QGroupBox("🔍 Nalezena stávající data")
            legacy_layout = QVBoxLayout(legacy_box)
            legacy_text = QLabel(
                "V <code>~/.bpdpmanager/</code> jsem našel existující "
                "<code>db.json</code> z předchozích verzí. Můžeme rovnou "
                "vyrobit profil „Výchozí“, který bude ukazovat na tuto složku — "
                "žádná data se nepřesouvají, jen se zaregistruje cesta."
            )
            legacy_text.setWordWrap(True)
            legacy_text.setTextFormat(Qt.TextFormat.RichText)
            legacy_layout.addWidget(legacy_text)
            btn_legacy = QPushButton("📦  Importovat jako profil „Výchozí“")
            btn_legacy.setMinimumHeight(36)
            btn_legacy.clicked.connect(self._import_legacy)
            legacy_layout.addWidget(btn_legacy)
            outer.addWidget(legacy_box)

        # Nový profil
        new_box = QGroupBox("🆕 Nový prázdný profil")
        new_layout = QVBoxLayout(new_box)
        new_layout.addWidget(
            QLabel(
                "Vytvoří se nová prázdná databáze ve složce, kterou si vybereš."
            )
        )
        btn_new = QPushButton("➕  Vytvořit nový profil…")
        btn_new.setMinimumHeight(36)
        btn_new.clicked.connect(self._new_profile)
        new_layout.addWidget(btn_new)
        outer.addWidget(new_box)

        # Otevřít existující
        open_box = QGroupBox("📂 Otevřít existující profil")
        open_layout = QVBoxLayout(open_box)
        open_layout.addWidget(
            QLabel(
                "Pokud máš složku s <code>db.json</code> (např. ze "
                "synchronizované složky), můžeš ji připojit jako profil."
            )
        )
        for w in open_box.findChildren(QLabel):
            w.setWordWrap(True)
            w.setTextFormat(Qt.TextFormat.RichText)
        btn_open = QPushButton("📁  Otevřít složku…")
        btn_open.setMinimumHeight(36)
        btn_open.clicked.connect(self._open_existing)
        open_layout.addWidget(btn_open)
        outer.addWidget(open_box)

        # Import ze ZIPu — typický flow pro nového uživatele na novém zařízení
        zip_box = QGroupBox("📥 Importovat ze ZIP balíku")
        zip_layout = QVBoxLayout(zip_box)
        zip_text = QLabel(
            "Máš na disku <code>.zip</code> exportovaný přes "
            "<i>Export profilu</i> z jiného zařízení? Otevři ho zde — "
            "rozbalí se data + dokumenty + šablony do nového profilu "
            "a aplikace ho rovnou aktivuje."
        )
        zip_text.setWordWrap(True)
        zip_text.setTextFormat(Qt.TextFormat.RichText)
        zip_layout.addWidget(zip_text)
        btn_zip = QPushButton("📥  Importovat .zip…")
        btn_zip.setMinimumHeight(36)
        btn_zip.clicked.connect(self._import_zip)
        zip_layout.addWidget(btn_zip)
        outer.addWidget(zip_box)

        # Zrušit
        row = QHBoxLayout()
        row.addStretch()
        btn_cancel = QPushButton("Zavřít")
        btn_cancel.clicked.connect(self.reject)
        row.addWidget(btn_cancel)
        outer.addLayout(row)

    # --- akce -----------------------------------------------------------

    def _import_zip(self) -> None:
        """Otevře ``ImportProfileDialog`` v módu „nový profil"
        (na čerstvém zařízení dává smysl jen tahle varianta — žádné
        existující profily k mergi nejsou).
        """
        # Lazy import (cyklický import s main_window přes profile_export_dialog)
        from .profile_export_dialog import ImportProfileDialog

        dlg = ImportProfileDialog(self.pm, self)
        # Nemáme do čeho slučovat → schovej radio výběr na merge
        dlg.rb_merge.setEnabled(False)
        dlg.rb_new.setChecked(True)
        if not dlg.exec() or dlg.created is None:
            return
        self.selected_profile = dlg.created
        self.accept()

    def _import_legacy(self) -> None:
        try:
            profile = self.pm.import_legacy(name="Výchozí")
        except ProfileError as exc:
            QMessageBox.critical(self, "Import selhal", str(exc))
            return
        self.selected_profile = profile
        self.accept()

    def _new_profile(self) -> None:
        # 1) jméno
        name, ok = QInputDialog.getText(
            self,
            "Nový profil",
            "Název profilu (např. „FAI UTB — osobní“):",
        )
        if not ok or not name.strip():
            return
        # 2) složka
        folder = QFileDialog.getExistingDirectory(
            self,
            "Vyber složku pro data profilu (vytvoří se db.json)",
            str(Path.home()),
        )
        if not folder:
            return
        try:
            profile = self.pm.create(name=name, data_dir=Path(folder))
        except ProfileError as exc:
            QMessageBox.critical(self, "Vytvoření selhalo", str(exc))
            return
        self.selected_profile = profile
        self.accept()

    def _open_existing(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Vyber existující složku profilu (obsahující db.json)",
            str(Path.home()),
        )
        if not folder:
            return
        folder_path = Path(folder)
        db_file = folder_path / "db.json"
        if not db_file.exists():
            confirm = QMessageBox.question(
                self,
                "Žádný db.json",
                f"Ve složce nebyl nalezen <code>db.json</code>. "
                "Vytvořit zde nový prázdný profil?",
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
        else:
            # validace, že to JE bpdpmanager databáze
            try:
                data = json.loads(db_file.read_text(encoding="utf-8"))
                if not isinstance(data, dict) or "theses" not in data:
                    raise ValueError("nevypadá jako BPDPManager db.json")
            except (json.JSONDecodeError, ValueError, OSError) as exc:
                QMessageBox.warning(
                    self,
                    "Neplatný soubor",
                    f"Soubor db.json ve složce nepatří BPDPManageru:\n{exc}",
                )
                return

        # jméno profilu
        default_name = folder_path.name
        name, ok = QInputDialog.getText(
            self,
            "Název profilu",
            "Jak chceš profil pojmenovat?",
            text=default_name,
        )
        if not ok or not name.strip():
            return
        try:
            profile = self.pm.create(name=name, data_dir=folder_path)
        except ProfileError as exc:
            QMessageBox.critical(self, "Vytvoření selhalo", str(exc))
            return
        self.selected_profile = profile
        self.accept()
