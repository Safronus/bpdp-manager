"""Kontrola pravopisu (čeština) přes spylls + hunspell slovník.

Je **volitelná a bezpečná**: když chybí balík ``spylls`` nebo slovníkové
soubory, funkce se ladně vypne (``is_available()`` vrátí ``False`` a
``check_word`` nic nepodtrhává). Nabízí jen **detekci** a **návrhy** —
žádná autokorekce.

Slovník se hledá na dvou místech (první funkční vyhraje):

1. **přibalený** v ``resources/dictionaries/cs_CZ.{aff,dic}`` (LibreOffice,
   viz ``LICENSE_cs_CZ.txt``),
2. **stažený** uživatelem do ``~/.bpdpmanager/dictionaries/`` přes
   :func:`download_dictionary` — záchrana, když přibalený slovník chybí nebo
   je poškozený (např. po konverzi konců řádků na jiném OS / git autocrlf).

Engine ``spylls`` je čistě pythonní (žádný systémový balík / Homebrew).
"""

from __future__ import annotations

import functools
import ssl
import urllib.error
import urllib.request
from pathlib import Path

from ..config import app_data_dir

_DICT_BASENAME = "cs_CZ"

# Kanonický zdroj českého hunspell slovníku (LibreOffice dictionaries).
_DICT_URLS: dict[str, str] = {
    ".aff": "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/cs_CZ/cs_CZ.aff",
    ".dic": "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/cs_CZ/cs_CZ.dic",
}


def _bundled_base() -> Path:
    # services/spellcheck.py → services → bpdpmanager → resources/dictionaries
    return (
        Path(__file__).resolve().parent.parent
        / "resources" / "dictionaries" / _DICT_BASENAME
    )


def _user_dict_dir() -> Path:
    return app_data_dir() / "dictionaries"


def _user_base() -> Path:
    return _user_dict_dir() / _DICT_BASENAME


def _has_files(base: Path) -> bool:
    return base.with_suffix(".dic").is_file() and base.with_suffix(".aff").is_file()


@functools.lru_cache(maxsize=1)
def _load():
    """Načte slovník jednou (cache). Vrátí spylls Dictionary nebo None.

    Zkusí přibalený slovník, pak stažený uživatelský — první, který se načte.
    """
    try:
        from spylls.hunspell import Dictionary
    except Exception:  #spylls nemusí být nainstalován
        return None
    for base in (_bundled_base(), _user_base()):
        if not _has_files(base):
            continue
        try:
            return Dictionary.from_files(str(base))
        except Exception:  #vadný/nečitelný slovník zkus další
            continue
    return None


def spylls_installed() -> bool:
    try:
        import spylls  # noqa: F401
    except Exception:
        return False
    return True


def is_available() -> bool:
    """True, když je kontrola pravopisu k dispozici (spylls + slovník)."""
    return _load() is not None


def can_download() -> bool:
    """Lze nabídnout stažení slovníku? (Má smysl jen když je spylls nainstalován.)"""
    return spylls_installed()


def unavailable_reason() -> str:
    """Lidsky čitelný důvod, proč kontrola pravopisu není dostupná."""
    if not spylls_installed():
        return "není nainstalován balík spylls (pip install spylls)."
    if not (_has_files(_bundled_base()) or _has_files(_user_base())):
        return "chybí český slovník — můžeš ho stáhnout."
    return "slovník se nepodařilo načíst — zkus stáhnout čerstvou kopii."


def download_dictionary(timeout: float = 60.0) -> None:
    """Stáhne český hunspell slovník (LibreOffice) do ``~/.bpdpmanager/dictionaries/``.

    Při chybě vyhodí výjimku. Po úspěchu vyprázdní cache, takže se slovník
    při dalším :func:`is_available` načte. Zapisuje se až po úspěšném stažení
    obou souborů, aby na disku nezůstal poloviční slovník.
    """
    ctx = ssl.create_default_context()
    payload: dict[str, bytes] = {}
    for suffix, url in _DICT_URLS.items():
        req = urllib.request.Request(url, headers={"User-Agent": "BPDPManager"})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                data = resp.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(
                "Nepodařilo se stáhnout slovník (zkontroluj připojení k "
                f"internetu): {exc}"
            ) from exc
        if len(data) < 1024:
            raise RuntimeError(f"Stažený soubor {suffix} je podezřele malý.")
        payload[suffix] = data

    dest_dir = _user_dict_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    for suffix, data in payload.items():
        _user_base().with_suffix(suffix).write_bytes(data)
    _load.cache_clear()


def check_word(word: str) -> bool:
    """True = slovo je správně (nebo není slovník → nic nehlásíme)."""
    d = _load()
    if d is None or not word:
        return True
    try:
        return bool(d.lookup(word))
    except Exception:
        return True


def suggest(word: str, limit: int = 7) -> list[str]:
    """Návrhy oprav pro slovo (max ``limit``). Prázdné, když nejsou / chybí slovník."""
    d = _load()
    if d is None or not word:
        return []
    out: list[str] = []
    try:
        for s in d.suggest(word):
            out.append(s)
            if len(out) >= limit:
                break
    except Exception:
        return []
    return out
