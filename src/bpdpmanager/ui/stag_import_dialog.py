"""STAG import dialog — načtení CSV, náhled, mapování oborů, provedení importu.

Workflow:
1) File picker + tvoje jméno → detekuje per-řádek roli
2) Náhled tabulky — sloupce Role / Student / Téma / Obor / Stav / Akce
3) Per-řádek volby (role override, obor mapping, status, akce)
4) Před spuštěním automatická záloha
5) Provedení importu — vytvoří/aktualizuje práce, studenty, vedoucí, oponenty
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models import (
    Obor,
    Opponent,
    OpposingThesis,
    Student,
    Supervisor,
    Thesis,
)
from ..models.enums import OpponentKind, ThesisStatus, ThesisType
from ..services import BackupManager, ProfileManager, ThesisService
from ..services.stag_csv_importer import (
    ImportFile,
    ImportRole,
    ParsedRecord,
    load_stag_csv,
)
from .obor_dialog import OborDialog

# Per-row akce
ACTION_CREATE = "create"
ACTION_UPDATE = "update"
ACTION_SKIP = "skip"


class StagImportDialog(QDialog):
    def __init__(
        self,
        service: ThesisService,
        profile_manager: ProfileManager | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.profile_manager = profile_manager
        self.import_file: ImportFile | None = None
        self.row_widgets: list[dict] = []  # každý řádek má { role, obor, status, action }

        self.setWindowTitle("Import dat ze STAG CSV")
        self.setMinimumSize(1100, 720)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        # ── Hlavička ────────────────────────────────────────────────────────
        title = QLabel("📥 Import dat ze STAG CSV")
        title.setStyleSheet("font-size:16px;font-weight:bold;")
        outer.addWidget(title)

        # ── Formulář s parametry ────────────────────────────────────────────
        form = QFormLayout()
        self.ed_path = QLineEdit()
        self.ed_path.setPlaceholderText("vyber CSV soubor exportovaný ze STAG")
        btn_browse = QPushButton("Procházet…")
        btn_browse.clicked.connect(self._browse)
        row_path = QHBoxLayout()
        row_path.addWidget(self.ed_path, stretch=1)
        row_path.addWidget(btn_browse)
        form.addRow("CSV soubor", row_path)

        # Tvoje jméno (pro detekci role)
        default_user_name = ""
        if profile_manager and profile_manager.active:
            default_user_name = profile_manager.active.user_name or ""
        self.ed_user_name = QLineEdit(default_user_name)
        self.ed_user_name.setPlaceholderText("např. Petr Žáček")
        form.addRow("Tvoje jméno", self.ed_user_name)
        help_lbl = QLabel(
            "<small><i>Použije se k auto-detekci role: pokud se najde "
            "v `vedouciJmeno` → ‚Vedu‘, v `oponentJmeno` → ‚Oponuji‘. "
            "Per řádek lze přepsat v náhledu.</i></small>"
        )
        help_lbl.setStyleSheet("color:#888;")
        help_lbl.setTextFormat(Qt.TextFormat.RichText)
        form.addRow("", help_lbl)

        # Default stav pro vedené (oponentury stavy nemají)
        self.cb_default_status = QComboBox()
        for st in ThesisStatus:
            self.cb_default_status.addItem(st.label, st.value)
        # Pre-set na "Obhájeno" pro typický import historických
        idx = self.cb_default_status.findData(ThesisStatus.DEFENDED.value)
        if idx >= 0:
            self.cb_default_status.setCurrentIndex(idx)
        form.addRow("Default stav (vedené práce)", self.cb_default_status)

        btn_load = QPushButton("🔍 Načíst náhled")
        btn_load.clicked.connect(self._load_preview)
        form.addRow("", btn_load)

        outer.addLayout(form)

        # ── Náhled tabulky ──────────────────────────────────────────────────
        self.lbl_info = QLabel("Načti CSV soubor pro náhled.")
        self.lbl_info.setStyleSheet("color:#888;")
        outer.addWidget(self.lbl_info)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Role", "Student", "Typ", "Rok", "Téma", "Obor (STAG → cíl)",
             "Stav", "Akce"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        outer.addWidget(self.table, stretch=1)

        # ── Tlačítka ────────────────────────────────────────────────────────
        row = QHBoxLayout()
        self.btn_import = QPushButton("📥 Provést import")
        self.btn_import.setEnabled(False)
        self.btn_import.clicked.connect(self._execute_import)
        f = self.btn_import.font()
        f.setBold(True)
        self.btn_import.setFont(f)
        btn_cancel = QPushButton("Zavřít")
        btn_cancel.clicked.connect(self.reject)
        row.addStretch()
        row.addWidget(btn_cancel)
        row.addWidget(self.btn_import)
        outer.addLayout(row)

    # --- akce ----------------------------------------------------------------

    def _browse(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Vyber STAG CSV soubor",
            str(Path.home()),
            "CSV soubory (*.csv);;Všechny soubory (*.*)",
        )
        if path_str:
            self.ed_path.setText(path_str)

    def _load_preview(self) -> None:
        path_str = self.ed_path.text().strip()
        if not path_str:
            QMessageBox.warning(self, "Chybí soubor", "Vyber nejdřív CSV soubor.")
            return
        user_name = self.ed_user_name.text().strip()
        try:
            self.import_file = load_stag_csv(Path(path_str), user_name=user_name)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Chyba načítání", f"Soubor nelze přečíst:\n{exc}")
            return

        # Ulož user_name do aktivního profilu, aby se příště předvyplnil
        if (
            self.profile_manager is not None
            and self.profile_manager.active is not None
            and user_name
            and self.profile_manager.active.user_name != user_name
        ):
            self.profile_manager.active.user_name = user_name
            try:
                self.profile_manager._save_registry()
            except Exception:
                pass

        self._populate_preview()

    def _populate_preview(self) -> None:
        if self.import_file is None:
            return

        # Reset
        self.row_widgets = []
        self.table.setRowCount(0)
        if not self.import_file.records:
            self.lbl_info.setText(
                f"⚠ Soubor neobsahuje data ({self.import_file.skipped} přeskočeno)."
            )
            self.btn_import.setEnabled(False)
            return

        # Akademické obory v naší DB — pro mapování
        all_obory = self.service.list_obor_objects()
        obory_by_stag = {o.stag_code: o for o in all_obory if o.stag_code}
        all_obor_names = [o.name for o in all_obory]

        default_status = ThesisStatus(self.cb_default_status.currentData())

        existing_theses = self.service.list_theses()
        existing_opposing = self.service.list_opposing_theses()

        for record in self.import_file.records:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)

            # === Role combobox ===
            cb_role = QComboBox()
            cb_role.addItem("🎓 Vedu já", ImportRole.SUPERVISOR.value)
            cb_role.addItem("🧐 Oponuji", ImportRole.OPPONENT.value)
            initial = (
                ImportRole.SUPERVISOR.value
                if record.role != ImportRole.OPPONENT
                else ImportRole.OPPONENT.value
            )
            cb_role.setCurrentIndex(0 if initial == ImportRole.SUPERVISOR.value else 1)
            if record.role == ImportRole.UNKNOWN:
                # Vizuálně varuj
                cb_role.setStyleSheet("QComboBox { background-color: #fff3e0; }")
            self.table.setCellWidget(row_idx, 0, cb_role)

            # === Student ===
            student_label = f"{record.student_last}, {record.student_first}"
            if record.student_uni_id:
                student_label += f"  [{record.student_uni_id}]"
            student_item = QTableWidgetItem(student_label)
            self.table.setItem(row_idx, 1, student_item)

            # === Typ ===
            type_item = QTableWidgetItem(record.type_code)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 2, type_item)

            # === Rok ===
            year_item = QTableWidgetItem(record.academic_year or "—")
            year_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 3, year_item)

            # === Téma ===
            theme_item = QTableWidgetItem(record.title_cs or "(bez názvu)")
            theme_item.setToolTip(record.title_cs or "")
            self.table.setItem(row_idx, 4, theme_item)

            # === Obor mapping ===
            cb_obor = QComboBox()
            cb_obor.setEditable(False)
            # Volby:
            #  - mapping na existující obor (auto-detekce přes stag_code)
            #  - "(zachovat STAG kód jako jméno)"
            #  - "+ Nový obor…"
            cb_obor.addItem(f"⚠ Nemapováno — uložit jako '{record.student_obor_stag}'", "__keep__")
            for obor_name in all_obor_names:
                cb_obor.addItem(obor_name, obor_name)
            cb_obor.addItem("➕ Nový obor…", "__new__")

            # Auto-mapping přes stag_code
            mapped = obory_by_stag.get(record.student_obor_stag)
            if mapped:
                idx = cb_obor.findData(mapped.name)
                if idx >= 0:
                    cb_obor.setCurrentIndex(idx)
            # Capture row pro on-change
            cb_obor.currentIndexChanged.connect(
                lambda _, r=row_idx: self._on_obor_combo_changed(r)
            )
            stag_label = QLabel(record.student_obor_stag or "—")
            stag_label.setStyleSheet("color:#888;font-size:11px;")
            obor_widget = QWidget()
            obor_layout = QHBoxLayout(obor_widget)
            obor_layout.setContentsMargins(2, 0, 2, 0)
            obor_layout.setSpacing(4)
            obor_layout.addWidget(stag_label)
            obor_layout.addWidget(cb_obor, stretch=1)
            self.table.setCellWidget(row_idx, 5, obor_widget)

            # === Stav (jen pro Vedené práce) ===
            cb_status = QComboBox()
            for st in ThesisStatus:
                cb_status.addItem(st.label, st.value)
            idx = cb_status.findData(default_status.value)
            if idx >= 0:
                cb_status.setCurrentIndex(idx)
            self.table.setCellWidget(row_idx, 6, cb_status)

            # === Akce ===
            existing_label = self._find_existing_label(
                record, existing_theses, existing_opposing,
                role=ImportRole(initial),
            )
            cb_action = QComboBox()
            if existing_label:
                cb_action.addItem(f"🔄 Aktualizovat ({existing_label})", ACTION_UPDATE)
                cb_action.addItem("✗ Přeskočit", ACTION_SKIP)
            else:
                cb_action.addItem("✓ Vytvořit novou", ACTION_CREATE)
                cb_action.addItem("✗ Přeskočit", ACTION_SKIP)
            self.table.setCellWidget(row_idx, 7, cb_action)

            self.row_widgets.append({
                "record": record,
                "cb_role": cb_role,
                "cb_obor": cb_obor,
                "cb_status": cb_status,
                "cb_action": cb_action,
            })

        self.lbl_info.setText(
            f"📊 Řádků: {len(self.import_file.records)} "
            f"(přeskočeno při parsingu: {self.import_file.skipped})  ·  "
            f"Encoding: {self.import_file.encoding}"
        )
        self.btn_import.setEnabled(True)

    def _on_obor_combo_changed(self, row_idx: int) -> None:
        if row_idx >= len(self.row_widgets):
            return
        cb_obor: QComboBox = self.row_widgets[row_idx]["cb_obor"]
        data = cb_obor.currentData()
        if data != "__new__":
            return
        # Otevři nový obor dialog
        record: ParsedRecord = self.row_widgets[row_idx]["record"]
        # Pre-fill: STAG kód = student_obor_stag
        new_obor = Obor(name="", stag_code=record.student_obor_stag or None)
        dlg = OborDialog(self.service, new_obor, parent=self)
        if dlg.exec():
            # Reload obory v combu (a vyber nově vytvořený)
            self._reload_obor_options(cb_obor, prefer_name=new_obor.name)
        else:
            # Cancel — vrať zpět na první volbu (Nemapováno)
            cb_obor.setCurrentIndex(0)

    def _reload_obor_options(self, cb_obor: QComboBox, prefer_name: str = "") -> None:
        all_obory = self.service.list_obor_objects()
        record = None
        for w in self.row_widgets:
            if w["cb_obor"] is cb_obor:
                record = w["record"]
                break
        stag = record.student_obor_stag if record else ""
        cb_obor.blockSignals(True)
        try:
            cb_obor.clear()
            cb_obor.addItem(f"⚠ Nemapováno — uložit jako '{stag}'", "__keep__")
            for o in all_obory:
                cb_obor.addItem(o.name, o.name)
            cb_obor.addItem("➕ Nový obor…", "__new__")
            if prefer_name:
                idx = cb_obor.findData(prefer_name)
                if idx >= 0:
                    cb_obor.setCurrentIndex(idx)
        finally:
            cb_obor.blockSignals(False)

    def _find_existing_label(
        self,
        record: ParsedRecord,
        existing_theses: list[Thesis],
        existing_opposing: list[OpposingThesis],
        role: ImportRole,
    ) -> str:
        """Vrátí krátký popis existující práce/posudku ke stejnému studentovi+roku.

        Pokud nenajde, vrátí prázdný string.
        """
        type_value = record.type_code
        year = record.academic_year
        uni_id = record.student_uni_id.strip()

        if role == ImportRole.SUPERVISOR:
            # match podle student_id (přes university_id) + year + type
            students_by_uni_id = {
                s.university_id: s for s in self.service.list_students()
                if s.university_id
            }
            student = students_by_uni_id.get(uni_id)
            if student is None:
                return ""
            for t in existing_theses:
                if (
                    t.student_id == student.id
                    and t.academic_year == year
                    and t.type.value == type_value
                ):
                    return f"existuje: {t.display_title[:40]}"
            return ""
        else:
            # OPPOSING — match podle student_uni_id (inline) + year + type
            for o in existing_opposing:
                if (
                    o.student_university_id == uni_id
                    and o.academic_year == year
                    and o.type.value == type_value
                ):
                    return f"existuje: {o.display_title[:40]}"
            return ""

    # --- vlastní import ------------------------------------------------------

    def _execute_import(self) -> None:
        if not self.row_widgets:
            return
        confirm = QMessageBox.question(
            self,
            "Provést import",
            f"Importovat {len(self.row_widgets)} řádků?\n\n"
            "Před importem se automaticky vytvoří záloha aktuálního stavu "
            "se značkou „before-stag-import“.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        # 1) Backup před importem
        if self.profile_manager and self.profile_manager.active:
            data_dir = self.profile_manager.active_data_dir()
            try:
                BackupManager(data_dir).create_backup(
                    data_dir / "db.json",
                    suffix="before-stag-import",
                    dedupe=False,
                )
            except Exception:
                pass

        # 2) Provést import řádek po řádku
        stats = {
            "created_thesis": 0, "updated_thesis": 0,
            "created_opposing": 0, "updated_opposing": 0,
            "created_student": 0, "created_opponent": 0,
            "created_supervisor": 0, "skipped": 0,
        }
        errors: list[str] = []

        for widget_set in self.row_widgets:
            record: ParsedRecord = widget_set["record"]
            cb_role: QComboBox = widget_set["cb_role"]
            cb_obor: QComboBox = widget_set["cb_obor"]
            cb_status: QComboBox = widget_set["cb_status"]
            cb_action: QComboBox = widget_set["cb_action"]

            action = cb_action.currentData()
            if action == ACTION_SKIP:
                stats["skipped"] += 1
                continue

            role = ImportRole(cb_role.currentData())
            obor_choice = cb_obor.currentData()
            obor_name = obor_choice if obor_choice not in ("__keep__", "__new__") else None
            if obor_choice == "__keep__":
                obor_name = record.student_obor_stag or ""
            elif obor_choice == "__new__":
                # Uživatel nevyrobil — fallback na STAG kód
                obor_name = record.student_obor_stag or ""

            status = ThesisStatus(cb_status.currentData())

            try:
                if role == ImportRole.SUPERVISOR:
                    created_new = self._apply_supervisor_role(
                        record, obor_name, status, stats
                    )
                else:
                    created_new = self._apply_opponent_role(record, obor_name, stats)
                if created_new:
                    pass  # už zahrnuto ve stats per metoda
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    f"{record.student_last} {record.student_first}: {exc}"
                )

        # 3) Sumář
        self.service.save()  # explicitní save (i když upsert už uložil)
        msg = (
            f"Vedené práce: {stats['created_thesis']} vytvořeno, "
            f"{stats['updated_thesis']} aktualizováno\n"
            f"Oponentury: {stats['created_opposing']} vytvořeno, "
            f"{stats['updated_opposing']} aktualizováno\n"
            f"Noví studenti: {stats['created_student']}\n"
            f"Noví oponenti v registru: {stats['created_opponent']}\n"
            f"Noví vedoucí v registru: {stats['created_supervisor']}\n"
            f"Přeskočeno: {stats['skipped']}"
        )
        if errors:
            msg += "\n\n⚠ Chyby:\n" + "\n".join(f"  • {e}" for e in errors[:10])
            if len(errors) > 10:
                msg += f"\n  … a {len(errors) - 10} dalších"
        QMessageBox.information(self, "Import dokončen", msg)
        self.accept()

    # --- per-role logic ------------------------------------------------------

    def _apply_supervisor_role(
        self,
        record: ParsedRecord,
        obor_name: str,
        status: ThesisStatus,
        stats: dict,
    ) -> bool:
        """Vytvoří/aktualizuje vedenou Thesis."""
        # 1) Student
        student = self._ensure_student(record, obor_name, stats)

        # 2) Opponent (z registry)
        opponent = self._ensure_opponent(record.opponent_name, stats) \
            if record.opponent_name else None

        # 3) Najdi existující práci (univ_id + year + type)
        existing = self._find_existing_thesis(student.id, record)
        is_new = existing is None
        thesis = existing or Thesis(
            type=ThesisType(record.type_code),
            status=status,
            academic_year=record.academic_year,
        )

        # 4) Naplň pole — preferujeme nové údaje (STAG má autoritativní data)
        thesis.student_id = student.id
        thesis.opponent_id = opponent.id if opponent else thesis.opponent_id
        thesis.type = ThesisType(record.type_code)
        thesis.academic_year = record.academic_year
        if is_new:
            thesis.status = status  # u nových volíme z dialogu; existující neměníme
        thesis.title_cs = record.title_cs or thesis.title_cs
        thesis.title_en = record.title_en or thesis.title_en
        thesis.annotation = record.annotation_cs or thesis.annotation
        thesis.annotation_en = record.annotation_en or thesis.annotation_en
        thesis.objectives = record.objectives_text or thesis.objectives
        thesis.references = record.references_text or thesis.references

        self.service.upsert_thesis(thesis)
        if is_new:
            stats["created_thesis"] += 1
        else:
            stats["updated_thesis"] += 1
        return is_new

    def _apply_opponent_role(
        self,
        record: ParsedRecord,
        obor_name: str,
        stats: dict,
    ) -> bool:
        """Vytvoří/aktualizuje OpposingThesis."""
        # Vedoucí v registru
        supervisor = self._ensure_supervisor(record.supervisor_name, stats) \
            if record.supervisor_name else None

        # Najdi existující posudek
        existing = self._find_existing_opposing(record)
        is_new = existing is None
        op = existing or OpposingThesis(
            type=ThesisType(record.type_code),
            academic_year=record.academic_year,
        )

        op.type = ThesisType(record.type_code)
        op.academic_year = record.academic_year
        op.student_first_name = record.student_first or op.student_first_name
        op.student_last_name = record.student_last or op.student_last_name
        op.student_obor = obor_name or op.student_obor
        op.student_university_id = record.student_uni_id or op.student_university_id
        op.supervisor_name = record.supervisor_name or op.supervisor_name
        op.supervisor_email = (
            (supervisor.email if supervisor else "")
            or op.supervisor_email
        )
        op.title_cs = record.title_cs or op.title_cs
        op.objectives = record.objectives_text or op.objectives
        op.grade_supervisor = record.grade_supervisor or op.grade_supervisor
        op.grade_opponent = record.grade_opponent or op.grade_opponent

        self.service.upsert_opposing_thesis(op)
        if is_new:
            stats["created_opposing"] += 1
        else:
            stats["updated_opposing"] += 1
        return is_new

    # --- entity ensure helpers -----------------------------------------------

    def _ensure_student(
        self, record: ParsedRecord, obor_name: str, stats: dict
    ) -> Student:
        """Najdi (podle uni_id) nebo vytvoř studenta."""
        uni_id = record.student_uni_id.strip()
        if uni_id:
            for s in self.service.list_students():
                if s.university_id == uni_id:
                    # Aktualizuj jméno/obor, pokud se liší
                    changed = False
                    if record.student_first and s.first_name != record.student_first:
                        s.first_name = record.student_first
                        changed = True
                    if record.student_last and s.last_name != record.student_last:
                        s.last_name = record.student_last
                        changed = True
                    if obor_name and s.obor != obor_name:
                        s.obor = obor_name
                        changed = True
                    if changed:
                        self.service.upsert_student(s)
                    return s
        # Vytvoř nového
        s = Student(
            first_name=record.student_first,
            last_name=record.student_last,
            obor=obor_name,
            university_id=uni_id or None,
        )
        self.service.upsert_student(s)
        stats["created_student"] += 1
        return s

    def _ensure_opponent(self, name: str, stats: dict) -> Opponent | None:
        """Najdi (podle jména) nebo vytvoř oponenta v registru."""
        name = (name or "").strip()
        if not name:
            return None
        for o in self.service.list_opponents():
            if o.name == name:
                return o
        # Vytvoř — default jako interní (lze přepsat)
        opp = Opponent(kind=OpponentKind.INTERNAL, name=name)
        self.service.upsert_opponent(opp)
        stats["created_opponent"] += 1
        return opp

    def _ensure_supervisor(self, name: str, stats: dict) -> Supervisor | None:
        """Najdi (podle jména) nebo vytvoř vedoucího v registru."""
        name = (name or "").strip()
        if not name:
            return None
        for sup in self.service.list_supervisors():
            if sup.name == name:
                return sup
        sup = Supervisor(name=name)
        self.service.upsert_supervisor(sup)
        stats["created_supervisor"] += 1
        return sup

    def _find_existing_thesis(self, student_id: str, record: ParsedRecord) -> Thesis | None:
        for t in self.service.list_theses():
            if (
                t.student_id == student_id
                and t.academic_year == record.academic_year
                and t.type.value == record.type_code
            ):
                return t
        return None

    def _find_existing_opposing(self, record: ParsedRecord) -> OpposingThesis | None:
        uni_id = record.student_uni_id.strip()
        for o in self.service.list_opposing_theses():
            if (
                o.student_university_id == uni_id
                and o.academic_year == record.academic_year
                and o.type.value == record.type_code
            ):
                return o
        return None
