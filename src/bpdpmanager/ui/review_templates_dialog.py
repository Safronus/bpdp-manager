"""Dialogy pro správu knihovny šablon posudků a generování posudku z šablony.

Tři dialogy:
- ``ReviewTemplatesDialog`` — manage list (toolbar 📝 Šablony posudků)
- ``ReviewTemplateEditDialog`` — přidání / úprava metadat jedné šablony
- ``GenerateReviewDialog`` — výběr šablony z kontextu konkrétní práce
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from ..models import CriterionScore, Review, ReviewTemplate, Thesis
from ..models.enums import ThesisType
from ..services import ThesisService

# Známé obory (heuristicky odvozené z šablon FAI UTB) — slouží jako návrhy
# v combo boxu, ale uživatel může vyplnit cokoli.
KNOWN_OBORS = ["SWI", "KYB", "UI", "ITA", ""]


def _open_in_app(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    elif sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", str(path)], check=False)
    elif sys.platform == "win32":
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except OSError:
            pass


def _reveal_in_filemanager(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", "-R", str(path)], check=False)
    elif sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", str(path.parent)], check=False)
    elif sys.platform == "win32":
        try:
            subprocess.run(["explorer", "/select,", str(path)], check=False)
        except OSError:
            pass


# ── Edit single template ───────────────────────────────────────────────────


class ReviewTemplateEditDialog(QDialog):
    """Form pro vytvoření / úpravu jedné šablony."""

    def __init__(
        self,
        service: ThesisService,
        template: ReviewTemplate | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.template = template
        self.is_new = template is None
        self.created: ReviewTemplate | None = None
        # Pro nové šablony — zdroj XLSX, který se zkopíruje
        self.selected_source: Path | None = None
        # Cached metadata z předskenu XLSX (vyplní _autofill_from_xlsx)
        self._detected_meta: dict | None = None

        self.setWindowTitle("Nová šablona posudku" if self.is_new else "Šablona posudku")
        self.setMinimumWidth(560)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        form = QFormLayout()

        # XLSX soubor (jen pro nové)
        if self.is_new:
            src_row = QHBoxLayout()
            self.ed_source = QLineEdit()
            self.ed_source.setPlaceholderText("vyber XLSX šablonu posudku")
            self.ed_source.setReadOnly(True)
            btn_browse = QPushButton("Procházet…")
            btn_browse.clicked.connect(self._browse_source)
            src_row.addWidget(self.ed_source, stretch=1)
            src_row.addWidget(btn_browse)
            form.addRow("Zdrojový XLSX", src_row)

        # Název
        self.ed_name = QLineEdit(template.name if template else "")
        self.ed_name.setPlaceholderText("např. Vedoucí DP — SWI 2025/2026")
        form.addRow("Název", self.ed_name)

        # Typ
        self.cb_type = QComboBox()
        for t in ThesisType:
            self.cb_type.addItem(t.label, t.value)
        if template:
            idx = self.cb_type.findData(template.type.value)
            if idx >= 0:
                self.cb_type.setCurrentIndex(idx)
        form.addRow("Typ práce", self.cb_type)

        # Role
        self.cb_role = QComboBox()
        self.cb_role.addItem("🎓 Vedoucí", "supervisor")
        self.cb_role.addItem("🧐 Oponent", "opponent")
        if template:
            idx = self.cb_role.findData(template.role)
            if idx >= 0:
                self.cb_role.setCurrentIndex(idx)
        form.addRow("Role", self.cb_role)

        # Jazyk
        self.cb_lang = QComboBox()
        self.cb_lang.addItem("🇨🇿 Čeština (CZ)", "cs")
        self.cb_lang.addItem("🇬🇧 English (EN)", "en")
        if template:
            idx = self.cb_lang.findData(template.language)
            if idx >= 0:
                self.cb_lang.setCurrentIndex(idx)
        form.addRow("Jazyk", self.cb_lang)

        # Obor (editable combobox)
        self.cb_obor = QComboBox()
        self.cb_obor.setEditable(True)
        for o in KNOWN_OBORS:
            self.cb_obor.addItem(o or "(univerzální)", o)
        if template:
            # Pokud obor zatím není mezi známými, přidáme ho
            if template.obor and template.obor not in KNOWN_OBORS:
                self.cb_obor.addItem(template.obor, template.obor)
            idx = self.cb_obor.findData(template.obor)
            if idx >= 0:
                self.cb_obor.setCurrentIndex(idx)
        form.addRow("Obor (volitelné)", self.cb_obor)

        # Akademický rok
        self.ed_year = QLineEdit(template.academic_year if template else "")
        self.ed_year.setPlaceholderText("např. 2025/2026 (volitelné)")
        form.addRow("Akademický rok", self.ed_year)

        # Poznámka
        self.ed_note = QPlainTextEdit(template.note if template else "")
        self.ed_note.setPlaceholderText("Volitelná poznámka — např. zdroj, datum verze…")
        self.ed_note.setMaximumHeight(70)
        form.addRow("Poznámka", self.ed_note)

        outer.addLayout(form)

        # Pomocná hint zóna
        if self.is_new:
            hint = QLabel(
                "<small><i>Šablona se zkopíruje do <code>profile_dir/templates/</code>. "
                "Originál zůstane nedotčený. Stejný XLSX lze přidat víckrát "
                "s různými metadaty (např. CZ + EN varianta, nebo BP + DP).</i></small>"
            )
            hint.setStyleSheet("color: #888;")
            hint.setTextFormat(Qt.TextFormat.RichText)
            hint.setWordWrap(True)
            outer.addWidget(hint)

        # OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Přidat" if self.is_new else "Uložit"
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _browse_source(self) -> None:
        start = os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            self, "Vyber XLSX šablonu posudku", start,
            "Excel soubory (*.xlsx);;Všechny soubory (*.*)",
        )
        if not path:
            return
        self.selected_source = Path(path)
        self.ed_source.setText(path)
        self._autofill_from_xlsx(self.selected_source)

    def _autofill_from_xlsx(self, xlsx_path: Path) -> None:
        """Otevře XLSX, vytáhne meta (typ/role/jazyk/obor/rok) a předvyplní form.

        Předvyplňuje JEN pole, která má uživatel zatím prázdná — vlastní
        explicitní volbu (např. opravený obor) nepřepisujeme.
        """
        from ..services.review_schema import extract_template_metadata

        try:
            meta = extract_template_metadata(xlsx_path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(
                self, "Skenování šablony",
                f"Šablona se nepodařilo proskenovat:\n{exc}\n\n"
                "Vyplň pole ručně.",
            )
            return

        # Cache pro registraci (zabráníme druhému scanu)
        self._detected_meta = meta

        # Název (jen pokud uživatel ještě nic ručně nevyplnil)
        if not self.ed_name.text().strip():
            self.ed_name.setText(meta.get("suggested_name") or xlsx_path.stem)

        # Typ (BP/DP)
        type_hint = meta.get("type")
        if type_hint:
            idx = self.cb_type.findData(type_hint)
            if idx >= 0:
                self.cb_type.setCurrentIndex(idx)

        # Role
        role_hint = meta.get("role")
        if role_hint:
            idx = self.cb_role.findData(role_hint)
            if idx >= 0:
                self.cb_role.setCurrentIndex(idx)

        # Jazyk
        lang_hint = meta.get("language")
        if lang_hint:
            idx = self.cb_lang.findData(lang_hint)
            if idx >= 0:
                self.cb_lang.setCurrentIndex(idx)

        # Obor — pro nový template vždy přebereme detekci (uživatel může opravit
        # ručně). Pro editaci existující šablony se _autofill_from_xlsx volá
        # jen z _browse_source — uživatel explicitně mění zdroj, takže obor
        # z nového XLSX dává smysl.
        obor_code = meta.get("obor_code") or ""
        if obor_code:
            idx = self.cb_obor.findData(obor_code)
            if idx < 0:
                self.cb_obor.addItem(obor_code, obor_code)
                idx = self.cb_obor.findData(obor_code)
            if idx >= 0:
                self.cb_obor.setCurrentIndex(idx)

        # Akademický rok
        year = meta.get("academic_year") or ""
        if year and not self.ed_year.text().strip():
            self.ed_year.setText(year)

        # Info hint o nascanovaných kritériích / polích — uživatel ví, že
        # se z šablony udělal i strukturální scan.
        n_crit = len(meta.get("criteria") or [])
        max_pts = sum(c["default_weight"] for c in (meta.get("criteria") or [])) * 5
        bits = [
            f"typ={meta.get('type') or '?'}",
            f"role={meta.get('role') or '?'}",
            f"jazyk={meta.get('language') or '?'}",
        ]
        if obor_code:
            bits.append(f"obor={obor_code}")
        if year:
            bits.append(f"rok={year}")
        if n_crit:
            bits.append(f"{n_crit} kritérií (max {max_pts:g} b.)")
        QMessageBox.information(
            self, "Auto-detekce",
            f"✓ Šablonu se podařilo proskenovat.\n\nDetekováno: "
            + ", ".join(bits)
            + ".\n\nMůžeš upravit pole ručně, pokud bys něco chtěl změnit.",
        )

    def _on_accept(self) -> None:
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Chybí název", "Zadej název šablony.")
            return

        thesis_type = ThesisType(self.cb_type.currentData())
        role = self.cb_role.currentData()
        language = self.cb_lang.currentData()
        obor = (self.cb_obor.currentData() or self.cb_obor.currentText() or "").strip()
        year = self.ed_year.text().strip()
        note = self.ed_note.toPlainText().strip()

        if self.is_new:
            if self.selected_source is None or not self.selected_source.is_file():
                QMessageBox.warning(self, "Chybí soubor", "Vyber XLSX šablonu.")
                return
            try:
                tmpl = self.service.register_review_template(
                    name=name, type=thesis_type, role=role, language=language,
                    obor=obor, academic_year=year, source_path=self.selected_source,
                    note=note,
                )
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Přidání selhalo", str(exc))
                return
            # Eager schema cache — pokud máme metadata z předskenu, uložíme je
            # přímo (vyhneme se druhému scan). Jinak ensure_template_schema
            # otevře XLSX znovu a doplní z disku.
            if self._detected_meta:
                from ..models import TemplateCriterion

                tmpl.criteria = [
                    TemplateCriterion(**c) for c in self._detected_meta["criteria"]
                ]
                tmpl.field_cells = dict(self._detected_meta["field_cells"])
                self.service.update_review_template(tmpl)
            else:
                self.service.ensure_template_schema(tmpl)
            self.created = tmpl
        else:
            assert self.template is not None
            self.template.name = name
            self.template.type = thesis_type
            self.template.role = role
            self.template.language = language
            self.template.obor = obor
            self.template.academic_year = year
            self.template.note = note
            self.service.update_review_template(self.template)
            self.created = self.template
        self.accept()


# ── Manage library ─────────────────────────────────────────────────────────


class ReviewTemplatesDialog(QDialog):
    """Správa knihovny šablon posudků."""

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Šablony posudků")
        self.setMinimumSize(900, 540)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        outer.addWidget(QLabel(
            "Knihovna XLSX šablon posudků v rámci profilu. Šablony se kopírují "
            "do <code>profile_dir/templates/</code> a jdou s profilem v ZIP exportu. "
            "Z kontextu konkrétní práce (pravý klik) → <i>Generovat posudek "
            "z šablony…</i> šablonu vyplní daty z práce a připojí jako přílohu."
        ))
        outer.itemAt(outer.count() - 1).widget().setWordWrap(True)
        outer.itemAt(outer.count() - 1).widget().setTextFormat(Qt.TextFormat.RichText)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(6)
        self.tree.setHeaderLabels(["Název", "Typ", "Role", "Jazyk", "Obor", "Ak. rok"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(False)
        self.tree.itemDoubleClicked.connect(self._edit)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 6):
            h.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        outer.addWidget(self.tree, stretch=1)

        row = QHBoxLayout()
        btn_new = QPushButton("+ Přidat šablonu…")
        btn_edit = QPushButton("Upravit…")
        btn_open = QPushButton("📂 Otevřít v Excelu")
        btn_reveal = QPushButton("🔍 Ukázat ve Finderu")
        btn_delete = QPushButton("Smazat")
        btn_close = QPushButton("Zavřít")
        btn_new.clicked.connect(self._add)
        btn_edit.clicked.connect(self._edit)
        btn_open.clicked.connect(self._open_in_app)
        btn_reveal.clicked.connect(self._reveal)
        btn_delete.clicked.connect(self._delete)
        btn_close.clicked.connect(self.accept)
        row.addWidget(btn_new)
        row.addWidget(btn_edit)
        row.addWidget(btn_open)
        row.addWidget(btn_reveal)
        row.addWidget(btn_delete)
        row.addStretch()
        row.addWidget(btn_close)
        outer.addLayout(row)

        self._refresh()

    def _refresh(self) -> None:
        selected_id = self._current_id()
        self.tree.clear()
        for tmpl in self.service.list_review_templates():
            item = QTreeWidgetItem([
                tmpl.name,
                tmpl.type.value,
                tmpl.role_label,
                tmpl.language_label,
                tmpl.obor or "—",
                tmpl.academic_year or "—",
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, tmpl.id)
            # Tooltip s detaily souboru
            fp = self.service.review_template_file_path(tmpl)
            tooltip_lines = [tmpl.name]
            if tmpl.note:
                tooltip_lines.append(f"\n{tmpl.note}")
            if fp:
                tooltip_lines.append(f"\nSoubor: {fp}")
                if not fp.is_file():
                    tooltip_lines.append("⚠ Soubor neexistuje!")
                    for col in range(self.tree.columnCount()):
                        from PySide6.QtGui import QBrush, QColor

                        item.setForeground(col, QBrush(QColor("#c62828")))
            item.setToolTip(0, "\n".join(tooltip_lines))
            self.tree.addTopLevelItem(item)
        if selected_id:
            self._select_id(selected_id)

    def _current_id(self) -> str | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        return item.data(0, Qt.ItemDataRole.UserRole)

    def _current_template(self) -> ReviewTemplate | None:
        tid = self._current_id()
        return self.service.get_review_template(tid) if tid else None

    def _select_id(self, template_id: str) -> None:
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == template_id:
                self.tree.setCurrentItem(item)
                return

    def _add(self) -> None:
        dlg = ReviewTemplateEditDialog(self.service, None, self)
        if dlg.exec() and dlg.created:
            self._refresh()
            self._select_id(dlg.created.id)

    def _edit(self) -> None:
        tmpl = self._current_template()
        if tmpl is None:
            return
        dlg = ReviewTemplateEditDialog(self.service, tmpl, self)
        if dlg.exec():
            self._refresh()

    def _open_in_app(self) -> None:
        tmpl = self._current_template()
        if tmpl is None:
            return
        fp = self.service.review_template_file_path(tmpl)
        if fp is None or not fp.is_file():
            QMessageBox.warning(self, "Soubor chybí", f"Soubor šablony nenalezen:\n{fp}")
            return
        _open_in_app(fp)

    def _reveal(self) -> None:
        tmpl = self._current_template()
        if tmpl is None:
            return
        fp = self.service.review_template_file_path(tmpl)
        if fp is None or not fp.is_file():
            QMessageBox.warning(self, "Soubor chybí", f"Soubor šablony nenalezen:\n{fp}")
            return
        _reveal_in_filemanager(fp)

    def _delete(self) -> None:
        tmpl = self._current_template()
        if tmpl is None:
            return
        confirm = QMessageBox.question(
            self,
            "Smazat šablonu",
            f'Smazat šablonu „{tmpl.name}"?\n\n'
            f"Soubor v profile_dir/templates/ se rovněž odstraní.\n"
            f"Posudky, které z této šablony byly v minulosti vygenerovány "
            f"a připojeny k pracem, zůstávají nedotčené.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.service.delete_review_template(tmpl.id, delete_file=True)
        self._refresh()


# ── Generate review from thesis context ────────────────────────────────────


class GenerateReviewDialog(QDialog):
    """Dialog pro výběr šablony a vygenerování posudku k vybrané práci.

    Defaultně auto-filtruje šablony pasující k práci (typ BP/DP +
    obor podle studenta). Toggle „Zobrazit všechny" zruší filtr.

    Po úspěšném vygenerování:
    - vyplněný XLSX leží jako příloha typu SUPERVISOR_REVIEW nebo
      OPPONENT_REVIEW (podle role v šabloně).
    - dialog ukáže sumář + tlačítka „Otevřít v Excelu" / „Ukázat ve Finderu".
    """

    def __init__(
        self,
        service: ThesisService,
        thesis: Thesis,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.thesis = thesis
        self.generated_path: Path | None = None
        self.generated_attachment = None

        self.setWindowTitle("Generovat posudek z šablony")
        self.setMinimumSize(820, 580)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        # ── Hlavička ────────────────────────────────────────────────────
        header = QLabel("📝 Generovat posudek z šablony")
        header.setStyleSheet("font-size:15px;font-weight:bold;")
        outer.addWidget(header)

        student = self.service.get_student(thesis.student_id) if thesis.student_id else None
        student_lbl = student.full_name if student else "(bez studenta)"
        ctx = QLabel(
            f"Práce: <b>{thesis.type.value} · {thesis.academic_year}</b> · "
            f"{student_lbl}<br><i>{thesis.display_title}</i>"
        )
        ctx.setTextFormat(Qt.TextFormat.RichText)
        ctx.setWordWrap(True)
        ctx.setStyleSheet(
            "background-color: palette(base); color: palette(text); "
            "border: 1px solid palette(mid); padding: 8px; border-radius: 3px;"
        )
        outer.addWidget(ctx)

        # ── Filtr ──────────────────────────────────────────────────────
        self.chk_all = QCheckBox("Zobrazit všechny šablony (vypnout auto-filtr)")
        self.chk_all.toggled.connect(self._refresh_list)
        outer.addWidget(self.chk_all)

        # (chk_auto_open zrušeno v 0.19.0 — editor sám nabízí
        # otevření XLSX/PDF přes tlačítka po dokončení.)

        # ── Tabulka šablon ──────────────────────────────────────────────
        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(["Název", "Typ", "Role", "Jazyk", "Obor"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(False)
        self.tree.itemSelectionChanged.connect(self._update_button_state)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 5):
            h.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        outer.addWidget(self.tree, stretch=1)

        # ── Tlačítka ───────────────────────────────────────────────────
        row = QHBoxLayout()
        btn_cancel = QPushButton("Zavřít")
        btn_cancel.clicked.connect(self.reject)
        self.btn_generate = QPushButton("📝 Vyplnit a připojit k práci")
        bf = self.btn_generate.font()
        bf.setBold(True)
        self.btn_generate.setFont(bf)
        self.btn_generate.clicked.connect(self._generate)
        self.btn_generate.setEnabled(False)
        row.addStretch()
        row.addWidget(btn_cancel)
        row.addWidget(self.btn_generate)
        outer.addLayout(row)

        self._refresh_list()

    # ── helpers ─────────────────────────────────────────────────────────

    def _student_obor_code(self) -> str:
        """Pokus odvodit kód oboru pro filtr (např. „SWI") z student.obor.

        Studentův obor je typicky „knIT-KYB" nebo „NSWI-P" — vrátíme suffix
        nebo prefix podle obvyklých konvencí.
        """
        if self.thesis.student_id is None:
            return ""
        st = self.service.get_student(self.thesis.student_id)
        if st is None or not st.obor:
            return ""
        # Heuristic: rozdělit na pomlčce, vzít poslední segment > 1 znak,
        # vyhodit '-P'/'-K' suffix (forma studia)
        parts = [p for p in st.obor.replace("/", "-").split("-") if p]
        for p in reversed(parts):
            if len(p) >= 2 and p.upper() not in {"P", "K"}:
                return p.upper()
        return ""

    def _refresh_list(self) -> None:
        self.tree.clear()
        if self.chk_all.isChecked():
            templates = self.service.list_review_templates()
        else:
            # Auto-filtr podle typu práce + oboru studenta
            obor_code = self._student_obor_code()
            templates = self.service.list_review_templates(
                type_filter=self.thesis.type,
                obor_filter=obor_code if obor_code else None,
            )
        for tmpl in templates:
            item = QTreeWidgetItem([
                tmpl.name,
                tmpl.type.value,
                tmpl.role_label,
                tmpl.language_label,
                tmpl.obor or "—",
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, tmpl.id)
            self.tree.addTopLevelItem(item)
        if self.tree.topLevelItemCount() == 0 and not self.chk_all.isChecked():
            # Žádná pasující — automaticky přepni na „Zobrazit všechny"
            note = QTreeWidgetItem([
                "Žádná šablona neodpovídá tomuto typu/oboru. "
                'Zaškrtni „Zobrazit všechny šablony" nebo přidej '
                "novou šablonu v menu Šablony posudků.",
                "", "", "", "",
            ])
            note.setFlags(note.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            from PySide6.QtGui import QBrush, QColor

            for c in range(5):
                note.setForeground(c, QBrush(QColor("#888")))
            self.tree.addTopLevelItem(note)

    def _update_button_state(self) -> None:
        current = self.tree.currentItem()
        self.btn_generate.setEnabled(
            current is not None
            and current.data(0, Qt.ItemDataRole.UserRole) is not None
        )

    def _generate(self) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        template_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not template_id:
            return
        tmpl = self.service.get_review_template(template_id)
        if tmpl is None:
            QMessageBox.warning(self, "Šablona", "Šablona nebyla nalezena.")
            return

        # Doplň schema (lazy) — kritéria + speciální pole
        try:
            tmpl = self.service.ensure_template_schema(tmpl)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(
                self, "Schema",
                f"Schema kritérií se nepodařilo nascanovat:\n{exc}\n\n"
                "Můžeš pokračovat — editor zobrazí jen základní pole bez bodování.",
            )

        # Sestav scaffold Review z thesis dat + template kritérií
        student = (
            self.service.get_student(self.thesis.student_id)
            if self.thesis.student_id else None
        )
        opponent_entity = (
            self.service.get_opponent(self.thesis.opponent_id)
            if self.thesis.opponent_id else None
        )
        user_name = self.service._guess_user_name()

        # Zjisti, jestli pro tuto práci a roli existuje uložený Review →
        # předáme ho do editoru k úpravě (zachová body z minula).
        existing = self.service.get_current_review(
            self.thesis.id, tmpl.role, opposing=False
        )

        if existing is not None and existing.template_id == tmpl.id:
            review = existing
        else:
            review = Review(
                template_id=tmpl.id,
                template_name=tmpl.name,
                role=tmpl.role,
                language=tmpl.language,
                student_name=student.full_name if student else "",
                user_name=user_name if tmpl.role == "supervisor" else (
                    user_name if tmpl.role == "opponent" else ""
                ),
                title_cs=self.thesis.title_cs,
                title_en=self.thesis.title_en,
                academic_year=self.thesis.academic_year,
                criteria=[
                    CriterionScore(
                        row=c.row, label=c.label, weight=c.default_weight,
                        weight_cell=c.weight_cell, score_cell=c.score_cell,
                        score=5.0,  # default plný počet, uživatel sníží
                    ) for c in tmpl.criteria
                ],
            )
            # Pokud uživatel není supervisor, je oponent — v poli „opponent"
            # je user_name. Pole „supervisor" zůstává prázdné (cizí).
            if tmpl.role == "opponent" and not review.user_name:
                review.user_name = user_name

        # Otevři editor
        from .review_editor_dialog import ReviewEditorDialog

        editor = ReviewEditorDialog(
            self.service, self.thesis.id, review, opposing=False, parent=self
        )
        if not editor.exec() or not editor.saved:
            return

        self.generated_path = editor.generated_xlsx
        # ``generated_attachment`` zůstává None — Attachment je interní
        # detail, MainWindow se zajímá hlavně o focus.
        self.accept()

    def _show_done_dialog(self, out_path: Path, attachment) -> None:
        body = f"""
        <p style='color:#2e7d32;font-weight:bold;'>✓ Posudek vygenerován.</p>
        <table style='border-collapse:collapse;'>
          <tr><td>Typ přílohy:</td><td><b>{attachment.kind.label}</b></td></tr>
          <tr><td>Verze:</td><td>v{attachment.version}</td></tr>
          <tr><td>Soubor:</td><td><code>{out_path.name}</code></td></tr>
        </table>
        <p style='color:#666;'>
          Posudek je připojen k práci jako příloha. Můžeš ho ihned otevřít
          v Excelu/Numbers a doplnit body hodnocení.
        </p>
        """
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Posudek vygenerován")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(body)
        btn_open = msg.addButton("📄 Otevřít v Excelu", QMessageBox.ButtonRole.ActionRole)
        btn_reveal = msg.addButton(
            "📂 Ukázat ve Finderu", QMessageBox.ButtonRole.ActionRole
        )
        msg.addButton(QMessageBox.StandardButton.Close)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_open:
            _open_in_app(out_path)
        elif clicked == btn_reveal:
            _reveal_in_filemanager(out_path)
        self.accept()
