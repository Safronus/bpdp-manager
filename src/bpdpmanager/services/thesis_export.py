"""Export/import jedné práce jako přenosný ZIP balík.

Balík obsahuje kompletní data práce (stav, téma, posudky, známky…) + navázané
entity (student, oponent, obor) + zvolené soubory práce. Lze ho importovat na
jiném zařízení / v jiném profilu jako **novou práci**, nebo jím **aktualizovat
existující** práci (uživatel zvolí, co se přepíše).

Struktura ZIPu:
    manifest.json          ← metadata (typ, verze, název, datum)
    thesis.json            ← Thesis (pydantic dump)
    student.json           ← Student (volitelně)
    opponent.json          ← Opponent (volitelně)
    obor.json              ← Obor (volitelně)
    documents/<…>          ← zvolené soubory práce (zachovaná struktura)
"""

from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .. import __version__
from ..config import SCHEMA_VERSION, thesis_documents_dir
from ..models import Obor, Opponent, Student, Thesis
from ..models.enums import AttachmentKind

MANIFEST_FILENAME = "manifest.json"
THESIS_FILENAME = "thesis.json"
STUDENT_FILENAME = "student.json"
OPPONENT_FILENAME = "opponent.json"
OBOR_FILENAME = "obor.json"
DOCUMENTS_PREFIX = "documents/"
EXPORT_TYPE = "thesis"


class ThesisExportError(Exception):
    """Chyba při exportu/importu ZIP balíku práce."""


# ── Sdílené datové struktury ──────────────────────────────────────────────────


@dataclass
class ExportFileItem:
    """Jeden soubor práce zařazený do kategorie (pro výběrový dialog)."""

    relpath: str  # cesta relativní k documents/ (posix)
    kind: AttachmentKind  # kategorie (dle přílohy, jinak OTHER)
    label: str  # popisek přílohy nebo název souboru
    size: int  # bajtů


@dataclass
class ThesisContents:
    """Přehled exportovatelného obsahu práce — podklad pro výběrový dialog."""

    thesis: Thesis
    student: Student | None
    opponent: Opponent | None
    obor: Obor | None
    files: list[ExportFileItem] = field(default_factory=list)


@dataclass
class ThesisExportSelection:
    """Co zahrnout do exportu. ``file_relpaths=None`` znamená „všechny soubory"."""

    include_student: bool = True
    include_opponent: bool = True
    include_obor: bool = True
    file_relpaths: set[str] | None = None


@dataclass
class ThesisUpdateSelection:
    """Co přepsat při aktualizaci existující práce.

    ``file_relpaths=None`` znamená „všechny soubory z balíku".
    """

    update_data: bool = True
    update_student: bool = True
    update_opponent: bool = True
    update_obor: bool = True
    file_relpaths: set[str] | None = None


# Pořadí kategorií ve výběrovém dialogu (dle enumu, „Jiné" naposledy).
KIND_ORDER: list[AttachmentKind] = list(AttachmentKind)


def _categorize_files(
    thesis: Thesis, raw: list[tuple[str, int]]
) -> list[ExportFileItem]:
    """Zařadí soubory (relpath, size) do kategorií podle příloh práce."""
    by_path: dict[str, Any] = {}
    for a in thesis.attachments:
        if a.is_file and a.url_or_path:
            by_path[a.url_or_path.replace("\\", "/")] = a
    items: list[ExportFileItem] = []
    for relpath, size in raw:
        att = by_path.get(relpath)
        if att is not None:
            kind = att.kind
            label = att.label or Path(relpath).name
        else:
            kind = AttachmentKind.OTHER
            label = Path(relpath).name
        items.append(ExportFileItem(relpath=relpath, kind=kind, label=label, size=size))

    def _sort_key(it: ExportFileItem) -> tuple[int, str]:
        try:
            order = KIND_ORDER.index(it.kind)
        except ValueError:
            order = len(KIND_ORDER)
        return (order, it.relpath.lower())

    items.sort(key=_sort_key)
    return items


@dataclass
class ThesisImportPreview:
    manifest: dict[str, Any]

    @property
    def export_type(self) -> str:
        return self.manifest.get("type", "")

    @property
    def title(self) -> str:
        return self.manifest.get("title", "(bez názvu)")

    @property
    def student_name(self) -> str:
        return self.manifest.get("student", "")


def _safe_member_path(name: str, root: Path) -> Path:
    """Cesta pro extrakci chráněná před path traversal."""
    clean = name.replace("\\", "/").lstrip("/")
    target = (root / clean).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise ThesisExportError(f"ZIP obsahuje nelegitimní cestu: {name!r}")
    return target


# ── Přehled obsahu (pro výběrový dialog při exportu) ──────────────────────────


def gather_thesis_contents(service, thesis_id: str) -> ThesisContents:
    """Sestaví přehled exportovatelného obsahu práce."""
    thesis = service.get_thesis(thesis_id)
    if thesis is None:
        raise ThesisExportError(f"Práce {thesis_id} neexistuje.")
    student = service.get_student(thesis.student_id) if thesis.student_id else None
    opponent = service.get_opponent(thesis.opponent_id) if thesis.opponent_id else None
    obor = service.get_obor(student.obor) if (student and student.obor) else None

    docs_dir = thesis_documents_dir(thesis_id)
    raw: list[tuple[str, int]] = []
    if docs_dir.is_dir():
        for p in sorted(docs_dir.rglob("*")):
            if p.is_file():
                raw.append((p.relative_to(docs_dir).as_posix(), p.stat().st_size))
    files = _categorize_files(thesis, raw)
    return ThesisContents(
        thesis=thesis, student=student, opponent=opponent, obor=obor, files=files
    )


# ── Export ───────────────────────────────────────────────────────────────────


def export_thesis_to_zip(
    service,
    thesis_id: str,
    target_zip: Path,
    selection: ThesisExportSelection | None = None,
) -> dict:
    """Zapíše ZIP balík práce. Vrací statistiku (počet souborů).

    ``selection=None`` zahrne vše (data, entity i všechny soubory).
    """
    sel = selection or ThesisExportSelection()
    thesis = service.get_thesis(thesis_id)
    if thesis is None:
        raise ThesisExportError(f"Práce {thesis_id} neexistuje.")

    student = service.get_student(thesis.student_id) if thesis.student_id else None
    opponent = service.get_opponent(thesis.opponent_id) if thesis.opponent_id else None
    obor = service.get_obor(student.obor) if (student and student.obor) else None

    manifest = {
        "type": EXPORT_TYPE,
        "app_version": __version__,
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "title": thesis.display_title,
        "student": student.full_name if student else "",
        "thesis_type": thesis.type.value,
        "academic_year": thesis.academic_year,
        # Klíče pro spárování s existující prací při importu.
        "thesis_id": thesis.id,
        "adipidno": thesis.adipidno,
        "student_university_id": (student.university_id if student else "") or "",
    }

    docs_dir = thesis_documents_dir(thesis_id)
    files_count = 0
    target_zip = Path(target_zip)
    target_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_FILENAME, json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr(THESIS_FILENAME, thesis.model_dump_json(indent=2))
        if student is not None and sel.include_student:
            zf.writestr(STUDENT_FILENAME, student.model_dump_json(indent=2))
        if opponent is not None and sel.include_opponent:
            zf.writestr(OPPONENT_FILENAME, opponent.model_dump_json(indent=2))
        if obor is not None and sel.include_obor:
            zf.writestr(OBOR_FILENAME, obor.model_dump_json(indent=2))
        if docs_dir.is_dir():
            for p in sorted(docs_dir.rglob("*")):
                if not p.is_file():
                    continue
                rel = p.relative_to(docs_dir).as_posix()
                if sel.file_relpaths is not None and rel not in sel.file_relpaths:
                    continue
                zf.write(p, DOCUMENTS_PREFIX + rel)
                files_count += 1

    return {"files": files_count, "zip": str(target_zip)}


# ── Import ───────────────────────────────────────────────────────────────────


def read_thesis_zip_manifest(source_zip: Path) -> ThesisImportPreview:
    """Načte manifest bez plné extrakce (pro náhled)."""
    try:
        with zipfile.ZipFile(source_zip, "r") as zf:
            with zf.open(MANIFEST_FILENAME) as f:
                manifest = json.loads(f.read().decode("utf-8"))
    except (KeyError, zipfile.BadZipFile, OSError, ValueError) as exc:
        raise ThesisExportError(f"ZIP není platný balík práce: {exc}") from exc
    return ThesisImportPreview(manifest=manifest)


@dataclass
class ThesisZipContents:
    """Rozbalená data balíku + informace o případné shodě s existující prací."""

    manifest: dict[str, Any]
    thesis: Thesis
    student: Student | None
    opponent: Opponent | None
    obor: Obor | None
    files: list[ExportFileItem]
    existing: Thesis | None = None
    match_reason: str = ""


def _read_zip_entities(source_zip: Path) -> tuple[dict, Thesis, Student | None,
                                                  Opponent | None, Obor | None,
                                                  list[tuple[str, int]]]:
    source_zip = Path(source_zip)
    try:
        zf = zipfile.ZipFile(source_zip, "r")
    except (zipfile.BadZipFile, OSError) as exc:
        raise ThesisExportError(f"Nelze otevřít ZIP: {exc}") from exc
    with zf:
        names = set(zf.namelist())
        if MANIFEST_FILENAME not in names or THESIS_FILENAME not in names:
            raise ThesisExportError("ZIP není balík práce (chybí manifest/thesis.json).")
        manifest = json.loads(zf.read(MANIFEST_FILENAME).decode("utf-8"))
        if manifest.get("type") != EXPORT_TYPE:
            raise ThesisExportError("ZIP není balík práce (jiný typ exportu).")
        thesis = Thesis.model_validate_json(zf.read(THESIS_FILENAME).decode("utf-8"))
        student = (
            Student.model_validate_json(zf.read(STUDENT_FILENAME).decode("utf-8"))
            if STUDENT_FILENAME in names else None
        )
        opponent = (
            Opponent.model_validate_json(zf.read(OPPONENT_FILENAME).decode("utf-8"))
            if OPPONENT_FILENAME in names else None
        )
        obor = (
            Obor.model_validate_json(zf.read(OBOR_FILENAME).decode("utf-8"))
            if OBOR_FILENAME in names else None
        )
        raw: list[tuple[str, int]] = []
        for info in zf.infolist():
            if info.is_dir() or not info.filename.startswith(DOCUMENTS_PREFIX):
                continue
            rel = info.filename[len(DOCUMENTS_PREFIX):]
            if rel:
                raw.append((rel, info.file_size))
    return manifest, thesis, student, opponent, obor, raw


def _find_existing_thesis(
    service, thesis: Thesis, student: Student | None
) -> tuple[Thesis | None, str]:
    """Najde už existující práci — nejdřív podle ID z balíku, pak heuristicky."""
    # 1) Přesná shoda podle původního ID práce.
    by_id = service.get_thesis(thesis.id)
    if by_id is not None:
        return by_id, "podle ID práce z balíku"
    # 2) Fallback: stejný student (os. číslo) + typ práce + akademický rok.
    uni = student.university_id if student else None
    if uni:
        target_sids = {
            s.id for s in service.list_students() if s.university_id == uni
        }
        for t in service.list_theses():
            if (
                t.student_id in target_sids
                and t.type == thesis.type
                and t.academic_year == thesis.academic_year
            ):
                return t, "podle studenta, typu a akademického roku"
    return None, ""


def read_thesis_zip(source_zip: Path, service=None) -> ThesisZipContents:
    """Rozbalí metadata balíku a (je-li ``service``) najde shodu s existující prací."""
    manifest, thesis, student, opponent, obor, raw = _read_zip_entities(source_zip)
    files = _categorize_files(thesis, raw)
    existing, reason = (None, "")
    if service is not None:
        existing, reason = _find_existing_thesis(service, thesis, student)
    return ThesisZipContents(
        manifest=manifest, thesis=thesis, student=student, opponent=opponent,
        obor=obor, files=files, existing=existing, match_reason=reason,
    )


def _resolve_student(service, student: Student | None, *, overwrite: bool) -> str | None:
    """Vrátí ID studenta pro propojení; volitelně přepíše existující záznam."""
    if student is None:
        return None
    existing = None
    if student.university_id:
        existing = next(
            (s for s in service.list_students()
             if s.university_id == student.university_id),
            None,
        )
    if existing is not None:
        if overwrite:
            data = student.model_dump()
            data["id"] = existing.id
            service.upsert_student(Student.model_validate(data))
        return existing.id
    fresh = student.model_copy(deep=True)
    fresh.id = str(uuid4())
    service.upsert_student(fresh)
    return fresh.id


def _resolve_opponent(service, opponent: Opponent | None, *, overwrite: bool) -> str | None:
    if opponent is None:
        return None
    existing = next(
        (o for o in service.list_opponents() if o.name == opponent.name), None
    )
    if existing is not None:
        if overwrite:
            data = opponent.model_dump()
            data["id"] = existing.id
            service.upsert_opponent(Opponent.model_validate(data))
        return existing.id
    fresh = opponent.model_copy(deep=True)
    fresh.id = str(uuid4())
    service.upsert_opponent(fresh)
    return fresh.id


def _resolve_obor(service, obor: Obor | None, *, overwrite: bool) -> None:
    if obor is None:
        return
    existing = service.get_obor(obor.name)
    if existing is None or overwrite:
        service.upsert_obor(obor)


def _extract_files(
    source_zip: Path, target_thesis_id: str, relpaths: set[str] | None
) -> int:
    """Rozbalí soubory z balíku do složky práce. ``relpaths=None`` = všechny."""
    docs_root = thesis_documents_dir(target_thesis_id)
    count = 0
    with zipfile.ZipFile(source_zip, "r") as zf:
        for info in zf.infolist():
            if info.is_dir() or not info.filename.startswith(DOCUMENTS_PREFIX):
                continue
            rel = info.filename[len(DOCUMENTS_PREFIX):]
            if not rel:
                continue
            if relpaths is not None and rel not in relpaths:
                continue
            target = _safe_member_path(rel, docs_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            count += 1
    return count


def import_thesis_from_zip(
    service,
    source_zip: Path,
    *,
    update_target_id: str | None = None,
    selection: ThesisUpdateSelection | None = None,
) -> str:
    """Naimportuje práci z balíku ZIP.

    - ``update_target_id=None`` → vytvoří **novou** práci (vrací její ID).
    - ``update_target_id`` zadáno → **aktualizuje** existující práci podle
      ``selection`` (co přepsat); vrací ID té práce.
    """
    contents = read_thesis_zip(source_zip, service=None)
    if update_target_id is None:
        return _import_as_new(service, source_zip, contents)
    return _import_as_update(
        service, source_zip, update_target_id, contents, selection
    )


def _import_as_new(service, source_zip: Path, contents: ThesisZipContents) -> str:
    thesis = contents.thesis.model_copy(deep=True)
    thesis.id = str(uuid4())  # nová identita, ať nepřepíšeme existující

    _resolve_obor(service, contents.obor, overwrite=False)
    sid = _resolve_student(service, contents.student, overwrite=False)
    if sid:
        thesis.student_id = sid
    oid = _resolve_opponent(service, contents.opponent, overwrite=False)
    if oid:
        thesis.opponent_id = oid

    _extract_files(source_zip, thesis.id, None)
    service.upsert_thesis(thesis)
    return thesis.id


def _import_as_update(
    service,
    source_zip: Path,
    target_id: str,
    contents: ThesisZipContents,
    selection: ThesisUpdateSelection | None,
) -> str:
    sel = selection or ThesisUpdateSelection()
    target = service.get_thesis(target_id)
    if target is None:
        raise ThesisExportError(f"Cílová práce {target_id} neexistuje.")

    work = target.model_copy(deep=True)
    if sel.update_data:
        data = contents.thesis.model_dump()
        # Zachovej identitu a vazby — ty řídí samostatné sekce níže.
        data["id"] = target.id
        data["created_at"] = target.created_at
        data["student_id"] = target.student_id
        data["opponent_id"] = target.opponent_id
        work = Thesis.model_validate(data)

    if sel.update_student and contents.student is not None:
        sid = _resolve_student(service, contents.student, overwrite=True)
        if sid:
            work.student_id = sid
    if sel.update_opponent and contents.opponent is not None:
        oid = _resolve_opponent(service, contents.opponent, overwrite=True)
        if oid:
            work.opponent_id = oid
    if sel.update_obor and contents.obor is not None:
        _resolve_obor(service, contents.obor, overwrite=True)

    # Soubory: None = všechny; prázdná množina = žádné.
    if sel.file_relpaths is None or sel.file_relpaths:
        _extract_files(source_zip, work.id, sel.file_relpaths)

    work.touch()
    service.upsert_thesis(work)
    return work.id
