"""Malý dialog na zadání hesla pro šifrovaný export/import průběhu SZZ.

Export = ``confirm=True`` (heslo dvakrát, ať se nepřeklepneš — zapomenuté heslo
data neodemkne). Import = ``confirm=False`` (jedno pole). Heslo se nikam
neukládá, jen se vrátí volajícímu.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr


class _PasswordDialog(QDialog):
    def __init__(self, parent, title: str, prompt: str, confirm: bool) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(380)
        self._confirm = confirm
        self.password: str | None = None

        root = QVBoxLayout(self)
        lbl = QLabel(prompt)
        lbl.setWordWrap(True)
        root.addWidget(lbl)

        self.ed = QLineEdit()
        self.ed.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed.setPlaceholderText(tr("Heslo"))
        root.addWidget(self.ed)

        self.ed2: QLineEdit | None = None
        if confirm:
            self.ed2 = QLineEdit()
            self.ed2.setEchoMode(QLineEdit.EchoMode.Password)
            self.ed2.setPlaceholderText(tr("Heslo znovu"))
            root.addWidget(self.ed2)

        self.chk_show = QCheckBox(tr("Zobrazit heslo"))
        root.addWidget(self.chk_show)

        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color:#c62828;")
        self.lbl_err.setWordWrap(True)
        root.addWidget(self.lbl_err)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        root.addWidget(self.buttons)

        self.chk_show.toggled.connect(self._toggle_echo)
        self.ed.textChanged.connect(self._validate)
        if self.ed2 is not None:
            self.ed2.textChanged.connect(self._validate)
        self.buttons.accepted.connect(self._accept)
        self.buttons.rejected.connect(self.reject)
        self._validate()

    def _toggle_echo(self, show: bool) -> None:
        mode = (QLineEdit.EchoMode.Normal if show
                else QLineEdit.EchoMode.Password)
        self.ed.setEchoMode(mode)
        if self.ed2 is not None:
            self.ed2.setEchoMode(mode)

    def _validate(self) -> None:
        ok = bool(self.ed.text())
        if self._confirm and self.ed2 is not None:
            ok = ok and self.ed.text() == self.ed2.text()
        self.buttons.button(
            QDialogButtonBox.StandardButton.Ok).setEnabled(ok)
        if (self._confirm and self.ed2 is not None and self.ed2.text()
                and self.ed.text() != self.ed2.text()):
            self.lbl_err.setText(tr("Hesla se neshodují."))
        else:
            self.lbl_err.setText("")

    def _accept(self) -> None:
        self.password = self.ed.text()
        self.accept()


def ask_password(parent: QWidget | None, title: str, prompt: str,
                 *, confirm: bool = False) -> str | None:
    """Zeptá se na heslo; vrátí ho, nebo ``None`` při zrušení."""
    dlg = _PasswordDialog(parent, title, prompt, confirm)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        return dlg.password
    return None
