"""Podklady pro výběr studenta — přehled studentů s jejich pracemi.

Jedna osoba může mít v evidenci víc záznamů (BP a DP mají ve STAGu různá osobní
čísla). Výběrový dialog proto u každého záznamu ukazuje osobní číslo, obor
a dosavadní práce, aby šlo záznamy rozlišit. Logika je tady (bez Qt), UI ji
jen zobrazuje.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from ..models import Student, Thesis
from ..models.enums import STATUSES_HISTORY, ThesisType
from .thesis_service import ThesisService


def fold(text: str | None) -> str:
    """Bez diakritiky a malými písmeny (``Žáček`` → ``zacek``) — pro hledání."""
    nfd = unicodedata.normalize("NFD", text or "")
    return "".join(c for c in nfd if not unicodedata.combining(c)).casefold()


@dataclass(frozen=True)
class StudentSummary:
    """Student + jeho vedené práce (seřazené od nejnovějšího roku)."""

    student: Student
    theses: tuple[Thesis, ...]

    @property
    def theses_label(self) -> str:
        """Krátký přehled prací, např. ``DP 2026/2027 Zájemce s tématem; BP …``."""
        return "; ".join(
            f"{t.type.value} {t.academic_year} {t.status.label}" for t in self.theses
        )

    @property
    def search_text(self) -> str:
        s = self.student
        return fold(" ".join(
            (s.full_name, s.last_name, s.university_id or "", s.obor, s.email or "")
        ))

    def matches(self, query: str) -> bool:
        """Všechna slova dotazu (bez diakritiky) se vyskytují v údajích studenta."""
        hay = self.search_text
        return all(tok in hay for tok in fold(query).split())


def _year_start(year: str) -> int:
    try:
        return int((year or "").split("/")[0])
    except ValueError:
        return 0


def student_summaries(service: ThesisService) -> list[StudentSummary]:
    """Všichni studenti s pracemi, řazeno podle příjmení, jména a os. čísla."""
    by_student: dict[str, list[Thesis]] = {}
    for t in service.list_theses():
        if t.student_id:
            by_student.setdefault(t.student_id, []).append(t)
    out = [
        StudentSummary(
            student=s,
            theses=tuple(sorted(
                by_student.get(s.id, ()),
                key=lambda t: (_year_start(t.academic_year), t.type.value),
                reverse=True,
            )),
        )
        for s in service.list_students()
    ]
    out.sort(key=lambda x: (fold(x.student.last_name), fold(x.student.first_name),
                            x.student.university_id or ""))
    return out


def filter_summaries(summaries: list[StudentSummary], query: str) -> list[StudentSummary]:
    if not query.strip():
        return list(summaries)
    return [s for s in summaries if s.matches(query)]


def same_name_count(summaries: list[StudentSummary], student: Student) -> int:
    """Kolik záznamů má stejné jméno (bez diakritiky) — vč. tohoto."""
    key = fold(student.full_name)
    return sum(1 for s in summaries if fold(s.student.full_name) == key)


def open_theses_of_type(
    service: ThesisService,
    student_id: str,
    thesis_type: ThesisType,
    *,
    exclude_id: str | None = None,
) -> list[Thesis]:
    """Neukončené práce (mimo Historii) daného typu u studenta.

    Slouží k upozornění „student už má rozpracovanou BP/DP" — typicky omylem
    zvolený BP záznam místo nového DP záznamu. Neblokuje uložení.
    """
    return [
        t for t in service.list_theses()
        if t.student_id == student_id
        and t.type == thesis_type
        and t.status not in STATUSES_HISTORY
        and t.id != exclude_id
    ]


def followup_student(source: Student) -> Student:
    """Nový záznam téže osoby pro navazující studium (BP → DP).

    Převezme jméno, e-mail a telefon; osobní číslo a obor zůstanou prázdné
    (ve STAGu jsou pro navazující studium jiné) a doplní je uživatel.
    """
    return Student(
        first_name=source.first_name,
        last_name=source.last_name,
        email=source.email,
        phone=source.phone,
    )
