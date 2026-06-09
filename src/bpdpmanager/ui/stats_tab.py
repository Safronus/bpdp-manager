"""Statistický přehled vedených prací, oponentur a studentů.

Read-only záložka (HTML render) — souhrnné statistiky napříč budoucími,
aktuálními i historickými pracemi. Počítá se z dat služby při každém
zobrazení / obnovení.
"""

from __future__ import annotations

from collections import Counter

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QPieSeries,
    QValueAxis,
)
from PySide6.QtCore import QMargins, Qt
from PySide6.QtGui import QColor, QPainter, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..config import thesis_documents_dir
from ..models.enums import (
    STATUSES_CURRENT,
    STATUSES_FUTURE,
    STATUSES_HISTORY,
    ThesisStatus,
)
from ..services import ThesisService


def _human_size(num_bytes: int) -> str:
    """Lidsky čitelná velikost (B/kB/MB/GB)."""
    size = float(num_bytes)
    for unit in ("B", "kB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"

_GRADE_COLORS = {
    "A": "#2e7d32", "B": "#43a047", "C": "#fb8c00",
    "D": "#f57c00", "E": "#e65100", "F": "#c62828", "FX": "#c62828",
}

# Kapacita a odměny (FAI UTB konvence — lze upravit).
_MAX_LED_THESES = 15          # max počet vedených prací
_FEE_THESIS = 3000            # Kč za vedenou (obhájenou) práci
_THESIS_FEE_CAP_PER_YEAR = 12  # max počet honorovaných vedení za rok
_FEE_OPPOSING = 600           # Kč za oponentský posudek


def _czk(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " Kč"


class StatsTab(QWidget):
    """Statistický přehled — dashboard: KPI banner + grid karet (grafy/tabulky),
    v rámci řádku sjednocené, různé řádky různě vysoké."""

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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        cv = QVBoxLayout(container)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(12)
        self._kpi_banner = QLabel()
        self._kpi_banner.setTextFormat(Qt.TextFormat.RichText)
        cv.addWidget(self._kpi_banner)
        # Řádky karet (každý řádek = QHBoxLayout s kartami stejné výšky).
        self._rows = QVBoxLayout()
        self._rows.setContentsMargins(0, 0, 0, 0)
        self._rows.setSpacing(12)
        cv.addLayout(self._rows)
        cv.addStretch(1)
        scroll.setWidget(container)
        outer.addWidget(scroll, stretch=1)

        self.refresh()

    # --- karty / grid --------------------------------------------------------

    def _card_frame(self) -> QFrame:
        """Prázdný rámeček karty (border, zaoblení, jemné pozadí)."""
        card = QFrame()
        card.setObjectName("statCard")
        card.setStyleSheet(
            "QFrame#statCard { "
            f"border:1px solid {self._border}; "
            "border-radius:10px; background: rgba(127,127,127,15); }"
        )
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return card

    def _make_card(self, html: str) -> QFrame | None:
        """Karta s HTML obsahem (tabulka / seznam)."""
        if not html or not html.strip():
            return None
        card = self._card_frame()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 8, 14, 12)
        lbl = QLabel(f"<div style='font-size:13px;'>{html}</div>")
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        lay.addWidget(lbl)
        lay.addStretch(1)
        return card

    def _chart_card(self, title: str, chart: QChart, center_text: str = "") -> QFrame:
        """Karta s grafem (nadpis + QChartView, volitelně text uprostřed donutu)."""
        card = self._card_frame()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 8, 14, 12)
        header = QLabel(
            f"<span style='color:#ffa726;font-weight:bold;font-size:14px;'>{title}</span>"
        )
        lay.addWidget(header)
        view = QChartView(chart)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setMinimumHeight(190)
        view.setStyleSheet("background:transparent; border:none;")
        if center_text:
            holder = QWidget()
            grid = QGridLayout(holder)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.addWidget(view, 0, 0)
            center = QLabel(center_text)
            center.setStyleSheet(
                f"font-size:30px;font-weight:bold;color:{self._fg};background:transparent;"
            )
            grid.addWidget(center, 0, 0, alignment=Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(holder, stretch=1)
        else:
            lay.addWidget(view, stretch=1)
        return card

    def _style_chart(self, chart: QChart, *, legend: bool = False) -> None:
        chart.setBackgroundVisible(False)
        chart.setMargins(QMargins(0, 0, 0, 0))
        chart.setBackgroundRoundness(0)
        chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        leg = chart.legend()
        leg.setVisible(legend)
        if legend:
            leg.setAlignment(Qt.AlignmentFlag.AlignBottom)
            leg.setLabelColor(QColor(self._fg))

    def _add_row(self, cards: list, stretches: list | None = None) -> None:
        """Přidá řádek karet (stejná výška, vyplní šířku)."""
        cards = [c for c in cards if c is not None]
        if not cards:
            return
        row = QWidget()
        hb = QHBoxLayout(row)
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(12)
        for i, card in enumerate(cards):
            hb.addWidget(card, stretches[i] if stretches else 1)
        self._rows.addWidget(row)

    def rendered_html(self) -> str:
        """Spojený text všech karet (nadpisy + HTML) — pro testy / kopírování."""
        parts = [self._kpi_banner.text()]
        for lbl in self.findChildren(QLabel):
            if lbl is not self._kpi_banner and lbl.text():
                parts.append(lbl.text())
        return "\n".join(parts)

    # --- výpočet -------------------------------------------------------------

    def refresh(self) -> None:
        # Barvy přizpůsob světlému/tmavému motivu.
        base = self.palette().color(QPalette.ColorRole.Base)
        luminance = (base.red() * 299 + base.green() * 587 + base.blue() * 114) / 1000
        dark = luminance < 128
        self._muted = "#b8b8b8" if dark else "#555555"
        self._border = "#666666" if dark else "#cccccc"
        self._fg = "#e6e6e6" if dark else "#333333"

        theses = self.service.list_theses()
        opposings = self.service.list_opposing_theses()
        students = self.service.list_students()
        rejected = self.service.list_rejected_students()

        # KPI banner přes celou šířku.
        self._kpi_banner.setText(
            f"<div style='font-size:13px;'>"
            f"{self._kpis(theses, opposings, students, rejected)}</div>"
        )

        # Vyprázdni staré řádky.
        while self._rows.count():
            item = self._rows.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        # Řádek 1 — grafy (pilot): vývoj po letech, podle stavu, úspěšnost.
        self._add_row([
            self._chart_year_trend(theses),
            self._chart_by_status(theses),
            self._chart_success(theses),
        ])
        # Řádek 2 — menší tabulkové karty.
        self._add_row([
            self._make_card(self._capacity(theses, rejected)),
            self._make_card(self._by_type(theses)),
            self._make_card(self._grades(theses)),
        ])
        # Řádek 3 — velké tabulky.
        self._add_row([
            self._make_card(self._by_year(theses)),
            self._make_card(self._by_obor(theses)),
        ], stretches=[3, 2])
        # Řádek 4 — oponentury / soubory / odměny.
        self._add_row([
            self._make_card(self._opposing_summary(opposings)),
            self._make_card(self._files(theses, opposings)),
            self._make_card(self._finance(theses, opposings)),
        ])
        # Řádek 5 — posudky.
        self._add_row([self._make_card(self._reviews(theses, opposings))])

    # --- grafy (pilot) -------------------------------------------------------

    def _chart_year_trend(self, theses) -> QFrame | None:
        if not theses:
            return None
        by_year: Counter[str] = Counter(t.academic_year or "(bez roku)" for t in theses)
        years = sorted(by_year)
        bset = QBarSet("")
        for y in years:
            bset.append(by_year[y])
        bset.setColor(QColor("#1565c0"))
        bset.setBorderColor(QColor("#1565c0"))
        bset.setLabelColor(QColor(self._fg))
        series = QBarSeries()
        series.append(bset)
        series.setLabelsVisible(True)
        chart = QChart()
        chart.addSeries(series)
        ax = QBarCategoryAxis()
        ax.append(years)
        ax.setLabelsColor(QColor(self._muted))
        ax.setGridLineVisible(False)
        chart.addAxis(ax, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(ax)
        ay = QValueAxis()
        ay.setLabelFormat("%d")
        ay.setLabelsColor(QColor(self._muted))
        ay.setGridLineColor(QColor(self._border))
        top = max(by_year.values())
        ay.setRange(0, top + 1)
        ay.setTickCount(min(top + 2, 6))
        chart.addAxis(ay, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(ay)
        self._style_chart(chart)
        return self._chart_card("Vývoj počtu vedených prací po letech", chart)

    def _chart_by_status(self, theses) -> QFrame | None:
        if not theses:
            return None
        counts: Counter = Counter(t.status for t in theses)
        series = QPieSeries()
        series.setHoleSize(0.45)
        for status in ThesisStatus:
            n = counts.get(status, 0)
            if not n:
                continue
            sl = series.append(f"{status.label}  {n}", n)
            sl.setColor(QColor(status.color))
            sl.setLabelVisible(False)
            sl.setBorderColor(QColor(self._border))
        chart = QChart()
        chart.addSeries(series)
        self._style_chart(chart, legend=True)
        return self._chart_card("Podle stavu", chart)

    def _chart_success(self, theses) -> QFrame | None:
        finished = [t for t in theses if t.status in STATUSES_HISTORY]
        if not finished:
            return None
        defended = sum(1 for t in finished if t.status == ThesisStatus.DEFENDED)
        rest = len(finished) - defended
        pct = defended / len(finished) * 100.0
        series = QPieSeries()
        series.setHoleSize(0.62)
        a = series.append("Obhájeno", defended)
        a.setColor(QColor("#2e7d32"))
        a.setLabelVisible(False)
        a.setBorderColor(QColor(self._border))
        if rest:
            b = series.append("Neúspěch / nedokončeno", rest)
            b.setColor(QColor("#c62828"))
            b.setLabelVisible(False)
            b.setBorderColor(QColor(self._border))
        chart = QChart()
        chart.addSeries(series)
        self._style_chart(chart, legend=True)
        return self._chart_card("Úspěšnost obhajob", chart, center_text=f"{pct:.0f}%")

    # --- sekce ---------------------------------------------------------------

    def _bar(self, label: str, count: int, total: int, color: str) -> str:
        """Jeden řádek s vodorovným pruhem (podíl z ``total``)."""
        pct = (count / total * 100.0) if total else 0.0
        width = max(2, round(pct)) if count else 0
        return (
            "<tr>"
            f"<td style='padding:2px 10px 2px 0;white-space:nowrap;'>{label}</td>"
            "<td style='width:100%;padding:2px 0;'>"
            f"<div style='background:{color};height:14px;width:{width}%;"
            "border-radius:3px;display:inline-block;min-width:2px;'></div></td>"
            f"<td style='padding:2px 0 2px 10px;white-space:nowrap;color:{self._muted};'>"
            f"<b>{count}</b> ({pct:.0f}%)</td>"
            "</tr>"
        )

    @staticmethod
    def _h(title: str) -> str:
        return f'<h3 style="color:#ffa726;margin:16px 0 6px 0;">{title}</h3>'

    def _kpis(self, theses, opposings, students, rejected) -> str:
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
            ("Odmítnutí", len(rejected), "#b71c1c"),
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

    def _capacity(self, theses, rejected) -> str:
        active = sum(1 for t in theses if t.status in STATUSES_CURRENT)
        color = "#2e7d32" if active < _MAX_LED_THESES else "#c62828"
        out = (
            self._h("Kapacita vedení")
            + f"<p>Aktuálně vedených prací (V řešení): "
            f"<b style='color:{color};'>{active}</b> z max. {_MAX_LED_THESES} "
            f"(volných {max(0, _MAX_LED_THESES - active)}).</p>"
        )
        if rejected:
            by_year: Counter[str] = Counter(r.academic_year or "(bez roku)" for r in rejected)
            items = " · ".join(
                f"{y}: {n}" for y, n in sorted(by_year.items(), reverse=True)
            )
            out += (
                f"<p>Odmítnutí zájemci: <b>{len(rejected)}</b> "
                f"<span style='color:{self._muted};'>({items})</span></p>"
            )
        return out

    def _led_trend(self, theses) -> str:
        if not theses:
            return ""
        by_year: Counter[str] = Counter(t.academic_year or "(bez roku)" for t in theses)
        years = sorted(by_year)  # chronologicky
        peak = max(by_year.values())
        rows = ""
        for y in years:
            rows += self._bar(y, by_year[y], peak, "#1565c0")
        return self._h("Vývoj počtu vedených prací po letech") + (
            f"<table style='width:100%;'>{rows}</table>"
        )

    def _finance(self, theses, opposings) -> str:
        years: dict[str, dict] = {}
        for t in theses:
            y = t.academic_year or "(bez roku)"
            d = years.setdefault(y, {"def": 0, "opp": 0})
            if t.status == ThesisStatus.DEFENDED:
                d["def"] += 1
        for op in opposings:
            y = op.academic_year or "(bez roku)"
            years.setdefault(y, {"def": 0, "opp": 0})["opp"] += 1
        if not years:
            return ""

        header = (
            "<tr style='color:" + self._muted + ";text-align:left;'>"
            "<th style='padding:2px 14px 2px 0;'>Rok</th>"
            "<th style='padding:2px 14px 2px 0;'>Obhájené</th>"
            "<th style='padding:2px 14px 2px 0;'>Odměna vedení</th>"
            "<th style='padding:2px 14px 2px 0;'>Oponentury</th>"
            "<th style='padding:2px 14px 2px 0;'>Odměna oponentur</th>"
            "<th style='padding:2px 0;'>Celkem</th></tr>"
        )
        rows = ""
        tot_sup = tot_opp = 0
        for y in sorted(years, reverse=True):
            d = years[y]
            sup_fee = min(d["def"], _THESIS_FEE_CAP_PER_YEAR) * _FEE_THESIS
            opp_fee = d["opp"] * _FEE_OPPOSING
            tot_sup += sup_fee
            tot_opp += opp_fee
            capped = " ⚠" if d["def"] > _THESIS_FEE_CAP_PER_YEAR else ""
            rows += (
                f"<tr><td style='padding:2px 14px 2px 0;'><b>{y}</b></td>"
                f"<td style='padding:2px 14px 2px 0;'>{d['def']}{capped}</td>"
                f"<td style='padding:2px 14px 2px 0;'>{_czk(sup_fee)}</td>"
                f"<td style='padding:2px 14px 2px 0;'>{d['opp']}</td>"
                f"<td style='padding:2px 14px 2px 0;'>{_czk(opp_fee)}</td>"
                f"<td style='padding:2px 0;'><b>{_czk(sup_fee + opp_fee)}</b></td></tr>"
            )
        rows += (
            "<tr style='border-top:1px solid " + self._border + ";'>"
            "<td style='padding:4px 14px 2px 0;'><b>Celkem</b></td>"
            f"<td></td><td style='padding:4px 14px 2px 0;'><b>{_czk(tot_sup)}</b></td>"
            f"<td></td><td style='padding:4px 14px 2px 0;'><b>{_czk(tot_opp)}</b></td>"
            f"<td style='padding:4px 0;'><b>{_czk(tot_sup + tot_opp)}</b></td></tr>"
        )
        return self._h("Odměny (orientačně)") + (
            f"<p style='color:{self._muted};font-size:11px;'>Vedení {_czk(_FEE_THESIS)}/práci "
            f"(jen <b>obhájené</b>, max {_THESIS_FEE_CAP_PER_YEAR}/rok — symbol ⚠ "
            f"značí překročení stropu), oponentský posudek {_czk(_FEE_OPPOSING)}.</p>"
            f"<table>{header}{rows}</table>"
        )

    def _by_status(self, theses) -> str:
        total = len(theses)
        if not total:
            return ""
        counts = Counter(t.status for t in theses)
        rows = ""
        for st in ThesisStatus:
            n = counts.get(st, 0)
            if n:
                rows += self._bar(st.label, n, total, st.color)
        return self._h("Podle stavu") + f"<table style='width:100%;'>{rows}</table>"

    def _by_type(self, theses) -> str:
        total = len(theses)
        if not total:
            return ""
        counts = Counter(t.type.value for t in theses)
        rows = (
            self._bar("Bakalářské (BP)", counts.get("BP", 0), total, "#1565c0")
            + self._bar("Diplomové (DP)", counts.get("DP", 0), total, "#6a1b9a")
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
            "<tr style='color:" + self._muted + ";text-align:left;'>"
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
            rows += self._bar(obor, n, total, "#3949ab")
        return self._h("Podle oboru") + f"<table style='width:100%;'>{rows}</table>"

    def _defense_success(self, theses) -> str:
        defended = sum(1 for t in theses if t.status == ThesisStatus.DEFENDED)
        failed = sum(1 for t in theses if t.status == ThesisStatus.FAILED)
        cancelled = sum(1 for t in theses if t.status == ThesisStatus.CANCELLED)
        finished = defended + failed + cancelled
        if not finished:
            return ""
        rate = defended / finished * 100.0
        rows = (
            self._bar("Obhájeno", defended, finished, "#2e7d32")
            + self._bar("Neobhájeno", failed, finished, "#c62828")
            + self._bar("Nedokončeno", cancelled, finished, "#9e9e9e")
        )
        retakes = sum(1 for t in theses if t.related_thesis_id) // 2
        retake_line = (
            f"<p>🔁 Opravné pokusy (repetenti): <b>{retakes}</b></p>" if retakes else ""
        )
        return (
            self._h("Úspěšnost obhajob (z dokončených)")
            + f"<p>Úspěšnost: <b style='color:#2e7d32;'>{rate:.0f}%</b> "
            f"({defended} z {finished})</p>"
            f"<table style='width:100%;'>{rows}</table>"
            f"{retake_line}"
        )

    def _grade_table(self, counts: Counter) -> str:
        """Tabulka rozpadu známek (A–FX) z čítače."""
        total = sum(counts.values())
        if not total:
            return ""
        rows = ""
        for g in ["A", "B", "C", "D", "E", "F", "FX"]:
            n = counts.get(g, 0)
            if n:
                rows += self._bar(g, n, total, _GRADE_COLORS.get(g, self._muted))
        return f"<table style='width:100%;'>{rows}</table>"

    def _grades(self, theses) -> str:
        sup: Counter[str] = Counter()
        opp: Counter[str] = Counter()
        for t in theses:
            if t.status != ThesisStatus.DEFENDED:
                continue
            gs = (t.grade_supervisor or "").strip().upper()
            if gs:
                sup[gs] += 1
            go = (t.grade_opponent or "").strip().upper()
            if go:
                opp[go] += 1
        if not sup and not opp:
            return ""
        out = self._h("Známky obhájených vedených prací")
        if sup:
            out += (
                "<p style='margin:6px 0 2px 0;'><b>Navržené vedoucím</b></p>"
                + self._grade_table(sup)
            )
        if opp:
            out += (
                "<p style='margin:8px 0 2px 0;'><b>Navržené oponentem</b></p>"
                + self._grade_table(opp)
            )
        return out

    def _opposing_summary(self, opposings) -> str:
        """Souhrn oponentur — počet, typ, rok, mnou navržené známky."""
        if not opposings:
            return ""
        total = len(opposings)
        by_type: Counter[str] = Counter(o.type.value for o in opposings)
        by_year: Counter[str] = Counter(
            o.academic_year or "(bez roku)" for o in opposings
        )
        grades: Counter[str] = Counter()
        for o in opposings:
            g = (o.grade_opponent or "").strip().upper()
            if g:
                grades[g] += 1

        type_rows = (
            self._bar("Bakalářské (BP)", by_type.get("BP", 0), total, "#1565c0")
            + self._bar("Diplomové (DP)", by_type.get("DP", 0), total, "#6a1b9a")
        )
        year_rows = "".join(
            f"<tr><td style='padding:2px 14px 2px 0;'><b>{y}</b></td>"
            f"<td style='padding:2px 0;'>{by_year[y]}</td></tr>"
            for y in sorted(by_year, reverse=True)
        )
        out = (
            self._h("Oponentury")
            + f"<p>Celkem oponentských posudků: <b>{total}</b></p>"
            + f"<table style='width:100%;'>{type_rows}</table>"
            + f"<table style='margin-top:6px;'>{year_rows}</table>"
        )
        if grades:
            out += (
                "<p style='margin:8px 0 2px 0;'><b>Mnou navržené známky "
                "(oponent)</b></p>" + self._grade_table(grades)
            )
        return out

    def _size_bar(self, label: str, size_bytes: int, total_bytes: int,
                  color: str) -> str:
        """Pruh úměrný velikosti; vpravo lidsky čitelná velikost."""
        pct = (size_bytes / total_bytes * 100.0) if total_bytes else 0.0
        width = max(2, round(pct)) if size_bytes else 0
        return (
            "<tr>"
            f"<td style='padding:2px 10px 2px 0;white-space:nowrap;'>{label}</td>"
            "<td style='width:100%;padding:2px 0;'>"
            f"<div style='background:{color};height:14px;width:{width}%;"
            "border-radius:3px;display:inline-block;min-width:2px;'></div></td>"
            f"<td style='padding:2px 0 2px 10px;white-space:nowrap;"
            f"color:{self._muted};'>{_human_size(size_bytes)}</td>"
            "</tr>"
        )

    def _files(self, theses, opposings) -> str:
        """Počty a velikost příloh — celkem, podle druhu dokumentu a podle prací."""
        by_kind: dict = {}                 # kind -> [count, bytes]
        per_work: list = []                # (label, count, bytes)
        total_count = 0
        total_bytes = 0

        def scan(atts, docs_id: str, label: str) -> None:
            nonlocal total_count, total_bytes
            docs_dir = thesis_documents_dir(docs_id)
            c = 0
            b = 0
            for att in atts:
                if not att.is_file:
                    continue
                p = docs_dir / att.url_or_path
                try:
                    if not p.is_file():
                        continue
                    size = p.stat().st_size
                except OSError:
                    continue
                c += 1
                b += size
                slot = by_kind.setdefault(att.kind, [0, 0])
                slot[0] += 1
                slot[1] += size
            if c:
                per_work.append((label, c, b))
                total_count += c
                total_bytes += b

        for t in theses:
            student = self.service.get_student(t.student_id) if t.student_id else None
            name = student.full_name if student else "(neznámý student)"
            scan(t.attachments, t.id,
                 f"{name} — {t.title_cs or '(bez názvu)'} ({t.type.value})")
        for o in opposings:
            name = f"{o.student_last_name} {o.student_first_name}".strip() or "(student)"
            scan(o.attachments, f"opposing-{o.id}",
                 f"{name} — {o.title_cs or '(bez názvu)'} ({o.type.value}, oponentura)")

        if not total_count:
            return ""

        denom = total_bytes or 1
        kind_rows = "".join(
            self._size_bar(f"{kind.label}  ({c}×)", b, denom, "#3949ab")
            for kind, (c, b) in sorted(
                by_kind.items(), key=lambda kv: kv[1][1], reverse=True
            )
        )
        top = sorted(per_work, key=lambda w: w[2], reverse=True)[:10]
        work_rows = "".join(
            self._size_bar(f"{lbl}  ({c}×)", b, denom, "#00897b")
            for lbl, c, b in top
        )
        more = (
            f"<p style='color:{self._muted};font-size:11px;'>"
            f"(zobrazeno 10 největších z {len(per_work)} prací se soubory)</p>"
            if len(per_work) > 10 else ""
        )

        return (
            self._h("Soubory (přílohy)")
            + f"<p>Celkem <b>{total_count}</b> souborů · "
            f"<b>{_human_size(total_bytes)}</b> "
            f"napříč <b>{len(per_work)}</b> pracemi "
            f"<span style='color:{self._muted};'>(včetně starších verzí)</span>.</p>"
            + "<p style='margin:6px 0 2px 0;'><b>Podle druhu dokumentu</b></p>"
            + f"<table style='width:100%;'>{kind_rows}</table>"
            + "<p style='margin:8px 0 2px 0;'><b>Největší práce</b></p>"
            + f"<table style='width:100%;'>{work_rows}</table>"
            + more
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
