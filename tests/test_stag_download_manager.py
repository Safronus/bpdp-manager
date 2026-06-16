"""StagFileDownloadManager — stahování příloh na pozadí (bez sítě, mock klienta)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from bpdpmanager.services import stag_api
from bpdpmanager.ui.stag_download_manager import (
    StagFileDownloadManager,
    StagFileJob,
)


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


class _FakeFile:
    def __init__(self, download_path, filename):
        self.download_path = download_path
        self.filename = filename
        self.section = "text"
        self.size_hint = 0
        self.soubidno = "1"


def _job(dp, fn, tid="t1"):
    return StagFileJob(target_id=tid, is_opposing=False, adipidno="111",
                       student_label="Novák", stag_file=_FakeFile(dp, fn))


def test_manager_success_and_failure(qapp, monkeypatch) -> None:
    """Frontu zpracuje: úspěšný stáhne (file_downloaded), neúspěšný do failed."""
    calls = {"n": 0}

    class FakeClient:
        def download_file_streamed(self, path, cb, timeout=0):
            calls["n"] += 1
            if "boom" in path:
                raise RuntimeError("nope")
            return b"DATA:" + path.encode()

    monkeypatch.setattr(stag_api, "StagClient", FakeClient)

    mgr = StagFileDownloadManager()
    mgr.enqueue([_job("ok1", "a.pdf"), _job("boom", "b.pdf", tid="t2")])
    downloaded = []
    summary = {}
    mgr.file_downloaded.connect(lambda r: downloaded.append(r))
    mgr.finished.connect(lambda s: summary.update(s))

    mgr._process()   # synchronně (test) — signály se doručí přímo

    assert len(downloaded) == 1
    assert downloaded[0].path is not None and downloaded[0].path.exists()
    assert downloaded[0].path.read_bytes() == b"DATA:ok1"
    assert len(summary["ok"]) == 1 and len(summary["failed"]) == 1
    assert "nope" in summary["failed"][0].error
    # boom soubor: 2 pokusy (auto-retry) → download volán 1x ok + 2x boom = 3
    assert calls["n"] == 3
    downloaded[0].path.unlink(missing_ok=True)


def test_manager_cancel_stops_queue(qapp, monkeypatch) -> None:
    """Po cancel() se zbytek fronty nezpracuje."""
    class FakeClient:
        def download_file_streamed(self, path, cb, timeout=0):
            return b"x"

    monkeypatch.setattr(stag_api, "StagClient", FakeClient)
    mgr = StagFileDownloadManager()
    mgr.enqueue([_job(f"f{i}", f"{i}.pdf") for i in range(5)])
    mgr.cancel()
    summary = {}
    mgr.finished.connect(lambda s: summary.update(s))
    mgr._process()
    assert summary["canceled"] is True
    assert summary["ok"] == [] and summary["failed"] == []


def test_manager_progress_emitted(qapp, monkeypatch) -> None:
    class FakeClient:
        def download_file_streamed(self, path, cb, timeout=0):
            return b"x"

    monkeypatch.setattr(stag_api, "StagClient", FakeClient)
    mgr = StagFileDownloadManager()
    mgr.enqueue([_job("a", "a.pdf"), _job("b", "b.pdf")])
    seen = []
    mgr.progress.connect(lambda d, t, lbl: seen.append((d, t)))
    mgr._process()
    assert (2, 2) in seen   # poslední progres = vše hotovo
    assert mgr._jobs == []   # fronta vyprázdněna


def test_mainwindow_background_download_attaches(qapp, tmp_path, monkeypatch) -> None:
    """MainWindow spustí stahování na pozadí; připojí každý soubor a skryje lištu."""
    import time
    from pathlib import Path

    from bpdpmanager.services import ThesisService
    from bpdpmanager.storage import JsonRepository
    from bpdpmanager.ui.main_window import MainWindow

    class FakeClient:
        def download_file_streamed(self, path, cb, timeout=0):
            return b"X" * 10

    monkeypatch.setattr(stag_api, "StagClient", FakeClient)
    svc = ThesisService(JsonRepository(path=tmp_path / "db.json",
                                       backup_path=tmp_path / "db.bak"))
    mw = MainWindow(svc)
    attached = []
    mw.start_stag_file_downloads(
        [_job("ok1", "a.pdf"), _job("ok2", "b.pdf")],
        lambda r: attached.append(r))
    assert not mw._bg_widget.isHidden()     # lišta se ukázala (okno není show())
    for _ in range(200):                    # počkej na doběhnutí vlákna
        qapp.processEvents()
        if mw._stag_file_mgr is None:
            break
        time.sleep(0.01)
    assert mw._stag_file_mgr is None
    assert len(attached) == 2               # oba soubory připojeny (přes callback)
    assert mw._bg_widget.isHidden()         # lišta skrytá po dokončení
    for r in attached:
        Path(r.path).unlink(missing_ok=True)
    mw.close()
