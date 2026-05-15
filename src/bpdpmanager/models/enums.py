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
    SUPERVISOR_REVIEW = "supervisor_review"
    OPPONENT_REVIEW = "opponent_review"
    THESIS_TEXT = "thesis_text"
    ASSIGNMENT = "assignment"
    PRESENTATION = "presentation"
    OTHER = "other"

    @property
    def label(self) -> str:
        return ATTACHMENT_KIND_LABELS[self]


ATTACHMENT_KIND_LABELS: dict[AttachmentKind, str] = {
    AttachmentKind.SUPERVISOR_REVIEW: "Posudek vedoucího",
    AttachmentKind.OPPONENT_REVIEW: "Posudek oponenta",
    AttachmentKind.THESIS_TEXT: "Text práce",
    AttachmentKind.ASSIGNMENT: "Oficiální zadání",
    AttachmentKind.PRESENTATION: "Prezentace",
    AttachmentKind.OTHER: "Jiné",
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
