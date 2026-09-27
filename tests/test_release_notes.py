"""Poznámky k GitHub Release z CHANGELOG.md (scripts/release_notes.py)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "release_notes.py"

_CHANGELOG = """# Changelog

## [Unreleased]

## [2.30.0] - 2026-09-27

### Added
- Spustitelna aplikace.

## [2.29.5] - 2026-06-20

### Fixed
- Stara oprava.
"""


def _load():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import release_notes
    finally:
        sys.path.pop(0)
    return release_notes


def test_release_notes_section_without_heading() -> None:
    rn = _load()
    notes = rn.release_notes("2.30.0", _CHANGELOG)
    assert notes.startswith("### Added")               # nadpis verze odříznut
    assert "Spustitelna aplikace." in notes
    assert "Stara oprava" not in notes                 # jen tahle verze
    assert "BPDPManager-2.30.0-macos-arm64.dmg" in notes
    assert "pravý klik → Otevřít" in notes


def test_release_notes_missing_version_raises() -> None:
    rn = _load()
    with pytest.raises(KeyError):
        rn.release_notes("9.9.9", _CHANGELOG)


def test_release_notes_cli_on_real_changelog() -> None:
    # Skutečný CHANGELOG musí mít sekci pro aktuální __version__ — jinak by CI
    # po bumpu verze nevydalo release.
    from bpdpmanager import __version__

    ok = subprocess.run([sys.executable, str(SCRIPT), __version__],
                        capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    assert f"BPDPManager-{__version__}-macos-arm64.dmg" in ok.stdout
    bad = subprocess.run([sys.executable, str(SCRIPT), "0.0.0"],
                         capture_output=True, text=True)
    assert bad.returncode == 1 and "nemá sekci" in bad.stderr
