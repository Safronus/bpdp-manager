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


def test_szz_fails_html_and_labels() -> None:
    from bpdpmanager.ui.komise_tab import _fail_labels, _szz_fails_html

    # prázdné → nic
    assert _szz_fails_html({}) == ""
    assert _szz_fails_html({"subjects": [], "predmety": [],
                            "defense": [], "overall": []}) == ""

    fails = {
        "subjects": [{"os": "A1", "jmeno": "Jan Novotný",
                      "predmet": "AZINF", "zkousejici": "Novák"}],
        "predmety": [{"os": "A1", "jmeno": "Jan Novotný"}],
        "defense": [{"os": "A2", "jmeno": ""}],
        "overall": [{"os": "A1", "jmeno": "Jan Novotný"}],
    }
    h = _szz_fails_html(fails)
    assert "Neúspěšní studenti" in h
    assert "Jan Novotný" in h and "AZINF" in h and "Novák" in h
    assert "Neprospěl" in h               # nadpis sekce „Celkově Neprospěl"
    assert "Neobhájili" in h              # lepší titulek pro obhajobu
    assert "Zkoušející" in h              # hlavička tabulky předmětů
    assert "<table" in h                  # render je tabulkový (zarovnání)
    assert 'href="szz:A1' in h            # jméno je klikací odkaz na souhrn SZZ
    assert 'href="szz:A2' in h and "A2" in h   # bez jména → klikací os. číslo

    # _fail_labels dedup dle os. čísla, fallback na os. číslo bez jména
    labels = _fail_labels([{"os": "A1", "jmeno": "Jan"},
                           {"os": "A1", "jmeno": "Jan"},
                           {"os": "A3", "jmeno": ""}])
    assert labels == ["Jan", "A3"]


def test_szz_student_dialog_changed_flag() -> None:
    # Pouhé nahlédnutí → changed False (volající nepřerenderuje, scroll zůstane).
    # Aktualizace ze STAG (upsert) → changed True.
    from PySide6.QtWidgets import QApplication

    from bpdpmanager.models.szz_result import SzzRecord
    from bpdpmanager.ui.szz_student_dialog import SzzStudentDialog

    QApplication.instance() or QApplication([])

    class _Svc:
        def __init__(self) -> None:
            self.store: dict = {}

        def load_szz_results(self) -> dict:
            return dict(self.store)

        def upsert_szz_result(self, rec) -> None:
            self.store[rec.os_cislo] = rec

    svc = _Svc()
    dlg = SzzStudentDialog("A1", "Jan", svc, on_update=lambda oc, cb: None)
    assert dlg.changed is False
    dlg._updated(SzzRecord(os_cislo="A1"), "")   # úspěšná aktualizace
    assert dlg.changed is True and "A1" in svc.store
    dlg.deleteLater()


def test_szz_avg_heat_gradient() -> None:
    from bpdpmanager.ui.komise_tab import _heat_color, _szz_avg_heat

    # okraje a střed heatmapy
    assert _heat_color(0.0) == "#43a047"     # zelená (nejhodnější)
    assert _heat_color(1.0) == "#e53935"     # červená (nejpřísnější)
    assert _heat_color(0.5) == "#f9a825"     # amber uprostřed
    assert _heat_color(-1) == "#43a047" and _heat_color(2) == "#e53935"  # ořez

    # nejnižší Ø zeleně, nejvyšší červeně, formát s čárkou
    assert "#43a047" in _szz_avg_heat(1.6, 1.6, 3.0)
    assert "#e53935" in _szz_avg_heat(3.0, 1.6, 3.0)
    assert "2,0" in _szz_avg_heat(2.0, 1.6, 3.0)
    # bez známky → neutrální „-" (žádný gradient)
    assert ">-<" in _szz_avg_heat(None, 1.6, 3.0)
