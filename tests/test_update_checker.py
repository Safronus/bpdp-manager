"""Kontrola aktualizací — parsování CHANGELOG, porovnání verzí, update kroky."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

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


def test_parse_latest_release_prefers_dmg() -> None:
    data = {
        "tag_name": "v2.30.0",
        "html_url": _REL + "tag/v2.30.0",
        "assets": [
            {"name": "poznamky.txt", "browser_download_url": _REL + "download/x.txt"},
            {"name": "BPDPManager-2.30.0-macos-arm64.dmg",
             "browser_download_url": _DMG_URL},
        ],
    }
    assert uc.parse_latest_release(data) == ("2.30.0", _DMG_URL)


def test_parse_latest_release_fallbacks_and_url_validation() -> None:
    # bez .dmg assetu → stránka Release
    no_dmg = {"tag_name": "v2.30.0", "html_url": _REL + "tag/v2.30.0", "assets": []}
    assert uc.parse_latest_release(no_dmg) == ("2.30.0", _REL + "tag/v2.30.0")
    # odkaz mimo náš repozitář se NIKDY neotevře → bezpečná záloha
    evil = {"tag_name": "v2.30.0", "html_url": "https://evil.example/r",
            "assets": [{"name": "BPDPManager-2.30.0-macos-arm64.dmg",
                        "browser_download_url": "https://evil.example/x.dmg"}]}
    assert uc.parse_latest_release(evil) == ("2.30.0", uc.RELEASES_PAGE)
    # neplatná odpověď → ValueError
    with pytest.raises(ValueError):
        uc.parse_latest_release({"tag_name": "latest"})
    with pytest.raises(ValueError):
        uc.parse_latest_release(["není", "dict"])


def test_check_for_frozen_update_limits_to_release() -> None:
    # CHANGELOG už má 1.19.0, ale CI ho ještě nevydalo → nesmí se nabídnout.
    changelog = "## [1.19.0] - 2026-06-12\n\n- Budoucí verze\n\n" + _CHANGELOG
    info = uc.check_for_frozen_update(
        "1.17.3", release=("1.18.0", _DMG_URL), changelog_text=changelog)
    assert info is not None
    assert info.latest == "1.18.0" and info.download_url == _DMG_URL
    assert info.versions == ["1.18.0", "1.17.4"]
    assert "Budoucí verze" not in info.changelog_md
    # aktuální / novější než release → nic
    assert uc.check_for_frozen_update(
        "1.18.0", release=("1.18.0", _DMG_URL), changelog_text=changelog) is None
    assert uc.check_for_frozen_update(
        "1.19.0", release=("1.18.0", _DMG_URL), changelog_text=changelog) is None


def test_check_for_frozen_update_offline_changelog(monkeypatch) -> None:
    def boom():
        raise OSError("offline")

    monkeypatch.setattr(uc, "fetch_changelog", boom)
    info = uc.check_for_frozen_update("1.0.0", release=("1.1.0", _DMG_URL))
    assert info is not None and info.changelog_md == "" and info.versions == ["1.1.0"]


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


def test_update_dialog_download_mode(monkeypatch, qapp) -> None:
    import bpdpmanager.ui.update_dialog as ud

    opened: list[str] = []

    class _FakeDesktop:
        @staticmethod
        def openUrl(url) -> bool:  # noqa: N802 (Qt API)
            opened.append(url.toString())
            return True

    monkeypatch.setattr(ud, "QDesktopServices", _FakeDesktop)
    monkeypatch.setattr(uc, "perform_update",
                        lambda root: pytest.fail("v .app se nesmí dělat git pull"))
    info = uc.UpdateInfo(current="2.29.5", latest="2.30.0", changelog_md="",
                         download_url=_DMG_URL)
    dlg = ud.UpdateDialog(info, check_enabled=True)
    assert dlg.btn_update.text().startswith("⬇")
    assert "stránce vydání" in dlg.changelog.toPlainText()   # prázdný changelog
    dlg.btn_update.click()
    assert opened == [_DMG_URL]
    assert not dlg.btn_update.isEnabled()
    assert ".dmg" in dlg.status.text() and "Aplikace" in dlg.status.text()
