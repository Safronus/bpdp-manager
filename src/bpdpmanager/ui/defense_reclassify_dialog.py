"""Přeřazení už stažených příloh „Jiné" na typ „Soubor s průběhem obhajoby".

Původní názvy souborů se při stažení ze STAG ztrácí (soubor se přejmenuje na
``Příjmení_jine_datum.pdf``). Tento dialog proto **znovu dotáhne seznam souborů
ze STAG**, obnoví původní názvy, spáruje je s lokálními přílohami typu *Jiné*
a v náhledu (s checkboxy) nabídne přeřazení — soubory vypadající jako protokol
obhajoby jsou předzaškrtnuté.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressDialog,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from ..models.enums import AttachmentKind
from ..services import BackupManager, stag_api
from ..services.stag_api import is_defense_record_filename


def pair_other_with_stag(local_others: list, stag_files: list) -> list[tuple]:
    """Spáruje lokální přílohy „Jiné" se STAG soubory ze sekcí other/defense.

    Vrací list ``(attachment, original_name|None, is_defense_guess)``. Páruje
    podle pořadí (typicky 1:1 — u jedné práce bývá jeden „jiný" soubor).
    """
    stag_other = [
        f for f in stag_files if f.section in ("other", "defense_record")
    ]
    pairs: list[tuple] = []
    for i, att in enumerate(local_others):
        sf = stag_other[i] if i < len(stag_other) else None
        orig = sf.filename if sf else None
        # Předzaškrtni, když to STAG značí jako průběh obhajoby (sekce) NEBO
        # tomu odpovídá název (záložní heuristika u starších/jiných případů).
        guess = bool(sf) and (
            sf.section == "defense_record" or is_defense_record_filename(orig)
        )
        pairs.append((att, orig, guess))
    return pairs


class DefenseReclassifyDialog(QDialog):
    """Re-fetch ze STAG + náhled s checkboxy pro přeřazení na průběh obhajoby."""

    _ROLE_REF = Qt.ItemDataRole.UserRole + 1

    def __init__(self, service, parent=None, *, profile_manager=None) -> None:
        super().__init__(parent)
        self.service = service
        self.profile_manager = profile_manager
        self.changed = False
        self._rows: list[tuple] = []  # (attachment, work_label, name)

        self.setWindowTitle("Přeřadit průběh obhajoby (ze STAG)")
        self.setMinimumSize(760, 560)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Dotáhnu ze STAG původní názvy příloh typu <b>Jiné</b> a nabídnu "
            "přeřazení na <b>Soubor s průběhem obhajoby</b>. Soubory, které "
            "vypadají jako protokol/zápis o obhajobě, jsou předzaškrtnuté — "
            "ostatní zkontroluj a případně zaškrtni.",
            textFormat=Qt.TextFormat.RichText,
        ))
        self.lbl_status = QLabel("⏳ Dotahuji seznam souborů ze STAG…")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Práce", "Původní název souboru ze STAG"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree, stretch=1)

        row = QHBoxLayout()
        btn_close = QPushButton("Zavřít")
        btn_close.clicked.connect(self.reject)
        self.btn_apply = QPushButton("✓ Přeřadit zaškrtnuté")
        self.btn_apply.setEnabled(False)
        self.btn_apply.clicked.connect(self._apply)
        row.addStretch()
        row.addWidget(btn_close)
        row.addWidget(self.btn_apply)
        layout.addLayout(row)

        QTimer.singleShot(0, self._scan)

    # --- sběr kandidátů ------------------------------------------------------

    def _candidates(self) -> list[tuple]:
        """(owner_label, adipidno, [current OTHER attachments]) pro práce s STAG ID."""
        out: list[tuple] = []
        for t in self.service.list_theses():
            if not t.adipidno:
                continue
            others = [a for a in t.attachments
                      if a.kind == AttachmentKind.OTHER and a.is_current and a.is_file]
            if not others:
                continue
            student = self.service.get_student(t.student_id) if t.student_id else None
            name = student.full_name if student else "(bez studenta)"
            out.append((f"{name} — {t.type.value} {t.academic_year}", t.adipidno, others))
        for o in self.service.list_opposing_theses():
            if not o.adipidno:
                continue
            others = [a for a in o.attachments
                      if a.kind == AttachmentKind.OTHER and a.is_current and a.is_file]
            if not others:
                continue
            name = f"{o.student_last_name} {o.student_first_name}".strip() or "(student)"
            out.append(
                (f"{name} — {o.type.value} {o.academic_year} (oponentura)",
                 o.adipidno, others)
            )
        return out

    def _scan(self) -> None:
        candidates = self._candidates()
        if not candidates:
            self.lbl_status.setText(
                "Žádné práce s přílohou typu „Jiné“ a STAG ID — není co přeřadit."
            )
            return

        progress = QProgressDialog(
            "Dotahuji seznam souborů ze STAG…", "Přerušit", 0, len(candidates), self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        def work(item):
            label, adip, others = item
            try:
                files = stag_api.list_thesis_files(adip)
            except Exception:  # noqa: BLE001 — práce může chybět / síť; přeskoč
                files = []
            return label, others, files

        results = []
        executor = ThreadPoolExecutor(max_workers=8)
        futures = {executor.submit(work, c): c for c in candidates}
        done = 0
        try:
            for fut in as_completed(futures):
                try:
                    results.append(fut.result())
                except Exception:  # noqa: BLE001
                    pass
                done += 1
                progress.setValue(done)
                QApplication.processEvents()
                if progress.wasCanceled():
                    break
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
            progress.close()

        self._populate(results)

    def _populate(self, results: list[tuple]) -> None:
        self.tree.clear()
        self._rows = []
        guessed = 0
        for label, others, files in results:
            for att, orig, guess in pair_other_with_stag(others, files):
                name = orig or att.label  # když STAG nedohledá, ukaž lokální název
                item = QTreeWidgetItem([label, name])
                item.setFlags(
                    (item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    & ~Qt.ItemFlag.ItemIsAutoTristate
                )
                item.setCheckState(
                    0, Qt.CheckState.Checked if guess else Qt.CheckState.Unchecked
                )
                item.setData(0, self._ROLE_REF, len(self._rows))
                self._rows.append((att, label, name))
                self.tree.addTopLevelItem(item)
                if guess:
                    guessed += 1
        self.tree.itemChanged.connect(lambda *_: self._update_btn())

        total = len(self._rows)
        self.lbl_status.setText(
            f"Nalezeno {total} příloh typu „Jiné“; "
            f"{guessed} vypadá jako průběh obhajoby (předzaškrtnuto)."
            if total else "Žádné přílohy typu „Jiné“ k přeřazení."
        )
        self.tree.resizeColumnToContents(0)
        self._update_btn()

    def _checked_indices(self) -> list[int]:
        out = []
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            if it.checkState(0) == Qt.CheckState.Checked:
                out.append(it.data(0, self._ROLE_REF))
        return out

    def _update_btn(self) -> None:
        n = len(self._checked_indices())
        self.btn_apply.setEnabled(n > 0)
        self.btn_apply.setText(
            "✓ Přeřadit zaškrtnuté" if not n else f"✓ Přeřadit zaškrtnuté ({n})"
        )

    def _apply(self) -> None:
        idxs = self._checked_indices()
        if not idxs:
            return
        # Záloha (záchranná brzda).
        if self.profile_manager and self.profile_manager.active:
            data_dir = self.profile_manager.active_data_dir()
            try:
                BackupManager(data_dir).create_backup(
                    data_dir / "db.json",
                    suffix="before-defense-reclassify", dedupe=False,
                )
            except Exception:  # noqa: BLE001
                pass

        for i in idxs:
            att = self._rows[i][0]
            att.kind = AttachmentKind.DEFENSE_RECORD
        self.service.save()
        self.changed = True
        self.accept()
