from __future__ import annotations

import os
from pathlib import Path

import pytest

from bpdpmanager.config import ENV_DATA_DIR


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Každý test má vlastní izolovaný datový adresář — nikdy nepíše do ~/.bpdpmanager."""
    data_dir = tmp_path / "data"
    monkeypatch.setenv(ENV_DATA_DIR, str(data_dir))
    return data_dir


#: Akademický rok, pro který jsou testovací data komisí (seed komise_szz.json,
#: rozpisy červen 2026).
TEST_ACADEMIC_YEAR = "2025/2026"


@pytest.fixture
def academic_year_2025_26(monkeypatch: pytest.MonkeyPatch) -> str:
    """Zafixuje „aktuální akademický rok" na rok testovacích dat komisí.

    ``ThesisService.current_academic_year`` čte ``date.today()`` a aplikace
    počítá oponované práce jen z aktuálního roku. Testy s daty pro 2025/2026 by
    jinak od 1. 9. 2026 (přechod na 2026/2027) začaly padat — časová bomba.
    Zapíná se v modulu přes ``pytestmark = pytest.mark.usefixtures(...)``.
    """
    from bpdpmanager.services import ThesisService

    monkeypatch.setattr(ThesisService, "current_academic_year",
                        staticmethod(lambda: TEST_ACADEMIC_YEAR))
    return TEST_ACADEMIC_YEAR
