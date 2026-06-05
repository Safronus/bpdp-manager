"""Sdílené OS akce — otevření souboru/URL a zobrazení ve správci souborů.

Sjednocuje dříve duplikovanou logiku (``open`` / ``xdg-open`` / ``os.startfile``
a „reveal in Finder") z několika dialogů na jedno místo. UI vrstva volá tyto
helpery místo vlastních ``subprocess`` bloků.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def open_path(target: str | Path) -> None:
    """Otevře soubor nebo URL v přidružené aplikaci (best-effort)."""
    target = str(target)
    if sys.platform == "darwin":
        subprocess.run(["open", target], check=False)
    elif sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", target], check=False)
    elif sys.platform == "win32":
        try:
            os.startfile(target)  # type: ignore[attr-defined]
        except OSError:
            pass


def reveal_in_file_manager(path: str | Path) -> None:
    """Zobrazí soubor ve správci souborů (Finder / Explorer / file manager).

    Na macOS a Windows soubor rovnou označí; na Linuxu (kde univerzální
    „reveal" neexistuje) otevře nadřazenou složku.
    """
    path = Path(path)
    if sys.platform == "darwin":
        subprocess.run(["open", "-R", str(path)], check=False)
    elif sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", str(path.parent)], check=False)
    elif sys.platform == "win32":
        try:
            subprocess.run(["explorer", "/select,", str(path)], check=False)
        except OSError:
            pass
