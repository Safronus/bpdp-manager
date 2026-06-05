"""Skládání jména s tituly před/za.

Tituly se ukládají jako volné stringy (např. ``"doc. Ing."`` a ``"Ph.D."``
nebo ``", Ph.D."``). ``compose_titled_name`` je poskládá do jednoho jména
``„doc. Ing. Petr Novák, Ph.D."`` — vkládá mezery, ale respektuje čárku na
začátku titulu za jménem (aby nevznikla mezera před čárkou).
"""

from __future__ import annotations


def compose_titled_name(
    title_before: str | None, name: str | None, title_after: str | None
) -> str:
    """Poskládá ``"titul_před Jméno titul_za"`` (prázdné části vynechá)."""
    before = (title_before or "").strip()
    base = (name or "").strip()
    after = (title_after or "").strip()

    out = f"{before} {base}".strip() if before else base
    if after:
        sep = "" if after[0] in ",;" else " "
        out = f"{out}{sep}{after}".strip()
    return out
