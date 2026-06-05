"""Evidence odmítnutých zájemců o vedení práce.

Lehký záznam (jméno, obor, akademický rok) — souvisí s kapacitou vedení
(max počet vedených prací). Není to plnohodnotný Student.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class RejectedStudent(BaseModel):
    """Odmítnutý zájemce o vedení práce."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = ""
    obor: str = ""
    academic_year: str = ""
    note: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
