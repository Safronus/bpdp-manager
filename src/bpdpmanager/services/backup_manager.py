"""Správa rotujících záloh ``db.json`` per profil.

- Maximálně ``MAX_BACKUPS`` souborů v ``<data_dir>/backups/``.
- Soubor se vytváří po úspěšném uložení (dedupe podle obsahu hash).
- Před obnovou ze zálohy se vždy vytvoří záloha aktuálního stavu jako
  ``before-restore``, aby šlo vrátit i to.
"""

from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# konvence názvu: db-YYYYMMDD-HHMMSS{__suffix}.json
_BACKUP_FILENAME_RE = re.compile(
    r"^db-(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})(?:__([\w-]+))?\.json$"
)


@dataclass
class BackupInfo:
    """Záznam o jedné záloze."""

    path: Path
    timestamp: datetime
    size_bytes: int
    suffix: str  # "" / "before-restore" / "manual" atd.

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def display_label(self) -> str:
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        if self.suffix:
            return f"{ts}  ·  {self.suffix}"
        return ts


class BackupManager:
    """Vytváří, rotuje a obnovuje zálohy pro jednu profilovou ``data_dir``."""

    MAX_BACKUPS = 10

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.backups_dir = self.data_dir / "backups"

    # --- veřejné API ----------------------------------------------------

    def list_backups(self) -> list[BackupInfo]:
        """Vrátí seznam záloh seřazený sestupně (nejnovější první)."""
        if not self.backups_dir.exists():
            return []
        out: list[BackupInfo] = []
        for p in self.backups_dir.iterdir():
            if not p.is_file():
                continue
            info = self._parse_backup_filename(p)
            if info is not None:
                out.append(info)
        # Primárně dle timestamp DESC, sekundárně dle filename DESC
        # (deterministické pořadí i při více zálohách v rámci stejné sekundy)
        out.sort(key=lambda b: (b.timestamp, b.filename), reverse=True)
        return out

    def create_backup(
        self,
        source: Path,
        suffix: str = "",
        dedupe: bool = True,
    ) -> BackupInfo | None:
        """Vytvoří zálohu zdrojového souboru.

        - ``suffix`` připojí jmenovku k souboru (např. „manual", „before-restore").
        - ``dedupe=True`` přeskočí, pokud poslední záloha má stejný hash obsahu.

        Vrací informaci o vytvořené záloze, nebo None pokud nebyla potřeba.
        """
        if not source.exists():
            return None

        self.backups_dir.mkdir(parents=True, exist_ok=True)

        if dedupe:
            last = self._most_recent_backup()
            if last is not None and self._hash_file(last.path) == self._hash_file(source):
                return None

        ts = datetime.now()
        name = self._make_filename(ts, suffix)
        target = self.backups_dir / name
        # Ošetříme kolizi (víc záloh v rámci stejné sekundy) — counter suffix.
        if target.exists():
            i = 2
            while True:
                alt_suffix = f"{suffix}-{i}" if suffix else f"{i}"
                alt = self.backups_dir / self._make_filename(ts, alt_suffix)
                if not alt.exists():
                    target = alt
                    break
                i += 1
        shutil.copy2(source, target)

        info = BackupInfo(
            path=target,
            timestamp=ts,
            size_bytes=target.stat().st_size,
            suffix=suffix,
        )

        self._rotate()
        return info

    def restore_backup(self, backup_filename: str, target: Path) -> BackupInfo | None:
        """Obnoví zálohu — přepíše ``target`` daným zálohovým souborem.

        Před obnovou vytvoří zálohu aktuálního stavu jako ``before-restore``.
        Vrací info o té nově vytvořené „před-restore" záloze.
        """
        backup_path = self.backups_dir / backup_filename
        if not backup_path.exists():
            raise FileNotFoundError(f"Záloha neexistuje: {backup_filename}")

        # bezpečnostní záloha aktuálního stavu — vždy (i kdyby byl stejný hash)
        pre_restore = self.create_backup(
            target, suffix="before-restore", dedupe=False
        ) if target.exists() else None

        # atomický replace
        tmp = target.with_suffix(target.suffix + ".tmp")
        shutil.copy2(backup_path, tmp)
        tmp.replace(target)
        return pre_restore

    def delete_backup(self, backup_filename: str) -> None:
        backup_path = self.backups_dir / backup_filename
        backup_path.unlink(missing_ok=True)

    # --- privátní -------------------------------------------------------

    def _rotate(self) -> None:
        """Zachová ``MAX_BACKUPS`` nejnovějších záloh, starší smaže."""
        backups = self.list_backups()
        for old in backups[self.MAX_BACKUPS:]:
            old.path.unlink(missing_ok=True)

    def _most_recent_backup(self) -> BackupInfo | None:
        backups = self.list_backups()
        return backups[0] if backups else None

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _make_filename(ts: datetime, suffix: str) -> str:
        base = ts.strftime("db-%Y%m%d-%H%M%S")
        if suffix:
            safe = re.sub(r"[^\w-]+", "-", suffix)
            return f"{base}__{safe}.json"
        return f"{base}.json"

    @staticmethod
    def _parse_backup_filename(path: Path) -> BackupInfo | None:
        m = _BACKUP_FILENAME_RE.match(path.name)
        if not m:
            return None
        y, mo, d, hh, mm, ss, suffix = m.groups()
        try:
            ts = datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss))
        except ValueError:
            return None
        return BackupInfo(
            path=path,
            timestamp=ts,
            size_bytes=path.stat().st_size,
            suffix=suffix or "",
        )
