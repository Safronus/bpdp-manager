from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..config import DEFAULT_OBORY, SCHEMA_VERSION, db_backup_path, db_path
from .repository import Database, Repository


class JsonRepository(Repository):
    """JSON úložiště s atomickým zápisem a zálohou."""

    def __init__(self, path: Path | None = None, backup_path: Path | None = None) -> None:
        self.path = path or db_path()
        self.backup_path = backup_path or db_backup_path()

    def load(self) -> Database:
        if not self.path.exists():
            db = Database(version=SCHEMA_VERSION, obory=list(DEFAULT_OBORY))
            self.save(db)
            return db

        raw = self.path.read_text(encoding="utf-8")
        data = json.loads(raw)
        db = Database.model_validate(data)
        db = self._migrate(db)
        return db

    def save(self, db: Database) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if self.path.exists():
            shutil.copy2(self.path, self.backup_path)

        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = db.model_dump(mode="json")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False),
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def _migrate(self, db: Database) -> Database:
        """Schema migration hook — pro budoucí verze."""
        if db.version < SCHEMA_VERSION:
            db.version = SCHEMA_VERSION
            self.save(db)
        return db
