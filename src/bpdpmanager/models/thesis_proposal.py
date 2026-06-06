"""Návrh tématu práce — nekompletní nápad bez studenta a bez stavu.

Slouží jako seznam vymyšlených potenciálních témat (BP/DP), která ještě
nikdo nevede. Akademický rok je zde irelevantní. Volitelně lze označit, že
je téma „zarezervováno" a komu (volný text). Z návrhu lze později založit
skutečnou vedenou práci (viz ``ThesisService.convert_proposal_to_thesis``).
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .enums import ThesisType


class ThesisProposal(BaseModel):
    """Jeden návrh tématu práce."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ThesisType = ThesisType.BP

    title_cs: str = ""
    description: str = ""        # popis tématu
    objectives: str = ""         # body zadání (volný text, 1 řádek = 1 bod)
    references: str = ""         # literatura (volný text)
    obor: str = ""               # studijní obor (volně, dle číselníku oborů)

    # Rezervace (téma si někdo „drží") — volný text, bez vazby na studenty.
    reserved: bool = False
    reserved_for: str = ""

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def touch(self) -> None:
        self.updated_at = datetime.now()
