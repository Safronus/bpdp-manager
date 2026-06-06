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
    WORK_JOURNAL = "work_journal"
    ASSIGNMENT = "assignment"
    SUPERVISOR_REVIEW = "supervisor_review"
    OPPONENT_REVIEW = "opponent_review"
    PRESENTATION = "presentation"
    STAG_EXPORT = "stag_export"
    OTHER = "other"

    @property
    def label(self) -> str:
        return ATTACHMENT_KIND_LABELS[self]


ATTACHMENT_KIND_LABELS: dict[AttachmentKind, str] = {
    AttachmentKind.THESIS_TEXT: "Text práce",
    AttachmentKind.THESIS_APPENDIX: "Přílohy práce",
    AttachmentKind.WORK_JOURNAL: "Pracovní deník",
    AttachmentKind.ASSIGNMENT: "Oficiální zadání",
    AttachmentKind.SUPERVISOR_REVIEW: "Posudek vedoucího",
    AttachmentKind.OPPONENT_REVIEW: "Posudek oponenta",
    AttachmentKind.PRESENTATION: "Prezentace",
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
}

STATUS_COLORS: dict[ThesisStatus, str] = {
    ThesisStatus.INTERESTED: "#9e9e9e",
    ThesisStatus.RESERVED: "#ffb74d",
    ThesisStatus.LISTED: "#64b5f6",
    ThesisStatus.IN_PROGRESS: "#7e57c2",
    ThesisStatus.DEFENDED: "#66bb6a",
    ThesisStatus.CANCELLED: "#e57373",
}

STATUS_ORDER: dict[ThesisStatus, int] = {
    s: i for i, s in enumerate(ThesisStatus)
}

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
    "done": "#2e7d32",   # sytá zelená (pro text počtů v liště)
    "draft": "#ef6c00",  # sytá oranžová
    "none": "#c62828",   # sytá červená
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
}


ALLOWED_TRANSITIONS: dict[ThesisStatus, set[ThesisStatus]] = {
    ThesisStatus.INTERESTED: {ThesisStatus.RESERVED, ThesisStatus.CANCELLED},
    ThesisStatus.RESERVED: {ThesisStatus.LISTED, ThesisStatus.INTERESTED, ThesisStatus.IN_PROGRESS, ThesisStatus.CANCELLED},
    ThesisStatus.LISTED: {ThesisStatus.IN_PROGRESS, ThesisStatus.RESERVED, ThesisStatus.CANCELLED},
    ThesisStatus.IN_PROGRESS: {ThesisStatus.DEFENDED, ThesisStatus.CANCELLED, ThesisStatus.LISTED},
    ThesisStatus.DEFENDED: set(),
    # Druhý pokus obhajoby: z Nedokončeno se dá zpět do V řešení (re-open)
    # nebo přímo Obhájeno (oprava omylu / shortcut když práce už fakticky obhájena).
    ThesisStatus.CANCELLED: {
        ThesisStatus.INTERESTED,
        ThesisStatus.IN_PROGRESS,
        ThesisStatus.DEFENDED,
    },
}
