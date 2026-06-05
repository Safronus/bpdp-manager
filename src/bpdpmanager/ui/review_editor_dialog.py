"""ReviewEditorDialog — strukturovaný formulář pro vyplnění posudku.

Vstup: ``Review`` (existující nebo nově vytvořený s předvyplněnými
základními poli + criteria scaffold ze schématu šablony).

Výstup: po úspěšném *Save* je ``self.review`` aktualizovaný objekt
a ``self.generated_xlsx`` / ``self.generated_pdf`` cesty k souborům
(pokud uživatel klikl Save & Generate).

Layout:
- Hlavička (read-only základní info)
- Sekce „Splnění bodů zadání" — combo
- Sekce „Kritéria hodnocení" — tabulka s váhou + spin box pro 0–5
  + live sum/percentage/grade
- Sekce „Plagiátorství" (jen pro supervisor)
- Volný text „Celkové hodnocení, připomínky a dotazy"
- Místo, datum
- Tlačítka: Zrušit · Uložit jen JSON · Uložit & vyrobit XLSX+PDF
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..models import Review
from ..services import ThesisService


class ReviewEditorDialog(QDialog):
    """Editor strukturovaného posudku.

    Args:
        service: ThesisService.
        thesis_id: ID práce (Thesis) nebo oponentského posudku
            (OpposingThesis) — záleží na ``opposing`` flag.
        review: Předvyplněný ``Review`` objekt (typicky vytvořený
            volajícím s template_id + scaffolded kritérii).
        opposing: True když thesis_id reprezentuje OpposingThesis.
    """

    def __init__(
        self,
        service: ThesisService,
        thesis_id: str,
        review: Review,
        *,
        opposing: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.thesis_id = thesis_id
        self.review = review
        self.opposing = opposing
        self.generated_xlsx: Path | None = None
        self.generated_pdf: Path | None = None
        self.saved = False  # True po úspěšném Save (i bez generování souborů)

        self.setWindowTitle(f"Posudek — {review.template_name or review.role}")
        # Minimum + výchozí velikost — editor má hodně sekcí (kritéria,
        # plagiátorství, komentář), takže otevři rovnou dost vysoko, ať
        # uživatel nemusí ručně zvětšovat.
        self.setMinimumSize(900, 600)
        self.resize(960, 940)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        # ── Hlavička ────────────────────────────────────────────────────
        title_text = (
            f"📝 {'Posudek vedoucího' if review.role == 'supervisor' else 'Posudek oponenta'}"
            f" — {review.template_name or 'bez šablony'}"
        )
        header = QLabel(title_text)
        header.setStyleSheet("font-size:15px;font-weight:bold;")
        outer.addWidget(header)

        meta = QLabel(
            f"<b>Student:</b> {escape(review.student_name or '—')} &nbsp;·&nbsp; "
            f"<b>{'Vedoucí' if review.role == 'supervisor' else 'Oponent'}:</b> "
            f"{escape(review.user_name or '—')}<br>"
            f"<b>Téma:</b> {escape(review.title_cs or '—')}<br>"
            f"<b>Rok:</b> {escape(review.academic_year or '—')}"
        )
        meta.setTextFormat(Qt.TextFormat.RichText)
        meta.setStyleSheet(
            "background-color: palette(base); color: palette(text); "
            "border: 1px solid palette(mid); padding: 8px; border-radius: 3px;"
        )
        outer.addWidget(meta)

        # ── Scroll area s obsahem ──────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)

        # ── Splnění bodů zadání ───────────────────────────────────────
        box_fulfill = QGroupBox("Splnění všech bodů zadání")
        form_f = QFormLayout(box_fulfill)
        self.cb_fulfilled = QComboBox()
        for v in (
            "splnil(a)",
            "nesplnil(a)",
            "fulfilled",
            "not fulfilled",
        ):
            self.cb_fulfilled.addItem(v, v)
        idx = self.cb_fulfilled.findData(review.assignment_fulfilled or "splnil(a)")
        if idx >= 0:
            self.cb_fulfilled.setCurrentIndex(idx)
        self.cb_fulfilled.currentTextChanged.connect(self._refresh_summary)
        form_f.addRow("Stav", self.cb_fulfilled)
        content_layout.addWidget(box_fulfill)

        # ── Kritéria ──────────────────────────────────────────────────
        box_crit = QGroupBox("Kritéria hodnocení (skóre 0–5)")
        crit_layout = QVBoxLayout(box_crit)
        crit_layout.setSpacing(2)

        # Header
        hdr_row = QHBoxLayout()
        hdr_row.addWidget(QLabel("<b>Kritérium</b>"), stretch=1)
        hdr_row.addWidget(QLabel("<b>Váha</b>"))
        hdr_row.addWidget(QLabel("<b>Body</b>"))
        for w in box_crit.findChildren(QLabel):
            w.setTextFormat(Qt.TextFormat.RichText)
        crit_layout.addLayout(hdr_row)

        self.score_spinboxes: list[QSpinBox] = []
        for cs in review.criteria:
            row = QHBoxLayout()
            lbl = QLabel(escape(cs.label))
            lbl.setWordWrap(True)
            lbl.setMinimumWidth(420)
            row.addWidget(lbl, stretch=1)

            weight_lbl = QLabel(f"{cs.weight:g}")
            weight_lbl.setStyleSheet("color:#888;")
            weight_lbl.setMinimumWidth(40)
            weight_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(weight_lbl)

            # Body 0–5 po celých bodech (ne po půlkách).
            spin = QSpinBox()
            spin.setRange(0, 5)
            spin.setSingleStep(1)
            spin.setValue(int(round(float(cs.score))))
            spin.setFixedWidth(64)
            spin.valueChanged.connect(self._refresh_summary)
            row.addWidget(spin)

            self.score_spinboxes.append(spin)
            crit_layout.addLayout(row)

        content_layout.addWidget(box_crit)

        # Souhrn (live)
        self.lbl_summary = QLabel()
        self.lbl_summary.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_summary.setStyleSheet(
            "background-color: palette(base); color: palette(text); "
            "border: 1px solid palette(mid); padding: 8px; border-radius: 3px;"
        )
        content_layout.addWidget(self.lbl_summary)

        # ── Plagiátorství (jen supervisor) ────────────────────────────
        if review.role == "supervisor":
            box_plag = QGroupBox("Výsledek kontroly plagiátorství (jen pro vedoucího)")
            form_p = QFormLayout(box_plag)
            self.cb_plag_verdict = QComboBox()
            for v in (
                "Práce není plagiát",
                "Práce je plagiát",
                "Práce nebyla posouzena",
            ):
                self.cb_plag_verdict.addItem(v, v)
            idx = self.cb_plag_verdict.findData(review.plagiarism_verdict)
            if idx >= 0:
                self.cb_plag_verdict.setCurrentIndex(idx)
            form_p.addRow("Verdikt", self.cb_plag_verdict)

            self.ed_plag_just = QPlainTextEdit(review.plagiarism_justification)
            self.ed_plag_just.setMaximumHeight(80)
            self.ed_plag_just.setPlaceholderText(
                "Zdůvodnění (% shody, kontext, …)"
            )
            form_p.addRow("Zdůvodnění", self.ed_plag_just)
            content_layout.addWidget(box_plag)
        else:
            self.cb_plag_verdict = None  # type: ignore
            self.ed_plag_just = None  # type: ignore

        # ── Celkové hodnocení ─────────────────────────────────────────
        box_overall = QGroupBox("Celkové hodnocení, připomínky a dotazy")
        v_overall = QVBoxLayout(box_overall)
        self.ed_overall = QPlainTextEdit(review.overall_comment)
        self.ed_overall.setMinimumHeight(140)
        self.ed_overall.setPlaceholderText(
            "Slovní zhodnocení práce, dotazy k obhajobě…"
        )
        v_overall.addWidget(self.ed_overall)
        content_layout.addWidget(box_overall)

        # ── Místo, datum ──────────────────────────────────────────────
        box_meta = QGroupBox("Podpis")
        form_m = QFormLayout(box_meta)
        self.ed_place_date = QLineEdit(review.place_date)
        self.ed_place_date.setPlaceholderText("např. Zlín, 26. 5. 2026")
        form_m.addRow("Místo, datum", self.ed_place_date)
        content_layout.addWidget(box_meta)

        # ── Tlačítka ──────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Zrušit")
        btn_cancel.clicked.connect(self.reject)
        self.btn_save_only = QPushButton("💾 Uložit (jen data)")
        self.btn_save_only.setToolTip(
            "Uloží strukturovaná data posudku. XLSX a PDF nevygeneruje — "
            "stačí třeba pro rozpracovaný posudek, který chceš dokončit později."
        )
        self.btn_save_only.clicked.connect(self._save_only)

        self.btn_save_generate = QPushButton("📝 Uložit & vyrobit XLSX + PDF")
        bf = self.btn_save_generate.font()
        bf.setBold(True)
        self.btn_save_generate.setFont(bf)
        self.btn_save_generate.setDefault(True)
        self.btn_save_generate.clicked.connect(self._save_and_generate)
        if not service.libreoffice_available:
            self.btn_save_generate.setText("📝 Uložit & vyrobit XLSX (PDF chybí soffice)")
            self.btn_save_generate.setToolTip(
                "LibreOffice není v PATH — PDF se nevygeneruje. "
                "Nainstaluj přes brew install --cask libreoffice nebo z libreoffice.org."
            )

        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_save_only)
        btn_row.addWidget(self.btn_save_generate)
        outer.addLayout(btn_row)

        self._refresh_summary()

    # ── helpers ─────────────────────────────────────────────────────────

    def _refresh_summary(self) -> None:
        # Inject current spin values into review.criteria, then read-back
        # via Review property accessors for consistent computation.
        for cs, spin in zip(self.review.criteria, self.score_spinboxes):
            cs.score = float(spin.value())
        self.review.assignment_fulfilled = self.cb_fulfilled.currentData()

        pts = self.review.total_weighted_points
        max_pts = self.review.max_points
        pct = self.review.percentage
        grade = self.review.suggested_grade

        grade_color = {
            "A": "#2e7d32", "B": "#43a047", "C": "#fb8c00",
            "D": "#f57c00", "E": "#e65100", "F": "#c62828", "FX": "#c62828",
        }.get(grade, "#666")

        self.lbl_summary.setText(
            f"<b>Celkový součet vážených bodů:</b> {pts:.2f} / {max_pts:g} &nbsp;·&nbsp; "
            f"<b>Procentuální úspěšnost:</b> {pct:.1f} % &nbsp;·&nbsp; "
            f"<b>Navržená známka:</b> "
            f"<span style='font-size:16px;background-color:{grade_color};color:white;"
            f"padding:2px 10px;border-radius:8px;font-weight:bold;'>{grade}</span>"
        )

    def _collect_into_review(self) -> None:
        """Sebere data z formuláře do ``self.review``."""
        self.review.assignment_fulfilled = self.cb_fulfilled.currentData()
        for cs, spin in zip(self.review.criteria, self.score_spinboxes):
            cs.score = float(spin.value())
        if self.cb_plag_verdict is not None:
            self.review.plagiarism_verdict = self.cb_plag_verdict.currentData()
            self.review.plagiarism_justification = self.ed_plag_just.toPlainText().strip()
        else:
            self.review.plagiarism_verdict = ""
            self.review.plagiarism_justification = ""
        self.review.overall_comment = self.ed_overall.toPlainText().strip()
        self.review.place_date = self.ed_place_date.text().strip()

    def _save_only(self) -> None:
        self._collect_into_review()
        try:
            self.service.upsert_review(
                self.thesis_id, self.review, opposing=self.opposing
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Uložení selhalo", str(exc))
            return
        self.saved = True
        QMessageBox.information(
            self,
            "Uloženo",
            "✓ Data posudku uložena. XLSX/PDF se nevygenerovaly — "
            "můžeš dokončit kdykoli později (z detailu práce).",
        )
        self.accept()

    def _save_and_generate(self) -> None:
        self._collect_into_review()
        try:
            self.service.upsert_review(
                self.thesis_id, self.review, opposing=self.opposing
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Uložení dat selhalo", str(exc))
            return

        try:
            xlsx, pdf = self.service.generate_review_files(
                self.thesis_id, self.review, opposing=self.opposing,
                also_pdf=True,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self,
                "Generování selhalo",
                f"Data byla uložena, ale generování XLSX/PDF skončilo chybou:\n{exc}",
            )
            self.saved = True
            self.accept()
            return

        self.saved = True
        self.generated_xlsx = xlsx
        self.generated_pdf = pdf

        # Sumární dialog s tlačítky pro otevření
        self._show_done_dialog(xlsx, pdf)
        self.accept()

    def _show_done_dialog(self, xlsx: Path, pdf: Path | None) -> None:
        body = (
            f"<p style='color:#2e7d32;font-weight:bold;'>✓ Posudek byl vyrobený.</p>"
            f"<p>"
            f"<b>XLSX:</b> <code>{escape(xlsx.name)}</code><br>"
        )
        if pdf is not None:
            body += f"<b>PDF:</b> <code>{escape(pdf.name)}</code>"
        else:
            body += (
                "<b>PDF:</b> <i>nevygenerováno</i> "
                "(LibreOffice nebyl detekován)"
            )
        body += (
            "</p>"
            "<p style='color:#666;'>Soubory jsou připojené jako přílohy k práci. "
            "Data posudku jsou uložená i v JSON — kdykoli můžeš znovu otevřít "
            "editor a upravit body / komentář, soubor se přegeneruje.</p>"
        )

        msg = QMessageBox(self.parent() or self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Posudek vyrobený")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(body)
        btn_open = msg.addButton(
            "📄 Otevřít XLSX", QMessageBox.ButtonRole.ActionRole
        )
        btn_open_pdf = None
        if pdf is not None:
            btn_open_pdf = msg.addButton(
                "📕 Otevřít PDF", QMessageBox.ButtonRole.ActionRole
            )
        msg.addButton(QMessageBox.StandardButton.Close)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_open:
            self._open_path(xlsx)
        elif btn_open_pdf is not None and clicked == btn_open_pdf:
            self._open_path(pdf)

    @staticmethod
    def _open_path(path: Path) -> None:
        import os
        import subprocess
        import sys

        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", str(path)], check=False)
        elif sys.platform == "win32":
            try:
                os.startfile(str(path))  # type: ignore[attr-defined]
            except OSError:
                pass
