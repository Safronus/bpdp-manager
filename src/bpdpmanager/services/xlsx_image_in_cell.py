"""Zploštění „obrázku v buňce" (Excel rich-value image / *Place in Cell*).

Excel umožňuje vložit obrázek **do buňky** (IMAGE / Vložit obrázek → *Umístit
do buňky*). Takový obrázek se neuloží jako klasický plovoucí drawing, ale jako
**rich value** (``xl/richData/…`` + ``xl/media/…``); samotná buňka nese jen
náhradní chybovou hodnotu ``#VALUE!`` (``t="e"`` + ``vm`` = value metadata).

LibreOffice tuhle Excel funkci **neumí vykreslit** → při převodu do PDF logo
zmizí a místo něj se ukáže ``#VALUE!``. Excel ji umí, takže „Uložit jako PDF"
přímo z Excelu vypadá správně.

Tento modul vezme XLSX a vyrobí **kopii**, kde je každý „obrázek v buňce"
převedený na běžný **anchored drawing** (``xl/drawings/…``) a chybová buňka
vyčištěná. Vstup se nemění — transformuje se jen kopie určená pro převod do PDF,
takže uživatel, který otevře původní XLSX v Excelu, má dál nativní obrázek
v buňce.

Použití::

    if flatten_image_in_cell(src_xlsx, tmp_xlsx):
        # tmp_xlsx má logo jako plovoucí obrázek → pošli ho do LibreOffice
    else:
        # nic k řešení, src_xlsx neobsahuje „obrázek v buňce"
"""

from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

# Jednotky DrawingML
EMU_PER_PX = 9525
EMU_PER_PT = 12700

# Namespaces
_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS_XLRD = "http://schemas.microsoft.com/office/spreadsheetml/2017/richdata"
_NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

_RICHVALUEREL_RELS = "xl/richData/_rels/richValueRel.xml.rels"


def has_image_in_cell(parts: dict[str, bytes]) -> bool:
    """True, pokud sešit obsahuje aspoň jeden „obrázek v buňce"."""
    return _RICHVALUEREL_RELS in parts and "xl/richData/richValueRel.xml" in parts


def flatten_image_in_cell(src: Path, dst: Path) -> bool:
    """Vyrobí ``dst`` jako kopii ``src`` s plochými plovoucími obrázky.

    Vrací ``True`` pokud byl aspoň jeden „obrázek v buňce" převeden (a ``dst``
    je tedy upravená kopie). Pokud sešit žádný nemá, jen zkopíruje ``src`` →
    ``dst`` a vrátí ``False``. Při jakékoli chybě transformace nechá ``dst``
    jako věrnou kopii ``src`` (fail-safe — radši PDF bez loga než spadlý převod).
    """
    with zipfile.ZipFile(src) as zin:
        names = zin.namelist()
        parts: dict[str, bytes] = {n: zin.read(n) for n in names}

    if not has_image_in_cell(parts):
        shutil.copy2(src, dst)
        return False

    try:
        changed = _transform_parts(parts, names)
    except Exception:  # noqa: BLE001 — fail-safe, nikdy nesmí shodit generování
        changed = False

    if not changed:
        shutil.copy2(src, dst)
        return False

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            zout.writestr(n, parts[n])
    return True


# ── interní transformace ─────────────────────────────────────────────────────


def _transform_parts(parts: dict[str, bytes], names: list[str]) -> bool:
    """Mutuje ``parts`` (a doplňuje do ``names`` nové party). Vrací True při změně."""
    rel_to_media = _image_rel_targets(parts)  # rel index -> "xl/media/imageN.ext"
    if not rel_to_media:
        return False
    vm_to_rel = _vm_to_rel_index(parts)  # vm (int) -> rel index

    any_changed = False
    drawing_seq = _existing_drawing_count(names)

    # Projdi všechny listy a najdi buňky s atributem vm.
    for sheet_name in [n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml$", n)]:
        sheet_xml = parts[sheet_name].decode("utf-8")
        vm_cells = _find_vm_cells(sheet_xml)  # [(cell_ref, vm_int)]
        if not vm_cells:
            continue

        anchors: list[str] = []
        rel_ids: list[tuple[str, str]] = []  # (drawing_rel_id, media_target_rel_from_drawing)
        geom = _SheetGeometry(sheet_xml)

        for cell_ref, vm in vm_cells:
            # vždy vyčisti chybovou (#VALUE!) hodnotu — v PDF ji nikdy nechceme
            sheet_xml = _clear_error_cell(sheet_xml, cell_ref)
            any_changed = True

            rel_idx = vm_to_rel.get(vm)
            if rel_idx is None:
                rel_idx = next(iter(rel_to_media)) if len(rel_to_media) == 1 else None
            if rel_idx is None or rel_idx not in rel_to_media:
                continue
            media_part = rel_to_media[rel_idx]  # "xl/media/imageN.ext"

            ext = _image_extent_emu(parts.get(media_part, b""), geom, cell_ref)
            if ext is None:
                continue
            cx, cy, off_x, off_y = ext
            drawing_rel_id = f"rIdImg{len(anchors) + 1}"
            anchors.append(
                _anchor_xml(cell_ref, cx, cy, off_x, off_y, drawing_rel_id, len(anchors) + 2)
            )
            media_from_drawing = "../" + media_part[len("xl/"):]  # ../media/imageN.ext
            rel_ids.append((drawing_rel_id, media_from_drawing))

        # Zapiš upravený list zpět
        parts[sheet_name] = sheet_xml.encode("utf-8")

        if not anchors:
            continue

        # Vyrob drawing part + jeho rels + napoj na list + content type
        drawing_seq += 1
        drawing_part = f"xl/drawings/drawing{drawing_seq}.xml"
        drawing_rels_part = f"xl/drawings/_rels/drawing{drawing_seq}.xml.rels"
        sheet_drawing_rel_id = _append_sheet_drawing(parts, names, sheet_name, drawing_part)

        parts[drawing_part] = _drawing_doc(anchors).encode("utf-8")
        names.append(drawing_part)
        parts[drawing_rels_part] = _drawing_rels(rel_ids).encode("utf-8")
        names.append(drawing_rels_part)

        # <drawing r:id="…"/> do listu
        parts[sheet_name] = _insert_drawing_ref(
            parts[sheet_name].decode("utf-8"), sheet_drawing_rel_id
        ).encode("utf-8")

        _add_content_type_override(parts, drawing_part)
        any_changed = True

    return any_changed


def _image_rel_targets(parts: dict[str, bytes]) -> dict[int, str]:
    """Mapuje pořadový index v ``richValueRel.xml`` → cesta k médiu v balíčku.

    ``richValueRel.xml`` má ``<rel r:id="rIdN"/>`` v pořadí; ``…rels`` přeloží
    rId na ``../media/imageN.ext``. Index (0-based) odpovídá hodnotě klíče
    ``_rvRel:LocalImageIdentifier`` v rich value.
    """
    rel_xml = parts.get("xl/richData/richValueRel.xml")
    rels_xml = parts.get(_RICHVALUEREL_RELS)
    if rel_xml is None or rels_xml is None:
        return {}

    rid_to_target: dict[str, str] = {}
    for rel in ET.fromstring(rels_xml):
        rid = rel.get("Id")
        target = rel.get("Target", "")
        if rid and target:
            # Target je relativní k xl/richData/ → normalizuj na cestu v balíčku
            norm = target.replace("../", "")
            rid_to_target[rid] = "xl/" + norm if not norm.startswith("xl/") else norm

    out: dict[int, str] = {}
    for idx, rel in enumerate(ET.fromstring(rel_xml)):
        rid = rel.get(f"{{{_NS_REL}}}id")
        if rid and rid in rid_to_target:
            out[idx] = rid_to_target[rid]
    return out


def _vm_to_rel_index(parts: dict[str, bytes]) -> dict[int, int]:
    """Sestaví mapu ``vm`` (value metadata, 1-based) → index obrázku v richValueRel.

    Řetězec: vm → metadata.xml valueMetadata → futureMetadata XLRICHVALUE →
    rdrichvalue rv → klíč ``_rvRel:LocalImageIdentifier`` (struktura) → index.
    Při neúspěchu vrací prázdnou mapu (volající má fallback na jediný obrázek).
    """
    meta = parts.get("xl/metadata.xml")
    rv = parts.get("xl/richData/rdrichvalue.xml")
    struct = parts.get("xl/richData/rdrichvaluestructure.xml")
    if meta is None or rv is None or struct is None:
        return {}

    # 1) Struktury → pro každou strukturu index klíče s LocalImageIdentifier
    struct_key_idx: dict[int, int] = {}
    for s_idx, s in enumerate(ET.fromstring(struct)):
        for k_idx, k in enumerate(s):
            name = k.get("n", "")
            if "LocalImageIdentifier" in name:
                struct_key_idx[s_idx] = k_idx
                break

    # 2) rdrichvalue rv → rel index (hodnota klíče LocalImageIdentifier)
    rv_to_rel: dict[int, int] = {}
    for rv_idx, rvel in enumerate(ET.fromstring(rv)):
        s_idx = int(rvel.get("s", "0"))
        key_idx = struct_key_idx.get(s_idx)
        if key_idx is None:
            continue
        vs = [v.text for v in rvel.findall(f"{{{_NS_XLRD}}}v")]
        if key_idx < len(vs) and vs[key_idx] is not None:
            try:
                rv_to_rel[rv_idx] = int(vs[key_idx])
            except ValueError:
                pass

    # 3) metadata.xml — vm → futureMetadata bk index → rvb i → rv index
    root = ET.fromstring(meta)
    future = None
    for fm in root.findall(f"{{{_NS_MAIN}}}futureMetadata"):
        if fm.get("name") == "XLRICHVALUE":
            future = fm
            break
    if future is None:
        return {}
    future_bks = future.findall(f"{{{_NS_MAIN}}}bk")
    future_to_rv: dict[int, int] = {}
    for bk_idx, bk in enumerate(future_bks):
        rvb = bk.find(f".//{{{_NS_XLRD}}}rvb")
        if rvb is not None and rvb.get("i") is not None:
            future_to_rv[bk_idx] = int(rvb.get("i"))

    value_meta = root.find(f"{{{_NS_MAIN}}}valueMetadata")
    if value_meta is None:
        return {}
    out: dict[int, int] = {}
    for bk_idx, bk in enumerate(value_meta.findall(f"{{{_NS_MAIN}}}bk")):
        rc = bk.find(f"{{{_NS_MAIN}}}rc")
        if rc is None or rc.get("v") is None:
            continue
        future_idx = int(rc.get("v"))
        rv_idx = future_to_rv.get(future_idx)
        if rv_idx is None:
            continue
        rel_idx = rv_to_rel.get(rv_idx)
        if rel_idx is None:
            continue
        out[bk_idx + 1] = rel_idx  # vm je 1-based
    return out


def _find_vm_cells(sheet_xml: str) -> list[tuple[str, int]]:
    """Najde buňky s atributem ``vm`` (= obrázek v buňce). Vrací [(ref, vm)]."""
    out: list[tuple[str, int]] = []
    for m in re.finditer(r'<c r="([A-Z]+\d+)"[^>]*\bvm="(\d+)"', sheet_xml):
        out.append((m.group(1), int(m.group(2))))
    return out


def _clear_error_cell(sheet_xml: str, cell_ref: str) -> str:
    """Vyčistí chybovou hodnotu buňky (#VALUE!) — zachová styl ``s``."""
    pattern = re.compile(
        r'<c r="' + re.escape(cell_ref) + r'"([^>]*?)(?:/>|>.*?</c>)',
        re.DOTALL,
    )

    def repl(m: re.Match[str]) -> str:
        attrs = m.group(1)
        s_match = re.search(r'\ss="(\d+)"', attrs)
        s_attr = f' s="{s_match.group(1)}"' if s_match else ""
        return f'<c r="{cell_ref}"{s_attr}/>'

    return pattern.sub(repl, sheet_xml, count=1)


def _insert_drawing_ref(sheet_xml: str, rel_id: str) -> str:
    """Vloží ``<drawing r:id="…"/>`` na konec listu (před ``</worksheet>``)."""
    tag = f'<drawing r:id="{rel_id}"/>'
    if "<drawing " in sheet_xml:  # už nějaký drawing má — nepřidávej druhý
        return sheet_xml
    return sheet_xml.replace("</worksheet>", tag + "</worksheet>", 1)


def _append_sheet_drawing(
    parts: dict[str, bytes], names: list[str], sheet_name: str, drawing_part: str
) -> str:
    """Doplní relaci listu na drawing part. Vrací rId relace."""
    rels_name = sheet_name.replace(
        "xl/worksheets/", "xl/worksheets/_rels/"
    ) + ".rels"
    target = "../drawings/" + Path(drawing_part).name

    if rels_name in parts:
        rels_xml = parts[rels_name].decode("utf-8")
        existing = [int(x) for x in re.findall(r'Id="rId(\d+)"', rels_xml)]
        rid = f"rId{max(existing, default=0) + 1}"
        rels_xml = rels_xml.replace(
            "</Relationships>",
            f'<Relationship Id="{rid}" Type="{_NS_REL}/drawing" '
            f'Target="{target}"/></Relationships>',
        )
        parts[rels_name] = rels_xml.encode("utf-8")
    else:
        rid = "rId1"
        rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{_NS_PKG_REL}">'
            f'<Relationship Id="{rid}" Type="{_NS_REL}/drawing" '
            f'Target="{target}"/></Relationships>'
        )
        parts[rels_name] = rels_xml.encode("utf-8")
        names.append(rels_name)
    return rid


def _add_content_type_override(parts: dict[str, bytes], drawing_part: str) -> None:
    ct = parts["[Content_Types].xml"].decode("utf-8")
    override = (
        f'<Override PartName="/{drawing_part}" '
        'ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>'
    )
    if override not in ct:
        ct = ct.replace("</Types>", override + "</Types>")
    parts["[Content_Types].xml"] = ct.encode("utf-8")


def _existing_drawing_count(names: list[str]) -> int:
    nums = [
        int(m.group(1))
        for n in names
        if (m := re.match(r"xl/drawings/drawing(\d+)\.xml$", n))
    ]
    return max(nums, default=0)


def _drawing_doc(anchors: list[str]) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"'
        ' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        + "".join(anchors)
        + "</xdr:wsDr>"
    )


def _anchor_xml(
    cell_ref: str, cx: int, cy: int, off_x: int, off_y: int, rel_id: str, pic_id: int
) -> str:
    col, row = _ref_to_col_row(cell_ref)
    return (
        "<xdr:oneCellAnchor>"
        f"<xdr:from><xdr:col>{col}</xdr:col><xdr:colOff>{off_x}</xdr:colOff>"
        f"<xdr:row>{row}</xdr:row><xdr:rowOff>{off_y}</xdr:rowOff></xdr:from>"
        f'<xdr:ext cx="{cx}" cy="{cy}"/>'
        "<xdr:pic><xdr:nvPicPr>"
        f'<xdr:cNvPr id="{pic_id}" name="Logo"/>'
        '<xdr:cNvPicPr><a:picLocks noChangeAspect="1"/></xdr:cNvPicPr>'
        "</xdr:nvPicPr>"
        "<xdr:blipFill>"
        f'<a:blip xmlns:r="{_NS_REL}" r:embed="{rel_id}"/>'
        "<a:stretch><a:fillRect/></a:stretch></xdr:blipFill>"
        f'<xdr:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr>'
        "</xdr:pic><xdr:clientData/></xdr:oneCellAnchor>"
    )


def _drawing_rels(rel_ids: list[tuple[str, str]]) -> str:
    rels = "".join(
        f'<Relationship Id="{rid}" Type="{_NS_REL}/image" Target="{target}"/>'
        for rid, target in rel_ids
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{_NS_PKG_REL}">{rels}</Relationships>'
    )


def _image_extent_emu(
    img_bytes: bytes, geom: _SheetGeometry, cell_ref: str
) -> tuple[int, int, int, int] | None:
    """Spočítá velikost (cx, cy) a malý offset obrázku tak, aby se vešel do
    sloučené oblasti buňky se zachováním poměru stran. Vrací EMU."""
    try:
        from io import BytesIO

        from PIL import Image

        with Image.open(BytesIO(img_bytes)) as im:
            iw, ih = im.size
    except Exception:  # noqa: BLE001
        return None
    if iw <= 0 or ih <= 0:
        return None

    region_w, region_h = geom.region_emu(cell_ref)
    if region_w <= 0 or region_h <= 0:
        return None

    # malý vnitřní okraj, ať logo není nalepené na hraně
    pad = int(min(region_w, region_h) * 0.06)
    avail_w = max(region_w - 2 * pad, 1)
    avail_h = max(region_h - 2 * pad, 1)

    aspect = iw / ih
    cx = avail_w
    cy = round(cx / aspect)
    if cy > avail_h:
        cy = avail_h
        cx = round(cy * aspect)
    # Vycentruj logo v oblasti buňky (vodorovně i svisle).
    off_x = max((region_w - cx) // 2, 0)
    off_y = max((region_h - cy) // 2, 0)
    return cx, cy, off_x, off_y


class _SheetGeometry:
    """Čte šířky sloupců, výšky řádků a sloučené buňky z XML listu."""

    def __init__(self, sheet_xml: str) -> None:
        root = ET.fromstring(sheet_xml)
        fmt = root.find(f"{{{_NS_MAIN}}}sheetFormatPr")
        self.default_col_w = float(fmt.get("defaultColWidth", "8.43")) if fmt is not None else 8.43
        self.default_row_h = float(fmt.get("defaultRowHeight", "15")) if fmt is not None else 15.0

        # šířky sloupců: min..max → width
        self.col_widths: dict[int, float] = {}
        cols = root.find(f"{{{_NS_MAIN}}}cols")
        if cols is not None:
            for col in cols:
                cmin = int(col.get("min", "1"))
                cmax = int(col.get("max", str(cmin)))
                w = float(col.get("width", str(self.default_col_w)))
                for c in range(cmin, cmax + 1):
                    self.col_widths[c] = w

        # výšky řádků
        self.row_heights: dict[int, float] = {}
        data = root.find(f"{{{_NS_MAIN}}}sheetData")
        if data is not None:
            for row in data:
                r = int(row.get("r", "0"))
                ht = row.get("ht")
                if r and ht is not None:
                    self.row_heights[r] = float(ht)

        # sloučené buňky
        self.merges: list[tuple[int, int, int, int]] = []  # (c1,r1,c2,r2) 0-based
        mc = root.find(f"{{{_NS_MAIN}}}mergeCells")
        if mc is not None:
            for cell in mc:
                ref = cell.get("ref", "")
                if ":" in ref:
                    a, b = ref.split(":")
                    c1, r1 = _ref_to_col_row(a)
                    c2, r2 = _ref_to_col_row(b)
                    self.merges.append((c1, r1, c2, r2))

    def _col_w_emu(self, col0: int) -> int:
        w = self.col_widths.get(col0 + 1, self.default_col_w)
        px = round(w * 7 + 5)  # přibližně (Calibri 11, MDW=7)
        return px * EMU_PER_PX

    def _row_h_emu(self, row0: int) -> int:
        h = self.row_heights.get(row0 + 1, self.default_row_h)
        return round(h * EMU_PER_PT)

    def region_emu(self, cell_ref: str) -> tuple[int, int]:
        """Rozměr (šířka, výška) oblasti buňky v EMU — respektuje merge."""
        col, row = _ref_to_col_row(cell_ref)
        c1, r1, c2, r2 = col, row, col, row
        for mc1, mr1, mc2, mr2 in self.merges:
            if mc1 <= col <= mc2 and mr1 <= row <= mr2:
                c1, r1, c2, r2 = mc1, mr1, mc2, mr2
                break
        width = sum(self._col_w_emu(c) for c in range(c1, c2 + 1))
        height = sum(self._row_h_emu(r) for r in range(r1, r2 + 1))
        return width, height


def _ref_to_col_row(ref: str) -> tuple[int, int]:
    """``A1`` → (0, 0); ``D4`` → (3, 3). 0-based sloupec, řádek."""
    m = re.match(r"([A-Z]+)(\d+)", ref)
    if not m:
        return 0, 0
    letters, digits = m.group(1), m.group(2)
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch) - ord("A") + 1)
    return col - 1, int(digits) - 1
