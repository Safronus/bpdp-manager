"""Generování doporučených komentářů ke kontrole plagiátorství.

Komentáře se předvyplňují na základě verdiktu (radio button) + procenta
shody. Uživatel je může libovolně upravit.
"""

from __future__ import annotations

from ..models.enums import PlagiarismVerdict

# Hranice (v %), nad kterou u „není plagiát" doporučíme delší vysvětlení
# o očekávaných shodách (citace, šablony, běžné fráze).
HIGH_SIMILARITY_THRESHOLD = 20.0


def _fmt_pct(pct: float | None) -> str:
    """Naformátuje procento bez zbytečných nul (12.0 → „12", 12.3 → „12,3")."""
    if pct is None:
        return "—"
    # české desetinné čárky, bez koncových nul
    s = f"{pct:g}".replace(".", ",")
    return s


def suggest_comment(verdict: PlagiarismVerdict, pct: float | None) -> str:
    """Vrátí doporučený komentář pro daný verdikt + procento shody.

    Pro ``NOT_ASSESSED`` vrací prázdný string (nemá co doporučit).
    """
    pct_str = _fmt_pct(pct)
    if verdict == PlagiarismVerdict.NOT_ASSESSED:
        return ""
    if verdict == PlagiarismVerdict.PLAGIARISM:
        return (
            f"Práce byla posouzena na plagiátorství s maximální shodou {pct_str} %. "
            f"Na základě posouzení se jedná o plagiát."
        )
    # NOT_PLAGIARISM — dvě varianty podle výše shody
    if pct is not None and pct >= HIGH_SIMILARITY_THRESHOLD:
        return (
            f"Práce byla posouzena na plagiátorství s maximální shodou {pct_str} % "
            f"a nejedná se o plagiát. Vyšší míra shody je zapříčiněná soubory, "
            f"u kterých se shoda dá očekávat (citace, šablony, běžné odborné formulace)."
        )
    return (
        f"Práce byla posouzena na plagiátorství s maximální shodou {pct_str} % "
        f"a nejedná se o plagiát."
    )


def comment_variants(pct: float | None) -> list[tuple[str, str]]:
    """Vrátí seznam ``(label, text)`` všech doporučených variant.

    Slouží pro menu „Doporučený komentář" — uživatel si vybere konkrétní
    znění bez ohledu na aktuální verdikt.
    """
    pct_str = _fmt_pct(pct)
    return [
        (
            "Nízká shoda — není plagiát",
            f"Práce byla posouzena na plagiátorství s maximální shodou {pct_str} % "
            f"a nejedná se o plagiát.",
        ),
        (
            "Vyšší shoda — není plagiát (očekávané soubory)",
            f"Práce byla posouzena na plagiátorství s maximální shodou {pct_str} % "
            f"a nejedná se o plagiát. Vyšší míra shody je zapříčiněná soubory, "
            f"u kterých se shoda dá očekávat (citace, šablony, běžné odborné formulace).",
        ),
        (
            "Je plagiát",
            f"Práce byla posouzena na plagiátorství s maximální shodou {pct_str} %. "
            f"Na základě posouzení se jedná o plagiát.",
        ),
    ]
