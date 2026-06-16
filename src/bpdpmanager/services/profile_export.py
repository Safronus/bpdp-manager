"""Export/import profilu jako přenosný ZIP balík.

Cíl: uživatel může profil exportovat na flash disk / iCloud / email a na jiném
zařízení (nebo na stejném po reinstalaci) ho otevřít a začít používat.

Struktura ZIP:
  manifest.json                              ← metadata exportu
  db.json                                    ← databáze
  db.json.bak                                ← poslední krátkodobá záloha (volitelně)
  documents/<thesis_id>/...                  ← přílohy k pracem (volitelně)
  harmonograms/*.pdf                         ← naimportované PDF harmonogramy (volitelně)

Manifest schema (verze 1):
  {
    "bpdp_manager_export_version": 1,
    "exported_at": "2026-06-04T12:34:56",
    "app_version": "0.16.0",
    "schema_version": 2,
    "profile": { "name": "...", "original_id": "uuid", "user_name": "..." },
    "contents": { "db_json": true, "documents": true, "harmonograms": true,
                  "backups": false },
    "stats": { "documents_count": N, "harmonograms_count": N,
               "total_uncompressed_bytes": N }
  }

Modul je úmyslně bez závislosti na PySide6 — UI vrstva si dialog
postaví sama nad zde vystavenými funkcemi.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import __version__
from ..config import SCHEMA_VERSION
from ..models import Profile

EXPORT_FORMAT_VERSION = 1
MANIFEST_FILENAME = "manifest.json"
DB_FILENAME = "db.json"
DB_BAK_FILENAME = "db.json.bak"


class ProfileExportError(Exception):
    """Chyba při exportu/importu profilu jako ZIP."""


@dataclass
class ExportOptions:
    include_documents: bool = True
    include_harmonograms: bool = True
    include_db_bak: bool = True
    include_backups: bool = False  # rotující 10× zálohy se typicky neexportují
    include_templates: bool = True  # XLSX šablony posudků (v0.17.0+)


@dataclass
class ExportPreview:
    """Co by export obsahoval — pro confirmation dialog před spuštěním."""

    db_json_size: int
    db_bak_size: int
    documents_count: int
    documents_bytes: int
    harmonograms_count: int
    harmonograms_bytes: int
    backups_count: int
    backups_bytes: int
    templates_count: int = 0
    templates_bytes: int = 0

    @property
    def total_bytes(self) -> int:
        return (
            self.db_json_size
            + self.db_bak_size
            + self.documents_bytes
            + self.harmonograms_bytes
            + self.backups_bytes
            + self.templates_bytes
        )


@dataclass
class ImportPreview:
    """Co by import přinesl — pro confirmation dialog před extrakcí."""

    manifest: dict[str, Any]
    valid: bool
    error: str = ""

    @property
    def profile_name(self) -> str:
        return (self.manifest.get("profile") or {}).get("name", "(neznámý)")

    @property
    def exported_at(self) -> str:
        return self.manifest.get("exported_at", "")

    @property
    def app_version(self) -> str:
        return self.manifest.get("app_version", "")

    @property
    def schema_version(self) -> int:
        return int(self.manifest.get("schema_version", 0))

    @property
    def stats(self) -> dict:
        return self.manifest.get("stats") or {}


# ── Helpers ────────────────────────────────────────────────────────────────


def _walk_files(root: Path) -> list[Path]:
    """Rekurzivně všechny soubory pod ``root``. Symlinky se nesledují."""
    if not root.is_dir():
        return []
    return [p for p in root.rglob("*") if p.is_file()]


def _dir_size(root: Path) -> tuple[int, int]:
    """Vrátí (počet souborů, total bytes) v adresáři rekurzivně."""
    files = _walk_files(root)
    return len(files), sum(p.stat().st_size for p in files)


def _safe_extract_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo, target_root: Path) -> Path:
    """Bezpečná extrakce jednoho ZIP záznamu — chrání před path traversal."""
    # Normalize: backslash → slash, leading slash removed, parent components rejected
    name = info.filename.replace("\\", "/").lstrip("/")
    target = (target_root / name).resolve()
    if not str(target).startswith(str(target_root.resolve())):
        raise ProfileExportError(
            f"ZIP obsahuje cestu mimo cílovou složku ({info.filename!r}). "
            "Soubor možná není legitimní BPDPManager export."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    if info.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        return target
    with zf.open(info) as src, target.open("wb") as dst:
        shutil.copyfileobj(src, dst)
    return target


# ── Export ─────────────────────────────────────────────────────────────────


def compute_export_preview(source_data_dir: Path, opts: ExportOptions) -> ExportPreview:
    """Spočítá, co by export obsahoval — bez vlastního zápisu."""
    db_path = source_data_dir / DB_FILENAME
    db_bak = source_data_dir / DB_BAK_FILENAME
    docs_dir = source_data_dir / "documents"
    harm_dir = source_data_dir / "harmonograms"
    backups_dir = source_data_dir / "backups"
    templates_dir = source_data_dir / "templates"

    docs_n, docs_b = _dir_size(docs_dir) if opts.include_documents else (0, 0)
    harm_n, harm_b = _dir_size(harm_dir) if opts.include_harmonograms else (0, 0)
    backups_n, backups_b = _dir_size(backups_dir) if opts.include_backups else (0, 0)
    tmpl_n, tmpl_b = _dir_size(templates_dir) if opts.include_templates else (0, 0)

    return ExportPreview(
        db_json_size=db_path.stat().st_size if db_path.is_file() else 0,
        db_bak_size=db_bak.stat().st_size if opts.include_db_bak and db_bak.is_file() else 0,
        documents_count=docs_n,
        documents_bytes=docs_b,
        harmonograms_count=harm_n,
        harmonograms_bytes=harm_b,
        backups_count=backups_n,
        backups_bytes=backups_b,
        templates_count=tmpl_n,
        templates_bytes=tmpl_b,
    )


def export_profile_to_zip(
    profile: Profile,
    source_data_dir: Path,
    target_zip: Path,
    opts: ExportOptions | None = None,
) -> dict:
    """Zapíše ZIP balík profilu.

    Args:
        profile: ``Profile`` z registry (pro jméno a původní ID v manifestu).
        source_data_dir: Skutečná data složka profilu (kde leží db.json …).
        target_zip: Kam zapsat ZIP. Pokud existuje, *přepíše se*.
        opts: Co zahrnout (default: db + db.bak + documents + harmonograms,
              bez rotujících backups).

    Returns:
        Statistiky exportu (file_count, total_bytes, target_zip_path).

    Raises:
        ProfileExportError: chybějící db.json, FS chyby zápisu.
    """
    opts = opts or ExportOptions()
    source_data_dir = Path(source_data_dir).expanduser().resolve()
    target_zip = Path(target_zip).expanduser()

    if not source_data_dir.is_dir():
        raise ProfileExportError(f"Datový adresář profilu neexistuje: {source_data_dir}")

    db_path = source_data_dir / DB_FILENAME
    if not db_path.is_file():
        raise ProfileExportError(
            f"db.json profilu chybí ({db_path}) — nelze exportovat prázdný profil."
        )

    target_zip.parent.mkdir(parents=True, exist_ok=True)

    # Spočti stats předem (pro manifest)
    preview = compute_export_preview(source_data_dir, opts)

    manifest = {
        "bpdp_manager_export_version": EXPORT_FORMAT_VERSION,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "app_version": __version__,
        "schema_version": SCHEMA_VERSION,
        "profile": {
            "name": profile.name,
            "original_id": profile.id,
            "user_name": profile.user_name or "",
            "user_first_name": profile.user_first_name or "",
            "user_surname": profile.user_surname or "",
            "created_at": profile.created_at.isoformat() if profile.created_at else "",
        },
        "contents": {
            "db_json": True,
            "db_bak": opts.include_db_bak,
            "documents": opts.include_documents,
            "harmonograms": opts.include_harmonograms,
            "backups": opts.include_backups,
            "templates": opts.include_templates,
        },
        "stats": {
            "documents_count": preview.documents_count,
            "harmonograms_count": preview.harmonograms_count,
            "backups_count": preview.backups_count,
            "templates_count": preview.templates_count,
            "total_uncompressed_bytes": preview.total_bytes,
        },
    }

    files_added = 0
    # Atomic write: pišeme do .tmp, na konci přejmenujeme.
    tmp_zip = target_zip.with_suffix(target_zip.suffix + ".tmp")
    try:
        with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                MANIFEST_FILENAME,
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
            files_added += 1

            zf.write(db_path, arcname=DB_FILENAME)
            files_added += 1

            if opts.include_db_bak:
                db_bak = source_data_dir / DB_BAK_FILENAME
                if db_bak.is_file():
                    zf.write(db_bak, arcname=DB_BAK_FILENAME)
                    files_added += 1

            def _add_tree(subdir_name: str) -> None:
                nonlocal files_added
                root = source_data_dir / subdir_name
                if not root.is_dir():
                    return
                for f in _walk_files(root):
                    arcname = f"{subdir_name}/{f.relative_to(root).as_posix()}"
                    zf.write(f, arcname=arcname)
                    files_added += 1

            if opts.include_documents:
                _add_tree("documents")
            if opts.include_harmonograms:
                _add_tree("harmonograms")
            if opts.include_backups:
                _add_tree("backups")
            if opts.include_templates:
                _add_tree("templates")

        tmp_zip.replace(target_zip)
    except Exception:
        # Cleanup tmp on failure
        if tmp_zip.exists():
            try:
                tmp_zip.unlink()
            except OSError:
                pass
        raise

    return {
        "target_zip": str(target_zip),
        "files_added": files_added,
        "zip_size_bytes": target_zip.stat().st_size,
        "uncompressed_bytes": preview.total_bytes,
        "manifest": manifest,
    }


# ── Import ─────────────────────────────────────────────────────────────────


def read_zip_manifest(source_zip: Path) -> ImportPreview:
    """Načte manifest ze ZIPu bez extrakce — pro preview dialog.

    Pokud manifest chybí nebo je nečitelný, vrací ``valid=False`` a důvod.
    """
    source_zip = Path(source_zip)
    if not source_zip.is_file():
        return ImportPreview(manifest={}, valid=False, error="Soubor neexistuje.")
    try:
        with zipfile.ZipFile(source_zip, "r") as zf:
            if MANIFEST_FILENAME not in zf.namelist():
                return ImportPreview(
                    manifest={},
                    valid=False,
                    error="Soubor není BPDPManager export (chybí manifest.json).",
                )
            with zf.open(MANIFEST_FILENAME) as f:
                manifest = json.loads(f.read().decode("utf-8"))
    except (zipfile.BadZipFile, json.JSONDecodeError, KeyError) as exc:
        return ImportPreview(
            manifest={},
            valid=False,
            error=f"ZIP nelze přečíst: {exc}",
        )

    if not isinstance(manifest, dict):
        return ImportPreview(
            manifest={}, valid=False, error="Manifest nemá očekávaný formát."
        )

    ver = manifest.get("bpdp_manager_export_version")
    if not isinstance(ver, int):
        return ImportPreview(
            manifest=manifest,
            valid=False,
            error="Manifest neoznačil export verzi (bpdp_manager_export_version).",
        )
    if ver > EXPORT_FORMAT_VERSION:
        return ImportPreview(
            manifest=manifest,
            valid=False,
            error=(
                f"ZIP byl vytvořen novější verzí aplikace (export verze {ver}, "
                f"podporujeme {EXPORT_FORMAT_VERSION}). Aktualizuj aplikaci."
            ),
        )

    schema = int(manifest.get("schema_version", 0))
    if schema > SCHEMA_VERSION:
        # Schema je novější — možná půjde, ale upozorni.
        return ImportPreview(
            manifest=manifest,
            valid=True,  # nezablokuj — Database.model_validate to případně odhalí
            error=(
                f"⚠ Pozor: ZIP má novější schema_version ({schema} > {SCHEMA_VERSION}). "
                "Některá pole mohou být ignorována. Pokračovat na vlastní riziko."
            ),
        )

    return ImportPreview(manifest=manifest, valid=True)


def import_profile_from_zip(
    source_zip: Path,
    target_data_dir: Path,
    overwrite_existing: bool = False,
) -> dict:
    """Rozbalí ZIP do ``target_data_dir`` a vrátí stats + manifest.

    Pokud ``target_data_dir`` neexistuje, vytvoří se. Pokud existuje a obsahuje
    ``db.json`` a ``overwrite_existing=False``, vyhodí ``ProfileExportError``.

    Po úspěšném importu *nevytváří* záznam v ``ProfileRegistry`` —
    o to se postará volající (typicky ``ProfileManager``).
    """
    source_zip = Path(source_zip).expanduser()
    target_data_dir = Path(target_data_dir).expanduser().resolve()

    preview = read_zip_manifest(source_zip)
    if not preview.valid:
        raise ProfileExportError(f"ZIP není validní: {preview.error}")

    existing_db = target_data_dir / DB_FILENAME
    if existing_db.is_file() and not overwrite_existing:
        raise ProfileExportError(
            f"Cílová složka už obsahuje databázi ({existing_db}). "
            'Pokud chceš přepsat, zaškrtni v dialogu „Přepsat existující data".'
        )

    target_data_dir.mkdir(parents=True, exist_ok=True)

    files_extracted = 0
    bytes_extracted = 0
    with zipfile.ZipFile(source_zip, "r") as zf:
        for info in zf.infolist():
            # Manifest se nesype do cílové složky — je metadata exportu, ne data.
            if info.filename == MANIFEST_FILENAME:
                continue
            _safe_extract_member(zf, info, target_data_dir)
            if not info.is_dir():
                files_extracted += 1
                bytes_extracted += info.file_size

    return {
        "manifest": preview.manifest,
        "target_data_dir": str(target_data_dir),
        "files_extracted": files_extracted,
        "bytes_extracted": bytes_extracted,
    }


# ── Merge ZIP into existing profile ────────────────────────────────────────


@dataclass
class MergePreview:
    """Co by merge přidal / přeskočil — pro confirmation dialog před spuštěním.

    Sémantika *add-only* merge: do cíle se přidají entity, které tam nejsou
    (podle klíče identity); existující se nemění (skip on conflict).
    Soubory se kopírují, pokud cílový name neexistuje.
    """

    # Entity, které se přidají (nejsou v target):
    new_students: int = 0
    new_opponents: int = 0
    new_supervisors: int = 0
    new_obory: int = 0
    new_theses: int = 0
    new_opposing: int = 0
    new_templates: int = 0
    new_academic_years: int = 0
    # Konflikty (existují v target — přeskočí se):
    skipped_students: int = 0
    skipped_opponents: int = 0
    skipped_supervisors: int = 0
    skipped_obory: int = 0
    skipped_theses: int = 0
    skipped_opposing: int = 0
    skipped_templates: int = 0
    skipped_academic_years: int = 0
    # Soubory:
    new_files: int = 0
    skipped_files: int = 0
    new_files_bytes: int = 0


def _load_source_db(source_zip: Path) -> dict:
    """Vytáhne ``db.json`` ze ZIPu jako dict — bez extrakce na disk."""
    with zipfile.ZipFile(source_zip, "r") as zf:
        if DB_FILENAME not in zf.namelist():
            raise ProfileExportError(
                f"ZIP neobsahuje ``{DB_FILENAME}`` — nelze provést merge."
            )
        with zf.open(DB_FILENAME) as f:
            data = json.loads(f.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ProfileExportError(f"``{DB_FILENAME}`` v ZIPu má neočekávaný formát.")
    return data


def compute_merge_preview(
    source_zip: Path, target_data_dir: Path
) -> tuple[MergePreview, dict]:
    """Spočítá, co by merge přidal/přeskočil, bez vlastního zápisu.

    Returns ``(preview, source_db_dict)`` — db dict se vrací aby ho
    ``merge_zip_into_profile`` znovu nemuselo načítat.
    """
    src_db = _load_source_db(source_zip)
    target_data_dir = Path(target_data_dir)

    # Načti target db.json (pokud existuje); jinak prázdný
    target_db_path = target_data_dir / DB_FILENAME
    if target_db_path.is_file():
        try:
            tgt_db = json.loads(target_db_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProfileExportError(
                f"Cílový {DB_FILENAME} nelze přečíst: {exc}"
            ) from exc
    else:
        tgt_db = {}

    preview = MergePreview()

    def _key_set(items: list, key_fn) -> set:
        out = set()
        for it in items or []:
            if isinstance(it, dict):
                k = key_fn(it)
                if k:
                    out.add(k)
        return out

    # IDs / klíče v target (které sloužit jako "už tam je")
    tgt_student_ids = _key_set(tgt_db.get("students", []), lambda s: s.get("id"))
    tgt_student_unis = _key_set(
        tgt_db.get("students", []), lambda s: (s.get("university_id") or "").strip()
    )
    tgt_opponent_names = _key_set(
        tgt_db.get("opponents", []), lambda o: (o.get("name") or "").strip()
    )
    tgt_supervisor_names = _key_set(
        tgt_db.get("supervisors", []), lambda s: (s.get("name") or "").strip()
    )
    tgt_obor_names = _key_set(
        tgt_db.get("obory", []), lambda o: (o.get("name") or "").strip()
    )
    tgt_thesis_ids = _key_set(tgt_db.get("theses", []), lambda t: t.get("id"))
    tgt_opposing_ids = _key_set(
        tgt_db.get("opposing_theses", []), lambda t: t.get("id")
    )
    tgt_template_ids = _key_set(
        tgt_db.get("review_templates", []), lambda t: t.get("id")
    )
    tgt_year_labels = _key_set(
        tgt_db.get("academic_years", []), lambda y: (y.get("label") or "").strip()
    )

    # Per-entity preview
    for s in src_db.get("students", []) or []:
        sid = s.get("id")
        uni = (s.get("university_id") or "").strip()
        # Match by ID nebo by university_id (univerzitní číslo je v praxi unikátní)
        if (sid and sid in tgt_student_ids) or (uni and uni in tgt_student_unis):
            preview.skipped_students += 1
        else:
            preview.new_students += 1

    for o in src_db.get("opponents", []) or []:
        name = (o.get("name") or "").strip()
        if name and name in tgt_opponent_names:
            preview.skipped_opponents += 1
        else:
            preview.new_opponents += 1

    for s in src_db.get("supervisors", []) or []:
        name = (s.get("name") or "").strip()
        if name and name in tgt_supervisor_names:
            preview.skipped_supervisors += 1
        else:
            preview.new_supervisors += 1

    for o in src_db.get("obory", []) or []:
        name = (o.get("name") or "").strip() if isinstance(o, dict) else str(o).strip()
        if name and name in tgt_obor_names:
            preview.skipped_obory += 1
        else:
            preview.new_obory += 1

    for t in src_db.get("theses", []) or []:
        if t.get("id") in tgt_thesis_ids:
            preview.skipped_theses += 1
        else:
            preview.new_theses += 1

    for t in src_db.get("opposing_theses", []) or []:
        if t.get("id") in tgt_opposing_ids:
            preview.skipped_opposing += 1
        else:
            preview.new_opposing += 1

    for t in src_db.get("review_templates", []) or []:
        if t.get("id") in tgt_template_ids:
            preview.skipped_templates += 1
        else:
            preview.new_templates += 1

    for y in src_db.get("academic_years", []) or []:
        label = (y.get("label") or "").strip()
        if label and label in tgt_year_labels:
            preview.skipped_academic_years += 1
        else:
            preview.new_academic_years += 1

    # Soubory: spočti jen pro odhad, zda by se kopírovaly nebo přeskočily
    with zipfile.ZipFile(source_zip, "r") as zf:
        for info in zf.infolist():
            if info.is_dir() or info.filename == MANIFEST_FILENAME:
                continue
            if info.filename == DB_FILENAME or info.filename == DB_BAK_FILENAME:
                continue  # db.json se merge-uje samostatně, ne kopíruje
            rel = info.filename.replace("\\", "/")
            target_path = target_data_dir / rel
            if target_path.exists():
                preview.skipped_files += 1
            else:
                preview.new_files += 1
                preview.new_files_bytes += info.file_size

    return preview, src_db


def merge_zip_into_profile(
    source_zip: Path,
    target_data_dir: Path,
) -> dict:
    """Add-only merge: do cílového profilu přidá entity, které v něm nejsou,
    a nakopíruje chybějící soubory. Konflikty se přeskočí (target verze
    se nemění).

    Identity klíče per entita:
      - Student: ``id`` nebo ``university_id``
      - Opponent / Supervisor / Obor: ``name``
      - Thesis / OpposingThesis / ReviewTemplate: ``id``
      - AcademicYearInfo: ``label``

    Po merge se zapíše merged ``db.json`` zpět do target_data_dir.

    Args:
        source_zip: ZIP balík vytvořený přes ``export_profile_to_zip``.
        target_data_dir: data_dir existujícího profilu, do kterého se mergne.

    Returns:
        Statistiky merge: stejná pole jako ``MergePreview`` + ``manifest``.

    Raises:
        ProfileExportError: nečitelný ZIP, chybějící db.json, FS chyba.
    """
    source_zip = Path(source_zip)
    target_data_dir = Path(target_data_dir).expanduser().resolve()

    preview = read_zip_manifest(source_zip)
    if not preview.valid:
        raise ProfileExportError(f"ZIP není validní: {preview.error}")

    merge_preview, src_db = compute_merge_preview(source_zip, target_data_dir)

    target_db_path = target_data_dir / DB_FILENAME
    if target_db_path.is_file():
        tgt_db = json.loads(target_db_path.read_text(encoding="utf-8"))
    else:
        # Cíl nemá db.json — neobvyklé pro existující profil, ale
        # zacházíme s tím jako s prázdnou databází.
        tgt_db = {"version": src_db.get("version", 1)}

    # Pomocné indexy pro lookup
    def _idx_by(items: list, key_fn) -> set:
        return {key_fn(it) for it in items or [] if isinstance(it, dict)}

    tgt_db.setdefault("students", [])
    tgt_db.setdefault("opponents", [])
    tgt_db.setdefault("supervisors", [])
    tgt_db.setdefault("obory", [])
    tgt_db.setdefault("theses", [])
    tgt_db.setdefault("opposing_theses", [])
    tgt_db.setdefault("academic_years", [])
    tgt_db.setdefault("review_templates", [])

    tgt_student_ids = _idx_by(tgt_db["students"], lambda s: s.get("id"))
    tgt_student_unis = {
        (s.get("university_id") or "").strip()
        for s in tgt_db["students"] if isinstance(s, dict)
    }
    tgt_opponent_names = {
        (o.get("name") or "").strip()
        for o in tgt_db["opponents"] if isinstance(o, dict)
    }
    tgt_supervisor_names = {
        (s.get("name") or "").strip()
        for s in tgt_db["supervisors"] if isinstance(s, dict)
    }
    tgt_obor_names = {
        (o.get("name") or "").strip() if isinstance(o, dict) else str(o).strip()
        for o in tgt_db["obory"]
    }
    tgt_thesis_ids = _idx_by(tgt_db["theses"], lambda t: t.get("id"))
    tgt_opposing_ids = _idx_by(
        tgt_db["opposing_theses"], lambda t: t.get("id")
    )
    tgt_template_ids = _idx_by(
        tgt_db["review_templates"], lambda t: t.get("id")
    )
    tgt_year_labels = {
        (y.get("label") or "").strip()
        for y in tgt_db["academic_years"] if isinstance(y, dict)
    }

    # Add new entities
    for s in src_db.get("students", []) or []:
        sid = s.get("id")
        uni = (s.get("university_id") or "").strip()
        if (sid and sid in tgt_student_ids) or (uni and uni in tgt_student_unis):
            continue
        tgt_db["students"].append(s)

    for o in src_db.get("opponents", []) or []:
        name = (o.get("name") or "").strip()
        if name and name in tgt_opponent_names:
            continue
        tgt_db["opponents"].append(o)

    for s in src_db.get("supervisors", []) or []:
        name = (s.get("name") or "").strip()
        if name and name in tgt_supervisor_names:
            continue
        tgt_db["supervisors"].append(s)

    for o in src_db.get("obory", []) or []:
        name = (o.get("name") or "").strip() if isinstance(o, dict) else str(o).strip()
        if name and name in tgt_obor_names:
            continue
        tgt_db["obory"].append(o)

    for t in src_db.get("theses", []) or []:
        if t.get("id") in tgt_thesis_ids:
            continue
        tgt_db["theses"].append(t)

    for t in src_db.get("opposing_theses", []) or []:
        if t.get("id") in tgt_opposing_ids:
            continue
        tgt_db["opposing_theses"].append(t)

    for t in src_db.get("review_templates", []) or []:
        if t.get("id") in tgt_template_ids:
            continue
        tgt_db["review_templates"].append(t)

    for y in src_db.get("academic_years", []) or []:
        label = (y.get("label") or "").strip()
        if label and label in tgt_year_labels:
            continue
        tgt_db["academic_years"].append(y)

    # Schema version: vezmi vyšší (forward-compat)
    src_ver = int(src_db.get("version", 0))
    tgt_ver = int(tgt_db.get("version", 0))
    tgt_db["version"] = max(src_ver, tgt_ver)

    # Atomic write merged db.json
    target_data_dir.mkdir(parents=True, exist_ok=True)
    tmp = target_db_path.with_suffix(target_db_path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(tgt_db, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(target_db_path)

    # Zkopíruj soubory (mimo db.json / db.json.bak / manifest) — skip existujících
    copied_files = 0
    copied_bytes = 0
    skipped_files = 0
    with zipfile.ZipFile(source_zip, "r") as zf:
        for info in zf.infolist():
            if info.is_dir() or info.filename == MANIFEST_FILENAME:
                continue
            if info.filename == DB_FILENAME or info.filename == DB_BAK_FILENAME:
                continue
            rel = info.filename.replace("\\", "/").lstrip("/")
            target_path = (target_data_dir / rel).resolve()
            # Path-traversal ochrana
            if not str(target_path).startswith(str(target_data_dir)):
                continue
            if target_path.exists():
                skipped_files += 1
                continue
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target_path.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            copied_files += 1
            copied_bytes += info.file_size

    return {
        "manifest": preview.manifest,
        "target_data_dir": str(target_data_dir),
        # Counts from merge_preview pro UI (jsou už spočtené)
        "new_students": merge_preview.new_students,
        "new_opponents": merge_preview.new_opponents,
        "new_supervisors": merge_preview.new_supervisors,
        "new_obory": merge_preview.new_obory,
        "new_theses": merge_preview.new_theses,
        "new_opposing": merge_preview.new_opposing,
        "new_templates": merge_preview.new_templates,
        "new_academic_years": merge_preview.new_academic_years,
        "skipped_students": merge_preview.skipped_students,
        "skipped_opponents": merge_preview.skipped_opponents,
        "skipped_supervisors": merge_preview.skipped_supervisors,
        "skipped_obory": merge_preview.skipped_obory,
        "skipped_theses": merge_preview.skipped_theses,
        "skipped_opposing": merge_preview.skipped_opposing,
        "skipped_templates": merge_preview.skipped_templates,
        "skipped_academic_years": merge_preview.skipped_academic_years,
        "files_copied": copied_files,
        "files_skipped": skipped_files,
        "bytes_copied": copied_bytes,
    }
