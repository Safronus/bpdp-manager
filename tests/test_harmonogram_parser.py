from __future__ import annotations

from datetime import date

from bpdpmanager.models import KeyDateCategory
from bpdpmanager.services.harmonogram_parser import parse_harmonogram_text

SAMPLE_TEXT = """
Vnitřní normy Univerzity Tomáše Bati ve Zlíně
RD/06/26 Časový plán výuky a akcí spojených s výukou na FAI

Článek 2
Časový plán výuky pro AR 2026/2027

31. 8. 2026 Mezní termín zápočtů a zkoušek v AR 2025/2026.

1. 9. 2026 - 4. 2. 2027 Zimní semestr
28. 8. 2026 - 6. 9. 2026 Kroužkový a doplňující předběžný zápis (dále jen „předzápis")
rozvrhové akce pro zimní semestr (dále jen „ZS") AR 2026/2027.
Září 2026 Imatrikulace studentů 1. ročníku bakalářského studia.
11. 9. 2026 - 19. 12. 2026 Výuka (rozvrhované a nerozvrhované aktivity - 14 týdnů).

Uzavření všech studijních povinností

29. 5. 2027 Mezní termín ukončení zápočtů a zkoušek 3. ročníku bakalářského studia.
květen-červen 2027 Odevzdání bakalářské / diplomové práce.
červen 2027 SZZ – bakalářské studijní programy.
12. 7. 2027 Promoce absolventů bakalářských studijních programů.

Závěrečné ustanovení
Tento dokument byl projednán...

Verze dokumentu
30. 3. 2026 01 Děkan Vytvoření dokumentu
"""


def test_parses_concrete_dates() -> None:
    items = parse_harmonogram_text(SAMPLE_TEXT)
    descriptions = [kd.description for kd in items]
    assert any("Mezní termín zápočtů a zkoušek v AR 2025/2026" in d for d in descriptions)
    assert any("Zimní semestr" in d for d in descriptions)


def test_parses_date_ranges() -> None:
    items = parse_harmonogram_text(SAMPLE_TEXT)
    ranges = [kd for kd in items if kd.date_end is not None]
    assert any(kd.date_start == date(2026, 9, 1) and kd.date_end == date(2027, 2, 4) for kd in ranges)


def test_parses_fuzzy_dates() -> None:
    items = parse_harmonogram_text(SAMPLE_TEXT)
    fuzzy = [kd for kd in items if kd.fuzzy_label]
    assert any(kd.fuzzy_label == "květen-červen 2027" for kd in fuzzy)
    assert any(kd.fuzzy_label and kd.fuzzy_label.startswith("Září") for kd in fuzzy)


def test_categorizes_thesis_dates_as_important() -> None:
    items = parse_harmonogram_text(SAMPLE_TEXT)
    thesis_items = [kd for kd in items if kd.category == KeyDateCategory.THESIS]
    assert len(thesis_items) >= 3  # odevzdání, SZZ, promoce
    assert all(kd.important for kd in thesis_items)


def test_excludes_version_table_noise() -> None:
    items = parse_harmonogram_text(SAMPLE_TEXT)
    descriptions = [kd.description for kd in items]
    # "01 Děkan Vytvoření dokumentu" je z tabulky verzí — nesmí prosáknout
    assert not any("Děkan Vytvoření" in d for d in descriptions)


def test_excludes_section_header_bleed() -> None:
    items = parse_harmonogram_text(SAMPLE_TEXT)
    # "Promoce" nesmí mít přilepený text z následující sekce
    promoce = [kd for kd in items if "Promoce absolventů" in kd.description]
    assert promoce
    assert "Přijímací řízení" not in promoce[0].description


def test_source_marked_as_imported() -> None:
    items = parse_harmonogram_text(SAMPLE_TEXT)
    assert items
    assert all(kd.source == "imported" for kd in items)
