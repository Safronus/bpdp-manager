"""Pojmenovávání a organizace nahrávaných souborů k pracem.

Cíl: jednotný název ``{Příjmení}_{typ}_{YYYY-MM-DD}[_vN].{ext}`` a roztřídění
do podsložek podle ``AttachmentKind``. Diakritika v příjmení se zachovává
(``Novák`` zůstává ``Novák``); strippují se jen znaky, které jsou problematické
na souborových systémech.

Modul je úmyslně bez závislosti na ``ThesisService`` / pydantic modelech —
přijímá primitivní vstupy, aby šel snadno testovat.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from ..models.enums import AttachmentKind

# --- mapování typu -> kód v názvu / podsložka ----------------------------

# Krátký kód, který se objeví v názvu souboru. Bez diakritiky a mezer.
KIND_TO_CODE: dict[AttachmentKind, str] = {
    AttachmentKind.THESIS_TEXT: "text-prace",
    AttachmentKind.THESIS_APPENDIX: "prilohy",
    AttachmentKind.WORK_JOURNAL: "pracovni-denik",
    AttachmentKind.ASSIGNMENT: "zadani",
    AttachmentKind.SUPERVISOR_REVIEW: "posudek-vedouciho",
    AttachmentKind.OPPONENT_REVIEW: "posudek-oponenta",
    AttachmentKind.PRESENTATION: "prezentace",
    AttachmentKind.DEFENSE_RECORD: "prubeh-obhajoby",
    AttachmentKind.STAG_EXPORT: "stag-export",
    AttachmentKind.OTHER: "jine",
}

# Podsložka uvnitř ``documents/{thesis_id}/``. Posudky (vedoucí + oponent)
# záměrně sdílí jednu složku — patří k sobě a obvykle se otevírají spolu.
KIND_TO_SUBDIR: dict[AttachmentKind, str] = {
    AttachmentKind.THESIS_TEXT: "text",
    AttachmentKind.THESIS_APPENDIX: "prilohy",
    AttachmentKind.WORK_JOURNAL: "denik",
    AttachmentKind.ASSIGNMENT: "zadani",
    AttachmentKind.SUPERVISOR_REVIEW: "posudky",
    AttachmentKind.OPPONENT_REVIEW: "posudky",
    AttachmentKind.PRESENTATION: "prezentace",
    AttachmentKind.DEFENSE_RECORD: "obhajoba",
    AttachmentKind.STAG_EXPORT: "stag",
    AttachmentKind.OTHER: "ostatni",
}

# Speciální kód/složka pro plagiátorský protokol (není v ``AttachmentKind``,
# řeší se vlastním flow přes ``set_plagiarism_pdf``).
PLAGIARISM_CODE = "protokol-plagiat"
PLAGIARISM_SUBDIR = "plagiat"


def subdir_for(kind: AttachmentKind) -> str:
    """Vrátí název podsložky pro daný typ přílohy."""
    return KIND_TO_SUBDIR[kind]


def code_for(kind: AttachmentKind) -> str:
    """Vrátí krátký kód použitý v názvu souboru."""
    return KIND_TO_CODE[kind]


# --- sanitizace ----------------------------------------------------------

# Znaky, které nelze (nebo by se nemělo) používat v názvech souborů napříč
# Windows/macOS/Linux. Diakritika tu **není** — Czech znaky zůstávají.
_FS_UNSAFE = re.compile(r'[\x00-\x1f/\\:*?"<>|]')
# Vícenásobné mezery/podtržítka → jedno podtržítko.
_SPACES = re.compile(r"[\s_]+")


def sanitize_for_fs(value: str) -> str:
    """Odstraní FS-nebezpečné znaky a sjednotí mezery na ``_``.

    Diakritika se zachovává. Prázdný/whitespace vstup vrátí prázdný string —
    volající si musí zařídit fallback.
    """
    if not value:
        return ""
    cleaned = _FS_UNSAFE.sub("", value)
    cleaned = _SPACES.sub("_", cleaned).strip("._-")
    return cleaned


# --- detekce data souboru ------------------------------------------------


def file_date(source_path: Path) -> date:
    """Datum vzniku/úpravy souboru. Fallback na dnešek, pokud ``stat`` selže."""
    try:
        mtime = source_path.stat().st_mtime
        return datetime.fromtimestamp(mtime).date()
    except OSError:
        return date.today()


# --- sestavení názvu -----------------------------------------------------


def _normalize_surname(surname: str | None) -> str:
    """Příjmení s diakritikou, ale FS-safe. Prázdné → ``Bez-prijmeni``."""
    cleaned = sanitize_for_fs(surname or "")
    return cleaned or "Bez-prijmeni"


def build_target_name(
    surname: str | None,
    kind: AttachmentKind,
    source_path: Path,
    existing_names: set[str] | None = None,
    file_date_override: date | None = None,
) -> str:
    """Sestaví cílový název souboru podle schématu ``{Příjmení}_{typ}_{YYYY-MM-DD}[_vN].{ext}``.

    Args:
        surname: Příjmení studenta. Diakritika se zachová, FS-nebezpečné
            znaky se strippují. Prázdné → ``Bez-prijmeni``.
        kind: Typ přílohy — určuje kód v názvu a podsložku.
        source_path: Cesta ke zdrojovému souboru (kvůli příponě a mtime).
        existing_names: Sada už použitých jmen v cílové podsložce. Pokud
            navrhované jméno koliduje, přidá se ``_v2``, ``_v3``, …
        file_date_override: Použij toto datum místo mtime souboru (pro
            plagiátorské PDF apod., kde mtime nedává smysl).

    Returns:
        Název souboru (bez cesty), připravený k uložení.
    """
    if existing_names is None:
        existing_names = set()

    norm_surname = _normalize_surname(surname)
    code = code_for(kind)
    d = file_date_override or file_date(source_path)
    suffix = source_path.suffix.lower()  # ``.pdf`` → ``.pdf``, ``.PDF`` → ``.pdf``

    base = f"{norm_surname}_{code}_{d.isoformat()}"
    candidate = f"{base}{suffix}"
    if candidate not in existing_names:
        return candidate

    n = 2
    while True:
        candidate = f"{base}_v{n}{suffix}"
        if candidate not in existing_names:
            return candidate
        n += 1


def build_plagiarism_name(
    surname: str | None,
    source_path: Path,
    existing_names: set[str] | None = None,
    file_date_override: date | None = None,
) -> str:
    """Verze ``build_target_name`` pro plagiátorský protokol.

    Plagiátorské PDF není v ``AttachmentKind`` (řeší se zvlášť v modelu Thesis),
    ale chceme mu dát stejný styl pojmenování.
    """
    if existing_names is None:
        existing_names = set()

    norm_surname = _normalize_surname(surname)
    d = file_date_override or file_date(source_path)
    suffix = source_path.suffix.lower()

    base = f"{norm_surname}_{PLAGIARISM_CODE}_{d.isoformat()}"
    candidate = f"{base}{suffix}"
    if candidate not in existing_names:
        return candidate

    n = 2
    while True:
        candidate = f"{base}_v{n}{suffix}"
        if candidate not in existing_names:
            return candidate
        n += 1


# --- heuristika typu z původního názvu -----------------------------------

# Pořadí pravidel záleží: specifičtější (posudek + vedouci) musí být před
# obecnějšími. ``re.IGNORECASE`` + diakritika v normalizovaném tvaru.
#
# Pozn.: heuristika se schválně dívá na ASCII-přepis i originál, aby chytila
# ``posudek_vedouciho.pdf`` i ``posudek_vedoucího.pdf``.
_HEURISTIC_RULES: list[tuple[re.Pattern[str], AttachmentKind]] = [
    (re.compile(r"posudek.*vedouc|posudek.*superv|superv.*review", re.IGNORECASE), AttachmentKind.SUPERVISOR_REVIEW),
    (re.compile(r"posudek.*opon|opon.*review|opponent", re.IGNORECASE), AttachmentKind.OPPONENT_REVIEW),
    (re.compile(r"zadani|assignment", re.IGNORECASE), AttachmentKind.ASSIGNMENT),
    (re.compile(r"prezent|slides|present", re.IGNORECASE), AttachmentKind.PRESENTATION),
    (re.compile(r"denik|journal|diary", re.IGNORECASE), AttachmentKind.WORK_JOURNAL),
    (re.compile(r"priloh|appendix|annex", re.IGNORECASE), AttachmentKind.THESIS_APPENDIX),
    # Protokol / zápis o průběhu obhajoby (státní závěrečné zkoušky).
    # Až po posudcích a prezentaci, aby je „obhajob" nepohltilo.
    (re.compile(r"obhajob|zapis.*(statni|zaverecn)|(prubeh|zaznam).*obhajob", re.IGNORECASE), AttachmentKind.DEFENSE_RECORD),
    # Text práce poznáváme z explicitních slov; samotná přípona PDF/DOCX nestačí
    # (mohl by to být kterýkoli z výše uvedených typů).
    (re.compile(r"text.*prace|prace.*text|thesis|bakal|diplom|bp[_\-\s]?text|dp[_\-\s]?text", re.IGNORECASE), AttachmentKind.THESIS_TEXT),
]

# Plagiátorský protokol řešíme zvlášť — vrací se ``None`` z hlediska
# ``AttachmentKind``, ale ``guess_is_plagiarism`` to detekuje pro upload flow.
_PLAGIARISM_RE = re.compile(r"plagiat|protokol|theses|antiplagi", re.IGNORECASE)


def _to_ascii_lossy(value: str) -> str:
    """Hrubý přepis diakritiky pro porovnávání. Není určen k zobrazení."""
    import unicodedata

    nfkd = unicodedata.normalize("NFKD", value)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def guess_kind_from_filename(filename: str) -> AttachmentKind | None:
    """Hádá typ přílohy z původního názvu souboru.

    Vrací ``None``, pokud žádné pravidlo nesedí — volající nechá uživatelovu
    aktuální volbu v ComboBoxu (typicky default ``OTHER`` nebo poslední výběr).
    """
    if not filename:
        return None
    # Porovnáváme na stem (bez přípony) v originále i ASCII verzi, aby
    # ``posudek_vedoucího.pdf`` i ``posudek_vedouciho.pdf`` chytly stejné pravidlo.
    stem = Path(filename).stem
    candidates = (stem, _to_ascii_lossy(stem))
    for pattern, kind in _HEURISTIC_RULES:
        if any(pattern.search(c) for c in candidates):
            return kind
    return None


def guess_is_plagiarism(filename: str) -> bool:
    """Vrátí True, pokud název souboru vypadá jako plagiátorský protokol."""
    if not filename:
        return False
    stem = Path(filename).stem
    return bool(_PLAGIARISM_RE.search(stem) or _PLAGIARISM_RE.search(_to_ascii_lossy(stem)))
