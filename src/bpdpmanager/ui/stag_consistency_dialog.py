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

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

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

        self.setWindowTitle("Kontrola konzistence se STAG")
        self.setMinimumSize(860, 620)
        self.resize(1040, 780)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        title = QLabel("🔍 Kontrola konzistence se STAG")
        title.setStyleSheet("font-size:16px;font-weight:bold;")
        outer.addWidget(title)

        intro = QLabel(
            "Porovná soubory u prací (vedených i oponovaných) se STAG a vypíše, "
            "kde STAG nabízí <b>druh dokumentu</b> (plný text / příloha / posudek), "
            "který <b>v databázi chybí</b>. Zaškrtnuté soubory můžeš rovnou "
            "<b>dostáhnout</b>. Budoucí práce (zájemci / vypsaná témata) se "
            "nekontrolují."
        )
        intro.setTextFormat(Qt.TextFormat.RichText)
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#888;")
        outer.addWidget(intro)

        self.lbl_status = QLabel("⏳ Porovnávám se STAG…")
        self.lbl_status.setWordWrap(True)
        outer.addWidget(self.lbl_status)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemChanged.connect(lambda _i: self._update_btn())
        outer.addWidget(self.tree, stretch=1)

        row = QHBoxLayout()
        btn_close = QPushButton("Zavřít")
        btn_close.clicked.connect(self.accept)
        self.btn_download = QPushButton("⬇ Dostáhnout vybrané")
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

    def _checked_files(self) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []

        def walk(item: QTreeWidgetItem) -> None:
            for i in range(item.childCount()):
                walk(item.child(i))
            ri = item.data(0, _ROLE_ROW)
            fi = item.data(0, _ROLE_FILE)
            if ri is not None and fi is not None and item.checkState(0) == Qt.CheckState.Checked:
                out.append((ri, fi))

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            walk(root.child(i))
        return out

    def _update_btn(self) -> None:
        n = len(self._checked_files())
        self.btn_download.setEnabled(n > 0)
        self.btn_download.setText(
            "⬇ Dostáhnout vybrané" if n == 0 else f"⬇ Dostáhnout vybrané ({n})"
        )

    def _download_selected(self) -> None:
        checked = self._checked_files()
        if not checked:
            return

        # Záloha (záchranná brzda).
        if self.profile_manager and self.profile_manager.active:
            data_dir = self.profile_manager.active_data_dir()
            try:
                BackupManager(data_dir).create_backup(
                    data_dir / "db.json", suffix="before-stag-consistency", dedupe=False
                )
            except Exception:  # noqa: BLE001
                pass

        # Seskup vybrané soubory dle práce (řádku).
        by_row: dict[int, list[int]] = {}
        for ri, fi in checked:
            by_row.setdefault(ri, []).append(fi)

        progress = QProgressDialog(
            "Dostahuji chybějící soubory…", "Přerušit", 0, len(by_row), self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        attached = 0
        errors: list[str] = []
        done = 0
        for ri, file_idxs in by_row.items():
            if progress.wasCanceled():
                break
            r = self._rows[ri]
            progress.setLabelText(f"Dostahuji:\n{r.label}")
            QApplication.processEvents()
            want_soub = {r.missing[fi][1].soubidno for fi in file_idxs}
            attached += self._download_for_work(r, want_soub, errors)
            done += 1
            progress.setValue(done)
            QApplication.processEvents()
        progress.close()

        if attached:
            self.changed_any = True
            self.changed.emit()

        # Souhrn + re-scan (aby zmizely dostažené).
        msg = f"Dostaženo souborů: {attached}."
        if errors:
            msg += "\n\nChyby:\n" + "\n".join(f"• {e}" for e in errors[:10])
        QMessageBox.information(self, "Kontrola se STAG", msg)
        self._scan()

    def _download_for_work(self, r: _Row, want_soub: set, errors: list) -> int:
        """Stáhne a připojí vybrané soubory jedné práce. Vrací počet připojených."""
        client = stag_api.StagClient()
        try:
            files = client.list_thesis_files(r.adipidno)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{r.label}: výpis souborů — {exc}")
            return 0
        by_soub = {f.soubidno: f for f in files}
        count = 0
        for soub in want_soub:
            sf = by_soub.get(soub)
            if sf is None:
                continue
            try:
                data = client.download_file(sf.download_path)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{r.label}: {sf.filename} — {exc}")
                continue
            safe = sf.filename or f"soubor_{soub}"
            tmp = Path(tempfile.gettempdir()) / f"stagchk_{r.adipidno}_{soub}_{safe}"
            try:
                tmp.write_bytes(data)
            except OSError as exc:
                errors.append(f"{r.label}: zápis {sf.filename} — {exc}")
                continue
            kind = _SECTION_TO_KIND.get(sf.section, AttachmentKind.OTHER)
            try:
                if r.is_opposing:
                    self.service.opposing_attach_document(r.obj_id, tmp, kind=kind)
                else:
                    self.service.attach_document(r.obj_id, tmp, kind=kind)
                count += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{r.label}: přiložení {sf.filename} — {exc}")
        # Dosynchronizuj známky z čerstvě připojených posudků.
        try:
            if r.is_opposing:
                self.service.sync_opposing_grades(r.obj_id)
            else:
                self.service.sync_thesis_grades(r.obj_id)
        except Exception:  # noqa: BLE001
            pass
        return count
