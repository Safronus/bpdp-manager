from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .enums import AttachmentKind, ThesisStatus, ThesisType


class Deadline(BaseModel):
    label: str
    date: date
    done: bool = False


class Attachment(BaseModel):
    label: str
    url_or_path: str  # absolute path, URL, nebo relativní cesta v documents/{thesis_id}/
    kind: AttachmentKind = AttachmentKind.OTHER
    is_file: bool = False  # True = lokální soubor v documents/, False = URL/externí cesta


class Thesis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ThesisType
    status: ThesisStatus = ThesisStatus.INTERESTED
    academic_year: str

    student_id: str | None = None
    opponent_id: str | None = None

    title_cs: str = ""
    title_en: str = ""
    annotation: str = ""
    objectives: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)

    deadlines: list[Deadline] = Field(default_factory=list)
    notes: str = ""
    attachments: list[Attachment] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def touch(self) -> None:
        self.updated_at = datetime.now()

    @property
    def display_title(self) -> str:
        return self.title_cs or "(bez názvu)"

    def is_ready_for_listing(self) -> tuple[bool, list[str]]:
        """Vypsání tématu vyžaduje název CZ a anotaci."""
        missing = []
        if not self.title_cs.strip():
            missing.append("název CZ")
        if not self.annotation.strip():
            missing.append("anotace")
        return (not missing, missing)

    def is_ready_for_assignment(self) -> tuple[bool, list[str]]:
        """Oficiální zadání vyžaduje navíc EN název, body zadání a literaturu."""
        ok, missing = self.is_ready_for_listing()
        if not self.title_en.strip():
            missing.append("název EN")
        if not self.objectives:
            missing.append("body zadání")
        if not self.references:
            missing.append("literární zdroje")
        return (not missing, missing)
