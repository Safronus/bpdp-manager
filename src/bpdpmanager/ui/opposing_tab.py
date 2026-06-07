"""Záložka 'Oponentské posudky' — strom kategorizovaný podle ak. roků + detail."""

from __future__ import annotations

import locale
import unicodedata

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models import OpposingThesis
from ..models.enums import (
    REVIEW_STATE_LABELS,
    REVIEW_STATE_STRONG,
    REVIEW_STATE_TINTS,
    AttachmentKind,
    ThesisType,
    review_sent_indicator,
)
from ..services import ThesisService
from .opposing_detail import OpposingDetail
from .stag_import_dialog import STAG_STATE_LABELS, STAG_STATE_SHORT
from .theses_tree import ROLE_GRADES, GradesDelegate

ROLE_ID = Qt.ItemDataRole.UserRole + 1
# Sloupce stromu oponentur (Obor je poslední — stejně jako v ostatních záložkách).
COL_GRADES = 4   # „V/O" (známka vedoucího / oponenta) — viz GradesDelegate
COL_SENT = 5     # Odesláno
COL_OBOR = 6     # Obor (poslední)

# Reuse Czech locale setup from theses_tree
_HAS_CZECH_LOCALE = False
for _loc in ("cs_CZ.UTF-8", "cs_CZ.utf8", "cs_CZ"):
    try:
        locale.setlocale(locale.LC_COLLATE, _loc)
        _HAS_CZECH_LOCALE = True
        break
    except locale.Error:
        continue


def _czech_key(s: str) -> str:
    if not s:
        return ""
    if _HAS_CZECH_LOCALE:
        return locale.strxfrm(s.casefold())
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if not unicodedata.combining(c)).casefold()


class _NewOpposingDialog(QDialog):
    """Dialog na rychlé založení nového posudku — typ + rok."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nový oponentský posudek")
        self.setMinimumWidth(380)
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.cb_type = QComboBox()
        for t in ThesisType:
            self.cb_type.addItem(t.label, t.value)
        form.addRow("Typ", self.cb_type)
        self.ed_year = QLineEdit()
        from datetime import date
        today = date.today()
        start = today.year if today.month >= 9 else today.year - 1
        self.ed_year.setText(f"{start}/{start + 1}")
        form.addRow("Akademický rok", self.ed_year)
        v.addLayout(form)
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    @property
    def type_value(self) -> str:
        return self.cb_type.currentData()

    @property
    def year(self) -> str:
        return self.ed_year.text().strip()


class OpposingTab(QWidget):
    """Vertikální splitter: strom posudků nahoře + detail dole."""

    # Emitne se po změně dat (posudek/uložení) — pro souhrn v dolní liště.
    changed = Signal()
    # Požadavek na odeslání oponentských posudků sekretářce (odbaví MainWindow,
    # který má přístup k profilu / e-mailovým nastavením).
    send_reviews_requested = Signal()

    def __init__(self, service: ThesisService, parent=None, *, profile_manager=None) -> None:
        super().__init__(parent)
        self.service = service
        self.profile_manager = profile_manager
        # id oponentur, u kterých už proběhl pokus o dotažení známky z PDF
        # (ať se PDF nečte opakovaně při každém refresh).
        self._grade_synced: set[str] = set()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Toolbar uvnitř tabu
        top = QHBoxLayout()
        top.setContentsMargins(6, 6, 6, 0)
        btn_new = QPushButton("➕ Nový oponentský posudek…")
        btn_new.clicked.connect(self._new_opposing)
        top.addWidget(btn_new)
        btn_send = QPushButton("✉ Odeslat sekretářce…")
        btn_send.setToolTip(
            "Odeslání připravených oponentských posudků sekretářce e-mailem "
            "(vybere se podle oborů sekretářky; přiloží se PDF posudků)."
        )
        btn_send.clicked.connect(self.send_reviews_requested.emit)
        top.addWidget(btn_send)
        top.addStretch()
        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color:#888;font-size:11px;")
        top.addWidget(self.lbl_count)
        outer.addLayout(top)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(7)
        self.tree.setHeaderLabels(
            ["Student / Skupina", "Téma", "Stav", "Vedoucí", "V/O",
             "Odesláno", "Obor"]
        )
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.setMinimumHeight(160)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in range(2, 7):
            h.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        h.setStretchLastSection(False)
        # Sloupec V/O — barevné dvojice písmen, stejně jako ve vedených pracích.
        self._grades_delegate = GradesDelegate(self.tree)
        self.tree.setItemDelegateForColumn(COL_GRADES, self._grades_delegate)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        # Kontextové menu — pravý klik na posudek → Roll-back
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        splitter.addWidget(self.tree)

        self.detail = OpposingDetail(service, profile_manager=self.profile_manager)
        self.detail.setMinimumHeight(520)
        self.detail.saved.connect(lambda _: (self.refresh(), self.changed.emit()))
        self.detail.deleted.connect(lambda _: (self.refresh(), self.changed.emit()))
        self.detail.generate_review_requested.connect(self._on_generate_review)
        splitter.addWidget(self.detail)

        splitter.setSizes([260, 640])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, stretch=1)

        self.refresh()

    # --- posudky ------------------------------------------------------------

    def _on_generate_review(self, opposing_id: str) -> None:
        """Otevře dialog pro výběr šablony + napsání oponentského posudku."""
        op = self.service.get_opposing_thesis(opposing_id)
        if op is None:
            return
        from .review_templates_dialog import GenerateReviewDialog

        dlg = GenerateReviewDialog(self.service, opposing_thesis=op, parent=self)
        dlg.exec()
        # Posudek/přílohy se mohly změnit → refresh seznamu i detailu.
        self.refresh()
        self._select_id(opposing_id)
        self.changed.emit()

    # --- načtení / refresh --------------------------------------------------

    def refresh_combos(self) -> None:
        """Re-naplnění comb vedoucích + oborů v detail panelu (po správě registry)."""
        try:
            self.detail._refresh_supervisors_combo()
        except Exception:
            pass
        try:
            self.detail._reload_obor_items()
        except Exception:
            pass

    def refresh(self) -> None:
        selected_id = self._selected_id()
        self.tree.blockSignals(True)
        try:
            self.tree.clear()
            opposings = self.service.list_opposing_theses()
            current_year = self.service.current_academic_year()
            # Doplň chybějící známku oponenta z nahraného PDF posudku (typicky
            # vlastní posudek stažený ze STAG). Jednorázově za session, jen u
            # prací s PDF a bez známky — jakmile se doplní, příště se přeskočí.
            for o in opposings:
                if (
                    not o.grade_opponent
                    and o.id not in self._grade_synced
                    and any(
                        a.kind == AttachmentKind.OPPONENT_REVIEW
                        and a.is_file
                        and a.url_or_path.lower().endswith(".pdf")
                        for a in o.attachments
                    )
                ):
                    self._grade_synced.add(o.id)
                    self.service.sync_opposing_grades(o.id)
            opposings = self.service.list_opposing_theses()  # re-fetch po sync
            # group by academic_year
            groups: dict[str, list[OpposingThesis]] = {}
            for op in opposings:
                groups.setdefault(op.academic_year or "(bez roku)", []).append(op)

            for year in sorted(groups.keys(), reverse=True):
                year_item = QTreeWidgetItem(
                    [f"📅 {year}    ({len(groups[year])})", "", "", "", ""]
                )
                year_item.setFirstColumnSpanned(True)
                f = year_item.font(0)
                f.setBold(True)
                f.setPointSize(f.pointSize() + 1)
                year_item.setFont(0, f)
                self.tree.addTopLevelItem(year_item)

                ops = sorted(
                    groups[year],
                    key=lambda o: (
                        o.type.value,
                        _czech_key(o.student_last_name),
                        _czech_key(o.student_first_name),
                    ),
                )
                for op in ops:
                    name = (
                        f"{op.student_last_name}, {op.student_first_name}"
                        if op.student_last_name or op.student_first_name
                        else "(neuvedený student)"
                    )
                    title = op.title_cs or "(bez názvu)"
                    state = op.opponent_review_state
                    # Indikace stavu posudku (puntík / Odesláno / podbarvení) má
                    # smysl jen u AKTUÁLNÍHO akademického roku — u starších let je
                    # irelevantní, takže ji potlačíme.
                    is_current = op.academic_year == current_year
                    if is_current:
                        dot = {"done": "🟢", "draft": "🟡", "none": "🔴"}.get(state, "")
                        if dot:
                            title = f"{dot} {title}"
                    if op.related_thesis_id:
                        title = f"🔁 {title}"
                    # Stav práce ze STAG (DUO/ND/…) — užitečné hlavně u
                    # nedokončených.
                    code = op.stag_state_code
                    stav = STAG_STATE_SHORT.get(code, code) if code else "—"
                    # Odeslání posudku sekretářce — jen aktuální rok.
                    if is_current:
                        sent_text, sent_tip = review_sent_indicator(
                            state == "done", op.opponent_review_sent_at
                        )
                    else:
                        sent_text, sent_tip = "", ""
                    gs = (op.grade_supervisor or "").strip()
                    go = (op.grade_opponent or "").strip()
                    # Známky kreslí GradesDelegate z dat ROLE_GRADES; text buňky
                    # je prázdný (a „—", když chybí obě).
                    grades_text = "" if (gs or go) else "—"
                    obor = op.student_obor or "—"
                    type_prefix = op.type.value
                    leaf = QTreeWidgetItem(
                        [
                            f"{type_prefix} · {name}",
                            title,
                            stav,
                            op.supervisor_name or "—",
                            grades_text,
                            sent_text,
                            obor,
                        ]
                    )
                    leaf.setData(0, ROLE_ID, op.id)
                    if gs or go:
                        leaf.setData(COL_GRADES, ROLE_GRADES, (gs, go))
                        leaf.setToolTip(
                            COL_GRADES,
                            f"Vedoucí: {gs or '—'}  ·  Oponent: {go or '—'}",
                        )
                    leaf.setTextAlignment(
                        COL_GRADES,
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                    )
                    if code:
                        leaf.setToolTip(
                            2, STAG_STATE_LABELS.get(code, code) + f" ({code})"
                        )
                    leaf.setTextAlignment(
                        COL_SENT, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                    )
                    if sent_tip:
                        leaf.setToolTip(COL_SENT, sent_tip)
                    # Oponentský posudek — podbarvi sloupec názvu práce
                    # (🟢 hotový · 🟡 jen data · 🔴 chybí) — jen aktuální rok.
                    tint = REVIEW_STATE_TINTS.get(state) if is_current else None
                    if tint:
                        leaf.setBackground(1, QBrush(QColor(tint)))
                        leaf.setForeground(1, QBrush(QColor("#212121")))
                        leaf.setToolTip(
                            1, f"Oponentský posudek: {REVIEW_STATE_LABELS.get(state, '')}"
                        )
                    year_item.addChild(leaf)
                # Aktuální rok rozbalený, starší roky defaultně sbalené.
                year_item.setExpanded(year == current_year)

            # Souhrn hotovo/chybí — jen za AKTUÁLNÍ rok (u starších je irelevantní).
            cur = [o for o in opposings if o.academic_year == current_year]
            done = sum(1 for o in cur if o.opponent_review_state == "done")
            missing = sum(1 for o in cur if o.opponent_review_state == "none")
            self.lbl_count.setText(
                f"Posudků celkem: {len(opposings)}  ·  "
                f"aktuální rok ({current_year}): "
                f"<span style='color:{REVIEW_STATE_STRONG['done']};'>hotovo {done}</span>  ·  "
                f"<span style='color:{REVIEW_STATE_STRONG['none']};'>chybí {missing}</span>"
            )
            self.lbl_count.setTextFormat(Qt.TextFormat.RichText)

            if selected_id:
                self._select_id(selected_id)
        finally:
            self.tree.blockSignals(False)

    def _selected_id(self) -> str | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        return item.data(0, ROLE_ID)

    def _select_id(self, op_id: str) -> bool:
        for i in range(self.tree.topLevelItemCount()):
            year_item = self.tree.topLevelItem(i)
            for j in range(year_item.childCount()):
                leaf = year_item.child(j)
                if leaf.data(0, ROLE_ID) == op_id:
                    self.tree.setCurrentItem(leaf)
                    return True
        return False

    def _on_selection_changed(self) -> None:
        op_id = self._selected_id()
        if op_id is None:
            self.detail.set_opposing(None)
            return
        op = self.service.get_opposing_thesis(op_id)
        self.detail.set_opposing(op)

    def _on_context_menu(self, pos: QPoint) -> None:
        """Kontextové menu — pravý klik na posudek → Roll-back."""
        item = self.tree.itemAt(pos)
        if item is None:
            return
        op_id = item.data(0, ROLE_ID)
        if not op_id:
            return  # year header — nemá menu

        # Import zde, ne na vrcholu (kruhový import s main_window)
        from .rollback_dialog import RollbackOpposingDialog

        menu = QMenu(self.tree)

        # Označení posudku za odeslaný — jen když je posudek hotový.
        op = self.service.get_opposing_thesis(op_id)
        if op is not None and op.opponent_review_state == "done":
            sent = bool(op.opponent_review_sent_at)
            label = (
                "✉ Zrušit označení odeslání posudku" if sent
                else "✉ Označit posudek za odeslaný sekretářce"
            )
            act_sent = QAction(label, self.tree)

            def _toggle_sent(_c=False, oid=op_id, new=not sent) -> None:
                self.service.set_opponent_review_sent(oid, new)
                self.refresh()
                self.detail.set_opposing(self.service.get_opposing_thesis(oid))
                self.changed.emit()

            act_sent.triggered.connect(_toggle_sent)
            menu.addAction(act_sent)
            menu.addSeparator()

        act_rollback = QAction("🗑 Roll-back — smazat kompletně…", self.tree)
        act_rollback.setToolTip(
            "Nenávratně smaže posudek z databáze a všechny jeho soubory."
        )

        def _do_rollback() -> None:
            try:
                self.detail.flush()
            except Exception:
                pass
            dlg = RollbackOpposingDialog(self.service, op_id, self)
            dlg.exec()
            if dlg.executed:
                self.detail.set_opposing(None)
                self.refresh()

        act_rollback.triggered.connect(_do_rollback)
        menu.addAction(act_rollback)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    # --- akce ---------------------------------------------------------------

    def _new_opposing(self) -> None:
        dlg = _NewOpposingDialog(self)
        if not dlg.exec():
            return
        if not dlg.year:
            return
        op = OpposingThesis(
            type=ThesisType(dlg.type_value),
            academic_year=dlg.year,
        )
        self.service.upsert_opposing_thesis(op)
        self.refresh()
        self._select_id(op.id)
