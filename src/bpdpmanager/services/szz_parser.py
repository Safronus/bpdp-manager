"""Parser HTML portálu IS/STAG „Zapisovatel u státnic" (3 podstránky).

Čistá logika nad vyrenderovaným HTML (bez sítě a UI). Vstup = HTML jedné
podstránky portletu ``ZapisovatelUStatnicPortlet``:

- ``zaverecne-zkousky``   → předměty SZZ (zkoušející/známka/body/průběh),
- ``obhajoba-kv-prace``   → obhajoba práce (hodnocení, vedoucí/oponent),
- ``celkova-klasifikace`` → celkový výsledek SZZ (prospěl/neprospěl, komise).

Tři podstránky se slévají přes **osobní číslo** do :class:`SzzRecord`.
Síťové stažení (přihlášený webview) řeší ``services/szz_portal.py``.
"""

from __future__ import annotations

import html
import re

from ..models.szz_result import (
    SubjectExam,
    SzzOverall,
    SzzRecord,
    ThesisDefense,
)

KNOWN_PAGES = ("zaverecne-zkousky", "obhajoba-kv-prace", "celkova-klasifikace")


# ── nízkoúrovňové helpery ─────────────────────────────────────────────────
def _clean(s: str) -> str:
    """HTML → čistý text: nejdřív unescape (kvůli ``&lt;p&gt;`` v CKEditoru),
    pak strip tagů a normalizace mezer."""
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _input_value(block: str, name: str) -> str:
    pat_a = r'<input[^>]*\bname="' + re.escape(name) + r'"[^>]*\bvalue="([^"]*)"'
    pat_b = r'<input[^>]*\bvalue="([^"]*)"[^>]*\bname="' + re.escape(name) + r'"'
    m = re.search(pat_a, block, re.I) or re.search(pat_b, block, re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def _select_selected(block: str, name: str) -> tuple[str, str]:
    """(value, text) vybrané ``<option selected>`` v ``<select name=NAME>``."""
    ms = re.search(
        r'<select[^>]*\bname="' + re.escape(name) + r'"[^>]*>(.*?)</select>',
        block, re.S | re.I)
    if not ms:
        return ("", "")
    mo = re.search(
        r'<option[^>]*\bvalue="([^"]*)"[^>]*\bselected[^>]*>(.*?)</option>',
        ms.group(1), re.S | re.I)
    return (html.unescape(mo.group(1)).strip(), _clean(mo.group(2))) if mo else ("", "")


def _textarea(block: str, name: str) -> str:
    m = re.search(
        r'<textarea[^>]*\bname="' + re.escape(name) + r'"[^>]*>(.*?)</textarea>',
        block, re.S | re.I)
    return _clean(m.group(1)) if m else ""


def _letter(text: str) -> str:
    """„A - výborně" → „A"."""
    return text.split(" - ")[0].strip() if text else ""


# ── detekce stránky / role / přihlášení ───────────────────────────────────
def detect_page_name(html_text: str) -> str:
    """Aktivní podstránka Zapisovatele (víc portletů → preferuj známou)."""
    vals = re.findall(
        r'name="FORM_portlet_page_name"[^>]*\bvalue="([^"]*)"', html_text)
    vals += re.findall(
        r'\bvalue="([^"]*)"[^>]*name="FORM_portlet_page_name"', html_text)
    for v in vals:
        if v in KNOWN_PAGES:
            return v
    return vals[0] if vals else ""


def is_logged_in(html_text: str) -> bool:
    """Přihlášen = stránka Zapisovatele má vyhledávací pole studenta."""
    return 'name="studentSearchOsCislo"' in html_text


def detect_role(html_text: str) -> str:
    """Text vybrané role z ``<select name=identifikatorRole>``."""
    return _select_selected(html_text, "identifikatorRole")[1]


def has_zapisovatel_role(html_text: str) -> bool:
    """Má přihlášený uživatel roli *Zapisovatel státnic*?"""
    return "zapisovatel st" in detect_role(html_text).lower()


# ── parsery jednotlivých podstránek ───────────────────────────────────────
_SUBJECT_FORM_RE = re.compile(
    r'<form\b[^>]*\bname="(ZUSStatnicovePredmety[^"]+)"[^>]*>', re.I)
_INSTANCE_RE = re.compile(
    r'^([A-Z0-9]+)_([A-Z0-9]+)_\d+_\d+_[A-Z]+_(A\w+)$', re.I)


def parse_subjects(html_text: str) -> tuple[str, list[SubjectExam]]:
    os_cislo = ""
    subjects: list[SubjectExam] = []
    for m in _SUBJECT_FORM_RE.finditer(html_text):
        start = m.end()
        end = html_text.find("</form>", start)
        block = html_text[start:end if end > 0 else start + 12000]
        katedra = predmet = oc = ""
        im = _INSTANCE_RE.match(_input_value(block, "FORM_INSTANCE_ID"))
        if im:
            katedra, predmet, oc = im.group(1), im.group(2), im.group(3)
        os_cislo = os_cislo or oc
        _, ztxt = _select_selected(block, "prZnamka")
        subjects.append(SubjectExam(
            predmet=predmet, katedra=katedra,
            znamka=_letter(ztxt), znamka_text=ztxt,
            zkousejici=_input_value(block, "prZkousejici"),
            ucitidno=_input_value(block, "prUcitidno"),
            body=_input_value(block, "prZiskanychBodu"),
            pokus=_input_value(block, "prCisloPokusu"),
            datum=_input_value(block, "prDatum"),
            jazyk=_select_selected(block, "prJazyk")[1],
            prubeh=_textarea(block, "prPrubeh"),
        ))
    return os_cislo, subjects


def parse_defense(html_text: str) -> ThesisDefense:
    _, ztxt = _select_selected(html_text, "obhajobaZnamka")
    return ThesisDefense(
        znamka=_letter(ztxt), znamka_text=ztxt,
        znamka_vedouci=_select_selected(html_text, "znamkaVedouci")[1],
        znamka_oponent=_select_selected(html_text, "znamkaOponent")[1],
        zkousejici=_input_value(html_text, "obhajobaZkousejici"),
        ucitidno=_input_value(html_text, "obhajobaUcitidno"),
        datum=_input_value(html_text, "obhajobaDatum"),
        pokus=_input_value(html_text, "obhajobaCisloPokusu"),
        prubeh=_textarea(html_text, "obhajobaPrubeh"),
        adipidno=_input_value(html_text, "obhajobaAdipidno"),
    )


def parse_overall(html_text: str) -> SzzOverall:
    _, vzt = _select_selected(html_text, "ckVysledekZkousek")
    studia = _select_selected(html_text, "ckVysledekStudia")[1]
    prospel = studia.strip().lower().startswith("prospěl") if studia else None
    return SzzOverall(
        vysledek_zkousek=_letter(vzt), vysledek_zkousek_text=vzt,
        vysledek_studia=studia, prospel=prospel,
        pokus=_input_value(html_text, "ckPokus"),
        misto=_select_selected(html_text, "ckMisto")[1],
        komise=_input_value(html_text, "ckKomise"),
        datum=_input_value(html_text, "ckDatum"),
        cas=_input_value(html_text, "ckCas"),
        poznamka=_textarea(html_text, "ckPoznamkaZoszz"),
    )


def parse_page(html_text: str) -> SzzRecord:
    """Naparsuje jednu podstránku → (částečný) SzzRecord."""
    rec = SzzRecord()
    page = detect_page_name(html_text)
    if page == "zaverecne-zkousky":
        rec.os_cislo, rec.subjects = parse_subjects(html_text)
    elif page == "obhajoba-kv-prace":
        rec.defense = parse_defense(html_text)
    elif page == "celkova-klasifikace":
        rec.overall = parse_overall(html_text)
        rec.os_cislo = _input_value(html_text, "ckOsCislo")
    return rec


def merge_pages(*recs: SzzRecord) -> SzzRecord:
    """Sloučí částečné záznamy ze tří podstránek (klíč = os. číslo)."""
    out = SzzRecord()
    for r in recs:
        out.os_cislo = out.os_cislo or r.os_cislo
        if r.subjects:
            out.subjects = r.subjects
        if r.defense:
            out.defense = r.defense
        if r.overall:
            out.overall = r.overall
    out.terminal = is_terminal(out)
    return out


def is_terminal(rec: SzzRecord) -> bool:
    """Hotový výsledek (už se nekontroluje): vyplněná celková **ZNÁMKA** SZZ.

    Záměrně se řídí známkou (``vysledek_zkousek``), ne textem „Prospěl/Neprospěl"
    (``vysledek_studia``) — ten může mít default i u nehodnocených, takže by se
    studenti „bez známky" nesprávně přeskakovali při kontrole zbývajících.
    """
    return bool(rec.overall and rec.overall.vysledek_zkousek)


def szz_to_check(oscisla, cache: dict, force: bool) -> list[str]:
    """Které osobní čísla zkontrolovat: deduplikuje a (není-li ``force``)
    **přeskočí hotové** (terminal v cache) — inkrementální/aditivní kontrola.

    Zachovává pořadí. ``cache`` je ``{os_cislo: SzzRecord}`` z
    ``ThesisService.load_szz_results()``.
    """
    out: list[str] = []
    for oc in oscisla:
        oc = (oc or "").strip()
        if not oc or oc in out:
            continue
        if not force:
            rec = cache.get(oc)
            # Živě (ne jen uložený příznak) — promítne i opravu definice terminal
            # do starší cache: „bez známky" i „nedostupné" se znovu zkontrolují.
            if rec is not None and is_terminal(rec):
                continue
        out.append(oc)
    return out
