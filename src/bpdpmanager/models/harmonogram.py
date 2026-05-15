from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class KeyDateCategory(str, Enum):
    """Kategorie pro filtrování a vizualizaci."""

    THESIS = "thesis"        # SZZ, odevzdání BP/DP, promoce
    SEMESTER = "semester"    # zimní/letní semestr, výuka
    EXAM = "exam"            # zkouškové období, mezní termíny zápočtů
    ENROLLMENT = "enrollment"  # předzápisy, imatrikulace
    HOLIDAY = "holiday"      # prázdniny, státní svátky
    ADMISSIONS = "admissions"  # přijímací řízení
    OTHER = "other"

    @property
    def label(self) -> str:
        return CATEGORY_LABELS[self]

    @property
    def color(self) -> str:
        return CATEGORY_COLORS[self]


CATEGORY_LABELS: dict[KeyDateCategory, str] = {
    KeyDateCategory.THESIS: "BP/DP a SZZ",
    KeyDateCategory.SEMESTER: "Semestr / výuka",
    KeyDateCategory.EXAM: "Zkouškové období",
    KeyDateCategory.ENROLLMENT: "Zápis",
    KeyDateCategory.HOLIDAY: "Prázdniny / svátky",
    KeyDateCategory.ADMISSIONS: "Přijímací řízení",
    KeyDateCategory.OTHER: "Ostatní",
}

CATEGORY_COLORS: dict[KeyDateCategory, str] = {
    KeyDateCategory.THESIS: "#d32f2f",
    KeyDateCategory.SEMESTER: "#1976d2",
    KeyDateCategory.EXAM: "#7b1fa2",
    KeyDateCategory.ENROLLMENT: "#0288d1",
    KeyDateCategory.HOLIDAY: "#388e3c",
    KeyDateCategory.ADMISSIONS: "#f57c00",
    KeyDateCategory.OTHER: "#616161",
}


class KeyDate(BaseModel):
    """Záznam v časovém plánu — buď konkrétní datum, interval, nebo fuzzy popis."""

    date_start: date | None = None
    date_end: date | None = None
    fuzzy_label: str | None = None  # např. "květen-červen 2027", "Září 2026"
    description: str
    category: KeyDateCategory = KeyDateCategory.OTHER
    important: bool = False
    source: str = "manual"  # "manual" | "imported"

    @property
    def is_range(self) -> bool:
        return self.date_end is not None and self.date_start is not None and self.date_end != self.date_start

    def display_date(self) -> str:
        if self.fuzzy_label and not self.date_start:
            return self.fuzzy_label
        if self.date_start and self.date_end and self.date_end != self.date_start:
            return f"{self.date_start.strftime('%d.%m.%Y')} – {self.date_end.strftime('%d.%m.%Y')}"
        if self.date_start:
            return self.date_start.strftime("%d.%m.%Y")
        return "—"

    def sort_key(self) -> date:
        """Pro řazení: konkrétní datum nebo dnešek + 365 dní pro fuzzy bez data."""
        return self.date_start or date.max


class AcademicYearInfo(BaseModel):
    """Záznam jednoho akademického roku s harmonogramem."""

    label: str  # "2026/2027"
    pdf_filename: str | None = None  # název souboru v ~/.bpdpmanager/harmonograms/
    pdf_source_path: str | None = None  # původní cesta (informativně)
    key_dates: list[KeyDate] = Field(default_factory=list)
    note: str = ""

    def upcoming(self, from_date: date, days: int = 60) -> list[KeyDate]:
        """Vrátí key dates začínající v rozmezí [from_date, from_date + days]."""
        from datetime import timedelta
        end = from_date + timedelta(days=days)
        return sorted(
            [
                kd
                for kd in self.key_dates
                if kd.date_start and from_date <= kd.date_start <= end
            ],
            key=lambda kd: kd.sort_key(),
        )
