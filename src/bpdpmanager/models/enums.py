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
    INTERESTED = "interested"
    RESERVED = "reserved"
    LISTED = "listed"
    ASSIGNED = "assigned"
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
    ThesisStatus.ASSIGNED: "Schválené téma",
    ThesisStatus.IN_PROGRESS: "V řešení",
    ThesisStatus.DEFENDED: "Obhájeno",
    ThesisStatus.CANCELLED: "Nedokončeno",
}

STATUS_COLORS: dict[ThesisStatus, str] = {
    ThesisStatus.INTERESTED: "#9e9e9e",
    ThesisStatus.RESERVED: "#ffb74d",
    ThesisStatus.LISTED: "#64b5f6",
    ThesisStatus.ASSIGNED: "#4fc3f7",
    ThesisStatus.IN_PROGRESS: "#7e57c2",
    ThesisStatus.DEFENDED: "#66bb6a",
    ThesisStatus.CANCELLED: "#e57373",
}

STATUS_ORDER: dict[ThesisStatus, int] = {
    s: i for i, s in enumerate(ThesisStatus)
}

ALLOWED_TRANSITIONS: dict[ThesisStatus, set[ThesisStatus]] = {
    ThesisStatus.INTERESTED: {ThesisStatus.RESERVED, ThesisStatus.CANCELLED},
    ThesisStatus.RESERVED: {ThesisStatus.LISTED, ThesisStatus.INTERESTED, ThesisStatus.CANCELLED},
    ThesisStatus.LISTED: {ThesisStatus.ASSIGNED, ThesisStatus.RESERVED, ThesisStatus.CANCELLED},
    ThesisStatus.ASSIGNED: {ThesisStatus.IN_PROGRESS, ThesisStatus.LISTED, ThesisStatus.CANCELLED},
    ThesisStatus.IN_PROGRESS: {ThesisStatus.DEFENDED, ThesisStatus.CANCELLED, ThesisStatus.ASSIGNED},
    ThesisStatus.DEFENDED: set(),
    ThesisStatus.CANCELLED: {ThesisStatus.INTERESTED},
}
