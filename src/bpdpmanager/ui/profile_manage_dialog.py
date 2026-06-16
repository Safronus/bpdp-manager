"""Dialog správy profilů — přehled, přejmenování, odebrání, otevření složky."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from ..i18n import tr
from ..models import Profile
from ..services import ProfileError, ProfileManager


class ProfileManageDialog(QDialog):
    def __init__(self, pm: ProfileManager, parent=None) -> None:
        super().__init__(parent)
        self.pm = pm
        self.setWindowTitle(tr("Správa profilů"))
        self.setMinimumSize(820, 460)

        layout = QVBoxLayout(self)

        hdr = QLabel(
            tr("Seznam profilů. Aktivní profil je zvýrazněn. "
            "Smazat profil z registry můžeš, data ve složce zůstanou (pokud explicitně neodklikneš jejich smazání).")
        )
        hdr.setWordWrap(True)
        layout.addWidget(hdr)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(
            [tr("Profil"), tr("Tvoje jméno"), tr("Cesta"), tr("Poslední otevření"), "Status"]
        )
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(self._rename)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setStretchLastSection(False)
        layout.addWidget(self.tree, stretch=1)

        row = QHBoxLayout()
        self.btn_rename = QPushButton(tr("Přejmenovat…"))
        self.btn_user_name = QPushButton(tr("👤 Tvoje jméno a tituly…"))
        self.btn_user_name.setToolTip(
            tr("Jméno uživatele profilu — pro auto-detekci role při STAG importu "
            "a podpis v posudcích")
        )
        self.btn_review_place = QPushButton(tr("📍 Místo posudku…"))
        self.btn_review_place.setToolTip(
            tr('Místo pro podpisový blok posudku (Místo, datum). Default „Zlín".')
        )
        self.btn_user_email = QPushButton(tr("✉ E-mail…"))
        self.btn_user_email.setToolTip(
            tr("E-mail uživatele (odesílatel posudků sekretářkám). SMTP server se "
            "nastavuje v 👤 → Nastavení e-mailu.")
        )
        self.btn_export = QPushButton(tr("📤 Export…"))
        self.btn_export.setToolTip(
            tr("Vyexportuje vybraný profil do přenosného ZIP balíku.")
        )
        self.btn_open_folder = QPushButton(tr("📂 Otevřít složku"))
        self.btn_remove = QPushButton(tr("Odebrat z registry…"))
        self.btn_close = QPushButton(tr("Zavřít"))
        self.btn_rename.clicked.connect(self._rename)
        self.btn_user_name.clicked.connect(self._edit_user_name)
        self.btn_review_place.clicked.connect(self._edit_review_place)
        self.btn_user_email.clicked.connect(self._edit_user_email)
        self.btn_export.clicked.connect(self._export_zip)
        self.btn_open_folder.clicked.connect(self._open_folder)
        self.btn_remove.clicked.connect(self._remove)
        self.btn_close.clicked.connect(self.accept)
        row.addWidget(self.btn_rename)
        row.addWidget(self.btn_user_name)
        row.addWidget(self.btn_review_place)
        row.addWidget(self.btn_user_email)
        row.addWidget(self.btn_export)
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
            from ..models.naming import compose_titled_name
            user_name = compose_titled_name(
                p.user_title_before, p.user_name, p.user_title_after
            ) or "—"
            item = QTreeWidgetItem([p.name, user_name, p.data_dir, last, status])
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
            QMessageBox.warning(self, tr("Přejmenování selhalo"), str(exc))
            return
        self._refresh()

    def _edit_user_name(self) -> None:
        profile = self._current()
        if profile is None:
            QMessageBox.information(
                self,
                tr("Vyber profil"),
                tr("Vyber v seznamu profil, kterému chceš nastavit jméno."),
            )
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Tvoje jméno a tituly"))
        dlg.setMinimumWidth(440)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel(
            tr("Jméno se používá k auto-detekci role při importu ze STAG.\n"
            "Tituly před/za se automaticky doplní do jména autora v posudku.")
        ))
        # Křestní + příjmení zvlášť — kvůli přesnému hledání ve STAG u dvojího
        # křestního jména i dvojího příjmení. U starého profilu (bez částí)
        # předvyplníme rozdělením celého jména (uživatel může opravit).
        from ..models.naming import split_first_surname
        first0 = profile.user_first_name
        surname0 = profile.user_surname
        if not first0 and not surname0:
            first0, surname0 = split_first_surname(profile.user_name or "")
        form = QFormLayout()
        ed_before = QLineEdit(profile.user_title_before or "")
        ed_before.setPlaceholderText(tr("např. doc. Ing."))
        ed_first = QLineEdit(first0)
        ed_first.setPlaceholderText(tr("např. Petr (i dvojí, např. Jan Petr)"))
        ed_surname = QLineEdit(surname0)
        ed_surname.setPlaceholderText(
            tr("např. Novák (i dvojí, např. Komínková Oplatková)"))
        ed_after = QLineEdit(profile.user_title_after or "")
        ed_after.setPlaceholderText(tr("např. Ph.D."))
        form.addRow(tr("Tituly před"), ed_before)
        form.addRow(tr("Křestní jméno"), ed_first)
        form.addRow(tr("Příjmení"), ed_surname)
        form.addRow(tr("Tituly za"), ed_after)
        v.addLayout(form)
        from ..models.naming import compose_titled_name
        preview = QLabel()
        preview.setStyleSheet("color:#666;")

        def _upd() -> None:
            name = f"{ed_first.text().strip()} {ed_surname.text().strip()}".strip()
            full = compose_titled_name(ed_before.text(), name, ed_after.text())
            preview.setText(f"V posudku: <b>{full or '—'}</b>")

        preview.setTextFormat(Qt.TextFormat.RichText)
        for ed in (ed_before, ed_first, ed_surname, ed_after):
            ed.textChanged.connect(lambda *_: _upd())
        _upd()
        v.addWidget(preview)
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if not dlg.exec():
            return
        try:
            self.pm.set_user_name_parts(
                profile.id, ed_first.text(), ed_surname.text())
            self.pm.set_user_titles(profile.id, ed_before.text(), ed_after.text())
        except ProfileError as exc:
            QMessageBox.warning(self, tr("Uložení selhalo"), str(exc))
            return
        self._refresh()

    def _edit_review_place(self) -> None:
        profile = self._current()
        if profile is None:
            QMessageBox.information(
                self,
                tr("Vyber profil"),
                tr("Vyber v seznamu profil, kterému chceš nastavit místo posudku."),
            )
            return
        new_place, ok = QInputDialog.getText(
            self,
            "Místo posudku",
            "Místo pro podpisový blok posudku (Místo, datum):",
            text=profile.review_place or "Zlín",
        )
        if not ok:
            return
        try:
            self.pm.set_review_place(profile.id, new_place)
        except ProfileError as exc:
            QMessageBox.warning(self, tr("Uložení selhalo"), str(exc))
            return
        self._refresh()

    def _edit_user_email(self) -> None:
        profile = self._current()
        if profile is None:
            QMessageBox.information(
                self,
                tr("Vyber profil"),
                tr("Vyber v seznamu profil, kterému chceš nastavit e-mail."),
            )
            return
        new_email, ok = QInputDialog.getText(
            self,
            "E-mail uživatele",
            "E-mail odesílatele posudků (např. prijmeni@utb.cz):",
            text=profile.user_email or "",
        )
        if not ok:
            return
        try:
            self.pm.set_user_email(profile.id, new_email)
        except ProfileError as exc:
            QMessageBox.warning(self, tr("Uložení selhalo"), str(exc))
            return
        self._refresh()

    def _export_zip(self) -> None:
        profile = self._current()
        if profile is None:
            QMessageBox.information(
                self, tr("Vyber profil"), tr("Vyber v seznamu profil pro export.")
            )
            return
        # Lazy import (kruhový import s main_window)
        from .profile_export_dialog import ExportProfileDialog

        dlg = ExportProfileDialog(self.pm, profile, self)
        dlg.exec()

    def _open_folder(self) -> None:
        profile = self._current()
        if profile is None:
            return
        path = Path(profile.data_dir)
        if not path.exists():
            QMessageBox.warning(
                self, tr("Složka neexistuje"), f"Složka {path} už neexistuje."
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
                tr("Aktivní profil"),
                tr("Nelze odebrat profil, který je právě aktivní. "
                "Přepni se nejprve jinam."),
            )
            return

        # Dotaz: jen z registry, nebo i data?
        msg = QMessageBox(self)
        msg.setWindowTitle(tr("Odebrat profil"))
        msg.setText(f"Odebrat profil „{profile.name}“?")
        msg.setInformativeText(
            f"Cesta: {profile.data_dir}\n\n"
            "Co se má stát s daty?"
        )
        btn_keep = msg.addButton(
            tr("Odebrat z registry (data zachovat)"), QMessageBox.ButtonRole.AcceptRole
        )
        btn_delete = msg.addButton(
            tr("⚠ Smazat i složku s daty"), QMessageBox.ButtonRole.DestructiveRole
        )
        msg.addButton(QMessageBox.StandardButton.Cancel)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_keep:
            self.pm.remove(profile.id, delete_files=False)
        elif clicked == btn_delete:
            confirm = QMessageBox.question(
                self,
                tr("Smazat data"),
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
