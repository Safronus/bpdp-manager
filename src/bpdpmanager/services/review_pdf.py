"""Vyčtení navržené známky z PDF posudku.

Používá se u oponentur: když uživatel nahraje **PDF posudku vedoucího**
(externí vedoucí ho dodá hotové), zkusíme z něj přečíst navrženou známku
a doplnit ji do `grade_supervisor`. Funguje pro CZ i EN šablony FAI UTB.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

# pypdf u některých (mírně vadných) PDF spamuje varování „Ignoring wrong
# pointing object …" — pro nás neškodná, ztlumíme ji.
logging.getLogger("pypdf").setLevel(logging.ERROR)

# Navrženou známku hledáme u několika formulací (FAI UTB šablony, novější
# i historické). Záměrně NE u boilerplate „...v případě hodnocení stupněm
# F – nedostatečně...", které je v každém posudku — proto se vážeme na
# konkrétní návrhovou frázi (navrhuji / doporučuji hodnotit / navržená známka).
# FX musí být v alternaci první, jinak by „F" pohltilo „FX".
_GRADE_RE = re.compile(
    r"(?:"
    r"navržen[áé]\s+známka"                       # „Navržená známka: D"
    r"|navrhuji\s+hodnocení"                       # „navrhuji hodnocení B - velmi dobře"
    r"|navrhuji\s+(?:klasifikovat\s+stupněm|známku|hodnotit\s+stupněm)"
    r"|doporučuji\s+hodnotit\s+stupněm"            # „doporučuji hodnotit stupněm B"
    r"|hodnotit\s+stupněm"                         # „a doporučuji hodnotit stupněm B"
    r"|s\s+hodnocením"                             # „doporučuji k obhajobě s hodnocením B"
    r"|proposed\s+grade|suggested\s+grade"         # EN šablony
    r")"
    r"\s*[:\-]?\s*(FX|F|[A-E])\b",
    re.IGNORECASE,
)


def parse_grade_from_text(text: str) -> str | None:
    """Najde navrženou známku v textu posudku (CZ i EN). Vrací A–F / FX nebo None."""
    m = _GRADE_RE.search(text or "")
    return m.group(1).upper() if m else None


def extract_grade_from_pdf(path: Path) -> str | None:
    """Vrátí navrženou známku (A–F / FX) z PDF posudku, nebo ``None``."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:  # noqa: BLE001 — PDF nemusí jít přečíst, to není fatal
        return None
    return parse_grade_from_text(text)


def _read_docx_text(path: Path) -> str:
    """Vytáhne čistý text z .docx (ZIP s word/document.xml) bez závislostí."""
    import xml.etree.ElementTree as ET
    import zipfile

    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
    except Exception:  # noqa: BLE001 — vadný/neúplný .docx
        return ""
    try:
        root = ET.fromstring(xml)
    except Exception:  # noqa: BLE001
        return ""
    # Text je v <w:t> elementech (namespace wordprocessingml). Bereme všechny.
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    parts = [el.text or "" for el in root.iter(f"{ns}t")]
    return " ".join(parts)


def _read_doc_text(path: Path) -> str:
    """Převede starý binární .doc na text přes LibreOffice (``soffice``)."""
    import subprocess
    import tempfile

    soffice = _find_soffice()
    if soffice is None:
        return ""
    with tempfile.TemporaryDirectory() as tmp:
        try:
            subprocess.run(
                [
                    str(soffice),
                    "--headless",
                    "--convert-to", "txt:Text",
                    "--outdir", tmp,
                    str(path),
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
        except Exception:  # noqa: BLE001 — LO nemusí být/převod selže, není fatal
            return ""
        produced = Path(tmp) / (path.stem + ".txt")
        if not produced.is_file():
            txts = list(Path(tmp).glob("*.txt"))
            if not txts:
                return ""
            produced = txts[0]
        try:
            return produced.read_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            return ""


def _find_soffice() -> Path | None:
    """Najde ``soffice``/``libreoffice`` (PATH, macOS app, Linux distro)."""
    import shutil

    bin_path = shutil.which("soffice") or shutil.which("libreoffice")
    if bin_path:
        return Path(bin_path)
    mac_path = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    if mac_path.is_file():
        return mac_path
    for candidate in ("/usr/bin/soffice", "/usr/local/bin/soffice"):
        p = Path(candidate)
        if p.is_file():
            return p
    return None


def extract_grade_from_file(path: Path) -> str | None:
    """Vrátí navrženou známku z posudku dle přípony (PDF/DOCX/DOC), jinak ``None``.

    PDF čteme přes pypdf, .docx přímo ze ZIP/XML, starý binární .doc přes
    LibreOffice (``soffice --convert-to txt``). Vše je „best effort" — když
    nelze přečíst (chybí LibreOffice, vadný soubor), vrátíme ``None``.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_grade_from_pdf(path)
    if suffix == ".docx":
        return parse_grade_from_text(_read_docx_text(path))
    if suffix == ".doc":
        return parse_grade_from_text(_read_doc_text(path))
    return None
