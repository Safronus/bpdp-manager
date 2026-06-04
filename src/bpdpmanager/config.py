from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "bpdpmanager"
# v2: ThesisStatus.ASSIGNED sloučeno do IN_PROGRESS;
#     Attachment dostal pole version + is_current.
SCHEMA_VERSION = 2
ENV_DATA_DIR = "BPDPMANAGER_DATA_DIR"

DEFAULT_OBORY: list[str] = [
    "NSWI-P",
    "NSWI-K",
    "NKYB-P",
    "NKYB-K",
    "NIB-P",
    "NIB-K",
    "NAI-P",
    "NAI-K",
]


# ── Datový adresář aktivního profilu ─────────────────────────────────────
# Místo natvrdo zafixované cesty `~/.bpdpmanager/` máme nyní profily
# (viz services/profile_manager.py). ProfileManager při otevření profilu
# zavolá `set_active_data_dir(path)` a všechny pomocné funkce níže pak
# vracejí cesty odvozené od něj.
#
# Pro testy (a power-user override) má přednost env proměnná `ENV_DATA_DIR`.
#
# Pokud není nastaveno nic, fallback je legacy `~/.bpdpmanager/` — backward
# compat pro případy, kdy je app spuštěn bez ProfileManageru (např. unit testy
# starého stylu).

_active_data_dir: Path | None = None


def set_active_data_dir(path: Path) -> None:
    """Nastav aktivní datovou složku (volá ProfileManager.open)."""
    global _active_data_dir
    _active_data_dir = Path(path)


def clear_active_data_dir() -> None:
    """Reset (zejména pro testy)."""
    global _active_data_dir
    _active_data_dir = None


def legacy_data_dir() -> Path:
    """Cesta k historické datové složce ``~/.bpdpmanager/`` (legacy import)."""
    return Path.home() / f".{APP_NAME}"


def app_data_dir() -> Path:
    """Aktuální datový adresář aplikace.

    Priorita:
    1) env ``BPDPMANAGER_DATA_DIR`` (pro testy)
    2) aktivní profil (``set_active_data_dir``)
    3) legacy ``~/.bpdpmanager/`` (backward compat)
    """
    override = os.environ.get(ENV_DATA_DIR)
    if override:
        path = Path(override).expanduser()
    elif _active_data_dir is not None:
        path = _active_data_dir
    else:
        path = legacy_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return app_data_dir() / "db.json"


def db_backup_path() -> Path:
    return app_data_dir() / "db.json.bak"


def harmonograms_dir() -> Path:
    path = app_data_dir() / "harmonograms"
    path.mkdir(parents=True, exist_ok=True)
    return path


def documents_dir() -> Path:
    path = app_data_dir() / "documents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def thesis_documents_dir(thesis_id: str) -> Path:
    path = documents_dir() / thesis_id
    path.mkdir(parents=True, exist_ok=True)
    return path


# ── User config (registry profilů) ────────────────────────────────────────
# Mimo data_dir — natvrdo daná systémová lokace.

def user_config_dir() -> Path:
    """Systémová user-config složka pro registr profilů a předvolby."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "BPDPManager"
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = (
            Path(appdata) / "BPDPManager"
            if appdata
            else Path.home() / "AppData" / "Roaming" / "BPDPManager"
        )
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = (
            Path(xdg) / "bpdpmanager"
            if xdg
            else Path.home() / ".config" / "bpdpmanager"
        )
    base.mkdir(parents=True, exist_ok=True)
    return base


def profiles_registry_path() -> Path:
    return user_config_dir() / "profiles.json"
