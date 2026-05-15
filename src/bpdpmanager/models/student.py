from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field

from .enums import StudyForm


class Student(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    first_name: str
    last_name: str
    obor: str = ""
    form: StudyForm | None = None
    email: str | EmailStr | None = None
    phone: str | None = None
    note: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_obor(self) -> str:
        if self.obor and self.form:
            return f"{self.obor}-{self.form.value}"
        return self.obor or "—"
