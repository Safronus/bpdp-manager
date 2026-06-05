from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .enums import StudyForm


class Student(BaseModel):
    """Student.

    Forma studia (prezenční/kombinovaná) se **neukládá** — odvozuje se z přípony
    oboru: ``-P`` (prezenční), ``-K`` (kombinovaná). Pokud obor není ve tvaru
    ``XXX-P``/``XXX-K``, ``form`` vrátí ``None``.

    Pole ``form`` v JSON datech ze starších verzí je při načítání tiše ignorováno
    (díky ``extra='ignore'``), nevyžaduje to migraci.
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid4()))
    first_name: str
    last_name: str
    obor: str = ""
    university_id: str | None = None
    email: str | None = None
    phone: str | None = None
    note: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def form(self) -> StudyForm | None:
        """Forma studia odvozená z přípony oboru."""
        return derive_form_from_obor(self.obor)

    @property
    def display_obor(self) -> str:
        return self.obor or "—"


def derive_form_from_obor(obor: str | None) -> StudyForm | None:
    """Z přípony oboru (``-P``/``-K``, case-insensitive) odvodí formu studia.

    Zvládá i anglické varianty se suffixem ``-EN`` (např. ``NSWI-P-EN``) —
    ten se před vyhodnocením formy odřízne.
    """
    if not obor:
        return None
    stripped = obor.strip().upper()
    if stripped.endswith("-EN"):
        stripped = stripped[:-3]
    if stripped.endswith("-P"):
        return StudyForm.PRESENTIAL
    if stripped.endswith("-K"):
        return StudyForm.COMBINED
    return None
