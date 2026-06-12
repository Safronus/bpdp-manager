"""Sbalitelný spodní panel s detailem práce (záložky se seznamy prací).

Chování (stejné pro vedené, budoucí, historické, „Vše" i oponované):

- **Bez vybrané práce je panel celý skrytý** — seznam prací má celou výšku
  záložky (žádný prázdný prostor s hláškou).
- **S vybranou prací** se nad detailem ukáže tenká lišta se šipkou; kliknutím
  se detail **sbalí dolů** (zůstane jen lišta) a seznam získá místo — hodí
  se při listování dlouhými seznamy (Historie, Vše). Dalším kliknutím se
  detail zase rozbalí. Stav sbalení se drží i při přepínání prací.

Panel se vkládá do vertikálního ``QSplitter`` místo samotného detailu;
velikosti splitteru si při sbalení/rozbalení sám uloží a obnoví.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy, QSplitter, QToolButton, QVBoxLayout, QWidget

from ..i18n import tr


class CollapsibleDetailPane(QWidget):
    """Obal detailu: skrytý bez výběru, ručně sbalitelný dolů na lištu."""

    def __init__(self, detail: QWidget, parent=None, *,
                 title: str = "Detail práce") -> None:
        super().__init__(parent)
        self.detail = detail
        self._collapsed = False
        self._saved_sizes: list[int] | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.btn_toggle = QToolButton()
        self.btn_toggle.setText(tr(title))
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setChecked(True)
        self.btn_toggle.setArrowType(Qt.ArrowType.DownArrow)
        self.btn_toggle.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.btn_toggle.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.btn_toggle.setToolTip(tr(
            "Sbalí/rozbalí detail práce — sbalený detail uvolní místo "
            "seznamu prací."
        ))
        self.btn_toggle.setStyleSheet(
            "QToolButton { border: none; padding: 3px 8px; text-align: left;"
            " color: #888; font-weight: bold; }"
            "QToolButton:hover { color: #555; }"
        )
        self.btn_toggle.toggled.connect(self._on_toggled)
        lay.addWidget(self.btn_toggle)
        lay.addWidget(detail, stretch=1)

        # Start bez výběru → panel je celý skrytý (zobrazí ho až výběr práce).
        self.hide()

    # --- API pro záložky -----------------------------------------------------

    def set_has_selection(self, has: bool) -> None:
        """Zobrazí/skryje celý panel podle toho, jestli je vybraná práce."""
        if has and not self.isVisible():
            self.show()
            # Respektuj případné dřívější sbalení uživatelem.
            self.detail.setVisible(not self._collapsed)
        elif not has:
            self.hide()

    @property
    def collapsed(self) -> bool:
        return self._collapsed

    # --- vnitřnosti -----------------------------------------------------------

    def _splitter(self) -> QSplitter | None:
        w = self.parentWidget()
        return w if isinstance(w, QSplitter) else None

    def _on_toggled(self, expanded: bool) -> None:
        self._collapsed = not expanded
        self.detail.setVisible(expanded)
        self.btn_toggle.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        sp = self._splitter()
        if sp is None:
            return
        if not expanded:
            self._saved_sizes = sp.sizes()
            bar = self.btn_toggle.sizeHint().height()
            total = sum(sp.sizes()) or (bar + 1)
            sp.setSizes([max(1, total - bar), bar])
        elif self._saved_sizes:
            sp.setSizes(self._saved_sizes)
