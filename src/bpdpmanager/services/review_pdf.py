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

# Navrženou známku čteme přednostně ze STRUKTUROVANÉHO pole „Navržená známka"
# (FAI UTB šablony). To je autoritativní; volný text v „Celkovém hodnocení"
# (např. „navrhuji hodnocení A") je u tohoto stylu jen orientační a může se
# s tabulkou rozcházet — proto se používá jen jako fallback u STARŠÍCH posudků,
# které strukturované pole vůbec nemají. FX je v alternaci první, jinak by „F"
# pohltilo „FX".
_GRADE = r"(FX|F|[A-E])"

# Hodnota přímo za polem (i přes zalomení): „Navržená známka: D" / „…:\nA".
_FIELD_INLINE_RE = re.compile(
    r"(?:navržen[áé]\s+známka|navržen[áé]\s+klasifikace"
    r"|výsledn[áé]\s+klasifikace|proposed\s+grade|suggested\s+grade)"
    rf"\s*[:\-]?\s*{_GRADE}\b",
    re.IGNORECASE,
)
# Samotný popisek pole (i bez hodnoty vedle) — značí strukturovaný posudek.
_FIELD_LABEL_RE = re.compile(
    r"navržen[áé]\s+známka|navržen[áé]\s+klasifikace"
    r"|výsledn[áé]\s+klasifikace|proposed\s+grade|suggested\s+grade",
    re.IGNORECASE,
)
# Známka jako samostatný řádek — hodnota buňky tabulky, kterou PDF extrakce
# „rozhodí" mimo popisek (typicky generované FAI posudky).
_STANDALONE_GRADE_RE = re.compile(rf"^[ \t]*{_GRADE}[ \t]*$", re.MULTILINE)
# Orientační závěrová fráze — fallback jen pro posudky BEZ strukturovaného pole.
_CONCLUSION_RE = re.compile(
    r"(?:navrhuji\s+hodnocení"
    r"|navrhuji\s+(?:klasifikovat\s+stupněm|známku|hodnotit\s+stupněm)"
    r"|doporučuji\s+hodnotit\s+stupněm|hodnotit\s+stupněm|s\s+hodnocením)"
    rf"\s*[:\-]?\s*{_GRADE}\b",
    re.IGNORECASE,
)


def parse_grade_from_text(text: str) -> str | None:
    """Najde navrženou známku v textu posudku (CZ i EN). Vrací A–F / FX nebo None.

    Priorita: 1) hodnota přímo u pole „Navržená známka", 2) je-li pole přítomné
    (strukturovaný posudek), samostatná známka z rozhozené tabulky — závěrová
    věta se ignoruje jako orientační, 3) u starších posudků bez pole závěrová
    fráze („navrhuji hodnocení …").
    """
    text = text or ""
    m = _FIELD_INLINE_RE.search(text)
    if m:
        return m.group(1).upper()
    if _FIELD_LABEL_RE.search(text):
        # Pole je autoritativní. Hodnotu vezmeme ze samostatného řádku, jen když
        # je jednoznačná (právě jedna známka) — jinak raději nic (uživatel doplní).
        uniq = {g.upper() for g in _STANDALONE_GRADE_RE.findall(text)}
        return next(iter(uniq)) if len(uniq) == 1 else None
    m3 = _CONCLUSION_RE.search(text)
    return m3.group(1).upper() if m3 else None


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
        # Izolovaný profil LO — jinak ``--headless`` zamrzne, když uživatel
        # má LibreOffice otevřené v GUI (sdílený zámek profilu).
        lo_profile = (Path(tmp) / "loprofile").as_uri()
        try:
            subprocess.run(
                [
                    str(soffice),
                    f"-env:UserInstallation={lo_profile}",
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
