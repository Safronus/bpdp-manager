"""Kontrola aktualizací aplikace proti GitHubu + provedení update.

Zdroj pravdy je ``CHANGELOG.md`` v ``main`` větvi na GitHubu (Keep a Changelog
formát — sekce ``## [X.Y.Z] - datum``). Z něj se vyčte nejnovější verze i
changelog všech verzí mezi nainstalovanou a nejnovější.

Update = ``git pull --ff-only`` v kořeni klonu + ``pip install -e .`` (kvůli
novým závislostem) + restart aplikace. Funguje jen když aplikace běží z git
klonu (jiná instalace nemá jak updatovat — kontrola se pak neprovádí).
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

_SECTION_RE = re.compile(r"^## \[(\d+(?:\.\d+)*)\]", re.MULTILINE)


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


def restart_app() -> None:
    """Spustí novou instanci aplikace a ukončí tuto (po úspěšném update)."""
    from PySide6.QtWidgets import QApplication

    subprocess.Popen([sys.executable, "-m", "bpdpmanager"])  # nezávislý proces
    app = QApplication.instance()
    if app is not None:
        app.quit()
