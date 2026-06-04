"""Dialog pro vytvoření nového profilu s volitelným importem dat z jiného."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ..models import Profile
from ..services import ProfileError, ProfileManager


class NewProfileDialog(QDialog):
    """Vytvoření profilu — název, cesta a volitelně import dat z existujícího profilu.

    Po úspěšném dokončení je v ``self.created`` Profile a v ``self.import_source_id``
    případně ID profilu, ze kterého se má zkopírovat data (callee provede copy
    po vytvoření, aby měl možnost ukázat progress).
    """

    def __init__(self, pm: ProfileManager, parent=None) -> None:
        super().__init__(parent)
        self.pm = pm
        self.created: Profile | None = None
        self.import_source_id: str | None = None
        self.include_documents: bool = True
        self.include_harmonograms: bool = True

        self.setWindowTitle("Nový profil")
        self.setMinimumWidth(560)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # Hlavní formulář
        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("např. „FAI UTB — osobní“")
        form.addRow("Název", self.ed_name)

        # Jméno uživatele profilu (pro STAG import auto-detect role)
        self.ed_user_name = QLineEdit()
        self.ed_user_name.setPlaceholderText(
            "např. Petr Žáček — slouží k auto-detekci role při STAG importu"
        )
        form.addRow("Tvoje jméno", self.ed_user_name)

        # Cesta + Procházet
        self.ed_path = QLineEdit()
        self.ed_path.setPlaceholderText("vyber složku, kam se uloží db.json a další")
        btn_browse = QPushButton("Procházet…")
        btn_browse.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self.ed_path, stretch=1)
        path_row.addWidget(btn_browse)
        form.addRow("Cesta ke složce", path_row)

        # Import zdroj — combobox
        self.cb_source = QComboBox()
        self.cb_source.addItem("(žádný — začít s prázdnou databází)", None)
        for p in self.pm.all_profiles():
            self.cb_source.addItem(f"📦 {p.name}", p.id)
        form.addRow("Importovat data z", self.cb_source)

        outer.addLayout(form)

        # Volby importu (zobrazí se jen pokud je vybrán zdroj)
        self.opts_label = QLabel(
            "Z vybraného profilu se zkopíruje db.json. Volitelně přibalit i:"
        )
        self.opts_label.setWordWrap(True)
        self.opts_label.setStyleSheet("color: #888; padding-left: 4px;")
        outer.addWidget(self.opts_label)

        self.chk_docs = QCheckBox("📎 Dokumenty (posudky, text práce, prezentace…)")
        self.chk_docs.setChecked(True)
        outer.addWidget(self.chk_docs)

        self.chk_harm = QCheckBox("📅 Naimportované PDF harmonogramy")
        self.chk_harm.setChecked(True)
        outer.addWidget(self.chk_harm)

        # Reaguj na změnu zdroje
        self.cb_source.currentIndexChanged.connect(self._update_options_visibility)
        self._update_options_visibility()

        # OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Vytvořit profil")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    # --- helpers --------------------------------------------------------

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Vyber složku pro data nového profilu",
            self.ed_path.text() or str(Path.home()),
        )
        if folder:
            self.ed_path.setText(folder)

    def _update_options_visibility(self) -> None:
        has_source = self.cb_source.currentData() is not None
        self.opts_label.setVisible(has_source)
        self.chk_docs.setVisible(has_source)
        self.chk_harm.setVisible(has_source)

    def _on_accept(self) -> None:
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Chybí název", "Zadej název profilu.")
            return

        path_str = self.ed_path.text().strip()
        if not path_str:
            QMessageBox.warning(self, "Chybí cesta", "Vyber složku pro data profilu.")
            return

        data_dir = Path(path_str).expanduser()
        try:
            profile = self.pm.create(name=name, data_dir=data_dir)
        except ProfileError as exc:
            QMessageBox.critical(self, "Vytvoření selhalo", str(exc))
            return

        # Propíše Tvoje jméno (volitelné — používá se v STAG importu)
        user_name = self.ed_user_name.text().strip()
        if user_name:
            try:
                self.pm.set_user_name(profile.id, user_name)
            except ProfileError:
                pass

        source_id = self.cb_source.currentData()
        if source_id:
            try:
                stats = self.pm.copy_data_into_profile(
                    source_id=source_id,
                    target_id=profile.id,
                    include_documents=self.chk_docs.isChecked(),
                    include_harmonograms=self.chk_harm.isChecked(),
                    overwrite=True,
                )
            except ProfileError as exc:
                # Profile byl vytvořen, ale import selhal — necháme ho a oznámíme.
                QMessageBox.warning(
                    self,
                    "Import nedokončen",
                    f"Profil byl vytvořen, ale kopírování dat selhalo:\n{exc}",
                )
                self.created = profile
                self.import_source_id = source_id
                self.accept()
                return
            QMessageBox.information(
                self,
                "Hotovo",
                f"Profil „{name}“ vytvořen a data zkopírována.\n\n"
                f"db.json: {stats['db']}\n"
                f"dokumenty (složek): {stats['documents']}\n"
                f"harmonogramy (souborů): {stats['harmonograms']}",
            )
        self.created = profile
        self.import_source_id = source_id
        self.accept()
