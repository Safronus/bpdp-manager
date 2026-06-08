"""Dialog „Tisk posudků přes MyQ" — odeslání PDF posudků do tiskové fronty.

Uživatel vybere z **aktuálně vedených** a **aktuálně oponovaných** prací ty,
jejichž PDF posudek chce vytisknout, zadá přihlašovací jméno + PIN (nikam se
neukládají) a odešle je na myq.utb.cz. Síťová komunikace běží ve vlákně, ať
neblokuje UI; na konci se zobrazí souhrn.

Výběr je rozdělen na **K tisku (nevytištěné)** — předzaškrtnuté — a **Již
vytištěné** (samostatný seznam, nezaškrtnuté) pro případný opětovný tisk.
Po úspěšném odeslání se dialog zeptá, zda odeslané rovnou označit jako
vytištěné.

Konektor je úmyslně izolovaný (``services/myq_client.py`` + tento dialog +
jediné napojení v toolbaru), aby šel snadno odebrat nebo rozšířit o další
způsoby tisku.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
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
_ROLE_KIND = Qt.ItemDataRole.UserRole + 3      # "supervised" | "opposing"
_ROLE_ID = Qt.ItemDataRole.UserRole + 4


class _PrintWorker(QThread):
    """Přihlásí se do MyQ a postupně nahraje vybraná PDF."""

    progress = Signal(int, int, str)        # hotovo, celkem, aktuální jméno
    done = Signal(list)                     # [(ok: bool, error: str)] dle pořadí jobs
    failed = Signal(str)                    # fatální chyba (např. přihlášení)

    def __init__(self, username: str, pin: str,
                 jobs: list[tuple[str, Path]], *, verify_tls: bool = True) -> None:
        super().__init__()
        self._username = username
        self._pin = pin
        self._jobs = jobs
        self._verify_tls = verify_tls

    def run(self) -> None:  # běží ve vlákně
        from ..services.myq_client import MyQClient, MyQError

        client = MyQClient(verify_tls=self._verify_tls)
        try:
            client.login(self._username, self._pin)
        except MyQError as exc:
            self.failed.emit(str(exc))
            return

        results: list[tuple[bool, str]] = []
        total = len(self._jobs)
        for i, (name, pdf) in enumerate(self._jobs, start=1):
            self.progress.emit(i, total, name)
            try:
                client.upload(pdf)
                results.append((True, ""))
            except MyQError as exc:
                results.append((False, str(exc)))
        self.done.emit(results)


class MyQPrintDialog(QDialog):
    """Výběr posudků + přihlášení + odeslání na tisk MyQ."""

    data_changed = Signal()  # po označení prací jako vytištěné

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self._worker: _PrintWorker | None = None
        self._jobs: list[tuple[str, Path]] = []
        self.setWindowTitle("Tisk posudků přes MyQ")
        self.setMinimumSize(640, 560)

        outer = QVBoxLayout(self)

        intro = QLabel(
            "Vyber posudky k tisku, zadej přihlašovací jméno a PIN do MyQ "
            "(<b>nikam se neukládají</b>) a odešli je do tiskové fronty na "
            "myq.utb.cz. Tisknou se <b>oboustranně</b>. Předzaškrtnuté jsou "
            "posudky, které ještě nebyly vytištěné."
        )
        intro.setWordWrap(True)
        outer.addWidget(intro)

        # ── strom výběru prací ────────────────────────────────────────────
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Práce", "Posudek"])
        self.tree.setRootIsDecorated(True)
        hdr = self.tree.header()
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
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

        # TLS ověření — MyQ server někdy posílá certifikát, který Python neumí
        # ověřit (neúplný řetězec / interní univerzitní CA). Pak je třeba ho
        # odznačit. Default zapnuto (bezpečně).
        self.cb_verify = QCheckBox("Ověřit TLS certifikát serveru")
        self.cb_verify.setChecked(True)
        self.cb_verify.setToolTip(
            "Když tisk hlásí chybu certifikátu (CERTIFICATE_VERIFY_FAILED), "
            "odznač — MyQ je interní univerzitní server, jen jeho certifikát "
            "Python neumí ověřit. Vypnutím se na něj připojíš bez ověření."
        )
        outer.addWidget(self.cb_verify)

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

        self._fit_width_to_content()

    # ── sběr tisknutelných posudků ────────────────────────────────────────
    def _printable_supervised(self) -> list[dict]:
        out: list[dict] = []
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
            out.append({
                "name": name, "pdf": pdf, "kind": "supervised", "id": t.id,
                "role": "posudek vedoucího",
                "printed": t.supervisor_review_printed_at is not None,
            })
        return out

    def _printable_opposing(self) -> list[dict]:
        out: list[dict] = []
        year = self.service.current_academic_year()
        for op in self.service.list_opposing_theses():
            if op.academic_year != year:
                continue
            pdf = self.service.current_opponent_review_pdf(op)
            if pdf is None:
                continue
            name = op.student_full_name or "(neuvedený student)"
            out.append({
                "name": name, "pdf": pdf, "kind": "opposing", "id": op.id,
                "role": "posudek oponenta",
                "printed": op.opponent_review_printed_at is not None,
            })
        return out

    def _all_items(self) -> list[dict]:
        items = self._printable_supervised() + self._printable_opposing()
        items.sort(key=lambda it: it["name"].lower())
        return items

    @staticmethod
    def _make_header(text: str, *, bold: bool) -> QTreeWidgetItem:
        item = QTreeWidgetItem([text, ""])
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
        f = item.font(0)
        f.setBold(bold)
        item.setFont(0, f)
        return item

    def _make_leaf(self, it: dict, *, checked: bool) -> QTreeWidgetItem:
        leaf = QTreeWidgetItem([it["name"], it["role"]])
        leaf.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        leaf.setCheckState(
            0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        )
        leaf.setData(0, _ROLE_PDF, str(it["pdf"]))
        leaf.setData(0, _ROLE_NAME, it["name"])
        leaf.setData(0, _ROLE_KIND, it["kind"])
        leaf.setData(0, _ROLE_ID, it["id"])
        return leaf

    def _add_group(self, title: str, items: list[dict], *, checked: bool) -> None:
        group = self._make_header(f"{title}  ({len(items)})", bold=True)
        self.tree.addTopLevelItem(group)
        if not items:
            empty = QTreeWidgetItem(["(žádné)", ""])
            empty.setFlags(Qt.ItemFlag.ItemIsEnabled)
            empty.setForeground(0, Qt.GlobalColor.gray)
            group.addChild(empty)
            group.setExpanded(True)
            return
        # Podskupiny podle typu posudku (vedoucího / oponenta).
        for kind, sub_title in (
            ("supervised", "🎓 Posudky vedoucího"),
            ("opposing", "🧐 Posudky oponenta"),
        ):
            sub_items = [it for it in items if it["kind"] == kind]
            if not sub_items:
                continue
            sub = self._make_header(f"{sub_title}  ({len(sub_items)})", bold=False)
            group.addChild(sub)
            for it in sub_items:
                sub.addChild(self._make_leaf(it, checked=checked))
            sub.setExpanded(True)
        group.setExpanded(True)

    def _populate_tree(self) -> None:
        self.tree.clear()
        items = self._all_items()
        not_printed = [it for it in items if not it["printed"]]
        printed = [it for it in items if it["printed"]]
        # Nevytištěné — předzaškrtnuté (výchozí nabídka k tisku).
        self._add_group("🖨 K tisku — nevytištěné", not_printed, checked=True)
        # Již vytištěné — samostatný seznam, nezaškrtnuté (volitelný 2. tisk).
        self._add_group(
            "✓ Již vytištěné (pro opětovný tisk)", printed, checked=False
        )

    def _iter_leaves(self):
        def walk(item):
            for i in range(item.childCount()):
                child = item.child(i)
                if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    yield child
                yield from walk(child)

        yield from walk(self.tree.invisibleRootItem())

    def _set_all_checked(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for leaf in self._iter_leaves():
            leaf.setCheckState(0, state)

    def _selected(self) -> list[dict]:
        out: list[dict] = []
        for leaf in self._iter_leaves():
            if leaf.checkState(0) == Qt.CheckState.Checked:
                out.append({
                    "name": leaf.data(0, _ROLE_NAME),
                    "pdf": Path(leaf.data(0, _ROLE_PDF)),
                    "kind": leaf.data(0, _ROLE_KIND),
                    "id": leaf.data(0, _ROLE_ID),
                })
        return out

    def _fit_width_to_content(self) -> None:
        """Šířka okna se odvíjí od obsahu sloupců (do limitu obrazovky)."""
        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)
        want = (
            self.tree.columnWidth(0) + self.tree.columnWidth(1)
            + 80  # okraje + scrollbar
        )
        screen = self.screen()
        avail = screen.availableGeometry().width() if screen else 1200
        width = max(self.minimumWidth(), min(want, int(avail * 0.9)))
        self.resize(width, self.height())

    # ── odeslání ──────────────────────────────────────────────────────────
    def _on_send(self) -> None:
        selected = self._selected()
        if not selected:
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

        self._jobs = selected
        self._set_busy(True)
        self.progress.setVisible(True)
        self.progress.setRange(0, len(selected))
        self.progress.setValue(0)
        self.status.setText("Přihlašuji se do MyQ…")

        worker_jobs = [(it["name"], it["pdf"]) for it in selected]
        self._worker = _PrintWorker(
            user, pin, worker_jobs, verify_tls=self.cb_verify.isChecked()
        )
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
        jobs = self._jobs
        ok_jobs = [jobs[i] for i, (good, _e) in enumerate(results) if good]
        bad = [
            (jobs[i]["name"], e)
            for i, (good, e) in enumerate(results) if not good
        ]
        lines = [f"✅ Odesláno na tisk: {len(ok_jobs)}"]
        if bad:
            lines.append("")
            lines.append(f"⚠ Nepodařilo se: {len(bad)}")
            lines += [f"   • {n} — {e}" for n, e in bad]
        self.status.setText(f"Hotovo — odesláno {len(ok_jobs)} z {len(results)}.")
        QMessageBox.information(self, "Souhrn tisku", "\n".join(lines))

        # Po úspěšném odeslání nabídni označení jako „vytištěno".
        if ok_jobs:
            ans = QMessageBox.question(
                self, "Označit jako vytištěné?",
                f"Označit {len(ok_jobs)} odeslaných posudků jako vytištěné?\n\n"
                "(Posudek se přesune do „Již vytištěné“. Lze kdykoli vrátit "
                "přes pravý klik na práci v seznamu.)",
            )
            if ans == QMessageBox.StandardButton.Yes:
                self._mark_printed(ok_jobs)

    def _mark_printed(self, jobs: list[dict]) -> None:
        for it in jobs:
            if it["kind"] == "supervised":
                self.service.set_supervisor_review_printed(it["id"], True)
            else:
                self.service.set_opponent_review_printed(it["id"], True)
        self._populate_tree()
        self.data_changed.emit()

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
