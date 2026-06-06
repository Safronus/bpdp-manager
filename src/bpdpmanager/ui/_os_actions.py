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


def print_path(path: str | Path) -> str:
    """Vytiskne soubor (best-effort). Vrací ``"printed"`` (odesláno na výchozí
    tiskárnu), ``"opened"`` (otevřeno v aplikaci k ručnímu tisku) nebo
    ``"error"``.

    - Windows: ``startfile(…, "print")`` (přes přidruženou aplikaci).
    - macOS/Linux: PDF se pošle na výchozí tiskárnu přes ``lpr`` (CUPS);
      ostatní formáty (XLSX…) se otevřou v aplikaci, ať uživatel vytiskne
      sám (Cmd/Ctrl+P) — tisk přes CUPS by je nezpracoval správně.
    """
    p = Path(path)
    if not p.is_file():
        return "error"
    try:
        if sys.platform == "win32":
            os.startfile(str(p), "print")  # type: ignore[attr-defined]
            return "printed"
        if p.suffix.lower() == ".pdf":
            subprocess.run(["lpr", str(p)], check=True)
            return "printed"
        open_path(p)
        return "opened"
    except Exception:  # noqa: BLE001
        return "error"


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
