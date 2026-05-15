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
