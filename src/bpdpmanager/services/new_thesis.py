"""Založení nové práce — nabídka stavů a roků, výchozí hodnoty, kontroly.

Jeden dialog „Nová práce" nahrazuje dřívější tři (Nová práce / Zájemce /
Minulá práce). Pravidla jsou tady (bez Qt), dialog je jen zobrazuje:

- stav vybíraný v dialogu, výchozí podle aktivní záložky,
- nabídka roků podle stavu (budoucí: letošní + 2 další; V řešení: letošní
  a minulé; ukončené: minulé a letošní),
- výchozí rok budoucích stavů podle měsíce (září až prosinec letošní, jinak příští),
- nepovinná upozornění ke zvolenému studentovi (neblokují uložení).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from ..models import AcademicYear, Thesis
from ..models.enums import (
    STATUSES_CURRENT,
    STATUSES_FUTURE,
    ThesisStatus,
    ThesisType,
)
from .student_lookup import open_theses_of_type
from .thesis_service import ThesisService

# Nejstarší rok v nabídce (shodně s detailem práce).
FIRST_YEAR_START = 2009

# Nabídka stavů v dialogu (pořadí = tok práce); založit lze v libovolném stavu.
CREATABLE_STATUSES: tuple[ThesisStatus, ...] = (
    ThesisStatus.INTERESTED,
    ThesisStatus.RESERVED,
    ThesisStatus.LISTED,
    ThesisStatus.IN_PROGRESS,
    ThesisStatus.DEFENDED,
    ThesisStatus.FAILED,
    ThesisStatus.SUBMITTED_NO_DEFENSE,
    ThesisStatus.CANCELLED,
)


class TabKind(StrEnum):
    """Záložka, ze které se dialog otevřel (určuje výchozí stav a rok)."""

    CURRENT = "current"
    FUTURE = "future"
    HISTORY = "history"
    OTHER = "other"


def _year_start(today: date | None) -> int:
    today = today or date.today()
    return today.year if today.month >= 9 else today.year - 1


def _label(start: int) -> str:
    return f"{start}/{start + 1}"


def year_choices(status: ThesisStatus, today: date | None = None) -> list[str]:
    """Nabídka akademických roků pro daný stav."""
    s = _year_start(today)
    if status in STATUSES_FUTURE:
        return [_label(s), _label(s + 1), _label(s + 2)]
    # V řešení i ukončené: letošní a minulé (sestupně) — i prodloužené práce
    # a letošní hotové (např. zimní obhajoby).
    return [_label(y) for y in range(s, FIRST_YEAR_START - 1, -1)]


def default_year(status: ThesisStatus, today: date | None = None) -> str:
    """Výchozí rok: budoucí stavy podle měsíce, V řešení letošní, ukončené minulý."""
    today = today or date.today()
    s = _year_start(today)
    if status in STATUSES_FUTURE:
        # Září až prosinec: témata se vypisují/schvalují pro běžící rok;
        # leden až srpen: už pro příští.
        return _label(s if today.month >= 9 else s + 1)
    if status in STATUSES_CURRENT:
        return _label(s)
    return _label(s - 1)


def tab_default_status(tab: TabKind) -> ThesisStatus:
    return {
        TabKind.CURRENT: ThesisStatus.IN_PROGRESS,
        TabKind.HISTORY: ThesisStatus.DEFENDED,
    }.get(tab, ThesisStatus.LISTED)


class WarningKind(StrEnum):
    OPEN_SAME_TYPE = "open_same_type"      # už má neukončenou práci stejného typu
    BP_RECORD_FOR_DP = "bp_record_for_dp"  # DP na záznam s BP (asi staré os. číslo)


@dataclass(frozen=True)
class StudentWarning:
    kind: WarningKind
    theses: tuple[Thesis, ...]


def student_warnings(
    service: ThesisService, student_id: str | None, thesis_type: ThesisType
) -> list[StudentWarning]:
    """Upozornění ke zvolenému studentovi (nic neblokuje)."""
    if not student_id:
        return []
    out: list[StudentWarning] = []
    open_same = open_theses_of_type(service, student_id, thesis_type)
    if open_same:
        out.append(StudentWarning(WarningKind.OPEN_SAME_TYPE, tuple(open_same)))
    if thesis_type == ThesisType.DP:
        bps = tuple(t for t in service.list_theses()
                    if t.student_id == student_id and t.type == ThesisType.BP)
        if bps:
            out.append(StudentWarning(WarningKind.BP_RECORD_FOR_DP, bps))
    return out


class NewThesisError(ValueError):
    """Neplatné vstupy pro novou práci (zpráva je pro uživatele)."""


def create_thesis(
    service: ThesisService,
    *,
    thesis_type: ThesisType,
    status: ThesisStatus,
    academic_year: str,
    student_id: str | None = None,
    obor: str = "",
    title: str = "",
    annotation: str = "",
) -> Thesis:
    """Založí a uloží práci. Obor se uloží ke studentovi (jen je-li zvolen)."""
    try:
        year = AcademicYear(label=academic_year).label
    except ValueError as exc:
        raise NewThesisError(
            f"Akademický rok musí být ve tvaru RRRR/RRRR, dostal: {academic_year!r}"
        ) from exc
    student = service.get_student(student_id) if student_id else None
    if student_id and student is None:
        raise NewThesisError("Zvolený student už v evidenci není.")

    thesis = Thesis(type=thesis_type, status=status, academic_year=year)
    thesis.title_cs = title.strip()
    thesis.annotation = annotation.strip()
    with service.batch():
        if student is not None:
            thesis.student_id = student.id
            obor = obor.strip()
            if obor and (student.obor or "") != obor:
                student.obor = obor
                service.upsert_student(student)
        service.upsert_thesis(thesis)
    return thesis

