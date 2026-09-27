"""Vypíše poznámky k GitHub Release pro danou verzi ze sekce v CHANGELOG.md.

Použití (CI):  python scripts/release_notes.py 2.30.0 > notes.md

Když CHANGELOG sekci ``## [X.Y.Z]`` pro verzi nemá, skončí chybou — release se
pak nevytvoří a CI zčervená (verze bez changelogu je chyba procesu).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bpdpmanager.services.update_checker import (  # noqa: E402 — po úpravě sys.path
    DMG_SUFFIX,
    parse_changelog_sections,
)

INSTALL_NOTE = (
    "---\n\n"
    "**Instalace (macOS, Apple Silicon):** stáhni `BPDPManager-{version}"
    f"{DMG_SUFFIX}` níže, otevři ho a přetáhni **BPDPManager** do složky "
    "**Aplikace**. Aplikace je podepsaná jen ad-hoc (bez Apple Developer účtu), "
    "takže ji macOS po stažení prohlížečem napoprvé zablokuje („nelze otevřít“): "
    "otevři **Nastavení systému → Soukromí a zabezpečení** a dole u BPDPManageru "
    "klikni na **Přesto otevřít**. Stačí jednou — další verze si aplikace "
    "stáhne a ověří sama a macOS už je neblokuje."
)


def release_notes(version: str, changelog: str) -> str:
    """Tělo poznámek: sekce verze bez nadpisu + instalační návod."""
    sections = dict(parse_changelog_sections(changelog))
    section = sections.get(version)
    if not section:
        raise KeyError(version)
    body = section.split("\n", 1)[1].strip() if "\n" in section else ""
    return f"{body}\n\n{INSTALL_NOTE.format(version=version)}\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Použití: release_notes.py <verze>", file=sys.stderr)
        return 2
    version = argv[1]
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    try:
        sys.stdout.write(release_notes(version, changelog))
    except KeyError:
        print(f"CHANGELOG.md nemá sekci [{version}] — doplň ji a pushni znovu.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
