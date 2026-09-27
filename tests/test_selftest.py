"""Smoke test instalace (``--self-test``) + CLI drobnosti pro zabalenou aplikaci."""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import pytest


def test_selftest_passes_from_source_and_restores_env(monkeypatch, tmp_path) -> None:
    from bpdpmanager.config import ENV_DATA_DIR
    from bpdpmanager.selftest import run_selftest

    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    buf = io.StringIO()
    assert run_selftest(buf) == 0, buf.getvalue()
    out = buf.getvalue()
    assert "SELF-TEST OK" in out and "❌" not in out
    # self-test běží nad VLASTNÍ dočasnou složkou a původní hodnotu vrátí
    assert os.environ[ENV_DATA_DIR] == str(tmp_path)
    assert not any(tmp_path.iterdir())          # do naší složky nic nezapsal


def test_selftest_reports_missing_resource(monkeypatch) -> None:
    import bpdpmanager.selftest as st

    monkeypatch.setattr(st, "REQUIRED_FILES",
                        (*st.REQUIRED_FILES, "resources/neexistuje.txt"))
    buf = io.StringIO()
    assert st.run_selftest(buf) == 1
    out = buf.getvalue()
    assert "❌ soubor resources/neexistuje.txt" in out
    assert "SELF-TEST SELHAL (1 chyb)" in out


def test_main_version_ignores_macos_psn_argument(monkeypatch, capsys) -> None:
    from bpdpmanager import __version__
    from bpdpmanager.__main__ import main

    # Finder občas předá „-psn_…" — argparse na něm nesmí spadnout.
    monkeypatch.setattr(sys, "argv", ["bpdp-manager", "-psn_0_12345", "--version"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert f"BPDPManager {__version__}" in capsys.readouterr().out


def test_restart_command_source_and_frozen(monkeypatch) -> None:
    from bpdpmanager.services.update_checker import restart_command

    assert restart_command() == [sys.executable, "-m", "bpdpmanager"]
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    # zabalená appka: binárka sama, žádné „-m bpdpmanager" (argparse by spadl)
    assert restart_command() == [sys.executable]


def test_examples_dir_source_and_frozen(monkeypatch, tmp_path) -> None:
    from bpdpmanager.__main__ import _examples_dir

    assert (_examples_dir() / "seed_demo.json").is_file()      # ze zdrojů
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert _examples_dir() == Path(tmp_path) / "examples"      # v bundlu
