from __future__ import annotations

from datetime import date

from ..models import Opponent, Student, Thesis
from ..models.enums import ALLOWED_TRANSITIONS, ThesisStatus
from ..storage import Database, Repository


class TransitionError(ValueError):
    """Pokud se pokoušíme o nepovolený přechod mezi stavy nebo chybí povinná pole."""


class ThesisService:
    """Hlavní fasáda nad úložištěm — drží konzistenci dat a vynucuje pravidla."""

    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        self._db: Database = repo.load()

    # --- načítání / ukládání -------------------------------------------------

    @property
    def db(self) -> Database:
        return self._db

    def reload(self) -> None:
        self._db = self._repo.load()

    def save(self) -> None:
        self._repo.save(self._db)

    # --- studenti ------------------------------------------------------------

    def list_students(self) -> list[Student]:
        return sorted(self._db.students, key=lambda s: (s.last_name.lower(), s.first_name.lower()))

    def get_student(self, student_id: str) -> Student | None:
        return next((s for s in self._db.students if s.id == student_id), None)

    def upsert_student(self, student: Student) -> Student:
        existing = self.get_student(student.id)
        if existing:
            idx = self._db.students.index(existing)
            self._db.students[idx] = student
        else:
            self._db.students.append(student)
        self.save()
        return student

    def delete_student(self, student_id: str) -> None:
        self._db.students = [s for s in self._db.students if s.id != student_id]
        for t in self._db.theses:
            if t.student_id == student_id:
                t.student_id = None
                t.touch()
        self.save()

    # --- oponenti ------------------------------------------------------------

    def list_opponents(self) -> list[Opponent]:
        return sorted(self._db.opponents, key=lambda o: o.name.lower())

    def get_opponent(self, opponent_id: str) -> Opponent | None:
        return next((o for o in self._db.opponents if o.id == opponent_id), None)

    def upsert_opponent(self, opponent: Opponent) -> Opponent:
        existing = self.get_opponent(opponent.id)
        if existing:
            idx = self._db.opponents.index(existing)
            self._db.opponents[idx] = opponent
        else:
            self._db.opponents.append(opponent)
        self.save()
        return opponent

    def delete_opponent(self, opponent_id: str) -> None:
        self._db.opponents = [o for o in self._db.opponents if o.id != opponent_id]
        for t in self._db.theses:
            if t.opponent_id == opponent_id:
                t.opponent_id = None
                t.touch()
        self.save()

    # --- obory ---------------------------------------------------------------

    def list_obory(self) -> list[str]:
        return sorted(self._db.obory)

    def add_obor(self, name: str) -> None:
        name = name.strip()
        if name and name not in self._db.obory:
            self._db.obory.append(name)
            self.save()

    # --- akademické roky -----------------------------------------------------

    def list_academic_years(self) -> list[str]:
        years = {t.academic_year for t in self._db.theses if t.academic_year}
        return sorted(years, reverse=True)

    @staticmethod
    def current_academic_year() -> str:
        today = date.today()
        start = today.year if today.month >= 9 else today.year - 1
        return f"{start}/{start + 1}"

    @staticmethod
    def next_academic_year() -> str:
        cur = ThesisService.current_academic_year()
        start = int(cur.split("/")[0]) + 1
        return f"{start}/{start + 1}"

    # --- práce ---------------------------------------------------------------

    def list_theses(self) -> list[Thesis]:
        return list(self._db.theses)

    def get_thesis(self, thesis_id: str) -> Thesis | None:
        return next((t for t in self._db.theses if t.id == thesis_id), None)

    def upsert_thesis(self, thesis: Thesis) -> Thesis:
        thesis.touch()
        existing = self.get_thesis(thesis.id)
        if existing:
            idx = self._db.theses.index(existing)
            self._db.theses[idx] = thesis
        else:
            self._db.theses.append(thesis)
        self.save()
        return thesis

    def delete_thesis(self, thesis_id: str) -> None:
        self._db.theses = [t for t in self._db.theses if t.id != thesis_id]
        self.save()

    def transition(self, thesis_id: str, target: ThesisStatus) -> Thesis:
        thesis = self.get_thesis(thesis_id)
        if thesis is None:
            raise TransitionError(f"Práce {thesis_id} neexistuje.")

        if thesis.status == target:
            return thesis

        allowed = ALLOWED_TRANSITIONS.get(thesis.status, set())
        if target not in allowed:
            raise TransitionError(
                f"Přechod {thesis.status.label} → {target.label} není povolen."
            )

        if target == ThesisStatus.LISTED:
            ok, missing = thesis.is_ready_for_listing()
            if not ok:
                raise TransitionError(
                    f"Pro vypsání tématu chybí: {', '.join(missing)}."
                )
        if target == ThesisStatus.ASSIGNED:
            ok, missing = thesis.is_ready_for_assignment()
            if not ok:
                raise TransitionError(
                    f"Pro oficiální zadání chybí: {', '.join(missing)}."
                )

        thesis.status = target
        thesis.touch()
        self.save()
        return thesis

    # --- pohledy -------------------------------------------------------------

    def theses_by_year_and_type(self) -> dict[str, dict[str, list[Thesis]]]:
        out: dict[str, dict[str, list[Thesis]]] = {}
        for t in self._db.theses:
            year = t.academic_year or "(bez roku)"
            out.setdefault(year, {"BP": [], "DP": []})
            out[year][t.type.value].append(t)
        return out
