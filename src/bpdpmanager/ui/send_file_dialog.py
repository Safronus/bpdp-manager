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
        self, profile_manager, file_path: Path, *, default_subject: str = "", parent=None
    ) -> None:
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.file_path = Path(file_path)

        self.setWindowTitle("Odeslat soubor e-mailem")
        self.setMinimumWidth(560)

        profile = profile_manager.active if profile_manager else None
        self._user_email = (profile.user_email if profile else "") or ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        title = QLabel("✉ Odeslat soubor e-mailem")
        title.setStyleSheet("font-size:16px;font-weight:bold;")
        outer.addWidget(title)

        form = QFormLayout()
        self.lbl_from = QLabel(self._user_email or "— (doplň v Nastavení e-mailu)")
        self.lbl_from.setStyleSheet("color:#888;")
        form.addRow("Odesílatel", self.lbl_from)

        self.ed_to = QLineEdit()
        self.ed_to.setPlaceholderText("příjemce@example.cz")
        form.addRow("Příjemce", self.ed_to)

        self.ed_subject = QLineEdit(default_subject or self.file_path.name)
        form.addRow("Předmět", self.ed_subject)

        self.lbl_attach = QLabel(f"📎 {self.file_path.name}")
        form.addRow("Příloha", self.lbl_attach)
        outer.addLayout(form)

        outer.addWidget(QLabel("Text e-mailu:"))
        self.ed_body = QPlainTextEdit("Dobrý den,\n\nv příloze zasílám soubor.\n\nS pozdravem")
        self.ed_body.setMinimumHeight(160)
        outer.addWidget(self.ed_body, stretch=1)

        row = QHBoxLayout()
        btn_settings = QPushButton("⚙ Nastavení e-mailu…")
        btn_settings.clicked.connect(self._open_settings)
        btn_cancel = QPushButton("Zrušit")
        btn_cancel.clicked.connect(self.reject)
        self.btn_send = QPushButton("✉ Odeslat…")
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
                self, "Chybí e-mail",
                "Nemáš vyplněný vlastní e-mail. Otevři „⚙ Nastavení e-mailu…“.",
            )
            return
        recipient = self.ed_to.text().strip()
        if not recipient:
            QMessageBox.warning(self, "Chybí příjemce", "Zadej e-mail příjemce.")
            return
        if not self.file_path.is_file():
            QMessageBox.warning(self, "Soubor", f"Soubor neexistuje:\n{self.file_path}")
            return

        profile = self.profile_manager.active
        draft = email_sender.MailDraft(
            from_addr=self._user_email,
            to=[recipient],
            subject=self.ed_subject.text().strip() or self.file_path.name,
            body=self.ed_body.toPlainText(),
            attachments=[self.file_path],
        )
        confirm = QMessageBox.question(
            self, "Odeslat e-mail?",
            f"Komu: {recipient}\nPředmět: {draft.subject}\nPříloha: {self.file_path.name}\n\n"
            "Odeslat nyní?",
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
            QMessageBox.critical(self, "Odeslání", f"Neočekávaná chyba:\n{exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        QMessageBox.information(self, "Odesláno", f"Soubor byl odeslán na {recipient}.")
        self.accept()

    def _offer_eml_fallback(self, draft: email_sender.MailDraft, reason: str) -> None:
        choice = QMessageBox.question(
            self, "Odeslání přes SMTP selhalo",
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
            QMessageBox.critical(self, "Chyba", f"Nepodařilo se vytvořit .eml:\n{exc}")
            return
        _open_path(target)
        QMessageBox.information(
            self, "Otevřeno v mailu",
            "Otevřel jsem připravený e-mail v tvém mailovém klientovi.",
        )
        self.accept()
