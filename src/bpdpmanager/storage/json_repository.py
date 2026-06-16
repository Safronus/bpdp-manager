from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from ..config import DEFAULT_OBORY, SCHEMA_VERSION, db_backup_path, db_path
from .repository import Database, Repository

if TYPE_CHECKING:
    from ..services.backup_manager import BackupManager


class JsonRepository(Repository):
    """JSON úložiště s atomickým zápisem, krátkodobou zálohou ``.bak``
    a volitelnou integrací s ``BackupManager`` (rotující zálohy 10×).
    """

    def __init__(
        self,
        path: Path | None = None,
        backup_path: Path | None = None,
        backup_manager: "BackupManager | None" = None,
    ) -> None:
        self.path = path or db_path()
        self.backup_path = backup_path or db_backup_path()
        self.backup_manager = backup_manager
        # True, pokud ``load()`` právě vytvořil novou (prázdnou) DB — vyšší
        # vrstva (app) podle toho doseeduje defaultní šablony do nového profilu.
        self.created_fresh = False

    def load(self) -> Database:
        if not self.path.exists():
            db = Database(version=SCHEMA_VERSION, obory=list(DEFAULT_OBORY))
            self.save(db)
            self.created_fresh = True
            return db

        raw = self.path.read_text(encoding="utf-8")
        data = json.loads(raw)
        db = Database.model_validate(data)
        db = self._migrate(db)
        return db

    def save(self, db: Database) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # krátkodobá .bak záloha (vždy poslední pre-save stav)
        if self.path.exists():
            shutil.copy2(self.path, self.backup_path)

        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = db.model_dump(mode="json")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False),
            encoding="utf-8",
        )
        tmp.replace(self.path)

        # rotující zálohy (dedupe podle obsahu hash)
        if self.backup_manager is not None:
            try:
                self.backup_manager.create_backup(self.path, suffix="", dedupe=True)
            except Exception:  # noqa: BLE001
                # Záloha selhala — to není fatal, zápis prošel.
                pass

    def _migrate(self, db: Database) -> Database:
        """Schema migration hook — pro budoucí verze."""
        if db.version < SCHEMA_VERSION:
            db.version = SCHEMA_VERSION
            self.save(db)
        return db
