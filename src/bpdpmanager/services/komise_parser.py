"""Parser fakultních PDF s komisemi SZZ (složení + rozpis studentů).

Dva druhy dokumentů (FAI UTB):

1. **Složení komisí** — text obsahuje bloky „Komise červená" (varianta A)
   nebo „Komise: žlutá" + „Datum: …" + „SP / SO/ specializace …" (varianta B)
   s rolemi Předseda / Místopředseda / Tajemník / Členové.
2. **Rozpis studentů** — jedna stránka = jedna komise; komise je daná
   **barvou nadpisů** (v textu jméno komise není). Hlavička nese program,
   specializaci a data; pod „Časový rozvrh" jsou sloupce po dnech s řádky
   ``HH:MM Axxxxx Jméno``.

Vše je čistá logika nad (text, barva) — testovatelné bez Qt. Barvy textu se
extrahují z content streamů (pypdf) — viz :func:`extract_pages`.
"""

from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass, field
from pathlib import Path

# ── klasifikace barvy ──────────────────────────────────────────────────────

def classify_color(rgb: tuple[float, float, float]) -> str:
    """RGB (0-1) → české jméno barvy komise (dle odstínu HSV)."""
    r, g, b = rgb
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if s < 0.15:                  # nenasycené — šedá/černá/bílá
        return "šedá"
    deg = h * 360
    if v < 0.45 and 15 <= deg <= 50:
        return "hnědá"
    if deg < 18 or deg >= 335:
        return "červená"
    if deg < 42:
        return "oranžová"
    if deg < 68:
        return "žlutá"
    if deg < 165:
        return "zelená"
    if deg < 200:
        return "tyrkysová"
    if deg < 262:
        return "modrá"
    if deg < 320:
        return "fialová"
    return "růžová"


# ── extrakce stránek (text + barva nadpisů) ────────────────────────────────

@dataclass
class PdfPage:
    text: str
    heading_color: str = ""      # české jméno barvy, "" když je vše černé


def extract_pages(path: Path) -> list[PdfPage]:
    """Načte PDF: text každé stránky + převažující ne-černou barvu textu.

    Barva nadpisů identifikuje komisi v rozpisech — sleduje se aktuální fill
    barva (operátory ``rg``/``g``/``sc``/``scn``) při textových operacích.
    """
    import collections

    from pypdf import PdfReader
    from pypdf.generic import ContentStream

    reader = PdfReader(str(path))
    pages: list[PdfPage] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        color_name = ""
        try:
            cs = ContentStream(page.get_contents(), reader)
            cur = (0.0, 0.0, 0.0)
            counts: collections.Counter = collections.Counter()
            for operands, op in cs.operations:
                if op == b"rg" and len(operands) == 3:
                    cur = tuple(float(x) for x in operands)
                elif op == b"g" and len(operands) == 1:
                    val = float(operands[0])
                    cur = (val, val, val)
                elif op in (b"sc", b"scn") and len(operands) == 3:
                    cur = tuple(float(x) for x in operands)
                elif op in (b"Tj", b"TJ", b"'", b'"'):
                    if cur != (0.0, 0.0, 0.0):
                        counts[cur] += 1
            if counts:
                color_name = classify_color(counts.most_common(1)[0][0])
        except Exception:  # bez barvy se obejdeme (jen rozpisy)
            color_name = ""
        pages.append(PdfPage(text=text, heading_color=color_name))
    return pages


# ── parsování složení komisí ───────────────────────────────────────────────

_ROLES = ("Předseda", "Místopředseda", "Tajemník", "Členové", "Člen")
_COLOR_WORDS = (
    "červená|modrá|zelená|žlutá|fialová|oranžová|růžová|tyrkysová|hnědá|šedá"
)
# Varianta A: „Komise cervena" / „Komise fialova (15.06.2026)"
_RE_COMMITTEE_A = re.compile(
    rf"^Komise\s+({_COLOR_WORDS})\s*(?:\(([^)]*)\))?\s*$", re.IGNORECASE | re.MULTILINE
)
# Varianta B: „Komise: žlutá"
_RE_COMMITTEE_B = re.compile(rf"^Komise:\s*({_COLOR_WORDS})\s*$", re.IGNORECASE | re.MULTILINE)
_RE_YEAR = re.compile(r"(\d{4}/\d{4})")
_RE_ROLE_LINE = re.compile(
    r"^(Předseda|Místopředseda|Tajemník|Členové|Člen)\s*:?\s*(.*)$"
)
# „Bc. - SWI, SWE: 15. - 16. 6. 2026" (hlavička varianty A)
_RE_LEVEL_LINE = re.compile(
    r"^(Bc|Mgr|Ing|Ph\.?D)\.?\s*[–\-—]\s*([^:]+?)\s*:\s*(.+)$"  # noqa: RUF001
)
_RE_DATE = re.compile(r"\d{1,2}\.\s*\d{1,2}\.\s*\d{4}|\d{2}\.\d{2}\.\d{4}")


def obor_from_program(program_label: str, level: str) -> str:
    """Z textu programu/specializace odvodí rodinu oboru aplikace.

    Bc → SWI/ITA, Mgr → NSWI/NKYB/NUI (prefix N = navazující). Slouží ke
    spárování rozpisu (i staršího importu složení) se správnou komisí —
    sama barva nestačí, protože např. Mgr fialová je NKYB i NUI.
    """
    t = (program_label or "").lower()
    mgr = "mgr" in (level or "").lower()
    toks = set(re.split(r"[^a-z]+", t))
    if "kybernet" in t or "kyb" in toks or "cyber" in t:
        return "NKYB"
    if "učitelstv" in t or "ucitelstv" in t or "ui" in toks:
        return "NUI"
    if "softwar" in t or "engineering" in t or "swi" in toks or "swe" in toks:
        return "NSWI" if mgr else "SWI"
    if "administrativ" in t or "ita" in toks:
        return "ITA"
    return ""


@dataclass
class ParsedCommittee:
    color: str = ""
    academic_year: str = ""
    level: str = ""
    obor: str = ""
    program_label: str = ""
    dates: list[str] = field(default_factory=list)
    members: list[tuple[str, str]] = field(default_factory=list)  # (role, jméno)


def parse_composition(text: str) -> list[ParsedCommittee]:
    """Z textu PDF „Složení komisí" vytáhne komise (obě varianty formátu)."""
    year = ""
    m = _RE_YEAR.search(text)
    if m:
        year = m.group(1)

    # Hlavička varianty A (stupeň + obory + data) — platí pro celý dokument.
    level = ""
    program = ""
    doc_dates: list[str] = []
    for line in text.splitlines():
        lm = _RE_LEVEL_LINE.match(line.strip())
        if lm:
            level = "Mgr" if lm.group(1).lower().startswith("mgr") else "Bc"
            program = lm.group(2).strip()
            doc_dates = _normalize_dates(lm.group(3))
            break
    if not level:   # varianta B: stupeň z textu „magisterský/bakalářský program"
        low = text.lower()
        if "magistersk" in low:
            level = "Mgr"
        elif "bakalářsk" in low:
            level = "Bc"

    # Najdi všechny začátky komisí (obou variant) a rozsekej text na bloky.
    starts: list[tuple[int, str, str]] = []   # (pozice, barva, poznámka)
    for m in _RE_COMMITTEE_A.finditer(text):
        starts.append((m.start(), m.group(1).lower(), (m.group(2) or "").strip()))
    for m in _RE_COMMITTEE_B.finditer(text):
        starts.append((m.start(), m.group(1).lower(), ""))
    starts.sort()
    # Dedup: nadpis „Komise červená …" těsně následovaný „Komise: červená"
    # je TENTÝŽ blok (varianta B má obojí) — ponech pozdější start.
    deduped: list[tuple[int, str, str]] = []
    for s in starts:
        if deduped and s[1] == deduped[-1][1] and s[0] - deduped[-1][0] < 160:
            deduped[-1] = (s[0], s[1], deduped[-1][2] or s[2])
        else:
            deduped.append(s)
    starts = deduped
    out: list[ParsedCommittee] = []
    for i, (pos, color, note) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        block = text[pos:end]
        c = ParsedCommittee(color=color, academic_year=year, level=level,
                            program_label=program)
        # Datum: z poznámky v závorce, řádku „Datum:" v bloku, jinak z hlavičky.
        block_dates = _normalize_dates(note)
        dm = re.search(r"^Datum:\s*(.+)$", block, re.MULTILINE)
        if dm:
            block_dates = block_dates or _normalize_dates(dm.group(1))
        c.dates = block_dates or list(doc_dates)
        # „SP / SO/ specializace …" v bloku (varianta B) upřesní program.
        sm = re.search(r"specializace\s+(.+?)\s*$", block, re.MULTILINE)
        if sm and not program:
            c.program_label = sm.group(1).strip()
        # Role — řádek po řádku; pokračovací řádky (bez role) patří k Členům.
        current_role = ""
        for raw in block.splitlines()[1:]:
            line = raw.strip()
            if not line or line.lower().startswith(("komise", "datum:", "sp / so")):
                continue
            rm = _RE_ROLE_LINE.match(line)
            if rm:
                role = "Člen" if rm.group(1) == "Členové" else rm.group(1)
                current_role = role
                name = rm.group(2).strip()
                if name:
                    c.members.append((role, name))
            elif current_role and _looks_like_name(line):
                c.members.append(("Člen" if current_role == "Člen" else current_role,
                                  line))
        c.obor = obor_from_program(c.program_label, c.level)
        if c.members:
            out.append(c)
    return out


def _looks_like_name(line: str) -> bool:
    """Heuristika: řádek vypadá jako jméno (ne nadpis/program/datum)."""
    if len(line) > 90 or _RE_DATE.search(line):
        return False
    low = line.lower()
    bad = ("program", "specializ", "komise", "zkoušk", "study", "stát")
    return not any(b in low for b in bad)


def _normalize_dates(s: str) -> list[str]:
    """Vytáhne všechna data z textu („15. - 16. 6. 2026" → 2 položky)."""
    if not s:
        return []
    out = list(_RE_DATE.findall(s))
    # „15. - 16. 6. 2026" - prvni cislo je den bez mesice/roku; doplni se z druheho.
    m = re.search(r"(\d{1,2})\.\s*[–\-—]\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", s)  # noqa: RUF001
    if m:
        d1, d2, mo, yr = m.groups()
        out = [f"{d1}. {mo}. {yr}", f"{d2}. {mo}. {yr}"]
    return [canonical_date(d) for d in out]


def canonical_date(d: str) -> str:
    """Sjednotí zápis data na „D. M. RRRR" („15.06.2026" → „15. 6. 2026")."""
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", d)
    if not m:
        return re.sub(r"\s+", " ", d).strip()
    return f"{int(m.group(1))}. {int(m.group(2))}. {m.group(3)}"


# ── parsování rozpisu studentů ─────────────────────────────────────────────

_RE_SLOT = re.compile(r"(\d{1,2}:\d{2})\s+(A\d{5})\s+(.+?)(?=\s+\d{1,2}:\d{2}\s+A\d{5}|\s*$)")
_RE_HEADER_DATES = re.compile(r"^\s*((?:\d{1,2}\.\s*\d{1,2}\.\s*\d{4}\s*)+)$")


@dataclass
class ParsedSchedule:
    color: str = ""
    academic_year: str = ""
    level: str = ""
    obor: str = ""
    program_label: str = ""
    dates: list[str] = field(default_factory=list)
    slots: list[tuple[str, str, str, str]] = field(default_factory=list)
    # (datum, čas, osobní číslo, jméno)


def academic_year_from_date(date_str: str) -> str:
    """„15. 6. 2026" → „2025/2026" (ak. rok začíná v září)."""
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", date_str)
    if not m:
        return ""
    month, year = int(m.group(2)), int(m.group(3))
    return f"{year}/{year + 1}" if month >= 9 else f"{year - 1}/{year}"


def parse_schedule_page(text: str, heading_color: str) -> ParsedSchedule | None:
    """Z jedné stránky rozpisu vytáhne komisi (barva), program, data a sloty."""
    if "Časový rozvrh" not in text:
        return None
    lines = [ln.strip() for ln in text.splitlines()]
    ps = ParsedSchedule(color=heading_color)

    # Program = řádek za „… studijním programu"; specializace za „specializace:".
    program = ""
    spec = ""
    for i, ln in enumerate(lines):
        if "studijním programu" in ln and i + 1 < len(lines):
            program = lines[i + 1]
        if ln.lower().startswith("specializace") and i + 1 < len(lines):
            spec = lines[i + 1]
    ps.program_label = spec or program
    if program and spec and spec != program:
        ps.program_label = f"{program} — {spec}"
    low = f"{program} {spec} {text[:400]}".lower()
    if "(mgr" in low or "magistersk" in low:
        ps.level = "Mgr"
    elif "(bc" in low or "bakalářsk" in low:
        ps.level = "Bc"
    ps.obor = obor_from_program(f"{program} {spec}", ps.level)

    # Data: řádky hlavičky pod „Časový rozvrh" obsahují jen data (1-2 sloupce).
    rozvrh_idx = next(
        (i for i, ln in enumerate(lines) if "Časový rozvrh" in ln), 0
    )
    col_dates: list[str] = []
    for ln in lines[rozvrh_idx + 1:]:
        m = _RE_HEADER_DATES.match(ln)
        if m:
            col_dates = _RE_DATE.findall(ln)
            break
        if _RE_SLOT.search(ln):
            break
    if not col_dates:
        # fallback: data z hlavičky dokumentu (řádky ZLÍN …)
        col_dates = _RE_DATE.findall(" ".join(lines[:rozvrh_idx]))
        col_dates = list(dict.fromkeys(col_dates))[:2]
    ps.dates = [canonical_date(d) for d in col_dates]
    if ps.dates:
        ps.academic_year = academic_year_from_date(ps.dates[0])

    # Sloty: na řádku může být 1-2 zápisy (sloupec 1 = 1. datum, 2 = 2. datum).
    for ln in lines[rozvrh_idx + 1:]:
        matches = list(_RE_SLOT.finditer(ln))
        for k, m in enumerate(matches):
            date = ps.dates[k] if k < len(ps.dates) else (ps.dates[0] if ps.dates else "")
            name = re.sub(r"\s+", " ", m.group(3)).strip()
            ps.slots.append((date, m.group(1), m.group(2), name))
    return ps if ps.slots else None


# ── auto-detekce druhu dokumentu ───────────────────────────────────────────

@dataclass
class ParsedPdf:
    committees: list[ParsedCommittee] = field(default_factory=list)
    schedules: list[ParsedSchedule] = field(default_factory=list)


def parse_pdf(path: Path) -> ParsedPdf:
    """Naparsuje PDF — sám pozná složení komisí vs. rozpis (po stránkách)."""
    out = ParsedPdf()
    pages = extract_pages(Path(path))
    # Složení: parsuje se z CELÉHO textu (bloky můžou přetékat přes stránky).
    full_text = "\n".join(p.text for p in pages)
    if _RE_COMMITTEE_A.search(full_text) or _RE_COMMITTEE_B.search(full_text):
        out.committees = parse_composition(full_text)
    # Rozpisy: stránka po stránce (každá má vlastní barvu komise).
    for p in pages:
        if "Časový rozvrh" in p.text:
            ps = parse_schedule_page(p.text, p.heading_color)
            if ps is not None:
                out.schedules.append(ps)
    return out
