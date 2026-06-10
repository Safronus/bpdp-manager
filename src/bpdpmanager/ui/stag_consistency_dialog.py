"""Kontrola konzistence souborů: co STAG nabízí vs. co máš v databázi.

Projde práce (vedené i oponentury) s STAG ID, dotáhne ze STAG seznam souborů
a porovná **druhy dokumentů**: nahlásí, kde STAG nabízí druh (plný text /
příloha / posudek), který u práce v databázi ještě nemáš — a umožní chybějící
soubory **rovnou dostáhnout**. Budoucí práce (zájemci / vypsaná témata) se
nekontrolují (ještě ve STAG soubory nemají).
"""

from __future__ import annotations

import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressDialog,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from ..i18n import tr
from ..models.enums import STATUSES_FUTURE, AttachmentKind
from ..services import BackupManager, stag_api
from .stag_import_dialog import _SECTION_TO_KIND, _fmt_size


@dataclass
class _Row:
    is_opposing: bool
    obj_id: str
    label: str
    adipidno: str
    db_kinds: set
    missing: list = field(default_factory=list)  # [(AttachmentKind, StagFile)]
    error: str = ""


def _fetch_files(adipidno: str):
    """Vrátí (seznam souborů STAG, chyba)."""
    try:
        return stag_api.list_thesis_files(adipidno), ""
    except Exception as exc:  # noqa: BLE001
        return [], str(exc)


# UserRole na listu souboru: index řádku v self._rows a index souboru v missing.
_ROLE_ROW = Qt.ItemDataRole.UserRole + 1
_ROLE_FILE = Qt.ItemDataRole.UserRole + 2


class StagConsistencyDialog(QDialog):
    """Přehled prací, u kterých STAG nabízí soubory chybějící v DB + dostažení."""

    changed = Signal()

    def __init__(self, service, parent=None, *, profile_manager=None) -> None:
        super().__init__(parent)
        self.service = service
        self.profile_manager = profile_manager
        self.changed_any = False
        self._rows: list[_Row] = []
        self._no_id: list[str] = []

        self.setWindowTitle(tr("Kontrola konzistence se STAG"))
        self.setMinimumSize(860, 620)
        self.resize(1040, 780)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        title = QLabel(tr("🔍 Kontrola konzistence se STAG"))
        title.setStyleSheet("font-size:16px;font-weight:bold;")
        outer.addWidget(title)

        intro = QLabel(
            tr("Porovná soubory u prací (vedených i oponovaných) se STAG a vypíše, "
            "kde STAG nabízí <b>druh dokumentu</b> (plný text / příloha / posudek), "
            "který <b>v databázi chybí</b>. Zaškrtnuté soubory můžeš rovnou "
            "<b>dostáhnout</b>. Budoucí práce (zájemci / vypsaná témata) se "
            "nekontrolují.")
        )
        intro.setTextFormat(Qt.TextFormat.RichText)
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#888;")
        outer.addWidget(intro)

        self.lbl_status = QLabel(tr("⏳ Porovnávám se STAG…"))
        self.lbl_status.setWordWrap(True)
        outer.addWidget(self.lbl_status)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemChanged.connect(lambda _i: self._update_btn())
        outer.addWidget(self.tree, stretch=1)

        row = QHBoxLayout()
        btn_close = QPushButton(tr("Zavřít"))
        btn_close.clicked.connect(self.accept)
        self.btn_download = QPushButton(tr("⬇ Dostáhnout vybrané"))
        self.btn_download.setEnabled(False)
        bf = self.btn_download.font()
        bf.setBold(True)
        self.btn_download.setFont(bf)
        self.btn_download.clicked.connect(self._download_selected)
        row.addStretch()
        row.addWidget(btn_close)
        row.addWidget(self.btn_download)
        outer.addLayout(row)

        QTimer.singleShot(0, self._scan)

    # --- sběr + dotažení -----------------------------------------------------

    def _collect(self) -> list[_Row]:
        rows: list[_Row] = []
        for t in self.service.list_theses():
            # Budoucí práce (zájemce / vypsané téma) se nekontrolují — ve STAG
            # ještě soubory nemají.
            if t.status in STATUSES_FUTURE:
                continue
            student = self.service.get_student(t.student_id) if t.student_id else None
            name = student.full_name if student else "(neznámý student)"
            label = f"{name} — {t.title_cs or '(bez názvu)'} ({t.type.value})"
            if not t.adipidno:
                self._no_id.append(label)
                continue
            rows.append(_Row(
                is_opposing=False, obj_id=t.id, label=label, adipidno=t.adipidno,
                db_kinds={a.kind for a in t.attachments if a.is_current},
            ))
        for o in self.service.list_opposing_theses():
            name = f"{o.student_last_name} {o.student_first_name}".strip() or "(student)"
            label = f"{name} — {o.title_cs or '(bez názvu)'} ({o.type.value}) — oponentura"
            if not o.adipidno:
                self._no_id.append(label)
                continue
            rows.append(_Row(
                is_opposing=True, obj_id=o.id, label=label, adipidno=o.adipidno,
                db_kinds={a.kind for a in o.attachments if a.is_current},
            ))
        return rows

    def _scan(self) -> None:
        self._no_id = []
        rows = self._collect()
        if not rows:
            self.lbl_status.setText(
                "Žádné práce s STAG ID k ověření "
                f"({len(self._no_id)} prací nemá STAG ID)."
            )
            self._rows = []
            self._populate()
            return

        progress = QProgressDialog(
            "Porovnávám soubory se STAG…", "Přerušit", 0, len(rows), self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        executor = ThreadPoolExecutor(max_workers=8)
        futures = {executor.submit(_fetch_files, r.adipidno): r for r in rows}
        done = 0
        try:
            for fut in as_completed(futures):
                r = futures[fut]
                try:
                    files, err = fut.result()
                except Exception as exc:  # noqa: BLE001
                    files, err = [], str(exc)
                if err:
                    r.error = err
                else:
                    for sf in files:
                        kind = _SECTION_TO_KIND.get(sf.section, AttachmentKind.OTHER)
                        if kind not in r.db_kinds:
                            r.missing.append((kind, sf))
                done += 1
                progress.setValue(done)
                QApplication.processEvents()
                if progress.wasCanceled():
                    break
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
            progress.close()

        self._rows = rows
        self._populate()

    # --- výpis ---------------------------------------------------------------

    def _populate(self) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        gray = QBrush(QColor("#888"))
        amber = QBrush(QColor("#e65100"))

        rows = self._rows
        missing_rows = [(i, r) for i, r in enumerate(rows) if r.missing and not r.error]
        ok_rows = [r for r in rows if not r.missing and not r.error]
        err_rows = [r for r in rows if r.error]

        if missing_rows:
            head = QTreeWidgetItem([f"⚠ Chybí soubory ({len(missing_rows)})"])
            f = head.font(0)
            f.setBold(True)
            head.setFont(0, f)
            self.tree.addTopLevelItem(head)
            for ri, r in sorted(missing_rows, key=lambda x: x[1].label.lower()):
                node = QTreeWidgetItem([r.label])
                node.setForeground(0, amber)
                head.addChild(node)
                for fi, (kind, sf) in enumerate(r.missing):
                    size = f"  ·  {_fmt_size(sf.size_hint)}" if sf.size_hint else ""
                    leaf = QTreeWidgetItem([f"📎 {kind.label}: {sf.filename}{size}"])
                    leaf.setFlags(
                        (leaf.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                        & ~Qt.ItemFlag.ItemIsAutoTristate
                    )
                    leaf.setCheckState(0, Qt.CheckState.Checked)
                    leaf.setData(0, _ROLE_ROW, ri)
                    leaf.setData(0, _ROLE_FILE, fi)
                    node.addChild(leaf)
                node.setExpanded(True)
            head.setExpanded(True)

        if err_rows:
            head = QTreeWidgetItem([f"✗ Nepodařilo se ověřit ({len(err_rows)})"])
            self.tree.addTopLevelItem(head)
            for r in err_rows:
                leaf = QTreeWidgetItem([f"{r.label} — {r.error}"])
                leaf.setForeground(0, gray)
                head.addChild(leaf)
            head.setExpanded(True)

        if self._no_id:
            head = QTreeWidgetItem([f"❔ Bez STAG ID — nelze ověřit ({len(self._no_id)})"])
            self.tree.addTopLevelItem(head)
            for label in sorted(self._no_id):
                leaf = QTreeWidgetItem([label])
                leaf.setForeground(0, gray)
                head.addChild(leaf)

        ok_head = QTreeWidgetItem([f"✓ Kompletní podle STAG ({len(ok_rows)})"])
        ok_head.setForeground(0, QBrush(QColor("#2e7d32")))
        self.tree.addTopLevelItem(ok_head)
        self.tree.blockSignals(False)

        total = len(rows)
        miss = len(missing_rows)
        self.lbl_status.setText(
            f"Ověřeno {total} prací: <b>{miss}</b> má ve STAG soubory, které "
            f"v databázi chybí. Bez STAG ID: {len(self._no_id)}."
        )
        self.lbl_status.setTextFormat(Qt.TextFormat.RichText)
        self._update_btn()

    # --- výběr + dostažení ---------------------------------------------------

    def _checked_leaves(self) -> list[QTreeWidgetItem]:
        out: list[QTreeWidgetItem] = []

        def walk(item: QTreeWidgetItem) -> None:
            for i in range(item.childCount()):
                walk(item.child(i))
            if (
                item.data(0, _ROLE_ROW) is not None
                and item.data(0, _ROLE_FILE) is not None
                and item.checkState(0) == Qt.CheckState.Checked
            ):
                out.append(item)

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            walk(root.child(i))
        return out

    def _update_btn(self) -> None:
        n = len(self._checked_leaves())
        self.btn_download.setEnabled(n > 0)
        self.btn_download.setText(
            "⬇ Dostáhnout vybrané" if n == 0 else f"⬇ Dostáhnout vybrané ({n})"
        )

    @staticmethod
    def _leaf_label(kind, sf) -> str:
        size = f"  ·  {_fmt_size(sf.size_hint)}" if sf.size_hint else ""
        return f"{kind.label}: {sf.filename}{size}"

    def _mark(self, leaf: QTreeWidgetItem, text: str, color: str,
              done: bool = False) -> None:
        leaf.setText(0, text)
        leaf.setForeground(0, QBrush(QColor(color)))
        if done:
            # Hotovo → už nelze znovu vybrat (a nepočítá se do výběru).
            self.tree.blockSignals(True)
            leaf.setCheckState(0, Qt.CheckState.Unchecked)
            leaf.setFlags(leaf.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            leaf.setData(0, _ROLE_ROW, None)
            leaf.setData(0, _ROLE_FILE, None)
            self.tree.blockSignals(False)

    def _download_selected(self) -> None:
        leaves = self._checked_leaves()
        if not leaves:
            return
        self.btn_download.setEnabled(False)

        # Záloha (záchranná brzda).
        if self.profile_manager and self.profile_manager.active:
            data_dir = self.profile_manager.active_data_dir()
            try:
                BackupManager(data_dir).create_backup(
                    data_dir / "db.json", suffix="before-stag-consistency", dedupe=False
                )
            except Exception:  # noqa: BLE001
                pass

        # Seskup listy dle práce (řádku) — soubory jedné práce sdílí session.
        by_row: dict[int, list[QTreeWidgetItem]] = {}
        for leaf in leaves:
            by_row.setdefault(leaf.data(0, _ROLE_ROW), []).append(leaf)

        executor = ThreadPoolExecutor(max_workers=1)
        attached = 0
        errors = 0
        try:
            for ri, row_leaves in by_row.items():
                r = self._rows[ri]
                client = stag_api.StagClient()
                try:
                    files = client.list_thesis_files(r.adipidno)
                except Exception:  # noqa: BLE001
                    for leaf in row_leaves:
                        self._mark(leaf, "✗ chyba: výpis souborů ze STAG", "#c62828")
                    errors += len(row_leaves)
                    continue
                by_soub = {f.soubidno: f for f in files}
                any_here = False
                for leaf in row_leaves:
                    kind, sf0 = r.missing[leaf.data(0, _ROLE_FILE)]
                    sf = by_soub.get(sf0.soubidno, sf0)
                    label = self._leaf_label(kind, sf)
                    data, err = self._download_bytes(executor, client, sf, leaf, label)
                    if data is None:
                        reason = err or "nestaženo"
                        self._mark(leaf, f"✗ {label} — {reason}", "#c62828")
                        errors += 1
                        continue
                    safe = sf.filename or f"soubor_{sf.soubidno}"
                    tmp = (
                        Path(tempfile.gettempdir())
                        / f"stagchk_{r.adipidno}_{sf.soubidno}_{safe}"
                    )
                    try:
                        tmp.write_bytes(data)
                    except OSError:
                        self._mark(leaf, f"✗ {label} — zápis selhal", "#c62828")
                        errors += 1
                        continue
                    kind_a = _SECTION_TO_KIND.get(sf.section, AttachmentKind.OTHER)
                    try:
                        if r.is_opposing:
                            self.service.opposing_attach_document(r.obj_id, tmp, kind=kind_a)
                        else:
                            self.service.attach_document(r.obj_id, tmp, kind=kind_a)
                        attached += 1
                        any_here = True
                        self._mark(leaf, f"✓ {label} — staženo", "#2e7d32", done=True)
                    except Exception:  # noqa: BLE001
                        self._mark(leaf, f"✗ {label} — nepřipojeno", "#c62828")
                        errors += 1
                if any_here:
                    try:
                        if r.is_opposing:
                            self.service.sync_opposing_grades(r.obj_id)
                        else:
                            self.service.sync_thesis_grades(r.obj_id)
                    except Exception:  # noqa: BLE001
                        pass
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        if attached:
            self.changed_any = True
            self.changed.emit()
        msg = f"Dostaženo souborů: <b>{attached}</b>"
        if errors:
            msg += f"  ·  chyby: {errors}"
        msg += ".  Zbývající nestažené zůstávají v seznamu."
        self.lbl_status.setText(msg)
        self.lbl_status.setTextFormat(Qt.TextFormat.RichText)
        self._update_btn()

    def _download_bytes(self, executor, client, sf, leaf: QTreeWidgetItem, label: str):
        """Stáhne soubor na vlákně, v řádku ukazuje průběh.

        Vrací ``(data, None)`` při úspěchu, ``(None, popis_chyby)`` při selhání
        (popis rozliší timeout od jiné chyby).
        """
        state = {"downloaded": 0, "total": None}

        def cb(downloaded, total, _s=state):
            _s["downloaded"] = downloaded
            _s["total"] = total
            return True

        fut = executor.submit(
            client.download_file_streamed, sf.download_path, cb,
            timeout=stag_api.download_timeout_for(sf.size_hint),
        )
        while not fut.done():
            dn = state["downloaded"]
            tot = state["total"] or sf.size_hint or 0
            if dn <= 0:
                leaf.setText(0, f"⏳ {label} — STAG připravuje soubor (čekám)…")
            else:
                sz = (
                    f"{_fmt_size(dn)} / {_fmt_size(tot)}" if tot else _fmt_size(dn)
                )
                leaf.setText(0, f"⏳ {label} — {sz}")
            QApplication.processEvents()
            QThread.msleep(40)
        try:
            return fut.result(), None
        except stag_api.StagError as exc:
            return None, str(exc)
        except Exception as exc:  # noqa: BLE001
            return None, str(exc)
