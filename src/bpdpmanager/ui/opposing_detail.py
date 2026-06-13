"""Detail panel pro jeden oponentský posudek.

Liší se od ``ThesisDetail`` zjednodušeným obsahem:
- žádné stavy / přechody / autosave debounce na bázi 1.5 s (jen explicitní)
- žádná anotace, literatura, plagiátorství, poznámky
- inline údaje o studentovi + vedoucím (ne přes Student/Opponent entity)
- známky vedoucího + oponenta
- dokumenty: plný text, posudek vedoucího, posudek oponenta
"""

from __future__ import annotations

import html
from datetime import datetime

from PySide6.QtCore import QTimer, QUrl, Signal
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..models import OpposingThesis
from ..models.enums import AttachmentKind
from ..services import ThesisService
from .thesis_detail import (
    _format_numbered,
    _split_items,
)
from .widgets import DocumentsWidget

AUTOSAVE_DEBOUNCE_MS = 1500


class OpposingDetail(QWidget):
    """Editor oponentského posudku — záložky Souhrn (vč. editace známek V/O)
    a Dokumenty. Ostatní data (student, název, vedoucí, obor, rok) jsou jen
    pro čtení a plní se importem ze STAG / vyčtením z posudku."""

    saved = Signal(str)  # opposing thesis id
    deleted = Signal(str)
    generate_review_requested = Signal(str)  # opposing thesis id
    # Id zobrazené oponentury ("" = prázdno) — sbalitelný panel
    # (CollapsibleDetailPane) podle toho skrývá detail a rozbalí při výběru jiné.
    content_changed = Signal(str)

    def __init__(self, service: ThesisService, parent=None, *, profile_manager=None) -> None:
        super().__init__(parent)
        self.service = service
        self.profile_manager = profile_manager
        self.op: OpposingThesis | None = None
        self._loading = False
        self._dirty = False
        self._last_save_at: datetime | None = None

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(AUTOSAVE_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._autosave)

        self._build_ui()
        self._show_empty()

    # --- konstrukce UI -------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.placeholder = QLabel(
            tr("Vyber posudek v seznamu nahoře, nebo přidej nový.")
        )
        self.placeholder.setStyleSheet("color: #888; padding: 24px;")
        outer.addWidget(self.placeholder)

        self.container = QWidget()
        outer.addWidget(self.container)

        layout = QVBoxLayout(self.container)

        # Hlavička
        header = QHBoxLayout()
        self.lbl_title = QLabel("")
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header.addWidget(self.lbl_title, stretch=1)
        self.lbl_save_state = QLabel("")
        self.lbl_save_state.setStyleSheet("color:#888;font-size:11px;")
        header.addWidget(self.lbl_save_state)
        self.btn_generate_review = QPushButton(tr("📝 Napsat posudek…"))
        self.btn_generate_review.setToolTip(
            tr("Vyplnit oponentský posudek z šablony (kritéria, body, známka) "
            "a připojit jako přílohu.")
        )
        self.btn_generate_review.clicked.connect(self._generate_review)
        header.addWidget(self.btn_generate_review)
        self.btn_delete = QPushButton(tr("Smazat"))
        self.btn_delete.clicked.connect(self._delete)
        header.addWidget(self.btn_delete)
        layout.addLayout(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_summary_tab(), tr("📋 Souhrn"))
        self.tabs.addTab(self._build_documents_tab(), tr("📎 Dokumenty"))
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs, stretch=1)

        # Save button
        save_row = QHBoxLayout()
        save_row.addStretch()
        self.btn_save = QPushButton(tr("Uložit změny"))
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._save_now)
        save_row.addWidget(self.btn_save)
        layout.addLayout(save_row)

        self._connect_dirty_signals()

    def _build_summary_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        # Editovatelné známky V/O — jediná věc, kterou u oponentury ručně měníš
        # (zbytek dat se plní importem ze STAG / vyčte z posudku). Ostatní pole
        # se u oponovaných prací needitují, proto samostatná záložka „Detail"
        # není (oprava jména/názvu apod. se řeší přes STAG re-import).
        box_grades = QGroupBox(tr("Známky"))
        gl = QHBoxLayout(box_grades)
        gl.setContentsMargins(8, 10, 8, 8)
        gl.addWidget(QLabel(tr("Vedoucí:")))
        self.cb_grade_sup = self._make_grade_combo()
        gl.addWidget(self.cb_grade_sup)
        gl.addSpacing(20)
        gl.addWidget(QLabel(tr("Oponent (moje):")))
        self.cb_grade_opp = self._make_grade_combo()
        gl.addWidget(self.cb_grade_opp)
        gl.addStretch()
        layout.addWidget(box_grades)

        self.summary_view = QTextBrowser()
        self.summary_view.setOpenExternalLinks(False)
        self.summary_view.setOpenLinks(False)
        self.summary_view.anchorClicked.connect(self._on_summary_anchor_clicked)
        self.summary_view.setStyleSheet("QTextBrowser { padding: 12px; }")
        layout.addWidget(self.summary_view, stretch=1)
        return w

    @staticmethod
    def _make_grade_combo() -> QComboBox:
        cb = QComboBox()
        cb.setEditable(True)
        cb.addItem("")  # nezvoleno
        for g in ("A", "B", "C", "D", "E", "F", "1", "2", "3", "4"):
            cb.addItem(g)
        cb.setMaximumWidth(110)
        return cb

    def _build_documents_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        layout.addWidget(QLabel(
            tr("Dokumenty k oponentskému posudku (plný text práce, posudek vedoucího, "
            "tvůj posudek oponenta, příp. další):")
        ))

        # Stejný agregovaný widget jako u vedených prací (strom podle typu,
        # verzování, otevřít / Finder / odebrat, indikace chybějících…).
        self.documents_widget = DocumentsWidget(
            self.service, profile_manager=self.profile_manager
        )
        self.documents_widget.changed.connect(self._on_documents_changed)
        layout.addWidget(self.documents_widget, stretch=1)
        return w

    def _on_documents_changed(self) -> None:
        # Dokumenty se mění přímo přes službu — přenačti op a souhrn. Nahrání PDF
        # posudku vedoucího mohlo doplnit známku → promítni i do polí v Detailu.
        if self.op is None:
            return
        # Re-sync známek z nahraného PDF posudku (vedoucího/oponenta).
        self.service.sync_opposing_grades(self.op.id)
        self.op = self.service.get_opposing_thesis(self.op.id)
        was_loading = self._loading
        self._loading = True
        try:
            self.cb_grade_sup.setCurrentText(self.op.grade_supervisor or "")
            self.cb_grade_opp.setCurrentText(self.op.grade_opponent or "")
        finally:
            self._loading = was_loading
        self._refresh_summary()
        # Obnov seznam oponentur (sloupce Známky V/O + Posudky) přes „saved".
        self.saved.emit(self.op.id)

    # --- pomocné: zobrazení -------------------------------------------------

    def _show_empty(self) -> None:
        self.placeholder.setVisible(True)
        self.container.setVisible(False)

    def _show_form(self) -> None:
        self.placeholder.setVisible(False)
        self.container.setVisible(True)

    def set_opposing(self, op: OpposingThesis | None) -> None:
        # flush rozdělané z předchozího posudku
        if self._dirty and self.op is not None:
            self._autosave()

        self.op = op
        if op is None:
            self.documents_widget.set_opposing_id(None)
            self._show_empty()
            self.content_changed.emit("")
            return
        # Doplň chybějící známky i zpětně (z napsaného posudku / nahraného PDF).
        synced = self.service.sync_opposing_grades(op.id)
        if synced is not None:
            self.op = op = synced
        self._show_form()
        self.content_changed.emit(op.id)

        self._loading = True
        try:
            # Editují se jen známky V/O; ostatní data práce jsou jen pro čtení
            # (v Souhrnu) a plní se importem ze STAG / vyčtením z posudku.
            self.cb_grade_sup.setCurrentText(op.grade_supervisor or "")
            self.cb_grade_opp.setCurrentText(op.grade_opponent or "")

            self.documents_widget.set_opposing_id(op.id)
            self.lbl_title.setText(self._compose_header_label())
        finally:
            self._loading = False
        self._dirty = False
        self._debounce.stop()
        self._update_save_label(idle=True)

        # auto-switch na Souhrn
        self.tabs.setCurrentIndex(0)
        self._refresh_summary()

    # --- dirty / autosave ---------------------------------------------------

    def _connect_dirty_signals(self) -> None:
        # Editují se jen známky V/O.
        self.cb_grade_sup.currentTextChanged.connect(self._mark_dirty)
        self.cb_grade_opp.currentTextChanged.connect(self._mark_dirty)

    def _mark_dirty(self, *_args) -> None:
        if self._loading or self.op is None:
            return
        self._dirty = True
        self._update_save_label(pending=True)
        self._debounce.start()

    def _autosave(self) -> None:
        if self.op is None or not self._dirty:
            return
        try:
            self._collect()
            self.service.upsert_opposing_thesis(self.op)
        except Exception as exc:  # noqa: BLE001
            self._update_save_label(error=str(exc))
            return
        self._dirty = False
        self._last_save_at = datetime.now()
        self._update_save_label()
        self.lbl_title.setText(self._compose_header_label())
        if self.tabs.currentIndex() == 0:
            self._refresh_summary()
        self.saved.emit(self.op.id)

    def _save_now(self) -> None:
        self._autosave()

    def _generate_review(self) -> None:
        """Klik na „📝 Napsat posudek…" → flush + emit (OpposingTab otevře dialog)."""
        if self.op is None:
            return
        # Flushni rozpracované změny, aby šablona dostala aktuální data.
        self.flush()
        self.generate_review_requested.emit(self.op.id)

    def flush(self) -> None:
        self._debounce.stop()
        if self._dirty:
            self._autosave()

    def _update_save_label(
        self, *, idle: bool = False, pending: bool = False, error: str | None = None
    ) -> None:
        if idle:
            self.lbl_save_state.setText("")
            return
        if error:
            self.lbl_save_state.setText(f"⚠ Chyba: {error}")
            self.lbl_save_state.setStyleSheet("color:#c62828;font-size:11px;")
            return
        if pending:
            self.lbl_save_state.setText(tr("● Ukládám…"))
            self.lbl_save_state.setStyleSheet("color:#ef6c00;font-size:11px;")
            return
        ts = self._last_save_at.strftime("%H:%M:%S") if self._last_save_at else ""
        self.lbl_save_state.setText(tr("✓ Uloženo") + f" {ts}")
        self.lbl_save_state.setStyleSheet("color:#2e7d32;font-size:11px;")

    def _collect(self) -> None:
        # Z editoru se ukládají jen známky V/O; ostatní pole zůstávají beze
        # změny (plní se importem ze STAG / z posudku), attachments řeší tabulka.
        assert self.op is not None
        self.op.grade_supervisor = self.cb_grade_sup.currentText().strip()
        self.op.grade_opponent = self.cb_grade_opp.currentText().strip()

    # --- header label -------------------------------------------------------

    def _compose_header_label(self) -> str:
        if self.op is None:
            return ""
        parts = []
        if self.op.type:
            parts.append(self.op.type.value)
        if self.op.title_cs:
            parts.append(self.op.title_cs)
        if self.op.student_last_name or self.op.student_first_name:
            parts.append(self.op.student_full_name)
        return " — ".join(parts) or "(bez názvu)"

    # --- delete -------------------------------------------------------------

    def _delete(self) -> None:
        if self.op is None:
            return
        confirm = QMessageBox.question(
            self,
            tr("Smazat posudek"),
            f"Opravdu smazat oponentský posudek „{self._compose_header_label()}“?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            op_id = self.op.id
            self.service.delete_opposing_thesis(op_id)
            self.set_opposing(None)
            self.deleted.emit(op_id)

    # --- souhrn -------------------------------------------------------------

    def _on_tab_changed(self, index: int) -> None:
        if index == 0:
            self._refresh_summary()

    def _refresh_summary(self) -> None:
        if self.op is None:
            self.summary_view.setHtml(
                "<p style='color:#888;padding:24px;'>Vyber posudek vlevo.</p>"
            )
            return
        self.summary_view.setHtml(self._build_summary_html(self.op))

    @staticmethod
    def _copy_btn(field: str, tooltip: str) -> str:
        return (
            f'&nbsp;<a href="copy:{field}" title="{tooltip}" '
            'style="text-decoration:none;font-size:11pt;color:#42a5f5;">📋</a>'
        )

    def _build_reviews_summary_html(self, op: OpposingThesis) -> str:
        """Náhled uložených posudků (current verze) — body, kritéria, známka.

        Stejně jako u vedených prací: ukáže strukturovaný posudek vč. komentáře
        a navržené známky, aby byl v Souhrnu vidět i u oponentur.
        """
        e = html.escape
        reviews = [r for r in op.reviews if r.is_current]
        if not reviews:
            return ""
        reviews.sort(key=lambda r: 0 if r.role == "supervisor" else 1)

        grade_colors = {
            "A": "#2e7d32", "B": "#43a047", "C": "#fb8c00",
            "D": "#f57c00", "E": "#e65100", "F": "#c62828", "FX": "#c62828",
        }
        blocks: list[str] = []
        for r in reviews:
            role_label = (
                "🎓 Posudek vedoucího" if r.role == "supervisor"
                else "🧐 Posudek oponenta"
            )
            grade = r.suggested_grade
            grade_color = grade_colors.get(grade, "#666")
            grade_badge = (
                f'<span style="background-color:{grade_color};color:white;'
                f'padding:2px 10px;border-radius:8px;font-weight:bold;">{e(grade)}</span>'
            )
            crit_rows = ""
            for c in r.criteria:
                crit_rows += (
                    f"<tr><td style='padding:1px 10px 1px 0;color:#555;'>{e(c.label)}</td>"
                    f"<td style='padding:1px 6px;color:#888;text-align:center;'>×{c.weight:g}</td>"
                    f"<td style='padding:1px 6px;text-align:center;'><b>{c.score:g}</b>/5</td></tr>"
                )
            crit_table = (
                f"<table style='margin:4px 0 4px 12px;'>{crit_rows}</table>"
                if crit_rows else ""
            )
            comment_html = (
                e(r.overall_comment.strip()).replace("\n", "<br>")
                if r.overall_comment.strip()
                else "<span style='color:#888;font-style:italic;'>(bez komentáře)</span>"
            )
            files_bits = []
            if r.xlsx_filename:
                files_bits.append("📄 XLSX")
            if r.pdf_filename:
                files_bits.append("📕 PDF")
            files_str = (
                " · ".join(files_bits) if files_bits
                else "<span style='color:#888;'>(soubory nevygenerovány)</span>"
            )
            blocks.append(
                f"<div style='margin:6px 0 12px 0;padding:8px;"
                f"border-left:3px solid {grade_color};background:rgba(128,128,128,0.06);'>"
                f"<p style='margin:0 0 4px 0;'><b>{role_label}</b> &nbsp; "
                f"body {r.total_weighted_points:.1f}/{r.max_points:g} &nbsp; "
                f"procenta {r.percentage:.1f} % &nbsp; známka {grade_badge}</p>"
                f"{crit_table}"
                f"<p style='margin:4px 0 0 0;'><b>Hodnocení:</b> {comment_html}</p>"
                f"<p style='margin:2px 0 0 0;color:#888;font-size:11px;'>"
                f"{files_str} &nbsp;·&nbsp; {e(r.place_date)}</p>"
                f"</div>"
            )
        return "".join(blocks)

    def _build_summary_html(self, op: OpposingThesis) -> str:
        e = html.escape
        cp = self._copy_btn

        type_label = op.type.value
        year = op.academic_year or "—"
        student = op.student_full_name or "(student neuveden)"
        obor = op.student_obor or "—"
        uni_id = op.student_university_id or "—"
        sup_name = op.supervisor_name or "(vedoucí neuveden)"
        sup_email = op.supervisor_email or ""

        # Velký nadpisový pruh
        hdr_color = "#1976d2"
        header_bar = (
            f'<table width="100%" cellpadding="14" cellspacing="0" '
            f'style="background-color:{hdr_color};margin-bottom:18px;">'
            f"<tr>"
            f'<td style="color:white;font-weight:bold;font-size:16pt;'
            f"letter-spacing:1.5px;\">📋 OPONENTSKÝ POSUDEK</td>"
            f'<td align="right" style="color:white;font-size:11pt;">'
            f"Akademický rok: <b>{e(year)}</b></td>"
            f"</tr></table>"
        )

        title_line = (
            f'<h2 style="color:{hdr_color};margin:0 0 4px 0;line-height:1.35;">'
            f"{e(type_label)} — {e(op.title_cs or '(bez názvu)')}"
            f"{cp('title_cs', 'Zkopírovat název')} — "
            f"<span>{e(student)}</span> "
            f'<span style="color:#9e9e9e;">({e(obor)})</span> '
            f'<span style="color:#9e9e9e;">→ {e(uni_id)}</span>'
            f"</h2>"
        )
        sup_line = (
            f'<p style="color:#666;margin:0 0 12px 0;">'
            f"<b>Vedoucí:</b> {e(sup_name)}"
        )
        if sup_email:
            sup_line += (
                f' &nbsp;<a href="mailto:{e(sup_email)}" '
                f'style="color:#1976d2;">{e(sup_email)}</a>'
            )
        sup_line += "</p>"

        # STAG
        stag_html = ""
        if op.stag_url:
            stag_html = (
                f'<p style="margin:6px 0 14px 0;color:#666;">'
                f'<b>🔗 STAG:</b> '
                f'<a href="{e(op.stag_url)}" style="color:#1976d2;">{e(op.stag_url)}</a>'
                f"{cp('stag_url', 'Zkopírovat STAG URL')}"
                f"</p>"
            )

        # Body zadání
        items = _split_items(op.objectives)
        if items:
            items_html = "".join(
                f"<li style='margin-bottom:4px;'>{e(line)}</li>" for line in items
            )
            obj_html = f"<ol style='margin-left:1.2em;line-height:1.55;'>{items_html}</ol>"
        else:
            obj_html = "<p style='color:#888;font-style:italic;'>(bez bodů zadání)</p>"

        # Známky — velké barevné badge (vycentrované)
        def grade_badge(label: str, value: str) -> str:
            color = self._grade_color(value)
            disp = e(value) if value else "—"
            return (
                '<td style="padding:0 24px;text-align:center;vertical-align:top;">'
                f"<div style='color:#666;font-size:10pt;text-align:center;'>{label}</div>"
                f'<div style="background-color:{color};color:white;'
                "font-weight:bold;font-size:18pt;padding:6px 16px;"
                "border-radius:6px;display:inline-block;text-align:center;"
                f'min-width:28px;">{disp}</div>'
                "</td>"
            )

        grades_table = (
            "<table style='margin:12px auto;'><tr>"
            + grade_badge(tr("Vedoucí:"), op.grade_supervisor)
            + grade_badge(tr("Oponent (moje):"), op.grade_opponent)
            + "</tr></table>"
        )

        # Dokumenty — jen AKTUÁLNÍ přílohy (archiv starších verzí se neukazuje),
        # stejně jako v Souhrnu vedených prací.
        cur_atts = [a for a in op.attachments if a.is_current]
        if cur_atts:
            rows = ""
            for att in sorted(cur_atts, key=lambda a: a.kind.label):
                rows += (
                    f"<tr>"
                    f"<td style='padding:3px 14px 3px 0;'><b>{e(att.kind.label)}</b></td>"
                    f"<td style='padding:3px 0;'>{'📄 ' if att.is_file else '🔗 '}{e(att.label)}</td>"
                    f"</tr>"
                )
            docs_html = f"<table>{rows}</table>"
        else:
            docs_html = "<p style='color:#888;font-style:italic;'>(žádné dokumenty)</p>"

        section_style = "color:#ffa726;margin-top:18px;margin-bottom:6px;"

        # Napsaný posudek (strukturovaná data) — stejně jako u vedených prací.
        reviews_html = self._build_reviews_summary_html(op)
        reviews_section = (
            f'<h3 style="{section_style}">📝 Napsaný posudek</h3>{reviews_html}'
            if reviews_html else ""
        )

        # Odeslání oponentského posudku sekretářce.
        has_review = any(
            a.kind == AttachmentKind.OPPONENT_REVIEW for a in op.attachments
        ) or any(r.role == "opponent" for r in op.reviews)
        if op.opponent_review_sent_at:
            sent_body = (
                '<span style="color:#2e7d32;">✓ odesláno '
                f'{e(op.opponent_review_sent_at.strftime("%d.%m.%Y"))}</span>'
            )
        elif has_review:
            sent_body = '<span style="color:#c62828;">✗ neodesláno</span>'
        else:
            sent_body = ""
        sent_section = (
            f'<h3 style="{section_style}">Odeslání posudku</h3>'
            f"<p>📨 Oponentský posudek sekretářce: {sent_body}</p>"
            if sent_body else ""
        )

        # Pořadí sekcí: Body zadání → Známky → Napsaný posudek → Odeslání → Dokumenty.
        return (
            "<html><body>"
            f"{header_bar}"
            f"{title_line}"
            f"{sup_line}"
            f"{stag_html}"
            f'<h3 style="{section_style}">Body zadání'
            f"{cp('objectives', 'Zkopírovat body zadání')}</h3>"
            f"{obj_html}"
            f'<h3 style="{section_style}">Známky</h3>'
            f"{grades_table}"
            f"{reviews_section}"
            f"{sent_section}"
            f'<h3 style="{section_style}">📎 Dokumenty</h3>'
            f"{docs_html}"
            "</body></html>"
        )

    @staticmethod
    def _grade_color(value: str) -> str:
        v = (value or "").upper()
        if v in ("A", "1"):
            return "#2e7d32"  # zelená
        if v in ("B", "2"):
            return "#66bb6a"  # světle zelená
        if v in ("C", "3"):
            return "#fbc02d"  # žlutá
        if v in ("D",):
            return "#ef6c00"  # oranžová
        if v in ("E", "4"):
            return "#e64a19"  # tmavě oranžová
        if v in ("F",):
            return "#c62828"  # červená
        return "#9e9e9e"  # šedá (nezadáno)

    def _on_summary_anchor_clicked(self, url: QUrl) -> None:
        s = url.toString()
        if s.startswith("copy:"):
            field = s[len("copy:"):]
            if self.op is None:
                return
            text = self._field_value(field)
            if text is None:
                return
            QApplication.clipboard().setText(text)
            QToolTip.showText(QCursor.pos(), f"📋 Zkopírováno", self.summary_view)
            return
        if url.scheme() in ("http", "https", "file", "mailto"):
            QDesktopServices.openUrl(url)

    def _field_value(self, field: str) -> str | None:
        op = self.op
        if op is None:
            return None
        if field == "title_cs":
            return op.title_cs or ""
        if field == "stag_url":
            return op.stag_url or ""
        if field == "objectives":
            return _format_numbered(op.objectives)
        return None
