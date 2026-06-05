"""Zápis hodnot do buněk XLSX **bez ztráty zbytku souboru**.

Proč ne openpyxl: ``openpyxl.load_workbook(...)`` + ``wb.save(...)`` umí
zahodit nebo poškodit části šablony, které nejsou v jeho datovém modelu —
typicky **obrázky v záhlaví/zápatí** (logo fakulty „nahoře"), VML, některé
typy kreseb, tisková nastavení apod. Pro posudky FAI UTB je požadavek
„výstup 1:1 jen s vyplněnými daty", takže nesmíme přepisovat celý sešit.

Tento modul proto:

1. otevře šablonu jako ZIP,
2. přepíše **pouze XML aktivního listu** (`xl/worksheets/sheetN.xml`) —
   nastaví hodnoty zadaných buněk a zachová jejich styl (`s`),
3. všechny ostatní části (``xl/media/*``, ``xl/drawings/*``, styly,
   ``[Content_Types].xml`` …) zkopíruje **beze změny**.

Tím je výstup totožný se šablonou až na vyplněné buňky.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


class XlsxWriteError(Exception):
    """Selhání zápisu hodnot do XLSX (poškozená/neočekávaná struktura)."""


# ── Pomocné: souřadnice ──────────────────────────────────────────────────────


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


# ── Pomocné: namespace round-trip ────────────────────────────────────────────


def _register_namespaces(xml_text: str) -> None:
    """Zaregistruje všechny namespace prefixy z kořene, aby je ET zachoval."""
    for prefix, uri in re.findall(r'xmlns:([A-Za-z0-9_]+)="([^"]+)"', xml_text):
        try:
            ET.register_namespace(prefix, uri)
        except ValueError:
            pass
    m = re.search(r'xmlns="([^"]+)"', xml_text)
    if m:
        ET.register_namespace("", m.group(1))


# ── Pomocné: resolve aktivního listu ─────────────────────────────────────────


def _resolve_active_sheet_part(zf: zipfile.ZipFile) -> str:
    """Vrátí cestu k XML aktivního listu (např. ``xl/worksheets/sheet1.xml``)."""
    try:
        wb_xml = zf.read("xl/workbook.xml").decode("utf-8")
        rels_xml = zf.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    except KeyError as exc:  # pragma: no cover
        raise XlsxWriteError("XLSX nemá očekávanou strukturu workbooku.") from exc

    m_active = re.search(r'activeTab="(\d+)"', wb_xml)
    active = int(m_active.group(1)) if m_active else 0

    # r:id listů v pořadí <sheets>
    rids = re.findall(r"<sheet\b[^>]*\br:id=\"([^\"]+)\"", wb_xml)
    if not rids:
        rids = re.findall(r"<sheet\b[^>]*:id=\"([^\"]+)\"", wb_xml)
    if not rids:
        raise XlsxWriteError("V workbook.xml nejsou žádné listy.")
    rid = rids[active] if 0 <= active < len(rids) else rids[0]

    m_target = re.search(
        r"<Relationship\b[^>]*\bId=\"" + re.escape(rid) + r"\"[^>]*\bTarget=\"([^\"]+)\"",
        rels_xml,
    )
    if not m_target:
        # Zkus opačné pořadí atributů (Target před Id)
        m_target = re.search(
            r"<Relationship\b[^>]*\bTarget=\"([^\"]+)\"[^>]*\bId=\"" + re.escape(rid) + r"\"",
            rels_xml,
        )
    if not m_target:
        raise XlsxWriteError(f"Nenalezen list pro r:id={rid}.")

    target = m_target.group(1).lstrip("/")
    if target.startswith("xl/"):
        return target
    return "xl/" + target


# ── Pomocné: manipulace s buňkami ────────────────────────────────────────────


def _find_or_create_row(sheet_data: ET.Element, rownum: int) -> ET.Element:
    rows = sheet_data.findall(f"{{{_MAIN_NS}}}row")
    for row in rows:
        if int(row.get("r", "0")) == rownum:
            return row
    new_row = ET.Element(f"{{{_MAIN_NS}}}row")
    new_row.set("r", str(rownum))
    # Vlož v pořadí podle r
    insert_at = len(list(sheet_data))
    for i, child in enumerate(list(sheet_data)):
        if int(child.get("r", "0")) > rownum:
            insert_at = i
            break
    sheet_data.insert(insert_at, new_row)
    return new_row


def _find_or_create_cell(row: ET.Element, coord: str, col: str) -> ET.Element:
    cells = row.findall(f"{{{_MAIN_NS}}}c")
    for c in cells:
        if c.get("r") == coord:
            return c
    new_cell = ET.Element(f"{{{_MAIN_NS}}}c")
    new_cell.set("r", coord)
    target_idx = _col_to_index(col)
    insert_at = len(list(row))
    for i, c in enumerate(list(row)):
        c_coord = c.get("r", "")
        m = re.match(r"^([A-Za-z]+)\d+$", c_coord)
        if m and _col_to_index(m.group(1)) > target_idx:
            insert_at = i
            break
    row.insert(insert_at, new_cell)
    return new_cell


def _format_number(value: float | int) -> str:
    if isinstance(value, bool):  # bool je podtyp int — ošetři zvlášť
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    f = float(value)
    if f.is_integer():
        return str(int(f))
    return repr(f)


def _set_cell_value(cell: ET.Element, value: object) -> None:
    # Odstraň existující obsah (v / f / is), styl `s` ponech.
    for tag in ("v", "f", "is"):
        for child in cell.findall(f"{{{_MAIN_NS}}}{tag}"):
            cell.remove(child)

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "t" in cell.attrib:
            del cell.attrib["t"]
        v = ET.SubElement(cell, f"{{{_MAIN_NS}}}v")
        v.text = _format_number(value)
    else:
        # Inline string — nezasahuje do sharedStrings.xml.
        cell.set("t", "inlineStr")
        is_el = ET.SubElement(cell, f"{{{_MAIN_NS}}}is")
        t_el = ET.SubElement(is_el, f"{{{_MAIN_NS}}}t")
        text = "" if value is None else str(value)
        if text != text.strip() or "\n" in text:
            t_el.set(_XML_SPACE, "preserve")
        t_el.text = text


# ── Veřejné API ──────────────────────────────────────────────────────────────


def set_cells(
    template_path: Path,
    output_path: Path,
    values: dict[str, object],
    *,
    sheet_part: str | None = None,
) -> None:
    """Zapíše ``values`` (souřadnice → hodnota) do kopie ``template_path``.

    Vše kromě XML aktivního listu se zkopíruje beze změny (logo, kresby,
    styly…). Hodnoty: ``str`` → inline string, ``int``/``float`` → číslo.
    Prázdné/None hodnoty se přeskočí.

    Args:
        sheet_part: volitelně cesta k listu uvnitř zipu
            (např. ``xl/worksheets/sheet1.xml``). Default = aktivní list.
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


def _edit_sheet_xml(sheet_xml: str, values: dict[str, object]) -> str:
    _register_namespaces(sheet_xml)
    decl_match = re.match(r"^\s*(<\?xml[^>]*\?>)", sheet_xml)
    declaration = (
        decl_match.group(1)
        if decl_match
        else '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    )
    try:
        root = ET.fromstring(sheet_xml)
    except ET.ParseError as exc:  # pragma: no cover
        raise XlsxWriteError(f"List nelze rozparsovat: {exc}") from exc

    sheet_data = root.find(f"{{{_MAIN_NS}}}sheetData")
    if sheet_data is None:
        raise XlsxWriteError("List nemá <sheetData>.")

    for coord, value in values.items():
        col, rownum = _split_coord(coord)
        row = _find_or_create_row(sheet_data, rownum)
        cell = _find_or_create_cell(row, f"{col}{rownum}", col)
        _set_cell_value(cell, value)

    body = ET.tostring(root, encoding="unicode")
    return declaration + "\n" + body
