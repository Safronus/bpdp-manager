"""Testy stahování ze STAG — varování u velkých příloh (regrese _cs_plural)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

import bpdpmanager.ui.stag_import_dialog as mod
from bpdpmanager.services import stag_api
from bpdpmanager.ui.stag_import_dialog import StagDownloadDialog


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def _dialog():
    dlg = StagDownloadDialog(service=None)
    dlg._enrich_visible = lambda: None
    return dlg


def _big():
    return stag_api.StagFile(
        soubidno="9", filename="velky_text.pdf", download_path="/big",
        section="text", size_hint=mod._LARGE_FILE_BYTES + 1,
    )


def _small():
    return stag_api.StagFile(
        soubidno="1", filename="posudek.pdf", download_path="/small",
        section="supervisor_review", size_hint=2048,
    )


def test_confirm_oversized_skip(qapp, monkeypatch) -> None:
    """Klik na „Přeskočit velké" → vrátí soubidno velké přílohy (žádný crash)."""
    dlg = _dialog()
    captured: dict = {}

    def fake_exec(self_msg):
        for b in self_msg.buttons():
            if "Přeskočit" in b.text():
                captured["b"] = b
        return 0

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: captured.get("b"))

    skip = dlg._confirm_oversized({"42": [_big(), _small()]})
    assert skip == {"9"}


def test_confirm_oversized_download_anyway(qapp, monkeypatch) -> None:
    """Klik na „Stáhnout i tak" → prázdná množina (nic se nepřeskočí)."""
    dlg = _dialog()
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: None)
    assert dlg._confirm_oversized({"42": [_big()]}) == set()


def test_confirm_oversized_no_big_no_dialog(qapp, monkeypatch) -> None:
    """Bez velkých příloh se dialog vůbec nevyvolá a vrátí prázdnou množinu."""
    dlg = _dialog()

    def boom(self):  # dialog se nesmí otevřít
        raise AssertionError("QMessageBox se neměl zobrazit")

    monkeypatch.setattr(QMessageBox, "exec", boom)
    assert dlg._confirm_oversized({"42": [_small()]}) == set()


def _result(adip="1"):
    return stag_api.StagThesisResult(
        adipidno=adip, surname="A", name="B", title="T",
        type_label="Bakalářská práce", status_code="DUO",
    )


def _cell_text(dlg, adip, col):
    root = dlg.tree_results.invisibleRootItem()
    found = []

    def walk(item):
        for i in range(item.childCount()):
            walk(item.child(i))
        if item.data(0, 0x0100) == adip:
            found.append(item.text(col))

    for i in range(root.childCount()):
        walk(root.child(i))
    return found[0] if found else None


def test_attachments_lazy_fill(qapp, monkeypatch) -> None:
    """Po zaškrtnutí práce se dotáhne počet + velikost příloh do sloupce."""
    monkeypatch.setattr(mod.stag_api, "list_thesis_files", lambda a: [_big(), _small()])
    dlg = _dialog()
    dlg._results = [_result("1")]
    dlg._render_results()
    assert _cell_text(dlg, "1", mod._ATTACH_COL) == ""   # zatím nezjištěno
    dlg._fetch_attachments(["1"])
    assert dlg._attach_info["1"] == (2, mod._LARGE_FILE_BYTES + 1 + 2048)
    assert _cell_text(dlg, "1", mod._ATTACH_COL).startswith("📎 2")


def test_first_column_capped(qapp) -> None:
    """Velmi dlouhý název nepřeroste strop sloupce „Práce"."""
    dlg = _dialog()
    dlg._results = [
        stag_api.StagThesisResult(
            adipidno="1", surname="Novák", name="Jan",
            title="Velmi dlouhý název kvalifikační práce " * 30,
            type_label="Bakalářská práce", status_code="DUO",
        )
    ]
    dlg._render_results()
    assert dlg.tree_results.columnWidth(0) <= mod._MAX_FIRST_COL


def test_attachments_error_shows_question_mark(qapp, monkeypatch) -> None:
    """Chyba při zjišťování příloh → „?" a nezakešuje se (jde zkusit znovu)."""
    def boom(adip):
        raise stag_api.StagError("síť")

    monkeypatch.setattr(mod.stag_api, "list_thesis_files", boom)
    dlg = _dialog()
    dlg._results = [_result("1")]
    dlg._render_results()
    dlg._fetch_attachments(["1"])
    assert "1" not in dlg._attach_info
    assert _cell_text(dlg, "1", mod._ATTACH_COL) == "?"


# ── Streamované stahování souborů (průběžný progres) ─────────────────────────

class _FakeResp:
    """Falešná HTTP odpověď pro download_file_streamed (čte po blocích)."""

    def __init__(self, data: bytes, total=None):
        self._data = data
        self._pos = 0
        self.headers = {} if total is None else {"Content-Length": str(total)}

    def read(self, n=-1):
        if n is None or n < 0:
            chunk = self._data[self._pos:]
            self._pos = len(self._data)
            return chunk
        chunk = self._data[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_download_file_streamed_reports_progress(monkeypatch) -> None:
    client = stag_api.StagClient()
    data = b"x" * (200 * 1024)  # 200 KB → víc 64KB bloků
    monkeypatch.setattr(
        client._opener, "open", lambda req, timeout=None: _FakeResp(data, len(data))
    )
    calls: list = []

    def cb(downloaded, total):
        calls.append((downloaded, total))
        return True

    out = client.download_file_streamed("/x", cb)
    assert out == data
    assert calls[0][1] == len(data)         # celková velikost z Content-Length
    assert calls[-1][0] == len(data)        # nakonec staženo = celé
    assert len(calls) > 2                    # průběžné aktualizace (po blocích)


def test_download_file_streamed_cancel(monkeypatch) -> None:
    client = stag_api.StagClient()
    data = b"y" * (200 * 1024)
    monkeypatch.setattr(
        client._opener, "open", lambda req, timeout=None: _FakeResp(data, len(data))
    )
    # Callback povolí start (downloaded==0) a pak přeruší.
    with pytest.raises(stag_api.StagCancelledError):
        client.download_file_streamed("/x", lambda d, t: d == 0)


def test_cleanup_temp_files(tmp_path) -> None:
    a = tmp_path / "a.bin"
    a.write_bytes(b"x")
    b = tmp_path / "b.bin"
    b.write_bytes(b"y")
    missing = tmp_path / "nope.bin"
    StagDownloadDialog._cleanup_temp_files([a, b, missing])
    assert not a.exists() and not b.exists()  # smazáno, na chybějící nespadne


def test_leftover_and_offer_cleanup(qapp, tmp_path, monkeypatch) -> None:
    """Najde a (po potvrzení) smaže zbylé STAG temp soubory; cizí nechá."""
    monkeypatch.setattr(mod.tempfile, "gettempdir", lambda: str(tmp_path))
    (tmp_path / "stag_Novak_111.csv").write_bytes(b"a")
    (tmp_path / "stagsync_1_2_p.pdf").write_bytes(b"b")
    (tmp_path / "unrelated.txt").write_bytes(b"c")

    dlg = _dialog()
    assert len(dlg._leftover_temp_files()) == 2

    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    dlg._offer_temp_cleanup()
    assert not (tmp_path / "stag_Novak_111.csv").exists()
    assert not (tmp_path / "stagsync_1_2_p.pdf").exists()
    assert (tmp_path / "unrelated.txt").exists()  # cizí soubor zůstal


def test_download_huge_total_no_overflow(qapp, tmp_path, monkeypatch) -> None:
    """Obří součet velikostí příloh (>2 GB) nesmí přetéct 32-bit progress."""
    monkeypatch.setattr(mod.tempfile, "gettempdir", lambda: str(tmp_path))

    huge = stag_api.StagFile(
        soubidno="9", filename="big.pdf", download_path="/big",
        section="text", size_hint=8_000_000_000,  # 8 GB > 2^31
    )

    class FakeClient:
        def download_csv(self, adip):
            return b"stavPrace;typPrace\r\nDUO;Bakalarska prace\r\n"

        def list_thesis_files(self, adip):
            return [huge]

        def download_file_streamed(self, path, on_progress=None, timeout=None):
            if on_progress:
                on_progress(10, 10)
            return b"x" * 10

    monkeypatch.setattr(mod.stag_api, "StagClient", FakeClient)
    # Oba potvrzovací dialogy (velké přílohy + velký objem) → „pokračovat".
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: None)

    result = stag_api.StagThesisResult(
        adipidno="1", surname="Novak", name="Jan",
        type_label="Bakalarska prace", status_code="DUO",
    )
    dlg = _dialog()
    dlg._checked_results = lambda: [result]
    dlg._preview_and_pick = lambda *a, **k: {}
    accepted = []
    dlg.accept = lambda: accepted.append(True)

    dlg._download_selected()  # nesmí spadnout na OverflowError

    assert accepted                      # došlo až k accept()
    assert dlg.result_items and dlg.result_items[0][1] is result


def test_download_uses_long_timeout(monkeypatch) -> None:
    """Stahování souboru používá výrazně delší timeout (velké/ZIP přílohy)."""
    client = stag_api.StagClient()
    captured: dict = {}

    def fake_open(req, timeout=None):
        captured["timeout"] = timeout
        return _FakeResp(b"x" * 10, 10)

    monkeypatch.setattr(client._opener, "open", fake_open)
    client.download_file_streamed("/x")
    assert captured["timeout"] == stag_api._DOWNLOAD_TIMEOUT
    assert captured["timeout"] >= 300  # mnohem víc než běžných 30 s


def test_download_timeout_friendly_message(monkeypatch) -> None:
    """Timeout při stahování → srozumitelná hláška (ne „zkontroluj internet")."""
    client = stag_api.StagClient()

    def fake_open(req, timeout=None):
        raise TimeoutError("timed out")

    monkeypatch.setattr(client._opener, "open", fake_open)
    with pytest.raises(stag_api.StagError) as ei:
        client.download_file_streamed("/x")
    assert "neodpověděl včas" in str(ei.value)
