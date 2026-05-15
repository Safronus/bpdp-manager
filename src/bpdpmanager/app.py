from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .services import ThesisService
from .storage import JsonRepository
from .ui import MainWindow


def _icon_path() -> Path | None:
    """Vrátí cestu k ikoně, pokud byla vygenerovaná, jinak None."""
    candidates = [
        Path(__file__).parent / "resources" / "icons" / "app_icon.png",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("BPDPManager")
    app.setApplicationDisplayName("BPDPManager")
    app.setOrganizationName("safronus")
    app.setOrganizationDomain("github.com/Safronus")

    icon_path = _icon_path()
    if icon_path is not None:
        icon = QIcon(str(icon_path))
        app.setWindowIcon(icon)

    repo = JsonRepository()
    service = ThesisService(repo)

    window = MainWindow(service)
    if icon_path is not None:
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    return app.exec()
