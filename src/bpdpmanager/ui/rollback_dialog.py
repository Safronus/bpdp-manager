"""Roll-back dialog — kompletní smazání práce vč. souborů s preview + confirm.

Workflow:
  1. ``RollbackThesisDialog(service, thesis_id, parent).exec()`` → preview +
     potvrzení.
  2. Pokud uživatel klikne *Smazat kompletně*, dialog provede
     ``service.rollback_thesis(id)`` a po dokončení ukáže sumář.
  3. Atribut ``self.executed`` je True, pokud rollback proběhl.

Obdobně ``RollbackOpposingDialog`` pro oponentské posudky.

Design: read-only preview je dlouhý → použijeme dvoufázový flow (jeden
dialog s dvěma stavy: *náhled* a *hotovo*), aby uživatel viděl jak
předtím, tak po smazání.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from ..services import ThesisService


def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} kB"
    return f"{n / (1024 * 1024):.1f} MB"


class _RollbackDialogBase(QDialog):
    """Společný kostel pro rollback dialogy (thesis i opposing)."""

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.executed = False  # True po úspěšném smazání

        self.setMinimumSize(680, 540)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        header = QLabel("🗑 Roll-back — kompletní smazání")
        header.setStyleSheet("font-size:15px;font-weight:bold;color:#c62828;")
        outer.addWidget(header)

        warning = QLabel(
            "Tato akce <b>nevratně</b> smaže záznam práce z databáze a <b>všechny "
            "související soubory</b> ze složky <code>documents/</code>. "
            "Student / oponent / vedoucí v registru zůstanou (mohou být provázáni "
            "s jinými pracemi)."
        )
        warning.setWordWrap(True)
        warning.setTextFormat(Qt.TextFormat.RichText)
        warning.setStyleSheet(
            "background:#fff3e0;color:#5d4037;padding:8px;border-radius:4px;"
        )
        outer.addWidget(warning)

        self.body = QTextBrowser()
        self.body.setOpenExternalLinks(False)
        outer.addWidget(self.body, stretch=1)

        # Footer tlačítka — vyplní subclass podle stavu
        self.btn_row = QHBoxLayout()
        outer.addLayout(self.btn_row)

    def _clear_buttons(self) -> None:
        while self.btn_row.count():
            item = self.btn_row.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _setup_preview_buttons(self) -> None:
        """Tlačítka v preview fázi: Zrušit + Smazat kompletně."""
        self._clear_buttons()
        self.btn_row.addStretch()
        btn_cancel = QPushButton("Zrušit")
        btn_cancel.clicked.connect(self.reject)
        self.btn_row.addWidget(btn_cancel)
        btn_delete = QPushButton("🗑 Smazat kompletně")
        btn_delete.setStyleSheet(
            "QPushButton { background:#c62828; color:white; padding:6px 14px; "
            "border-radius:3px; font-weight:bold; }"
            "QPushButton:hover { background:#b71c1c; }"
        )
        btn_delete.clicked.connect(self._on_confirm)
        self.btn_row.addWidget(btn_delete)

    def _setup_summary_buttons(self) -> None:
        """Tlačítka v sumární fázi (po úspěšném mazání): Zavřít."""
        self._clear_buttons()
        self.btn_row.addStretch()
        btn_close = QPushButton("Zavřít")
        btn_close.setDefault(True)
        btn_close.clicked.connect(self.accept)
        self.btn_row.addWidget(btn_close)

    def _on_confirm(self) -> None:
        # Druhotné potvrzení — yes/no message box jako last-chance
        confirm = QMessageBox.question(
            self,
            "Potvrď smazání",
            "Opravdu chceš <b>nenávratně</b> smazat tuto práci včetně všech "
            "souborů?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._execute()


# ── Thesis rollback ────────────────────────────────────────────────────────


class RollbackThesisDialog(_RollbackDialogBase):
    """Roll-back vedené práce (``Thesis``)."""

    def __init__(self, service: ThesisService, thesis_id: str, parent=None) -> None:
        super().__init__(service, parent)
        self.thesis_id = thesis_id
        self.setWindowTitle("Roll-back vedené práce")
        self._show_preview()
        self._setup_preview_buttons()

    def _show_preview(self) -> None:
        info = self.service.rollback_preview(self.thesis_id)
        thesis = info["thesis"]
        if thesis is None:
            self.body.setHtml(
                "<p style='color:#c62828;'>Práce nebyla nalezena (možná byla "
                "smazána mezitím). Zavři tento dialog.</p>"
            )
            self._setup_summary_buttons()
            return

        # Student / oponent labely (read-only kontext)
        student = self.service.get_student(thesis.student_id) if thesis.student_id else None
        student_label = (
            f"{student.last_name}, {student.first_name}"
            + (f" [{student.university_id}]" if student.university_id else "")
            if student
            else "<i>bez studenta</i>"
        )
        opp = self.service.get_opponent(thesis.opponent_id) if thesis.opponent_id else None
        opp_label = opp.name if opp else "<i>bez oponenta</i>"

        # File items
        att_rows: list[str] = []
        for label, path, exists, size in info["attachments"]:
            mark = "✓" if exists else "<span style='color:#c62828;'>chybí na disku</span>"
            att_rows.append(
                f"<tr><td>{escape(label)}</td>"
                f"<td><code>{escape(str(path.name))}</code></td>"
                f"<td>{_fmt_bytes(size) if exists else '—'}</td>"
                f"<td>{mark}</td></tr>"
            )
        att_table = (
            "<table style='border-collapse:collapse;'>"
            "<tr style='color:#666;'><th style='text-align:left;'>Štítek</th>"
            "<th style='text-align:left;padding-left:12px;'>Soubor</th>"
            "<th style='text-align:left;padding-left:12px;'>Velikost</th>"
            "<th style='padding-left:12px;'></th></tr>"
            + "".join(att_rows)
            + "</table>"
            if att_rows
            else "<p style='color:#888;'>Žádné přílohy.</p>"
        )

        plag_html = ""
        if info["plagiarism_pdf"]:
            fname, p, exists, size = info["plagiarism_pdf"]
            plag_html = (
                f"<h3>Plagiátorský PDF protokol</h3>"
                f"<p><code>{escape(str(fname))}</code> "
                f"({_fmt_bytes(size) if exists else 'chybí na disku'})</p>"
            )

        extra_html = ""
        if info["extra_files"]:
            items = "".join(
                f"<li><code>{escape(str(p.relative_to(info['documents_dir'])))}</code> "
                f"({_fmt_bytes(size)})</li>"
                for p, size in info["extra_files"]
            )
            extra_html = (
                f"<h3>Další soubory ve složce (neevidované)</h3>"
                f"<ul style='margin-top:0;'>{items}</ul>"
            )

        title_cs = thesis.title_cs or "<i>(bez názvu)</i>"
        html = f"""
        <style>
          h3 {{ margin: 10px 0 4px 0; font-size: 13px; color: #444; }}
          table.kv td {{ padding: 2px 8px 2px 0; vertical-align: top; }}
          table.kv td.k {{ color: #666; white-space: nowrap; }}
        </style>
        <h3>Záznam práce</h3>
        <table class='kv'>
          <tr><td class='k'>Typ / Rok</td><td><b>{thesis.type.value}</b> · {escape(thesis.academic_year)}</td></tr>
          <tr><td class='k'>Stav</td><td>{escape(thesis.status.label)}</td></tr>
          <tr><td class='k'>Student</td><td>{escape(student_label)}</td></tr>
          <tr><td class='k'>Oponent</td><td>{escape(opp_label)}</td></tr>
          <tr><td class='k'>Název CZ</td><td>{escape(title_cs)}</td></tr>
        </table>

        <h3>Přílohy ({len(info['attachments'])})</h3>
        {att_table}
        {plag_html}
        {extra_html}

        <hr>
        <p style='color:#666;'>
          Celkem k odstranění: <b>{_fmt_bytes(info['total_bytes'])}</b><br>
          Složka: <code>{escape(str(info['documents_dir']))}</code>
        </p>
        """
        self.body.setHtml(html)
        self._stash_info = info

    def _execute(self) -> None:
        try:
            stats = self.service.rollback_thesis(self.thesis_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self, "Mazání selhalo", f"Roll-back skončil chybou:\n{exc}"
            )
            return
        self.executed = True
        self._show_summary(stats)

    def _show_summary(self, stats: dict) -> None:
        html = f"""
        <p style='color:#2e7d32;font-weight:bold;'>✓ Práce byla kompletně smazána.</p>
        <table style='border-collapse:collapse;'>
          <tr><td>Soubory smazány:</td><td><b>{stats['files_deleted']}</b></td></tr>
          <tr><td>Plagiátorský PDF:</td><td><b>{stats['plagiarism_pdf']}</b></td></tr>
          <tr><td>Složka documents/ odstraněna:</td>
              <td>{'✓' if stats['documents_dir_removed'] else '—'}</td></tr>
        </table>
        <hr>
        <p style='color:#888;font-size:11px;'>
          Záznam v <code>db.json</code> byl odstraněn.
          Student / oponent / vedoucí v registru zůstávají.
        </p>
        """
        self.body.setHtml(html)
        self._setup_summary_buttons()


# ── Opposing rollback ──────────────────────────────────────────────────────


class RollbackOpposingDialog(_RollbackDialogBase):
    """Roll-back oponentského posudku (``OpposingThesis``)."""

    def __init__(self, service: ThesisService, op_id: str, parent=None) -> None:
        super().__init__(service, parent)
        self.op_id = op_id
        self.setWindowTitle("Roll-back oponentského posudku")
        self._show_preview()
        self._setup_preview_buttons()

    def _show_preview(self) -> None:
        info = self.service.rollback_opposing_preview(self.op_id)
        op = info["opposing"]
        if op is None:
            self.body.setHtml(
                "<p style='color:#c62828;'>Posudek nebyl nalezen.</p>"
            )
            self._setup_summary_buttons()
            return

        # File items
        att_rows: list[str] = []
        for label, path, exists, size in info["attachments"]:
            mark = "✓" if exists else "<span style='color:#c62828;'>chybí na disku</span>"
            att_rows.append(
                f"<tr><td>{escape(label)}</td>"
                f"<td><code>{escape(str(path.name))}</code></td>"
                f"<td>{_fmt_bytes(size) if exists else '—'}</td>"
                f"<td>{mark}</td></tr>"
            )
        att_table = (
            "<table style='border-collapse:collapse;'>"
            "<tr style='color:#666;'><th style='text-align:left;'>Štítek</th>"
            "<th style='text-align:left;padding-left:12px;'>Soubor</th>"
            "<th style='text-align:left;padding-left:12px;'>Velikost</th>"
            "<th style='padding-left:12px;'></th></tr>"
            + "".join(att_rows)
            + "</table>"
            if att_rows
            else "<p style='color:#888;'>Žádné přílohy.</p>"
        )

        extra_html = ""
        if info["extra_files"]:
            items = "".join(
                f"<li><code>{escape(str(p.relative_to(info['documents_dir'])))}</code> "
                f"({_fmt_bytes(size)})</li>"
                for p, size in info["extra_files"]
            )
            extra_html = (
                f"<h3>Další soubory ve složce (neevidované)</h3>"
                f"<ul style='margin-top:0;'>{items}</ul>"
            )

        student_label = (
            f"{op.student_last_name}, {op.student_first_name}"
            + (f" [{op.student_university_id}]" if op.student_university_id else "")
        )
        title_cs = op.title_cs or "<i>(bez názvu)</i>"
        html = f"""
        <style>
          h3 {{ margin: 10px 0 4px 0; font-size: 13px; color: #444; }}
          table.kv td {{ padding: 2px 8px 2px 0; vertical-align: top; }}
          table.kv td.k {{ color: #666; white-space: nowrap; }}
        </style>
        <h3>Záznam oponentského posudku</h3>
        <table class='kv'>
          <tr><td class='k'>Typ / Rok</td><td><b>{op.type.value}</b> · {escape(op.academic_year)}</td></tr>
          <tr><td class='k'>Student</td><td>{escape(student_label)}</td></tr>
          <tr><td class='k'>Vedoucí</td><td>{escape(op.supervisor_name or '—')}</td></tr>
          <tr><td class='k'>Název CZ</td><td>{escape(title_cs)}</td></tr>
        </table>

        <h3>Přílohy ({len(info['attachments'])})</h3>
        {att_table}
        {extra_html}

        <hr>
        <p style='color:#666;'>
          Celkem k odstranění: <b>{_fmt_bytes(info['total_bytes'])}</b><br>
          Složka: <code>{escape(str(info['documents_dir']))}</code>
        </p>
        """
        self.body.setHtml(html)

    def _execute(self) -> None:
        try:
            stats = self.service.rollback_opposing_thesis(self.op_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self, "Mazání selhalo", f"Roll-back skončil chybou:\n{exc}"
            )
            return
        self.executed = True
        self._show_summary(stats)

    def _show_summary(self, stats: dict) -> None:
        html = f"""
        <p style='color:#2e7d32;font-weight:bold;'>✓ Posudek byl kompletně smazán.</p>
        <table style='border-collapse:collapse;'>
          <tr><td>Soubory smazány:</td><td><b>{stats['files_deleted']}</b></td></tr>
          <tr><td>Složka documents/opposing-… odstraněna:</td>
              <td>{'✓' if stats['documents_dir_removed'] else '—'}</td></tr>
        </table>
        <hr>
        <p style='color:#888;font-size:11px;'>
          Záznam v <code>db.json</code> byl odstraněn.
          Vedoucí (registr) zůstává.
        </p>
        """
        self.body.setHtml(html)
        self._setup_summary_buttons()
