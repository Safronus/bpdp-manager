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
logger = logging.getLogger(__name__)

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
    """Vrátí navrženou známku (A–F / FX) z PDF posudku, nebo ``None``.

    Posudky stažené ze STAG bývají **AES-šifrované** (prázdné uživatelské heslo,
    jen omezení práv) — pypdf je umí dešifrovat jen s knihovnou ``cryptography``
    (proto závislost ``pypdf[crypto]``). Bez ní by extrakce textu tiše selhala
    a známka by se nenačetla.
    """
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:  # noqa: BLE001 — PDF nemusí jít přečíst, to není fatal
        # Logujeme (debug) — ať je důvod „nenačtené známky" dohledatelný.
        logger.debug("Nelze přečíst PDF posudku %s", path, exc_info=True)
        return None
    return parse_grade_from_text(text)


# Položka rozevíracího seznamu vypadá jako známka (např. „C - dobře").
_GRADE_OPTION_RE = re.compile(rf"\s*{_GRADE}\b")


def _text_from_docx_xml(xml: str) -> str:
    """Čistý text z ``word/document.xml`` (všechny ``<w:t>`` elementy)."""
    import xml.etree.ElementTree as ET

    if not xml:
        return ""
    try:
        root = ET.fromstring(xml)
    except Exception:  # noqa: BLE001 — vadné XML
        return ""
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    return " ".join(el.text or "" for el in root.iter(f"{ns}t"))


def _grade_from_docx_xml(xml: str) -> str | None:
    """Navržená známka z **formulářového rozevíracího pole** posudku.

    Starší (Wordové) posudky FAI mají známku jako *drop-down* ve větě „…navrhuji
    hodnocení [A-F]". Hodnota v poli je **autoritativní** (volný text typu
    „s hodnocením B-C" je jen orientační a může se lišit). Najdeme dropdown,
    jehož položky vypadají jako známky, a vrátíme *vybranou* hodnotu — dropdowny
    oboru / „doporučuji" se přeskočí.
    """
    for block in re.findall(r"<w:ddList\b.*?</w:ddList>", xml, re.DOTALL):
        entries = re.findall(r'<w:listEntry\s+w:val="([^"]*)"', block)
        if sum(1 for e in entries if _GRADE_OPTION_RE.match(e)) < 3:
            continue  # málo položek tvaru „A …" → není to známkový dropdown
        res = re.search(r'<w:result\s+w:val="(\d+)"', block)
        idx = int(res.group(1)) if res else 0   # bez <result> = první (= „vyberte")
        if 0 <= idx < len(entries):
            m = _GRADE_OPTION_RE.match(entries[idx])
            if m:
                return m.group(1).upper()
    return None


def _docx_document_xml(path: Path) -> str:
    """Vrátí ``word/document.xml`` z .docx (ZIP), nebo prázdný řetězec."""
    import zipfile

    try:
        with zipfile.ZipFile(path) as zf:
            return zf.read("word/document.xml").decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 — vadný/neúplný .docx
        return ""


def _doc_to_docx_xml(path: Path) -> str:
    """Převede starý binární .doc na .docx (LibreOffice) a vrátí document.xml.

    Převod na **.docx** (ne txt) schválně — txt zahodí formulářová pole, kdežto
    .docx zachová rozevírací seznam se známkou.
    """
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
                    "--convert-to", "docx",
                    "--outdir", tmp,
                    str(path),
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
        except Exception:  # noqa: BLE001 — LO nemusí být/převod selže, není fatal
            return ""
        produced = Path(tmp) / (path.stem + ".docx")
        if not produced.is_file():
            cand = list(Path(tmp).glob("*.docx"))
            if not cand:
                return ""
            produced = cand[0]
        return _docx_document_xml(produced)


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

    PDF čteme přes pypdf (text), Word (.docx přímo, starý .doc přes LibreOffice
    do .docx). U Wordu má přednost **formulářové rozevírací pole** se známkou
    (autoritativní), a teprve když není, použije se **volný text** posudku.
    Vše je „best effort" — když nelze přečíst (chybí LibreOffice, vadný soubor),
    vrátíme ``None``.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_grade_from_pdf(path)
    if suffix == ".docx":
        xml = _docx_document_xml(path)
    elif suffix == ".doc":
        xml = _doc_to_docx_xml(path)
    else:
        return None
    return _grade_from_docx_xml(xml) or parse_grade_from_text(_text_from_docx_xml(xml))
