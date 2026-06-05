"""Okno nápovědy — renderuje ``resources/napoveda.md`` (jediný zdroj pravdy).

Markdown soubor je sdílený mezi aplikací (toto okno) a repozitářem
(README na něj odkazuje). Při změně funkcí se upravuje jen on.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from .. import __version__


def _napoveda_path() -> Path:
    """Cesta k markdown souboru nápovědy uvnitř balíčku."""
    # ui/help_dialog.py → ui → bpdpmanager → resources/napoveda.md
    return Path(__file__).resolve().parent.parent / "resources" / "napoveda.md"


def _extract_section(md: str, heading_prefix: str) -> str:
    """Vrátí markdown jedné sekce (od ``## …`` po další ``## `` na začátku řádku).

    ``heading_prefix`` je text za „## " (např. „🚀 Začínáme"). Pokud sekce
    není nalezena, vrátí prázdný string.
    """
    lines = md.splitlines()
    out: list[str] = []
    capturing = False
    for line in lines:
        if line.startswith("## "):
            if capturing:
                break  # narazili jsme na další sekci
            if heading_prefix in line:
                capturing = True
                out.append(line)
                continue
        if capturing:
            out.append(line)
    return "\n".join(out).strip()


class HelpDialog(QDialog):
    """Zobrazí nápovědu z markdown souboru s vyhledáváním."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Nápověda — BPDPManager {__version__}")
        self.setMinimumSize(820, 720)
        self.resize(900, 860)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(8)

        # ── Hledání ─────────────────────────────────────────────────────
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("🔍 Hledat:"))
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText("napiš výraz a stiskni Enter…")
        self.ed_search.returnPressed.connect(self._find_next)
        search_row.addWidget(self.ed_search, stretch=1)
        btn_next = QPushButton("Další")
        btn_next.clicked.connect(self._find_next)
        search_row.addWidget(btn_next)
        outer.addLayout(search_row)

        # ── Obsah ───────────────────────────────────────────────────────
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        outer.addWidget(self.view, stretch=1)
        self._load_content()

        # ── Tlačítka ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_top = QPushButton("↑ Nahoru")
        btn_top.clicked.connect(
            lambda: self.view.verticalScrollBar().setValue(0)
        )
        btn_close = QPushButton("Zavřít")
        btn_close.setDefault(True)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_top)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        outer.addLayout(btn_row)

    def _load_content(self) -> None:
        path = _napoveda_path()
        try:
            md = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.view.setPlainText(
                f"Nápovědu se nepodařilo načíst ({path}):\n{exc}"
            )
            return
        # QTextBrowser umí CommonMark přes setMarkdown (Qt 5.14+).
        self.view.setMarkdown(md)

    def _find_next(self) -> None:
        text = self.ed_search.text().strip()
        if not text:
            return
        # find() hledá od aktuální pozice kurzoru dál; když nenajde,
        # vrátí se na začátek a zkusí znovu (wrap-around).
        if not self.view.find(text):
            cursor = self.view.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            self.view.setTextCursor(cursor)
            self.view.find(text)


class FirstRunDialog(QDialog):
    """Uvítací tutorial po prvním nastavení — sekce „Začínáme" z nápovědy.

    Single-source: text bere ze stejného ``napoveda.md`` jako plná nápověda.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.open_full_help = False  # nastaví se, když uživatel chce plnou nápovědu
        self.dont_show_again = True  # default: po zavření už neukazovat

        self.setWindowTitle("Vítej v BPDPManageru — Začínáme")
        self.setMinimumSize(720, 640)
        self.resize(780, 720)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        header = QLabel("👋 Vítej! Pár kroků, než začneš")
        header.setStyleSheet("font-size:16px;font-weight:bold;")
        outer.addWidget(header)

        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        outer.addWidget(self.view, stretch=1)
        self._load_getting_started()

        self.chk_dont_show = QCheckBox("Příště nezobrazovat tento průvodce")
        self.chk_dont_show.setChecked(True)
        outer.addWidget(self.chk_dont_show)

        btn_row = QHBoxLayout()
        btn_help = QPushButton("📖 Otevřít plnou nápovědu")
        btn_help.clicked.connect(self._on_open_help)
        btn_ok = QPushButton("Rozumím, jdeme na to")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._on_ok)
        btn_row.addWidget(btn_help)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        outer.addLayout(btn_row)

    def _load_getting_started(self) -> None:
        try:
            md = _napoveda_path().read_text(encoding="utf-8")
        except OSError:
            self.view.setPlainText("Průvodce se nepodařilo načíst.")
            return
        section = _extract_section(md, "Začínáme")
        self.view.setMarkdown(section or md)

    def _on_open_help(self) -> None:
        self.open_full_help = True
        self.dont_show_again = self.chk_dont_show.isChecked()
        self.accept()

    def _on_ok(self) -> None:
        self.dont_show_again = self.chk_dont_show.isChecked()
        self.accept()
