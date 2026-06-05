"""Oponentské posudky — práce, kde já vystupuji jako oponent.

Oddělený model od ``Thesis`` (kde jsem vedoucí). Záměrně inline údaje
o studentovi a vedoucím (žádné FK na Student/Opponent entity) — tihle
lidé nejsou „moji" a nepotřebuju je spravovat napříč pracemi.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import AttachmentKind, ThesisType
from .review import Review
from .thesis import Attachment


class OpposingThesis(BaseModel):
    """Posuzovaná BP/DP, kde já jsem oponent."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ThesisType
    academic_year: str

    # Student — inline (jen evidence, neukládáme do globálního Student registru)
    student_first_name: str = ""
    student_last_name: str = ""
    student_obor: str = ""
    student_university_id: str = ""

    # Vedoucí (jako string — externí osoba)
    supervisor_name: str = ""
    supervisor_email: str = ""

    # Téma
    title_cs: str = ""
    objectives: str = ""  # body zadání jako volný text (1 řádek = 1 bod)

    # Známky (volný text — připouští "1", "A", "B−" atd.)
    grade_supervisor: str = ""
    grade_opponent: str = ""

    # Odkaz na práci v IS/STAG
    stag_url: str = ""
    adipidno: str = ""  # STAG ID práce (adipIdno) — pro přesné párování při importu

    # Dokumenty: plný text práce, posudek vedoucího, posudek oponenta + příp. další
    attachments: list[Attachment] = Field(default_factory=list)
    # v4+ (0.19.0): strukturované posudky.
    reviews: list[Review] = Field(default_factory=list)

    # Kdy byl oponentský posudek odeslán sekretářce (None = neodesláno).
    opponent_review_sent_at: datetime | None = None

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="before")
    @classmethod
    def _migrate_list_objectives(cls, data: Any) -> Any:
        """Zpětně kompatibilní — kdyby přišel list[str], převeď na text."""
        if isinstance(data, dict):
            v = data.get("objectives")
            if isinstance(v, list):
                items = [str(x).strip() for x in v if str(x).strip()]
                data["objectives"] = "\n".join(items)
        return data

    def touch(self) -> None:
        self.updated_at = datetime.now()

    @property
    def student_full_name(self) -> str:
        return f"{self.student_first_name} {self.student_last_name}".strip()

    @property
    def display_title(self) -> str:
        return self.title_cs or "(bez názvu)"

    @property
    def opponent_review_state(self) -> str:
        """Stav oponentského posudku: ``"done"`` (vyrobený soubor) /
        ``"draft"`` (jen uložená data) / ``"none"`` (nic)."""
        if any(
            a.is_file and a.kind == AttachmentKind.OPPONENT_REVIEW
            for a in self.attachments
        ):
            return "done"
        if any(r.role == "opponent" for r in self.reviews):
            return "draft"
        return "none"
