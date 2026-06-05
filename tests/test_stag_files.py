"""Testy parsování seznamu souborů práce ze STAG (síťová vrstva bez sítě).

Fixtury jsou odvozené z reálného HARu, ale sanitizované (žádná reálná jména).
"""

from __future__ import annotations

import base64

from bpdpmanager.services.stag_api import (
    StagFile,
    _b64_std,
    _find_ajax_loads,
    _parse_file_fragment,
    _refine_sections,
    _section_from_body,
)


def test_b64_std_roundtrip() -> None:
    assert _b64_std(base64.b64encode(b"/portal/x?a=1").decode()) == "/portal/x?a=1"
    assert _b64_std("***not base64***") == ""  # nevalidní → prázdné


def test_find_ajax_loads() -> None:
    url_b64 = base64.b64encode(b"/portal/studium/prohlizeni.html?pc_phase=resource").decode()
    body_b64 = base64.b64encode(b"pp_page=ssProhlizeniElPodobaVSKPPage&sou_adipidno=66896").decode()
    html = f"<script>GenericAjaxLoad2('{url_b64}', '{body_b64}', 'XYZ');</script>"
    pairs = _find_ajax_loads(html)
    assert pairs == [(url_b64, body_b64)]
    assert _b64_std(pairs[0][0]).endswith("pc_phase=resource")
    assert "ElPodoba" in _b64_std(pairs[0][1])


def test_section_from_body() -> None:
    assert _section_from_body("x&sou_aplikace=PROHLIZENI_VSKP_POSUDKY_VEDOUCIHO_K_VSKP") == "supervisor_review"
    assert _section_from_body("sou_aplikace=PROHLIZENI_VSKP_POSUDKY_OPONENTA_K_VSKP") == "opponent_review"
    assert _section_from_body("pp_page=ssProhlizeniElPodobaVSKPPage") == "elpodoba"
    assert _section_from_body("sou_aplikace=PROHLIZENI_VSKP_PRILOHY") == "appendix"
    assert _section_from_body("pp_page=neco") == "other"


def test_parse_file_fragment() -> None:
    frag = (
        '<table><tr><td>1. soubor: </td><td>'
        '<a class="xg_stag_a_in" href="/StagPortletsJSR168/PagesDispatcherServlet'
        '?pp_page=souboryStudentuDownloadPage&pp_nameSpace=G17612&soubidno=205074">'
        " Prilohy.zip </a> (11 KB)</td></tr></table>"
        '<table><tr><td>2. soubor: </td><td>'
        '<a href="/StagPortletsJSR168/PagesDispatcherServlet?soubidno=205075">'
        "Vzor_text.pdf</a> (1 MB)</td></tr></table>"
    )
    files = _parse_file_fragment(frag)
    assert len(files) == 2
    assert files[0] == ("205074", "Prilohy.zip",
                        "/StagPortletsJSR168/PagesDispatcherServlet"
                        "?pp_page=souboryStudentuDownloadPage&pp_nameSpace=G17612&soubidno=205074",
                        11 * 1024)
    assert files[1][0] == "205075" and files[1][1] == "Vzor_text.pdf"
    assert files[1][3] == 1024 * 1024  # „(1 MB)"


def test_parse_file_fragment_size_variants() -> None:
    from bpdpmanager.services.stag_api import _size_to_bytes
    assert _size_to_bytes("217", "KB") == 217 * 1024
    assert _size_to_bytes("1,2", "MB") == int(1.2 * 1024 * 1024)
    assert _size_to_bytes("800", "B") == 800
    assert _size_to_bytes("3", "GB") == 3 * 1024**3
    assert _size_to_bytes("", "KB") == 0       # nečitelné → 0
    # Soubor bez uvedené velikosti → velikost 0.
    no_size = _parse_file_fragment('<a href="?soubidno=9">x.pdf</a>')
    assert no_size == [("9", "x.pdf", "?soubidno=9", 0)]


def test_refine_sections_text_then_appendix() -> None:
    files = [
        StagFile("1", "text.pdf", "/d?soubidno=1", "elpodoba"),
        StagFile("2", "prilohy.zip", "/d?soubidno=2", "elpodoba"),
        StagFile("3", "posudek_v.pdf", "/d?soubidno=3", "supervisor_review"),
    ]
    _refine_sections(files)
    assert files[0].section == "text"       # 1. el. podoba = plný text
    assert files[1].section == "appendix"   # další = příloha
    assert files[2].section == "supervisor_review"  # posudek beze změny


def test_empty_fragment_no_files() -> None:
    assert _parse_file_fragment(
        '<div class="xg_msgFromServerDefault">Žádné soubory nenalezeny</div>'
    ) == []
