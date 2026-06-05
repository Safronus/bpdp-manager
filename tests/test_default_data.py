"""Testy výchozích dat — obory (vč. STAG) a šablony posudků + seedování."""

from __future__ import annotations

from pathlib import Path

import pytest

from bpdpmanager.models.enums import ThesisType
from bpdpmanager.models.student import StudyForm, derive_form_from_obor
from bpdpmanager.services import ThesisService
from bpdpmanager.services.default_data import (
    default_obory,
    discipline_from_app_code,
    list_default_template_specs,
    parse_default_template_filename,
)
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


# ── obory ────────────────────────────────────────────────────────────────────


def test_default_obory_have_stag_codes() -> None:
    obory = default_obory()
    assert len(obory) == 16
    by_name = {o.name: o.stag_code for o in obory}
    assert by_name["NSWI-P"] == "pnIT-SWI"
    assert by_name["NKYB-K"] == "knIT-KYB"
    assert by_name["SWI-P"] == "pbSWI"
    assert by_name["SWI-P-EN"] == "pbSWI-E"
    # NUI-K oprava: nesmí kolidovat s NUI-P (pnUI)
    assert by_name["NUI-P"] == "pnUI"
    assert by_name["NUI-K"] == "knUI"
    # všechny STAG kódy jsou unikátní → import je jednoznačný
    stags = [o.stag_code for o in obory]
    assert len(set(stags)) == len(stags)


def test_fresh_db_seeds_default_obory_with_stag(service: ThesisService) -> None:
    assert len(service.list_obory()) == 16
    assert service.get_obor("NUI-K").stag_code == "knUI"
    # lookup podle STAG funguje (pro import)
    assert service.get_obor_by_stag_code("knIT-KYB").name == "NKYB-K"


# ── disciplína / parsování názvu šablony ─────────────────────────────────────


@pytest.mark.parametrize(
    "app_code,expected",
    [
        ("NSWI-P", "SWI"),
        ("NSWI-K-EN", "SWI"),
        ("NKYB-P", "KYB"),
        ("NUI-K", "UI"),
        ("SWI-P", "SWI"),
        ("SWI-P-EN", "SWI"),
        ("ITA-K", "ITA"),
    ],
)
def test_discipline_from_app_code(app_code: str, expected: str) -> None:
    assert discipline_from_app_code(app_code) == expected


def test_parse_template_filename_variants() -> None:
    s = parse_default_template_filename(Path("NSWI-P - DP - Vedoucí.xlsx"))
    assert s is not None
    assert (s.type, s.role, s.language, s.obor) == (ThesisType.DP, "supervisor", "cs", "SWI")

    s = parse_default_template_filename(Path("SWI-P-EN - BP - Oponent.xlsx"))
    assert s is not None
    assert (s.type, s.role, s.language, s.obor) == (ThesisType.BP, "opponent", "en", "SWI")
    assert "(EN)" in s.name

    # case-insensitive role (zdroj měl i 'vedoucí' malým písmenem)
    s = parse_default_template_filename(Path("SWI-K - BP - vedoucí.xlsx"))
    assert s is not None and s.role == "supervisor"

    assert parse_default_template_filename(Path("nesmysl.xlsx")) is None


def test_bundled_templates_present_and_parse() -> None:
    specs = list_default_template_specs()
    assert len(specs) == 32
    # názvy jsou unikátní (slouží jako klíč pro deduplikaci)
    names = [s.name for s in specs]
    assert len(set(names)) == len(names)
    # každý zdrojový soubor existuje
    assert all(s.source_path.is_file() for s in specs)


# ── seedování oborů ──────────────────────────────────────────────────────────


def test_seed_default_obory_merge_and_overwrite(service: ThesisService) -> None:
    # smaž jeden default + změň STAG u jiného → vznikne 1 chybějící + 1 konflikt
    service.remove_obor("NUI-K")
    obor = service.get_obor("NSWI-P")
    obor.stag_code = "WRONG"
    service.upsert_obor(obor)

    missing, conflicts = service.default_obory_seed_status()
    assert missing == 1 and conflicts == 1

    # bez přepisu: doplní chybějící, konflikt nechá
    res = service.seed_default_obory(overwrite_conflicts=False)
    assert res["added"] == 1 and res["skipped"] == 1 and res["updated"] == 0
    assert service.get_obor("NUI-K").stag_code == "knUI"
    assert service.get_obor("NSWI-P").stag_code == "WRONG"

    # s přepisem: konflikt se srovná na default
    res = service.seed_default_obory(overwrite_conflicts=True)
    assert res["updated"] == 1
    assert service.get_obor("NSWI-P").stag_code == "pnIT-SWI"


# ── seedování šablon ─────────────────────────────────────────────────────────


def test_seed_default_templates(service: ThesisService) -> None:
    missing, present = service.default_templates_seed_status()
    assert missing == 32 and present == 0

    res = service.seed_default_templates()
    assert res["added"] == 32 and res["replaced"] == 0
    templates = service.list_review_templates()
    assert len(templates) == 32
    # schema se nascanovalo (kritéria nejsou prázdná)
    assert all(t.criteria for t in templates)

    # idempotence: druhý běh nic nepřidá
    res2 = service.seed_default_templates()
    assert res2["added"] == 0 and res2["skipped"] == 32

    # overwrite přegeneruje
    res3 = service.seed_default_templates(overwrite_existing=True)
    assert res3["replaced"] == 32 and res3["added"] == 0
    assert len(service.list_review_templates()) == 32


def test_seed_propagates_academic_year(service: ThesisService) -> None:
    service.seed_default_templates()
    templates = service.list_review_templates()
    # Šablony FAI UTB mají v hlavičce akademický rok → nesmí být všechny prázdné.
    assert any(t.academic_year.strip() for t in templates)


def test_reset_obory_to_defaults(service: ThesisService) -> None:
    service.add_obor("CUSTOM-X")
    assert "CUSTOM-X" in service.list_obory()
    n = service.reset_obory_to_defaults()
    assert n == 16
    names = service.list_obory()
    assert "CUSTOM-X" not in names
    assert len(names) == 16
    assert service.get_obor("NUI-K").stag_code == "knUI"


def test_reset_templates_to_defaults(service: ThesisService) -> None:
    service.seed_default_templates()
    # přidej „cizí" šablonu navíc
    from bpdpmanager.services.default_data import list_default_template_specs
    spec = list_default_template_specs()[0]
    service.register_review_template(
        name="MOJE VLASTNÍ", type=spec.type, role=spec.role,
        language=spec.language, obor="X", academic_year="", source_path=spec.source_path,
    )
    assert len(service.list_review_templates()) == 33
    res = service.reset_templates_to_defaults()
    assert res["added"] == 32
    names = {t.name for t in service.list_review_templates()}
    assert "MOJE VLASTNÍ" not in names
    assert len(names) == 32


def test_relink_review_template_by_name(service: ThesisService) -> None:
    """Posudek se stalým template_id se přepojí podle uloženého názvu."""
    from bpdpmanager.models.review import Review

    service.seed_default_templates()
    tmpl = service.list_review_templates()[0]
    review = Review(
        template_id="neexistujici-id",
        template_name=tmpl.name,
        role=tmpl.role,
        language=tmpl.language,
    )
    relinked = service._relink_review_template(review)
    assert relinked is not None
    assert relinked.id == tmpl.id
    assert review.template_id == tmpl.id  # posudek se opravil

    # Neznámý název → robustní fallback dle role/typu/oboru vybere vhodnou
    # šablonu (nikdy neselže, když nějaká pasující existuje).
    from bpdpmanager.models.enums import ThesisType
    bad = Review(template_id="x", template_name="ZCELA NEEXISTUJE",
                 role="supervisor", language="cs")
    got = service._relink_review_template(bad, expected_type=ThesisType.BP, obor_hint="SWI")
    assert got is not None
    assert got.role == "supervisor" and got.type == ThesisType.BP and got.obor == "SWI"

    # Když pro danou roli žádná šablona není → None
    none_role = Review(template_id="x", template_name="NIC", role="nonexistent-role")
    assert service._relink_review_template(none_role) is None


def test_maybe_seed_defaults_only_on_fresh(tmp_path: Path) -> None:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    svc = ThesisService(repo)  # load() vytvořil čerstvou DB → created_fresh
    assert repo.created_fresh is True
    svc.maybe_seed_defaults()
    assert len(svc.list_review_templates()) == 32
    assert repo.created_fresh is False  # flag se shodil

    # nová služba nad EXISTUJÍCÍ DB → není fresh → no-op
    repo2 = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    svc2 = ThesisService(repo2)
    assert repo2.created_fresh is False
    before = len(svc2.list_review_templates())
    svc2.maybe_seed_defaults()
    assert len(svc2.list_review_templates()) == before  # nepřibyly duplicity


# ── forma studia z -EN oboru ─────────────────────────────────────────────────


def test_derive_form_handles_en_suffix() -> None:
    assert derive_form_from_obor("NSWI-P-EN") == StudyForm.PRESENTIAL
    assert derive_form_from_obor("NKYB-K-EN") == StudyForm.COMBINED
    assert derive_form_from_obor("SWI-P") == StudyForm.PRESENTIAL
    assert derive_form_from_obor("NUI") is None
