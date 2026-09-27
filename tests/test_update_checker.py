"""Kontrola aktualizací — parsování CHANGELOG, porovnání verzí, update kroky."""

from __future__ import annotations

import hashlib
import io
import os
import subprocess
from pathlib import Path
from typing import ClassVar

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from bpdpmanager.services import update_checker as uc

_CHANGELOG = """# Changelog

## [Unreleased]

## [1.18.0] - 2026-06-11

### Added
- Automaticka kontrola aktualizaci.

## [1.17.4] - 2026-06-10

### Added
- Indikace znamky bez posudku.

## [1.17.3] - 2026-06-10

### Fixed
- Nahrani noveho posudku prepise znamku.
"""


def test_parse_version() -> None:
    assert uc.parse_version("1.17.4") == (1, 17, 4)
    assert uc.parse_version("1.18.0") > uc.parse_version("1.17.4")
    assert uc.parse_version("1.9.9") < uc.parse_version("1.10.0")
    assert uc.parse_version("") == (0,)


def test_parse_changelog_sections() -> None:
    sections = uc.parse_changelog_sections(_CHANGELOG)
    versions = [v for v, _md in sections]
    assert versions == ["1.18.0", "1.17.4", "1.17.3"]   # Unreleased přeskočen
    assert "kontrola aktualizaci" in sections[0][1]


def test_check_for_update_newer() -> None:
    info = uc.check_for_update("1.17.3", changelog_text=_CHANGELOG)
    assert info is not None
    assert info.latest == "1.18.0"
    assert info.versions == ["1.18.0", "1.17.4"]
    # Changelog obsahuje VŠECHNY verze mezi (1.18.0 i 1.17.4), 1.17.3 ne.
    assert "1.18.0" in info.changelog_md and "1.17.4" in info.changelog_md
    assert "## [1.17.3]" not in info.changelog_md


def test_check_for_update_up_to_date() -> None:
    assert uc.check_for_update("1.18.0", changelog_text=_CHANGELOG) is None
    assert uc.check_for_update("2.0.0", changelog_text=_CHANGELOG) is None


def test_check_for_update_empty_changelog() -> None:
    assert uc.check_for_update("1.0.0", changelog_text="# nic tu neni") is None


def test_repo_root_found() -> None:
    # Testy běží v git klonu projektu → kořen musí existovat a mít .git.
    root = uc.repo_root()
    assert root is not None and (root / ".git").exists()


def test_perform_update_refuses_dirty(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(uc, "is_repo_dirty", lambda root: True)
    ok, msg = uc.perform_update(tmp_path)
    assert ok is False
    assert "lokální změny" in msg


def test_perform_update_runs_pull_and_pip(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, root, timeout=300):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(uc, "is_repo_dirty", lambda root: False)
    monkeypatch.setattr(uc, "_run", fake_run)
    ok, _msg = uc.perform_update(tmp_path)
    assert ok is True
    assert calls[0][:3] == ["git", "pull", "--ff-only"]
    assert "pip" in calls[1] and "-e" in calls[1]      # doinstaluje závislosti


def test_perform_update_pull_failure(monkeypatch, tmp_path: Path) -> None:
    def fake_run(cmd, root, timeout=300):
        if cmd[0] == "git":
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="fatal: x")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(uc, "is_repo_dirty", lambda root: False)
    monkeypatch.setattr(uc, "_run", fake_run)
    ok, msg = uc.perform_update(tmp_path)
    assert ok is False and "git pull selhal" in msg


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def test_update_dialog_content(qapp) -> None:
    from bpdpmanager.ui.update_dialog import UpdateDialog

    info = uc.UpdateInfo(
        current="1.17.3", latest="1.18.0",
        changelog_md="## [1.18.0]\n\n- Novinka A\n\n## [1.17.4]\n\n- Oprava B",
        versions=["1.18.0", "1.17.4"],
    )
    dlg = UpdateDialog(info, check_enabled=True)
    assert "1.18.0" in dlg.windowTitle() or "Aktualizace" in dlg.windowTitle()
    text = dlg.changelog.toPlainText()
    assert "Novinka A" in text and "Oprava B" in text
    assert dlg.btn_update.text().startswith("🔄")
    assert dlg.cb_check.isChecked()
    # „Přeskočit tuto verzi" nastaví flag a zavře dialog.
    dlg.btn_skip.click()
    assert dlg.skip_requested is True


def test_update_dialog_unchecking_disables(qapp) -> None:
    from bpdpmanager.ui.update_dialog import UpdateDialog

    info = uc.UpdateInfo(current="1.0.0", latest="1.0.1", changelog_md="x")
    dlg = UpdateDialog(info, check_enabled=True)
    dlg.cb_check.setChecked(False)
    dlg.reject()
    assert dlg.check_enabled is False


# ── Zabalená aplikace (.app): update z GitHub Releases ─────────────────────

_REL = "https://github.com/Safronus/bpdp-manager/releases/"
_DMG_URL = _REL + "download/v2.30.0/BPDPManager-2.30.0-macos-arm64.dmg"
_PAYLOAD = b"fake dmg payload " * 4096            # ~70 kB
_SHA = hashlib.sha256(_PAYLOAD).hexdigest()


def _release_json(**asset_overrides) -> dict:
    asset = {"name": "BPDPManager-2.30.0-macos-arm64.dmg",
             "browser_download_url": _DMG_URL,
             "digest": f"sha256:{_SHA}", "size": len(_PAYLOAD)}
    asset.update(asset_overrides)
    return {"tag_name": "v2.30.0", "html_url": _REL + "tag/v2.30.0",
            "assets": [{"name": "x.txt", "browser_download_url": _REL + "download/x.txt"},
                       asset]}


def test_parse_latest_release_dmg_with_digest() -> None:
    rel = uc.parse_latest_release(_release_json())
    assert (rel.version, rel.url, rel.sha256, rel.size) == ("2.30.0", _DMG_URL, _SHA,
                                                           len(_PAYLOAD))


def test_parse_latest_release_fallbacks_and_validation() -> None:
    # bez .dmg assetu → stránka Release, žádný digest
    rel = uc.parse_latest_release({"tag_name": "v2.30.0",
                                   "html_url": _REL + "tag/v2.30.0", "assets": []})
    assert (rel.url, rel.sha256, rel.size) == (_REL + "tag/v2.30.0", "", 0)
    # neplatný formát digestu → prázdný (stáhne se pak přes prohlížeč)
    assert uc.parse_latest_release(_release_json(digest="md5:abc")).sha256 == ""
    # odkaz mimo náš repozitář → bezpečná záloha a digest se ZAHODÍ
    rel = uc.parse_latest_release(_release_json(
        browser_download_url="https://evil.example/x.dmg"))
    assert (rel.url, rel.sha256) == (uc.RELEASES_PAGE, "")
    # neplatná odpověď → ValueError
    with pytest.raises(ValueError):
        uc.parse_latest_release({"tag_name": "latest"})
    with pytest.raises(ValueError):
        uc.parse_latest_release(["není", "dict"])


def test_check_for_frozen_update_limits_to_release() -> None:
    # CHANGELOG už má 1.19.0, ale CI ho ještě nevydalo → nesmí se nabídnout.
    changelog = "## [1.19.0] - 2026-06-12\n\n- Budoucí verze\n\n" + _CHANGELOG
    rel = uc.ReleaseInfo("1.18.0", _DMG_URL, _SHA, len(_PAYLOAD))
    info = uc.check_for_frozen_update("1.17.3", release=rel, changelog_text=changelog)
    assert info is not None
    assert info.latest == "1.18.0" and info.versions == ["1.18.0", "1.17.4"]
    assert (info.download_url, info.download_sha256, info.download_size) == (
        _DMG_URL, _SHA, len(_PAYLOAD))
    assert info.can_download_in_app
    assert "Budoucí verze" not in info.changelog_md
    for cur in ("1.18.0", "1.19.0"):                  # aktuální / novější → nic
        assert uc.check_for_frozen_update(cur, release=rel,
                                          changelog_text=changelog) is None


def test_check_for_frozen_update_offline_changelog(monkeypatch) -> None:
    def boom():
        raise OSError("offline")

    monkeypatch.setattr(uc, "fetch_changelog", boom)
    info = uc.check_for_frozen_update("1.0.0", release=uc.ReleaseInfo("1.1.0", _DMG_URL))
    assert info is not None and info.changelog_md == "" and info.versions == ["1.1.0"]
    assert not info.can_download_in_app               # bez digestu → prohlížeč


class _FakeResponse(io.BytesIO):
    def __init__(self, data: bytes, length: bool = True) -> None:
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))} if length else {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _fake_urlopen(monkeypatch, data: bytes = _PAYLOAD) -> list[str]:
    import urllib.request

    requested: list[str] = []

    def fake(req, timeout=None):
        requested.append(req.full_url)
        return _FakeResponse(data)

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    return requested


def test_download_update_ok(monkeypatch, tmp_path: Path) -> None:
    requested = _fake_urlopen(monkeypatch)
    seen: list[tuple[int, int]] = []
    dest = tmp_path / "BPDPManager.dmg"
    out = uc.download_update(_DMG_URL, dest, _SHA.upper(),     # hex bez ohledu na velikost
                             progress=lambda d, t: seen.append((d, t)),
                             chunk_size=8192)
    assert out == dest and dest.read_bytes() == _PAYLOAD
    assert requested == [_DMG_URL]
    assert seen[-1] == (len(_PAYLOAD), len(_PAYLOAD)) and len(seen) > 1
    assert not (tmp_path / "BPDPManager.dmg.part").exists()


def test_download_update_bad_checksum_leaves_nothing(monkeypatch, tmp_path: Path) -> None:
    _fake_urlopen(monkeypatch, data=_PAYLOAD + b"podvrh")
    dest = tmp_path / "x.dmg"
    with pytest.raises(uc.UpdateDownloadError, match="Kontrolní součet nesedí"):
        uc.download_update(_DMG_URL, dest, _SHA)
    assert list(tmp_path.iterdir()) == []                      # ani .part, ani .dmg


def test_download_update_cancel_leaves_nothing(monkeypatch, tmp_path: Path) -> None:
    _fake_urlopen(monkeypatch)
    calls = {"n": 0}

    def cancel_after_first() -> bool:
        calls["n"] += 1
        return calls["n"] > 1

    with pytest.raises(uc.UpdateDownloadCancelledError):
        uc.download_update(_DMG_URL, tmp_path / "x.dmg", _SHA,
                           is_cancelled=cancel_after_first, chunk_size=4096)
    assert list(tmp_path.iterdir()) == []


def test_download_update_refuses_foreign_url_and_missing_digest(monkeypatch,
                                                                tmp_path: Path) -> None:
    requested = _fake_urlopen(monkeypatch)
    with pytest.raises(uc.UpdateDownloadError, match="nevede"):
        uc.download_update("https://evil.example/x.dmg", tmp_path / "x.dmg", _SHA)
    with pytest.raises(uc.UpdateDownloadError, match="Chybí kontrolní součet"):
        uc.download_update(_DMG_URL, tmp_path / "x.dmg", "")
    assert requested == []                                     # nic se nestahovalo


def test_download_update_network_error_is_wrapped(monkeypatch, tmp_path: Path) -> None:
    import urllib.request

    def fail(req, timeout=None):
        raise OSError("connection reset")

    monkeypatch.setattr(urllib.request, "urlopen", fail)
    with pytest.raises(uc.UpdateDownloadError, match="Stažení selhalo"):
        uc.download_update(_DMG_URL, tmp_path / "x.dmg", _SHA)
    assert list(tmp_path.iterdir()) == []


def test_update_checker_branches(monkeypatch, qapp) -> None:
    from bpdpmanager.ui.update_dialog import UpdateChecker

    sentinel = uc.UpdateInfo(current="1.0.0", latest="1.1.0", changelog_md="")
    got: list = []

    # zabalená appka → Release, git se vůbec neřeší
    monkeypatch.setattr(uc, "is_frozen", lambda: True)
    monkeypatch.setattr(uc, "check_for_frozen_update", lambda cur: sentinel)
    monkeypatch.setattr(uc, "repo_root", lambda: pytest.fail("git v .app"))
    checker = UpdateChecker("1.0.0")
    checker.finished.connect(got.append)
    checker._work()
    assert got == [sentinel]

    # ani .app, ani git klon (pip) → ticho
    monkeypatch.setattr(uc, "is_frozen", lambda: False)
    monkeypatch.setattr(uc, "repo_root", lambda: None)
    got.clear()
    checker._work()
    assert got == [None]


class _FakeDesktop:
    opened: ClassVar[list[str]] = []

    @staticmethod
    def openUrl(url) -> bool:  # noqa: N802 (Qt API)
        _FakeDesktop.opened.append(url.toString())
        return True


def test_update_dialog_browser_fallback(monkeypatch, qapp) -> None:
    """Release bez digestu → stažení v prohlížeči + návod „Přesto otevřít"."""
    import bpdpmanager.ui.update_dialog as ud

    _FakeDesktop.opened = []
    monkeypatch.setattr(ud, "QDesktopServices", _FakeDesktop)
    monkeypatch.setattr(uc, "perform_update",
                        lambda root: pytest.fail("v .app se nesmí dělat git pull"))
    info = uc.UpdateInfo(current="2.29.5", latest="2.30.0", changelog_md="",
                         download_url=_DMG_URL)             # bez sha256
    dlg = ud.UpdateDialog(info, check_enabled=True)
    assert dlg.btn_update.text() == "⬇ Stáhnout novou verzi"
    assert "stránce vydání" in dlg.changelog.toPlainText()   # prázdný changelog
    dlg.btn_update.click()
    assert _FakeDesktop.opened == [_DMG_URL]
    assert not dlg.btn_update.isEnabled()
    assert "Přesto otevřít" in dlg.status.text()


def _inapp_info() -> uc.UpdateInfo:
    return uc.UpdateInfo(current="2.29.5", latest="2.30.0", changelog_md="x",
                         download_url=_DMG_URL, download_sha256=_SHA,
                         download_size=len(_PAYLOAD))


def test_update_dialog_inapp_download(monkeypatch, qapp, qtbot, tmp_path: Path) -> None:
    """Digest k dispozici → uložit jako… → stáhnout + ověřit → otevřít .dmg."""
    import bpdpmanager.ui.update_dialog as ud

    _FakeDesktop.opened = []
    monkeypatch.setattr(ud, "QDesktopServices", _FakeDesktop)
    target = tmp_path / "vybrane" / "BPDPManager-2.30.0-macos-arm64.dmg"
    target.parent.mkdir()
    asked: list[str] = []

    def fake_save(parent, title, default, flt):
        asked.append(default)
        return str(target), flt

    monkeypatch.setattr(ud.QFileDialog, "getSaveFileName", staticmethod(fake_save))
    _fake_urlopen(monkeypatch)

    dlg = ud.UpdateDialog(_inapp_info(), check_enabled=True,
                          download_dir=str(tmp_path))
    assert dlg.btn_update.text() == "⬇ Stáhnout a otevřít"
    dlg.btn_update.click()
    qtbot.waitUntil(lambda: dlg.downloaded_path is not None, timeout=5000)

    assert asked == [str(tmp_path / "BPDPManager-2.30.0-macos-arm64.dmg")]  # předvyplněno
    assert target.read_bytes() == _PAYLOAD
    assert dlg.download_dir == str(target.parent)               # zapamatuje se nová
    assert _FakeDesktop.opened == [f"file://{target}"]          # .dmg otevřen ve Finderu
    assert "ověřeno" in dlg.status.text() and dlg.btn_later.text() == "Zavřít"


def test_update_dialog_inapp_cancel_save_dialog_does_nothing(monkeypatch, qapp,
                                                             tmp_path: Path) -> None:
    import bpdpmanager.ui.update_dialog as ud

    monkeypatch.setattr(ud.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a: ("", "")))
    monkeypatch.setattr(uc, "download_update",
                        lambda *a, **k: pytest.fail("nemá se stahovat"))
    dlg = ud.UpdateDialog(_inapp_info(), check_enabled=True)
    dlg.btn_update.click()
    assert dlg.btn_update.isEnabled() and dlg._dl_worker is None


def test_update_dialog_default_path_falls_back_to_downloads(qapp, tmp_path: Path) -> None:
    import bpdpmanager.ui.update_dialog as ud

    dlg = ud.UpdateDialog(_inapp_info(), download_dir=str(tmp_path / "neexistuje"))
    assert dlg._default_download_path() == (
        Path.home() / "Downloads" / "BPDPManager-2.30.0-macos-arm64.dmg")
