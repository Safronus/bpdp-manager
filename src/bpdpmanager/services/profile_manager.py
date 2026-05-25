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

    # --- lock helpers ---------------------------------------------------

    def check_lock(self, profile_id: str) -> LockCheckResult:
        profile = self.get(profile_id)
        if profile is None:
            raise ProfileError(f"Profil {profile_id} neexistuje.")
        return LockFile(Path(profile.data_dir)).check()
