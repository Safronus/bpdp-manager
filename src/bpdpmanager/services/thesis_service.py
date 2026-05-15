from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from ..config import harmonograms_dir, thesis_documents_dir
from ..models import (
    AcademicYearInfo,
    Attachment,
    KeyDate,
    Opponent,
    Student,
    Thesis,
)
from ..models.enums import ALLOWED_TRANSITIONS, AttachmentKind, OpponentKind, ThesisStatus
from ..storage import Database, Repository
from .harmonogram_parser import parse_pdf


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

    def list_opponents(self, kind: OpponentKind | None = None) -> list[Opponent]:
        opps = self._db.opponents
        if kind is not None:
            opps = [o for o in opps if o.kind == kind]
        return sorted(opps, key=lambda o: o.name.lower())

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

    def rename_obor(self, old_name: str, new_name: str) -> int:
        """Přejmenuje obor v číselníku a u všech studentů s tímto oborem.

        Vrací počet aktualizovaných studentů.
        """
        new_name = new_name.strip()
        if not new_name or old_name == new_name:
            return 0
        if old_name in self._db.obory:
            self._db.obory[self._db.obory.index(old_name)] = new_name
        # dedup pro případ, že nový název už existoval
        self._db.obory = list(dict.fromkeys(self._db.obory))
        count = 0
        for student in self._db.students:
            if student.obor == old_name:
                student.obor = new_name
                count += 1
        self.save()
        return count

    def remove_obor(self, name: str) -> int:
        """Smaže obor z číselníku. Studentům s tímto oborem ho vyprázdní.

        Vrací počet ovlivněných studentů.
        """
        if name in self._db.obory:
            self._db.obory.remove(name)
        count = 0
        for student in self._db.students:
            if student.obor == name:
                student.obor = ""
                count += 1
        self.save()
        return count

    def obor_usage_count(self, name: str) -> int:
        return sum(1 for s in self._db.students if s.obor == name)

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

    # --- harmonogram ---------------------------------------------------------

    def get_year_info(self, label: str) -> AcademicYearInfo | None:
        return next((y for y in self._db.academic_years if y.label == label), None)

    def get_or_create_year_info(self, label: str) -> AcademicYearInfo:
        info = self.get_year_info(label)
        if info is None:
            info = AcademicYearInfo(label=label)
            self._db.academic_years.append(info)
            self.save()
        return info

    def list_year_infos(self) -> list[AcademicYearInfo]:
        return sorted(self._db.academic_years, key=lambda y: y.label, reverse=True)

    def upsert_year_info(self, info: AcademicYearInfo) -> AcademicYearInfo:
        existing = self.get_year_info(info.label)
        if existing:
            idx = self._db.academic_years.index(existing)
            self._db.academic_years[idx] = info
        else:
            self._db.academic_years.append(info)
        self.save()
        return info

    def import_harmonogram_pdf(self, label: str, source_pdf: Path) -> AcademicYearInfo:
        """Importuje PDF harmonogramu pro daný akademický rok.

        - Zkopíruje PDF do ``~/.bpdpmanager/harmonograms/{label}.pdf``
        - Spustí parser a uloží extrahované klíčové termíny
        """
        info = self.get_or_create_year_info(label)
        target_name = label.replace("/", "-") + ".pdf"
        target_path = harmonograms_dir() / target_name
        shutil.copy2(source_pdf, target_path)

        info.pdf_filename = target_name
        info.pdf_source_path = str(source_pdf)

        parsed = parse_pdf(target_path)
        # zachovej manuálně přidané, nahraď jen ty importované
        manual = [kd for kd in info.key_dates if kd.source == "manual"]
        info.key_dates = manual + parsed

        return self.upsert_year_info(info)

    def add_key_date(self, year_label: str, key_date: KeyDate) -> AcademicYearInfo:
        info = self.get_or_create_year_info(year_label)
        info.key_dates.append(key_date)
        return self.upsert_year_info(info)

    def update_key_date(self, year_label: str, index: int, key_date: KeyDate) -> AcademicYearInfo:
        info = self.get_or_create_year_info(year_label)
        if 0 <= index < len(info.key_dates):
            info.key_dates[index] = key_date
        return self.upsert_year_info(info)

    def remove_key_date(self, year_label: str, index: int) -> AcademicYearInfo:
        info = self.get_or_create_year_info(year_label)
        if 0 <= index < len(info.key_dates):
            del info.key_dates[index]
        return self.upsert_year_info(info)

    # --- dokumenty k práci ---------------------------------------------------

    def attach_document(
        self,
        thesis_id: str,
        source_path: Path,
        kind: AttachmentKind = AttachmentKind.OTHER,
        label: str | None = None,
    ) -> Attachment:
        """Nahraje soubor do ~/.bpdpmanager/documents/{thesis_id}/ a přidá ho k práci."""
        thesis = self.get_thesis(thesis_id)
        if thesis is None:
            raise ValueError(f"Práce {thesis_id} neexistuje.")

        target_dir = thesis_documents_dir(thesis_id)
        target_name = source_path.name
        target_path = target_dir / target_name
        if target_path.exists():
            # přidej suffix _2, _3, … aby se nepřepisovalo
            stem, suffix = target_path.stem, target_path.suffix
            i = 2
            while target_path.exists():
                target_path = target_dir / f"{stem}_{i}{suffix}"
                i += 1
        shutil.copy2(source_path, target_path)

        attachment = Attachment(
            label=label or target_path.name,
            url_or_path=target_path.name,
            kind=kind,
            is_file=True,
        )
        thesis.attachments.append(attachment)
        self.upsert_thesis(thesis)
        return attachment

    def remove_document(self, thesis_id: str, index: int, delete_file: bool = False) -> None:
        thesis = self.get_thesis(thesis_id)
        if thesis is None or not (0 <= index < len(thesis.attachments)):
            return
        attachment = thesis.attachments[index]
        if delete_file and attachment.is_file:
            target = thesis_documents_dir(thesis_id) / attachment.url_or_path
            if target.exists():
                target.unlink()
        del thesis.attachments[index]
        self.upsert_thesis(thesis)

    def document_absolute_path(self, thesis_id: str, attachment: Attachment) -> Path | None:
        if not attachment.is_file:
            return None
        return thesis_documents_dir(thesis_id) / attachment.url_or_path

    # --- harmonogram napříč roky --------------------------------------------

    def upcoming_dates_all_years(self, from_date: date, days: int = 60) -> list[tuple[str, KeyDate]]:
        """Vrátí důležité nadcházející termíny napříč všemi roky."""
        out: list[tuple[str, KeyDate]] = []
        for info in self._db.academic_years:
            for kd in info.upcoming(from_date, days):
                out.append((info.label, kd))
        return sorted(out, key=lambda x: x[1].sort_key())
