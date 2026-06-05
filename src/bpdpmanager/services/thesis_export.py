"""Export/import jedné práce jako přenosný ZIP balík.

Balík obsahuje kompletní data práce (stav, téma, posudky, známky…) + navázané
entity (student, oponent, obor) + všechny soubory práce. Lze ho importovat na
jiném zařízení / v jiném profilu jako novou práci.

Struktura ZIPu:
    manifest.json          ← metadata (typ, verze, název, datum)
    thesis.json            ← Thesis (pydantic dump)
    student.json           ← Student (volitelně)
    opponent.json          ← Opponent (volitelně)
    obor.json              ← Obor (volitelně)
    documents/<…>          ← všechny soubory práce (zachovaná struktura)
"""

from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .. import __version__
from ..config import SCHEMA_VERSION, thesis_documents_dir
from ..models import Obor, Opponent, Student, Thesis

MANIFEST_FILENAME = "manifest.json"
THESIS_FILENAME = "thesis.json"
STUDENT_FILENAME = "student.json"
OPPONENT_FILENAME = "opponent.json"
OBOR_FILENAME = "obor.json"
DOCUMENTS_PREFIX = "documents/"
EXPORT_TYPE = "thesis"


class ThesisExportError(Exception):
    """Chyba při exportu/importu ZIP balíku práce."""


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


# ── Export ───────────────────────────────────────────────────────────────────


def export_thesis_to_zip(service, thesis_id: str, target_zip: Path) -> dict:
    """Zapíše ZIP balík práce. Vrací statistiku (počet souborů)."""
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
    }

    docs_dir = thesis_documents_dir(thesis_id)
    files_count = 0
    target_zip = Path(target_zip)
    target_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_FILENAME, json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr(THESIS_FILENAME, thesis.model_dump_json(indent=2))
        if student is not None:
            zf.writestr(STUDENT_FILENAME, student.model_dump_json(indent=2))
        if opponent is not None:
            zf.writestr(OPPONENT_FILENAME, opponent.model_dump_json(indent=2))
        if obor is not None:
            zf.writestr(OBOR_FILENAME, obor.model_dump_json(indent=2))
        if docs_dir.is_dir():
            for p in sorted(docs_dir.rglob("*")):
                if p.is_file():
                    rel = p.relative_to(docs_dir).as_posix()
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


def import_thesis_from_zip(service, source_zip: Path) -> str:
    """Vytvoří novou práci z balíku ZIP. Vrací ID nově vytvořené práce."""
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

        # Nová identita práce (ať nepřepíšeme existující).
        thesis.id = str(uuid4())

        # Obor — založ, pokud chybí.
        if obor is not None and service.get_obor(obor.name) is None:
            service.upsert_obor(obor)

        # Student — napáruj přes osobní číslo, jinak založ nového.
        if student is not None:
            existing = None
            if student.university_id:
                existing = next(
                    (s for s in service.list_students()
                     if s.university_id == student.university_id),
                    None,
                )
            if existing is not None:
                thesis.student_id = existing.id
            else:
                student.id = str(uuid4())
                service.upsert_student(student)
                thesis.student_id = student.id

        # Oponent — napáruj přes jméno, jinak založ.
        if opponent is not None:
            existing_o = next(
                (o for o in service.list_opponents() if o.name == opponent.name), None
            )
            if existing_o is not None:
                thesis.opponent_id = existing_o.id
            else:
                opponent.id = str(uuid4())
                service.upsert_opponent(opponent)
                thesis.opponent_id = opponent.id

        # Soubory → do složky nové práce.
        docs_root = thesis_documents_dir(thesis.id)
        for info in zf.infolist():
            if info.is_dir() or not info.filename.startswith(DOCUMENTS_PREFIX):
                continue
            rel = info.filename[len(DOCUMENTS_PREFIX):]
            if not rel:
                continue
            target = _safe_member_path(rel, docs_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)

        service.upsert_thesis(thesis)
        return thesis.id
