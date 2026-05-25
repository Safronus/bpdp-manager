"""Lock soubor pro detekci souběžného otevření profilu na více zařízeních."""

from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class LockStatus(str, Enum):
    CLEAN = "clean"  # žádný lock, vše ok
    STALE_SAME_DEVICE = "stale_same_device"  # lock z předchozího běhu na tomto Macu
    LOCKED_BY_OTHER = "locked_by_other"  # lock z jiného zařízení / uživatele


@dataclass
class LockInfo:
    hostname: str
    username: str
    pid: int
    started_at: datetime
    app_version: str

    def to_dict(self) -> dict:
        return {
            "hostname": self.hostname,
            "username": self.username,
            "pid": self.pid,
            "started_at": self.started_at.isoformat(),
            "app_version": self.app_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LockInfo":
        return cls(
            hostname=data.get("hostname", "?"),
            username=data.get("username", "?"),
            pid=int(data.get("pid", 0)),
            started_at=datetime.fromisoformat(
                data.get("started_at", datetime.now().isoformat())
            ),
            app_version=data.get("app_version", "?"),
        )


@dataclass
class LockCheckResult:
    status: LockStatus
    existing: LockInfo | None = None


class LockFile:
    """Lock soubor v data_dir profilu — ``.bpdpmanager.lock``.

    Drží JSON s metainformacemi o aktivní instanci. Aplikace při startu
    volá ``acquire``, při ukončení ``release``. Pokud je lock z jiného
    zařízení, výsledek je ``LOCKED_BY_OTHER`` a UI vrstva rozhodne, jestli
    user může pokračovat (= ignorovat lock) či profil odmítnout otevřít.
    """

    FILENAME = ".bpdpmanager.lock"

    def __init__(self, data_dir: Path) -> None:
        self.path = Path(data_dir) / self.FILENAME

    # --- pomocné --------------------------------------------------------

    @staticmethod
    def _this_lock_info(app_version: str = "?") -> LockInfo:
        return LockInfo(
            hostname=socket.gethostname(),
            username=os.environ.get("USER") or os.environ.get("USERNAME") or "?",
            pid=os.getpid(),
            started_at=datetime.now(),
            app_version=app_version,
        )

    # --- veřejné API ----------------------------------------------------

    def read(self) -> LockInfo | None:
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return LockInfo.from_dict(data)
        except (OSError, json.JSONDecodeError, ValueError):
            return None

    def check(self) -> LockCheckResult:
        existing = self.read()
        if existing is None:
            return LockCheckResult(status=LockStatus.CLEAN)
        if existing.hostname == socket.gethostname():
            # Lock z téhož Macu — buď duplicate startup, nebo crash. V obou
            # případech ho považujeme za bezpečně přepsatelný (nový PID).
            return LockCheckResult(
                status=LockStatus.STALE_SAME_DEVICE, existing=existing
            )
        return LockCheckResult(status=LockStatus.LOCKED_BY_OTHER, existing=existing)

    def acquire(self, app_version: str = "?", force: bool = False) -> LockCheckResult:
        """Pokus o získání zámku.

        - ``CLEAN`` nebo ``STALE_SAME_DEVICE`` → zámek se zapíše, vrátí výsledek.
        - ``LOCKED_BY_OTHER`` a ``force=False`` → zámek se NEZAPÍŠE, vrátí status.
        - ``LOCKED_BY_OTHER`` a ``force=True`` → přepíše stávající a vrátí status.
        """
        result = self.check()
        if result.status == LockStatus.LOCKED_BY_OTHER and not force:
            return result
        self._write_lock(app_version)
        return result

    def release(self) -> None:
        """Smaže lock soubor (pokud patří této instanci)."""
        try:
            existing = self.read()
            if existing is None:
                return
            if (
                existing.hostname == socket.gethostname()
                and existing.pid == os.getpid()
            ):
                self.path.unlink(missing_ok=True)
        except OSError:
            pass

    # --- privátní -------------------------------------------------------

    def _write_lock(self, app_version: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        info = self._this_lock_info(app_version=app_version)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(info.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self.path)
