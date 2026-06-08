"""Dialog „Tisk posudků přes MyQ" — odeslání PDF posudků do tiskové fronty.

Uživatel vybere z **aktuálně vedených** a **aktuálně oponovaných** prací ty,
jejichž PDF posudek chce vytisknout, zadá přihlašovací jméno + PIN (nikam se
neukládají) a odešle je na myq.utb.cz. Síťová komunikace běží ve vlákně, ať
neblokuje UI; na konci se zobrazí souhrn.

Konektor je úmyslně izolovaný (``services/myq_client.py`` + tento dialog +
jediné napojení v toolbaru), aby šel snadno odebrat nebo rozšířit o další
způsoby tisku.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from ..models.enums import STATUSES_CURRENT
from ..services import ThesisService

_ROLE_PDF = Qt.ItemDataRole.UserRole + 1
_ROLE_NAME = Qt.ItemDataRole.UserRole + 2


class _PrintWorker(QThread):
    """Přihlásí se do MyQ a postupně nahraje vybraná PDF."""

    progress = Signal(int, int, str)        # hotovo, celkem, aktuální jméno
    done = Signal(list)                     # [(name, ok: bool, error: str)]
    failed = Signal(str)                    # fatální chyba (např. přihlášení)

    def __init__(self, username: str, pin: str,
                 jobs: list[tuple[str, Path]]) -> None:
        super().__init__()
        self._username = username
        self._pin = pin
        self._jobs = jobs

    def run(self) -> None:  # běží ve vlákně
        from ..services.myq_client import MyQClient, MyQError

        client = MyQClient()
        try:
            client.login(self._username, self._pin)
        except MyQError as exc:
            self.failed.emit(str(exc))
            return

        results: list[tuple[str, bool, str]] = []
        total = len(self._jobs)
        for i, (name, pdf) in enumerate(self._jobs, start=1):
            self.progress.emit(i, total, name)
            try:
                client.upload(pdf)
                results.append((name, True, ""))
            except MyQError as exc:
                results.append((name, False, str(exc)))
        self.done.emit(results)


class MyQPrintDialog(QDialog):
    """Výběr posudků + přihlášení + odeslání na tisk MyQ."""

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self._worker: _PrintWorker | None = None
        self.setWindowTitle("Tisk posudků přes MyQ")
        self.setMinimumSize(560, 560)

        outer = QVBoxLayout(self)

        intro = QLabel(
            "Vyber posudky k tisku, zadej přihlašovací jméno a PIN do MyQ "
            "(<b>nikam se neukládají</b>) a odešli je do tiskové fronty na "
            "myq.utb.cz. Tisknou se <b>oboustranně</b>."
        )
        intro.setWordWrap(True)
        outer.addWidget(intro)

        # ── strom výběru prací ────────────────────────────────────────────
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Práce", "Posudek"])
        self.tree.setRootIsDecorated(True)
        self.tree.header().setStretchLastSection(False)
        self.tree.setColumnWidth(0, 360)
        outer.addWidget(self.tree, stretch=1)
        self._populate_tree()

        sel_row = QHBoxLayout()
        btn_all = QPushButton("Vybrat vše")
        btn_none = QPushButton("Zrušit vše")
        btn_all.clicked.connect(lambda: self._set_all_checked(True))
        btn_none.clicked.connect(lambda: self._set_all_checked(False))
        sel_row.addWidget(btn_all)
        sel_row.addWidget(btn_none)
        sel_row.addStretch(1)
        outer.addLayout(sel_row)

        # ── přihlašovací údaje ────────────────────────────────────────────
        cred = QHBoxLayout()
        cred.addWidget(QLabel("Jméno:"))
        self.ed_user = QLineEdit()
        self.ed_user.setPlaceholderText("uživatelské jméno MyQ")
        cred.addWidget(self.ed_user, stretch=1)
        cred.addWidget(QLabel("PIN:"))
        self.ed_pin = QLineEdit()
        self.ed_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_pin.setPlaceholderText("PIN")
        self.ed_pin.setMaximumWidth(120)
        cred.addWidget(self.ed_pin)
        outer.addLayout(cred)

        # ── průběh ────────────────────────────────────────────────────────
        self.status = QLabel("")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        outer.addWidget(self.progress)

        # ── tlačítka ──────────────────────────────────────────────────────
        self.buttons = QDialogButtonBox()
        self.btn_send = self.buttons.addButton(
            "🖨 Odeslat na tisk", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.btn_close = self.buttons.addButton(QDialogButtonBox.StandardButton.Close)
        self.btn_send.clicked.connect(self._on_send)
        self.btn_close.clicked.connect(self.reject)
        outer.addWidget(self.buttons)

    # ── naplnění stromu ───────────────────────────────────────────────────
    def _printable_supervised(self) -> list[tuple[str, Path]]:
        out: list[tuple[str, Path]] = []
        for t in self.service.list_theses():
            if t.status not in STATUSES_CURRENT:
                continue
            pdf = self.service.current_supervisor_review_pdf(t)
            if pdf is None:
                continue
            student = (
                self.service.get_student(t.student_id) if t.student_id else None
            )
            name = student.full_name if student else t.display_title
            out.append((name, pdf))
        out.sort(key=lambda x: x[0].lower())
        return out

    def _printable_opposing(self) -> list[tuple[str, Path]]:
        out: list[tuple[str, Path]] = []
        year = self.service.current_academic_year()
        for op in self.service.list_opposing_theses():
            if op.academic_year != year:
                continue
            pdf = self.service.current_opponent_review_pdf(op)
            if pdf is None:
                continue
            name = op.student_full_name or "(neuvedený student)"
            out.append((name, pdf))
        out.sort(key=lambda x: x[0].lower())
        return out

    def _add_group(self, title: str, jobs: list[tuple[str, Path]],
                   role_label: str) -> None:
        group = QTreeWidgetItem([f"{title}  ({len(jobs)})", ""])
        group.setFlags(group.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
        f = group.font(0)
        f.setBold(True)
        group.setFont(0, f)
        self.tree.addTopLevelItem(group)
        if not jobs:
            empty = QTreeWidgetItem(["(žádný hotový PDF posudek)", ""])
            empty.setFlags(Qt.ItemFlag.ItemIsEnabled)
            empty.setForeground(0, Qt.GlobalColor.gray)
            group.addChild(empty)
        for name, pdf in jobs:
            leaf = QTreeWidgetItem([name, role_label])
            leaf.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
            )
            leaf.setCheckState(0, Qt.CheckState.Unchecked)
            leaf.setData(0, _ROLE_PDF, str(pdf))
            leaf.setData(0, _ROLE_NAME, name)
            group.addChild(leaf)
        group.setExpanded(True)

    def _populate_tree(self) -> None:
        self.tree.clear()
        self._add_group(
            "🎓 Aktuálně vedené práce", self._printable_supervised(),
            "posudek vedoucího",
        )
        self._add_group(
            "🧐 Aktuálně oponované práce", self._printable_opposing(),
            "posudek oponenta",
        )

    def _iter_leaves(self):
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            grp = root.child(i)
            for j in range(grp.childCount()):
                leaf = grp.child(j)
                if leaf.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    yield leaf

    def _set_all_checked(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for leaf in self._iter_leaves():
            leaf.setCheckState(0, state)

    def _selected_jobs(self) -> list[tuple[str, Path]]:
        jobs: list[tuple[str, Path]] = []
        for leaf in self._iter_leaves():
            if leaf.checkState(0) == Qt.CheckState.Checked:
                jobs.append((leaf.data(0, _ROLE_NAME), Path(leaf.data(0, _ROLE_PDF))))
        return jobs

    # ── odeslání ──────────────────────────────────────────────────────────
    def _on_send(self) -> None:
        jobs = self._selected_jobs()
        if not jobs:
            QMessageBox.information(
                self, "Tisk posudků", "Nevybral jsi žádný posudek k tisku."
            )
            return
        user = self.ed_user.text().strip()
        pin = self.ed_pin.text().strip()
        if not user or not pin:
            QMessageBox.information(
                self, "Tisk posudků", "Zadej přihlašovací jméno i PIN do MyQ."
            )
            return

        self._set_busy(True)
        self.progress.setVisible(True)
        self.progress.setRange(0, len(jobs))
        self.progress.setValue(0)
        self.status.setText("Přihlašuji se do MyQ…")

        self._worker = _PrintWorker(user, pin, jobs)
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, done: int, total: int, name: str) -> None:
        self.progress.setValue(done - 1)
        self.status.setText(f"Odesílám {done}/{total}: {name}…")

    def _on_failed(self, message: str) -> None:
        self._set_busy(False)
        self.progress.setVisible(False)
        self.status.setText("")
        QMessageBox.warning(self, "Tisk posudků — chyba přihlášení", message)

    def _on_done(self, results: list) -> None:
        self._set_busy(False)
        self.progress.setValue(self.progress.maximum())
        ok = [n for (n, good, _e) in results if good]
        bad = [(n, e) for (n, good, e) in results if not good]
        lines = [f"✅ Odesláno na tisk: {len(ok)}"]
        if bad:
            lines.append("")
            lines.append(f"⚠ Nepodařilo se: {len(bad)}")
            lines += [f"   • {n} — {e}" for n, e in bad]
        self.status.setText(f"Hotovo — odesláno {len(ok)} z {len(results)}.")
        QMessageBox.information(self, "Souhrn tisku", "\n".join(lines))
        # Odeslané odškrtni, ať nejdou omylem znovu.
        sent = {n for n in ok}
        for leaf in self._iter_leaves():
            if leaf.data(0, _ROLE_NAME) in sent:
                leaf.setCheckState(0, Qt.CheckState.Unchecked)

    def _set_busy(self, busy: bool) -> None:
        self.btn_send.setEnabled(not busy)
        self.tree.setEnabled(not busy)
        self.ed_user.setEnabled(not busy)
        self.ed_pin.setEnabled(not busy)

    def reject(self) -> None:  # zabraň zavření během odesílání
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(
                self, "Tisk posudků",
                "Počkej, než doběhne odesílání na tisk.",
            )
            return
        super().reject()
