"""Statistický přehled vedených prací, oponentur a studentů.

Read-only záložka (HTML render) — souhrnné statistiky napříč budoucími,
aktuálními i historickými pracemi. Počítá se z dat služby při každém
zobrazení / obnovení.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import ClassVar

from PySide6.QtCharts import (
    QAbstractBarSeries,
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QPieSeries,
    QValueAxis,
)
from PySide6.QtCore import QMargins, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
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
    GRADE_TINTS,
    STATUSES_CURRENT,
    STATUSES_FUTURE,
    STATUSES_HISTORY,
    StudyForm,
    ThesisStatus,
    obor_color,
)
from ..services import ThesisService
from ..services.default_data import discipline_from_app_code


def _human_size(num_bytes: int) -> str:
    """Lidsky čitelná velikost (B/kB/MB/GB)."""
    size = float(num_bytes)
    for unit in ("B", "kB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


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
        self._kpi_banner = QLabel()   # nadpis „Souhrn" (drží text pro testy)
        self._kpi_banner.setTextFormat(Qt.TextFormat.RichText)
        self._kpi_banner.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        cv.addWidget(self._kpi_banner, alignment=Qt.AlignmentFlag.AlignHCenter)
        # KPI „pilulky" jako skutečné widgety — zaoblené rohy přes stylesheet
        # (HTML <div border-radius> Qt rich-text neumí; badge známek je kreslený).
        self._kpi_cards = QWidget()
        self._kpi_cards_lay = QHBoxLayout(self._kpi_cards)
        self._kpi_cards_lay.setContentsMargins(0, 0, 0, 0)
        self._kpi_cards_lay.setSpacing(10)
        cv.addWidget(self._kpi_cards, alignment=Qt.AlignmentFlag.AlignHCenter)
        # Stav interaktivních karet (přepínače).
        self._trend_mode = "led"   # "led" = vedené, "opp" = oponované
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

    def _make_card(self, html: str, *, center: bool = False) -> QFrame | None:
        """Karta s HTML obsahem (tabulka / seznam). ``center`` = obsah na střed."""
        if not html or not html.strip():
            return None
        card = self._card_frame()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 8, 14, 12)
        align = "center" if center else "left"
        lbl = QLabel(f"<div style='font-size:13px;text-align:{align};'>{html}</div>")
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setAlignment(
            Qt.AlignmentFlag.AlignCenter if center else Qt.AlignmentFlag.AlignTop
        )
        lay.addWidget(lbl, stretch=1 if center else 0)
        if not center:
            lay.addStretch(1)
        return card

    def _chart_view(self, chart: QChart | None = None, min_h: int = 150) -> QChartView:
        view = QChartView(chart) if chart is not None else QChartView()
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setMinimumHeight(min_h)
        view.setMaximumHeight(220)
        view.setStyleSheet("background:transparent; border:none;")
        return view

    def _apply_axis_font(self, *axes) -> None:
        """Malý font popisků os, ať grafy nejsou „gigantické"."""
        f = QFont()
        f.setPointSize(8)
        for ax in axes:
            ax.setLabelsFont(f)
            ax.setLabelsColor(QColor(self._muted))

    @staticmethod
    def _header_label(title: str) -> QLabel:
        lbl = QLabel(
            f"<span style='color:#ffa726;font-weight:bold;font-size:13px;'>{title}</span>"
        )
        lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        return lbl

    def _header_with_control(self, title: str, control: QWidget | None = None) -> QWidget:
        """Hlavička karty: vycentrovaný titulek + ovládací prvek vpravo v rohu,
        oba na jednom řádku."""
        w = QWidget()
        hb = QHBoxLayout(w)
        hb.setContentsMargins(0, 0, 0, 0)
        title_lbl = self._header_label(title)
        if control is None:
            hb.addWidget(title_lbl)
            return w
        # Levá mezera o šířce comboboxu vyváží jeho pravou pozici → titulek je
        # vycentrovaný v celé šířce a combo sedí v pravém horním rohu.
        hb.addSpacing(max(control.sizeHint().width(), 1))
        hb.addStretch(1)
        hb.addWidget(title_lbl)
        hb.addStretch(1)
        hb.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        return w

    @staticmethod
    def _short_year(year: str) -> str:
        """„2017/2018" → „17/18" (kratší popisek osy); jinak beze změny."""
        m = re.fullmatch(r"(\d{4})/(\d{4})", year)
        return f"{m.group(1)[2:]}/{m.group(2)[2:]}" if m else year

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

        # KPI souhrn — nadpis + řada zaoblených pilulek (vycentrováno nahoře).
        self._kpi_banner.setText(self._h("Souhrn"))
        while self._kpi_cards_lay.count():
            it = self._kpi_cards_lay.takeAt(0)
            if it.widget() is not None:
                it.widget().deleteLater()
        for label, n, color in self._kpi_data(theses, opposings, students, rejected):
            self._kpi_cards_lay.addWidget(self._kpi_pill(n, label, color))

        while self._rows.count():
            item = self._rows.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        # Řádek 1 — obory, podle roku (data + koláč dle přepínání), známky.
        self._add_row([
            self._card_obory(theses, rejected),
            self._card_year(theses),
            self._card_grades(theses, opposings),
        ])
        # Řádek 2 — vývoj počtu po letech přes celou šířku (roky tu přibývají).
        self._add_row([self._card_trend(theses, opposings)])
        # Řádek 3 — soubory a odměny vedle sebe (posudky jsou jinde v GUI).
        self._add_row([
            self._make_card(self._files(theses, opposings)),
            self._make_card(self._finance(theses, opposings), center=True),
        ])

    # --- grafy / interaktivní karty ------------------------------------------

    def _card_trend(self, theses, opposings) -> QFrame | None:
        if not theses and not opposings:
            return None
        self._trend_theses = theses
        self._trend_opposings = opposings
        card = self._card_frame()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 8, 14, 12)
        self._trend_combo = QComboBox()
        self._trend_combo.addItem("Vedené")      # index 0
        self._trend_combo.addItem("Oponované")   # index 1
        self._trend_combo.setCurrentIndex(0 if self._trend_mode == "led" else 1)
        self._trend_combo.currentIndexChanged.connect(
            lambda i: self._set_trend("led" if i == 0 else "opp")
        )
        lay.addWidget(
            self._header_with_control("Vývoj počtu prací po letech", self._trend_combo)
        )
        self._trend_view = self._chart_view()
        lay.addWidget(self._trend_view, stretch=1)
        self._render_trend()
        return card

    def _set_trend(self, mode: str) -> None:
        self._trend_mode = mode
        self._render_trend()

    def _render_trend(self) -> None:
        data = self._trend_theses if self._trend_mode == "led" else self._trend_opposings
        by_year: Counter[str] = Counter(
            (getattr(x, "academic_year", None) or "(bez roku)") for x in data
        )
        chart = QChart()
        if by_year:
            years = sorted(by_year)
            bset = QBarSet("")
            for y in years:
                bset.append(by_year[y])
            color = "#1565c0" if self._trend_mode == "led" else "#5e35b1"
            bset.setColor(QColor(color))
            bset.setLabelColor(QColor(self._fg))
            series = QBarSeries()
            series.append(bset)
            series.setLabelsVisible(True)
            chart.addSeries(series)
            ax = QBarCategoryAxis()
            ax.append([self._short_year(y) for y in years])  # „17/18" místo „2017/2018"
            ax.setLabelsAngle(0)            # vodorovné popisky (řádek 2 je dost široký)
            ax.setGridLineVisible(False)
            chart.addAxis(ax, Qt.AlignmentFlag.AlignBottom)
            series.attachAxis(ax)
            ay = QValueAxis()
            ay.setLabelFormat("%d")
            ay.setGridLineColor(QColor(self._border))
            top = max(by_year.values())
            ay.setRange(0, top + 1)
            ay.setTickCount(min(top + 2, 6))
            chart.addAxis(ay, Qt.AlignmentFlag.AlignLeft)
            series.attachAxis(ay)
            self._apply_axis_font(ax, ay)
            # Popisky roků o něco větší a tučné — jsou hlavní orientace v grafu.
            xf = QFont()
            xf.setPointSize(10)
            xf.setBold(True)
            ax.setLabelsFont(xf)
            ax.setLabelsColor(QColor(self._fg))
        self._style_chart(chart)
        chart.setMargins(QMargins(0, 0, 4, 0))   # rezerva, ať poslední popisek není uťatý
        self._trend_view.setChart(chart)

    def _card_obory(self, theses, rejected) -> QFrame | None:
        if not theses:
            return None
        total = len(theses)
        card = self._card_frame()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 8, 14, 12)
        lay.setSpacing(6)
        lay.addWidget(self._header_label("Obory · typ prací · kapacita"))
        bp = sum(1 for t in theses if t.type.value == "BP")
        dp = total - bp
        # Obory sjednocené jako v Šablonách (ITA/SWI/KYB/UI/BTSM — forma -P/-K,
        # jazyk -EN i prefix N se ignorují). Zároveň počty podle formy studia.
        counts: Counter[str] = Counter()
        forms: Counter[str | None] = Counter()
        for t in theses:
            student = self.service.get_student(t.student_id) if t.student_id else None
            raw = (student.obor if student else "") or ""
            disc = discipline_from_app_code(raw) if raw else ""
            counts[disc or "(bez oboru)"] += 1
            forms[(student.form.value if student and student.form else None)] += 1
        ordered = counts.most_common()
        top_n = 10
        if len(ordered) > top_n:
            ordered = [*ordered[:top_n], ("ostatní", sum(n for _o, n in ordered[top_n:]))]
        # Každý obor = vlastní QBarSet → vlastní barva + položka v legendě
        # (svislé sloupce, QBarSet umí jen jednu barvu na set).
        series = QBarSeries()
        for obor, n in ordered:
            bset = QBarSet(obor)
            bset.append(n)
            bset.setColor(QColor(obor_color(obor)))
            bset.setLabelColor(QColor(self._fg))
            series.append(bset)
        series.setLabelsVisible(True)
        series.setLabelsPosition(QAbstractBarSeries.LabelsPosition.LabelsOutsideEnd)
        chart = QChart()
        chart.addSeries(series)
        ax = QBarCategoryAxis()
        ax.append([""])    # jediná kategorie — obory rozlišuje barva + legenda
        ax.setGridLineVisible(False)
        chart.addAxis(ax, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(ax)
        avy = QValueAxis()
        avy.setLabelFormat("%d")
        avy.setGridLineColor(QColor(self._border))
        top = max(n for _o, n in ordered)
        avy.setRange(0, top + max(1, round(top * 0.15)))   # rezerva nad sloupce pro čísla
        avy.setTickCount(6)
        avy.setLabelsVisible(False)   # počty jsou nad sloupci → osa Y je nadbytečná
        chart.addAxis(avy, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(avy)
        self._apply_axis_font(ax, avy)
        self._style_chart(chart, legend=True)
        # Nahoře graf přes celou šíři karty.
        lay.addWidget(self._chart_view(chart), stretch=1)
        # Dole tři části (na střed): počty BP/DP · forma studia · kapacita.
        bp_pct = bp / total * 100.0
        dp_pct = dp / total * 100.0
        type_html = (
            self._h("Typ prací")
            + f"<p>Bakalářské (BP): <b>{bp}</b> "
            f"<span style='color:{self._muted};'>({bp_pct:.0f}%)</span><br>"
            f"Diplomové (DP): <b>{dp}</b> "
            f"<span style='color:{self._muted};'>({dp_pct:.0f}%)</span></p>"
        )
        pres = forms.get(StudyForm.PRESENTIAL.value, 0)
        comb = forms.get(StudyForm.COMBINED.value, 0)
        unkn = forms.get(None, 0)
        form_rows = (
            f"{StudyForm.PRESENTIAL.label}: <b>{pres}</b> "
            f"<span style='color:{self._muted};'>({pres / total * 100:.0f}%)</span><br>"
            f"{StudyForm.COMBINED.label}: <b>{comb}</b> "
            f"<span style='color:{self._muted};'>({comb / total * 100:.0f}%)</span>"
        )
        if unkn:
            form_rows += (
                f"<br>Neuvedeno: <b>{unkn}</b> "
                f"<span style='color:{self._muted};'>({unkn / total * 100:.0f}%)</span>"
            )
        form_html = self._h("Forma studia") + f"<p>{form_rows}</p>"
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        for html in (type_html, form_html, self._capacity(theses, rejected)):
            lbl = QLabel(f"<div style='font-size:13px;text-align:center;'>{html}</div>")
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setWordWrap(True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bottom.addWidget(lbl, 1)
        lay.addLayout(bottom)
        return card

    def _card_year(self, theses) -> QFrame | None:
        if not theses:
            return None
        years: dict[str, dict] = {}
        for t in theses:
            y = t.academic_year or "(bez roku)"
            d = years.setdefault(y, {"n": 0, "bp": 0, "dp": 0, "st": Counter()})
            d["n"] += 1
            d["bp" if t.type.value == "BP" else "dp"] += 1
            d["st"][t.status] += 1
        self._year_data = years
        card = self._card_frame()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 8, 14, 12)
        self._year_combo = QComboBox()
        self._year_combo.addItem(self._ALL_YEARS)   # výchozí: souhrn přes všechny roky
        for y in sorted(years, reverse=True):
            self._year_combo.addItem(y)
        self._year_combo.currentTextChanged.connect(self._render_year)
        lay.addWidget(
            self._header_with_control("Podle akademického roku", self._year_combo)
        )
        # Data a koláč vedle sebe, vycentrované doprostřed karty (přepíná se
        # s comboboxem; legenda netřeba — popis je v datech vlevo).
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        self._year_detail = QLabel()
        self._year_detail.setTextFormat(Qt.TextFormat.RichText)
        self._year_detail.setWordWrap(False)   # ať se „Celkem … DP" nezalamuje
        self._year_detail.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._year_pie = self._chart_view()
        self._year_pie.setMinimumWidth(170)
        self._year_pie.setMaximumWidth(210)
        body.addStretch(1)
        body.addWidget(self._year_detail, 0, Qt.AlignmentFlag.AlignVCenter)
        body.addSpacing(18)
        body.addWidget(self._year_pie, 0, Qt.AlignmentFlag.AlignVCenter)
        body.addStretch(1)
        lay.addLayout(body, stretch=1)
        if self._year_combo.count():
            self._render_year(self._year_combo.currentText())
        return card

    def _render_year(self, sel: str) -> None:
        if sel == self._ALL_YEARS:
            # Souhrn přes všechny roky (sloučí stavy).
            st: Counter = Counter()
            for dd in self._year_data.values():
                st.update(dd["st"])
            d = {
                "n": sum(dd["n"] for dd in self._year_data.values()),
                "bp": sum(dd["bp"] for dd in self._year_data.values()),
                "dp": sum(dd["dp"] for dd in self._year_data.values()),
                "st": st,
            }
        else:
            d = self._year_data.get(sel)
        if not d or not d["n"]:
            return
        # Jen stavy, které v daném výběru reálně jsou (budoucí → vypsaná témata
        # apod.; historický rok → bez „V řešení"). Kompaktní, vycentrované.
        rows = ""
        for status in ThesisStatus:
            n = d["st"].get(status, 0)
            if not n:
                continue
            pct = n / d["n"] * 100.0
            rows += (
                f"<tr><td style='padding:1px 6px 1px 0;color:{status.color};'>●</td>"
                f"<td style='padding:1px 12px 1px 0;'>{status.label}</td>"
                f"<td style='padding:1px 0;'><b>{n}</b> "
                f"<span style='color:{self._muted};'>({pct:.0f}%)</span></td></tr>"
            )
        # Úspěšnost obhajob (z dokončených) — dříve samostatná dlaždice.
        defended = d["st"].get(ThesisStatus.DEFENDED, 0)
        failed = d["st"].get(ThesisStatus.FAILED, 0)
        cancelled = d["st"].get(ThesisStatus.CANCELLED, 0)
        finished = defended + failed + cancelled
        success_line = ""
        if finished:
            rate = defended / finished * 100.0
            success_line = (
                f"<p style='margin-top:6px;'>Úspěšnost obhajob: "
                f"<b style='color:#2e7d32;'>{rate:.0f}%</b> "
                f"<span style='color:{self._muted};'>({defended} z {finished})</span></p>"
            )
        self._year_detail.setText(
            "<div style='font-size:13px;'>"
            f"<p>Celkem <b>{d['n']}</b> &nbsp;·&nbsp; BP <b>{d['bp']}</b> "
            f"&nbsp;·&nbsp; DP <b>{d['dp']}</b></p>"
            f"<table>{rows}</table>{success_line}</div>"
        )
        # Koláč stavů pro vybraný výběr (barvy stavů, bez legendy).
        series = QPieSeries()
        series.setHoleSize(0.40)
        for status in ThesisStatus:
            n = d["st"].get(status, 0)
            if not n:
                continue
            sl = series.append(status.label, n)
            sl.setColor(QColor(status.color))
            sl.setLabelVisible(False)
            sl.setBorderColor(QColor(self._border))
        chart = QChart()
        chart.addSeries(series)
        self._style_chart(chart, legend=False)
        self._year_pie.setChart(chart)

    _GRADES: ClassVar[list[str]] = ["A", "B", "C", "D", "E", "F"]
    _ALL_YEARS = "Všechny roky"   # výchozí volba v kartě „Podle akademického roku"

    def _card_grades(self, theses, opposings) -> QFrame | None:
        led_me: Counter = Counter()
        led_opp: Counter = Counter()
        opp_me: Counter = Counter()
        opp_sup: Counter = Counter()
        for t in theses:
            if t.status != ThesisStatus.DEFENDED:
                continue
            gs = (t.grade_supervisor or "").strip().upper()
            go = (t.grade_opponent or "").strip().upper()
            if gs in self._GRADES:
                led_me[gs] += 1
            if go in self._GRADES:
                led_opp[go] += 1
        for o in opposings:
            go = (o.grade_opponent or "").strip().upper()
            gs = (o.grade_supervisor or "").strip().upper()
            if go in self._GRADES:
                opp_me[go] += 1
            if gs in self._GRADES:
                opp_sup[gs] += 1
        # 4 pohledy přepínatelné comboboxem.
        self._grade_views = [
            ("Vedu já", led_me, "#1565c0"),
            ("Jsem oponent", opp_me, "#8e24aa"),
            ("Oponent mých vedených", led_opp, "#00897b"),
            ("Vedoucí mých oponovaných", opp_sup, "#ef6c00"),
        ]
        if not any(c for _n, c, _col in self._grade_views):
            return None
        card = self._card_frame()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 8, 14, 12)
        self._grade_combo = QComboBox()
        for name, _c, _col in self._grade_views:
            self._grade_combo.addItem(name)
        self._grade_combo.currentIndexChanged.connect(self._render_grades)
        lay.addWidget(self._header_with_control("Známky", self._grade_combo))
        # Koláč známek A-F obarvený stejně jako známky v tabulce prací
        # (GRADE_TINTS: zelená A → červená F). Popis přes legendu, ne v dílcích.
        self._grade_pie = self._chart_view()
        lay.addWidget(self._grade_pie, stretch=1)
        self._render_grades(0)
        return card

    def _render_grades(self, index: int) -> None:
        if not (0 <= index < len(self._grade_views)):
            return
        _name, counter, _color = self._grade_views[index]
        chart = QChart()
        if sum(counter.values()):
            series = QPieSeries()
            for g in self._GRADES:
                n = counter.get(g, 0)
                if not n:
                    continue
                sl = series.append(f"{g}  ({n})", n)   # text jde do legendy
                sl.setColor(QColor(GRADE_TINTS.get(g, self._muted)))
                sl.setLabelVisible(False)              # ne do dílců, jen legenda
                sl.setBorderColor(QColor(self._border))
            chart.addSeries(series)
        self._style_chart(chart, legend=True)
        self._grade_pie.setChart(chart)

    # --- sekce ---------------------------------------------------------------

    @staticmethod
    def _h(title: str) -> str:
        return f'<h3 style="color:#ffa726;margin:16px 0 6px 0;">{title}</h3>'

    def _kpi_data(self, theses, opposings, students, rejected) -> list[tuple[str, int, str]]:
        cur = sum(1 for t in theses if t.status in STATUSES_CURRENT)
        fut = sum(1 for t in theses if t.status in STATUSES_FUTURE)
        hist = sum(1 for t in theses if t.status in STATUSES_HISTORY)
        return [
            ("Vedené práce", len(theses), "#1565c0"),
            ("V řešení", cur, "#00897b"),
            ("Budoucí", fut, "#7cb342"),
            ("Historie", hist, "#8e24aa"),
            ("Oponentury", len(opposings), "#5e35b1"),
            ("Studenti", len(students), "#546e7a"),
            ("Odmítnutí", len(rejected), "#b71c1c"),
        ]

    def _kpi_pill(self, n: int, label: str, color: str) -> QLabel:
        """Zaoblená „pilulka" KPI (číslo + popisek) — rohy přes stylesheet."""
        lbl = QLabel(
            "<div style='text-align:center;line-height:115%;'>"
            f"<span style='font-size:22px;font-weight:bold;'>{n}</span><br>"
            f"<span style='font-size:11px;'>{label}</span></div>"
        )
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"QLabel {{ background:{color}; color:white; border-radius:10px; "
            "padding:8px 14px; min-width:80px; }"
        )
        return lbl

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
        # width='100%' + cellpadding → tabulka vyplní šířku i výšku panelu.
        return self._h("Odměny (orientačně)") + (
            f"<p style='color:{self._muted};font-size:11px;'>Vedení {_czk(_FEE_THESIS)}/práci "
            f"(jen <b>obhájené</b>, max {_THESIS_FEE_CAP_PER_YEAR}/rok — symbol ⚠ "
            f"značí překročení stropu), oponentský posudek {_czk(_FEE_OPPOSING)}.</p>"
            f"<table width='100%' cellpadding='6' cellspacing='0' "
            f"style='font-size:14px;'>{header}{rows}</table>"
        )

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
