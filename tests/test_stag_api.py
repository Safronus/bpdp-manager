"""Testy parseru výsledků STAG (offline, syntetická data — žádná síť).

Pokrývá čistě parsovací funkce :mod:`bpdpmanager.services.stag_api`.
Síťové metody (``search``/``download_csv``) se zde netestují.
"""

from __future__ import annotations

import base64

from bpdpmanager.services import stag_api


def _make_interaction_token(prace_idno: str) -> str:
    """Sestaví ``pc_interactionstate`` token jako STAG — base64 s ``*`` místo ``=``.

    Byty napodobují serializaci JBoss (klíč ``praceIdno`` + hodnota).
    """
    raw = b"\xac\xed\x00\x05w\x10praceIdno\x00\x00\x05" + prace_idno.encode()
    encoded = base64.b64encode(raw).decode().replace("=", "*")
    return "JBPNS_" + encoded


def _row(prace_idno: str, surname: str, name: str, title: str, type_label: str,
         supervisor: str, reviewer: str, date: str) -> str:
    token = _make_interaction_token(prace_idno)
    href = (
        f"/portal/studium/prohlizeni.html?pc_interactionstate={token}"
        "&amp;pc_phase=action"
    )
    return (
        "<tr>"
        "<td></td>"
        f'<td><a href="{href}">{surname}</a></td>'
        f"<td>{name}</td>"
        f'<td><a href="{href}">{title}</a></td>'
        "<td></td><td></td>"
        f"<td>{supervisor}</td>"
        f"<td>{reviewer}</td>"
        f"<td>{type_label}</td>"
        f"<td>{date}</td>"
        "</tr>"
    )


def _page(*rows: str) -> str:
    header = (
        "<tr><th></th><th>Příjmení</th><th>Jméno</th><th>Název</th>"
        "<th>Stav</th><th></th><th>Vedoucí</th><th>Oponent</th>"
        "<th>Typ</th><th>Datum</th></tr>"
    )
    body = "".join(rows)
    return (
        "<html><body>"
        '<table id="prace_prijmeni_search_result_big">'
        f"{header}{body}</table>"
        "</body></html>"
    )


def test_extract_praceidno_from_token() -> None:
    token = _make_interaction_token("70373")
    href = f"/portal/studium/prohlizeni.html?pc_interactionstate={token}"
    assert stag_api._extract_praceidno(href) == "70373"


def test_extract_praceidno_missing() -> None:
    assert stag_api._extract_praceidno("/portal/studium/prohlizeni.html?x=1") is None


def test_parse_single_result() -> None:
    page = _page(
        _row(
            "72503", "Pohanka", "Josef",
            "Návrh a testování politiky hesel",
            "bakalářská", "Jašek Roman", "Žáček Petr", "",
        )
    )
    results = stag_api._parse_results(page)
    assert len(results) == 1
    r = results[0]
    assert r.adipidno == "72503"
    assert r.surname == "Pohanka"
    assert r.name == "Josef"
    assert r.title == "Návrh a testování politiky hesel"
    assert r.type_label == "bakalářská"
    assert "Pohanka Josef" in r.display_label


def test_parse_multiple_results_dedup_and_fields() -> None:
    page = _page(
        _row(
            "70373", "Novák", "Adam", "Open source plánovač směn",
            "bakalářská", "Vala Radek", "Janků Peter", "17.06.2025",
        ),
        _row(
            "40949", "Novák", "Adam", "Optimalizace tepelného zpracování",
            "diplomová", "Kdosi", "Kdosi", "12.05.2015",
        ),
        # duplikát stejné práce (jiný odkaz, stejné praceIdno) — nesmí se zdvojit
        _row(
            "70373", "Novák", "Adam", "Open source plánovač směn",
            "bakalářská", "Vala Radek", "Janků Peter", "17.06.2025",
        ),
    )
    results = stag_api._parse_results(page)
    assert [r.adipidno for r in results] == ["70373", "40949"]
    assert results[0].year == "2025"
    assert results[1].type_label == "diplomová"
    assert results[1].year == "2015"


def test_parse_no_table_fallback_adipidno() -> None:
    page = (
        "<html><body>"
        '<a href="/StagPortletsJSR168/ProhlizeniPrint?outputFormat=CSV'
        '&adipIdno=99999&lang=cs">CSV</a>'
        "</body></html>"
    )
    results = stag_api._parse_results(page)
    assert len(results) == 1
    assert results[0].adipidno == "99999"


def test_parse_empty_page() -> None:
    assert stag_api._parse_results("<html><body>nic</body></html>") == []


def test_display_label_minimal() -> None:
    r = stag_api.StagThesisResult(adipidno="1")
    assert r.student_full == "(neznámý student)"
    assert "(neznámý student)" in r.display_label


def test_csv_export_url_shape() -> None:
    url = stag_api.CSV_EXPORT_URL.format(adipidno="72503")
    assert "outputFormat=CSV" in url
    assert "adipIdno=72503" in url
    assert url.startswith("https://stag.utb.cz/")


def test_search_supervisor_only(monkeypatch) -> None:
    """Hledání jen dle vedoucího (prázdný student) projde a vyplní pole vedoucího."""
    import pytest

    client = stag_api.StagClient()
    monkeypatch.setattr(client, "_open_search_form", lambda: "/action")
    captured: dict = {}

    def fake_request(url, data=None, **kw):
        captured["data"] = data
        return "<html><body>žádné výsledky</body></html>"

    monkeypatch.setattr(client, "_request", fake_request)
    res = client.search("", "Žáček", stag_api.ROLE_SUPERVISOR)
    assert res == []
    body = captured["data"].decode()
    assert "praceSearchVedouci=%" in body          # vedoucí vyplněn
    assert "studentSearchPrijmeni=&" in body        # student prázdný

    with pytest.raises(stag_api.StagError):
        client.search("", "")                       # obojí prázdné → chyba
