"""Kontrola konzistence souborů: co STAG nabízí vs. co máš v databázi.

Read-only audit — projde všechny práce (vedené i oponentury) s STAG ID,
dotáhne ze STAG seznam souborů a porovná **druhy dokumentů**: nahlásí, kde
STAG nabízí druh (plný text / příloha / posudek), který u práce v databázi
ještě nemáš. Stahování ani import zde neprobíhá (na to slouží *Import ze
STAG → 🔄 Aktualizovat …*).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from PySide6.QtCore import Qt, QTimer
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

from ..models.enums import AttachmentKind
from ..services import stag_api
from .stag_import_dialog import _SECTION_TO_KIND


@dataclass
class _Row:
    is_opposing: bool
    label: str
    adipidno: str
    db_kinds: set
    missing: list = field(default_factory=list)  # [(AttachmentKind, filename)]
    error: str = ""


def _fetch_files(adipidno: str):
    """Vrátí (seznam souborů STAG, chyba)."""
    try:
        return stag_api.list_thesis_files(adipidno), ""
    except Exception as exc:  # noqa: BLE001
        return [], str(exc)


class StagConsistencyDialog(QDialog):
    """Přehled prací, u kterých STAG nabízí soubory chybějící v DB."""

    def __init__(self, service, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self._rows: list[_Row] = []
        self._no_id: list[str] = []

        self.setWindowTitle("Kontrola konzistence se STAG")
        self.setMinimumSize(820, 600)
        self.resize(1000, 760)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        title = QLabel("🔍 Kontrola konzistence se STAG")
        title.setStyleSheet("font-size:16px;font-weight:bold;")
        outer.addWidget(title)

        intro = QLabel(
            "Porovná soubory u prací (vedených i oponovaných) se STAG a vypíše, "
            "kde STAG nabízí <b>druh dokumentu</b> (plný text / příloha / posudek), "
            "který <b>v databázi ještě nemáš</b>. Soubory dohraješ přes "
            "<i>Import ze STAG → 🔄 Aktualizovat …</i>."
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
        outer.addWidget(self.tree, stretch=1)

        row = QHBoxLayout()
        btn_close = QPushButton("Zavřít")
        btn_close.clicked.connect(self.accept)
        row.addStretch()
        row.addWidget(btn_close)
        outer.addLayout(row)

        QTimer.singleShot(0, self._scan)

    # --- sběr + dotažení -----------------------------------------------------

    def _collect(self) -> list[_Row]:
        rows: list[_Row] = []
        for t in self.service.list_theses():
            if not t.adipidno:
                student = self.service.get_student(t.student_id) if t.student_id else None
                name = student.full_name if student else "(neznámý student)"
                self._no_id.append(f"{name} — {t.title_cs or '(bez názvu)'} ({t.type.value})")
                continue
            student = self.service.get_student(t.student_id) if t.student_id else None
            name = student.full_name if student else "(neznámý student)"
            rows.append(_Row(
                is_opposing=False,
                label=f"{name} — {t.title_cs or '(bez názvu)'} ({t.type.value})",
                adipidno=t.adipidno,
                db_kinds={a.kind for a in t.attachments if a.is_current},
            ))
        for o in self.service.list_opposing_theses():
            name = f"{o.student_last_name} {o.student_first_name}".strip() or "(student)"
            label = f"{name} — {o.title_cs or '(bez názvu)'} ({o.type.value}) — oponentura"
            if not o.adipidno:
                self._no_id.append(label)
                continue
            rows.append(_Row(
                is_opposing=True, label=label, adipidno=o.adipidno,
                db_kinds={a.kind for a in o.attachments if a.is_current},
            ))
        return rows

    def _scan(self) -> None:
        rows = self._collect()
        if not rows:
            self.lbl_status.setText(
                "Žádné práce s STAG ID k ověření "
                f"({len(self._no_id)} prací nemá STAG ID)."
            )
            self._populate([])
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
                            r.missing.append((kind, sf.filename))
                done += 1
                progress.setValue(done)
                QApplication.processEvents()
                if progress.wasCanceled():
                    break
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
            progress.close()

        self._rows = rows
        self._populate(rows)

    # --- výpis ---------------------------------------------------------------

    def _populate(self, rows: list[_Row]) -> None:
        self.tree.clear()
        gray = QBrush(QColor("#888"))
        amber = QBrush(QColor("#e65100"))

        missing_rows = [r for r in rows if r.missing and not r.error]
        ok_rows = [r for r in rows if not r.missing and not r.error]
        err_rows = [r for r in rows if r.error]

        if missing_rows:
            head = QTreeWidgetItem([f"⚠ Chybí soubory ({len(missing_rows)})"])
            f = head.font(0)
            f.setBold(True)
            head.setFont(0, f)
            self.tree.addTopLevelItem(head)
            for r in sorted(missing_rows, key=lambda x: x.label.lower()):
                node = QTreeWidgetItem([r.label])
                node.setForeground(0, amber)
                head.addChild(node)
                for kind, fname in r.missing:
                    leaf = QTreeWidgetItem([f"📎 {kind.label}: {fname}"])
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

        total = len(rows)
        miss = len(missing_rows)
        self.lbl_status.setText(
            f"Ověřeno {total} prací: <b>{miss}</b> má ve STAG soubory, které "
            f"v databázi chybí. Bez STAG ID: {len(self._no_id)}."
        )
        self.lbl_status.setTextFormat(Qt.TextFormat.RichText)
