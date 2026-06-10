"""Odeslání jednoho souboru e-mailem (volba příjemce, předmětu, těla).

Odesílatel je e-mail uživatele z profilu, transport řeší SMTP služba
(:mod:`bpdpmanager.services.email_sender`) jako u odesílání posudků — heslo se
zadává při odeslání a neukládá se; při selhání SMTP je fallback přes .eml.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from ..i18n import tr
from ..services import email_sender


def _open_path(path: Path) -> None:
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:  # noqa: BLE001
        pass


class SendFileDialog(QDialog):
    def __init__(
        self, profile_manager, file_paths, *, default_subject: str = "", parent=None
    ) -> None:
        super().__init__(parent)
        self.profile_manager = profile_manager
        # Přijmi jeden Path i seznam.
        if isinstance(file_paths, (str, Path)):
            self.file_paths = [Path(file_paths)]
        else:
            self.file_paths = [Path(p) for p in file_paths]

        self.setWindowTitle(tr("Odeslat soubor e-mailem"))
        self.setMinimumWidth(560)

        profile = profile_manager.active if profile_manager else None
        self._user_email = (profile.user_email if profile else "") or ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        title = QLabel(tr("✉ Odeslat soubor e-mailem"))
        title.setStyleSheet("font-size:16px;font-weight:bold;")
        outer.addWidget(title)

        form = QFormLayout()
        self.lbl_from = QLabel(self._user_email or "— (doplň v Nastavení e-mailu)")
        self.lbl_from.setStyleSheet("color:#888;")
        form.addRow(tr("Odesílatel"), self.lbl_from)

        self.ed_to = QLineEdit()
        self.ed_to.setPlaceholderText(tr("příjemce@example.cz"))
        form.addRow(tr("Příjemce"), self.ed_to)

        self.ed_subject = QLineEdit(default_subject or self.file_paths[0].name)
        form.addRow(tr("Předmět"), self.ed_subject)

        names = ", ".join(p.name for p in self.file_paths)
        self.lbl_attach = QLabel(f"📎 {names}")
        self.lbl_attach.setWordWrap(True)
        self.lbl_attach.setToolTip(names)
        form.addRow(f"Přílohy ({len(self.file_paths)})", self.lbl_attach)
        outer.addLayout(form)

        word = "soubor" if len(self.file_paths) == 1 else "soubory"
        outer.addWidget(QLabel(tr("Text e-mailu:")))
        self.ed_body = QPlainTextEdit(
            f"Dobrý den,\n\nv příloze zasílám {word}.\n\nS pozdravem"
        )
        self.ed_body.setMinimumHeight(160)
        outer.addWidget(self.ed_body, stretch=1)

        row = QHBoxLayout()
        btn_settings = QPushButton(tr("⚙ Nastavení e-mailu…"))
        btn_settings.clicked.connect(self._open_settings)
        btn_cancel = QPushButton(tr("Zrušit"))
        btn_cancel.clicked.connect(self.reject)
        self.btn_send = QPushButton(tr("✉ Odeslat…"))
        f = self.btn_send.font()
        f.setBold(True)
        self.btn_send.setFont(f)
        self.btn_send.setDefault(True)
        self.btn_send.clicked.connect(self._send)
        row.addWidget(btn_settings)
        row.addStretch()
        row.addWidget(btn_cancel)
        row.addWidget(self.btn_send)
        outer.addLayout(row)

    def _open_settings(self) -> None:
        from .email_settings_dialog import EmailSettingsDialog

        if self.profile_manager is None:
            return
        if EmailSettingsDialog(self.profile_manager, self).exec() == QDialog.DialogCode.Accepted:
            profile = self.profile_manager.active
            self._user_email = (profile.user_email if profile else "") or ""
            self.lbl_from.setText(self._user_email or "— (doplň v Nastavení e-mailu)")

    def _send(self) -> None:
        if not self._user_email:
            QMessageBox.warning(
                self, tr("Chybí e-mail"),
                tr("Nemáš vyplněný vlastní e-mail. Otevři „⚙ Nastavení e-mailu…“."),
            )
            return
        recipient = self.ed_to.text().strip()
        if not recipient:
            QMessageBox.warning(self, tr("Chybí příjemce"), tr("Zadej e-mail příjemce."))
            return
        missing = [p.name for p in self.file_paths if not p.is_file()]
        if missing:
            QMessageBox.warning(
                self, tr("Soubor"), "Neexistují soubory:\n" + "\n".join(missing)
            )
            return

        profile = self.profile_manager.active
        draft = email_sender.MailDraft(
            from_addr=self._user_email,
            to=[recipient],
            subject=self.ed_subject.text().strip() or self.file_paths[0].name,
            body=self.ed_body.toPlainText(),
            attachments=list(self.file_paths),
        )
        confirm = QMessageBox.question(
            self, tr("Odeslat e-mail?"),
            f"Komu: {recipient}\nPředmět: {draft.subject}\n"
            f"Příloh: {len(self.file_paths)}\n\nOdeslat nyní?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        smtp = profile.smtp
        login_name = (smtp.username or self._user_email).strip()
        password, ok = QInputDialog.getText(
            self, "Heslo k e-mailu",
            f"Heslo pro {login_name}\n(neuloží se, použije se jen k odeslání):",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            email_sender.send_via_smtp(smtp, password, draft)
        except email_sender.EmailError as exc:
            QApplication.restoreOverrideCursor()
            self._offer_eml_fallback(draft, str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, tr("Odeslání"), f"Neočekávaná chyba:\n{exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        QMessageBox.information(self, tr("Odesláno"), f"Soubor byl odeslán na {recipient}.")
        self.accept()

    def _offer_eml_fallback(self, draft: email_sender.MailDraft, reason: str) -> None:
        choice = QMessageBox.question(
            self, tr("Odeslání přes SMTP selhalo"),
            f"{reason}\n\nVytvořit hotový e-mail a otevřít ho v mailovém klientovi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return
        try:
            safe = "".join(c for c in draft.to[0] if c.isalnum()) or "soubor"
            target = Path(tempfile.gettempdir()) / f"mail_{safe}.eml"
            email_sender.save_as_eml(draft, target)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, tr("Chyba"), f"Nepodařilo se vytvořit .eml:\n{exc}")
            return
        _open_path(target)
        QMessageBox.information(
            self, tr("Otevřeno v mailu"),
            tr("Otevřel jsem připravený e-mail v tvém mailovém klientovi."),
        )
        self.accept()
