"""Strukturovaná data posudku — zdroj pravdy pro XLSX/PDF výstupy.

Posudek (``Review``) je samostatná entita uvnitř ``Thesis.reviews`` /
``OpposingThesis.reviews``. Drží všechna data, která uživatel vyplnil
v editor dialogu (body za kritéria, komentáře, plagiátorství atd.).
Vygenerovaný XLSX a PDF jsou v ``documents/{thesis_id}/posudky/`` a v
``Thesis.attachments`` existují jako standardní ``Attachment`` záznamy
typu ``SUPERVISOR_REVIEW`` / ``OPPONENT_REVIEW`` — pro Posudky sloupec
v stromu prací a pro běžnou správu souborů.

Storage: JSON je atomický zdroj pravdy. XLSX a PDF lze kdykoli
regenerovat z JSON dat + šablony.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class CriterionScore(BaseModel):
    """Body za jedno kritérium hodnocení v rámci posudku.

    ``row`` a ``score_cell`` propagují identitu mezi XLSX šablonou
    a JSON daty — při regen znají přesně kam zapsat.
    """

    model_config = ConfigDict(extra="ignore")

    row: int                # řádek v šabloně (např. 18)
    label: str              # popisek kritéria (z col A)
    weight: float           # váha (z col C, např. 1.0 nebo 0.5)
    score: float = 0.0      # uživatelovo skóre 0–5
    weight_cell: str = ""   # např. "C18" (kde je váha)
    score_cell: str = ""    # např. "D18" (kde je skóre)


class Review(BaseModel):
    """Posudek vedoucího nebo oponenta — strukturovaná data.

    Identita: ``id`` (UUID). Asociace s konkrétní šablonou přes
    ``template_id``. Verzování přes ``version`` + ``is_current``
    (analogicky k ``Attachment``) — multiple verze pro 2. pokus
    obhajoby atd.
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid4()))
    template_id: str = ""           # ReviewTemplate.id (může být prázdné po smazání šablony)
    template_name: str = ""         # snapshot názvu šablony (pro UI po smazání šablony)

    role: str = "supervisor"        # "supervisor" / "opponent"
    language: str = "cs"            # "cs" / "en"

    # Základní pole (řádek 8–13 v typické FAI UTB šabloně)
    student_name: str = ""
    user_name: str = ""             # vedoucí/oponent (autor posudku)
    title_cs: str = ""
    title_en: str = ""
    academic_year: str = ""
    study_program: str = ""
    specialization: str = ""

    # Vyhodnocení
    assignment_fulfilled: str = "splnil(a)"   # ev. "nesplnil(a)" / "fulfilled" / "not fulfilled"
    criteria: list[CriterionScore] = Field(default_factory=list)

    # Plagiátorství (jen pro vedoucího)
    plagiarism_verdict: str = "Práce není plagiát"
    plagiarism_justification: str = ""

    # Volný text
    overall_comment: str = ""       # Celkové hodnocení, připomínky a dotazy
    place_date: str = ""            # např. "Zlín, 26. 5. 2026"

    # Generované soubory (relativní názvy v documents/{thesis_id}/posudky/)
    xlsx_filename: str = ""
    pdf_filename: str = ""

    # Verzování
    version: int = 1
    is_current: bool = True

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def touch(self) -> None:
        self.updated_at = datetime.now()

    @property
    def total_weighted_points(self) -> float:
        return sum(c.weight * c.score for c in self.criteria)

    @property
    def max_points(self) -> float:
        # Max = sum(weight) * 5  (každé kritérium max 5 bodů)
        return sum(c.weight for c in self.criteria) * 5.0

    @property
    def percentage(self) -> float:
        m = self.max_points
        return (self.total_weighted_points / m * 100.0) if m > 0 else 0.0

    @property
    def suggested_grade(self) -> str:
        """ECTS stupnice podle BP/DP — 1:1 se vzorcem v XLSX šablonách FAI UTB.

        BP (max 30): A≥29, B≥26, C≥23, D≥20, E≥18, jinak FX  (E≥18 = 60 %)
        DP (max 35): A≥33, B≥30, C≥27, D≥24, E≥21, jinak F   (E≥21 = 60 %)

        Hranice E je u obou na 60 % → cokoli pod 60 % je FX (BP) / F (DP).
        Pokud uživatel zvolil 'nesplnil(a)' / 'not fulfilled', vrátí FX/F.
        """
        afv = self.assignment_fulfilled.lower()
        is_dp = abs(self.max_points - 35.0) < 0.5  # rounding margin
        if "nespl" in afv or "not fulfilled" in afv:
            return "F" if is_dp else "FX"
        pts = self.total_weighted_points
        if is_dp:
            for threshold, grade in [(33, "A"), (30, "B"), (27, "C"), (24, "D"), (21, "E")]:
                if pts >= threshold:
                    return grade
            return "F"
        # BP
        for threshold, grade in [(29, "A"), (26, "B"), (23, "C"), (20, "D"), (18, "E")]:
            if pts >= threshold:
                return grade
        return "FX"
