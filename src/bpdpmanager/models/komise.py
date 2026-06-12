"""Komise SZZ — složení a rozpis studentů (z fakultních PDF).

Komise je identifikovaná **akademickým rokem, barvou a stupněm** (Bc/Mgr) —
fakulta komise značí barvami (červená, modrá, žlutá, zelená, fialová, …).
Složení (role + jména) pochází z PDF „Složení komisí SZZ", rozpis studentů
(datum, čas, osobní číslo, jméno) z PDF „Rozpis studentů" — tam je barva
komise daná **barvou nadpisů** stránky.
"""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field

#: Zobrazované barvy komisí → hex pro badge v UI (světlé/tmavé téma řeší text).
COMMITTEE_COLORS: dict[str, str] = {
    "červená": "#e53935",
    "modrá": "#1e88e5",
    "zelená": "#7cb342",
    "žlutá": "#fbc02d",
    "fialová": "#8e24aa",
    "oranžová": "#fb8c00",
    "růžová": "#ec407a",
    "tyrkysová": "#00897b",
    "hnědá": "#8d6e63",
    "šedá": "#757575",
}


def committee_color_hex(name: str) -> str:
    return COMMITTEE_COLORS.get((name or "").strip().lower(), "#757575")


class CommitteeMember(BaseModel):
    """Člen komise: role (Předseda/Místopředseda/Tajemník/Člen) + jméno."""

    role: str = "Člen"
    name: str = ""


class DefenseSlot(BaseModel):
    """Jeden slot rozpisu: kdy jde který student.

    ``personal_number`` (Axxxxx) slouží k přesnému spárování se studentem
    v databázi (zvýraznění vedených); jméno k párování oponovaných (inline).
    """

    date: str = ""             # "15. 6. 2026" (jak je v PDF)
    time: str = ""             # "09:00"
    personal_number: str = ""  # "A23625"
    student_name: str = ""     # "Marko Adámek" (bez titulů se nečistí)


class Committee(BaseModel):
    """Komise SZZ pro jeden akademický rok (složení + rozpis)."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    academic_year: str = ""    # "2025/2026"
    color: str = ""            # "červená" (lowercase)
    level: str = ""            # "Bc" / "Mgr" / ""
    program_label: str = ""    # "SWI, SWE" / "Informační technologie — SWI"
    dates: list[str] = Field(default_factory=list)   # ["15. 6. 2026", …]
    members: list[CommitteeMember] = Field(default_factory=list)
    slots: list[DefenseSlot] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)  # rel. cesty v komise/
    note: str = ""

    @property
    def color_hex(self) -> str:
        return committee_color_hex(self.color)

    @property
    def display_name(self) -> str:
        parts = [f"Komise {self.color}" if self.color else "Komise"]
        if self.program_label:
            parts.append(f"— {self.program_label}")
        if self.level:
            parts.append(f"({self.level})")
        return " ".join(parts)
