from __future__ import annotations

from enum import Enum


class ThesisType(str, Enum):
    BP = "BP"
    DP = "DP"

    @property
    def label(self) -> str:
        return {"BP": "Bakalářská práce", "DP": "Diplomová práce"}[self.value]


class StudyForm(str, Enum):
    PRESENTIAL = "P"
    COMBINED = "K"

    @property
    def label(self) -> str:
        return {"P": "Prezenční", "K": "Kombinovaná"}[self.value]


class OpponentKind(str, Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"

    @property
    def label(self) -> str:
        return {"internal": "Interní", "external": "Externí"}[self.value]


class AttachmentKind(str, Enum):
    THESIS_TEXT = "thesis_text"
    THESIS_APPENDIX = "thesis_appendix"
    # Jeden archiv (zip) obsahující text práce i přílohy pohromadě — STAG ho
    # někdy nabízí jako jediný soubor v sekci „el. podoba" bez samostatného PDF.
    THESIS_BUNDLE = "thesis_bundle"
    WORK_JOURNAL = "work_journal"
    ASSIGNMENT = "assignment"
    SUPERVISOR_REVIEW = "supervisor_review"
    OPPONENT_REVIEW = "opponent_review"
    PRESENTATION = "presentation"
    # 0.71.0: protokol/zápis o průběhu obhajoby (státní závěrečné zkoušky).
    DEFENSE_RECORD = "defense_record"
    STAG_EXPORT = "stag_export"
    OTHER = "other"

    @property
    def label(self) -> str:
        return ATTACHMENT_KIND_LABELS[self]


ATTACHMENT_KIND_LABELS: dict[AttachmentKind, str] = {
    AttachmentKind.THESIS_TEXT: "Text práce",
    AttachmentKind.THESIS_APPENDIX: "Přílohy práce",
    AttachmentKind.THESIS_BUNDLE: "Text práce + přílohy",
    AttachmentKind.WORK_JOURNAL: "Pracovní deník",
    AttachmentKind.ASSIGNMENT: "Oficiální zadání",
    AttachmentKind.SUPERVISOR_REVIEW: "Posudek vedoucího",
    AttachmentKind.OPPONENT_REVIEW: "Posudek oponenta",
    AttachmentKind.PRESENTATION: "Prezentace",
    AttachmentKind.DEFENSE_RECORD: "Soubor s průběhem obhajoby",
    AttachmentKind.STAG_EXPORT: "STAG export (CSV)",
    AttachmentKind.OTHER: "Jiné",
}


class PlagiarismVerdict(str, Enum):
    """Posouzení výsledku plagiátorství vedoucím."""

    NOT_ASSESSED = "not_assessed"
    PLAGIARISM = "plagiarism"
    NOT_PLAGIARISM = "not_plagiarism"

    @property
    def label(self) -> str:
        return PLAGIARISM_VERDICT_LABELS[self]

    @property
    def color(self) -> str:
        return PLAGIARISM_VERDICT_COLORS[self]


PLAGIARISM_VERDICT_LABELS: dict["PlagiarismVerdict", str] = {
    PlagiarismVerdict.NOT_ASSESSED: "Neposouzen",
    PlagiarismVerdict.PLAGIARISM: "Posouzen — je plagiát",
    PlagiarismVerdict.NOT_PLAGIARISM: "Posouzen — není plagiát",
}

PLAGIARISM_VERDICT_COLORS: dict["PlagiarismVerdict", str] = {
    PlagiarismVerdict.NOT_ASSESSED: "#9e9e9e",   # šedá
    PlagiarismVerdict.PLAGIARISM: "#c62828",     # červená
    PlagiarismVerdict.NOT_PLAGIARISM: "#2e7d32", # zelená
}


class ThesisStatus(str, Enum):
    # Pozn.: ``ASSIGNED`` (Schválené téma) byl ve verzi 0.15.0 sloučen
    # do ``IN_PROGRESS`` — po schválení tématu de facto začíná práce
    # a samostatný stav přidával jen šum. Migrace v ``Database`` převede
    # všechny existující ``assigned`` na ``in_progress``.
    INTERESTED = "interested"
    RESERVED = "reserved"
    LISTED = "listed"
    IN_PROGRESS = "in_progress"
    DEFENDED = "defended"
    CANCELLED = "cancelled"
    # 0.68.0: „Neobhájeno" — neúspěšná obhajoba (odlišené od „Nedokončeno",
    # což je práce nikdy nedotažená k obhajobě). Ze STAG: DBUO/OPUNO.
    FAILED = "failed"

    @property
    def label(self) -> str:
        return STATUS_LABELS[self]

    @property
    def color(self) -> str:
        return STATUS_COLORS[self]

    @property
    def order(self) -> int:
        return STATUS_ORDER[self]


STATUS_LABELS: dict[ThesisStatus, str] = {
    ThesisStatus.INTERESTED: "Zájemce bez tématu",
    ThesisStatus.RESERVED: "Zájemce s tématem",
    ThesisStatus.LISTED: "Vypsané téma",
    ThesisStatus.IN_PROGRESS: "V řešení",
    ThesisStatus.DEFENDED: "Obhájeno",
    ThesisStatus.CANCELLED: "Nedokončeno",
    ThesisStatus.FAILED: "Neobhájeno",
}

STATUS_COLORS: dict[ThesisStatus, str] = {
    ThesisStatus.INTERESTED: "#9e9e9e",
    ThesisStatus.RESERVED: "#ffb74d",
    ThesisStatus.LISTED: "#64b5f6",
    ThesisStatus.IN_PROGRESS: "#7e57c2",
    ThesisStatus.DEFENDED: "#66bb6a",
    ThesisStatus.CANCELLED: "#d6d6d6",  # světle šedá — nedokončeno (jen opuštěno)
    ThesisStatus.FAILED: "#c62828",  # sytější červená — neúspěšná obhajoba
}

STATUS_ORDER: dict[ThesisStatus, int] = {
    s: i for i, s in enumerate(ThesisStatus)
}

# Navržené známky (ECTS) — pořadí pro filtr a barvy pro vizualizaci sloupce
# „Známky". Světlé odstíny pro podbarvení písmene (tmavý text čitelný),
# přechod zelená (A) → červená (F/FX).
GRADES_ORDER: list[str] = ["A", "B", "C", "D", "E", "F", "FX"]
GRADE_TINTS: dict[str, str] = {
    # Výraznější gradient A→F/FX (text se kreslí kontrastně — viz GradesDelegate).
    "A": "#66bb6a",   # výrazná zelená
    "B": "#9ccc65",   # zelenožlutá
    "C": "#ffee58",   # žlutá
    "D": "#ffa726",   # oranžová
    "E": "#ff7043",   # červenooranžová (výraznější)
    "F": "#ef5350",   # červená (výraznější)
    "FX": "#e53935",  # sytá červená (nejvýraznější)
}

# Barvy oborů v grafu Statistik. Klíčem je obor zbavený jen formy (-P/-K) a
# jazyka (-EN) — prefix N (navazující/DP) i specializace (-M/-T) zůstávají, BP a
# DP obory se tedy nemíchají. Když není přesná shoda, hledá se rodina (NSWI→SWI,
# BTSM-M→BTSM).
OBOR_COLORS: dict[str, str] = {
    # Bakalářské programy
    "SWI": "#1565c0",     # modrá — softwarové inženýrství
    "IRT": "#00897b",     # tyrkysová
    "ITA": "#ef6c00",     # oranžová — IT v administrativě
    "BTSM": "#c62828",    # červená — bezpečnostní technologie
    # Navazující (DP) programy a specializace
    "NSWI": "#1565c0",    # modrá (rodina SWI)
    "NKYB": "#6a1b9a",    # fialová — kybernetická bezpečnost
    "IT": "#3949ab",      # indigo
    "PKS": "#00838f",     # azurová
    "BTSM-M": "#e53935",  # červená — bezpečnostní technologie, management
    "BTSM-T": "#ad1457",  # vínová — bezpečnostní technologie, technologie
    "UI": "#7cb342",      # zelená — učitelství informatiky
}
_OBOR_FALLBACK = "#607d8b"   # šedomodrá pro neznámé / „(bez oboru)"


def obor_color(code: str) -> str:
    """Barva oboru; nejdřív přesná shoda, pak rodina (NSWI→SWI, BTSM-M→BTSM)."""
    c = (code or "").strip().upper()
    if c in OBOR_COLORS:
        return OBOR_COLORS[c]
    base = c[1:] if c.startswith("N") and len(c) >= 3 else c   # NSWI → SWI
    base = base.split("-", 1)[0]                                # BTSM-M → BTSM
    return OBOR_COLORS.get(base, _OBOR_FALLBACK)


# Stav posudku (vedoucího / oponenta) → barva pro odlišení v seznamech.
# "done" = vyrobený soubor (zelená), "draft" = jen uložená data (oranžová),
# "none" = nic (červená). Světlé odstíny pro podbarvení buňky (text čitelný).
REVIEW_STATE_LABELS: dict[str, str] = {
    "done": "posudek hotový",
    "draft": "rozpracovaný (jen data)",
    "none": "posudek chybí",
}
REVIEW_STATE_TINTS: dict[str, str] = {
    "done": "#c8e6c9",   # světle zelená
    "draft": "#ffe0b2",  # světle oranžová
    "none": "#ffcdd2",   # světle červená
}
REVIEW_STATE_STRONG: dict[str, str] = {
    # Světlejší odstíny — čitelné v light i dark theme (text počtů v liště).
    "done": "#66bb6a",   # zelená (čitelná i na tmavém pozadí)
    "draft": "#ffa726",  # oranžová
    "none": "#ef5350",   # červená
}


def review_sent_indicator(prepared: bool, sent_at) -> tuple[str, str]:
    """Jednotná indikace odeslání posudku sekretářce (text do sloupce, tooltip).

    Používá se shodně v seznamu vedených prací i oponentur. Vrací prázdné,
    pokud posudek ještě není hotový (není co odeslat).
    """
    if not prepared:
        return "", ""
    if sent_at:
        return "✉ ✓", f"Posudek odeslán sekretářce {sent_at.strftime('%d.%m.%Y')}"
    return "✉ ✗", "Posudek zatím NEODESLÁN sekretářce"


# Barvy pro sloupec „Odesláno" (obálka na barevném pozadí).
SENT_BG = "#43a047"     # zelená — odesláno
UNSENT_BG = "#e53935"   # červená — neodesláno


def review_sent_badge(prepared: bool, sent_at) -> tuple[str, str, str]:
    """Indikace odeslání jako obálka + barva pozadí buňky.

    Vrací ``(text, background_color, tooltip)``. Když posudek ještě není hotový
    (není co odeslat), vrátí prázdný text i barvu.
    """
    if not prepared:
        return "", "", ""
    if sent_at:
        return "✉", SENT_BG, f"Posudek odeslán sekretářce {sent_at.strftime('%d.%m.%Y')}"
    return "✉", UNSENT_BG, "Posudek zatím NEODESLÁN sekretářce"


def review_printed_badge(prepared: bool, printed_at) -> tuple[str, str, str]:
    """Indikace vytištění posudku jako ✓/✗ + barva pozadí buňky.

    Vrací ``(text, background_color, tooltip)``. Když posudek ještě není hotový
    (není co tisknout), vrátí prázdný text i barvu.
    """
    if not prepared:
        return "", "", ""
    if printed_at:
        return "🖨", SENT_BG, f"Posudek vytištěn {printed_at.strftime('%d.%m.%Y')}"
    return "🖨", UNSENT_BG, "Posudek zatím NEVYTIŠTĚN"


# ── Tab buckety (status-driven, bez ohledu na rok) ──────────────────────────
#
# Status-driven filtrace pro hlavní záložky. Rok se používá jen pro
# řazení uvnitř, ne pro vyloučení z tabu (viz ``main_window.py``).
STATUSES_FUTURE: set[ThesisStatus] = {
    ThesisStatus.INTERESTED,
    ThesisStatus.RESERVED,
    ThesisStatus.LISTED,
}
STATUSES_CURRENT: set[ThesisStatus] = {
    ThesisStatus.IN_PROGRESS,
}
STATUSES_HISTORY: set[ThesisStatus] = {
    ThesisStatus.DEFENDED,
    ThesisStatus.CANCELLED,
    ThesisStatus.FAILED,
}


ALLOWED_TRANSITIONS: dict[ThesisStatus, set[ThesisStatus]] = {
    ThesisStatus.INTERESTED: {ThesisStatus.RESERVED, ThesisStatus.CANCELLED},
    ThesisStatus.RESERVED: {ThesisStatus.LISTED, ThesisStatus.INTERESTED, ThesisStatus.IN_PROGRESS, ThesisStatus.CANCELLED},
    ThesisStatus.LISTED: {ThesisStatus.IN_PROGRESS, ThesisStatus.RESERVED, ThesisStatus.CANCELLED},
    ThesisStatus.IN_PROGRESS: {
        ThesisStatus.DEFENDED,
        ThesisStatus.CANCELLED,
        ThesisStatus.FAILED,
        ThesisStatus.LISTED,
    },
    ThesisStatus.DEFENDED: set(),
    # Druhý pokus obhajoby: z Nedokončeno/Neobhájeno se dá zpět do V řešení
    # (re-open) nebo přímo Obhájeno (oprava omylu / práce už fakticky obhájena).
    # Mezi Nedokončeno a Neobhájeno lze přepnout (oprava klasifikace).
    ThesisStatus.CANCELLED: {
        ThesisStatus.INTERESTED,
        ThesisStatus.IN_PROGRESS,
        ThesisStatus.DEFENDED,
        ThesisStatus.FAILED,
    },
    ThesisStatus.FAILED: {
        ThesisStatus.INTERESTED,
        ThesisStatus.IN_PROGRESS,
        ThesisStatus.DEFENDED,
        ThesisStatus.CANCELLED,
    },
}
