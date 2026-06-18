"""Výsledky státní závěrečné zkoušky (SZZ) jednoho studenta.

Data pocházejí z portálu IS/STAG „Zapisovatel u státnic" (jen po přihlášení,
role *Zapisovatel státnic*) — viz ``services/szz_parser.py`` a
``services/szz_portal.py``. Jediný spojovací klíč je **osobní číslo**
(``os_cislo``, Axxxxx); jméno je čistě zobrazovací.

Tři podstránky portletu (předmětové zkoušky / obhajoba / celková klasifikace)
se slévají do jednoho :class:`SzzRecord`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SubjectExam(BaseModel):
    """Jedna předmětová zkouška SZZ (zkoušející + známka + průběh)."""

    predmet: str = ""        # kód předmětu SZZ (AZINF, AZKYB, …)
    katedra: str = ""
    znamka: str = ""         # písmeno (A-F/FX)
    znamka_text: str = ""    # plný text ("A - výborně")
    zkousejici: str = ""     # jméno zkoušejícího (zobrazovací)
    ucitidno: str = ""       # ID zkoušejícího (stabilní klíč osoby)
    body: str = ""
    pokus: str = ""
    datum: str = ""
    jazyk: str = ""
    prubeh: str = ""         # text "Průběh zkoušky / rozpravy" (otázky/poznámky)


class ThesisDefense(BaseModel):
    """Obhajoba kvalifikační práce v rámci SZZ."""

    znamka: str = ""
    znamka_text: str = ""
    znamka_vedouci: str = ""
    znamka_oponent: str = ""
    zkousejici: str = ""
    ucitidno: str = ""
    datum: str = ""
    pokus: str = ""
    prubeh: str = ""
    adipidno: str = ""       # STAG ID práce (shodné s importem prací)


class SzzOverall(BaseModel):
    """Celkový výsledek SZZ studenta."""

    vysledek_zkousek: str = ""       # celkový výsledek SZZ (písmeno)
    vysledek_zkousek_text: str = ""
    vysledek_studia: str = ""        # text "Prospěl" / "Neprospěl"
    prospel: bool | None = None      # odvozeno z vysledek_studia
    pokus: str = ""
    misto: str = ""
    komise: str = ""                 # barva komise (fialová, …)
    datum: str = ""
    cas: str = ""
    poznamka: str = ""


class SzzRecord(BaseModel):
    """Kompletní SZZ záznam studenta (sloučení tří podstránek)."""

    os_cislo: str = ""
    jmeno: str = ""
    prijmeni: str = ""
    subjects: list[SubjectExam] = Field(default_factory=list)
    defense: ThesisDefense | None = None
    overall: SzzOverall | None = None
    fetched_at: str = ""             # ISO timestamp posledního stažení
    terminal: bool = False           # True = výsledek hotový (už nekontrolovat)
    unavailable: bool = False        # zatím nedostupné (nemáme přístup / komise
    #                                  ještě neproběhla) — nezahazovat, zkusit znovu
