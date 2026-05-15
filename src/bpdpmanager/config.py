from __future__ import annotations

from pathlib import Path

APP_NAME = "bpdpmanager"
SCHEMA_VERSION = 1

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


def app_data_dir() -> Path:
    """Vrátí adresář pro lokální data uživatele (vytvoří, pokud neexistuje)."""
    path = Path.home() / f".{APP_NAME}"
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
