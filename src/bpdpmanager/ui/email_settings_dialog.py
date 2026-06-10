"""Správce nastavení odchozí pošty (SMTP) + e-mailu uživatele.

Samostatný dialog: e-mail odesílatele, SMTP server/port/zabezpečení a
**Test spojení** (vyzve heslo, přihlásí se, nahlásí výsledek). Heslo se nikde
neukládá. Výchozí hodnoty odpovídají UTB Office365.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ..i18n import tr
from ..models import SmtpConfig
from ..services import ProfileManager, email_sender

# Popisky zabezpečení ↔ hodnoty v SmtpConfig.security
_SECURITY_CHOICES = [
    ("STARTTLS (port 587)", "starttls"),
    ("SSL/TLS (port 465)", "ssl"),
    ("Bez šifrování (nedoporučeno)", "none"),
]


class EmailSettingsDialog(QDialog):
    """Nastavení e-mailu uživatele a SMTP serveru pro odesílání posudků."""

    def __init__(self, profile_manager: ProfileManager, parent=None) -> None:
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.setWindowTitle(tr("Nastavení e-mailu (SMTP)"))
        self.setMinimumWidth(560)

        profile = profile_manager.active
        smtp = profile.smtp if profile else SmtpConfig()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        title = QLabel(tr("✉ Nastavení e-mailu (SMTP)"))
        title.setStyleSheet("font-size:16px;font-weight:bold;")
        outer.addWidget(title)

        intro = QLabel(
            tr("E-mail a odchozí server pro odesílání posudků sekretářkám. "
            "Výchozí hodnoty jsou pro <b>UTB Office365</b> "
            "(<a href='https://www.utb.cz/cvt/office365-thunderbird-doc'>nastavení CVT UTB</a>). "
            "<b>Heslo se nikde neukládá</b> — zadáš ho při každém odeslání i testu.")
        )
        intro.setTextFormat(Qt.TextFormat.RichText)
        intro.setOpenExternalLinks(True)
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#888;")
        outer.addWidget(intro)

        form = QFormLayout()

        self.ed_email = QLineEdit(profile.user_email if profile else "")
        self.ed_email.setPlaceholderText(tr("např. prijmeni@utb.cz"))
        form.addRow(tr("Tvůj e-mail (odesílatel)"), self.ed_email)

        self.ed_host = QLineEdit(smtp.host)
        self.ed_host.setPlaceholderText("outlook.office365.com")
        form.addRow("SMTP server", self.ed_host)

        self.sp_port = QSpinBox()
        self.sp_port.setRange(1, 65535)
        self.sp_port.setValue(smtp.port)
        form.addRow("Port", self.sp_port)

        self.cb_security = QComboBox()
        for label, value in _SECURITY_CHOICES:
            self.cb_security.addItem(label, value)
        idx = self.cb_security.findData(smtp.security)
        if idx >= 0:
            self.cb_security.setCurrentIndex(idx)
        self.cb_security.currentIndexChanged.connect(self._on_security_changed)
        form.addRow(tr("Zabezpečení"), self.cb_security)

        self.ed_username = QLineEdit(smtp.username)
        self.ed_username.setPlaceholderText(tr("(prázdné = stejné jako e-mail)"))
        form.addRow(tr("Přihlašovací jméno"), self.ed_username)

        outer.addLayout(form)

        # Test spojení
        test_row = QHBoxLayout()
        self.btn_test = QPushButton(tr("🔌 Test spojení"))
        self.btn_test.setToolTip(
            tr("Připojí se k serveru a přihlásí (vyzve heslo) — bez odeslání e-mailu.")
        )
        self.btn_test.clicked.connect(self._test_connection)
        self.lbl_test = QLabel("")
        self.lbl_test.setWordWrap(True)
        test_row.addWidget(self.btn_test)
        test_row.addWidget(self.lbl_test, stretch=1)
        outer.addLayout(test_row)

        # Tlačítka
        row = QHBoxLayout()
        btn_cancel = QPushButton(tr("Zrušit"))
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton(tr("💾 Uložit"))
        btn_save.setDefault(True)
        f = btn_save.font()
        f.setBold(True)
        btn_save.setFont(f)
        btn_save.clicked.connect(self._save)
        row.addStretch()
        row.addWidget(btn_cancel)
        row.addWidget(btn_save)
        outer.addLayout(row)

    def _on_security_changed(self) -> None:
        """Při změně zabezpečení nabídni odpovídající výchozí port."""
        sec = self.cb_security.currentData()
        if sec == "ssl" and self.sp_port.value() in (587, 25):
            self.sp_port.setValue(465)
        elif sec == "starttls" and self.sp_port.value() in (465, 25):
            self.sp_port.setValue(587)

    def _current_config(self) -> tuple[str, SmtpConfig]:
        email = self.ed_email.text().strip()
        smtp = SmtpConfig(
            host=self.ed_host.text().strip() or "outlook.office365.com",
            port=self.sp_port.value(),
            security=self.cb_security.currentData() or "starttls",
            username=self.ed_username.text().strip(),
        )
        return email, smtp

    def _test_connection(self) -> None:
        email, smtp = self._current_config()
        if not email and not smtp.username:
            QMessageBox.warning(
                self, tr("Chybí e-mail"),
                tr("Zadej e-mail (nebo přihlašovací jméno) před testem spojení."),
            )
            return
        login_name = smtp.username or email
        password, ok = QInputDialog.getText(
            self,
            "Heslo k e-mailu",
            f"Heslo pro {login_name}\n(použije se jen k testu, neuloží se):",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return
        self.lbl_test.setText(tr("⏳ Testuji spojení…"))
        self.btn_test.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            email_sender.test_connection(smtp, email, password)
        except email_sender.EmailError as exc:
            self.lbl_test.setText(tr("❌ Spojení selhalo."))
            QMessageBox.warning(self, tr("Test spojení"), str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            self.lbl_test.setText(tr("❌ Neočekávaná chyba."))
            QMessageBox.critical(self, tr("Test spojení"), f"Neočekávaná chyba:\n{exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()
            self.btn_test.setEnabled(True)
        self.lbl_test.setStyleSheet("color:#2e7d32;")
        self.lbl_test.setText(tr("✓ Spojení i přihlášení v pořádku."))

    def _save(self) -> None:
        profile = self.profile_manager.active
        if profile is None:
            QMessageBox.warning(self, tr("Profil"), tr("Není aktivní žádný profil."))
            return
        email, smtp = self._current_config()
        try:
            self.profile_manager.set_user_email(profile.id, email)
            self.profile_manager.set_smtp_config(profile.id, smtp)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, tr("Uložení"), f"Nepodařilo se uložit:\n{exc}")
            return
        self.accept()
