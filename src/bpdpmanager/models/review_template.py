"""Šablona posudku (vedoucího / oponenta) — XLSX soubor s metadaty.

Šablona je registrována v knihovně profilu (``Database.review_templates``)
a fyzicky leží v ``profile_dir/templates/{filename}``. Filename obsahuje
ID šablony jako prefix pro robustní identifikaci i při manuální úpravě
souborů (uživatel může mít stejný název pro CZ + EN variantu).
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .enums import ThesisType


class TemplateCriterion(BaseModel):
    """Schema definice jednoho kritéria v šabloně.

    Schema je nascanováno z XLSX při prvním použití (viz
    ``services/review_schema.py``) a ulozeno v ``ReviewTemplate.criteria``.
    Slouží jako mapování pro ReviewEditorDialog (které řádky jsou
    kritéria a kde se zapisuje skóre).
    """

    row: int                # řádek v šabloně (např. 18)
    label: str              # popisek z col A
    default_weight: float   # váha z col C (např. 1.0 nebo 0.5)
    weight_cell: str        # např. "C18"
    score_cell: str         # např. "D18"


class ReviewTemplate(BaseModel):
    """Šablona posudku v knihovně profilu."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = ""  # Lidsky čitelný název, např. „Vedoucí BP — SWI (2025/2026)"
    type: ThesisType  # BP / DP
    role: str = "supervisor"  # ``"supervisor"`` (vedoucí) nebo ``"opponent"`` (oponent)
    language: str = "cs"  # ``"cs"`` nebo ``"en"``
    obor: str = ""  # volitelné — např. „SWI", „KYB", „UI" (typicky jen u DP)
    academic_year: str = ""  # volitelné — např. „2025/2026"
    # Filename relativně k ``profile_dir/templates/``. Kopie originálního XLSX.
    filename: str = ""
    note: str = ""
    created_at: datetime = Field(default_factory=datetime.now)

    # v4+ (0.19.0): cache schema kritérií nascanovaného z XLSX. Pokud je
    # prázdné, schema se znovu nascanuje při prvním použití šablony.
    criteria: list[TemplateCriterion] = Field(default_factory=list)
    # Volitelně: cell pro ostatní známé pole (assignment_fulfilled,
    # plagiarism_verdict, plagiarism_justification, overall_comment, place_date)
    field_cells: dict[str, str] = Field(default_factory=dict)

    @property
    def role_label(self) -> str:
        return "Vedoucí" if self.role == "supervisor" else "Oponent"

    @property
    def language_label(self) -> str:
        return {"cs": "CZ", "en": "EN"}.get(self.language, self.language.upper())

    @property
    def short_label(self) -> str:
        """Krátký popisek pro tabulky: ``BP · V · SWI · 2025/2026``."""
        parts = [self.type.value, self.role_label[0]]  # B/D + V/O
        if self.obor:
            parts.append(self.obor)
        if self.language != "cs":
            parts.append(self.language_label)
        if self.academic_year:
            parts.append(self.academic_year)
        return " · ".join(parts)
