from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..models import Thesis
from ..models.enums import ThesisStatus, ThesisType
from ..services import (
    BackupManager,
    LockStatus,
    ProfileError,
    ProfileManager,
    ThesisService,
)
from ..storage import JsonRepository
from .backup_dialog import BackupBrowserDialog
from .harmonogram_tab import HarmonogramTab
from .manage_dialogs import (
    OboryManageDialog,
    OpponentsManageDialog,
    StudentsManageDialog,
)
from .new_profile_dialog import NewProfileDialog
from .profile_manage_dialog import ProfileManageDialog
from .theses_tree import ThesesTreeWidget
from .thesis_detail import (
    YEAR_MODE_ALL,
    YEAR_MODE_CURRENT,
    YEAR_MODE_FUTURE,
    YEAR_MODE_HISTORY,
    ThesisDetail,
)


class _ThesesTab(QWidget):
    """Jedna záložka = strom prací (grupování rok → BP/DP) nahoře + detail dole."""

    def __init__(
        self,
        service: ThesisService,
        filter_predicate,
        year_mode: str = YEAR_MODE_ALL,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        self.tree = ThesesTreeWidget(service)
        self.tree.setMinimumHeight(160)
        self.tree.set_filter(filter_predicate)
        self.detail = ThesisDetail(service, year_mode=year_mode)
        self.detail.setMinimumHeight(520)

        splitter.addWidget(self.tree)
        splitter.addWidget(self.detail)
        # Výchozí proporce: detail má dvojnásobek místa proti seznamu,
        # aby se formulářová pole vlezla bez vnitřního skrolování.
        splitter.setSizes([260, 640])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        self.tree.thesis_selected.connect(self._on_thesis_selected)
        self.detail.saved.connect(lambda _: self.tree.refresh())
        self.detail.deleted.connect(lambda _: self.tree.refresh())

    def _on_thesis_selected(self, thesis_id: str) -> None:
        thesis = self.service.get_thesis(thesis_id)
        self.detail.set_thesis(thesis)

    def refresh(self) -> None:
        self.tree.refresh()


class MainWindow(QMainWindow):
    def __init__(
        self,
        service: ThesisService,
        profile_manager: ProfileManager | None = None,
    ) -> None:
        super().__init__()
        self.service = service
        self.profile_manager = profile_manager
        self.setWindowTitle(self._compose_title())
        self.resize(1400, 960)
        self.setMinimumSize(1100, 760)

        current_year = ThesisService.current_academic_year()
        next_year = ThesisService.next_academic_year()

        active_states = {
            ThesisStatus.RESERVED,
            ThesisStatus.LISTED,
            ThesisStatus.ASSIGNED,
            ThesisStatus.IN_PROGRESS,
        }
        finished_states = {ThesisStatus.DEFENDED, ThesisStatus.CANCELLED}

        self.tabs = QTabWidget()
        self.tab_current = _ThesesTab(
            service,
            lambda t: t.academic_year == current_year and t.status in active_states,
            year_mode=YEAR_MODE_CURRENT,
        )
        self.tab_future = _ThesesTab(
            service,
            lambda t: t.academic_year == next_year
            or (t.status == ThesisStatus.INTERESTED and t.academic_year >= current_year),
            year_mode=YEAR_MODE_FUTURE,
        )
        self.tab_history = _ThesesTab(
            service,
            lambda t: t.status in finished_states
            or (
                t.academic_year
                and t.academic_year < current_year
                and t.status not in {ThesisStatus.INTERESTED}
            ),
            year_mode=YEAR_MODE_HISTORY,
        )
        self.tab_all = _ThesesTab(service, lambda t: True, year_mode=YEAR_MODE_ALL)
        self.tab_harmonogram = HarmonogramTab(service)

        self.tabs.addTab(self.tab_current, f"Aktuální ({current_year})")
        self.tabs.addTab(self.tab_future, f"Budoucí ({next_year})")
        self.tabs.addTab(self.tab_history, "Historie")
        self.tabs.addTab(self.tab_all, "Vše")
        self.tabs.addTab(self.tab_harmonogram, "📅 Harmonogram")

        self.setCentralWidget(self.tabs)
        self.setStatusBar(QStatusBar())

        self._build_toolbar(current_year, next_year)
        self._update_status()

    # --- toolbar -------------------------------------------------------------

    def _build_toolbar(self, current_year: str, next_year: str) -> None:
        toolbar = QToolBar("Hlavní")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        act_new_thesis = QAction("+ Nová práce", self)
        act_new_thesis.triggered.connect(lambda: self._new_thesis(current_year))
        toolbar.addAction(act_new_thesis)

        act_new_interest = QAction("+ Zájemce (budoucí rok)", self)
        act_new_interest.triggered.connect(
            lambda: self._new_thesis(next_year, ThesisStatus.INTERESTED)
        )
        toolbar.addAction(act_new_interest)

        act_new_past = QAction("+ Minulá práce", self)
        act_new_past.triggered.connect(self._new_past_thesis)
        toolbar.addAction(act_new_past)

        toolbar.addSeparator()

        act_students = QAction("Studenti", self)
        act_students.triggered.connect(self._manage_students)
        toolbar.addAction(act_students)

        act_opponents = QAction("Oponenti", self)
        act_opponents.triggered.connect(self._manage_opponents)
        toolbar.addAction(act_opponents)

        act_obory = QAction("Obory", self)
        act_obory.triggered.connect(self._manage_obory)
        toolbar.addAction(act_obory)

        toolbar.addSeparator()

        # Profile switcher (pouze pokud máme ProfileManager)
        if self.profile_manager is not None:
            self._profile_button = QToolButton()
            self._profile_button.setText("👤 " + (self.profile_manager.active.name if self.profile_manager.active else "Profil"))
            self._profile_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            self._refresh_profile_menu()
            toolbar.addWidget(self._profile_button)
            toolbar.addSeparator()

        act_refresh = QAction("Obnovit", self)
        act_refresh.triggered.connect(self._refresh_all)
        toolbar.addAction(act_refresh)

    # --- profil --------------------------------------------------------------

    def _compose_title(self) -> str:
        base = "BPDPManager"
        if self.profile_manager and self.profile_manager.active:
            return f"{base} — {self.profile_manager.active.name}"
        return f"{base} — správa BP/DP"

    def _refresh_profile_menu(self) -> None:
        if self.profile_manager is None:
            return
        menu = QMenu(self._profile_button)
        active = self.profile_manager.active
        for p in self.profile_manager.all_profiles():
            label = ("● " if active and p.id == active.id else "   ") + p.name
            act = menu.addAction(label)
            act.setData(p.id)
            act.triggered.connect(
                lambda _checked=False, pid=p.id: self._switch_profile(pid)
            )
        menu.addSeparator()
        act_new = menu.addAction("➕ Nový profil…")
        act_new.triggered.connect(self._action_new_profile)
        act_open = menu.addAction("📂 Otevřít existující složku…")
        act_open.triggered.connect(self._action_open_existing_profile)
        menu.addSeparator()
        act_manage = menu.addAction("🗂 Správa profilů…")
        act_manage.triggered.connect(self._action_manage_profiles)
        act_backups = menu.addAction("💾 Zálohy…")
        act_backups.triggered.connect(self._action_show_backups)
        self._profile_button.setMenu(menu)
        # Update label
        if active is not None:
            self._profile_button.setText("👤 " + active.name)

    def _switch_profile(self, profile_id: str) -> None:
        if self.profile_manager is None:
            return
        active = self.profile_manager.active
        if active is not None and active.id == profile_id:
            return  # už jsme tady
        # Flushni rozpracované změny v detail panelech
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, _ThesesTab):
                try:
                    w.detail.flush()
                except Exception:
                    pass

        # Lock check
        check = self.profile_manager.check_lock(profile_id)
        force = False
        if check.status == LockStatus.LOCKED_BY_OTHER:
            if not self._confirm_locked(check):
                return
            force = True

        self.profile_manager.close()
        try:
            result = self.profile_manager.open(profile_id, force=force)
        except ProfileError as exc:
            QMessageBox.critical(self, "Přepnutí profilu", str(exc))
            return

        # Vytvoř nový repository nad novou data_dir + bind do existující service
        data_dir = self.profile_manager.active_data_dir()
        new_repo = JsonRepository(
            path=data_dir / "db.json",
            backup_path=data_dir / "db.json.bak",
            backup_manager=BackupManager(data_dir),
        )
        self.service.reset(new_repo)

        # Refresh UI a window title
        self.setWindowTitle(self._compose_title())
        self._refresh_all()
        self._refresh_profile_menu()

    def _confirm_locked(self, check) -> bool:
        info = check.existing
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Profil je otevřený jinde")
        text = (
            "Profil je zřejmě otevřený na jiném zařízení nebo uživatelem.\n\n"
            f"Zařízení: {info.hostname if info else '?'}\n"
            f"Uživatel:  {info.username if info else '?'}\n"
            f"Začátek:   {info.started_at.strftime('%d.%m.%Y %H:%M:%S') if info else '?'}\n"
            f"Aplikace:  {info.app_version if info else '?'}\n\n"
            "Pokud víš, že tam aplikace neběží (např. po pádu), můžeš pokračovat. "
            "Jinak je lepší zavřít aplikaci na druhém zařízení a počkat na "
            "synchronizaci, aby si vy a druhé zařízení vzájemně nepřepsali změny."
        )
        msg.setText(text)
        btn_ignore = msg.addButton("Otevřít stejně", QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)
        msg.exec()
        return msg.clickedButton() == btn_ignore

    def _action_new_profile(self) -> None:
        if self.profile_manager is None:
            return
        dlg = NewProfileDialog(self.profile_manager, self)
        if not dlg.exec() or dlg.created is None:
            return
        self._switch_profile(dlg.created.id)

    def _action_open_existing_profile(self) -> None:
        if self.profile_manager is None:
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Vyber existující složku profilu (s db.json)", str(Path.home())
        )
        if not folder:
            return
        name, ok = QInputDialog.getText(
            self,
            "Název profilu",
            "Jak chceš profil pojmenovat?",
            text=Path(folder).name,
        )
        if not ok or not name.strip():
            return
        try:
            profile = self.profile_manager.create(name.strip(), Path(folder))
        except ProfileError as exc:
            QMessageBox.critical(self, "Vytvoření selhalo", str(exc))
            return
        self._switch_profile(profile.id)

    def _action_manage_profiles(self) -> None:
        if self.profile_manager is None:
            return
        dlg = ProfileManageDialog(self.profile_manager, self)
        dlg.exec()
        self._refresh_profile_menu()

    def _action_show_backups(self) -> None:
        if self.profile_manager is None or self.profile_manager.active is None:
            return
        data_dir = self.profile_manager.active_data_dir()
        bm = BackupManager(data_dir)
        dlg = BackupBrowserDialog(bm, data_dir / "db.json", self)
        dlg.restored.connect(self._on_backup_restored)
        dlg.exec()

    def _on_backup_restored(self) -> None:
        # Po obnově db.json přemontuj service nad ten samý profil
        self.service.reload()
        self._refresh_all()

    # --- akce ----------------------------------------------------------------

    def _new_thesis(self, year: str, status: ThesisStatus = ThesisStatus.RESERVED) -> None:
        thesis_type_label, ok = QInputDialog.getItem(
            self,
            "Typ práce",
            "Vyber typ nové práce:",
            [t.label for t in ThesisType],
            0,
            False,
        )
        if not ok:
            return
        thesis_type = next(t for t in ThesisType if t.label == thesis_type_label)
        thesis = Thesis(type=thesis_type, status=status, academic_year=year)
        self.service.upsert_thesis(thesis)
        self._refresh_all()
        self._focus_thesis(thesis.id)

    def _new_past_thesis(self) -> None:
        """Dialog pro přidání historické práce — libovolný rok, typ, stav."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Přidat minulou práci")
        dialog.setMinimumWidth(420)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        ed_year = QLineEdit(ThesisService.previous_academic_year())
        ed_year.setPlaceholderText("např. 2024/2025")

        cb_type = QComboBox()
        for t in ThesisType:
            cb_type.addItem(t.label, t.value)

        cb_status = QComboBox()
        past_statuses = [
            ThesisStatus.DEFENDED,
            ThesisStatus.IN_PROGRESS,
            ThesisStatus.ASSIGNED,
            ThesisStatus.CANCELLED,
        ]
        for s in past_statuses:
            cb_status.addItem(s.label, s.value)

        form.addRow("Akademický rok", ed_year)
        form.addRow("Typ", cb_type)
        form.addRow("Stav", cb_status)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        year = ed_year.text().strip()
        if not year:
            return

        thesis_type = ThesisType(cb_type.currentData())
        status = ThesisStatus(cb_status.currentData())
        thesis = Thesis(type=thesis_type, status=status, academic_year=year)
        self.service.upsert_thesis(thesis)
        self._refresh_all()
        self._focus_thesis(thesis.id)

    def _focus_thesis(self, thesis_id: str) -> None:
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, _ThesesTab) and widget.tree.select_thesis(thesis_id):
                self.tabs.setCurrentIndex(i)
                widget.detail.set_thesis(self.service.get_thesis(thesis_id))
                return

    def _manage_students(self) -> None:
        StudentsManageDialog(self.service, self).exec()
        self._refresh_all()

    def _manage_opponents(self) -> None:
        OpponentsManageDialog(self.service, self).exec()
        self._refresh_all()

    def _manage_obory(self) -> None:
        OboryManageDialog(self.service, self).exec()
        self._refresh_all()

    def _refresh_all(self) -> None:
        self.service.reload()
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, _ThesesTab):
                widget.refresh()
                # Combo se studenty/oponenty obnov taky — když uživatel
                # přidal studenta/oponenta v management dialogu, ať se
                # hned objeví v rozbalovači u Téma zadání.
                widget.detail.refresh_combos()
            elif isinstance(widget, HarmonogramTab):
                widget._refresh_year_combo()
        self._update_status()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt API)
        """Při zavření okna ještě flushne všechny dirty formuláře."""
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, _ThesesTab):
                widget.detail.flush()
        super().closeEvent(event)

    def _update_status(self) -> None:
        total = len(self.service.list_theses())
        students = len(self.service.list_students())
        opponents = len(self.service.list_opponents())
        obory = len(self.service.list_obory())
        self.statusBar().showMessage(
            f"Práce: {total} • Studenti: {students} • Oponenti: {opponents} • Obory: {obory}"
        )
