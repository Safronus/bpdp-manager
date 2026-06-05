"""Statistický přehled vedených prací, oponentur a studentů.

Read-only záložka (HTML render) — souhrnné statistiky napříč budoucími,
aktuálními i historickými pracemi. Počítá se z dat služby při každém
zobrazení / obnovení.
"""

from __future__ import annotations

from collections import Counter

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from ..models.enums import (
    STATUSES_CURRENT,
    STATUSES_FUTURE,
    STATUSES_HISTORY,
    ThesisStatus,
)
from ..services import ThesisService

_GRADE_COLORS = {
    "A": "#2e7d32", "B": "#43a047", "C": "#fb8c00",
    "D": "#f57c00", "E": "#e65100", "F": "#c62828", "FX": "#c62828",
}


def _bar(label: str, count: int, total: int, color: str) -> str:
    """Jeden řádek s vodorovným pruhem (podíl z ``total``)."""
    pct = (count / total * 100.0) if total else 0.0
    width = max(2, round(pct)) if count else 0
    return (
        "<tr>"
        f"<td style='padding:2px 10px 2px 0;white-space:nowrap;'>{label}</td>"
        "<td style='width:100%;padding:2px 0;'>"
        f"<div style='background:{color};height:14px;width:{width}%;"
        "border-radius:3px;display:inline-block;min-width:2px;'></div></td>"
        f"<td style='padding:2px 0 2px 10px;white-space:nowrap;color:#444;'>"
        f"<b>{count}</b> ({pct:.0f}%)</td>"
        "</tr>"
    )


class StatsTab(QWidget):
    """Statistický přehled — KPI karty + rozpady podle stavu, typu, roku, oboru."""

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel("📊 Statistiky")
        title.setStyleSheet("font-size:16px;font-weight:bold;")
        head.addWidget(title)
        head.addStretch()
        btn_refresh = QPushButton("🔄 Přepočítat")
        btn_refresh.clicked.connect(self.refresh)
        head.addWidget(btn_refresh)
        outer.addLayout(head)

        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(False)
        outer.addWidget(self.view, stretch=1)

        self.refresh()

    # --- výpočet -------------------------------------------------------------

    def refresh(self) -> None:
        theses = self.service.list_theses()
        opposings = self.service.list_opposing_theses()
        students = self.service.list_students()

        parts: list[str] = ["<html><body style='font-size:13px;'>"]
        parts.append(self._kpis(theses, opposings, students))
        parts.append(self._by_status(theses))
        parts.append(self._by_type(theses))
        parts.append(self._by_year(theses))
        parts.append(self._by_obor(theses))
        parts.append(self._defense_success(theses))
        parts.append(self._grades(theses))
        parts.append(self._reviews(theses, opposings))
        parts.append("</body></html>")
        self.view.setHtml("".join(parts))

    # --- sekce ---------------------------------------------------------------

    @staticmethod
    def _h(title: str) -> str:
        return f'<h3 style="color:#ffa726;margin:16px 0 6px 0;">{title}</h3>'

    def _kpis(self, theses, opposings, students) -> str:
        cur = sum(1 for t in theses if t.status in STATUSES_CURRENT)
        fut = sum(1 for t in theses if t.status in STATUSES_FUTURE)
        hist = sum(1 for t in theses if t.status in STATUSES_HISTORY)
        cards = [
            ("Vedené práce", len(theses), "#1565c0"),
            ("V řešení", cur, "#00897b"),
            ("Budoucí", fut, "#7cb342"),
            ("Historie", hist, "#8e24aa"),
            ("Oponentury", len(opposings), "#5e35b1"),
            ("Studenti", len(students), "#546e7a"),
        ]
        cells = ""
        for label, n, color in cards:
            cells += (
                "<td style='padding:6px;'>"
                f"<div style='background:{color};color:white;border-radius:8px;"
                "padding:10px 14px;text-align:center;min-width:90px;'>"
                f"<div style='font-size:22px;font-weight:bold;'>{n}</div>"
                f"<div style='font-size:11px;opacity:0.9;'>{label}</div></div></td>"
            )
        return self._h("Souhrn") + f"<table><tr>{cells}</tr></table>"

    def _by_status(self, theses) -> str:
        total = len(theses)
        if not total:
            return ""
        counts = Counter(t.status for t in theses)
        rows = ""
        for st in ThesisStatus:
            n = counts.get(st, 0)
            if n:
                rows += _bar(st.label, n, total, st.color)
        return self._h("Podle stavu") + f"<table style='width:100%;'>{rows}</table>"

    def _by_type(self, theses) -> str:
        total = len(theses)
        if not total:
            return ""
        counts = Counter(t.type.value for t in theses)
        rows = (
            _bar("Bakalářské (BP)", counts.get("BP", 0), total, "#1565c0")
            + _bar("Diplomové (DP)", counts.get("DP", 0), total, "#6a1b9a")
        )
        return self._h("Bakalářské vs diplomové") + f"<table style='width:100%;'>{rows}</table>"

    def _by_year(self, theses) -> str:
        if not theses:
            return ""
        years: dict[str, dict] = {}
        for t in theses:
            y = t.academic_year or "(bez roku)"
            d = years.setdefault(y, {"n": 0, "def": 0, "prog": 0, "canc": 0, "bp": 0, "dp": 0})
            d["n"] += 1
            d["bp" if t.type.value == "BP" else "dp"] += 1
            if t.status == ThesisStatus.DEFENDED:
                d["def"] += 1
            elif t.status == ThesisStatus.IN_PROGRESS:
                d["prog"] += 1
            elif t.status == ThesisStatus.CANCELLED:
                d["canc"] += 1
        header = (
            "<tr style='color:#666;text-align:left;'>"
            "<th style='padding:2px 14px 2px 0;'>Rok</th>"
            "<th style='padding:2px 14px 2px 0;'>Celkem</th>"
            "<th style='padding:2px 14px 2px 0;'>BP</th>"
            "<th style='padding:2px 14px 2px 0;'>DP</th>"
            "<th style='padding:2px 14px 2px 0;'>V řešení</th>"
            "<th style='padding:2px 14px 2px 0;'>Obhájeno</th>"
            "<th style='padding:2px 0;'>Nedokončeno</th></tr>"
        )
        rows = ""
        for y in sorted(years, reverse=True):
            d = years[y]
            rows += (
                f"<tr><td style='padding:2px 14px 2px 0;'><b>{y}</b></td>"
                f"<td style='padding:2px 14px 2px 0;'>{d['n']}</td>"
                f"<td style='padding:2px 14px 2px 0;'>{d['bp']}</td>"
                f"<td style='padding:2px 14px 2px 0;'>{d['dp']}</td>"
                f"<td style='padding:2px 14px 2px 0;'>{d['prog']}</td>"
                f"<td style='padding:2px 14px 2px 0;color:#2e7d32;'>{d['def']}</td>"
                f"<td style='padding:2px 0;color:#c62828;'>{d['canc']}</td></tr>"
            )
        return self._h("Podle akademického roku") + f"<table>{header}{rows}</table>"

    def _by_obor(self, theses) -> str:
        if not theses:
            return ""
        counts: Counter[str] = Counter()
        for t in theses:
            student = self.service.get_student(t.student_id) if t.student_id else None
            obor = (student.obor if student else "") or "(bez oboru)"
            counts[obor] += 1
        total = len(theses)
        rows = ""
        for obor, n in counts.most_common():
            rows += _bar(obor, n, total, "#3949ab")
        return self._h("Podle oboru") + f"<table style='width:100%;'>{rows}</table>"

    def _defense_success(self, theses) -> str:
        defended = sum(1 for t in theses if t.status == ThesisStatus.DEFENDED)
        cancelled = sum(1 for t in theses if t.status == ThesisStatus.CANCELLED)
        finished = defended + cancelled
        if not finished:
            return ""
        rate = defended / finished * 100.0
        rows = (
            _bar("Obhájeno", defended, finished, "#2e7d32")
            + _bar("Nedokončeno", cancelled, finished, "#c62828")
        )
        return (
            self._h("Úspěšnost obhajob (z dokončených)")
            + f"<p>Úspěšnost: <b style='color:#2e7d32;'>{rate:.0f}%</b> "
            f"({defended} z {finished})</p>"
            f"<table style='width:100%;'>{rows}</table>"
        )

    def _grades(self, theses) -> str:
        counts: Counter[str] = Counter()
        for t in theses:
            if t.status != ThesisStatus.DEFENDED:
                continue
            g = (t.grade_supervisor or "").strip().upper()
            if g:
                counts[g] += 1
        total = sum(counts.values())
        if not total:
            return ""
        rows = ""
        for g in ["A", "B", "C", "D", "E", "F", "FX"]:
            n = counts.get(g, 0)
            if n:
                rows += _bar(g, n, total, _GRADE_COLORS.get(g, "#666"))
        return (
            self._h("Známky obhájených (navržené vedoucím)")
            + f"<table style='width:100%;'>{rows}</table>"
        )

    def _reviews(self, theses, opposings) -> str:
        in_progress = [t for t in theses if t.status == ThesisStatus.IN_PROGRESS]
        sup_done = sum(1 for t in in_progress if t.supervisor_review_state == "done")
        sup_draft = sum(1 for t in in_progress if t.supervisor_review_state == "draft")
        sup_none = sum(1 for t in in_progress if t.supervisor_review_state == "none")
        sup_sent = sum(1 for t in theses if t.supervisor_review_sent_at)
        opp_done = sum(1 for o in opposings if o.opponent_review_state == "done")
        opp_none = sum(1 for o in opposings if o.opponent_review_state == "none")
        opp_sent = sum(1 for o in opposings if o.opponent_review_sent_at)
        return (
            self._h("Posudky")
            + "<p><b>Posudky vedoucího (práce V řešení):</b> "
            f"<span style='color:#2e7d32;'>hotových {sup_done}</span> · "
            f"<span style='color:#f9a825;'>rozpracovaných {sup_draft}</span> · "
            f"<span style='color:#c62828;'>chybí {sup_none}</span> · "
            f"📨 odesláno sekretářce {sup_sent}</p>"
            "<p><b>Oponentské posudky:</b> "
            f"<span style='color:#2e7d32;'>hotových {opp_done}</span> · "
            f"<span style='color:#c62828;'>chybí {opp_none}</span> · "
            f"📨 odesláno {opp_sent}</p>"
        )
