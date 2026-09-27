"""Kontrola aktualizací aplikace proti GitHubu + provedení update.

Zdroj pravdy je ``CHANGELOG.md`` v ``main`` větvi na GitHubu (Keep a Changelog
formát — sekce ``## [X.Y.Z] - datum``). Z něj se vyčte nejnovější verze i
changelog všech verzí mezi nainstalovanou a nejnovější.

Dva režimy:

* **Git klon** — update = ``git pull --ff-only`` v kořeni klonu + ``pip install
  -e .`` (kvůli novým závislostem) + restart aplikace.
* **Zabalená aplikace** (PyInstaller ``.app``) — nejnovější verze se bere
  z posledního *vydaného* GitHub Release (ne z CHANGELOGu: sekce v CHANGELOGu
  existuje dřív, než CI release dostaví). Update = stažení nového ``.dmg``
  v prohlížeči; výměnu aplikace dokončí uživatel (přetáhnout do Aplikací).

Jiná instalace (např. pip bez klonu) aktualizovat neumí — kontrola se neprovádí.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

#: Raw CHANGELOG.md v main větvi — jeden HTTP GET, žádné API limity.
CHANGELOG_URL = (
    "https://raw.githubusercontent.com/Safronus/bpdp-manager/main/CHANGELOG.md"
)

#: Poslední vydaný Release (pro zabalenou aplikaci) — veřejné API, bez tokenu
#: (limit 60 dotazů/h na IP; kontrola běží jednou po startu).
RELEASES_API = "https://api.github.com/repos/Safronus/bpdp-manager/releases/latest"
#: Jen odkazy s tímto prefixem se smí otevřít v prohlížeči (obrana proti
#: podvržené/nečekané odpovědi API).
RELEASES_URL_PREFIX = "https://github.com/Safronus/bpdp-manager/releases/"
#: Záloha, když Release nemá .dmg asset nebo URL neprojde validací.
RELEASES_PAGE = RELEASES_URL_PREFIX + "latest"
#: Koncovka instalačního souboru, který vyrábí CI (scripts/build_macos.sh).
DMG_SUFFIX = "-macos-arm64.dmg"

_SECTION_RE = re.compile(r"^## \[(\d+(?:\.\d+)*)\]", re.MULTILINE)


def is_frozen() -> bool:
    """True, když aplikace běží jako zabalená (PyInstaller .app)."""
    return bool(getattr(sys, "frozen", False))


def parse_version(s: str) -> tuple[int, ...]:
    """„1.17.4" → (1, 17, 4); nečíselné části se ignorují (robustní řazení)."""
    parts = []
    for p in (s or "").strip().split("."):
        digits = "".join(ch for ch in p if ch.isdigit())
        if digits:
            parts.append(int(digits))
    return tuple(parts) or (0,)


def parse_changelog_sections(text: str) -> list[tuple[str, str]]:
    """Rozseká CHANGELOG.md na [(verze, markdown sekce vč. nadpisu), …].

    Sekce ``## [Unreleased]`` se přeskočí. Pořadí dle souboru (nejnovější první).
    """
    matches = list(_SECTION_RE.finditer(text))
    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((m.group(1), text[start:end].strip()))
    return out


@dataclass
class UpdateInfo:
    """Dostupná aktualizace: nejnovější verze + changelog verzí mezi."""

    current: str
    latest: str
    changelog_md: str                      # spojené sekce novějších verzí
    versions: list[str] = field(default_factory=list)
    #: Zabalená aplikace: odkaz ke stažení nového .dmg (prázdné = git režim).
    download_url: str = ""


def fetch_changelog(timeout: float = 6.0) -> str:
    """Stáhne raw CHANGELOG.md z GitHubu. Při chybě vyhodí výjimku."""
    import urllib.request

    req = urllib.request.Request(
        CHANGELOG_URL, headers={"User-Agent": "bpdp-manager-update-check"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def check_for_update(current_version: str, changelog_text: str | None = None) -> UpdateInfo | None:
    """Vrátí ``UpdateInfo``, když je na GitHubu novější verze; jinak ``None``.

    ``changelog_text`` lze předat v testech; jinak se stáhne z GitHubu
    (výjimky síťové vrstvy propadají volajícímu — ten je tiše spolkne).
    """
    text = changelog_text if changelog_text is not None else fetch_changelog()
    sections = parse_changelog_sections(text)
    if not sections:
        return None
    cur = parse_version(current_version)
    newer = [(v, md) for v, md in sections if parse_version(v) > cur]
    if not newer:
        return None
    return UpdateInfo(
        current=current_version,
        latest=newer[0][0],
        changelog_md="\n\n".join(md for _v, md in newer),
        versions=[v for v, _md in newer],
    )


def _safe_release_url(url: object) -> str:
    """Vrátí ``url`` jen když míří do Releases tohoto repozitáře, jinak zálohu."""
    if isinstance(url, str) and url.startswith(RELEASES_URL_PREFIX):
        return url
    return RELEASES_PAGE


def parse_latest_release(data: object) -> tuple[str, str]:
    """Z JSON odpovědi ``releases/latest`` vytáhne ``(verze, odkaz ke stažení)``.

    Preferuje ``.dmg`` asset (``*-macos-arm64.dmg``), jinak stránku Release.
    Neplatná odpověď → ``ValueError`` (volající ji tiše spolkne).
    """
    if not isinstance(data, dict):
        raise ValueError("Neočekávaná odpověď GitHub API.")
    tag = data.get("tag_name")
    if not isinstance(tag, str) or parse_version(tag) == (0,):
        raise ValueError(f"Release bez platného tagu: {tag!r}")
    version = tag[1:] if tag[:1] in ("v", "V") else tag
    url = ""
    for asset in data.get("assets") or []:
        if isinstance(asset, dict) and str(asset.get("name", "")).endswith(DMG_SUFFIX):
            url = asset.get("browser_download_url", "")
            break
    return version, _safe_release_url(url or data.get("html_url"))


def fetch_latest_release(timeout: float = 6.0) -> tuple[str, str]:
    """Stáhne poslední vydaný GitHub Release → ``(verze, odkaz ke stažení)``."""
    import json
    import urllib.request

    req = urllib.request.Request(
        RELEASES_API,
        headers={"User-Agent": "bpdp-manager-update-check",
                 "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return parse_latest_release(json.loads(resp.read().decode("utf-8")))


def check_for_frozen_update(
    current_version: str,
    *,
    release: tuple[str, str] | None = None,
    changelog_text: str | None = None,
) -> UpdateInfo | None:
    """Kontrola pro zabalenou aplikaci: nejnovější verze = poslední Release.

    Changelog se dočte z CHANGELOG.md (jen verze ``aktuální < v ≤ release``);
    když se ho nepodaří stáhnout, nabídne se update i tak (bez novinek).
    ``release``/``changelog_text`` lze předat v testech.
    """
    latest, url = release if release is not None else fetch_latest_release()
    cur, top = parse_version(current_version), parse_version(latest)
    if top <= cur:
        return None
    try:
        text = changelog_text if changelog_text is not None else fetch_changelog()
        sections = parse_changelog_sections(text)
    except Exception:  # offline apod. — update nabídnout i bez novinek
        sections = []
    newer = [(v, md) for v, md in sections if cur < parse_version(v) <= top]
    return UpdateInfo(
        current=current_version,
        latest=latest,
        changelog_md="\n\n".join(md for _v, md in newer),
        versions=[v for v, _md in newer] or [latest],
        download_url=url,
    )


def repo_root() -> Path | None:
    """Kořen git klonu, ze kterého aplikace běží; ``None`` mimo klon."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    return None


def _run(cmd: list[str], cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
    )


def is_repo_dirty(root: Path) -> bool:
    """True, když má klon necommitnuté změny (pull by mohl selhat)."""
    res = _run(["git", "status", "--porcelain"], root, timeout=30)
    return bool(res.stdout.strip())


def perform_update(root: Path) -> tuple[bool, str]:
    """Provede ``git pull --ff-only`` + ``pip install -e .``.

    Vrací ``(ok, zpráva)`` — zpráva je lidsky čitelný popis výsledku/chyby.
    Nikdy nepřepisuje lokální změny (ff-only; špinavý klon hlásí předem).
    """
    if is_repo_dirty(root):
        return False, (
            "V instalační složce jsou neuložené lokální změny — aktualizace by "
            "je mohla poškodit. Ukliď je (commit / stash) a zkus to znovu."
        )
    pull = _run(["git", "pull", "--ff-only"], root)
    if pull.returncode != 0:
        err = (pull.stderr or pull.stdout or "").strip().splitlines()
        return False, "git pull selhal: " + (err[-1] if err else "neznámá chyba")
    # Doinstalovat případné nové závislosti (např. pypdf[crypto] v 1.17.1) —
    # bez toho by update mohl aplikaci rozbít chybějící knihovnou.
    pip = _run([sys.executable, "-m", "pip", "install", "-e", str(root), "-q"], root)
    if pip.returncode != 0:
        err = (pip.stderr or pip.stdout or "").strip().splitlines()
        return False, (
            "Kód je aktualizovaný (git pull OK), ale instalace závislostí "
            "selhala: " + (err[-1] if err else "neznámá chyba")
        )
    return True, "Aktualizace proběhla. Aplikace se restartuje."


def restart_command() -> list[str]:
    """Příkaz pro spuštění nové instance aplikace.

    Ze zdrojů ``python -m bpdpmanager``; v zabalené aplikaci (PyInstaller) je
    ``sys.executable`` samotná binárka aplikace — ``-m bpdpmanager`` by dostala
    jako neznámé argumenty a nová instance by se vůbec nespustila.
    """
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "bpdpmanager"]


def restart_app() -> None:
    """Spustí novou instanci aplikace a ukončí tuto (po update / změně jazyka)."""
    from PySide6.QtWidgets import QApplication

    subprocess.Popen(restart_command())  # nezávislý proces
    app = QApplication.instance()
    if app is not None:
        app.quit()
