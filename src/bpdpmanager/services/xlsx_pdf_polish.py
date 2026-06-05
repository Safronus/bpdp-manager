"""Kosmetické úpravy **dočasné kopie** XLSX před převodem do PDF.

Uložený XLSX (přílohu k práci) necháváme 1:1 se šablonou — tyhle úpravy se
dělají jen na dočasné kopii, kterou pak LibreOffice převede do PDF:

1. **Vyvážené okraje** — ``horizontalCentered`` vycentruje tisk na stránce,
   takže vpravo vznikne stejná mezera jako vlevo.
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
        changed |= _center_print(parts, names)
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


def _center_print(parts: dict[str, bytes], names: list[str]) -> bool:
    """Zapne ``horizontalCentered`` na všech listech (vyvážené okraje)."""
    changed = False
    for n in names:
        if not _SHEET_RE.match(n):
            continue
        s = parts[n].decode("utf-8")
        if "<printOptions" in s:
            if "horizontalCentered" not in s:
                s = s.replace(
                    "<printOptions", '<printOptions horizontalCentered="1"', 1
                )
                changed = True
        else:
            tag = '<printOptions horizontalCentered="1"/>'
            if "<pageMargins" in s:  # printOptions musí být před pageMargins
                s = s.replace("<pageMargins", tag + "<pageMargins", 1)
                changed = True
            elif "</worksheet>" in s:
                s = s.replace("</worksheet>", tag + "</worksheet>", 1)
                changed = True
        parts[n] = s.encode("utf-8")
    return changed


def _restyle_body_header(parts: dict[str, bytes], names: list[str]) -> bool:
    """Buňce „Body (0–5)" dá menší a černý font (klon stylu, jen tahle buňka)."""
    ss = parts.get("xl/sharedStrings.xml")
    styles = parts.get("xl/styles.xml")
    if ss is None or styles is None:
        return False

    # 1) index sdíleného řetězce „Body (0…"
    target_si = None
    for i, si in enumerate(ET.fromstring(ss)):
        txt = "".join(t.text or "" for t in si.iter() if t.tag.endswith("}t"))
        norm = txt.lower().replace(" ", "")
        if norm.startswith("body(0") or norm.startswith("body(0–"):
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
