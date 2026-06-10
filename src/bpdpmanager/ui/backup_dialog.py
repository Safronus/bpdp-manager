"""Dialog správce záloh — seznam, obnova, mazání."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from ..i18n import tr
from ..services import BackupInfo, BackupManager


def _format_size(num_bytes: int) -> str:
    for unit in ("B", "kB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.0f} {unit}" if unit == "B" else f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024  # type: ignore[assignment]
    return f"{num_bytes:.1f} TB"


class BackupBrowserDialog(QDialog):
    """Seznam 10 nejnovějších záloh, obnova s před-restore zálohou."""

    restored = Signal()

    def __init__(self, backup_manager: BackupManager, db_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.backup_manager = backup_manager
        self.db_path = db_path
        self.setWindowTitle(tr("Zálohy databáze"))
        self.setMinimumSize(720, 460)

        layout = QVBoxLayout(self)

        info = QLabel(
            f"Aplikace si drží posledních {BackupManager.MAX_BACKUPS} záloh. "
            "Při obnově se před přepsáním vytvoří záloha aktuálního stavu "
            "se značkou „before-restore“, takže se dá vrátit i to."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels([tr("Čas vytvoření"), tr("Označení"), "Velikost"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(False)
        self.tree.itemDoubleClicked.connect(self._restore)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setStretchLastSection(False)
        layout.addWidget(self.tree, stretch=1)

        row = QHBoxLayout()
        self.btn_backup_now = QPushButton(tr("💾 Zálohovat teď"))
        self.btn_backup_now.setToolTip(tr("Vytvoří ruční zálohu aktuálního stavu databáze."))
        bf = self.btn_backup_now.font()
        bf.setBold(True)
        self.btn_backup_now.setFont(bf)
        self.btn_backup_now.clicked.connect(self._backup_now)
        self.btn_restore = QPushButton(tr("🔄 Obnovit vybranou zálohu"))
        self.btn_restore.clicked.connect(self._restore)
        self.btn_open_folder = QPushButton(tr("📂 Otevřít složku záloh"))
        self.btn_open_folder.clicked.connect(self._open_folder)
        self.btn_delete = QPushButton("Smazat")
        self.btn_delete.clicked.connect(self._delete)
        self.btn_close = QPushButton(tr("Zavřít"))
        self.btn_close.clicked.connect(self.accept)
        row.addWidget(self.btn_backup_now)
        row.addWidget(self.btn_restore)
        row.addWidget(self.btn_open_folder)
        row.addWidget(self.btn_delete)
        row.addStretch()
        row.addWidget(self.btn_close)
        layout.addLayout(row)

        self._refresh()

    # --- načítání -------------------------------------------------------

    def _refresh(self) -> None:
        self.tree.clear()
        backups = self.backup_manager.list_backups()
        if not backups:
            placeholder = QTreeWidgetItem(["(žádné zálohy zatím)", "", ""])
            placeholder.setFirstColumnSpanned(True)
            self.tree.addTopLevelItem(placeholder)
            return
        for b in backups:
            ts = b.timestamp.strftime("%d.%m.%Y %H:%M:%S")
            item = QTreeWidgetItem(
                [
                    ts,
                    b.suffix or "—",
                    _format_size(b.size_bytes),
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, b)
            self.tree.addTopLevelItem(item)

    def _current(self) -> BackupInfo | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        return data if isinstance(data, BackupInfo) else None

    # --- akce -----------------------------------------------------------

    def _backup_now(self) -> None:
        """Vytvoří ruční zálohu aktuálního stavu databáze."""
        if not self.db_path.exists():
            QMessageBox.warning(self, tr("Záloha"), tr("Databáze zatím neexistuje."))
            return
        try:
            info = self.backup_manager.create_backup(
                self.db_path, suffix="manual", dedupe=False
            )
        except OSError as exc:
            QMessageBox.critical(self, tr("Záloha selhala"), str(exc))
            return
        self._refresh()
        if info is not None:
            QMessageBox.information(
                self, tr("Záloha vytvořena"),
                f"Vytvořena ruční záloha:\n{info.path.name}",
            )

    def _restore(self) -> None:
        backup = self._current()
        if backup is None:
            return
        ts = backup.timestamp.strftime("%d.%m.%Y %H:%M:%S")
        confirm = QMessageBox.question(
            self,
            tr("Obnovit zálohu"),
            f"Obnovit zálohu z {ts}?\n\n"
            "Aktuální stav db.json se před přepsáním uloží jako "
            "„before-restore“ záloha, takže se dá vrátit i tato akce.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self.backup_manager.restore_backup(backup.filename, self.db_path)
        except (OSError, FileNotFoundError) as exc:
            QMessageBox.critical(self, tr("Obnova selhala"), str(exc))
            return
        self.restored.emit()
        QMessageBox.information(
            self,
            tr("Hotovo"),
            tr("Záloha byla obnovena. Aplikace nyní pracuje nad obnovenými daty."),
        )
        self._refresh()

    def _open_folder(self) -> None:
        path = self.backup_manager.backups_dir
        if not path.exists():
            QMessageBox.information(self, tr("Otevřít složku"), tr("Složka záloh ještě neexistuje."))
            return
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", str(path)], check=False)
        elif sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]

    def _delete(self) -> None:
        backup = self._current()
        if backup is None:
            return
        ts = backup.timestamp.strftime("%d.%m.%Y %H:%M:%S")
        confirm = QMessageBox.question(
            self,
            tr("Smazat zálohu"),
            f"Smazat zálohu z {ts}? Tuto akci nelze vrátit.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.backup_manager.delete_backup(backup.filename)
        self._refresh()
