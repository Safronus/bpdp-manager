"""Tichá kontrola aktualizací po startu + dialog „Je k dispozici nová verze".

Kontrola běží na vlákně (neblokuje start); offline/chyba = ticho. Dialog ukáže
novou verzi a changelog všech verzí mezi nainstalovanou a nejnovější; po
potvrzení provede ``git pull`` + ``pip install -e .`` a restartuje aplikaci.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

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
            if uc.repo_root() is not None:      # mimo git klon nelze updatovat
                info = uc.check_for_update(self._current)
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


class UpdateDialog(QDialog):
    """„K dispozici je verze X" + changelog + Aktualizovat / Později / Přeskočit."""

    def __init__(self, info: uc.UpdateInfo, parent=None, *,
                 check_enabled: bool = True) -> None:
        super().__init__(parent)
        self.info = info
        self.skip_requested = False          # „Přeskočit tuto verzi"
        self.check_enabled = check_enabled   # stav vypínače po zavření
        self.updated = False
        self._worker: _UpdateWorker | None = None
        self.setWindowTitle("Aktualizace aplikace")
        self.setMinimumSize(560, 480)

        lay = QVBoxLayout(self)
        head = QLabel(
            f"<b>K dispozici je verze {info.latest}</b> "
            f"<span style='color:#888;'>(nainstalovaná {info.current})</span>"
        )
        head.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(head)

        sub = QLabel("Novinky od tvé verze:")
        lay.addWidget(sub)
        self.changelog = QTextBrowser()
        self.changelog.setOpenExternalLinks(True)
        self.changelog.setMarkdown(info.changelog_md)
        lay.addWidget(self.changelog, stretch=1)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        self.cb_check = QCheckBox("Kontrolovat aktualizace po startu aplikace")
        self.cb_check.setChecked(check_enabled)
        lay.addWidget(self.cb_check)

        btns = QHBoxLayout()
        self.btn_update = QPushButton("🔄 Aktualizovat a restartovat")
        self.btn_update.setDefault(True)
        self.btn_update.clicked.connect(self._on_update)
        self.btn_skip = QPushButton("Přeskočit tuto verzi")
        self.btn_skip.setToolTip(
            f"Verze {info.latest} se už nebude nabízet (další ano)."
        )
        self.btn_skip.clicked.connect(self._on_skip)
        self.btn_later = QPushButton("Později")
        self.btn_later.clicked.connect(self.reject)
        btns.addWidget(self.btn_update)
        btns.addStretch(1)
        btns.addWidget(self.btn_skip)
        btns.addWidget(self.btn_later)
        lay.addLayout(btns)

    # ── akce ───────────────────────────────────────────────────────────────
    def _on_skip(self) -> None:
        self.skip_requested = True
        self.reject()

    def _on_update(self) -> None:
        for b in (self.btn_update, self.btn_skip, self.btn_later):
            b.setEnabled(False)
        self.status.setText("⏳ Stahuji aktualizaci (git pull + závislosti)…")
        self._worker = _UpdateWorker(parent=self)
        self._worker.done.connect(self._on_update_done)
        self._worker.start()

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
        super().closeEvent(event)

    def reject(self) -> None:
        self.check_enabled = self.cb_check.isChecked()
        super().reject()

    def accept(self) -> None:
        self.check_enabled = self.cb_check.isChecked()
        super().accept()
