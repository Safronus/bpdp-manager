"""Stahování souborů příloh ze STAG **na pozadí** (neblokuje UI).

Fronta jobů (``StagFileJob``) se stahuje na vlákně; každý úspěšně stažený soubor
se ohlásí signálem ``file_downloaded`` — konzument (hlavní vlákno) ho připojí
k práci. Na konci ``finished`` nese souhrn (úspěšné / neúspěšné / přerušeno).
Lze přerušit (``cancel``); každý soubor má 1 opakování na přechodné selhání.

Síťovou vrstvu řeší ``services.stag_api`` (UI nesahá na HTTP přímo).
"""

from __future__ import annotations

import re
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal


@dataclass
class StagFileJob:
    """Jeden soubor ke stažení a připojení k práci."""

    target_id: str            # id práce (Thesis.id) nebo oponentury
    is_opposing: bool         # True = oponentura, False = vedená práce
    adipidno: str             # STAG ID práce (jen pro pojmenování temp souboru)
    student_label: str        # popisek do progresu (jméno studenta)
    stag_file: object         # stag_api.StagFile (download_path, filename, section, …)
    kind: object | None = None  # AttachmentKind zvolený v náhledu (pro připojení)


@dataclass
class StagFileResult:
    """Výsledek stažení jednoho souboru."""

    job: StagFileJob
    path: Path | None = None  # dočasná cesta ke staženému souboru (None = chyba)
    size: int = 0
    error: str = ""


class StagFileDownloadManager(QObject):
    """Stáhne frontu souborů ze STAG na pozadí; výsledky hlásí signály."""

    progress = Signal(int, int, str)   # (hotovo, celkem, popisek aktuálního)
    file_downloaded = Signal(object)   # StagFileResult (úspěšný — k připojení)
    finished = Signal(object)          # {"ok": [...], "failed": [...], "canceled": bool}

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._jobs: list[StagFileJob] = []
        self._cancel = False
        self._active = False
        self._thread: threading.Thread | None = None

    @property
    def active(self) -> bool:
        return self._active

    def enqueue(self, jobs) -> None:
        self._jobs.extend(jobs)

    def cancel(self) -> None:
        self._cancel = True

    def start(self) -> None:
        """Spustí stahování fronty na vlákně (no-op, když už běží / je prázdná)."""
        if self._active or not self._jobs:
            return
        self._active = True
        self._cancel = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            self._process()
        except Exception as exc:  # výsledek nesmí shodit vlákno
            self.finished.emit(
                {"ok": [], "failed": [], "canceled": False, "error": str(exc)})
        finally:
            self._active = False

    def _process(self) -> None:
        """Stáhne celou frontu. Volá se z vlákna; pro testy lze i synchronně."""
        from ..services import stag_api

        jobs = self._jobs
        self._jobs = []
        client = stag_api.StagClient()
        ok: list[StagFileResult] = []
        failed: list[StagFileResult] = []
        total = len(jobs)
        for i, job in enumerate(jobs):
            if self._cancel:
                break
            self.progress.emit(
                i, total, f"{job.student_label} — {job.stag_file.filename}")
            res = self._download_one(client, job)
            if res.path is not None:
                ok.append(res)
                self.file_downloaded.emit(res)
            else:
                failed.append(res)
            self.progress.emit(i + 1, total, "")
        self.finished.emit(
            {"ok": ok, "failed": failed, "canceled": self._cancel})

    @staticmethod
    def _download_one(client, job: StagFileJob) -> StagFileResult:
        from ..services import stag_api

        sf = job.stag_file
        last_err = ""
        for _attempt in (1, 2):   # 1 opakování na přechodné selhání STAG
            try:
                data = client.download_file_streamed(
                    sf.download_path, None,
                    timeout=stag_api.download_timeout_for(
                        getattr(sf, "size_hint", 0)),
                )
            except Exception as exc:  # síť/parser → bereme jako neúspěch souboru
                last_err = str(exc)
                continue
            safe = (re.sub(r"[^0-9A-Za-zÀ-ž._-]+", "_", sf.filename).strip("_")
                    or f"soubor_{getattr(sf, 'soubidno', '')}")
            target = (Path(tempfile.gettempdir())
                      / f"stag_{job.adipidno}_{getattr(sf, 'soubidno', '')}_{safe}")
            try:
                target.write_bytes(data)
            except OSError as exc:
                return StagFileResult(job, None, 0, f"zápis selhal: {exc}")
            return StagFileResult(job, target, len(data), "")
        return StagFileResult(job, None, 0, last_err or "stažení selhalo")
