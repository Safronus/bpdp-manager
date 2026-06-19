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
    # barva role obarví odkaz a jméno zůstane klikací (vedený zeleně apod.)
    colored = _szz_student_anchor("A1", "Jan", "Jan", "#43a047")
    assert "color:#43a047" in colored and 'href="szz:A1' in colored
    # bez osobního čísla + barva role → aspoň obarvený span (čitelné na tmavém)
    assert _szz_student_anchor("", "Eva", "Eva", "#ab47bc") == (
        '<span style="color:#ab47bc;">Eva</span>')


def test_student_szz_html_states() -> None:
    from bpdpmanager.ui.szz_student_dialog import student_szz_html

    assert "zatím nejsou" in student_szz_html(None, "A1", "Jan")
    assert "nedostupný" in student_szz_html(
        SzzRecord(os_cislo="A2", unavailable=True), "A2", "X")
    rec = SzzRecord(
        os_cislo="A1",
        overall=SzzOverall(vysledek_zkousek="B", vysledek_predmety="A",
                           komise="fialová", prospel=True),
        subjects=[SubjectExam(predmet="AZINF", znamka="A", zkousejici="Novák",
                              prubeh="Otázka 1: definice grafu")],
    )
    h = student_szz_html(rec, "A1", "Jan")
    assert "AZINF" in h and "Prospěl" in h and "Novák" in h
    assert "z předmětů" in h   # dimenze celkový výsledek z předmětů
    # Otázky/průběh se zobrazují JEN tady (v souhrnu studenta), ne v agregaci.
    assert "Otázka 1: definice grafu" in h


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


def test_szz_examiner_sort_toggle_and_order() -> None:
    from bpdpmanager.ui.komise_tab import (
        _stats_szz_html,
        _szz_examiner_sort_toggle,
    )

    # přepínač má 4 volby: aktivní tučně, ostatní jako klikací odkazy szzsort:
    t_count = _szz_examiner_sort_toggle("count")
    assert "<b" in t_count
    for mode in ("avg", "median", "per_day"):
        assert f'href="szzsort:{mode}"' in t_count
    assert 'href="szzsort:count"' in _szz_examiner_sort_toggle("avg")

    def _ex(name, n, avg, median, per_day):
        return {"jmeno": name, "ucitidno": name, "n": n,
                "dist": dict.fromkeys("ABCDEF", 0), "avg": avg,
                "median": median, "per_day": per_day,
                "colors": {}, "own": 0, "foreign": 0,
                "pass": 0, "fail": 0, "none": 0}

    szz = {
        "totals": {"students": 3, "prospel": 3, "neprospel": 0,
                   "bez_znamky": 0, "nedostupne": 0, "avg": 2.0},
        "by_komise": [], "by_predmet": [], "dist": {}, "fails": {},
        "questions": {},
        "by_examiner": [_ex("Mírný", 37, 1.6, 1.0, 5.0),
                        _ex("Přísný", 20, 3.0, 3.0, 2.0),
                        _ex("Střední", 25, 2.0, 2.0, 8.0)],
    }

    def _order(mode):
        seg = _stats_szz_html(szz, "x", 3, mode).split("Per zkoušející")[1]
        seg = seg.split("Per předmět")[0]
        return sorted(["Mírný", "Přísný", "Střední"], key=seg.find)

    # default drží pořadí ze service; ostatní řadí danou metrikou sestupně.
    assert _order("count") == ["Mírný", "Přísný", "Střední"]
    assert _order("avg") == ["Přísný", "Střední", "Mírný"]       # 3,0/2,0/1,6
    assert _order("median") == ["Přísný", "Střední", "Mírný"]    # 3,0/2,0/1,0
    assert _order("per_day") == ["Střední", "Mírný", "Přísný"]   # 8,0/5,0/2,0


def test_fit_tables_hscroll_and_chart_minwidth() -> None:
    from PySide6.QtWidgets import QApplication, QTextBrowser, QTextEdit

    QApplication.instance() or QApplication([])
    from bpdpmanager.ui.komise_tab import _DefenseBarChart, _fit_tables_hscroll

    # tabulka → FixedPixelWidth na šířku TABULKY (ne na dlouhý text/legendu)
    tb = QTextBrowser()
    tb.setHtml("<p>" + ("velmi dlouhy text " * 60) + "</p>"
               "<table border='1'><tr><td>A</td><td>B</td></tr></table>")
    _fit_tables_hscroll(tb)
    assert tb.lineWrapMode() == QTextEdit.LineWrapMode.FixedPixelWidth
    assert 0 < tb.lineWrapColumnOrWidth() < 400   # úzká tabulka, ne odstavec
    # bez tabulky → běžné zalamování dle šířky widgetu
    tb2 = QTextBrowser()
    tb2.setHtml("<p>jen text</p>")
    _fit_tables_hscroll(tb2)
    assert tb2.lineWrapMode() == QTextEdit.LineWrapMode.WidgetWidth

    # graf: minWidth roste s počtem skupin (úzké okno → vodorovný posuvník)
    ch = _DefenseBarChart()
    ch.set_data([])
    assert ch.minimumWidth() == 0
    ch.set_data([{"color": "fialová", "defended": 1, "undefended": 0,
                  "none": 0, "by_day": []}] * 5)
    assert ch.minimumWidth() > 5 * 60


def test_is_defense_done() -> None:
    from bpdpmanager.services.komise_stats import student_name_key
    from bpdpmanager.ui.komise_tab import _is_defense_done

    states = {"A100": "defended", "A200": "failed",
              student_name_key("Eva Malá"): "none"}
    assert _is_defense_done(states, "A100", "Jan")        # Obhájeno → hotovo
    assert _is_defense_done(states, "A200", "Petr")       # Neobhájeno → hotovo
    assert not _is_defense_done(states, "A300", "Karel")  # neznámý stav
    assert not _is_defense_done(states, "", "Eva Malá")   # „bez obhajoby"
    assert not _is_defense_done(None, "A100", "Jan")      # bez states


def test_studia_chart_html() -> None:
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])
    from bpdpmanager.ui.komise_tab import _studia_chart_html

    # s daty → PNG <img> v zadané šířce
    html = _studia_chart_html(
        {"vyznamenani": 5, "prospel": 10, "neprospel": 2, "nevyplneno": 3}, 600)
    assert "<img" in html and "base64" in html and "width='600'" in html
    assert "Celkový výsledek studia" in html
    # bez dat (samé nuly) → prázdné
    assert _studia_chart_html(
        {"vyznamenani": 0, "prospel": 0, "neprospel": 0, "nevyplneno": 0}, 600) == ""
    # nulová/malá šířka → prázdné
    assert _studia_chart_html({"prospel": 5}, 0) == ""


def test_szz_komise_cells_home_foreign() -> None:
    from bpdpmanager.ui.komise_tab import _szz_homeforeign_cell, _szz_komise_cell

    r = {"own": 2, "foreign": 1, "own_colors": {"fialová"},
         "colors": {"fialová": 2, "modrá": 1}, "jmeno": "Petr Žáček"}
    # doma/cizí souhrn
    hf = _szz_homeforeign_cell(r)
    assert "<b>2</b>" in hf and "/1" in hf
    # Komise = jen barevné tečky ● (žádný domeček ⌂); obě barvy přítomné
    cell = _szz_komise_cell(r)
    assert "⌂" not in cell and "●" in cell
    assert "#8e24aa" in cell and "#1e88e5" in cell      # fialová i modrá
    # prázdné → pomlčka
    assert _szz_komise_cell({"colors": {}}) == _szz_homeforeign_cell(
        {"own": 0, "foreign": 0})

    # jméno = pořadí + puntík(y) vlastní komise + jméno
    from bpdpmanager.ui.komise_tab import _szz_dist_cells, _szz_examiner_name
    nm = _szz_examiner_name(3, r)
    assert "3." in nm and "Petr Žáček" in nm
    assert "#8e24aa" in nm                              # puntík v barvě fialové
    # 6 buněk rozložení A-F, nenulové barevně, nuly ztlumeně
    cells = _szz_dist_cells({"A": 5, "B": 0, "C": 0, "D": 0, "E": 0, "F": 2})
    assert cells.count("<td") == 6
    assert ">5</td>" in cells and ">2</td>" in cells


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
