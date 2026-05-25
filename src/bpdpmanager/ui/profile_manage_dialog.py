"""Dialog správy profilů — přehled, přejmenování, odebrání, otevření složky."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from ..models import Profile
from ..services import ProfileError, ProfileManager


class ProfileManageDialog(QDialog):
    def __init__(self, pm: ProfileManager, parent=None) -> None:
        super().__init__(parent)
        self.pm = pm
        self.setWindowTitle("Správa profilů")
        self.setMinimumSize(820, 460)

        layout = QVBoxLayout(self)

        hdr = QLabel(
            "Seznam profilů. Aktivní profil je zvýrazněn. "
            "Smazat profil z registry můžeš, data ve složce zůstanou (pokud explicitně neodklikneš jejich smazání)."
        )
        hdr.setWordWrap(True)
        layout.addWidget(hdr)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Profil", "Cesta", "Poslední otevření", "Status"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(self._rename)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setStretchLastSection(False)
        layout.addWidget(self.tree, stretch=1)

        row = QHBoxLayout()
        self.btn_rename = QPushButton("Přejmenovat…")
        self.btn_open_folder = QPushButton("📂 Otevřít složku")
        self.btn_remove = QPushButton("Odebrat z registry…")
        self.btn_close = QPushButton("Zavřít")
        self.btn_rename.clicked.connect(self._rename)
        self.btn_open_folder.clicked.connect(self._open_folder)
        self.btn_remove.clicked.connect(self._remove)
        self.btn_close.clicked.connect(self.accept)
        row.addWidget(self.btn_rename)
        row.addWidget(self.btn_open_folder)
        row.addWidget(self.btn_remove)
        row.addStretch()
        row.addWidget(self.btn_close)
        layout.addLayout(row)

        self._refresh()

    # --- načítání -------------------------------------------------------

    def _refresh(self) -> None:
        self.tree.clear()
        active_id = self.pm.active.id if self.pm.active else None
        for p in self.pm.all_profiles():
            last = (
                p.last_opened_at.strftime("%d.%m.%Y %H:%M") if p.last_opened_at else "—"
            )
            is_active = p.id == active_id
            status = "● aktivní" if is_active else ""
            data_dir_exists = Path(p.data_dir).exists()
            if not data_dir_exists:
                status = (status + "  ·  ⚠ složka neexistuje").strip()
            item = QTreeWidgetItem([p.name, p.data_dir, last, status])
            item.setData(0, Qt.ItemDataRole.UserRole, p)
            if is_active:
                f = item.font(0)
                f.setBold(True)
                item.setFont(0, f)
            self.tree.addTopLevelItem(item)

    def _current(self) -> Profile | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        return data if isinstance(data, Profile) else None

    # --- akce -----------------------------------------------------------

    def _rename(self) -> None:
        profile = self._current()
        if profile is None:
            return
        new_name, ok = QInputDialog.getText(
            self,
            "Přejmenovat profil",
            "Nový název:",
            text=profile.name,
        )
        if not ok or not new_name.strip():
            return
        try:
            self.pm.rename(profile.id, new_name.strip())
        except ProfileError as exc:
            QMessageBox.warning(self, "Přejmenování selhalo", str(exc))
            return
        self._refresh()

    def _open_folder(self) -> None:
        profile = self._current()
        if profile is None:
            return
        path = Path(profile.data_dir)
        if not path.exists():
            QMessageBox.warning(
                self, "Složka neexistuje", f"Složka {path} už neexistuje."
            )
            return
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", str(path)], check=False)
        elif sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]

    def _remove(self) -> None:
        profile = self._current()
        if profile is None:
            return
        if self.pm.active and self.pm.active.id == profile.id:
            QMessageBox.warning(
                self,
                "Aktivní profil",
                "Nelze odebrat profil, který je právě aktivní. "
                "Přepni se nejprve jinam.",
            )
            return

        # Dotaz: jen z registry, nebo i data?
        msg = QMessageBox(self)
        msg.setWindowTitle("Odebrat profil")
        msg.setText(f"Odebrat profil „{profile.name}“?")
        msg.setInformativeText(
            f"Cesta: {profile.data_dir}\n\n"
            "Co se má stát s daty?"
        )
        btn_keep = msg.addButton(
            "Odebrat z registry (data zachovat)", QMessageBox.ButtonRole.AcceptRole
        )
        btn_delete = msg.addButton(
            "⚠ Smazat i složku s daty", QMessageBox.ButtonRole.DestructiveRole
        )
        msg.addButton(QMessageBox.StandardButton.Cancel)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_keep:
            self.pm.remove(profile.id, delete_files=False)
        elif clicked == btn_delete:
            confirm = QMessageBox.question(
                self,
                "Smazat data",
                f"Opravdu nenávratně smazat složku\n{profile.data_dir}\n"
                "se VŠEMI daty?",
            )
            if confirm == QMessageBox.StandardButton.Yes:
                self.pm.remove(profile.id, delete_files=True)
            else:
                return
        else:
            return
        self._refresh()
