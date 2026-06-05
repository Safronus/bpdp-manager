"""Extrakce strukturálního schématu z XLSX šablony posudku.

Heuristika nad FAI UTB šablonami:

- Kritéria hodnocení leží v souvislé sekci, typicky řádek 17 hlavička
  (``A="Kritérium hodnocení"``, ``C="Váha"``, ``D="Body (0–5)"``)
  a následují páry (label + weight + score) / (sub-description).

- Detekce řádku jako kritéria:
    * ``A`` má neprázdný text
    * ``C`` má numerickou hodnotu (váha, např. 0.5 nebo 1.0)
    * ``D`` má numerickou hodnotu (přednastavené skóre, typicky 5)
    * ani ``C`` ani ``D`` není formule (``=...``)

- Konec sekce kritérií: řádek s formulí v ``C`` (``=SUM(...)``) nebo
  ``A=="Celkový součet vážených bodů:"``.

Pak ještě hledáme zvláštní pole pro snazší vyplňování:
- ``Splnění bodů zadání`` → buňka v ``C`` daného řádku
- ``Výsledek kontroly plagiátorství`` → ``C``
- ``Zdůvodnění výsledku kontroly plagiátorství`` → následující řádek
- ``Celkové hodnocení práce, připomínky a dotazy`` → 3 řádky dole

Modul je úmyslně bez závislosti na pydantic/PySide6 — vrací plain
dict, který volající (``ThesisService``) předá do
``ReviewTemplate.criteria`` / ``field_cells``.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any


def _ascii_fold_lower(s: str) -> str:
    if not s:
        return ""
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if not unicodedata.combining(c)).lower()


def _is_numeric(value: Any) -> bool:
    """True pokud value je číslo (int/float) — ne formule, ne string s číslem."""
    if isinstance(value, bool):
        return False  # bool je instance int, ale ne chceme
    if isinstance(value, (int, float)):
        return True
    return False


# ── Title patterns (pro detekci typu + role + jazyka z A6) ──────────────────
# A6 obsahuje hlavičku jako "POSUDEK VEDOUCÍHO BAKALÁŘSKÉ PRÁCE",
# "POSUDEK OPONENTA DIPLOMOVÉ PRÁCE", "SUPERVISOR'S REPORT ON BACHELOR THESIS"
# atd. Z toho dovodíme type / role / language.

_TITLE_TYPE_ROLE_LANG: list[tuple[re.Pattern[str], dict]] = [
    # CZ
    (re.compile(r"posudek\s+vedouciho\s+bakalarske"),
     {"type": "BP", "role": "supervisor", "language": "cs"}),
    (re.compile(r"posudek\s+oponenta\s+bakalarske"),
     {"type": "BP", "role": "opponent", "language": "cs"}),
    (re.compile(r"posudek\s+vedouciho\s+diplomove"),
     {"type": "DP", "role": "supervisor", "language": "cs"}),
    (re.compile(r"posudek\s+oponenta\s+diplomove"),
     {"type": "DP", "role": "opponent", "language": "cs"}),
    # EN
    (re.compile(r"supervisor.*report.*bachelor"),
     {"type": "BP", "role": "supervisor", "language": "en"}),
    (re.compile(r"opponent.*report.*bachelor"),
     {"type": "BP", "role": "opponent", "language": "en"}),
    (re.compile(r"supervisor.*report.*master"),
     {"type": "DP", "role": "supervisor", "language": "en"}),
    (re.compile(r"opponent.*report.*master"),
     {"type": "DP", "role": "opponent", "language": "en"}),
]

# Mapování specializace / studijního programu → krátký kód oboru, který
# používáme v ReviewTemplate.obor. Pro DP je kód v specializaci (B11),
# pro BP v programu (B10).
_PROGRAM_TO_OBOR: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"softwar[oóô]v[ée]\s+in[zžZ]en[ýy]rstv[ií]", re.IGNORECASE), "SWI"),
    (re.compile(r"software\s+engineering", re.IGNORECASE), "SWI"),
    (re.compile(r"kybernetick[áa]\s+bezpe[čc]nost", re.IGNORECASE), "KYB"),
    (re.compile(r"cyber\s+security", re.IGNORECASE), "KYB"),
    (re.compile(r"u[čc]itelstv[ií]\s+informatiky", re.IGNORECASE), "UI"),
    (re.compile(r"informatics\s+teaching", re.IGNORECASE), "UI"),
    (re.compile(r"informa[čc]n[ií]\s+technologie\s+v\s+administrativ", re.IGNORECASE), "ITA"),
    (re.compile(r"aplikovan[áa]\s+informatika.*pr[ůu]myslov", re.IGNORECASE), "AIPA"),
    (re.compile(r"bezpe[čc]nostn[ií]\s+technologie", re.IGNORECASE), "BTSM"),
    (re.compile(r"automatick[ée]\s+[řr][ií]zen[ií]", re.IGNORECASE), "ARI"),
]


def _guess_obor_code(specialization: str, study_program: str) -> str:
    """Z popisu specializace / programu odhadne krátký kód (SWI, KYB, UI, ...).

    Zkouší se nejdřív specialization (B11), pak study_program (B10) — protože
    pro DP je obor v specializaci, pro BP v programu.
    """
    for text in (specialization, study_program):
        if not text or not text.strip() or text.strip() == "-":
            continue
        for pattern, code in _PROGRAM_TO_OBOR:
            if pattern.search(text):
                return code
    return ""


# Patterns pro speciální pole (CZ + EN, normalized lowercase + ASCII-fold)
_FIELD_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^\s*splneni\s+vsech\s+bodu\s+zadani"), "assignment_fulfilled"),
    (re.compile(r"^\s*fulfilment\s+of\s+all\s+assignment\s+points"), "assignment_fulfilled"),
    (re.compile(r"^\s*vysledek\s+kontroly\s+plagi"), "plagiarism_verdict"),
    (re.compile(r"^\s*plagiarism\s+check\s+result"), "plagiarism_verdict"),
    (re.compile(r"^\s*zduvodneni\s+vysledku\s+kontroly\s+plagi"), "plagiarism_justification"),
    (re.compile(r"^\s*plagiarism\s+check\s+justification"), "plagiarism_justification"),
    (re.compile(r"^\s*celkove\s+hodnoceni"), "overall_comment"),
    (re.compile(r"^\s*overall\s+evaluation"), "overall_comment"),
    (re.compile(r"^\s*misto,?\s*datum"), "place_date"),
    (re.compile(r"^\s*place,?\s*date"), "place_date"),
]


def extract_template_schema(template_path: Path) -> dict:
    """Otevře XLSX šablonu a vrátí strukturální schema.

    Returns:
        ``{
            "criteria": [
                {"row": 18, "label": "...", "default_weight": 1.0,
                 "weight_cell": "C18", "score_cell": "D18"},
                ...
            ],
            "field_cells": {
                "assignment_fulfilled": "C15",
                "plagiarism_verdict": "C39",
                "plagiarism_justification": "A41",  # nebo merge B41…
                "overall_comment": "A44",
                "place_date": "A49",
            },
        }``

    Pokud žádné kritérium nedetekuje, ``criteria`` je prázdný list — UI
    si zvolí fallback ručního vyplnění bez bodování.
    """
    from .review_template_filler import load_template_workbook

    wb = load_template_workbook(template_path, data_only=False)
    ws = wb.active

    criteria: list[dict] = []
    field_cells: dict[str, str] = {}

    max_row = min(ws.max_row, 200)  # bezpečnostní strop

    for row_idx in range(1, max_row + 1):
        a = ws.cell(row=row_idx, column=1).value
        c = ws.cell(row=row_idx, column=3).value
        d = ws.cell(row=row_idx, column=4).value

        # Kritéria — A=text, C=numeric weight, D=numeric score, žádné formule
        if (
            isinstance(a, str)
            and a.strip()
            and _is_numeric(c)
            and _is_numeric(d)
            and not (isinstance(c, str) and c.startswith("="))
            and not (isinstance(d, str) and d.startswith("="))
        ):
            criteria.append({
                "row": row_idx,
                "label": a.strip(),
                "default_weight": float(c),
                "weight_cell": f"C{row_idx}",
                "score_cell": f"D{row_idx}",
            })
            continue

        # Detekce konce sekce kritérií — formule v C (typicky =SUM nebo =C18+…)
        if isinstance(c, str) and c.startswith("=") and criteria:
            # Stačí to k tomu, abychom přestali přidávat — všechny criteria
            # už jsou před tímhle řádkem.
            pass  # noqa — nemusíme breakovat, dále hledáme field_cells

        # Speciální pole — A obsahuje label, hledáme příslušnou cell
        if isinstance(a, str) and a.strip():
            norm = _ascii_fold_lower(a)
            for pattern, key in _FIELD_PATTERNS:
                if pattern.search(norm):
                    if key in field_cells:
                        # Už máme jednou nalezeno — zachovej první match
                        continue
                    # Default: hodnota je v C na stejném řádku (assignment_fulfilled,
                    # plagiarism_verdict)
                    target_cell = f"C{row_idx}"
                    # Výjimky: justification + overall_comment + place_date jsou
                    # typicky pod labelem (víceřádkový text) → zapisujeme do
                    # následujícího řádku A.
                    if key in {"plagiarism_justification", "overall_comment"}:
                        target_cell = f"A{row_idx + 1}"
                    elif key == "place_date":
                        target_cell = f"A{row_idx}"  # přímo na řádku s "Místo, datum:"
                    field_cells[key] = target_cell
                    break

    return {"criteria": criteria, "field_cells": field_cells}


def extract_template_metadata(template_path: Path) -> dict:
    """Vrátí kompletní metadata + schema šablony — pro auto-vyplnění
    při registraci.

    Returns:
        ``{
            "type": "BP"|"DP"|"",            # heuristika z A6 titulu
            "role": "supervisor"|"opponent"|"",
            "language": "cs"|"en"|"",
            "study_program": str,            # B10
            "specialization": str,           # B11
            "academic_year": str,            # B12
            "obor_code": str,                # heuristika: SWI/KYB/UI/...
            "suggested_name": str,           # např. "Vedoucí DP — SWI — 2025/2026"
            "criteria": [...],               # z extract_template_schema
            "field_cells": {...},
        }``

    Všechna pole jsou best-effort; cokoli, co nelze detekovat, je prázdný
    string / prázdný list / prázdný dict.
    """
    from .review_template_filler import load_template_workbook

    # Schema (criteria + field_cells)
    base = extract_template_schema(template_path)

    # Headers (typ/role/language z A6, study_program z B10 atd.)
    wb = load_template_workbook(template_path, data_only=False)
    ws = wb.active

    title = (ws["A6"].value or "")
    if not isinstance(title, str):
        title = ""
    title_norm = _ascii_fold_lower(title)

    type_role_lang = {"type": "", "role": "", "language": ""}
    for pattern, hint in _TITLE_TYPE_ROLE_LANG:
        if pattern.search(title_norm):
            type_role_lang = hint
            break

    study_program = (ws["B10"].value or "")
    specialization = (ws["B11"].value or "")
    academic_year = (ws["B12"].value or "")

    # Normalize na string
    study_program = str(study_program).strip() if study_program else ""
    specialization = str(specialization).strip() if specialization else ""
    academic_year = str(academic_year).strip() if academic_year else ""
    # B11 obvykle obsahuje "-" pokud nemá specializaci → normalizuj na prázdné
    if specialization == "-":
        specialization = ""

    obor_code = _guess_obor_code(specialization, study_program)

    # Načti list „Konfigurace" — nabídka platných hodnot pro combo boxy,
    # když auto-detekce nechá pole prázdné.
    available = _read_konfigurace(wb)

    # Sestav suggested_name typu „Vedoucí DP — SWI — 2025/2026"
    role_cs = {"supervisor": "Vedoucí", "opponent": "Oponent"}.get(
        type_role_lang["role"], ""
    )
    role_en = {"supervisor": "Supervisor", "opponent": "Opponent"}.get(
        type_role_lang["role"], ""
    )
    parts: list[str] = []
    if type_role_lang["language"] == "en":
        if role_en:
            parts.append(role_en)
        if type_role_lang["type"]:
            parts.append(type_role_lang["type"])
        if obor_code:
            parts.append("— " + obor_code)
        if academic_year:
            parts.append("— " + academic_year)
    else:
        if role_cs:
            parts.append(role_cs)
        if type_role_lang["type"]:
            parts.append(type_role_lang["type"])
        if obor_code:
            parts.append("— " + obor_code)
        if academic_year:
            parts.append("— " + academic_year)
    suggested_name = " ".join(parts).strip() or Path(template_path).stem

    return {
        "type": type_role_lang["type"],
        "role": type_role_lang["role"],
        "language": type_role_lang["language"],
        "study_program": study_program,
        "specialization": specialization,
        "academic_year": academic_year,
        "obor_code": obor_code,
        "suggested_name": suggested_name,
        "criteria": base["criteria"],
        "field_cells": base["field_cells"],
        # Platné volby z listu „Konfigurace" (pro combo boxy v dialogu,
        # když auto-detekce nechá pole prázdné):
        "available_programs": available["programs"],
        "available_specializations": available["specializations"],
        "available_years": available["years"],
    }


def _read_konfigurace(wb) -> dict:
    """Načte list ``Konfigurace`` (pokud existuje) — nabídka platných hodnot.

    Layout:
      A=studijní programy (CZ), B=programy (EN),
      C=specializace (CZ), D=specializace (EN),
      E=akademické roky

    Hodnoty „-" / prázdné / hlavičkový řádek se odfiltrují.

    Returns ``{"programs": [...], "specializations": [...], "years": [...]}``.
    """
    out: dict[str, list[str]] = {"programs": [], "specializations": [], "years": []}
    if "Konfigurace" not in wb.sheetnames:
        return out
    ws = wb["Konfigurace"]

    def _clean(col_idx: int) -> list[str]:
        vals: list[str] = []
        for r, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if r == 1:  # hlavička
                continue
            if col_idx >= len(row):
                continue
            v = row[col_idx]
            if v is None:
                continue
            s = str(v).strip()
            if not s or s == "-":
                continue
            if s not in vals:
                vals.append(s)
        return vals

    out["programs"] = _clean(0)        # col A (CZ programy)
    out["specializations"] = _clean(2) # col C (CZ specializace)
    out["years"] = _clean(4)           # col E (roky)
    return out
