"""Tichá kontrola aktualizací po startu + dialog „Je k dispozici nová verze".

Kontrola běží na vlákně (neblokuje start); offline/chyba = ticho. Dialog ukáže
novou verzi a changelog všech verzí mezi nainstalovanou a nejnovější. Po
potvrzení:

* z git klonu — ``git pull`` + ``pip install -e .`` a restart aplikace,
* v zabalené aplikaci (.app) — stáhne nové ``.dmg`` z GitHub Releases přímo
  v aplikaci (uživatel zvolí, kam), ověří SHA-256 a otevře ho ve Finderu.
  Takto stažený soubor nemá karanténu, takže ho macOS po přetažení do
  Aplikací nezablokuje. Když Release digest neuvádí, otevře se stažení
  v prohlížeči (s návodem na „Přesto otevřít").
"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from ..i18n import tr
from ..services import update_checker as uc


class UpdateChecker(QObject):
    """Tichá kontrola nové verze na pozadí. ``finished(UpdateInfo | None)``.

    Chyby (offline, GitHub nedostupný, není git klon) = ``None`` — uživatele
    nikdy neotravujeme kvůli selhané kontrole.
    """

    finished = Signal(object)

    def __init__(self, current_version: str, parent=None) -> None:
        super().__init__(parent)
        self._current = current_version

    def start(self) -> None:
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self) -> None:
        info = None
        try:
            if uc.is_frozen():                  # .app → poslední GitHub Release
                info = uc.check_for_frozen_update(self._current)
            elif uc.repo_root() is not None:    # git klon → CHANGELOG na main
                info = uc.check_for_update(self._current)
            # jinak (pip bez klonu) aktualizovat neumíme → ticho
        except Exception:
            info = None
        self.finished.emit(info)


class _UpdateWorker(QObject):
    """Provedení update (git pull + pip install) na vlákně."""

    done = Signal(bool, str)

    def start(self) -> None:
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self) -> None:
        root = uc.repo_root()
        if root is None:
            self.done.emit(False, "Aplikace neběží z git klonu — nelze aktualizovat.")
            return
        try:
            ok, msg = uc.perform_update(root)
        except Exception as exc:
            ok, msg = False, f"Aktualizace selhala: {exc}"
        self.done.emit(ok, msg)


class _DownloadWorker(QObject):
    """Stažení + ověření .dmg na vlákně (``uc.download_update``)."""

    progress = Signal(object, object)      # (staženo, celkem) v bajtech
    done = Signal(bool, str, str)          # (ok, zpráva, cesta k souboru)

    def __init__(self, info: uc.UpdateInfo, dest: Path, parent=None) -> None:
        super().__init__(parent)
        self._info = info
        self._dest = dest
        self._cancel = False

    def start(self) -> None:
        threading.Thread(target=self._work, daemon=True).start()

    def cancel(self) -> None:
        self._cancel = True

    def _work(self) -> None:
        try:
            path = uc.download_update(
                self._info.download_url, self._dest, self._info.download_sha256,
                progress=lambda d, t: self.progress.emit(d, t),
                is_cancelled=lambda: self._cancel,
            )
        except uc.UpdateDownloadCancelledError:
            self.done.emit(False, tr("Stahování zrušeno."), "")
            return
        except uc.UpdateDownloadError as exc:
            self.done.emit(False, str(exc), "")
            return
        self.done.emit(True, "", str(path))


class UpdateDialog(QDialog):
    """„K dispozici je verze X" + changelog + Aktualizovat / Později / Přeskočit."""

    def __init__(self, info: uc.UpdateInfo, parent=None, *,
                 check_enabled: bool = True,
                 download_dir: str | None = None) -> None:
        super().__init__(parent)
        self.info = info
        self.skip_requested = False          # „Přeskočit tuto verzi"
        self.check_enabled = check_enabled   # stav vypínače po zavření
        self.updated = False
        #: Složka, kam uživatel naposledy ukládal .dmg (volající si ji uloží).
        self.download_dir = download_dir
        #: Cesta ke staženému a ověřenému .dmg (po úspěchu).
        self.downloaded_path: str | None = None
        self._worker: _UpdateWorker | None = None
        self._dl_worker: _DownloadWorker | None = None
        if info.can_download_in_app:
            self._mode = "inapp"       # stáhnout + ověřit v aplikaci
        elif info.download_url:
            self._mode = "browser"     # Release bez digestu → prohlížeč
        else:
            self._mode = "git"
        self.setWindowTitle(tr("Aktualizace aplikace"))
        self.setMinimumSize(560, 480)

        lay = QVBoxLayout(self)
        head = QLabel(
            f"<b>K dispozici je verze {info.latest}</b> "
            f"<span style='color:#888;'>(nainstalovaná {info.current})</span>"
        )
        head.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(head)

        sub = QLabel(tr("Novinky od tvé verze:"))
        lay.addWidget(sub)
        self.changelog = QTextBrowser()
        self.changelog.setOpenExternalLinks(True)
        self.changelog.setMarkdown(
            info.changelog_md
            or tr("Seznam novinek se nepodařilo načíst — najdeš ho na stránce vydání.")
        )
        lay.addWidget(self.changelog, stretch=1)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        lay.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        self.cb_check = QCheckBox(tr("Kontrolovat aktualizace po startu aplikace"))
        self.cb_check.setChecked(check_enabled)
        lay.addWidget(self.cb_check)

        btns = QHBoxLayout()
        # Zabalená aplikace se nemůže sama přepsat — stáhne nové .dmg.
        self.btn_update = QPushButton({
            "inapp": tr("⬇ Stáhnout a otevřít"),
            "browser": tr("⬇ Stáhnout novou verzi"),
            "git": tr("🔄 Aktualizovat a restartovat"),
        }[self._mode])
        self.btn_update.setDefault(True)
        self.btn_update.clicked.connect(self._on_update)
        self.btn_skip = QPushButton(tr("Přeskočit tuto verzi"))
        self.btn_skip.setToolTip(
            f"Verze {info.latest} se už nebude nabízet (další ano)."
        )
        self.btn_skip.clicked.connect(self._on_skip)
        self.btn_later = QPushButton(tr("Později"))
        self.btn_later.clicked.connect(self._on_later)
        btns.addWidget(self.btn_update)
        btns.addStretch(1)
        btns.addWidget(self.btn_skip)
        btns.addWidget(self.btn_later)
        lay.addLayout(btns)

    # ── akce ───────────────────────────────────────────────────────────────
    def _on_skip(self) -> None:
        self.skip_requested = True
        self.reject()

    def _on_later(self) -> None:
        """„Později" / „Zrušit stahování" (během stahování dialog nezavírá)."""
        if self._dl_worker is not None:
            self._dl_worker.cancel()
            self.status.setText(tr("⏳ Ruším stahování…"))
            return
        self.reject()

    def _on_update(self) -> None:
        if self._mode == "inapp":
            self._start_in_app_download()
            return
        if self._mode == "browser":
            self._open_download()
            return
        for b in (self.btn_update, self.btn_skip, self.btn_later):
            b.setEnabled(False)
        self.status.setText(tr("⏳ Stahuji aktualizaci (git pull + závislosti)…"))
        self._worker = _UpdateWorker(parent=self)
        self._worker.done.connect(self._on_update_done)
        self._worker.start()

    def _default_download_path(self) -> Path:
        folder = Path(self.download_dir) if self.download_dir else None
        if folder is None or not folder.is_dir():
            folder = Path.home() / "Downloads"
        name = self.info.download_url.rsplit("/", 1)[-1]
        if not name.endswith(".dmg"):
            name = f"BPDPManager-{self.info.latest}{uc.DMG_SUFFIX}"
        return folder / name

    def _start_in_app_download(self) -> None:
        """Zeptá se, kam uložit, a na pozadí stáhne + ověří .dmg."""
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Kam uložit instalační soubor"),
            str(self._default_download_path()), tr("Obraz disku (*.dmg)"),
        )
        if not path:
            return                                   # uživatel volbu zrušil
        dest = Path(path)
        if dest.suffix.lower() != ".dmg":
            dest = dest.with_name(dest.name + ".dmg")
        self.download_dir = str(dest.parent)

        self.btn_update.setEnabled(False)
        self.btn_skip.setEnabled(False)
        self.btn_later.setText(tr("Zrušit stahování"))
        self.progress.setVisible(True)
        self.progress.setRange(0, 1000 if self.info.download_size else 0)
        self.progress.setValue(0)
        self.status.setText(tr("⬇ Stahuji instalační soubor…"))

        self._dl_worker = _DownloadWorker(self.info, dest, parent=self)
        self._dl_worker.progress.connect(self._on_download_progress)
        self._dl_worker.done.connect(self._on_download_done)
        self._dl_worker.start()

    def _on_download_progress(self, done, total) -> None:
        total = total or self.info.download_size
        if total:
            self.progress.setRange(0, 1000)
            self.progress.setValue(min(1000, int(done * 1000 / total)))
            self.status.setText(tr("⬇ Stahuji instalační soubor… {d} / {t} MB").format(
                d=done // (1 << 20), t=total // (1 << 20)))

    def _on_download_done(self, ok: bool, msg: str, path: str) -> None:
        self._dl_worker = None
        self.progress.setVisible(False)
        if not ok:
            self.status.setText(f"⚠ {msg}")
            self.btn_update.setEnabled(True)
            self.btn_skip.setEnabled(True)
            self.btn_later.setText(tr("Později"))
            return
        self.downloaded_path = path
        self.btn_later.setText(tr("Zavřít"))
        self.status.setText(tr(
            "✅ Staženo a ověřeno (SHA-256). Otevírám instalační soubor — zavři "
            "BPDPManager a přetáhni ho z okna .dmg do složky Aplikace (nahradit). "
            "Tvoje data zůstanou beze změny."
        ))
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _open_download(self) -> None:
        """Záloha (Release bez digestu): stažení .dmg v prohlížeči + návod."""
        QDesktopServices.openUrl(QUrl(self.info.download_url))
        self.btn_update.setEnabled(False)
        self.btn_later.setText(tr("Zavřít"))
        self.status.setText(tr(
            "⬇ Stahuje se instalační soubor .dmg. Až se stáhne: zavři aplikaci, "
            "otevři .dmg a přetáhni BPDPManager do složky Aplikace (nahradit). "
            "Když macOS hlásí, že aplikaci nelze otevřít: Nastavení systému → "
            "Soukromí a zabezpečení → Přesto otevřít. Tvoje data zůstanou beze změny."
        ))

    def _on_update_done(self, ok: bool, msg: str) -> None:
        self._worker = None
        if ok:
            self.updated = True
            self.status.setText(f"✅ {msg}")
            self.accept()
            uc.restart_app()
            return
        self.status.setText(f"⚠ {msg}")
        for b in (self.btn_update, self.btn_skip, self.btn_later):
            b.setEnabled(True)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self.check_enabled = self.cb_check.isChecked()
        if self._dl_worker is not None:       # zavřením okna stahování zrušit
            self._dl_worker.cancel()
        super().closeEvent(event)

    def reject(self) -> None:
        self.check_enabled = self.cb_check.isChecked()
        if self._dl_worker is not None:       # Esc během stahování = zrušit
            self._dl_worker.cancel()
        super().reject()

    def accept(self) -> None:
        self.check_enabled = self.cb_check.isChecked()
        super().accept()
