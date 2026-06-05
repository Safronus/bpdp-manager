"""Kosmetické úpravy **dočasné kopie** XLSX před převodem do PDF.

Uložený XLSX (přílohu k práci) necháváme 1:1 se šablonou — tyhle úpravy se
dělají jen na dočasné kopii, kterou pak LibreOffice převede do PDF:

1. **Vyvážené okraje / širší tabulka** — tisk se omezí na sloupce s obsahem
   (aby prázdné sloupce vpravo nedělaly velkou mezeru) a obsah se měřítkem
   roztáhne na šířku stránky. Levý okraj zůstává, vpravo se mezera zmenší.
2. **Hlavička „Body (0–5)"** — buňka dostane menší a černý font (na úzký
   sloupec se vejde na jeden řádek a líp se čte).

Vše je fail-safe: jakákoli chyba úpravu jen přeskočí, PDF se vyrobí dál.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_BODY_FONT_SIZE = "9"
_SHEET_RE = re.compile(r"xl/worksheets/sheet\d+\.xml$")
_EMU_PER_PX = 9525
_EMU_PER_MM = 36000
_EMU_PER_INCH = 914400


def polish_pdf_layout(path: Path) -> None:
    """Upraví XLSX ``path`` na místě (jen pro PDF). Fail-safe."""
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            parts = {n: z.read(n) for n in names}
    except Exception:  # noqa: BLE001
        return

    changed = False
    try:
        changed |= _fit_table_width(parts, names)
    except Exception:  # noqa: BLE001
        pass
    try:
        changed |= _restyle_body_header(parts, names)
    except Exception:  # noqa: BLE001
        pass

    if not changed:
        return
    try:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for n in names:
                z.writestr(n, parts[n])
    except Exception:  # noqa: BLE001
        pass


def _col_num(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def _fit_table_width(parts: dict[str, bytes], names: list[str]) -> bool:
    """Omez tisk na sloupce s obsahem a roztáhni tabulku na šířku stránky.

    Posudek je na prvním listu (``sheet1``). Pravý okraj rozvržení bereme z
    nejširší sloučené buňky (u FAI šablon sloupec D), poslední řádek z dat.
    Tisk omezíme na ``A1:{pravý}{poslední}`` a nastavíme měřítko, aby tabulka
    vyplnila šířku stránky (levý okraj zůstává, mezera vpravo se zmenší).
    """
    # Idempotence — pokud už máme oblast tisku, je soubor upravený (neroztahuj
    # sloupce podruhé).
    wbx = parts.get("xl/workbook.xml", b"").decode("utf-8", "ignore")
    if "_xlnm.Print_Area" in wbx:
        return False

    sheet_part = "xl/worksheets/sheet1.xml"
    if sheet_part not in parts:
        ws = [n for n in names if _SHEET_RE.match(n)]
        if not ws:
            return False
        sheet_part = ws[0]
    sx = parts[sheet_part].decode("utf-8")

    merge_cols = re.findall(r'<mergeCell ref="[A-Z]+\d+:([A-Z]+)\d+"', sx)
    if not merge_cols:
        return False
    right_col = max(merge_cols, key=_col_num)
    rows = [int(m) for m in re.findall(r'<row r="(\d+)"', sx)]
    max_row = max(rows) if rows else 49

    right_col_num = _col_num(right_col)
    table_emu = _columns_width_emu(sx, right_col_num)
    paper_w = _paper_width_emu(sx)
    left_in, right_in = _margins_inches(sx)
    printable = paper_w - int((left_in + right_in) * _EMU_PER_INCH)
    if table_emu <= 0 or printable <= 0:
        return False

    _set_print_area(parts, right_col, max_row)

    # Roztáhni POUZE šířku sloupců A..D na šířku stránky (vodorovně). Nepoužíváme
    # měřítko celého tisku (`scale`) — to by zvětšilo i výšku a posunulo obsah na
    # další stránku. Odhad šířky sloupců (px) skutečnou rezervu podhodnocuje, tak
    # ho zkorigujeme (×1.06) a omezíme stropem 1.10 (ověřeno: vyplní šířku a drží
    # počet stran). Když tabulka už šířku stránky vyplňuje, neroztahuje se.
    headroom = printable / table_emu
    if headroom > 1.02:
        factor = min(1.10, headroom * 1.06)
        sx = _scale_column_widths(sx, right_col_num, factor)

    parts[sheet_part] = sx.encode("utf-8")
    return True


def _columns_width_emu(sx: str, right_col_num: int) -> int:
    default = 8.43
    fmt = re.search(r'<sheetFormatPr[^>]*defaultColWidth="([0-9.]+)"', sx)
    if fmt:
        default = float(fmt.group(1))
    widths: dict[int, float] = {}
    for cmin, cmax, w in re.findall(
        r'<col min="(\d+)" max="(\d+)"[^>]*?width="([0-9.]+)"', sx
    ):
        for c in range(int(cmin), int(cmax) + 1):
            widths[c] = float(w)
    total_px = 0
    for c in range(1, right_col_num + 1):
        total_px += round(widths.get(c, default) * 7 + 5)  # Calibri/Arial ~MDW 7
    return total_px * _EMU_PER_PX


def _scale_column_widths(sx: str, right_col_num: int, factor: float) -> str:
    """Vynásobí šířku sloupců, které patří do tabulky (min <= right_col)."""
    def repl(m: re.Match[str]) -> str:
        tag = m.group(0)
        cmin = int(re.search(r'min="(\d+)"', tag).group(1))
        if cmin > right_col_num:  # sloupce mimo tabulku nech být
            return tag
        wm = re.search(r'width="([0-9.]+)"', tag)
        if not wm:
            return tag
        new_w = round(float(wm.group(1)) * factor, 4)
        return tag.replace(wm.group(0), f'width="{new_w}"')

    return re.sub(r"<col\b[^>]*/>", repl, sx)


def _paper_width_emu(sx: str) -> int:
    w_mm = 297 if 'orientation="landscape"' in sx else 210  # A4
    return w_mm * _EMU_PER_MM


def _margins_inches(sx: str) -> tuple[float, float]:
    m = re.search(r'<pageMargins[^>]*\bleft="([0-9.]+)"[^>]*\bright="([0-9.]+)"', sx)
    return (float(m.group(1)), float(m.group(2))) if m else (0.7, 0.7)


def _set_print_area(parts: dict[str, bytes], right_col: str, max_row: int) -> None:
    """Nastaví oblast tisku ``A1:{right_col}{max_row}`` pro první list."""
    wb = parts.get("xl/workbook.xml")
    if wb is None:
        return
    wbx = wb.decode("utf-8")
    if "_xlnm.Print_Area" in wbx:
        return  # už má vlastní — nezasahuj
    m = re.search(r'<sheet [^>]*name="([^"]+)"', wbx)
    if not m:
        return
    sheet_name = m.group(1)
    ref = f"'{sheet_name}'!$A$1:${right_col}${max_row}"
    dn = f'<definedName name="_xlnm.Print_Area" localSheetId="0">{ref}</definedName>'
    if "<definedNames>" in wbx:
        wbx = wbx.replace("<definedNames>", "<definedNames>" + dn, 1)
    else:
        wbx = re.sub(r"(</sheets>)", r"\1<definedNames>" + dn + "</definedNames>", wbx, 1)
    parts["xl/workbook.xml"] = wbx.encode("utf-8")


def _restyle_body_header(parts: dict[str, bytes], names: list[str]) -> bool:
    """Buňce „Body (0–5)" dá menší a černý font (klon stylu, jen tahle buňka)."""
    ss = parts.get("xl/sharedStrings.xml")
    styles = parts.get("xl/styles.xml")
    if ss is None or styles is None:
        return False

    # 1) index sdíleného řetězce hlavičky bodů — „Body (0–5)" / „Points (0–5)"
    #    (jakákoli pomlčka). Matchuje „…(0…5)".
    target_si = None
    for i, si in enumerate(ET.fromstring(ss)):
        txt = "".join(t.text or "" for t in si.iter() if t.tag.endswith("}t"))
        norm = txt.lower().replace(" ", "")
        if "(0" in norm and "5)" in norm:
            target_si = i
            break
    if target_si is None:
        return False

    # 2) najdi buňku, která ten řetězec používá → její ref + styl
    cell_ref = cell_style = sheet_name = None
    for n in names:
        if not _SHEET_RE.match(n):
            continue
        root = ET.fromstring(parts[n])
        for c in root.iter(f"{_M}c"):
            if c.get("t") == "s":
                v = c.find(f"{_M}v")
                if v is not None and v.text == str(target_si):
                    cell_ref = c.get("r")
                    cell_style = int(c.get("s") or "0")
                    sheet_name = n
                    break
        if cell_ref:
            break
    if cell_ref is None:
        return False

    # 3) klon fontu (menší + černý) a klon xf (jen pro tuhle buňku)
    styles_xml = styles.decode("utf-8")
    new_styles, new_xf_idx = _clone_style_smaller_black(styles_xml, cell_style)
    if new_styles is None:
        return False
    parts["xl/styles.xml"] = new_styles.encode("utf-8")

    # 4) přepiš styl jen u téhle buňky
    sheet_xml = parts[sheet_name].decode("utf-8")
    sheet_xml = _set_cell_style(sheet_xml, cell_ref, new_xf_idx)
    parts[sheet_name] = sheet_xml.encode("utf-8")
    return True


def _split_elements(block: str, tag: str) -> list[str]:
    return re.findall(rf"<{tag}\b[^>]*/>|<{tag}\b.*?</{tag}>", block, re.DOTALL)


def _clone_style_smaller_black(
    styles_xml: str, xf_index: int
) -> tuple[str | None, int]:
    """Naklonuje font (menší + černý) a xf[xf_index] s tím fontem.

    Vrací ``(nové styles.xml, index nového xf)`` nebo ``(None, -1)``.
    """
    fonts_m = re.search(r"<fonts\b[^>]*>(.*?)</fonts>", styles_xml, re.DOTALL)
    xfs_m = re.search(r"<cellXfs\b[^>]*>(.*?)</cellXfs>", styles_xml, re.DOTALL)
    if not fonts_m or not xfs_m:
        return None, -1

    fonts = _split_elements(fonts_m.group(1), "font")
    xfs = _split_elements(xfs_m.group(1), "xf")
    if xf_index >= len(xfs):
        return None, -1

    xf = xfs[xf_index]
    font_id_m = re.search(r'fontId="(\d+)"', xf)
    font_id = int(font_id_m.group(1)) if font_id_m else 0
    if font_id >= len(fonts):
        return None, -1

    # nový font: zmenši sz a nastav černou barvu
    base = fonts[font_id]
    new_font = re.sub(r'<sz val="[^"]*"/>', f'<sz val="{_BODY_FONT_SIZE}"/>', base)
    if "<sz " not in new_font:  # font bez velikosti — doplň
        new_font = new_font.replace("<font>", f'<font><sz val="{_BODY_FONT_SIZE}"/>', 1)
    new_font = re.sub(r"<color[^/]*/>", "", new_font)  # zahoď stávající barvu
    new_font = re.sub(
        r'(<sz val="[^"]*"/>)', r'\1<color rgb="FF000000"/>', new_font, count=1
    )
    new_font_id = len(fonts)

    # nový xf = klon s novým fontId
    new_xf = re.sub(r'fontId="\d+"', f'fontId="{new_font_id}"', xf, count=1)
    if 'fontId="' not in new_xf:  # přidej applyFont+fontId
        new_xf = new_xf.replace("<xf", f'<xf fontId="{new_font_id}" applyFont="1"', 1)
    elif "applyFont" not in new_xf:
        new_xf = new_xf.replace("<xf", '<xf applyFont="1"', 1)
    new_xf_idx = len(xfs)

    # poskládej zpět + uprav count
    new_fonts_block = _replace_block_with_count(
        styles_xml, "fonts", "".join(fonts) + new_font, len(fonts) + 1
    )
    new_styles = _replace_block_with_count(
        new_fonts_block, "cellXfs", "".join(xfs) + new_xf, len(xfs) + 1
    )
    return new_styles, new_xf_idx


def _replace_block_with_count(
    styles_xml: str, tag: str, inner: str, count: int
) -> str:
    """Nahradí obsah ``<tag …>…</tag>`` a nastaví ``count``."""
    def repl(m: re.Match[str]) -> str:
        attrs = m.group(1)
        attrs = re.sub(r'count="\d+"', f'count="{count}"', attrs)
        if "count=" not in attrs:
            attrs += f' count="{count}"'
        return f"<{tag}{attrs}>{inner}</{tag}>"

    return re.sub(
        rf"<{tag}(\b[^>]*)>.*?</{tag}>", repl, styles_xml, count=1, flags=re.DOTALL
    )


def _set_cell_style(sheet_xml: str, cell_ref: str, xf_idx: int) -> str:
    """Nastaví ``s="xf_idx"`` u konkrétní buňky (zachová ostatní atributy)."""
    pattern = re.compile(r'<c r="' + re.escape(cell_ref) + r'"([^>]*)>')

    def repl(m: re.Match[str]) -> str:
        attrs = m.group(1)
        if re.search(r'\ss="\d+"', attrs):
            attrs = re.sub(r'\ss="\d+"', f' s="{xf_idx}"', attrs, count=1)
        else:
            attrs = f' s="{xf_idx}"' + attrs
        return f'<c r="{cell_ref}"{attrs}>'

    return pattern.sub(repl, sheet_xml, count=1)
