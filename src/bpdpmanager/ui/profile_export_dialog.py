"""Dialogy pro export profilu do ZIPu a import ze ZIPu.

Workflow exportu:
  1. ``ExportProfileDialog`` — vyber, co zahrnout (default vše kromě
     rotujících 10× zálohy) + cesta cílového ZIPu. Ukáže preview velikosti.
  2. Po potvrzení zapíše ZIP a ukáže summary s tlačítkem „Otevřít složku".

Workflow importu:
  1. ``ImportProfileDialog`` — vyber ZIP, ukáže manifest preview (jméno
     profilu, app version, počty souborů, ...).
  2. Uživatel zvolí název nového profilu + cílovou složku.
  3. Po potvrzení rozbalí + zaregistruje profil. ``self.created`` obsahuje
     vytvořený ``Profile``, ``self.target_data_dir`` cestu k datům.
"""

from __future__ import annotations

import os
import subprocess
import sys
from html import escape
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextBrowser,
    QVBoxLayout,
)

from ..models import Profile
from ..services import ProfileError, ProfileManager
from ..services.profile_export import (
    EXPORT_FORMAT_VERSION,
    ExportOptions,
    compute_export_preview,
    read_zip_manifest,
)


def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} kB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    return f"{n / (1024 * 1024 * 1024):.2f} GB"


def _open_in_filemanager(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", "-R", str(path)], check=False)
    elif sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", str(path.parent)], check=False)
    elif sys.platform == "win32":
        try:
            subprocess.run(["explorer", "/select,", str(path)], check=False)
        except OSError:
            pass


# ── Export ─────────────────────────────────────────────────────────────────


class ExportProfileDialog(QDialog):
    """Dialog pro export aktuálního profilu jako ZIP."""

    def __init__(
        self,
        pm: ProfileManager,
        profile: Profile,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.pm = pm
        self.profile = profile
        self.exported_zip: Path | None = None

        self.setWindowTitle(f"Exportovat profil — {profile.name}")
        self.setMinimumSize(620, 520)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        header = QLabel("📤 Export profilu do ZIP balíku")
        header.setStyleSheet("font-size:15px;font-weight:bold;")
        outer.addWidget(header)

        desc = QLabel(
            f"Vyexportuje profil <b>{escape(profile.name)}</b> jako přenosný "
            f"ZIP soubor. Na druhém zařízení ho otevřeš přes "
            f"<i>👤 Importovat profil ze ZIPu…</i>."
        )
        desc.setWordWrap(True)
        desc.setTextFormat(Qt.TextFormat.RichText)
        outer.addWidget(desc)

        # ── Co zahrnout ─────────────────────────────────────────────────
        form = QFormLayout()
        self.chk_docs = QCheckBox("📎 Dokumenty (přílohy k pracem)")
        self.chk_docs.setChecked(True)
        self.chk_harm = QCheckBox("📅 Naimportované PDF harmonogramy")
        self.chk_harm.setChecked(True)
        self.chk_templates = QCheckBox("📝 Šablony posudků (XLSX knihovna)")
        self.chk_templates.setChecked(True)
        self.chk_bak = QCheckBox("💾 Krátkodobá záloha db.json.bak")
        self.chk_bak.setChecked(True)
        self.chk_backups = QCheckBox(
            "🔄 Rotující 10× zálohy (typicky netřeba — pojistka)"
        )
        self.chk_backups.setChecked(False)

        for w in (self.chk_docs, self.chk_harm, self.chk_templates, self.chk_bak, self.chk_backups):
            w.toggled.connect(self._refresh_preview)
            outer.addWidget(w)

        # ── Cesta cílového ZIPu ─────────────────────────────────────────
        path_row = QHBoxLayout()
        self.ed_path = QLineEdit()
        self.ed_path.setPlaceholderText("cesta k cílovému .zip souboru")
        self._set_default_target_path()
        btn_browse = QPushButton("Procházet…")
        btn_browse.clicked.connect(self._browse)
        path_row.addWidget(self.ed_path, stretch=1)
        path_row.addWidget(btn_browse)
        outer.addLayout(path_row)

        # ── Preview velikosti ───────────────────────────────────────────
        self.lbl_preview = QLabel()
        self.lbl_preview.setTextFormat(Qt.TextFormat.RichText)
        # Theme-aware pozadí — Qt palette respektuje system dark/light mode.
        # ``palette(base)`` je editovatelné pozadí (světlé na light, tmavé
        # na dark), ``palette(text)`` je hlavní text. Border z ``palette(mid)``.
        self.lbl_preview.setStyleSheet(
            "QLabel {"
            " background-color: palette(base);"
            " color: palette(text);"
            " border: 1px solid palette(mid);"
            " padding: 8px;"
            " border-radius: 3px;"
            "}"
        )
        outer.addWidget(self.lbl_preview)
        self._refresh_preview()

        # ── Tlačítka ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Zavřít")
        btn_cancel.clicked.connect(self.reject)
        self.btn_export = QPushButton("📤 Exportovat")
        self.btn_export.setDefault(True)
        bf = self.btn_export.font()
        bf.setBold(True)
        self.btn_export.setFont(bf)
        self.btn_export.clicked.connect(self._do_export)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_export)
        outer.addLayout(btn_row)

    # ── helpers ─────────────────────────────────────────────────────────

    def _set_default_target_path(self) -> None:
        """Default cesta: ~/Downloads/{název}_{datum}.zip."""
        from datetime import date

        downloads = Path.home() / "Downloads"
        if not downloads.is_dir():
            downloads = Path.home()
        # Filename-safe varianta jména profilu
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in self.profile.name)
        target = downloads / f"{safe}_{date.today().isoformat()}.zip"
        self.ed_path.setText(str(target))

    def _browse(self) -> None:
        current = self.ed_path.text().strip() or str(Path.home() / "Downloads")
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Kam uložit ZIP exportu",
            current,
            "ZIP soubory (*.zip);;Všechny soubory (*.*)",
        )
        if target:
            if not target.lower().endswith(".zip"):
                target += ".zip"
            self.ed_path.setText(target)

    def _current_opts(self) -> ExportOptions:
        return ExportOptions(
            include_documents=self.chk_docs.isChecked(),
            include_harmonograms=self.chk_harm.isChecked(),
            include_db_bak=self.chk_bak.isChecked(),
            include_backups=self.chk_backups.isChecked(),
            include_templates=self.chk_templates.isChecked(),
        )

    def _refresh_preview(self) -> None:
        opts = self._current_opts()
        try:
            prev = compute_export_preview(Path(self.profile.data_dir), opts)
        except Exception as exc:  # noqa: BLE001
            self.lbl_preview.setText(f"<i>Náhled nelze spočítat: {escape(str(exc))}</i>")
            return
        rows = [
            f"<tr><td>📄 db.json:</td><td>{_fmt_bytes(prev.db_json_size)}</td></tr>",
        ]
        if opts.include_db_bak:
            rows.append(
                f"<tr><td>💾 db.json.bak:</td>"
                f"<td>{_fmt_bytes(prev.db_bak_size)}</td></tr>"
            )
        if opts.include_documents:
            rows.append(
                f"<tr><td>📎 dokumenty:</td>"
                f"<td>{prev.documents_count} souborů · "
                f"{_fmt_bytes(prev.documents_bytes)}</td></tr>"
            )
        if opts.include_harmonograms:
            rows.append(
                f"<tr><td>📅 harmonogramy:</td>"
                f"<td>{prev.harmonograms_count} souborů · "
                f"{_fmt_bytes(prev.harmonograms_bytes)}</td></tr>"
            )
        if opts.include_templates:
            rows.append(
                f"<tr><td>📝 šablony posudků:</td>"
                f"<td>{prev.templates_count} souborů · "
                f"{_fmt_bytes(prev.templates_bytes)}</td></tr>"
            )
        if opts.include_backups:
            rows.append(
                f"<tr><td>🔄 zálohy:</td>"
                f"<td>{prev.backups_count} souborů · "
                f"{_fmt_bytes(prev.backups_bytes)}</td></tr>"
            )
        html = (
            "<style>td { padding: 2px 12px 2px 0; }</style>"
            f"<table>{''.join(rows)}</table>"
            f"<p style='margin-top:6px;'><b>Celkem: {_fmt_bytes(prev.total_bytes)}</b>"
            f" <span style='color:#888;'>(nekomprimovaně — ZIP bude menší)</span></p>"
        )
        self.lbl_preview.setText(html)

    def _do_export(self) -> None:
        target_str = self.ed_path.text().strip()
        if not target_str:
            QMessageBox.warning(self, "Chybí cesta", "Vyber cílový .zip soubor.")
            return
        target = Path(target_str).expanduser()
        if not str(target).lower().endswith(".zip"):
            target = target.with_suffix(".zip")

        if target.exists():
            confirm = QMessageBox.question(
                self,
                "Cílový soubor existuje",
                f"Soubor <code>{escape(str(target))}</code> už existuje. Přepsat?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

        opts = self._current_opts()
        try:
            result = self.pm.export_profile_to_zip(
                profile_id=self.profile.id,
                target_zip=target,
                include_documents=opts.include_documents,
                include_harmonograms=opts.include_harmonograms,
                include_db_bak=opts.include_db_bak,
                include_backups=opts.include_backups,
                include_templates=opts.include_templates,
            )
        except ProfileError as exc:
            QMessageBox.critical(self, "Export selhal", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self, "Neočekávaná chyba", f"Export skončil chybou:\n{exc}"
            )
            return

        self.exported_zip = target
        self._show_done_dialog(result)

    def _show_done_dialog(self, result: dict) -> None:
        zip_size = result["zip_size_bytes"]
        uncompressed = result["uncompressed_bytes"]
        ratio = (zip_size / uncompressed * 100) if uncompressed else 100.0
        target = result["target_zip"]
        body = f"""
        <p style='color:#2e7d32;font-weight:bold;'>✓ Export dokončen.</p>
        <table style='border-collapse:collapse;'>
          <tr><td>Cíl:</td><td><code>{escape(str(target))}</code></td></tr>
          <tr><td>Velikost ZIPu:</td><td>{_fmt_bytes(zip_size)}</td></tr>
          <tr><td>Nekomprimovaně:</td><td>{_fmt_bytes(uncompressed)}</td></tr>
          <tr><td>Komprese:</td><td>{ratio:.1f} % původní velikosti</td></tr>
          <tr><td>Souborů v ZIPu:</td><td>{result['files_added']}</td></tr>
        </table>
        <p style='color:#666;'>
          Soubor můžeš přenést přes USB / iCloud / email a na druhém zařízení
          otevřít přes 👤 → 📥 Importovat profil ze ZIPu…
        </p>
        """
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Export dokončen")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(body)
        btn_reveal = msg.addButton(
            "📂 Ukázat ve Finderu", QMessageBox.ButtonRole.ActionRole
        )
        msg.addButton(QMessageBox.StandardButton.Close)
        msg.exec()
        if msg.clickedButton() == btn_reveal:
            _open_in_filemanager(Path(target))
        self.accept()


# ── Import ─────────────────────────────────────────────────────────────────


class ImportProfileDialog(QDialog):
    """Dialog pro import profilu ze ZIPu jako nový profil v registry."""

    def __init__(self, pm: ProfileManager, parent=None) -> None:
        super().__init__(parent)
        self.pm = pm
        self.created: Profile | None = None
        self.target_data_dir: Path | None = None

        self.setWindowTitle("Importovat profil ze ZIPu")
        self.setMinimumSize(680, 580)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        header = QLabel("📥 Importovat profil ze ZIPu")
        header.setStyleSheet("font-size:15px;font-weight:bold;")
        outer.addWidget(header)

        # ── Zdroj (.zip) ────────────────────────────────────────────────
        zip_row = QHBoxLayout()
        self.ed_zip = QLineEdit()
        self.ed_zip.setPlaceholderText("vyber .zip vytvořený přes Export profilu")
        self.ed_zip.textChanged.connect(self._on_zip_changed)
        btn_browse = QPushButton("Procházet…")
        btn_browse.clicked.connect(self._browse_zip)
        zip_row.addWidget(self.ed_zip, stretch=1)
        zip_row.addWidget(btn_browse)
        outer.addLayout(zip_row)

        # ── Manifest preview ────────────────────────────────────────────
        self.manifest_view = QTextBrowser()
        self.manifest_view.setMinimumHeight(180)
        self.manifest_view.setHtml(
            "<p style='color:#888;'>Vyber ZIP soubor pro náhled manifestu.</p>"
        )
        outer.addWidget(self.manifest_view, stretch=1)

        # ── Cíl importu: nový profil VS sloučit s existujícím ───────────
        target_box = QGroupBox("Cíl importu")
        target_layout = QVBoxLayout(target_box)

        self.rb_new = QRadioButton(
            "🆕 Vytvořit nový profil"
        )
        self.rb_new.setChecked(True)
        self.rb_merge = QRadioButton(
            "🔀 Sloučit s existujícím profilem (add-only merge)"
        )
        self._target_group = QButtonGroup(self)
        self._target_group.addButton(self.rb_new)
        self._target_group.addButton(self.rb_merge)
        target_layout.addWidget(self.rb_new)

        # — pole pro „nový profil"
        new_form = QFormLayout()
        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText(
            "Název profilu v registry — předvyplní se z manifestu"
        )
        new_form.addRow("    Název profilu", self.ed_name)

        target_row = QHBoxLayout()
        self.ed_target = QLineEdit()
        self.ed_target.setPlaceholderText("cílová složka, kam rozbalit data")
        self._set_default_target()
        btn_target_browse = QPushButton("Procházet…")
        btn_target_browse.clicked.connect(self._browse_target)
        target_row.addWidget(self.ed_target, stretch=1)
        target_row.addWidget(btn_target_browse)
        new_form.addRow("    Cílová složka", target_row)

        self.chk_overwrite = QCheckBox(
            "⚠ Přepsat existující data v cílové složce"
        )
        self.chk_overwrite.setStyleSheet("color:#c62828;")
        new_form.addRow("", self.chk_overwrite)
        target_layout.addLayout(new_form)

        target_layout.addWidget(self.rb_merge)

        # — pole pro „merge"
        merge_form = QFormLayout()
        self.cb_target_profile = QComboBox()
        self._populate_target_combo()
        merge_form.addRow("    Cílový profil", self.cb_target_profile)
        self.lbl_merge_help = QLabel(
            "<small><i>Add-only: do cílového profilu se přidají entity "
            "(studenti / oponenti / práce / šablony…), které tam nejsou; "
            "existující se <b>nemění</b>. Soubory se zkopírují, pokud cílový "
            "název ještě neexistuje. Před zápisem uvidíš preview, co se "
            "přidá a co se přeskočí.</i></small>"
        )
        self.lbl_merge_help.setWordWrap(True)
        self.lbl_merge_help.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_merge_help.setStyleSheet("color:#888;")
        merge_form.addRow("", self.lbl_merge_help)
        target_layout.addLayout(merge_form)

        outer.addWidget(target_box)

        # Toggle visibility podle radio výběru
        self.rb_new.toggled.connect(self._update_target_visibility)
        self._update_target_visibility()

        # ── Tlačítka ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Zavřít")
        btn_cancel.clicked.connect(self.reject)
        self.btn_import = QPushButton("📥 Importovat")
        self.btn_import.setEnabled(False)
        bf = self.btn_import.font()
        bf.setBold(True)
        self.btn_import.setFont(bf)
        self.btn_import.clicked.connect(self._do_import)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_import)
        outer.addLayout(btn_row)

    # ── helpers ─────────────────────────────────────────────────────────

    def _set_default_target(self) -> None:
        # ~/BPDPManager-Profiles/imported-{timestamp}/
        from datetime import datetime as _dt

        base = Path.home() / "BPDPManager-Profiles"
        target = base / f"imported-{_dt.now().strftime('%Y%m%d-%H%M%S')}"
        self.ed_target.setText(str(target))

    def _populate_target_combo(self) -> None:
        """Naplní combo s registrovanými profily (jako cíl pro merge)."""
        self.cb_target_profile.clear()
        active_id = self.pm.active.id if self.pm.active else None
        for p in self.pm.all_profiles():
            label = ("● " if active_id and p.id == active_id else "   ") + p.name
            self.cb_target_profile.addItem(label, p.id)
        # Disable merge radio pokud žádný profil neexistuje
        has_any = self.cb_target_profile.count() > 0
        self.rb_merge.setEnabled(has_any)
        if not has_any:
            self.rb_merge.setToolTip(
                "Žádný profil v registru — nejdřív vytvoř profil "
                'nebo zvol „Vytvořit nový profil".'
            )

    def _update_target_visibility(self) -> None:
        """Skryj / ukaž pole podle zvoleného režimu."""
        is_new = self.rb_new.isChecked()
        # „nový profil" pole
        self.ed_name.setEnabled(is_new)
        self.ed_target.setEnabled(is_new)
        self.chk_overwrite.setEnabled(is_new)
        # „merge" pole
        self.cb_target_profile.setEnabled(not is_new)

    def _browse_zip(self) -> None:
        current = self.ed_zip.text().strip() or str(Path.home() / "Downloads")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Vyber .zip s exportem profilu",
            current,
            "ZIP soubory (*.zip);;Všechny soubory (*.*)",
        )
        if path:
            self.ed_zip.setText(path)

    def _browse_target(self) -> None:
        current = self.ed_target.text().strip() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(
            self,
            "Cílová složka pro data profilu",
            current,
        )
        if folder:
            self.ed_target.setText(folder)

    def _on_zip_changed(self) -> None:
        zip_str = self.ed_zip.text().strip()
        if not zip_str:
            self.manifest_view.setHtml(
                "<p style='color:#888;'>Vyber ZIP soubor pro náhled manifestu.</p>"
            )
            self.btn_import.setEnabled(False)
            return
        try:
            preview = read_zip_manifest(Path(zip_str))
        except Exception as exc:  # noqa: BLE001
            self.manifest_view.setHtml(
                f"<p style='color:#c62828;'>Chyba čtení: {escape(str(exc))}</p>"
            )
            self.btn_import.setEnabled(False)
            return

        if not preview.valid:
            self.manifest_view.setHtml(
                f"<p style='color:#c62828;'>❌ {escape(preview.error)}</p>"
            )
            self.btn_import.setEnabled(False)
            return

        stats = preview.stats
        manifest = preview.manifest
        contents = manifest.get("contents") or {}
        body = f"""
        <style>
          h3 {{ margin: 8px 0 4px 0; font-size: 13px; color: #444; }}
          table.kv td {{ padding: 2px 8px 2px 0; vertical-align: top; }}
          table.kv td.k {{ color: #666; white-space: nowrap; }}
        </style>
        <p style='color:#2e7d32;'>✓ Validní BPDPManager export</p>
        <table class='kv'>
          <tr><td class='k'>Profil:</td><td><b>{escape(preview.profile_name)}</b></td></tr>
          <tr><td class='k'>Exportováno:</td><td>{escape(preview.exported_at)}</td></tr>
          <tr><td class='k'>App verze:</td><td>{escape(preview.app_version)}</td></tr>
          <tr><td class='k'>Schema:</td><td>v{preview.schema_version}</td></tr>
          <tr><td class='k'>Export verze:</td>
              <td>v{manifest.get('bpdp_manager_export_version', '?')} </td></tr>
        </table>

        <h3>Obsah</h3>
        <table class='kv'>
          <tr><td class='k'>db.json:</td>
              <td>{'✓' if contents.get('db_json') else '—'}</td></tr>
          <tr><td class='k'>db.json.bak:</td>
              <td>{'✓' if contents.get('db_bak') else '—'}</td></tr>
          <tr><td class='k'>Dokumenty:</td>
              <td>{stats.get('documents_count', 0)} souborů</td></tr>
          <tr><td class='k'>Harmonogramy:</td>
              <td>{stats.get('harmonograms_count', 0)} souborů</td></tr>
          <tr><td class='k'>Zálohy:</td>
              <td>{stats.get('backups_count', 0)} souborů</td></tr>
          <tr><td class='k'>Celkem nekomprimovaně:</td>
              <td>{_fmt_bytes(int(stats.get('total_uncompressed_bytes', 0)))}</td></tr>
        </table>
        """
        self.manifest_view.setHtml(body)

        # Předvyplň název z manifestu (pokud uživatel ještě nic nepřepsal)
        suggested_name = preview.profile_name or "Importovaný profil"
        if not self.ed_name.text().strip():
            self.ed_name.setText(suggested_name)

        self.btn_import.setEnabled(True)

    def _do_import(self) -> None:
        zip_str = self.ed_zip.text().strip()
        if not zip_str:
            return

        if self.rb_merge.isChecked():
            self._do_merge_import(zip_str)
        else:
            self._do_new_profile_import(zip_str)

    def _do_new_profile_import(self, zip_str: str) -> None:
        """Vytvoří nový profil z ZIPu (jako dosud)."""
        target_str = self.ed_target.text().strip()
        if not target_str:
            QMessageBox.warning(
                self, "Chybí cíl", "Vyber cílovou složku pro data profilu."
            )
            return
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Chybí název", "Zadej název profilu.")
            return

        try:
            profile, result = self.pm.import_profile_from_zip(
                source_zip=Path(zip_str),
                target_data_dir=Path(target_str).expanduser(),
                name=name,
                overwrite_existing=self.chk_overwrite.isChecked(),
            )
        except ProfileError as exc:
            QMessageBox.critical(self, "Import selhal", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self, "Neočekávaná chyba", f"Import skončil chybou:\n{exc}"
            )
            return

        self.created = profile
        self.target_data_dir = Path(result["target_data_dir"])
        self._show_done_dialog(profile, result)

    def _do_merge_import(self, zip_str: str) -> None:
        """Merge ZIPu do existujícího vybraného profilu."""
        target_id = self.cb_target_profile.currentData()
        if not target_id:
            QMessageBox.warning(
                self, "Chybí cíl", "Vyber cílový profil v combo boxu."
            )
            return
        target_profile = self.pm.get(target_id)
        if target_profile is None:
            QMessageBox.warning(self, "Chybí cíl", "Cílový profil neexistuje.")
            return

        # 1) Spočti preview bez modifikace
        try:
            merge_prev, _ = self.pm.compute_merge_preview(
                Path(zip_str), target_id
            )
        except ProfileError as exc:
            QMessageBox.critical(self, "Preview selhalo", str(exc))
            return

        # 2) Confirmation dialog s preview
        if not self._confirm_merge(target_profile, merge_prev):
            return

        # 3) Vytvoř bezpečnostní zálohu cíle (před zápisem)
        try:
            from ..services import BackupManager  # lazy

            target_db = Path(target_profile.data_dir) / "db.json"
            if target_db.is_file():
                BackupManager(Path(target_profile.data_dir)).create_backup(
                    target_db, suffix="before-merge", dedupe=False
                )
        except Exception:  # noqa: BLE001
            # Záloha selhala — nepovinné, pokračujeme.
            pass

        # 4) Provést merge
        try:
            result = self.pm.merge_zip_into_profile(
                source_zip=Path(zip_str),
                target_profile_id=target_id,
            )
        except ProfileError as exc:
            QMessageBox.critical(self, "Merge selhal", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self, "Neočekávaná chyba", f"Merge skončil chybou:\n{exc}"
            )
            return

        self.created = target_profile  # signalizace pro MainWindow, kam přepnout
        self.target_data_dir = Path(target_profile.data_dir)
        self._show_merge_done_dialog(target_profile, result)

    def _confirm_merge(self, target_profile, prev) -> bool:
        """Pre-merge confirmation dialog s detailním preview."""
        rows: list[str] = []

        def _add_row(label: str, new_count: int, skipped_count: int) -> None:
            new_str = f"<b style='color:#2e7d32;'>+{new_count}</b>" if new_count else "—"
            skipped_str = (
                f"<span style='color:#888;'>{skipped_count} přeskočeno</span>"
                if skipped_count else ""
            )
            rows.append(
                f"<tr><td>{escape(label)}</td>"
                f"<td>{new_str}</td><td>{skipped_str}</td></tr>"
            )

        _add_row("👨‍🎓 Studenti", prev.new_students, prev.skipped_students)
        _add_row("🧐 Oponenti", prev.new_opponents, prev.skipped_opponents)
        _add_row("🎓 Vedoucí (registr)", prev.new_supervisors, prev.skipped_supervisors)
        _add_row("🗂 Obory", prev.new_obory, prev.skipped_obory)
        _add_row("📚 Vedené práce", prev.new_theses, prev.skipped_theses)
        _add_row("🧐 Oponentské posudky", prev.new_opposing, prev.skipped_opposing)
        _add_row("📝 Šablony posudků", prev.new_templates, prev.skipped_templates)
        _add_row("📅 Akademické roky", prev.new_academic_years, prev.skipped_academic_years)
        rows.append(
            f"<tr><td>📎 Soubory</td>"
            f"<td><b style='color:#2e7d32;'>+{prev.new_files}</b></td>"
            f"<td><span style='color:#888;'>{prev.skipped_files} přeskočeno</span> · "
            f"{_fmt_bytes(prev.new_files_bytes)}</td></tr>"
        )

        total_new = (
            prev.new_students + prev.new_opponents + prev.new_supervisors
            + prev.new_obory + prev.new_theses + prev.new_opposing
            + prev.new_templates + prev.new_academic_years + prev.new_files
        )
        total_skip = (
            prev.skipped_students + prev.skipped_opponents + prev.skipped_supervisors
            + prev.skipped_obory + prev.skipped_theses + prev.skipped_opposing
            + prev.skipped_templates + prev.skipped_academic_years + prev.skipped_files
        )

        body = (
            f"<p>Merge bude proveden do profilu "
            f"<b>{escape(target_profile.name)}</b>. Sémantika "
            f"<b>add-only</b> — žádná existující data v cílovém profilu "
            f"se nezmění. Konflikty se přeskočí.</p>"
            f"<hr>"
            f"<table style='border-collapse:collapse;'>"
            f"<tr style='color:#888;'>"
            f"<th style='text-align:left;'>Entita</th>"
            f"<th style='text-align:left;padding-left:14px;'>Přidá se</th>"
            f"<th style='text-align:left;padding-left:14px;'>Konflikty</th>"
            f"</tr>"
            f"{''.join(rows)}"
            f"</table>"
            f"<p style='margin-top:10px;'>"
            f"Celkem: <b>+{total_new}</b> nových položek, "
            f"<span style='color:#888;'>{total_skip} přeskočeno</span>.</p>"
            f"<p style='color:#666;font-size:11px;'>"
            f"Před zápisem se vytvoří záloha <code>before-merge</code> "
            f"v profilu pro případný rollback.</p>"
        )

        if total_new == 0:
            body += (
                "<p style='color:#c62828;'><b>⚠ Žádná data k přidání</b> — "
                "cíl už obsahuje vše, co ZIP nabízí. Merge nepřinese změnu.</p>"
            )

        # Vlastní dialog s rich textem
        dlg = QDialog(self)
        dlg.setWindowTitle("Potvrdit merge")
        dlg.setMinimumSize(620, 520)
        outer = QVBoxLayout(dlg)
        header = QLabel("🔀 Potvrdit merge")
        header.setStyleSheet("font-size:14px;font-weight:bold;")
        outer.addWidget(header)
        body_view = QTextBrowser()
        body_view.setHtml(body)
        outer.addWidget(body_view, stretch=1)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Zrušit")
        btn_cancel.clicked.connect(dlg.reject)
        btn_go = QPushButton("🔀 Provést merge")
        btn_go.setEnabled(total_new > 0)
        bf = btn_go.font()
        bf.setBold(True)
        btn_go.setFont(bf)
        btn_go.setDefault(True)
        btn_go.clicked.connect(dlg.accept)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_go)
        outer.addLayout(btn_row)

        return dlg.exec() == QDialog.DialogCode.Accepted

    def _show_merge_done_dialog(self, profile, result: dict) -> None:
        """Sumární dialog po úspěšném merge."""
        body = f"""
        <p style='color:#2e7d32;font-weight:bold;'>✓ Merge dokončen.</p>
        <p>Sloučeno do profilu <b>{escape(profile.name)}</b>.</p>
        <table style='border-collapse:collapse;'>
          <tr><td>👨‍🎓 Studenti:</td>
              <td><b>+{result['new_students']}</b>
              <span style='color:#888;'>· {result['skipped_students']} přeskočeno</span></td></tr>
          <tr><td>🧐 Oponenti:</td>
              <td><b>+{result['new_opponents']}</b>
              <span style='color:#888;'>· {result['skipped_opponents']} přeskočeno</span></td></tr>
          <tr><td>🎓 Vedoucí:</td>
              <td><b>+{result['new_supervisors']}</b>
              <span style='color:#888;'>· {result['skipped_supervisors']} přeskočeno</span></td></tr>
          <tr><td>🗂 Obory:</td>
              <td><b>+{result['new_obory']}</b>
              <span style='color:#888;'>· {result['skipped_obory']} přeskočeno</span></td></tr>
          <tr><td>📚 Vedené práce:</td>
              <td><b>+{result['new_theses']}</b>
              <span style='color:#888;'>· {result['skipped_theses']} přeskočeno</span></td></tr>
          <tr><td>🧐 Oponentské posudky:</td>
              <td><b>+{result['new_opposing']}</b>
              <span style='color:#888;'>· {result['skipped_opposing']} přeskočeno</span></td></tr>
          <tr><td>📝 Šablony posudků:</td>
              <td><b>+{result['new_templates']}</b>
              <span style='color:#888;'>· {result['skipped_templates']} přeskočeno</span></td></tr>
          <tr><td>📅 Akademické roky:</td>
              <td><b>+{result['new_academic_years']}</b>
              <span style='color:#888;'>· {result['skipped_academic_years']} přeskočeno</span></td></tr>
          <tr><td>📎 Soubory:</td>
              <td><b>+{result['files_copied']}</b>
              <span style='color:#888;'>· {result['files_skipped']} přeskočeno · </span>
              {_fmt_bytes(result['bytes_copied'])}</td></tr>
        </table>
        <p style='color:#666;'>
          Po zavření dialogu se aplikace přepne na sloučený profil (pokud
          ještě není aktivní). Zálohu před merge najdeš v <i>👤 → 💾 Zálohy</i>
          se značkou <code>before-merge</code>.
        </p>
        """
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Merge dokončen")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(body)
        msg.addButton(QMessageBox.StandardButton.Close)
        msg.exec()
        self.accept()

    def _show_done_dialog(self, profile: Profile, result: dict) -> None:
        stats = result.get("manifest", {}).get("stats") or {}
        body = f"""
        <p style='color:#2e7d32;font-weight:bold;'>✓ Import dokončen.</p>
        <table style='border-collapse:collapse;'>
          <tr><td>Nový profil:</td><td><b>{escape(profile.name)}</b></td></tr>
          <tr><td>Cesta:</td><td><code>{escape(str(self.target_data_dir))}</code></td></tr>
          <tr><td>Souborů rozbaleno:</td><td>{result['files_extracted']}</td></tr>
          <tr><td>Velikost dat:</td>
              <td>{_fmt_bytes(int(stats.get('total_uncompressed_bytes', 0)))}</td></tr>
        </table>
        <p style='color:#666;'>
          Po zavření dialogu se aplikace přepne na nový profil.
        </p>
        """
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Import dokončen")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(body)
        msg.addButton(QMessageBox.StandardButton.Close)
        msg.exec()
        self.accept()
