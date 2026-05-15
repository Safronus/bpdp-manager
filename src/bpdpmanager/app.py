from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .services import ThesisService
from .storage import JsonRepository
from .ui import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("BPDPManager")
    app.setOrganizationName("safronus")

    repo = JsonRepository()
    service = ThesisService(repo)

    window = MainWindow(service)
    window.show()
    return app.exec()
