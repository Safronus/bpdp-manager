from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from ...models.enums import ThesisStatus


class StatusBadge(QLabel):
    """Malý barevný štítek pro stav práce."""

    def __init__(self, status: ThesisStatus, parent=None) -> None:
        super().__init__(status.label, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"""
            QLabel {{
                background-color: {status.color};
                color: white;
                font-weight: bold;
                padding: 2px 8px;
                border-radius: 8px;
            }}
            """
        )
