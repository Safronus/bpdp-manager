"""Souhrn výsledků SZZ jednoho studenta (z cache, volitelně aktualizace ze STAG).

Otevírá se kontextovou akcí / klikem na studenta v rozpisu komise (centrální
panel) nebo v „Můj harmonogram" (pravý panel). Primárně čte lokální cache
(``ThesisService.load_szz_results``); když student výsledky nemá, řekne to.
Tlačítko *Aktualizovat ze STAG* stáhne čerstvá data — vyžaduje přihlášení
(jinak nabídne otevřít přihlašovací okno).
"""

from __future__ import annotations

from html import escape

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr

_MUTED = "#9aa0a6"
_GRADE_COLORS = {"A": "#2e7d32", "B": "#7cb342", "C": "#f9a825",
                 "D": "#ef6c00", "E": "#e64a19", "F": "#c62828"}


def _grade(text: str, letter: str) -> str:
    if not text:
        return f"<span style='color:{_MUTED};'>—</span>"
    col = _GRADE_COLORS.get((letter or "")[:1].upper(), _MUTED)
    return f"<span style='color:{col};font-weight:bold;'>{escape(text)}</span>"


def student_szz_html(rec, os_cislo: str, jmeno: str) -> str:
    """HTML souhrn SZZ studenta; ``rec`` je SzzRecord nebo ``None`` (bez dat)."""
    head = (f"<h3 style='margin:2px 0 6px;'>{escape(jmeno or '?')} "
            f"<span style='color:{_MUTED};font-size:12px;'>{escape(os_cislo)}</span></h3>")
    if rec is None:
        return head + (f"<p style='color:{_MUTED};'>"
                       + escape(tr("Pro tohoto studenta zatím nejsou v cache žádné "
                                   "výsledky SZZ. Zkus Aktualizovat ze STAG.")) + "</p>")
    if getattr(rec, "unavailable", False):
        return head + ("<p style='color:#fb8c00;'>⏳ "
                       + escape(tr("Záznam zatím nedostupný — komise možná ještě "
                                   "neproběhla nebo k ní nemáš přístup.")) + "</p>")

    out = head
    ov = rec.overall
    if ov:
        prospel = (tr("Prospěl") if ov.prospel else
                   (tr("Neprospěl") if ov.prospel is False else tr("zatím bez výsledku")))
        pcol = "#2e7d32" if ov.prospel else ("#c62828" if ov.prospel is False else _MUTED)
        out += (f"<p style='margin:2px 0 8px;'>"
                f"<b style='color:{pcol};'>{escape(prospel)}</b> &nbsp;·&nbsp; "
                f"{escape(tr('celkový výsledek SZZ'))}: "
                f"{_grade(ov.vysledek_zkousek_text or ov.vysledek_zkousek, ov.vysledek_zkousek)}"
                + (f" &nbsp;·&nbsp; {escape(tr('z předmětů'))}: "
                   f"{_grade(ov.vysledek_predmety, ov.vysledek_predmety)}"
                   if ov.vysledek_predmety else "")
                + (f" &nbsp;·&nbsp; {escape(tr('komise'))} {escape(ov.komise)}"
                   if ov.komise else "")
                + (f" &nbsp;·&nbsp; {escape(ov.datum)} {escape(ov.cas or '')}"
                   if ov.datum else "")
                + "</p>")

    if rec.defense:
        d = rec.defense
        out += (f"<p style='margin:8px 0 2px;'><b>🎓 {escape(tr('Obhajoba práce'))}</b>: "
                f"{_grade(d.znamka_text or d.znamka, d.znamka)}"
                f" &nbsp;<span style='color:{_MUTED};'>"
                f"({escape(tr('vedoucí'))} {escape(d.znamka_vedouci or '—')}, "
                f"{escape(tr('oponent'))} {escape(d.znamka_oponent or '—')})</span></p>")
        if d.zkousejici:
            out += (f"<p style='margin:0 0 0 14px;color:{_MUTED};'>"
                    f"{escape(tr('zkoušející'))}: {escape(d.zkousejici)}</p>")
        if getattr(d, "prubeh", ""):
            out += (f"<p style='margin:0 0 0 14px;color:{_MUTED};font-size:11px;'>"
                    f"❓ {escape(d.prubeh)}</p>")

    if rec.subjects:
        out += (f"<p style='margin:8px 0 2px;'><b>📚 "
                f"{escape(tr('Předmětové zkoušky'))}</b> "
                f"<span style='color:{_MUTED};font-size:11px;'>"
                f"({escape(tr('❓ = průběh / otázky'))})</span></p>")
        out += "<table style='border-collapse:collapse;margin-left:8px;'>"
        for s in rec.subjects:
            out += (f"<tr><td style='padding:1px 10px 1px 0;white-space:nowrap;'>"
                    f"{escape(s.katedra)}/{escape(s.predmet)}</td>"
                    f"<td style='padding:1px 10px 1px 0;'>"
                    f"{_grade(s.znamka_text or s.znamka, s.znamka)}</td>"
                    f"<td style='padding:1px 0;color:{_MUTED};'>"
                    f"{escape(s.zkousejici or '—')}</td></tr>")
            if getattr(s, "prubeh", ""):
                out += (f"<tr><td colspan='3' style='padding:0 0 5px 0;"
                        f"color:{_MUTED};font-size:11px;'>"
                        f"❓ {escape(s.prubeh)}</td></tr>")
        out += "</table>"

    if getattr(rec, "fetched_at", ""):
        out += (f"<p style='margin:10px 0 0;color:{_MUTED};font-size:11px;'>"
                f"{escape(tr('staženo'))}: {escape(rec.fetched_at.replace('T', ' ')[:16])}</p>")
    return out


class SzzStudentDialog(QDialog):
    """Souhrn SZZ studenta (cache) + volitelná aktualizace ze STAG."""

    def __init__(self, os_cislo: str, jmeno: str, service,
                 on_update=None, on_open_login=None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.os_cislo = (os_cislo or "").strip().upper()
        self.jmeno = jmeno or ""
        self.service = service
        self._on_update = on_update           # callable(os_cislo, callback)
        self._on_open_login = on_open_login   # callable() — otevři přihlášení
        self._alive = True
        self.changed = False                  # cache změněna → volající přerenderuje
        self.setWindowTitle(tr("Souhrn SZZ — ") + (self.jmeno or self.os_cislo))
        self.resize(560, 520)

        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.lbl = QLabel("")
        self.lbl.setStyleSheet(f"color:{_MUTED};")
        bar.addWidget(self.lbl)
        bar.addStretch(1)
        if self._on_update is not None:
            self.btn_update = QPushButton("🔄 " + tr("Aktualizovat ze STAG"))
            self.btn_update.clicked.connect(self._update)
            bar.addWidget(self.btn_update)
        root.addLayout(bar)

        self.out = QTextBrowser()
        self.out.setOpenExternalLinks(False)
        root.addWidget(self.out, 1)
        self._render()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self._alive = False
        super().closeEvent(event)

    def _render(self) -> None:
        rec = self.service.load_szz_results().get(self.os_cislo)
        self.out.setHtml(student_szz_html(rec, self.os_cislo, self.jmeno))

    def _update(self) -> None:
        self.btn_update.setEnabled(False)
        self.lbl.setText("⏳ " + tr("Aktualizuji ze STAG…"))
        self._on_update(self.os_cislo, self._updated)

    def _updated(self, rec, error: str) -> None:
        if not self._alive:
            return
        self.btn_update.setEnabled(True)
        if error == "logged_out":
            self.lbl.setText("🔴 " + tr("Nepřihlášeno"))
            if self._on_open_login is not None:
                self.lbl.setText("")
                self.out.setHtml(
                    student_szz_html(
                        self.service.load_szz_results().get(self.os_cislo),
                        self.os_cislo, self.jmeno)
                    + "<p style='color:#c62828;'>⚠ "
                    + escape(tr("Pro aktualizaci se musíš přihlásit do portálu "
                                "(Státnice (admin)). Otevři přihlášení a pak zkus "
                                "Aktualizovat znovu.")) + "</p>")
                self._show_login_button()
            return
        if rec is not None and getattr(rec, "os_cislo", ""):
            self.service.upsert_szz_result(rec)
            self.changed = True
            self.lbl.setText("✅ " + tr("Aktualizováno"))
        elif error == "not_found":
            from ..models.szz_result import SzzRecord
            self.service.upsert_szz_result(
                SzzRecord(os_cislo=self.os_cislo, unavailable=True))
            self.changed = True
            self.lbl.setText("⏳ " + tr("Zatím nedostupné"))
        else:
            self.lbl.setText("⚠ " + tr("Nepodařilo se načíst"))
        self._render()

    def _show_login_button(self) -> None:
        if getattr(self, "_btn_login", None) is not None:
            return
        self._btn_login = QPushButton("🔐 " + tr("Přihlásit se ke STAG"))
        self._btn_login.clicked.connect(lambda: self._on_open_login())
        self.layout().insertWidget(1, self._btn_login)
