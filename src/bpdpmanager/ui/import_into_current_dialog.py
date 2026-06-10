"""Dialog: Importovat data z jiného profilu DO aktuálního profilu (přepíše).

Destruktivní akce — silné varování + automatická záloha aktuálního stavu
před přepisem (vznikne ``before-import`` v ``backups/``).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)

from ..i18n import tr
from ..services import ProfileManager


class ImportIntoCurrentDialog(QDialog):
    """Import dat z jiného profilu do **aktuálně otevřeného** profilu.

    Po úspěšném dokončení (``self.accepted``) má volající k dispozici:
    - ``self.source_id``       — ID zdrojového profilu
    - ``self.include_documents``
    - ``self.include_harmonograms``
    - ``self.include_db``      — vždy True (přepsání db.json je jádro akce)
    """

    def __init__(self, pm: ProfileManager, parent=None) -> None:
        super().__init__(parent)
        self.pm = pm
        self.source_id: str | None = None
        self.include_documents: bool = True
        self.include_harmonograms: bool = True
        self.include_db: bool = True

        active = pm.active
        if active is None:
            # Pro jistotu — UI by neměl tento dialog otevřít bez aktivního profilu
            self.setWindowTitle(tr("Žádný aktivní profil"))
            QVBoxLayout(self).addWidget(QLabel(tr("Není otevřený žádný profil.")))
            return

        self.setWindowTitle(tr("Import dat do aktuálního profilu"))
        self.setMinimumWidth(620)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # Hlavička s cílem
        title = QLabel(tr("📥 Import dat do aktuálního profilu"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        outer.addWidget(title)

        target_lbl = QLabel(
            f'Cíl (přepíše se): <b>{active.name}</b><br>'
            f'<span style="color:#888;">{active.data_dir}</span>'
        )
        target_lbl.setTextFormat(Qt.TextFormat.RichText)
        target_lbl.setWordWrap(True)
        outer.addWidget(target_lbl)

        # Zdroj
        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self.cb_source = QComboBox()
        other_profiles = [p for p in self.pm.all_profiles() if p.id != active.id]
        if not other_profiles:
            self.cb_source.addItem(tr("(žádný jiný profil neexistuje)"), None)
            self.cb_source.setEnabled(False)
        else:
            for p in other_profiles:
                self.cb_source.addItem(f"📦 {p.name}", p.id)
        form.addRow(tr("Zdroj (odkud importovat)"), self.cb_source)
        outer.addLayout(form)

        # Co kopírovat
        outer.addWidget(QLabel(tr("Co naimportovat:")))
        self.chk_db = QCheckBox(tr("🗂  db.json (hlavní databáze) — PŘEPÍŠE aktuální obsah"))
        self.chk_db.setChecked(True)
        self.chk_db.setEnabled(False)  # zatím povinné — jádro akce
        outer.addWidget(self.chk_db)
        self.chk_docs = QCheckBox(tr("📎 Dokumenty (posudky, text práce, prezentace…)"))
        self.chk_docs.setChecked(True)
        outer.addWidget(self.chk_docs)
        self.chk_harm = QCheckBox(tr("📅 Naimportované PDF harmonogramy"))
        self.chk_harm.setChecked(True)
        outer.addWidget(self.chk_harm)

        # Varovný panel
        warn = QLabel(
            tr("<b>⚠ Pozor:</b> Aktuální data v cílovém profilu budou přepsána "
            "(db.json) nebo doplněna (dokumenty / harmonogramy). "
            "<b>Před přepsáním se automaticky vytvoří záloha aktuálního stavu</b> "
            'se značkou <code>before-import</code> ve složce <code>backups/</code> '
            "— takže se dá vrátit přes <i>👤 → 💾 Zálohy</i>.")
        )
        warn.setTextFormat(Qt.TextFormat.RichText)
        warn.setWordWrap(True)
        warn.setStyleSheet(
            "QLabel { background-color: #fff3e0; color: #5d4037; "
            "padding: 10px 14px; border-left: 4px solid #ef6c00; "
            "border-radius: 4px; }"
        )
        outer.addWidget(warn)

        # Tlačítka
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText(tr("🔄 Importovat (přepsat aktuální data)"))
        f: QFont = ok_btn.font()
        f.setBold(True)
        ok_btn.setFont(f)
        if not other_profiles:
            ok_btn.setEnabled(False)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _on_accept(self) -> None:
        sid = self.cb_source.currentData()
        if sid is None:
            self.reject()
            return
        self.source_id = sid
        self.include_db = self.chk_db.isChecked()
        self.include_documents = self.chk_docs.isChecked()
        self.include_harmonograms = self.chk_harm.isChecked()
        self.accept()
