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

from PySide6.QtCore import Qt, QThread, Signal
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
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..models import Review
from ..models.enums import AttachmentKind
from ..services import ThesisService, spellcheck
from ._os_actions import open_path, reveal_in_file_manager
from .widgets.spell_text_edit import SpellCheckEdit

# Kostra („skeleton") volného hodnocení — tematické nadpisy, pod které autor
# píše. Liší se podle role (vedoucí má navíc přístup/samostatnost studenta)
# a jazyka šablony (CZ/EN). Vkládá se u NOVÉHO posudku, případně tlačítkem.
_SKELETON_HEADINGS: dict[tuple[str, str], list[str]] = {
    ("supervisor", "cs"): [
        "Aktuálnost, náročnost a relevance tématu:",
        "Přístup, samostatnost a spolupráce studenta:",
        "Formální stránka práce:",
        "Obsahová část a praktický výstup:",
        "Splnění bodů zadání:",
        "Doporučení k hodnocení:",
        "Dotazy a připomínky:",
    ],
    ("opponent", "cs"): [
        "Aktuálnost, náročnost a relevance tématu:",
        "Formální stránka práce:",
        "Obsahová část a praktický výstup:",
        "Splnění bodů zadání:",
        "Doporučení k hodnocení:",
        "Dotazy a připomínky:",
    ],
    ("supervisor", "en"): [
        "Relevance, difficulty and topicality of the theme:",
        "Student's approach, independence and cooperation:",
        "Formal quality of the thesis:",
        "Content and practical output:",
        "Fulfilment of the assignment:",
        "Grade recommendation:",
        "Questions and comments:",
    ],
    ("opponent", "en"): [
        "Relevance, difficulty and topicality of the theme:",
        "Formal quality of the thesis:",
        "Content and practical output:",
        "Fulfilment of the assignment:",
        "Grade recommendation:",
        "Questions and comments:",
    ],
}


def build_review_skeleton(role: str, language: str) -> str:
    """Vrátí kostru volného hodnocení (nadpisy + prázdné řádky) dle role/jazyka."""
    r = role if role in ("supervisor", "opponent") else "opponent"
    lang = "en" if language == "en" else "cs"
    headings = _SKELETON_HEADINGS[(r, lang)]
    # Mezi nadpisy jeden prázdný řádek pro psaní.
    return "\n\n".join(headings) + "\n"


class _GenerateWorker(QThread):
    """Generuje XLSX + PDF mimo hlavní vlákno, ať se UI (progress) nezasekne.

    LibreOffice převod do PDF je blokující subprocess — kdyby běžel v hlavním
    vlákně, progress bar by zamrznul. Worker jen volá službu a hlásí výsledek.
    """

    finished_ok = Signal(object, object)  # (xlsx_path, pdf_path|None)
    failed = Signal(str)

    def __init__(self, service, thesis_id, review, opposing, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._thesis_id = thesis_id
        self._review = review
        self._opposing = opposing

    def run(self) -> None:
        try:
            xlsx, pdf = self._service.generate_review_files(
                self._thesis_id, self._review, opposing=self._opposing, also_pdf=True
            )
            self.finished_ok.emit(xlsx, pdf)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _DictDownloadWorker(QThread):
    """Stáhne český slovník mimo hlavní vlákno (síť neblokuje UI)."""

    done = Signal(bool, str)  # (ok, error)

    def run(self) -> None:
        try:
            spellcheck.download_dictionary()
            self.done.emit(True, "")
        except Exception as exc:  # noqa: BLE001
            self.done.emit(False, str(exc))


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
        # Šířka pevná; výšku přizpůsobíme obsahu (viz _fit_height_to_content na
        # konci __init__) — co se vejde na obrazovku, ukáže se bez scrollování.
        self.setMinimumSize(900, 420)
        self.resize(960, 760)

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

        # ── Rychlé otevření podkladů: text práce + opačný posudek ─────────
        # U psaného posudku VEDOUCÍHO nabídneme posudek OPONENTA a naopak,
        # plus PDF/soubor s textem práce (pro nahlédnutí během psaní).
        quick = QHBoxLayout()
        text_path = self._attachment_path(AttachmentKind.THESIS_TEXT)
        btn_text = QPushButton(tr("📄 Otevřít text práce"))
        btn_text.setToolTip(tr("Otevře nahraný text práce (PDF), je-li k dispozici."))
        btn_text.setEnabled(text_path is not None and text_path.exists())
        if btn_text.isEnabled():
            btn_text.clicked.connect(lambda _c=False, p=text_path: open_path(p))
        quick.addWidget(btn_text)

        other_is_opponent = review.role == "supervisor"
        other_kind = (
            AttachmentKind.OPPONENT_REVIEW if other_is_opponent
            else AttachmentKind.SUPERVISOR_REVIEW
        )
        other_path = self._attachment_path(other_kind)
        btn_other = QPushButton(
            "📕 Otevřít posudek oponenta" if other_is_opponent
            else "📘 Otevřít posudek vedoucího"
        )
        btn_other.setToolTip(tr("Otevře protější posudek (PDF/soubor), je-li k dispozici."))
        btn_other.setEnabled(other_path is not None and other_path.exists())
        if btn_other.isEnabled():
            btn_other.clicked.connect(lambda _c=False, p=other_path: open_path(p))
        quick.addWidget(btn_other)
        quick.addStretch()
        outer.addLayout(quick)

        # ── Scroll area s obsahem ──────────────────────────────────────
        scroll = self._scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)

        # ── Splnění bodů zadání ───────────────────────────────────────
        box_fulfill = QGroupBox(tr("Splnění všech bodů zadání"))
        form_f = QFormLayout(box_fulfill)
        self.cb_fulfilled = QComboBox()
        # Volby dle JAZYKA ŠABLONY — EN posudek nabízí jen anglické varianty,
        # CZ jen české (ne všechny 4 najednou).
        if review.language == "en":
            opts = ("fulfilled", "not fulfilled")
        else:
            opts = ("splnil(a)", "nesplnil(a)")
        for v in opts:
            self.cb_fulfilled.addItem(v, v)
        idx = self.cb_fulfilled.findData(review.assignment_fulfilled or opts[0])
        if idx < 0:
            idx = 0  # uložená hodnota v jiném jazyce → výchozí (kladná)
        self.cb_fulfilled.setCurrentIndex(idx)
        self.cb_fulfilled.currentTextChanged.connect(self._refresh_summary)
        form_f.addRow("Stav", self.cb_fulfilled)
        content_layout.addWidget(box_fulfill)

        # ── Kritéria ──────────────────────────────────────────────────
        box_crit = QGroupBox(tr("Kritéria hodnocení (skóre 0–5)"))
        crit_layout = QVBoxLayout(box_crit)
        crit_layout.setSpacing(2)

        # Header
        hdr_row = QHBoxLayout()
        hdr_row.addWidget(QLabel(tr("<b>Kritérium</b>")), stretch=1)
        hdr_row.addWidget(QLabel(tr("<b>Váha</b>")))
        hdr_row.addWidget(QLabel(tr("<b>Body</b>")))
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
            box_plag = QGroupBox(tr("Výsledek kontroly plagiátorství (jen pro vedoucího)"))
            form_p = QFormLayout(box_plag)
            # Pole zarovnaná doleva a roztažená na šířku dialogu (zejména
            # „Zdůvodnění" — víceřádkový text potřebuje celou šířku).
            form_p.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
            form_p.setFormAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
            form_p.setFieldGrowthPolicy(
                QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
            )
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
            form_p.addRow(tr("Verdikt"), self.cb_plag_verdict)

            self.ed_plag_just = SpellCheckEdit(review.plagiarism_justification)
            self.ed_plag_just.setMaximumHeight(80)
            self.ed_plag_just.setPlaceholderText(
                tr("Zdůvodnění (% shody, kontext, …)")
            )
            form_p.addRow(tr("Zdůvodnění"), self.ed_plag_just)
            content_layout.addWidget(box_plag)
        else:
            self.cb_plag_verdict = None  # type: ignore
            self.ed_plag_just = None  # type: ignore

        # ── Celkové hodnocení ─────────────────────────────────────────
        box_overall = QGroupBox(tr("Celkové hodnocení, připomínky a dotazy"))
        v_overall = QVBoxLayout(box_overall)
        skel_row = QHBoxLayout()
        skel_row.addStretch()
        btn_skeleton = QPushButton(tr("🦴 Vložit kostru posudku"))
        btn_skeleton.setToolTip(
            tr("Vloží tematické nadpisy (kostru) pro slovní hodnocení podle role "
            "a jazyka šablony. Když už něco píšeš, vloží se za kurzor.")
        )
        btn_skeleton.clicked.connect(self._insert_skeleton)
        skel_row.addWidget(btn_skeleton)
        v_overall.addLayout(skel_row)
        self.ed_overall = SpellCheckEdit(review.overall_comment)
        self.ed_overall.setMinimumHeight(140)
        self.ed_overall.setPlaceholderText(
            tr("Slovní zhodnocení práce, dotazy k obhajobě…")
        )
        v_overall.addWidget(self.ed_overall)
        # Hláška, když kontrola pravopisu není k dispozici (chybí spylls/slovník).
        self._spell_hint: QLabel | None = None
        self._spell_dl_btn: QPushButton | None = None
        self._dict_worker: _DictDownloadWorker | None = None
        if not spellcheck.is_available():
            self._spell_hint = QLabel(
                "ⓘ Kontrola pravopisu je vypnutá — " + spellcheck.unavailable_reason()
            )
            self._spell_hint.setStyleSheet("color:#888;font-size:11px;")
            self._spell_hint.setWordWrap(True)
            v_overall.addWidget(self._spell_hint)
            # Když je spylls, ale chybí/nejde slovník → nabídni stažení.
            if spellcheck.can_download():
                self._spell_dl_btn = QPushButton(tr("⬇ Stáhnout český slovník"))
                self._spell_dl_btn.setToolTip(
                    tr("Stáhne český hunspell slovník (LibreOffice) do "
                    "~/.bpdpmanager/dictionaries/ a zapne kontrolu pravopisu.")
                )
                self._spell_dl_btn.clicked.connect(self._download_dictionary)
                v_overall.addWidget(self._spell_dl_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        content_layout.addWidget(box_overall)

        # ── Místo, datum ──────────────────────────────────────────────
        box_meta = QGroupBox(tr("Podpis"))
        form_m = QFormLayout(box_meta)
        self.ed_place_date = QLineEdit(review.place_date)
        self.ed_place_date.setPlaceholderText(tr("např. Zlín, 26. 5. 2026"))
        form_m.addRow(tr("Místo, datum"), self.ed_place_date)
        content_layout.addWidget(box_meta)

        # ── Tlačítka ──────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton(tr("Zrušit"))
        btn_cancel.clicked.connect(self.reject)
        self.btn_save_only = QPushButton(tr("💾 Uložit (jen data)"))
        self.btn_save_only.setToolTip(
            tr("Uloží strukturovaná data posudku. XLSX a PDF nevygeneruje — "
            "stačí třeba pro rozpracovaný posudek, který chceš dokončit později.")
        )
        self.btn_save_only.clicked.connect(self._save_only)

        self.btn_save_generate = QPushButton(tr("📝 Uložit & vyrobit XLSX + PDF"))
        bf = self.btn_save_generate.font()
        bf.setBold(True)
        self.btn_save_generate.setFont(bf)
        self.btn_save_generate.setDefault(True)
        self.btn_save_generate.clicked.connect(self._save_and_generate)
        if not service.libreoffice_available:
            self.btn_save_generate.setText(tr("📝 Uložit & vyrobit XLSX (PDF chybí soffice)"))
            self.btn_save_generate.setToolTip(
                tr("LibreOffice není v PATH — PDF se nevygeneruje. "
                "Nainstaluj přes brew install --cask libreoffice nebo z libreoffice.org.")
            )

        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_save_only)
        btn_row.addWidget(self.btn_save_generate)
        outer.addLayout(btn_row)

        self._refresh_summary()
        self._fit_height_to_content()

    def _fit_height_to_content(self) -> None:
        """Přizpůsobí výšku okna obsahu — vejde-li se, ukáže ho bez scrollování;
        jinak se zastropuje výškou obrazovky (a scroll zůstane)."""
        content = self._scroll.widget()
        if content is None:
            return
        # Výška „chromu" = vše mimo scroll oblast (hlavička, meta, tlačítka,
        # okraje) = sizeHint celého layoutu minus to, čím přispívá scroll.
        chrome = self.layout().sizeHint().height() - self._scroll.sizeHint().height()
        desired = chrome + content.sizeHint().height() + 4
        screen = self.screen()
        avail = screen.availableGeometry().height() if screen is not None else 1000
        height = min(desired, int(avail * 0.95))
        height = max(height, self.minimumHeight())
        self.resize(self.width(), height)

    # ── stažení slovníku ────────────────────────────────────────────────
    def _download_dictionary(self) -> None:
        if self._spell_dl_btn is None:
            return
        self._spell_dl_btn.setEnabled(False)
        self._spell_dl_btn.setText(tr("Stahuji slovník…"))
        if self._spell_hint is not None:
            self._spell_hint.setText(tr("ⓘ Stahuji český slovník z LibreOffice…"))
        self._dict_worker = _DictDownloadWorker()
        self._dict_worker.done.connect(self._on_dict_downloaded)
        self._dict_worker.start()

    def _on_dict_downloaded(self, ok: bool, error: str) -> None:
        if ok and spellcheck.is_available():
            if self._spell_hint is not None:
                self._spell_hint.setText(tr("✓ Slovník stažen — kontrola pravopisu zapnuta."))
            if self._spell_dl_btn is not None:
                self._spell_dl_btn.hide()
            # Zapni podtržení živě v obou editorech.
            for ed in (self.ed_overall, self.ed_plag_just):
                if ed is not None:
                    ed.recheck()
            return
        if self._spell_dl_btn is not None:
            self._spell_dl_btn.setEnabled(True)
            self._spell_dl_btn.setText(tr("⬇ Stáhnout český slovník"))
        if self._spell_hint is not None:
            self._spell_hint.setText(
                "ⓘ Kontrola pravopisu je vypnutá — " + spellcheck.unavailable_reason()
            )
        QMessageBox.warning(
            self, tr("Stažení slovníku"),
            "Slovník se nepodařilo stáhnout:\n" + (error or "neznámá chyba"),
        )

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

    def _insert_skeleton(self) -> None:
        """Vloží kostru posudku — do prázdného pole rovnou, jinak za kurzor."""
        skeleton = build_review_skeleton(self.review.role, self.review.language)
        if not self.ed_overall.toPlainText().strip():
            self.ed_overall.setPlainText(skeleton)
        else:
            self.ed_overall.textCursor().insertText(skeleton)
        self.ed_overall.setFocus()

    def _attachment_path(self, kind: AttachmentKind):
        """Absolutní cesta k aktuálnímu souboru dané přílohy (preferuje PDF)."""
        work = (
            self.service.get_opposing_thesis(self.thesis_id) if self.opposing
            else self.service.get_thesis(self.thesis_id)
        )
        if work is None:
            return None
        atts = [a for a in work.attachments if a.is_file and a.kind == kind]
        if not atts:
            return None
        # Preferuj current a PDF; jinak vezmi cokoliv dostupného.
        atts.sort(key=lambda a: (
            0 if a.is_current else 1,
            0 if a.url_or_path.lower().endswith(".pdf") else 1,
        ))
        att = atts[0]
        return (
            self.service.opposing_document_absolute_path(self.thesis_id, att)
            if self.opposing
            else self.service.document_absolute_path(self.thesis_id, att)
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
            QMessageBox.critical(self, tr("Uložení selhalo"), str(exc))
            return
        self.saved = True
        QMessageBox.information(
            self,
            tr("Uloženo"),
            tr("✓ Data posudku uložena. XLSX/PDF se nevygenerovaly — "
            "můžeš dokončit kdykoli později (z detailu práce)."),
        )
        self.accept()

    def _save_and_generate(self) -> None:
        self._collect_into_review()
        try:
            self.service.upsert_review(
                self.thesis_id, self.review, opposing=self.opposing
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, tr("Uložení dat selhalo"), str(exc))
            return

        # Generování XLSX + PDF běží ve vlákně, ať progress nezamrzne (PDF
        # převod je blokující). Ukážeme „busy" indikátor po dobu generování.
        progress = QProgressDialog(
            "Generuji posudek (vyplňuji XLSX a převádím do PDF)…",
            "", 0, 0, self,
        )
        progress.setWindowTitle(tr("Generování posudku"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)  # krátká operace — bez rušení
        progress.setAutoClose(False)
        progress.setAutoReset(False)

        result: dict[str, object] = {"xlsx": None, "pdf": None, "error": None}
        worker = _GenerateWorker(
            self.service, self.thesis_id, self.review, self.opposing, self
        )
        worker.finished_ok.connect(lambda x, p: result.update(xlsx=x, pdf=p))
        worker.failed.connect(lambda msg: result.update(error=msg))
        # KRITICKÉ: progress se zavírá až po DOBĚHNUTÍ vlákna přes ``close()``.
        # ``reset()`` při ``autoClose=False`` modální ``exec()`` neukončí —
        # dialog by visel, i když jsou soubory hotové. ``finished`` (QThread)
        # se emituje vždy po ``run()``, tedy i kdyby signály nahoře selhaly.
        worker.finished.connect(progress.close)
        worker.start()
        progress.exec()
        worker.wait()

        if result["error"] is not None:
            QMessageBox.critical(
                self,
                tr("Generování selhalo"),
                f"Data byla uložena, ale generování XLSX/PDF skončilo chybou:\n"
                f"{result['error']}",
            )
            self.saved = True
            self.accept()
            return

        self.saved = True
        self.generated_xlsx = result["xlsx"]
        self.generated_pdf = result["pdf"]

        # Sumární dialog s tlačítky pro otevření
        self._show_done_dialog(result["xlsx"], result["pdf"])
        self.accept()

    def _show_done_dialog(self, xlsx: Path, pdf: Path | None) -> None:
        """Dokončovací dialog s akcemi, které ho NEzavírají.

        Záměrně to není ``QMessageBox`` — u toho každé „action" tlačítko box
        zavře, takže po otevření XLSX už nešlo otevřít PDF. Vlastní ``QDialog``
        nechá uživatele otevřít XLSX, PDF i složku ve Finderu z jednoho okna;
        zavře se až tlačítkem „Zavřít".
        """
        body = (
            "<p style='color:#2e7d32;font-weight:bold;'>✓ Posudek byl vyrobený.</p>"
            "<p>"
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

        dlg = QDialog(self.parent() or self)
        dlg.setWindowTitle(tr("Posudek vyrobený"))
        dlg.setMinimumWidth(460)
        lay = QVBoxLayout(dlg)
        lbl = QLabel(body)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        btn_row = QHBoxLayout()
        btn_xlsx = QPushButton(tr("📄 Otevřít XLSX"))
        btn_xlsx.clicked.connect(lambda: open_path(xlsx))
        btn_row.addWidget(btn_xlsx)
        if pdf is not None:
            btn_pdf = QPushButton(tr("📕 Otevřít PDF"))
            btn_pdf.clicked.connect(lambda: open_path(pdf))
            btn_row.addWidget(btn_pdf)
        btn_reveal = QPushButton(tr("📂 Ukázat ve Finderu"))
        btn_reveal.clicked.connect(lambda: reveal_in_file_manager(pdf or xlsx))
        btn_row.addWidget(btn_reveal)
        btn_row.addStretch()
        btn_close = QPushButton(tr("Zavřít"))
        btn_close.setDefault(True)
        btn_close.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_close)
        lay.addLayout(btn_row)

        dlg.exec()
