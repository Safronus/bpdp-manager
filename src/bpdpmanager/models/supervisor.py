"""Vedoucí cizí BP/DP — registr pro oponentské posudky.

Uchovávají se odděleně od ``Opponent`` (i když v praxi to může být tatáž
osoba v jiné roli). Důvod: vedoucí jsou *cizí* osoby na cizích pracích,
zatímco oponenti jsou *moji* spolupracovníci na *mnou vedených* pracích.
Oddělená správa je přehlednější.
"""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Supervisor(BaseModel):
    """Vedoucí cizí BP/DP — používá se v oponentských posudcích."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    email: str | None = None
    affiliation: str | None = None  # např. "FAI UTB", "FAV ZČU", "ČVUT FEL"
    phone: str | None = None
    note: str | None = None

    @property
    def display_label(self) -> str:
        suffix = f" ({self.affiliation})" if self.affiliation else ""
        return f"{self.name}{suffix}"
