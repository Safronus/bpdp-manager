from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config import harmonograms_dir
from ..models import AcademicYearInfo, KeyDate, KeyDateCategory
from ..services import ThesisService


class HarmonogramTab(QWidget):
    """Záložka s časovým plánem (harmonogramem) pro akademický rok."""

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self._build_ui()
        self._refresh_year_combo()

    # --- konstrukce ----------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # horní lišta: výběr roku + akce
        top = QHBoxLayout()
        top.addWidget(QLabel("Akademický rok:"))
        self.cb_year = QComboBox()
        self.cb_year.currentTextChanged.connect(self._on_year_change)
        top.addWidget(self.cb_year)

        self.btn_add_year = QPushButton("+ Přidat rok")
        self.btn_add_year.clicked.connect(self._add_year)
        top.addWidget(self.btn_add_year)

        top.addSpacing(20)
        self.btn_import = QPushButton("📄 Importovat PDF…")
        self.btn_import.clicked.connect(self._import_pdf)
        top.addWidget(self.btn_import)

        self.btn_open_pdf = QPushButton("Otevřít PDF")
        self.btn_open_pdf.clicked.connect(self._open_pdf)
        top.addWidget(self.btn_open_pdf)

        top.addStretch()

        self.btn_add_kd = QPushButton("+ Termín")
        self.btn_add_kd.clicked.connect(self._add_keydate)
        top.addWidget(self.btn_add_kd)

        self.btn_edit_kd = QPushButton("Upravit")
        self.btn_edit_kd.clicked.connect(self._edit_keydate)
        top.addWidget(self.btn_edit_kd)

        self.btn_delete_kd = QPushButton("Smazat")
        self.btn_delete_kd.clicked.connect(self._delete_keydate)
        top.addWidget(self.btn_delete_kd)

        layout.addLayout(top)

        # filtr
        filter_row = QHBoxLayout()
        self.chk_only_important = QCheckBox("Jen důležité")
        self.chk_only_important.toggled.connect(self._refresh_table)
        filter_row.addWidget(self.chk_only_important)

        self.chk_hide_past = QCheckBox("Skrýt už uplynulé")
        self.chk_hide_past.toggled.connect(self._refresh_table)
        filter_row.addWidget(self.chk_hide_past)

        filter_row.addStretch()

        self.lbl_pdf_info = QLabel("")
        self.lbl_pdf_info.setStyleSheet("color: #888;")
        filter_row.addWidget(self.lbl_pdf_info)

        layout.addLayout(filter_row)

        # přehled nadcházejících (60 dní) — žlutý info panel.
        # Explicitní tmavý text, aby byl čitelný i v dark theme
        # (jinak by se zdědil světlý palette(text) na světle žlutém pozadí).
        self.upcoming_label = QLabel("")
        self.upcoming_label.setStyleSheet(
            "QLabel { background: #fff9c4; color: #5d4037; "
            "padding: 8px; border-radius: 6px; }"
        )
        self.upcoming_label.setWordWrap(True)
        layout.addWidget(self.upcoming_label)

        # tabulka
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Datum", "Kategorie", "Popis", "Zdroj"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.doubleClicked.connect(self._edit_keydate)
        layout.addWidget(self.table)

    # --- data ----------------------------------------------------------------

    def _refresh_year_combo(self) -> None:
        previously = self.cb_year.currentText()
        self.cb_year.blockSignals(True)
        self.cb_year.clear()

        labels = {info.label for info in self.service.list_year_infos()}
        labels.add(ThesisService.current_academic_year())
        labels.add(ThesisService.next_academic_year())

        for label in sorted(labels, reverse=True):
            self.cb_year.addItem(label)

        if previously:
            idx = self.cb_year.findText(previously)
            if idx >= 0:
                self.cb_year.setCurrentIndex(idx)
        self.cb_year.blockSignals(False)
        self._refresh_table()

    def current_info(self) -> AcademicYearInfo | None:
        label = self.cb_year.currentText()
        if not label:
            return None
        return self.service.get_or_create_year_info(label)

    def _refresh_table(self) -> None:
        info = self.current_info()
        self.table.setRowCount(0)
        if info is None:
            self.lbl_pdf_info.setText("")
            self.upcoming_label.setText("Žádný vybraný rok.")
            return

        # PDF info
        if info.pdf_filename:
            self.lbl_pdf_info.setText(f"PDF: {info.pdf_filename}")
        else:
            self.lbl_pdf_info.setText("(žádné PDF naimportované)")

        # filtrování
        today = date.today()
        items = list(enumerate(info.key_dates))
        if self.chk_only_important.isChecked():
            items = [(i, kd) for i, kd in items if kd.important]
        if self.chk_hide_past.isChecked():
            items = [
                (i, kd)
                for i, kd in items
                if (kd.date_end or kd.date_start or date.max) >= today
            ]

        items.sort(key=lambda x: x[1].sort_key())

        # nadcházející ⭐ termíny
        upcoming = [kd for kd in info.upcoming(today, 60) if kd.important]
        if upcoming:
            lines = ["📌 <b>Důležité v následujících 60 dnech:</b>"]
            for kd in upcoming:
                lines.append(f"&nbsp;&nbsp;• {kd.display_date()} — {kd.description}")
            self.upcoming_label.setText("<br>".join(lines))
            self.upcoming_label.setVisible(True)
        else:
            self.upcoming_label.setVisible(False)

        # vyplň tabulku
        for idx, (orig_index, kd) in enumerate(items):
            self.table.insertRow(idx)

            date_item = QTableWidgetItem(kd.display_date())
            if kd.important:
                font: QFont = date_item.font()
                font.setBold(True)
                date_item.setFont(font)
            date_item.setData(Qt.ItemDataRole.UserRole, orig_index)
            self.table.setItem(idx, 0, date_item)

            cat_item = QTableWidgetItem(kd.category.label)
            cat_item.setForeground(QBrush(QColor(kd.category.color)))
            cat_font: QFont = cat_item.font()
            cat_font.setBold(True)
            cat_item.setFont(cat_font)
            self.table.setItem(idx, 1, cat_item)

            desc_text = ("⭐ " if kd.important else "") + kd.description
            self.table.setItem(idx, 2, QTableWidgetItem(desc_text))

            src_label = "import" if kd.source == "imported" else "ruční"
            self.table.setItem(idx, 3, QTableWidgetItem(src_label))

    def _on_year_change(self, _label: str) -> None:
        self._refresh_table()

    # --- akce ----------------------------------------------------------------

    def _add_year(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        text, ok = QInputDialog.getText(
            self,
            "Nový akademický rok",
            "Zadej rok ve tvaru YYYY/YYYY:",
            text=ThesisService.next_academic_year(),
        )
        if not ok or not text.strip():
            return
        try:
            self.service.get_or_create_year_info(text.strip())
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Neplatný rok", str(exc))
            return
        self._refresh_year_combo()
        idx = self.cb_year.findText(text.strip())
        if idx >= 0:
            self.cb_year.setCurrentIndex(idx)

    def _import_pdf(self) -> None:
        label = self.cb_year.currentText()
        if not label:
            QMessageBox.information(self, "Import PDF", "Nejdřív vyber akademický rok.")
            return
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            f"Vyber PDF harmonogramu pro {label}",
            str(Path.home()),
            "PDF soubory (*.pdf)",
        )
        if not path_str:
            return
        try:
            info = self.service.import_harmonogram_pdf(label, Path(path_str))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Chyba importu", f"Nepodařilo se importovat PDF:\n{exc}")
            return
        QMessageBox.information(
            self,
            "Import dokončen",
            f"Naimportováno {len(info.key_dates)} klíčových termínů.",
        )
        self._refresh_table()

    def _open_pdf(self) -> None:
        info = self.current_info()
        if info is None or not info.pdf_filename:
            QMessageBox.information(self, "Otevřít PDF", "Pro tento rok není naimportované žádné PDF.")
            return
        target = harmonograms_dir() / info.pdf_filename
        if not target.exists():
            QMessageBox.warning(self, "Otevřít PDF", f"PDF neexistuje: {target}")
            return
        # otevři PDF v defaultní aplikaci OS
        import os
        import subprocess
        import sys

        if sys.platform == "darwin":
            subprocess.run(["open", str(target)], check=False)
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", str(target)], check=False)
        elif sys.platform == "win32":
            os.startfile(str(target))  # type: ignore[attr-defined]

    def _selected_index(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _add_keydate(self) -> None:
        info = self.current_info()
        if info is None:
            return
        dlg = KeyDateDialog(self)
        if dlg.exec():
            self.service.add_key_date(info.label, dlg.value)
            self._refresh_table()

    def _edit_keydate(self) -> None:
        info = self.current_info()
        if info is None:
            return
        idx = self._selected_index()
        if idx is None:
            return
        existing = info.key_dates[idx]
        dlg = KeyDateDialog(self, existing)
        if dlg.exec():
            self.service.update_key_date(info.label, idx, dlg.value)
            self._refresh_table()

    def _delete_keydate(self) -> None:
        info = self.current_info()
        if info is None:
            return
        idx = self._selected_index()
        if idx is None:
            return
        kd = info.key_dates[idx]
        confirm = QMessageBox.question(
            self,
            "Smazat termín",
            f"Smazat „{kd.description}“?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.service.remove_key_date(info.label, idx)
            self._refresh_table()


class KeyDateDialog(QDialog):
    """Dialog pro přidání/úpravu klíčového termínu."""

    def __init__(self, parent, existing: KeyDate | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Termín v harmonogramu")
        self.setMinimumWidth(480)
        self._existing = existing

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.chk_has_date = QCheckBox("Konkrétní datum")
        self.chk_has_date.setChecked(True)
        form.addRow(self.chk_has_date)

        self.de_start = QDateEdit()
        self.de_start.setCalendarPopup(True)
        self.de_start.setDisplayFormat("dd.MM.yyyy")
        self.de_start.setDate(existing.date_start if existing and existing.date_start else date.today())
        form.addRow("Od", self.de_start)

        self.chk_range = QCheckBox("Interval (do)")
        form.addRow(self.chk_range)

        self.de_end = QDateEdit()
        self.de_end.setCalendarPopup(True)
        self.de_end.setDisplayFormat("dd.MM.yyyy")
        if existing and existing.date_end:
            self.de_end.setDate(existing.date_end)
            self.chk_range.setChecked(True)
        else:
            self.de_end.setDate(date.today())
        form.addRow("Do", self.de_end)

        self.ed_fuzzy = QLineEdit(existing.fuzzy_label if existing and existing.fuzzy_label else "")
        self.ed_fuzzy.setPlaceholderText("např. květen-červen 2027")
        form.addRow("Volný popis data", self.ed_fuzzy)

        self.ed_desc = QLineEdit(existing.description if existing else "")
        form.addRow("Popis", self.ed_desc)

        self.cb_cat = QComboBox()
        for c in KeyDateCategory:
            self.cb_cat.addItem(c.label, c.value)
        if existing:
            idx = self.cb_cat.findData(existing.category.value)
            if idx >= 0:
                self.cb_cat.setCurrentIndex(idx)
        form.addRow("Kategorie", self.cb_cat)

        self.chk_important = QCheckBox("Označit jako důležitý termín")
        self.chk_important.setChecked(existing.important if existing else False)
        form.addRow(self.chk_important)

        layout.addLayout(form)

        if existing is None or existing.fuzzy_label:
            self.chk_has_date.setChecked(existing is None)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def value(self) -> KeyDate:
        has_date = self.chk_has_date.isChecked()
        return KeyDate(
            date_start=self.de_start.date().toPython() if has_date else None,
            date_end=self.de_end.date().toPython() if has_date and self.chk_range.isChecked() else None,
            fuzzy_label=(self.ed_fuzzy.text().strip() or None) if not has_date else None,
            description=self.ed_desc.text().strip(),
            category=KeyDateCategory(self.cb_cat.currentData()),
            important=self.chk_important.isChecked(),
            source=self._existing.source if self._existing else "manual",
        )
