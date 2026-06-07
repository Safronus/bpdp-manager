"""Výchozí (default) data dodávaná v repu — obory a šablony posudků.

Obory (vč. STAG zkratek) jsou v :data:`bpdpmanager.config.DEFAULT_OBORY`.
Šablony posudků jsou prázdné XLSX formuláře v
``resources/default_templates/`` pojmenované konvencí::

    {AppKód} - {BP|DP} - {Vedoucí|Oponent}.xlsx
    např. „NSWI - DP - Vedoucí.xlsx", „SWI-EN - BP - Oponent.xlsx"

Z názvu jde deterministicky odvodit typ práce, roli, jazyk i obor —
viz :func:`parse_default_template_filename`. Šablony jsou **form-neutrální**
(prezenční i kombinovaná forma sdílí jednu šablonu, liší je jen obor — STAG
značky ``-P``/``-K`` se na úrovni šablon ignorují).

Defaulty se seedují do nového prázdného profilu a jsou kdykoli dostupné
přes tlačítko „Defaultní" v manažeru oborů / šablon.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..config import DEFAULT_OBORY
from ..models import Obor
from ..models.enums import ThesisType


def default_obory() -> list[Obor]:
    """Kanonický seznam výchozích oborů (jako ``Obor`` objekty)."""
    return [Obor(**entry) for entry in DEFAULT_OBORY]


def default_templates_dir() -> Path:
    """Cesta ke složce s dodávanými XLSX šablonami v balíčku."""
    # services/default_data.py → services → bpdpmanager → resources/default_templates
    return Path(__file__).resolve().parent.parent / "resources" / "default_templates"


@dataclass(frozen=True)
class DefaultTemplateSpec:
    """Metadata jedné výchozí šablony odvozená z názvu souboru."""

    source_path: Path
    app_code: str          # „NSWI-P", „SWI-P-EN", …
    type: ThesisType       # BP / DP
    role: str              # „supervisor" / „opponent"
    language: str          # „cs" / „en"
    obor: str              # disciplína pro filtr šablon: SWI / KYB / UI / ITA
    name: str              # lidský název šablony (a klíč pro deduplikaci)


def form_neutral_name(name: str) -> str:
    """Odstraní z názvu šablony značku formy (``-P``/``-K``) a redundantní
    ``-EN`` v kódu (jazyk drží přípona „ (EN)").

    Šablony posudků jsou form-neutrální (prezenční i kombinovaná forma sdílí
    jednu šablonu), takže název nemá formu zobrazovat. Idempotentní:

    >>> form_neutral_name("Vedoucí DP — NKYB-P-EN (EN)")
    'Vedoucí DP — NKYB (EN)'
    >>> form_neutral_name("Oponent BP — SWI-K")
    'Oponent BP — SWI'
    >>> form_neutral_name("Vedoucí DP — NSWI")
    'Vedoucí DP — NSWI'
    """
    out = re.sub(r"-[PK]\b", "", name)          # odeber -P / -K segmenty
    out = re.sub(r"-EN\b(\s*\(EN\))", r"\1", out)  # „…-EN (EN)" → „… (EN)"
    return out


def discipline_from_app_code(app_code: str) -> str:
    """Z AppKódu odvodí disciplínu pro filtr šablon (SWI/KYB/UI/ITA).

    Odřízne jazyk (``-EN``) a formu (``-P``/``-K``) a prefix navazujícího
    studia (``N``): ``NSWI-P`` → ``SWI``, ``NUI-K`` → ``UI``, ``ITA-P`` → ``ITA``.
    """
    code = app_code.strip().upper()
    if code.endswith("-EN"):
        code = code[:-3]
    if code.endswith("-P") or code.endswith("-K"):
        code = code[:-2]
    # Prefix „N" = navazující (DP) studium před disciplínou (NSWI→SWI, NUI→UI).
    # Bakalářské disciplíny (SWI, ITA) prefix nemají, takže se nestripují.
    if code.startswith("N") and len(code) >= 3:
        code = code[1:]
    return code


def parse_default_template_filename(path: Path) -> DefaultTemplateSpec | None:
    """Naparsuje ``{AppKód} - {BP|DP} - {Vedoucí|Oponent}`` z názvu souboru.

    Vrací ``None``, pokud název neodpovídá konvenci.
    """
    parts = [p.strip() for p in path.stem.split(" - ")]
    if len(parts) != 3:
        return None
    app_code, type_token, role_token = parts

    type_token = type_token.upper()
    if type_token == "BP":
        ttype = ThesisType.BP
    elif type_token == "DP":
        ttype = ThesisType.DP
    else:
        return None

    role_norm = role_token.strip().lower()
    if role_norm.startswith("vedouc"):
        role = "supervisor"
    elif role_norm.startswith("oponent") or role_norm.startswith("opponent"):
        role = "opponent"
    else:
        return None

    language = "en" if app_code.upper().endswith("-EN") else "cs"
    role_label = "Vedoucí" if role == "supervisor" else "Oponent"
    # Zobrazovací kód bez jazykové přípony (jazyk indikuje „(EN)" zvlášť).
    display_code = app_code[:-3] if app_code.upper().endswith("-EN") else app_code
    lang_suffix = " (EN)" if language == "en" else ""
    name = f"{role_label} {ttype.value} — {display_code}{lang_suffix}"

    return DefaultTemplateSpec(
        source_path=path,
        app_code=app_code,
        type=ttype,
        role=role,
        language=language,
        obor=discipline_from_app_code(app_code),
        name=name,
    )


def list_default_template_specs() -> list[DefaultTemplateSpec]:
    """Vrátí specifikace všech dodávaných šablon (seřazené podle názvu)."""
    base = default_templates_dir()
    if not base.is_dir():
        return []
    specs: list[DefaultTemplateSpec] = []
    for path in sorted(base.glob("*.xlsx")):
        spec = parse_default_template_filename(path)
        if spec is not None:
            specs.append(spec)
    return specs
