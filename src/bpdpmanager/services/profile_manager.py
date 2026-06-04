"""ProfileManager — registr profilů + aktivace + zámek.

Profil = pojmenovaná datová sada s vlastní ``data_dir``. Registry je v
user config dir (mimo data) — JSON soubor ``profiles.json``.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .. import __version__
from ..config import (
    legacy_data_dir,
    profiles_registry_path,
    set_active_data_dir,
)
from ..models import Profile, ProfileRegistry
from .lock_file import LockCheckResult, LockFile, LockStatus


class ProfileError(Exception):
    """Chyba spojená s profilovou operací."""


class ProfileManager:
    """Drží registry, aktivní profil a lock soubor.

    Použití:
        pm = ProfileManager()
        if not pm.has_any_profile():
            # první spuštění — welcome flow
            ...
        else:
            pm.open(pm.last_opened_id() or pm.all_profiles()[0].id)
        # pracuj…
        pm.close()
    """

    def __init__(self) -> None:
        self._registry_path: Path = profiles_registry_path()
        self._registry: ProfileRegistry = self._load_registry()
        self._active: Profile | None = None
        self._lock: LockFile | None = None

    # --- registry IO ----------------------------------------------------

    def _load_registry(self) -> ProfileRegistry:
        if not self._registry_path.exists():
            return ProfileRegistry()
        try:
            data = json.loads(self._registry_path.read_text(encoding="utf-8"))
            return ProfileRegistry.model_validate(data)
        except (OSError, json.JSONDecodeError, ValueError):
            return ProfileRegistry()

    def _save_registry(self) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._registry.model_dump(mode="json")
        tmp = self._registry_path.with_suffix(self._registry_path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self._registry_path)

    # --- veřejné API ----------------------------------------------------

    def has_any_profile(self) -> bool:
        return len(self._registry.profiles) > 0

    def all_profiles(self) -> list[Profile]:
        # nejdříve podle last_opened_at sestupně, fallback created_at
        return sorted(
            self._registry.profiles,
            key=lambda p: (p.last_opened_at or p.created_at),
            reverse=True,
        )

    def get(self, profile_id: str) -> Profile | None:
        return next(
            (p for p in self._registry.profiles if p.id == profile_id), None
        )

    def last_opened_id(self) -> str | None:
        return self._registry.last_opened

    def has_legacy_data(self) -> bool:
        """Detekuje ``~/.bpdpmanager/db.json`` — nabízí se import jako 'Výchozí'."""
        return (legacy_data_dir() / "db.json").exists()

    @property
    def active(self) -> Profile | None:
        return self._active

    def active_data_dir(self) -> Path:
        if self._active is None:
            raise ProfileError("Žádný aktivní profil.")
        return Path(self._active.data_dir)

    # --- create / import ------------------------------------------------

    def create(self, name: str, data_dir: Path) -> Profile:
        """Vytvoří nový profil ukazující na zadanou složku.

        Pokud data_dir neexistuje, vytvoří ho. Pokud existuje a obsahuje
        db.json, použije ho — uživatel může „otevřít existující profil".
        """
        name = name.strip()
        if not name:
            raise ProfileError("Název profilu nesmí být prázdný.")
        data_dir = Path(data_dir).expanduser().resolve()
        data_dir.mkdir(parents=True, exist_ok=True)

        profile = Profile(
            id=str(uuid4()),
            name=name,
            data_dir=str(data_dir),
            created_at=datetime.now(),
        )
        self._registry.profiles.append(profile)
        self._save_registry()
        return profile

    def import_legacy(self, name: str = "Výchozí") -> Profile:
        """Vytvoří profil ukazující na ``~/.bpdpmanager/``."""
        return self.create(name=name, data_dir=legacy_data_dir())

    # --- open / close ---------------------------------------------------

    def open(
        self,
        profile_id: str,
        *,
        force: bool = False,
    ) -> LockCheckResult:
        """Aktivuje profil, získá zámek a propíše data_dir do configu.

        - Pokud je profil zamčený z jiného zařízení a ``force=False``,
          NEAKTIVUJE ho a vrátí ``LOCKED_BY_OTHER`` — UI vrstva může nabídnout
          „Otevřít stejně" (pak zavolá s ``force=True``).
        - Jinak zámek získá a vrátí jeho status (CLEAN / STALE_SAME_DEVICE
          / LOCKED_BY_OTHER s force).
        """
        profile = self.get(profile_id)
        if profile is None:
            raise ProfileError(f"Profil {profile_id} neexistuje.")

        # zavři případný předchozí
        if self._active is not None and self._active.id != profile_id:
            self.close()

        data_dir = Path(profile.data_dir).expanduser()
        data_dir.mkdir(parents=True, exist_ok=True)

        lock = LockFile(data_dir)
        result = lock.acquire(app_version=__version__, force=force)
        if result.status == LockStatus.LOCKED_BY_OTHER and not force:
            return result

        self._active = profile
        self._lock = lock
        set_active_data_dir(data_dir)

        profile.last_opened_at = datetime.now()
        self._registry.last_opened = profile.id
        self._save_registry()

        return result

    def close(self) -> None:
        """Pustí zámek, uloží last_opened_at."""
        if self._lock is not None:
            self._lock.release()
        if self._active is not None:
            self._active.last_opened_at = datetime.now()
            self._save_registry()
        self._active = None
        self._lock = None

    # --- modifikace -----------------------------------------------------

    def rename(self, profile_id: str, new_name: str) -> Profile:
        profile = self.get(profile_id)
        if profile is None:
            raise ProfileError(f"Profil {profile_id} neexistuje.")
        new_name = new_name.strip()
        if not new_name:
            raise ProfileError("Název nesmí být prázdný.")
        profile.name = new_name
        self._save_registry()
        return profile

    def set_user_name(self, profile_id: str, user_name: str) -> Profile:
        """Nastaví jméno uživatele profilu (pro STAG import auto-detect role)."""
        profile = self.get(profile_id)
        if profile is None:
            raise ProfileError(f"Profil {profile_id} neexistuje.")
        profile.user_name = (user_name or "").strip()
        self._save_registry()
        return profile

    # --- UI předvolby (perzistentní mezi spuštěními) --------------------

    @property
    def last_stag_import_dir(self) -> str:
        return self._registry.last_stag_import_dir or ""

    def set_last_stag_import_dir(self, path: str) -> None:
        self._registry.last_stag_import_dir = (path or "").strip()
        self._save_registry()

    def remove(self, profile_id: str, *, delete_files: bool = False) -> None:
        """Odebere profil z registry. Pokud ``delete_files=True``, smaže i složku."""
        profile = self.get(profile_id)
        if profile is None:
            return
        if self._active is not None and self._active.id == profile_id:
            raise ProfileError("Nelze smazat aktivní profil. Nejprve přepni jinam.")
        self._registry.profiles = [
            p for p in self._registry.profiles if p.id != profile_id
        ]
        if self._registry.last_opened == profile_id:
            self._registry.last_opened = None
        if delete_files:
            try:
                shutil.rmtree(Path(profile.data_dir), ignore_errors=True)
            except OSError:
                pass
        self._save_registry()

    # --- import dat z jiného profilu ------------------------------------

    def copy_data_into_profile(
        self,
        source_id: str,
        target_id: str,
        *,
        include_documents: bool = True,
        include_harmonograms: bool = True,
        overwrite: bool = True,
    ) -> dict[str, int]:
        """Zkopíruje data ze zdrojového profilu do cílového.

        Co se kopíruje:
        - ``db.json`` (přepíše cílový, pokud ``overwrite=True``)
        - ``documents/`` (volitelně, merge per-thesis složky)
        - ``harmonograms/`` (volitelně)

        Co se NEKOPÍRUJE:
        - ``db.json.bak`` (krátkodobá záloha — vznikne při dalším save)
        - ``backups/`` (rotující zálohy — každý profil má vlastní historii)
        - ``.bpdpmanager.lock`` (zámek je per-zařízení)

        Vrací statistiku: ``{"db": 0|1, "documents": N, "harmonograms": M}``.
        """
        src = self.get(source_id)
        tgt = self.get(target_id)
        if src is None:
            raise ProfileError(f"Zdrojový profil {source_id} neexistuje.")
        if tgt is None:
            raise ProfileError(f"Cílový profil {target_id} neexistuje.")
        if src.id == tgt.id:
            raise ProfileError("Zdroj a cíl jsou stejný profil.")

        src_dir = Path(src.data_dir)
        tgt_dir = Path(tgt.data_dir)
        if not src_dir.exists():
            raise ProfileError(f"Zdrojová složka neexistuje: {src_dir}")
        tgt_dir.mkdir(parents=True, exist_ok=True)

        stats = {"db": 0, "documents": 0, "harmonograms": 0}

        # db.json
        src_db = src_dir / "db.json"
        tgt_db = tgt_dir / "db.json"
        if src_db.exists() and (overwrite or not tgt_db.exists()):
            shutil.copy2(src_db, tgt_db)
            stats["db"] = 1

        # documents/
        if include_documents:
            src_docs = src_dir / "documents"
            if src_docs.exists() and src_docs.is_dir():
                tgt_docs = tgt_dir / "documents"
                tgt_docs.mkdir(parents=True, exist_ok=True)
                for child in src_docs.iterdir():
                    target = tgt_docs / child.name
                    if child.is_dir():
                        shutil.copytree(child, target, dirs_exist_ok=True)
                    else:
                        shutil.copy2(child, target)
                    stats["documents"] += 1

        # harmonograms/
        if include_harmonograms:
            src_harm = src_dir / "harmonograms"
            if src_harm.exists() and src_harm.is_dir():
                tgt_harm = tgt_dir / "harmonograms"
                tgt_harm.mkdir(parents=True, exist_ok=True)
                for child in src_harm.iterdir():
                    if child.is_file():
                        shutil.copy2(child, tgt_harm / child.name)
                        stats["harmonograms"] += 1

        return stats

    # --- export / import ZIP ---------------------------------------------

    def export_profile_to_zip(
        self,
        profile_id: str,
        target_zip: Path,
        *,
        include_documents: bool = True,
        include_harmonograms: bool = True,
        include_db_bak: bool = True,
        include_backups: bool = False,
    ) -> dict:
        """Vyexportuje profil jako přenosný ZIP balík.

        Manifest + db.json + (volitelně) documents/, harmonograms/, backups/.
        Použití na druhém zařízení: ``import_profile_from_zip``.
        """
        # Lazy import — vyhneme se kruhové závislosti se ``__init__``.
        from .profile_export import ExportOptions, export_profile_to_zip

        profile = self.get(profile_id)
        if profile is None:
            raise ProfileError(f"Profil {profile_id} neexistuje.")
        return export_profile_to_zip(
            profile=profile,
            source_data_dir=Path(profile.data_dir),
            target_zip=Path(target_zip),
            opts=ExportOptions(
                include_documents=include_documents,
                include_harmonograms=include_harmonograms,
                include_db_bak=include_db_bak,
                include_backups=include_backups,
            ),
        )

    def import_profile_from_zip(
        self,
        source_zip: Path,
        target_data_dir: Path,
        *,
        name: str | None = None,
        overwrite_existing: bool = False,
    ) -> tuple[Profile, dict]:
        """Rozbalí ZIP do ``target_data_dir`` a vytvoří záznam v registry.

        Args:
            source_zip: ZIP balík vytvořený přes ``export_profile_to_zip``.
            target_data_dir: Kam rozbalit (vytvoří se, pokud neexistuje).
            name: Název nového profilu v registry. Pokud ``None``, použije
                  se název z manifestu (nebo „Importovaný profil").
            overwrite_existing: Pokud cílová složka už obsahuje ``db.json``,
                  selhání nebo přepis. Pokud True, lokální data se nahradí.

        Returns:
            ``(Profile, dict)`` — záznam v registry + statistiky importu.
        """
        from .profile_export import (
            ProfileExportError,
            import_profile_from_zip,
            read_zip_manifest,
        )

        # Validace dřív, než cokoli sáhne na disk
        preview = read_zip_manifest(Path(source_zip))
        if not preview.valid:
            raise ProfileError(f"Neplatný ZIP: {preview.error}")

        try:
            result = import_profile_from_zip(
                source_zip=Path(source_zip),
                target_data_dir=Path(target_data_dir),
                overwrite_existing=overwrite_existing,
            )
        except ProfileExportError as exc:
            raise ProfileError(str(exc)) from exc

        # Zaregistruj nový profil. Generujeme nové UUID — original_id
        # z manifestu si nemusíme přebírat (mohlo by kolidovat s jiným
        # importem stejného exportu).
        original = result["manifest"].get("profile") or {}
        chosen_name = (name or "").strip() or original.get("name") or "Importovaný profil"
        # Pokud už existuje profil se stejným jménem, přidej suffix " (2)" …
        existing_names = {p.name for p in self._registry.profiles}
        unique_name = chosen_name
        n = 2
        while unique_name in existing_names:
            unique_name = f"{chosen_name} ({n})"
            n += 1

        profile = self.create(name=unique_name, data_dir=Path(target_data_dir))
        # Pokud byl exportován user_name (pro STAG auto-detect role), přebíráme.
        user_name = (original.get("user_name") or "").strip()
        if user_name:
            self.set_user_name(profile.id, user_name)
        return profile, result

    # --- lock helpers ---------------------------------------------------

    def check_lock(self, profile_id: str) -> LockCheckResult:
        profile = self.get(profile_id)
        if profile is None:
            raise ProfileError(f"Profil {profile_id} neexistuje.")
        return LockFile(Path(profile.data_dir)).check()
