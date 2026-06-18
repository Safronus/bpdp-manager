"""Testy souhrnu SZZ studenta (odkaz na studenta + render dialogu z cache)."""

from __future__ import annotations

from bpdpmanager.models.szz_result import SubjectExam, SzzOverall, SzzRecord


def test_szz_student_anchor_roundtrip() -> None:
    from bpdpmanager.ui.komise_tab import _parse_szz_href, _szz_student_anchor

    a = _szz_student_anchor("A24538", "Jan Nový Žáček", "Jan Nový Žáček")
    href = a.split('href="')[1].split('"')[0]
    assert _parse_szz_href(href) == ("A24538", "Jan Nový Žáček")
    # bez osobního čísla → bez odkazu
    assert _szz_student_anchor("", "X", "X") == "X"
    assert _parse_szz_href("http://example") is None
    assert _parse_szz_href("szz:A1") == ("A1", "")


def test_student_szz_html_states() -> None:
    from bpdpmanager.ui.szz_student_dialog import student_szz_html

    assert "zatím nejsou" in student_szz_html(None, "A1", "Jan")
    assert "nedostupný" in student_szz_html(
        SzzRecord(os_cislo="A2", unavailable=True), "A2", "X")
    rec = SzzRecord(
        os_cislo="A1",
        overall=SzzOverall(vysledek_zkousek="B", vysledek_predmety="A",
                           komise="fialová", prospel=True),
        subjects=[SubjectExam(predmet="AZINF", znamka="A", zkousejici="Novák")],
    )
    h = student_szz_html(rec, "A1", "Jan")
    assert "AZINF" in h and "Prospěl" in h and "Novák" in h
    assert "z předmětů" in h   # dimenze celkový výsledek z předmětů
