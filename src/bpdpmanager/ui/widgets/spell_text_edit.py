"""QPlainTextEdit s kontrolou pravopisu (čeština).

- neznámá slova se **podtrhnou** (červené vlnovkové podtržení),
- pravý klik na podtržené slovo nabídne **návrhy** oprav (uživatel vybere —
  žádná autokorekce).

Když není kontrola pravopisu k dispozici (chybí spylls / slovník), widget se
chová jako obyčejný editor (nic se nepodtrhává).
"""

from __future__ import annotations

import re

from PySide6.QtGui import (
    QAction,
    QColor,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import QPlainTextEdit

from ...services import spellcheck

# Slova = sekvence písmen (vč. diakritiky), min. 2 znaky; čísla/podtržítka ne.
_WORD_RE = re.compile(r"[^\W\d_]{2,}", re.UNICODE)


class _SpellHighlighter(QSyntaxHighlighter):
    """Podtrhne slova, která slovník nezná."""

    def __init__(self, document) -> None:
        super().__init__(document)
        self._fmt = QTextCharFormat()
        self._fmt.setUnderlineColor(QColor("#e53935"))
        self._fmt.setUnderlineStyle(
            QTextCharFormat.UnderlineStyle.SpellCheckUnderline
        )

    def highlightBlock(self, text: str) -> None:  # noqa: N802 (Qt API)
        if not spellcheck.is_available():
            return
        for m in _WORD_RE.finditer(text):
            word = m.group()
            if not spellcheck.check_word(word):
                self.setFormat(m.start(), len(word), self._fmt)


class SpellCheckEdit(QPlainTextEdit):
    """Editor s českou kontrolou pravopisu (podtržení + návrhy v kontext. menu)."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self._highlighter = _SpellHighlighter(self.document())

    def contextMenuEvent(self, event) -> None:  # noqa: N802 (Qt API)
        menu = self.createStandardContextMenu()
        if spellcheck.is_available():
            cursor = self.cursorForPosition(event.pos())
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            word = cursor.selectedText()
            if word and not spellcheck.check_word(word):
                start, end = cursor.selectionStart(), cursor.selectionEnd()
                first = menu.actions()[0] if menu.actions() else None
                suggestions = spellcheck.suggest(word)
                if suggestions:
                    for s in suggestions:
                        act = QAction(s, menu)
                        f = act.font()
                        f.setBold(True)
                        act.setFont(f)
                        act.triggered.connect(
                            lambda _c=False, a=start, b=end, repl=s:
                            self._replace_range(a, b, repl)
                        )
                        menu.insertAction(first, act)
                else:
                    none_act = QAction("(žádné návrhy)", menu)
                    none_act.setEnabled(False)
                    menu.insertAction(first, none_act)
                if first is not None:
                    menu.insertSeparator(first)
        menu.exec(event.globalPos())

    def _replace_range(self, start: int, end: int, replacement: str) -> None:
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(replacement)
