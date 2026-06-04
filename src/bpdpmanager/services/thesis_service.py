from __future__ import annotations

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from ..config import harmonograms_dir, thesis_documents_dir
from ..models import (
    AcademicYearInfo,
    Attachment,
    KeyDate,
    Obor,
    Opponent,
    OpposingThesis,
    Student,
    Supervisor,
    Thesis,
)
from ..models.enums import ALLOWED_TRANSITIONS, AttachmentKind, OpponentKind, ThesisStatus
from ..storage import Database, Repository
from .file_naming import (
    build_plagiarism_name,
    build_target_name,
    subdir_for,
)
from .harmonogram_parser import parse_pdf


class TransitionError(ValueError):
    """Pokud se pokoušíme o nepovolený přechod mezi stavy nebo chybí povinná pole."""


class ThesisService:
    """Hlavní fasáda nad úložištěm — drží konzistenci dat a vynucuje pravidla."""

    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        self._db: Database = repo.load()
        # Hloubka aktivní transakce. Když > 0, ``save()`` se odkládá až na konec
        # nejvyšší úrovně. Při výjimce uvnitř ``batch()`` se ``_db`` znovu načte
        # z disku — všechny rozdělané změny jsou zahozeny.
        self._batch_depth: int = 0

    # --- načítání / ukládání -------------------------------------------------

    @property
    def db(self) -> Database:
        return self._db

    def reload(self) -> None:
        self._db = self._repo.load()

    def reset(self, repo: Repository) -> None:
        """Nahradí podkladový repozitář a načte data z něj.

        Používá se při přepnutí na jiný profil — bez nutnosti vytvářet
        nový ThesisService a přemontovávat UI.
        """
        self._repo = repo
        self._db = repo.load()

    def save(self) -> None:
        """Persist ``_db`` na disk. V rámci ``batch()`` se zápis odkládá."""
        if self._batch_depth > 0:
            return  # odložit; reálné save proběhne na konci batche
        self._repo.save(self._db)

    @contextmanager
    def batch(self) -> Iterator[None]:
        """Transakční blok — všechny ``upsert_*`` / ``delete_*`` uvnitř
        nepíšou na disk. Save proběhne až na konci, atomicky.

        Při výjimce uvnitř se ``_db`` znovu načte z disku → všechny změny
        provedené v rámci tohoto bloku se zahodí (rollback).

        Pozor: copy souborů (``attach_document`` apod.) je *durable* —
        soubory zůstanou na disku i po rollbacku, ale bez záznamu v ``_db``
        se z hlediska aplikace stávají neviditelnými („orphan files").
        Mazání orphanu je out-of-scope této transakce.
        """
        self._batch_depth += 1
        try:
            yield
        except Exception:
            self._batch_depth -= 1
            if self._batch_depth == 0:
                # Zahoď in-memory změny, vrať na poslední uložený stav
                self._db = self._repo.load()
            raise
        else:
            self._batch_depth -= 1
            if self._batch_depth == 0:
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

    # --- vedoucí (pro oponentské posudky) -----------------------------------

    def list_supervisors(self) -> list[Supervisor]:
        return sorted(self._db.supervisors, key=lambda s: s.name.lower())

    def get_supervisor(self, supervisor_id: str) -> Supervisor | None:
        return next(
            (s for s in self._db.supervisors if s.id == supervisor_id), None
        )

    def get_supervisor_by_name(self, name: str) -> Supervisor | None:
        """Najde vedoucího podle přesné shody jména (case-sensitive)."""
        if not name:
            return None
        return next(
            (s for s in self._db.supervisors if s.name == name), None
        )

    def upsert_supervisor(self, supervisor: Supervisor) -> Supervisor:
        existing = self.get_supervisor(supervisor.id)
        if existing:
            idx = self._db.supervisors.index(existing)
            self._db.supervisors[idx] = supervisor
        else:
            self._db.supervisors.append(supervisor)
        self.save()
        return supervisor

    def delete_supervisor(self, supervisor_id: str) -> None:
        """Smaže vedoucího z registry. Inline údaje v oponentských posudcích
        zůstávají (jsou kopií, ne FK)."""
        self._db.supervisors = [
            s for s in self._db.supervisors if s.id != supervisor_id
        ]
        self.save()

    # --- obory ---------------------------------------------------------------

    def list_obory(self) -> list[str]:
        """Vrátí seznam názvů oborů — pro plnění combo boxů (backward compat)."""
        return sorted(o.name for o in self._db.obory)

    def list_obor_objects(self) -> list[Obor]:
        """Vrátí seznam Obor objektů (včetně kontaktu na sekretářku)."""
        return sorted(self._db.obory, key=lambda o: o.name.lower())

    def get_obor(self, name: str) -> Obor | None:
        return next((o for o in self._db.obory if o.name == name), None)

    def get_obor_by_stag_code(self, stag_code: str) -> Obor | None:
        if not stag_code:
            return None
        return next(
            (o for o in self._db.obory if (o.stag_code or "") == stag_code), None
        )

    def add_obor(self, name: str) -> Obor | None:
        """Přidá obor (pokud neexistuje). Vrací příslušný Obor."""
        name = name.strip()
        if not name:
            return None
        existing = self.get_obor(name)
        if existing:
            return existing
        obor = Obor(name=name)
        self._db.obory.append(obor)
        self.save()
        return obor

    def upsert_obor(self, obor: Obor) -> Obor:
        """Vloží nebo aktualizuje obor (klíč = ``name``)."""
        existing = self.get_obor(obor.name)
        if existing:
            idx = self._db.obory.index(existing)
            self._db.obory[idx] = obor
        else:
            self._db.obory.append(obor)
        self.save()
        return obor

    def rename_obor(self, old_name: str, new_name: str) -> int:
        """Přejmenuje obor v číselníku a u všech studentů s tímto oborem.

        Vrací počet aktualizovaných studentů.
        """
        new_name = new_name.strip()
        if not new_name or old_name == new_name:
            return 0
        old_obor = self.get_obor(old_name)
        target = self.get_obor(new_name)
        if old_obor is not None:
            if target is not None and target is not old_obor:
                # cíl už existuje — sloučení: starý zahodíme, ponecháme target
                self._db.obory = [o for o in self._db.obory if o is not old_obor]
            else:
                old_obor.name = new_name
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
        self._db.obory = [o for o in self._db.obory if o.name != name]
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

    @staticmethod
    def previous_academic_year() -> str:
        cur = ThesisService.current_academic_year()
        start = int(cur.split("/")[0]) - 1
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

    def rollback_thesis(self, thesis_id: str) -> dict[str, int]:
        """Kompletně smaže práci z DB **i** všechny její soubory na disku.

        Použití: oprava chybného importu, omyl při zakládání, ...
        Studenta/oponenta v registru nemažeme — mohou být provázáni s jinými
        pracemi a tady nemáme dost kontextu na rozhodnutí.

        Vrací statistiky: ``{"files_deleted": N, "plagiarism_pdf": 0|1,
        "documents_dir_removed": 0|1}``.
        """
        thesis = self.get_thesis(thesis_id)
        if thesis is None:
            return {"files_deleted": 0, "plagiarism_pdf": 0, "documents_dir_removed": 0}

        stats = {"files_deleted": 0, "plagiarism_pdf": 0, "documents_dir_removed": 0}
        docs_dir = thesis_documents_dir(thesis_id)

        # 1) Smaž každý záznam přílohy explicitně (kvůli statistice). Adresář
        #    poté smažeme rekurzivně — chytí i orphan soubory bez záznamu.
        for att in list(thesis.attachments):
            try:
                p = docs_dir / att.url_or_path
                if p.is_file():
                    p.unlink()
                    stats["files_deleted"] += 1
            except OSError:
                pass

        # 2) Plagiátorský PDF protokol
        if thesis.plagiarism_pdf_filename:
            try:
                p = docs_dir / thesis.plagiarism_pdf_filename
                if p.is_file():
                    p.unlink()
                    stats["plagiarism_pdf"] = 1
            except OSError:
                pass

        # 3) Smaž celou složku ``documents/{id}/`` rekurzivně (chytí orphany)
        try:
            if docs_dir.exists():
                shutil.rmtree(docs_dir, ignore_errors=True)
                stats["documents_dir_removed"] = 1
        except OSError:
            pass

        # 4) Vyřaď z DB
        self._db.theses = [t for t in self._db.theses if t.id != thesis_id]
        self.save()
        return stats

    def rollback_opposing_thesis(self, op_id: str) -> dict[str, int]:
        """Analog ``rollback_thesis`` pro oponentský posudek."""
        op = self.get_opposing_thesis(op_id)
        if op is None:
            return {"files_deleted": 0, "documents_dir_removed": 0}

        stats = {"files_deleted": 0, "documents_dir_removed": 0}
        docs_dir = thesis_documents_dir(f"opposing-{op_id}")

        for att in list(op.attachments):
            try:
                p = docs_dir / att.url_or_path
                if p.is_file():
                    p.unlink()
                    stats["files_deleted"] += 1
            except OSError:
                pass

        try:
            if docs_dir.exists():
                shutil.rmtree(docs_dir, ignore_errors=True)
                stats["documents_dir_removed"] = 1
        except OSError:
            pass

        self._db.opposing_theses = [
            t for t in self._db.opposing_theses if t.id != op_id
        ]
        self.save()
        return stats

    def rollback_preview(self, thesis_id: str) -> dict:
        """Spočítá, co by ``rollback_thesis`` smazalo — pro confirmation dialog.

        Vrací: ``{"thesis": Thesis, "attachments": [(label, path, exists)],
        "plagiarism_pdf": (filename, exists) | None, "extra_files": [path],
        "total_bytes": int}``.
        """
        thesis = self.get_thesis(thesis_id)
        if thesis is None:
            return {"thesis": None, "attachments": [], "plagiarism_pdf": None,
                    "extra_files": [], "total_bytes": 0}

        docs_dir = thesis_documents_dir(thesis_id)
        atts: list[tuple[str, Path, bool, int]] = []
        tracked_paths: set[Path] = set()
        for att in thesis.attachments:
            p = docs_dir / att.url_or_path
            size = p.stat().st_size if p.is_file() else 0
            atts.append((att.label or att.url_or_path, p, p.is_file(), size))
            tracked_paths.add(p.resolve())

        plagiarism = None
        if thesis.plagiarism_pdf_filename:
            p = docs_dir / thesis.plagiarism_pdf_filename
            plagiarism = (thesis.plagiarism_pdf_filename, p, p.is_file(),
                          p.stat().st_size if p.is_file() else 0)
            tracked_paths.add(p.resolve())

        # Orphan soubory ve složce — vše ostatní co tam je
        extra: list[tuple[Path, int]] = []
        if docs_dir.exists():
            for p in docs_dir.rglob("*"):
                if p.is_file() and p.resolve() not in tracked_paths:
                    extra.append((p, p.stat().st_size))

        total = (
            sum(s for _, _, _, s in atts)
            + (plagiarism[3] if plagiarism else 0)
            + sum(s for _, s in extra)
        )
        return {
            "thesis": thesis,
            "attachments": atts,
            "plagiarism_pdf": plagiarism,
            "extra_files": extra,
            "total_bytes": total,
            "documents_dir": docs_dir,
        }

    def rollback_opposing_preview(self, op_id: str) -> dict:
        """Preview pro ``rollback_opposing_thesis``."""
        op = self.get_opposing_thesis(op_id)
        if op is None:
            return {"opposing": None, "attachments": [], "extra_files": [], "total_bytes": 0}

        docs_dir = thesis_documents_dir(f"opposing-{op_id}")
        atts: list[tuple[str, Path, bool, int]] = []
        tracked_paths: set[Path] = set()
        for att in op.attachments:
            p = docs_dir / att.url_or_path
            size = p.stat().st_size if p.is_file() else 0
            atts.append((att.label or att.url_or_path, p, p.is_file(), size))
            tracked_paths.add(p.resolve())

        extra: list[tuple[Path, int]] = []
        if docs_dir.exists():
            for p in docs_dir.rglob("*"):
                if p.is_file() and p.resolve() not in tracked_paths:
                    extra.append((p, p.stat().st_size))

        total = sum(s for _, _, _, s in atts) + sum(s for _, s in extra)
        return {
            "opposing": op,
            "attachments": atts,
            "extra_files": extra,
            "total_bytes": total,
            "documents_dir": docs_dir,
        }

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
        if target == ThesisStatus.IN_PROGRESS:
            # Vstup do V řešení (= dřívější ASSIGNED + IN_PROGRESS) vyžaduje
            # úplné oficiální zadání (titul EN, body zadání, literatura).
            # Výjimka: druhý pokus obhajoby (CANCELLED → IN_PROGRESS) —
            # tam už zadání jednou bylo, neblokujeme.
            if thesis.status != ThesisStatus.CANCELLED:
                ok, missing = thesis.is_ready_for_assignment()
                if not ok:
                    raise TransitionError(
                        f"Pro spuštění práce chybí: {', '.join(missing)}."
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
        """Nahraje soubor do ``~/.bpdpmanager/documents/{thesis_id}/{podsložka}/``.

        Cílový název se generuje podle schématu
        ``{Příjmení}_{typ}_{YYYY-MM-DD}[_vN].{ext}`` (viz ``file_naming``).
        Pokud práce nemá přiřazeného studenta, použije se fallback ``Bez-prijmeni``.
        """
        thesis = self.get_thesis(thesis_id)
        if thesis is None:
            raise ValueError(f"Práce {thesis_id} neexistuje.")

        surname = self._student_surname_for_thesis(thesis)
        subdir = subdir_for(kind)
        target_dir = thesis_documents_dir(thesis_id) / subdir
        target_dir.mkdir(parents=True, exist_ok=True)

        existing = {p.name for p in target_dir.iterdir() if p.is_file()}
        target_name = build_target_name(surname, kind, source_path, existing_names=existing)
        target_path = target_dir / target_name
        shutil.copy2(source_path, target_path)

        # ``url_or_path`` ukládáme jako relativní cestu vč. podsložky, aby
        # ``document_absolute_path`` fungovala beze změny pro nové i starší záznamy
        # (starší byly v rootu ``documents/{thesis_id}/``, tj. bez podadresáře).
        rel_path = f"{subdir}/{target_name}"

        # Verzování: nová příloha téhož ``kind`` přepne stávající current
        # (is_current=True) na False a stane se aktuální v rámci kindu.
        # Version se inkrementuje od max(existing of same kind).
        same_kind = [a for a in thesis.attachments if a.kind == kind]
        next_version = max((a.version for a in same_kind), default=0) + 1
        for a in same_kind:
            a.is_current = False

        attachment = Attachment(
            label=label or target_name,
            url_or_path=rel_path,
            kind=kind,
            is_file=True,
            version=next_version,
            is_current=True,
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

    def _student_surname_for_thesis(self, thesis: Thesis) -> str | None:
        """Pomocná funkce — dohledá příjmení studenta navázaného na práci.

        Vrací ``None``, pokud práce nemá studenta nebo student neexistuje
        (``build_target_name`` si pak zařídí fallback).
        """
        if not thesis.student_id:
            return None
        student = self.get_student(thesis.student_id)
        return student.last_name if student else None

    # --- plagiátorství ------------------------------------------------------

    def set_plagiarism_pdf(self, thesis_id: str, source_path: Path) -> str:
        """Zkopíruje PDF s výsledkem plagiátorství do ``plagiat/`` podsložky.

        Uložené ``plagiarism_pdf_filename`` je relativní cesta vč. podadresáře
        (``plagiat/Příjmení_protokol-plagiat_YYYY-MM-DD.pdf``), takže
        ``plagiarism_pdf_path`` funguje stejně pro staré (flat) i nové záznamy.
        """
        from .file_naming import PLAGIARISM_SUBDIR

        thesis = self.get_thesis(thesis_id)
        if thesis is None:
            raise ValueError(f"Práce {thesis_id} neexistuje.")

        surname = self._student_surname_for_thesis(thesis)
        target_dir = thesis_documents_dir(thesis_id) / PLAGIARISM_SUBDIR
        target_dir.mkdir(parents=True, exist_ok=True)

        existing = {p.name for p in target_dir.iterdir() if p.is_file()}
        target_name = build_plagiarism_name(surname, source_path, existing_names=existing)
        target_path = target_dir / target_name
        shutil.copy2(source_path, target_path)

        rel_path = f"{PLAGIARISM_SUBDIR}/{target_name}"
        thesis.plagiarism_pdf_filename = rel_path
        self.upsert_thesis(thesis)
        return rel_path

    def remove_plagiarism_pdf(self, thesis_id: str, delete_file: bool = False) -> None:
        thesis = self.get_thesis(thesis_id)
        if thesis is None or not thesis.plagiarism_pdf_filename:
            return
        if delete_file:
            target = thesis_documents_dir(thesis_id) / thesis.plagiarism_pdf_filename
            if target.exists():
                target.unlink()
        thesis.plagiarism_pdf_filename = None
        self.upsert_thesis(thesis)

    def plagiarism_pdf_path(self, thesis_id: str) -> Path | None:
        thesis = self.get_thesis(thesis_id)
        if thesis is None or not thesis.plagiarism_pdf_filename:
            return None
        return thesis_documents_dir(thesis_id) / thesis.plagiarism_pdf_filename

    # --- harmonogram napříč roky --------------------------------------------

    # --- oponentské posudky -------------------------------------------------

    def list_opposing_theses(self) -> list[OpposingThesis]:
        return list(self._db.opposing_theses)

    def get_opposing_thesis(self, op_id: str) -> OpposingThesis | None:
        return next(
            (t for t in self._db.opposing_theses if t.id == op_id), None
        )

    def upsert_opposing_thesis(self, op: OpposingThesis) -> OpposingThesis:
        op.touch()
        existing = self.get_opposing_thesis(op.id)
        if existing:
            idx = self._db.opposing_theses.index(existing)
            self._db.opposing_theses[idx] = op
        else:
            self._db.opposing_theses.append(op)
        self.save()
        return op

    def delete_opposing_thesis(self, op_id: str) -> None:
        self._db.opposing_theses = [
            t for t in self._db.opposing_theses if t.id != op_id
        ]
        self.save()

    def opposing_attach_document(
        self,
        op_id: str,
        source_path: Path,
        kind: AttachmentKind = AttachmentKind.OTHER,
        label: str | None = None,
    ) -> Attachment:
        """Nahraje soubor k oponentskému posudku.

        Soubory leží v ``documents/opposing-{id}/{podsložka}/`` se stejným
        schématem názvu jako u vedených prací — viz ``attach_document``.
        """
        op = self.get_opposing_thesis(op_id)
        if op is None:
            raise ValueError(f"Oponentský posudek {op_id} neexistuje.")

        surname = op.student_last_name or None
        subdir = subdir_for(kind)
        target_dir = thesis_documents_dir(f"opposing-{op_id}") / subdir
        target_dir.mkdir(parents=True, exist_ok=True)

        existing = {p.name for p in target_dir.iterdir() if p.is_file()}
        target_name = build_target_name(surname, kind, source_path, existing_names=existing)
        target_path = target_dir / target_name
        shutil.copy2(source_path, target_path)

        rel_path = f"{subdir}/{target_name}"

        # Verzování (stejně jako u ``attach_document``).
        same_kind = [a for a in op.attachments if a.kind == kind]
        next_version = max((a.version for a in same_kind), default=0) + 1
        for a in same_kind:
            a.is_current = False

        attachment = Attachment(
            label=label or target_name,
            url_or_path=rel_path,
            kind=kind,
            is_file=True,
            version=next_version,
            is_current=True,
        )
        op.attachments.append(attachment)
        self.upsert_opposing_thesis(op)
        return attachment

    def opposing_remove_document(
        self, op_id: str, index: int, delete_file: bool = False
    ) -> None:
        op = self.get_opposing_thesis(op_id)
        if op is None or not (0 <= index < len(op.attachments)):
            return
        attachment = op.attachments[index]
        if delete_file and attachment.is_file:
            target = thesis_documents_dir(f"opposing-{op_id}") / attachment.url_or_path
            if target.exists():
                target.unlink()
        del op.attachments[index]
        self.upsert_opposing_thesis(op)

    def opposing_document_absolute_path(
        self, op_id: str, attachment: Attachment
    ) -> Path | None:
        if not attachment.is_file:
            return None
        return thesis_documents_dir(f"opposing-{op_id}") / attachment.url_or_path

    # --- harmonogram napříč roky --------------------------------------------

    def upcoming_dates_all_years(self, from_date: date, days: int = 60) -> list[tuple[str, KeyDate]]:
        """Vrátí důležité nadcházející termíny napříč všemi roky."""
        out: list[tuple[str, KeyDate]] = []
        for info in self._db.academic_years:
            for kd in info.upcoming(from_date, days):
                out.append((info.label, kd))
        return sorted(out, key=lambda x: x[1].sort_key())
