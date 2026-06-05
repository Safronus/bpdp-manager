"""Odeslání připravených posudků sekretářce e-mailem.

Režim ``role``:
- ``"supervisor"`` — posudky vedoucího u vedených prací (záložka *Aktuální*),
- ``"opponent"``  — oponentské posudky (záložka *Oponentské posudky*).

Tok: vyber sekretářku → podle jejích oborů se nabídnou práce, které mají
**hotové PDF** posudku (nezaslané jsou předzaškrtnuté, zaslané volitelně) →
editovatelný náhled předmětu a textu → Odeslat (SMTP), při selhání fallback
přes .eml otevřený v mailovém klientovi.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..services import ProfileManager, ThesisService, email_sender


@dataclass
class _ReviewItem:
    work_id: str
    type_code: str        # "BP" | "DP"
    student_name: str
    student_uni_id: str
    title: str
    obor: str
    pdf_path: Path
    sent_at_label: str    # "" když neodesláno, jinak datum


@dataclass
class _Secretary:
    name: str
    email: str
    obory: set[str]       # názvy oborů, které spravuje


def _open_path(path: Path) -> None:
    """Otevře soubor výchozí aplikací OS (mailový klient pro .eml)."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:  # noqa: BLE001
        pass


class SendReviewsDialog(QDialog):
    def __init__(
        self,
        service: ThesisService,
        profile_manager: ProfileManager,
        role: str,  # "supervisor" | "opponent"
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.profile_manager = profile_manager
        self.role = role
        self._items: list[_ReviewItem] = []
        self._row_items: list[tuple[_ReviewItem, QTableWidgetItem]] = []
        self._body_dirty = False  # uživatel ručně upravil text → neautoregeneruj

        what = "vedoucího" if role == "supervisor" else "oponenta"
        self.setWindowTitle(f"Odeslat posudky {what} sekretářce")
        self.setMinimumSize(860, 720)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        title = QLabel(f"✉ Odeslat posudky {what} sekretářce")
        title.setStyleSheet("font-size:16px;font-weight:bold;")
        outer.addWidget(title)

        # ── Sekretářka + volby ──────────────────────────────────────────────
        form = QFormLayout()
        self.cb_secretary = QComboBox()
        self.cb_secretary.currentIndexChanged.connect(self._on_secretary_changed)
        form.addRow("Sekretářka", self.cb_secretary)

        self.lbl_recipient = QLabel("—")
        self.lbl_recipient.setStyleSheet("color:#888;")
        form.addRow("Příjemce", self.lbl_recipient)

        profile = profile_manager.active
        self._user_email = (profile.user_email if profile else "") or ""
        self.chk_cc = QCheckBox(
            f"Kopie mně ({self._user_email})" if self._user_email else "Kopie mně"
        )
        self.chk_cc.setChecked(bool(self._user_email))
        self.chk_cc.setEnabled(bool(self._user_email))
        self.chk_cc.setToolTip(
            "Pošle kopii na tvůj e-mail, aby byla jistota, že se mail odeslal."
        )
        form.addRow("", self.chk_cc)

        self.chk_show_sent = QCheckBox("Zobrazit i už odeslané posudky")
        self.chk_show_sent.setChecked(False)
        self.chk_show_sent.stateChanged.connect(lambda _s: self._reload_table())
        form.addRow("", self.chk_show_sent)
        outer.addLayout(form)

        # ── Tabulka prací ───────────────────────────────────────────────────
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["", "Typ", "Student", "Os. číslo", "Téma", "Stav"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.setMinimumHeight(220)
        outer.addWidget(self.table, stretch=1)

        sel_row = QHBoxLayout()
        btn_all = QPushButton("☑ Vše")
        btn_all.clicked.connect(lambda: self._set_all(True))
        btn_none = QPushButton("☐ Nic")
        btn_none.clicked.connect(lambda: self._set_all(False))
        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color:#888;")
        sel_row.addWidget(btn_all)
        sel_row.addWidget(btn_none)
        sel_row.addStretch()
        sel_row.addWidget(self.lbl_count)
        outer.addLayout(sel_row)

        # ── Předmět + tělo (náhled, editovatelné) ───────────────────────────
        subj_row = QFormLayout()
        self.ed_subject = QLineEdit()
        subj_row.addRow("Předmět", self.ed_subject)
        outer.addLayout(subj_row)

        body_head = QHBoxLayout()
        body_lbl = QLabel("Text e-mailu (náhled — lze upravit):")
        self.btn_regen = QPushButton("↻ Přegenerovat text")
        self.btn_regen.setToolTip("Sestaví text znovu podle aktuálně vybraných prací.")
        self.btn_regen.clicked.connect(self._regenerate_body)
        body_head.addWidget(body_lbl)
        body_head.addStretch()
        body_head.addWidget(self.btn_regen)
        outer.addLayout(body_head)

        self.ed_body = QPlainTextEdit()
        self.ed_body.textChanged.connect(self._on_body_edited)
        self.ed_body.setMinimumHeight(180)
        outer.addWidget(self.ed_body)

        # ── Tlačítka ────────────────────────────────────────────────────────
        row = QHBoxLayout()
        btn_settings = QPushButton("⚙ Nastavení e-mailu…")
        btn_settings.clicked.connect(self._open_settings)
        btn_cancel = QPushButton("Zavřít")
        btn_cancel.clicked.connect(self.reject)
        self.btn_test = QPushButton("🧪 Test — poslat jen sobě")
        self.btn_test.setToolTip(
            "Pošle stejný e-mail (včetně PDF příloh) jen na tvůj e-mail — pro "
            "kontrolu, než ho pošleš sekretářce. Posudky NEoznačí jako odeslané."
        )
        self.btn_test.clicked.connect(lambda: self._send(dry_run=True))
        self.btn_send = QPushButton("✉ Odeslat…")
        f = self.btn_send.font()
        f.setBold(True)
        self.btn_send.setFont(f)
        self.btn_send.setDefault(True)
        self.btn_send.clicked.connect(lambda: self._send(dry_run=False))
        row.addWidget(btn_settings)
        row.addStretch()
        row.addWidget(btn_cancel)
        row.addWidget(self.btn_test)
        row.addWidget(self.btn_send)
        outer.addLayout(row)

        self._load_secretaries()

    # --- data ----------------------------------------------------------------

    def _load_secretaries(self) -> None:
        by_email: dict[str, _Secretary] = {}
        for o in self.service.list_obor_objects():
            email = (o.secretary_email or "").strip()
            if not email:
                continue
            key = email.lower()
            sec = by_email.get(key)
            if sec is None:
                sec = _Secretary(
                    name=(o.secretary_name or "").strip(), email=email, obory=set()
                )
                by_email[key] = sec
            sec.obory.add(o.name)
            if not sec.name and o.secretary_name:
                sec.name = o.secretary_name.strip()

        self._secretaries = sorted(
            by_email.values(), key=lambda s: (s.name.lower(), s.email.lower())
        )
        self.cb_secretary.blockSignals(True)
        self.cb_secretary.clear()
        if not self._secretaries:
            self.cb_secretary.addItem("(žádná sekretářka s e-mailem)", None)
        for s in self._secretaries:
            label = f"{s.name} <{s.email}>" if s.name else s.email
            self.cb_secretary.addItem(label, s.email)
        self.cb_secretary.blockSignals(False)
        self._on_secretary_changed()

    def _current_secretary(self) -> _Secretary | None:
        email = self.cb_secretary.currentData()
        if not email:
            return None
        return next((s for s in self._secretaries if s.email == email), None)

    def _gather_items(self, secretary: _Secretary) -> list[_ReviewItem]:
        items: list[_ReviewItem] = []
        if self.role == "supervisor":
            for t in self.service.list_theses():
                student = (
                    self.service.get_student(t.student_id) if t.student_id else None
                )
                obor = (student.obor if student else "") or ""
                if obor not in secretary.obory:
                    continue
                pdf = self.service.current_supervisor_review_pdf(t)
                if pdf is None or not pdf.exists():
                    continue
                name = student.full_name if student else "(neznámý student)"
                uni = (student.university_id if student else "") or ""
                items.append(
                    _ReviewItem(
                        work_id=t.id,
                        type_code=t.type.value,
                        student_name=name,
                        student_uni_id=uni,
                        title=t.title_cs or "(bez názvu)",
                        obor=obor,
                        pdf_path=pdf,
                        sent_at_label=(
                            t.supervisor_review_sent_at.strftime("%d.%m.%Y")
                            if t.supervisor_review_sent_at
                            else ""
                        ),
                    )
                )
        else:
            for op in self.service.list_opposing_theses():
                obor = (op.student_obor or "").strip()
                if obor not in secretary.obory:
                    continue
                pdf = self.service.current_opponent_review_pdf(op)
                if pdf is None or not pdf.exists():
                    continue
                items.append(
                    _ReviewItem(
                        work_id=op.id,
                        type_code=op.type.value,
                        student_name=op.student_full_name or "(neznámý student)",
                        student_uni_id=op.student_university_id or "",
                        title=op.title_cs or "(bez názvu)",
                        obor=obor,
                        pdf_path=pdf,
                        sent_at_label=(
                            op.opponent_review_sent_at.strftime("%d.%m.%Y")
                            if op.opponent_review_sent_at
                            else ""
                        ),
                    )
                )
        # BP první, pak DP; v rámci skupiny dle jména
        items.sort(key=lambda it: (0 if it.type_code == "BP" else 1, it.student_name.lower()))
        return items

    def _on_secretary_changed(self) -> None:
        self._reload_table()
        self._regenerate_body(force=True)
        self._update_recipient()

    def _update_recipient(self) -> None:
        sec = self._current_secretary()
        self.lbl_recipient.setText(
            f"{sec.name} <{sec.email}>" if sec and sec.name else (sec.email if sec else "—")
        )

    def _reload_table(self) -> None:
        sec = self._current_secretary()
        self._items = self._gather_items(sec) if sec else []
        show_sent = self.chk_show_sent.isChecked()

        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self._row_items = []
        for it in self._items:
            if it.sent_at_label and not show_sent:
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            # Nezaslané předzaškrtnuté; zaslané ne.
            chk.setCheckState(
                Qt.CheckState.Unchecked if it.sent_at_label else Qt.CheckState.Checked
            )
            self.table.setItem(row, 0, chk)
            type_item = QTableWidgetItem(it.type_code)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, type_item)
            self.table.setItem(row, 2, QTableWidgetItem(it.student_name))
            self.table.setItem(row, 3, QTableWidgetItem(it.student_uni_id))
            title_item = QTableWidgetItem(it.title)
            title_item.setToolTip(it.title)
            self.table.setItem(row, 4, title_item)
            stav = f"✓ odesláno {it.sent_at_label}" if it.sent_at_label else "připraveno"
            stav_item = QTableWidgetItem(stav)
            if it.sent_at_label:
                stav_item.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row, 5, stav_item)
            self._row_items.append((it, chk))
        self.table.blockSignals(False)
        self._update_count()

    def _checked_items(self) -> list[_ReviewItem]:
        return [
            it for it, chk in self._row_items
            if chk.checkState() == Qt.CheckState.Checked
        ]

    def _set_all(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.table.blockSignals(True)
        for _it, chk in self._row_items:
            chk.setCheckState(state)
        self.table.blockSignals(False)
        self._after_selection_changed()

    def _on_item_changed(self, _item: QTableWidgetItem) -> None:
        self._after_selection_changed()

    def _after_selection_changed(self) -> None:
        self._update_count()
        if not self._body_dirty:
            self._regenerate_body(force=True)

    def _update_count(self) -> None:
        n = len(self._checked_items())
        total = len(self._row_items)
        self.lbl_count.setText(f"Vybráno {n} z {total}")
        self.btn_send.setEnabled(n > 0)
        self.btn_test.setEnabled(n > 0)

    # --- text ----------------------------------------------------------------

    def _sender_display(self) -> str:
        profile = self.profile_manager.active
        if profile is None:
            return ""
        parts = [
            profile.user_title_before.strip(),
            profile.user_name.strip(),
            profile.user_title_after.strip(),
        ]
        return " ".join(p for p in parts if p).strip()

    def _regenerate_body(self, force: bool = False) -> None:
        if self._body_dirty and not force:
            return
        sec = self._current_secretary()
        items = self._checked_items()
        body_items = [
            (it.type_code, it.student_name, it.student_uni_id, it.title)
            for it in items
        ]
        body = email_sender.compose_body(
            body_items,
            role=self.role,
            secretary_name=sec.name if sec else "",
            sender_display=self._sender_display(),
        )
        self.ed_subject.setText(email_sender.compose_subject(self.role))
        self.ed_body.blockSignals(True)
        self.ed_body.setPlainText(body)
        self.ed_body.blockSignals(False)
        self._body_dirty = False

    def _on_body_edited(self) -> None:
        # textChanged se spustí i z našeho setPlainText (to máme blokované),
        # takže sem se dostaneme jen při ruční editaci uživatele.
        self._body_dirty = True

    # --- odeslání ------------------------------------------------------------

    def _open_settings(self) -> None:
        from .email_settings_dialog import EmailSettingsDialog

        dlg = EmailSettingsDialog(self.profile_manager, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            profile = self.profile_manager.active
            self._user_email = (profile.user_email if profile else "") or ""
            self.chk_cc.setText(
                f"Kopie mně ({self._user_email})" if self._user_email else "Kopie mně"
            )
            self.chk_cc.setEnabled(bool(self._user_email))
            if not self._user_email:
                self.chk_cc.setChecked(False)

    def _build_draft(
        self, items: list[_ReviewItem], *, dry_run: bool = False
    ) -> email_sender.MailDraft | None:
        sec = self._current_secretary()
        if sec is None:
            QMessageBox.warning(self, "Sekretářka", "Vyber sekretářku.")
            return None
        profile = self.profile_manager.active
        from_addr = (profile.user_email if profile else "") or ""
        if not from_addr:
            QMessageBox.warning(
                self, "Chybí e-mail",
                "Nemáš vyplněný vlastní e-mail. Otevři „⚙ Nastavení e-mailu…“ "
                "a doplň ho.",
            )
            return None

        subject = self.ed_subject.text().strip() or email_sender.compose_subject(self.role)
        body = self.ed_body.toPlainText()
        if dry_run:
            # Testovací odeslání jen sobě — nepřijde sekretářce.
            to = [from_addr]
            cc: list[str] = []
            subject = f"[TEST] {subject}"
            real_to = f"{sec.name} <{sec.email}>" if sec.name else sec.email
            body = (
                "‼ TESTOVACÍ ODESLÁNÍ — tento e-mail jde jen tobě, sekretářce "
                f"se neodeslal.\nOstrý příjemce by byl: {real_to}\n"
                "─────────────────────────────────────────────\n\n"
            ) + body
        else:
            to = [sec.email]
            cc = [from_addr] if (self.chk_cc.isChecked() and from_addr) else []

        return email_sender.MailDraft(
            from_addr=from_addr,
            from_name=self._sender_display(),
            to=to,
            cc=cc,
            subject=subject,
            body=body,
            attachments=[it.pdf_path for it in items],
        )

    def _send(self, dry_run: bool = False) -> None:
        items = self._checked_items()
        if not items:
            return
        draft = self._build_draft(items, dry_run=dry_run)
        if draft is None:
            return

        # Náhled / potvrzení před odesláním
        cc_line = f"\nKopie: {', '.join(draft.cc)}" if draft.cc else ""
        header = (
            "🧪 TEST — poslat jen sobě (sekretářce se nic nepošle):\n\n"
            if dry_run
            else ""
        )
        confirm = QMessageBox.question(
            self,
            "Testovací odeslání?" if dry_run else "Odeslat e-mail?",
            f"{header}"
            f"Komu: {', '.join(draft.to)}{cc_line}\n"
            f"Předmět: {draft.subject}\n"
            f"Příloh (PDF posudků): {len(draft.attachments)}\n\n"
            "Odeslat nyní?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        profile = self.profile_manager.active
        smtp = profile.smtp
        login_name = (smtp.username or draft.from_addr).strip()
        password, ok = QInputDialog.getText(
            self,
            "Heslo k e-mailu",
            f"Heslo pro {login_name}\n(neuloží se, použije se jen k odeslání):",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        sent_ok = False
        try:
            email_sender.send_via_smtp(smtp, password, draft)
            sent_ok = True
        except email_sender.EmailError as exc:
            QApplication.restoreOverrideCursor()
            self._offer_eml_fallback(draft, items, str(exc), dry_run=dry_run)
            return
        except Exception as exc:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Odeslání", f"Neočekávaná chyba:\n{exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        if sent_ok:
            if dry_run:
                # Test — neoznačovat jako odeslané, nechat dialog otevřený.
                QMessageBox.information(
                    self, "Testovací e-mail odeslán",
                    f"Testovací e-mail s {len(items)} posudky byl odeslán na "
                    f"{draft.to[0]} (jen tobě). Posudky nebyly označeny jako "
                    "odeslané — zkontroluj e-mail a pak pošli sekretářce.",
                )
                return
            self._mark_sent(items)
            QMessageBox.information(
                self, "Odesláno",
                f"E-mail s {len(items)} posudky byl odeslán na {draft.to[0]}.",
            )
            self.accept()

    def _offer_eml_fallback(
        self, draft: email_sender.MailDraft, items: list[_ReviewItem], reason: str,
        *, dry_run: bool = False,
    ) -> None:
        choice = QMessageBox.question(
            self,
            "Odeslání přes SMTP selhalo",
            f"{reason}\n\n"
            "Chceš místo toho vytvořit hotový e-mail a otevřít ho v mailovém "
            "klientovi (Outlook/Thunderbird)? Tam jsi přihlášen(a) a stačí "
            "kliknout Odeslat.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return
        try:
            safe = "".join(c for c in draft.to[0] if c.isalnum()) or "posudky"
            target = Path(tempfile.gettempdir()) / f"posudky_{safe}.eml"
            email_sender.save_as_eml(draft, target)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Chyba", f"Nepodařilo se vytvořit .eml:\n{exc}")
            return
        _open_path(target)
        if dry_run:
            # Test — žádné označení odeslání, dialog zůstane otevřený.
            QMessageBox.information(
                self, "Testovací e-mail otevřen",
                "Otevřel jsem testovací e-mail (jen tobě) v mailovém klientovi. "
                "Posudky nebyly označeny jako odeslané.",
            )
            return
        mark = QMessageBox.question(
            self,
            "Otevřeno v mailu",
            "Otevřel jsem připravený e-mail v tvém mailovém klientovi.\n\n"
            "Až ho tam odešleš, mám tyto posudky označit jako odeslané?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if mark == QMessageBox.StandardButton.Yes:
            self._mark_sent(items)
        self.accept()

    def _mark_sent(self, items: list[_ReviewItem]) -> None:
        for it in items:
            try:
                if self.role == "supervisor":
                    self.service.mark_supervisor_review_sent(it.work_id)
                else:
                    self.service.mark_opponent_review_sent(it.work_id)
            except Exception:  # noqa: BLE001
                pass
