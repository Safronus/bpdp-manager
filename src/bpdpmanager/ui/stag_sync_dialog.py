"""Aktualizace existujících prací ze STAG (stav + nové soubory).

Na rozdíl od :class:`StagDownloadDialog` (hledá ve STAG a importuje nové práce)
tento dialog vezme **práce, které už v databázi máš**, dohledá je ve STAG podle
``adipIdno`` (nebo dle příjmení, když ID chybí) a nabídne:

* **změnu stavu** (např. *V řešení → Obhájeno*) — navrhne a necháš potvrdit,
* **dohrání chybějících souborů** (typicky přibyl posudek nebo odevzdaná práce) —
  předzaškrtne soubory, jejichž *druh* u práce ještě není.

Síťovou vrstvu řeší :mod:`bpdpmanager.services.stag_api` (UI nesahá na HTTP).
"""

from __future__ import annotations

import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from ..models.enums import AttachmentKind, ThesisStatus
from ..services import BackupManager, stag_api
from ..services.stag_csv_importer import load_stag_csv_bytes
from .stag_import_dialog import (
    _SECTION_TO_KIND,
    STAG_STATE_TO_STATUS,
    _fmt_size,
    _fold,
)


@dataclass
class _SyncTarget:
    """Jedna existující práce (vedená/oponovaná) a její STAG protějšek."""

    is_opposing: bool
    obj_id: str
    type_code: str            # "BP" / "DP"
    surname: str
    label: str
    local_status: ThesisStatus | None      # None u oponovaných (nemají stav)
    local_kinds: set[AttachmentKind]
    adipidno: str = ""
    # vyplní se po dotažení ze STAG:
    found_via_search: bool = False
    stag_status_code: str = ""
    stag_files: list[stag_api.StagFile] = field(default_factory=list)
    error: str = ""

    @property
    def new_status(self) -> ThesisStatus | None:
        """Stav dle STAG (nebo None, když ho neznáme / je stejný)."""
        if self.is_opposing or not self.stag_status_code:
            return None
        mapped = STAG_STATE_TO_STATUS.get(self.stag_status_code)
        if mapped is None or mapped == self.local_status:
            return None
        return mapped


# Role pole odpovídají tlačítkům: vedené práce v řešení / oponentury akt. rok.
ROLE_SUPERVISOR = "supervisor"
ROLE_OPPONENT = "opponent"


def _fetch_target_state(adipidno: str) -> tuple[str, list[stag_api.StagFile], str]:
    """Vrátí (STAG kód stavu, soubory, chyba) pro práci dle adipIdno."""
    status_code = ""
    files: list[stag_api.StagFile] = []
    try:
        raw = stag_api.download_csv(adipidno)
        imp = load_stag_csv_bytes(raw)
        if imp.records:
            status_code = imp.records[0].stag_state_code or ""
    except Exception as exc:  # noqa: BLE001
        return "", [], str(exc)
    try:
        files = stag_api.list_thesis_files(adipidno)
    except Exception:  # noqa: BLE001
        pass
    return status_code, files, ""


def _resolve_adipidno(surname: str, type_code: str, role: str) -> str:
    """Dohledá adipIdno práce ve STAG dle příjmení studenta (best-effort)."""
    person_role = (
        stag_api.ROLE_SUPERVISOR if role == ROLE_SUPERVISOR else stag_api.ROLE_OPPONENT
    )
    try:
        results = stag_api.search_theses(surname, "", person_role)
    except Exception:  # noqa: BLE001
        return ""
    folded = _fold(surname)
    for r in results:
        rtype = "DP" if "diplom" in (r.type_label or "").lower() else (
            "BP" if "bakal" in (r.type_label or "").lower() else ""
        )
        if rtype and rtype != type_code:
            continue
        if folded and folded not in _fold(r.surname):
            continue
        return r.adipidno
    return ""


class StagSyncDialog(QDialog):
    """Aktualizuje existující práce (stav + nové soubory) ze STAG."""

    def __init__(self, service, role: str, parent=None, *, profile_manager=None) -> None:
        super().__init__(parent)
        self.service = service
        self.role = role
        self.profile_manager = profile_manager
        self._targets: list[_SyncTarget] = []
        self.changed = False  # nastav True, když se něco aktualizovalo

        led = role == ROLE_SUPERVISOR
        what = "vedené práce v řešení" if led else "oponentury (aktuální rok)"
        self.setWindowTitle(f"Aktualizovat {what} ze STAG")
        self.setMinimumSize(820, 620)
        self.resize(1040, 820)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        title = QLabel(f"🔄 Aktualizovat {what} ze STAG")
        title.setStyleSheet("font-size:16px;font-weight:bold;")
        outer.addWidget(title)

        intro = QLabel(
            "Porovná tvé práce se STAG a nabídne <b>změnu stavu</b> a "
            "<b>dohrání chybějících souborů</b> (např. nový posudek nebo "
            "odevzdaná práce). Zaškrtni, co aplikovat."
        )
        intro.setTextFormat(Qt.TextFormat.RichText)
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#888;")
        outer.addWidget(intro)

        self.lbl_status = QLabel("⏳ Zjišťuji stav prací ve STAG…")
        self.lbl_status.setWordWrap(True)
        outer.addWidget(self.lbl_status)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemChanged.connect(lambda _i: self._update_apply_btn())
        outer.addWidget(self.tree, stretch=1)

        row = QHBoxLayout()
        btn_close = QPushButton("Zavřít")
        btn_close.clicked.connect(self.reject)
        self.btn_apply = QPushButton("✓ Aktualizovat vybrané")
        self.btn_apply.setEnabled(False)
        af = self.btn_apply.font()
        af.setBold(True)
        self.btn_apply.setFont(af)
        self.btn_apply.clicked.connect(self._apply)
        row.addStretch()
        row.addWidget(btn_close)
        row.addWidget(self.btn_apply)
        outer.addLayout(row)

        QTimer.singleShot(0, self._scan)

    # --- sběr prací z DB -----------------------------------------------------

    def _collect_targets(self) -> list[_SyncTarget]:
        targets: list[_SyncTarget] = []
        if self.role == ROLE_SUPERVISOR:
            for t in self.service.list_theses():
                if t.status != ThesisStatus.IN_PROGRESS:
                    continue
                student = self.service.get_student(t.student_id) if t.student_id else None
                surname = student.last_name if student else ""
                name = student.full_name if student else "(neznámý student)"
                label = f"{name} — {t.title_cs or '(bez názvu)'} ({t.type.value})"
                kinds = {a.kind for a in t.attachments if a.is_current}
                targets.append(_SyncTarget(
                    is_opposing=False, obj_id=t.id, type_code=t.type.value,
                    surname=surname, label=label, local_status=t.status,
                    local_kinds=kinds, adipidno=t.adipidno or "",
                ))
        else:
            current = self.service.current_academic_year()
            for o in self.service.list_opposing_theses():
                if o.academic_year != current:
                    continue
                name = f"{o.student_last_name} {o.student_first_name}".strip() or "(student)"
                label = f"{name} — {o.title_cs or '(bez názvu)'} ({o.type.value})"
                kinds = {a.kind for a in o.attachments if a.is_current}
                targets.append(_SyncTarget(
                    is_opposing=True, obj_id=o.id, type_code=o.type.value,
                    surname=o.student_last_name, label=label, local_status=None,
                    local_kinds=kinds, adipidno=o.adipidno or "",
                ))
        return targets

    # --- scan (dohledání ID + dotažení stavu/souborů) ------------------------

    def _scan(self) -> None:
        targets = self._collect_targets()
        if not targets:
            self.lbl_status.setText(
                "Nemáš žádné práce k aktualizaci "
                "(vedené v řešení / oponentury aktuálního roku)."
            )
            return

        progress = QProgressDialog(
            "Zjišťuji stav prací ve STAG…", "Přerušit", 0, len(targets), self
        )
        progress.setWindowTitle("STAG — aktualizace")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        def work(tgt: _SyncTarget) -> _SyncTarget:
            adip = tgt.adipidno
            if not adip:
                adip = _resolve_adipidno(tgt.surname, tgt.type_code, self.role)
                if adip:
                    tgt.adipidno = adip
                    tgt.found_via_search = True
                else:
                    tgt.error = "nenalezeno ve STAG (chybí STAG ID i shoda dle příjmení)"
                    return tgt
            status_code, files, err = _fetch_target_state(adip)
            tgt.stag_status_code = status_code
            tgt.stag_files = files
            if err:
                tgt.error = err
            return tgt

        executor = ThreadPoolExecutor(max_workers=8)
        futures = {executor.submit(work, t): t for t in targets}
        done = 0
        try:
            for fut in as_completed(futures):
                try:
                    fut.result()
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

        self._targets = targets
        self._populate()

    # --- naplnění stromu -----------------------------------------------------

    def _populate(self) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        gray = QBrush(QColor("#888"))
        amber = QBrush(QColor("#e65100"))

        actionable = 0
        skipped = 0
        for ti, tgt in enumerate(self._targets):
            top = QTreeWidgetItem([tgt.label])
            top.setFlags(top.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            f = top.font(0)
            f.setBold(True)
            top.setFont(0, f)
            self.tree.addTopLevelItem(top)

            if tgt.error:
                note = QTreeWidgetItem([f"⚠ {tgt.error}"])
                note.setForeground(0, amber)
                top.addChild(note)
                top.setExpanded(True)
                skipped += 1
                continue
            if tgt.found_via_search:
                note = QTreeWidgetItem(["ℹ dohledáno ve STAG dle příjmení"])
                note.setForeground(0, gray)
                top.addChild(note)

            has_action = False

            # Návrh změny stavu.
            new_status = tgt.new_status
            if new_status is not None:
                old = tgt.local_status.label if tgt.local_status else "—"
                code = tgt.stag_status_code
                leaf = QTreeWidgetItem(
                    [f"🔄 Stav: {old} → {new_status.label}  (STAG: {code})"]
                )
                leaf.setFlags(
                    (leaf.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    & ~Qt.ItemFlag.ItemIsAutoTristate
                )
                leaf.setCheckState(0, Qt.CheckState.Checked)
                leaf.setData(0, Qt.ItemDataRole.UserRole, ("status", ti))
                top.addChild(leaf)
                has_action = True

            # Soubory ze STAG — předzaškrtni ty, jejichž druh u práce chybí.
            for fi, sf in enumerate(tgt.stag_files):
                kind = _SECTION_TO_KIND.get(sf.section, AttachmentKind.OTHER)
                is_new = kind not in tgt.local_kinds
                tag = "nový druh" if is_new else "už máš tento druh"
                size = f" · {_fmt_size(sf.size_hint)}" if sf.size_hint else ""
                leaf = QTreeWidgetItem(
                    [f"📎 {kind.label}: {sf.filename}{size}  [{tag}]"]
                )
                leaf.setFlags(
                    (leaf.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    & ~Qt.ItemFlag.ItemIsAutoTristate
                )
                leaf.setCheckState(
                    0, Qt.CheckState.Checked if is_new else Qt.CheckState.Unchecked
                )
                if not is_new:
                    leaf.setForeground(0, gray)
                leaf.setData(0, Qt.ItemDataRole.UserRole, ("file", ti, fi, sf.soubidno))
                top.addChild(leaf)
                has_action = True

            if has_action:
                actionable += 1
                top.setExpanded(True)
            else:
                top.addChild(QTreeWidgetItem(["✓ beze změn"]))
                top.child(top.childCount() - 1).setForeground(0, gray)

        self.tree.blockSignals(False)

        total = len(self._targets)
        msg = (
            f"Prošlo {total} "
            f"{'prací' if total != 1 else 'práce'}: "
            f"{actionable} se změnami k aktualizaci."
        )
        if skipped:
            msg += f"  ·  {skipped} bez nalezení ve STAG."
        self.lbl_status.setText(msg)
        self._update_apply_btn()

    # --- výběr / aplikace ----------------------------------------------------

    def _checked_actions(self) -> list[tuple]:
        out: list[tuple] = []

        def walk(item: QTreeWidgetItem) -> None:
            for i in range(item.childCount()):
                walk(item.child(i))
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and item.checkState(0) == Qt.CheckState.Checked:
                out.append(data)

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            walk(root.child(i))
        return out

    def _update_apply_btn(self) -> None:
        n = len(self._checked_actions())
        self.btn_apply.setEnabled(n > 0)
        self.btn_apply.setText(
            "✓ Aktualizovat vybrané" if n == 0 else f"✓ Aktualizovat vybrané ({n})"
        )

    def _apply(self) -> None:
        actions = self._checked_actions()
        if not actions:
            return

        # Záloha před změnami (záchranná brzda).
        backup_name = None
        data_dir = None
        if self.profile_manager and self.profile_manager.active:
            data_dir = self.profile_manager.active_data_dir()
            try:
                info = BackupManager(data_dir).create_backup(
                    data_dir / "db.json", suffix="before-stag-sync", dedupe=False
                )
                if info is not None:
                    backup_name = info.path.name
            except Exception:  # noqa: BLE001
                pass

        # Seskup akce dle práce (soubory potřebují re-list v jedné session).
        status_targets: list[int] = [a[1] for a in actions if a[0] == "status"]
        files_by_target: dict[int, set[str]] = {}
        for a in actions:
            if a[0] == "file":
                files_by_target.setdefault(a[1], set()).add(a[3])

        stats = {"status": 0, "files": 0, "errors": []}

        progress = QProgressDialog(
            "Aktualizuji práce…", "Přerušit", 0,
            len(set(status_targets) | set(files_by_target)), self,
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        done = 0
        all_targets = sorted(set(status_targets) | set(files_by_target))
        for ti in all_targets:
            if progress.wasCanceled():
                break
            tgt = self._targets[ti]
            progress.setLabelText(f"Aktualizuji:\n{tgt.label}")
            QApplication.processEvents()

            # 1) Stav (jen vedené práce).
            if ti in status_targets and not tgt.is_opposing and tgt.new_status:
                try:
                    self.service.transition(tgt.obj_id, tgt.new_status)
                    stats["status"] += 1
                    self.changed = True
                except Exception as exc:  # noqa: BLE001
                    stats["errors"].append(f"{tgt.label}: stav — {exc}")

            # 2) Soubory — re-list v čerstvé session a stáhni vybrané.
            if ti in files_by_target:
                self._apply_files(tgt, files_by_target[ti], stats)

            done += 1
            progress.setValue(done)
            QApplication.processEvents()
        progress.close()

        self._show_summary(stats, backup_name, data_dir)

    def _apply_files(self, tgt: _SyncTarget, soubidna: set[str], stats: dict) -> None:
        client = stag_api.StagClient()
        try:
            files = client.list_thesis_files(tgt.adipidno)
        except Exception as exc:  # noqa: BLE001
            stats["errors"].append(f"{tgt.label}: výpis souborů — {exc}")
            return
        by_soub = {f.soubidno: f for f in files}
        for soub in soubidna:
            sf = by_soub.get(soub)
            if sf is None:
                continue
            try:
                data = client.download_file(sf.download_path)
            except Exception as exc:  # noqa: BLE001
                stats["errors"].append(f"{tgt.label}: {sf.filename} — {exc}")
                continue
            safe = sf.filename or f"soubor_{soub}"
            tmp = Path(tempfile.gettempdir()) / f"stagsync_{tgt.adipidno}_{soub}_{safe}"
            try:
                tmp.write_bytes(data)
            except OSError as exc:
                stats["errors"].append(f"{tgt.label}: zápis {sf.filename} — {exc}")
                continue
            kind = _SECTION_TO_KIND.get(sf.section, AttachmentKind.OTHER)
            try:
                if tgt.is_opposing:
                    self.service.opposing_attach_document(tgt.obj_id, tmp, kind=kind)
                else:
                    self.service.attach_document(tgt.obj_id, tmp, kind=kind)
                stats["files"] += 1
                self.changed = True
            except Exception as exc:  # noqa: BLE001
                stats["errors"].append(f"{tgt.label}: přiložení {sf.filename} — {exc}")
        # Dosynchronizuj známky z čerstvě připojených posudků.
        try:
            if tgt.is_opposing:
                self.service.sync_opposing_grades(tgt.obj_id)
            else:
                self.service.sync_thesis_grades(tgt.obj_id)
        except Exception:  # noqa: BLE001
            pass

    def _show_summary(self, stats: dict, backup_name, data_dir) -> None:
        parts = [
            f"Aktualizováno stavů: {stats['status']}",
            f"Dohráno souborů: {stats['files']}",
        ]
        if stats["errors"]:
            parts.append("")
            parts.append("Chyby:")
            parts.extend(f"• {e}" for e in stats["errors"][:12])

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle("Aktualizace dokončena")
        box.setText("\n".join(parts))
        if backup_name and data_dir is not None:
            btn_revert = box.addButton("↩ Vrátit vše", QMessageBox.ButtonRole.DestructiveRole)
        else:
            btn_revert = None
        box.addButton("Zavřít", QMessageBox.ButtonRole.AcceptRole)
        box.exec()

        if btn_revert is not None and box.clickedButton() == btn_revert:
            try:
                BackupManager(data_dir).restore_backup(
                    backup_name, data_dir / "db.json"
                )
                self.service.reload()
                self.changed = True  # data se změnila (zpět na původní)
                QMessageBox.information(
                    self, "Vráceno", "Změny byly vráceny ze zálohy."
                )
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Vrácení selhalo", str(exc))
        self.accept()
