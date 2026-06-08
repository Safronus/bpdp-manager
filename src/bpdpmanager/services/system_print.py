"""Tisk PDF na systémovou tiskárnu (CUPS ``lp``) — alternativa k MyQ.

Seznam tiskáren bere z Qt (``QPrinterInfo`` — funguje cross-platform),
samotný tisk posílá přes ``lp`` (CUPS), který pošle **původní PDF** rovnou
do tiskové fronty ovladače (bez překreslování → plná kvalita).

Podporováno na macOS / Linux (CUPS). Na Windows ``lp`` není — tam se
:func:`system_print_available` vrátí ``False`` a tisk vyhodí chybu.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PrinterInfo:
    name: str        # název CUPS fronty (pro ``lp -d``)
    label: str       # lidsky čitelný popis (pro UI)
    is_default: bool


def list_printers() -> list[PrinterInfo]:
    """Seznam systémových tiskáren (výchozí jako první, je-li známá)."""
    try:
        from PySide6.QtPrintSupport import QPrinterInfo
    except Exception:  # pragma: no cover - QtPrintSupport by měl být vždy
        return []
    default_name = ""
    d = QPrinterInfo.defaultPrinter()
    if not d.isNull():
        default_name = d.printerName()
    printers: list[PrinterInfo] = []
    for p in QPrinterInfo.availablePrinters():
        name = p.printerName()
        label = (p.description() or "").strip() or name
        printers.append(
            PrinterInfo(name=name, label=label, is_default=(name == default_name))
        )
    printers.sort(key=lambda p: (not p.is_default, p.label.lower()))
    return printers


def system_print_available() -> bool:
    """True, když lze tisknout přes systém (CUPS ``lp``)."""
    return sys.platform != "win32" and shutil.which("lp") is not None


def print_pdf(
    pdf_path: str | Path,
    printer_name: str,
    *,
    duplex: bool = True,
    copies: int = 1,
) -> None:
    """Vytiskne PDF na zvolenou tiskárnu přes ``lp``. Chybu vyhodí jako výjimku."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise RuntimeError(f"Soubor neexistuje: {pdf_path}")
    if not printer_name:
        raise RuntimeError("Není vybraná tiskárna.")
    if not system_print_available():
        raise RuntimeError(
            "Systémový tisk (CUPS/lp) není na tomto systému dostupný."
        )
    cmd = ["lp", "-d", printer_name]
    if copies and copies > 1:
        cmd += ["-n", str(copies)]
    cmd += ["-o", "sides=two-sided-long-edge" if duplex else "sides=one-sided"]
    cmd.append(str(pdf_path))
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"Tisk se nepodařilo spustit: {exc}") from exc
    if res.returncode != 0:
        detail = (res.stderr or res.stdout or "").strip() or "lp vrátil chybu"
        raise RuntimeError(f"Tisk selhal: {detail}")
