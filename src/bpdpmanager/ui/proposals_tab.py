"""Záložka „Návrhy témat" — seznam vymyšlených potenciálních témat (BP/DP).

Nekompletní nápady bez studenta a bez stavu: název, popis, body zadání,
literatura, obor, typ (BP/DP) a volitelně rezervace (komu, volný text).
Detail má Souhrn s tlačítky do schránky (jako ostatní záložky) a editor.
Z návrhu lze založit skutečnou vedenou práci.
"""

from __future__ import annotations

import html

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QBrush, QColor, QCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QToolTip,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models import ThesisProposal
from ..models.enums import ThesisType
from ..services import ThesisService


def _format_numbered(text: str) -> str:
    """Volný text (1 řádek = 1 bod) → očíslovaný seznam pro Souhrn/schránku."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    return "\n".join(f"{i}. {ln}" for i, ln in enumerate(lines, start=1))


class ProposalsTab(QWidget):
    """Seznam návrhů témat + detail (Souhrn / editor)."""

    changed = Signal()
    converted = Signal(str)  # předá id nově založené práce

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.current_id: str | None = None

        outer = QVBoxLayout(self)

        top = QHBoxLayout()
        btn_new = QPushButton("➕ Nový návrh")
        btn_new.clicked.connect(self._new_proposal)
        top.addWidget(btn_new)
        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color:#888;")
        top.addWidget(self.lbl_count)
        top.addStretch()
        outer.addLayout(top)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Téma", "Obor", "Rezervace"])
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.tree)

        splitter.addWidget(self._build_detail())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, stretch=1)

        self.refresh()

    # --- detail panel --------------------------------------------------------

    def _build_detail(self) -> QWidget:
        self.detail_tabs = QTabWidget()

        # Souhrn (read-only HTML s clipboard odkazy).
        self.summary_view = QTextBrowser()
        self.summary_view.setOpenExternalLinks(False)
        self.summary_view.setOpenLinks(False)
        self.summary_view.anchorClicked.connect(self._on_summary_anchor_clicked)
        self.summary_view.setStyleSheet("QTextBrowser { padding: 12px; }")
        self.detail_tabs.addTab(self.summary_view, "📋 Souhrn")

        # Editor.
        editor = QWidget()
        form = QVBoxLayout(editor)

        row_type = QHBoxLayout()
        row_type.addWidget(QLabel("Typ:"))
        self.cmb_type = QComboBox()
        for t in (ThesisType.BP, ThesisType.DP):
            self.cmb_type.addItem(t.label, t.value)
        row_type.addWidget(self.cmb_type)
        row_type.addSpacing(16)
        row_type.addWidget(QLabel("Obor:"))
        self.cmb_obor = QComboBox()
        self.cmb_obor.setEditable(True)
        self.cmb_obor.setMinimumWidth(220)
        row_type.addWidget(self.cmb_obor, stretch=1)
        form.addLayout(row_type)

        form.addWidget(QLabel("Název tématu:"))
        self.ed_title = QLineEdit()
        form.addWidget(self.ed_title)

        form.addWidget(QLabel("Popis:"))
        self.ed_desc = QPlainTextEdit()
        self.ed_desc.setMinimumHeight(60)
        form.addWidget(self.ed_desc)

        form.addWidget(QLabel("Body zadání (1 řádek = 1 bod):"))
        self.ed_obj = QPlainTextEdit()
        self.ed_obj.setMinimumHeight(60)
        form.addWidget(self.ed_obj)

        form.addWidget(QLabel("Literatura:"))
        self.ed_refs = QPlainTextEdit()
        self.ed_refs.setMinimumHeight(50)
        form.addWidget(self.ed_refs)

        row_res = QHBoxLayout()
        self.chk_reserved = QCheckBox("Zarezervováno")
        self.chk_reserved.toggled.connect(
            lambda on: self.ed_reserved_for.setEnabled(on)
        )
        row_res.addWidget(self.chk_reserved)
        row_res.addWidget(QLabel("Komu:"))
        self.ed_reserved_for = QLineEdit()
        self.ed_reserved_for.setPlaceholderText("jméno / poznámka (volný text)")
        self.ed_reserved_for.setEnabled(False)
        row_res.addWidget(self.ed_reserved_for, stretch=1)
        form.addLayout(row_res)

        buttons = QHBoxLayout()
        self.btn_save = QPushButton("💾 Uložit")
        self.btn_save.clicked.connect(self._save)
        self.btn_convert = QPushButton("🎓 Převést na vedenou práci")
        self.btn_convert.setToolTip(
            "Z návrhu založí novou vedenou práci (název, popis, body, typ) "
            "a návrh odebere. Obor přiřadíš až se studentem."
        )
        self.btn_convert.clicked.connect(self._convert)
        self.btn_delete = QPushButton("🗑 Smazat návrh")
        self.btn_delete.clicked.connect(self._delete)
        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_convert)
        buttons.addStretch()
        buttons.addWidget(self.btn_delete)
        form.addLayout(buttons)

        self.detail_tabs.addTab(editor, "✏ Detail")
        return self.detail_tabs

    # --- načtení / refresh ---------------------------------------------------

    def refresh_combos(self) -> None:
        """Obnoví nabídku oborů (volá se po změně číselníku)."""
        cur = self.cmb_obor.currentText()
        self.cmb_obor.blockSignals(True)
        self.cmb_obor.clear()
        self.cmb_obor.addItem("")
        for name in self.service.list_obory():
            self.cmb_obor.addItem(name)
        self.cmb_obor.setEditText(cur)
        self.cmb_obor.blockSignals(False)

    def refresh(self) -> None:
        self.refresh_combos()
        keep = self.current_id
        self.tree.blockSignals(True)
        self.tree.clear()
        proposals = self.service.list_proposals()
        groups = {"BP": [], "DP": []}
        for p in proposals:
            groups.setdefault(p.type.value, []).append(p)
        reserved_count = 0
        for type_code, label in (("BP", "Bakalářské"), ("DP", "Diplomové")):
            members = groups.get(type_code, [])
            if not members:
                continue
            head = QTreeWidgetItem([f"{label} ({len(members)})", "", ""])
            head.setFlags(head.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            f = head.font(0)
            f.setBold(True)
            head.setFont(0, f)
            self.tree.addTopLevelItem(head)
            for p in sorted(members, key=lambda x: (x.title_cs or "").lower()):
                res = ""
                if p.reserved:
                    reserved_count += 1
                    res = f"🔒 {p.reserved_for}".strip()
                leaf = QTreeWidgetItem(
                    [p.title_cs or "(bez názvu)", p.obor or "—", res or "—"]
                )
                leaf.setData(0, Qt.ItemDataRole.UserRole, p.id)
                if p.reserved:
                    leaf.setForeground(2, QBrush(QColor("#e65100")))
                head.addChild(leaf)
            head.setExpanded(True)
        self.tree.blockSignals(False)
        self.tree.resizeColumnToContents(0)

        total = len(proposals)
        self.lbl_count.setText(
            f"Návrhů: <b>{total}</b>  ·  rezervováno: <b>{reserved_count}</b>"
            if total else "Zatím žádné návrhy — přidej první přes ➕ Nový návrh."
        )
        self.lbl_count.setTextFormat(Qt.TextFormat.RichText)

        if keep and self._select_id(keep):
            return
        self.current_id = None
        self._load_into_editor(None)

    def _select_id(self, pid: str) -> bool:
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            head = root.child(i)
            for j in range(head.childCount()):
                leaf = head.child(j)
                if leaf.data(0, Qt.ItemDataRole.UserRole) == pid:
                    self.tree.setCurrentItem(leaf)
                    return True
        return False

    def _selected_id(self) -> str | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        return item.data(0, Qt.ItemDataRole.UserRole)

    def _on_selection_changed(self) -> None:
        pid = self._selected_id()
        self.current_id = pid
        self._load_into_editor(self.service.get_proposal(pid) if pid else None)

    # --- editor load/save ----------------------------------------------------

    def _load_into_editor(self, p: ThesisProposal | None) -> None:
        editable = p is not None
        for w in (
            self.cmb_type, self.cmb_obor, self.ed_title, self.ed_desc,
            self.ed_obj, self.ed_refs, self.chk_reserved,
            self.btn_save, self.btn_convert, self.btn_delete,
        ):
            w.setEnabled(editable)
        self.ed_reserved_for.setEnabled(editable and (p.reserved if p else False))

        if p is None:
            self.ed_title.clear()
            self.ed_desc.clear()
            self.ed_obj.clear()
            self.ed_refs.clear()
            self.ed_reserved_for.clear()
            self.chk_reserved.setChecked(False)
            self.summary_view.setHtml(
                "<p style='color:#888;padding:24px;'>Vyber návrh vlevo, "
                "nebo přidej nový.</p>"
            )
            return

        idx = self.cmb_type.findData(p.type.value)
        self.cmb_type.setCurrentIndex(max(0, idx))
        self.cmb_obor.setEditText(p.obor)
        self.ed_title.setText(p.title_cs)
        self.ed_desc.setPlainText(p.description)
        self.ed_obj.setPlainText(p.objectives)
        self.ed_refs.setPlainText(p.references)
        self.chk_reserved.setChecked(p.reserved)
        self.ed_reserved_for.setText(p.reserved_for)
        self.summary_view.setHtml(self._build_summary_html(p))

    def _new_proposal(self) -> None:
        p = ThesisProposal(title_cs="Nový návrh tématu")
        self.service.upsert_proposal(p)
        self.changed.emit()
        self.refresh()
        if self._select_id(p.id):
            self.detail_tabs.setCurrentIndex(1)  # rovnou do editoru
            self.ed_title.setFocus()
            self.ed_title.selectAll()

    def _save(self) -> None:
        if self.current_id is None:
            return
        p = self.service.get_proposal(self.current_id)
        if p is None:
            return
        p.type = ThesisType(self.cmb_type.currentData())
        p.obor = self.cmb_obor.currentText().strip()
        p.title_cs = self.ed_title.text().strip()
        p.description = self.ed_desc.toPlainText().strip()
        p.objectives = self.ed_obj.toPlainText().strip()
        p.references = self.ed_refs.toPlainText().strip()
        p.reserved = self.chk_reserved.isChecked()
        p.reserved_for = self.ed_reserved_for.text().strip() if p.reserved else ""
        self.service.upsert_proposal(p)
        self.changed.emit()
        self.refresh()
        QToolTip.showText(QCursor.pos(), "💾 Uloženo", self.btn_save)

    def _delete(self) -> None:
        if self.current_id is None:
            return
        p = self.service.get_proposal(self.current_id)
        if p is None:
            return
        title = p.title_cs or "(bez názvu)"
        if QMessageBox.question(
            self, "Smazat návrh", f"Smazat návrh „{title}“?",
        ) != QMessageBox.StandardButton.Yes:
            return
        self.service.delete_proposal(self.current_id)
        self.current_id = None
        self.changed.emit()
        self.refresh()

    def _convert(self) -> None:
        if self.current_id is None:
            return
        p = self.service.get_proposal(self.current_id)
        if p is None:
            return
        title = p.title_cs or "(bez názvu)"
        if QMessageBox.question(
            self, "Převést na vedenou práci",
            f"Z návrhu „{title}“ založit novou vedenou práci "
            "(stav „Zájemce s tématem“, aktuální akademický rok) a návrh "
            "odebrat?\n\nObor se nepřenese — přiřadíš ho až se studentem.",
        ) != QMessageBox.StandardButton.Yes:
            return
        thesis = self.service.convert_proposal_to_thesis(self.current_id)
        self.current_id = None
        self.changed.emit()
        self.refresh()
        self.converted.emit(thesis.id)

    # --- Souhrn (HTML + schránka) -------------------------------------------

    @staticmethod
    def _copy_btn(field: str, tooltip: str) -> str:
        return (
            f'&nbsp;<a href="copy:{field}" title="{tooltip}" '
            'style="text-decoration:none;font-size:11pt;color:#42a5f5;">📋</a>'
        )

    def _build_summary_html(self, p: ThesisProposal) -> str:
        e = html.escape
        cp = self._copy_btn
        rows: list[str] = []

        def section(title: str, body_html: str, copy_field: str = "") -> None:
            btn = cp(copy_field, f"Kopírovat: {title}") if copy_field else ""
            rows.append(
                f"<tr><td style='padding:6px 10px;vertical-align:top;"
                f"font-weight:bold;color:#555;white-space:nowrap;'>{e(title)}{btn}"
                f"</td><td style='padding:6px 10px;'>{body_html}</td></tr>"
            )

        type_label = p.type.label
        head = (
            f"<div style='font-size:15pt;font-weight:bold;'>"
            f"{e(p.title_cs or '(bez názvu)')}{cp('title_cs', 'Kopírovat název')}</div>"
            f"<div style='color:#888;margin-top:2px;'>{e(type_label)}"
            + (f" · {e(p.obor)}" if p.obor else "")
            + "</div>"
        )
        if p.reserved:
            who = f" — {e(p.reserved_for)}" if p.reserved_for else ""
            head += (
                f"<div style='margin-top:6px;color:#e65100;font-weight:bold;'>"
                f"🔒 Zarezervováno{who}</div>"
            )

        if p.description:
            section("Popis", e(p.description).replace("\n", "<br>"), "description")
        if p.objectives:
            numbered = _format_numbered(p.objectives)
            section("Body zadání", e(numbered).replace("\n", "<br>"), "objectives")
        if p.references:
            section("Literatura", e(p.references).replace("\n", "<br>"), "references")

        table = (
            "<table style='border-collapse:collapse;width:100%;margin-top:10px;'>"
            + "".join(rows) + "</table>"
        ) if rows else ""
        copy_all = (
            "<div style='margin-top:14px;'>"
            "<a href='copy:all' style='color:#42a5f5;text-decoration:none;'>"
            "📋 Kopírovat celý návrh</a></div>"
        )
        return head + table + copy_all

    def _field_value(self, field: str) -> str | None:
        p = self.service.get_proposal(self.current_id) if self.current_id else None
        if p is None:
            return None
        if field == "title_cs":
            return p.title_cs or ""
        if field == "description":
            return p.description or ""
        if field == "objectives":
            return _format_numbered(p.objectives)
        if field == "references":
            return p.references or ""
        if field == "all":
            parts = [p.title_cs or "(bez názvu)", f"Typ: {p.type.label}"]
            if p.obor:
                parts.append(f"Obor: {p.obor}")
            if p.reserved:
                parts.append(f"Zarezervováno: {p.reserved_for or 'ano'}")
            if p.description:
                parts.append(f"\nPopis:\n{p.description}")
            if p.objectives:
                parts.append(f"\nBody zadání:\n{_format_numbered(p.objectives)}")
            if p.references:
                parts.append(f"\nLiteratura:\n{p.references}")
            return "\n".join(parts)
        return None

    def _on_summary_anchor_clicked(self, url: QUrl) -> None:
        s = url.toString()
        if s.startswith("copy:"):
            text = self._field_value(s[len("copy:"):])
            if text is None:
                return
            QApplication.clipboard().setText(text)
            QToolTip.showText(QCursor.pos(), "📋 Zkopírováno", self.summary_view)
