"""Zápis hodnot do buněk XLSX **bez ztráty zbytku souboru**.

Proč ne openpyxl: ``openpyxl.load_workbook(...)`` + ``wb.save(...)`` umí
zahodit nebo poškodit části šablony, které nejsou v jeho datovém modelu —
typicky **obrázky v záhlaví/zápatí** (logo fakulty „nahoře"), VML, kresby,
ověření dat (data validation) apod. Pro posudky FAI UTB je požadavek
„výstup 1:1 jen s vyplněnými daty", takže nesmíme přepisovat celý sešit.

Proč ne ani XML re-serializace (ElementTree): ta zahazuje deklarace
namespace, které nejsou „použité" elementem, ale jsou odkazované v
``mc:Ignorable`` (např. ``x14ac``, ``xr``). Výsledek pak Excel odmítne
otevřít.

Tento modul proto edituje **jen textové úseky cílových buněk** v XML
aktivního listu (regexem najde/nahradí ``<c r="…">…</c>``) a zbytek souboru
zkopíruje **byte za byte**. Výstup je tak prakticky totožný se šablonou až
na vyplněné buňky.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape


class XlsxWriteError(Exception):
    """Selhání zápisu hodnot do XLSX (poškozená/neočekávaná struktura)."""


# ── Souřadnice ───────────────────────────────────────────────────────────────


def _split_coord(coord: str) -> tuple[str, int]:
    m = re.match(r"^([A-Za-z]+)(\d+)$", coord.strip())
    if not m:
        raise XlsxWriteError(f"Neplatná souřadnice buňky: {coord!r}")
    return m.group(1).upper(), int(m.group(2))


def _col_to_index(col: str) -> int:
    idx = 0
    for ch in col.upper():
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx


def _format_number(value: float | int) -> str:
    if isinstance(value, bool):  # bool je podtyp int — ošetři zvlášť
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    f = float(value)
    if f.is_integer():
        return str(int(f))
    return repr(f)


# ── Sestavení buňky ──────────────────────────────────────────────────────────


def _clean_attrs(attrs: str) -> str:
    """Z atributů ``<c>`` (bez ``r``) zahodí ``t`` (typ přepíšeme), zbytek
    (zejména ``s`` = styl) ponechá v původním pořadí."""
    kept: list[str] = []
    for am in re.finditer(r'([\w:]+)="([^"]*)"', attrs):
        if am.group(1) == "t":
            continue
        kept.append(f' {am.group(1)}="{am.group(2)}"')
    return "".join(kept)


def _cell_xml(coord: str, value: object, kept_attrs: str) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{coord}"{kept_attrs}><v>{_format_number(value)}</v></c>'
    text = str(value)
    space = (
        ' xml:space="preserve"'
        if (text != text.strip() or "\n" in text)
        else ""
    )
    return (
        f'<c r="{coord}"{kept_attrs} t="inlineStr">'
        f"<is><t{space}>{_xml_escape(text)}</t></is></c>"
    )


# ── Editace XML listu (čistě textově) ────────────────────────────────────────


def _set_cell_in_xml(
    xml: str, coord: str, col: str, rownum: int, value: object
) -> str:
    # Najdi existující buňku (předpoklad: ``r`` je první atribut, jako to píše
    # Excel/openpyxl/LibreOffice). Pokrývá self-closing i plnou variantu.
    pat = re.compile(
        r'<c\s+r="' + re.escape(coord) + r'"'
        r'(?P<attrs>(?:\s+[\w:]+="[^"]*")*)\s*(?:/>|>.*?</c>)',
        re.DOTALL,
    )
    m = pat.search(xml)
    if m:
        kept = _clean_attrs(m.group("attrs"))
        return xml[: m.start()] + _cell_xml(coord, value, kept) + xml[m.end():]
    return _insert_cell(xml, coord, col, rownum, value)


def _insert_cell(
    xml: str, coord: str, col: str, rownum: int, value: object
) -> str:
    new_cell = _cell_xml(coord, value, "")

    # 1) Řádek existuje (plná varianta s tělem)
    row_pat = re.compile(
        r'(<row\s+r="' + str(rownum) + r'"[^>]*>)(?P<body>.*?)(</row>)',
        re.DOTALL,
    )
    m = row_pat.search(xml)
    if m:
        new_body = _insert_cell_into_body(m.group("body"), col, new_cell)
        return (
            xml[: m.start()]
            + m.group(1) + new_body + m.group(3)
            + xml[m.end():]
        )

    # 2) Řádek existuje jako self-closing (prázdný)
    row_sc = re.compile(r'<row\s+r="' + str(rownum) + r'"(?P<attrs>[^>]*?)/>')
    m = row_sc.search(xml)
    if m:
        new_row = f'<row r="{rownum}"{m.group("attrs")}>{new_cell}</row>'
        return xml[: m.start()] + new_row + xml[m.end():]

    # 3) Řádek neexistuje → vlož do <sheetData> ve správném pořadí
    return _insert_row(xml, rownum, new_cell)


def _insert_cell_into_body(body: str, col: str, new_cell: str) -> str:
    target = _col_to_index(col)
    for cm in re.finditer(r'<c\s+r="([A-Z]+)\d+"', body):
        if _col_to_index(cm.group(1)) > target:
            return body[: cm.start()] + new_cell + body[cm.start():]
    return body + new_cell


def _insert_row(xml: str, rownum: int, new_cell: str) -> str:
    new_row = f'<row r="{rownum}">{new_cell}</row>'

    sd = re.search(r"(<sheetData[^>]*>)(?P<body>.*?)(</sheetData>)", xml, re.DOTALL)
    if sd:
        body = sd.group("body")
        insert_pos = None
        for rm in re.finditer(r'<row\s+r="(\d+)"', body):
            if int(rm.group(1)) > rownum:
                insert_pos = rm.start()
                break
        new_body = (
            body + new_row
            if insert_pos is None
            else body[:insert_pos] + new_row + body[insert_pos:]
        )
        return xml[: sd.start()] + sd.group(1) + new_body + sd.group(3) + xml[sd.end():]

    # Prázdný self-closing <sheetData/>
    sd_sc = re.search(r"<sheetData([^>]*)/>", xml)
    if sd_sc:
        replacement = f"<sheetData{sd_sc.group(1)}>{new_row}</sheetData>"
        return xml[: sd_sc.start()] + replacement + xml[sd_sc.end():]

    raise XlsxWriteError("List nemá <sheetData>.")


def _edit_sheet_xml(sheet_xml: str, values: dict[str, object]) -> str:
    for coord, value in values.items():
        col, rownum = _split_coord(coord)
        sheet_xml = _set_cell_in_xml(sheet_xml, coord, col, rownum, value)
    return sheet_xml


# ── Resolve aktivního listu ──────────────────────────────────────────────────


def _resolve_active_sheet_part(zf: zipfile.ZipFile) -> str:
    """Vrátí cestu k XML aktivního listu (např. ``xl/worksheets/sheet1.xml``)."""
    try:
        wb_xml = zf.read("xl/workbook.xml").decode("utf-8")
        rels_xml = zf.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    except KeyError as exc:  # pragma: no cover
        raise XlsxWriteError("XLSX nemá očekávanou strukturu workbooku.") from exc

    m_active = re.search(r'activeTab="(\d+)"', wb_xml)
    active = int(m_active.group(1)) if m_active else 0

    rids = re.findall(r'<sheet\b[^>]*\br:id="([^"]+)"', wb_xml)
    if not rids:
        rids = re.findall(r'<sheet\b[^>]*:id="([^"]+)"', wb_xml)
    if not rids:
        raise XlsxWriteError("V workbook.xml nejsou žádné listy.")
    rid = rids[active] if 0 <= active < len(rids) else rids[0]

    m_target = re.search(
        r'<Relationship\b[^>]*\bId="' + re.escape(rid) + r'"[^>]*\bTarget="([^"]+)"',
        rels_xml,
    )
    if not m_target:
        m_target = re.search(
            r'<Relationship\b[^>]*\bTarget="([^"]+)"[^>]*\bId="' + re.escape(rid) + r'"',
            rels_xml,
        )
    if not m_target:
        raise XlsxWriteError(f"Nenalezen list pro r:id={rid}.")

    target = m_target.group(1).lstrip("/")
    return target if target.startswith("xl/") else "xl/" + target


# ── Veřejné API ──────────────────────────────────────────────────────────────


def set_cells(
    template_path: Path,
    output_path: Path,
    values: dict[str, object],
    *,
    sheet_part: str | None = None,
) -> None:
    """Zapíše ``values`` (souřadnice → hodnota) do kopie ``template_path``.

    Vše kromě cílových buněk v XML aktivního listu se zkopíruje beze změny
    (logo, kresby, ověření dat, styly, namespace deklarace…). Hodnoty:
    ``str`` → inline string, ``int``/``float`` → číslo. Prázdné/None se
    přeskočí.
    """
    template_path = Path(template_path)
    output_path = Path(output_path)
    if not template_path.is_file():
        raise FileNotFoundError(f"Šablona neexistuje: {template_path}")

    clean = {
        coord: val
        for coord, val in (values or {}).items()
        if val is not None and (not isinstance(val, str) or val.strip())
    }

    with zipfile.ZipFile(template_path, "r") as zin:
        infos = zin.infolist()
        part = sheet_part or _resolve_active_sheet_part(zin)
        try:
            sheet_xml = zin.read(part).decode("utf-8")
        except KeyError as exc:
            raise XlsxWriteError(f"List {part} v šabloně chybí.") from exc
        contents = {info.filename: zin.read(info.filename) for info in infos}

    if clean:
        sheet_xml = _edit_sheet_xml(sheet_xml, clean)
    contents[part] = sheet_xml.encode("utf-8")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
        # Zachovej původní pořadí i metadata položek.
        for info in infos:
            zout.writestr(info, contents[info.filename])
