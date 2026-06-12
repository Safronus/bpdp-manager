"""Tichá kontrola na pozadí — jsou ve STAG změny pro aktuální akademický rok?

Zjišťuje (read-only, bez zápisu do DB):
- u **vedených prací „V řešení"** změnu stavu nebo chybějící druh souboru,
- u **oponentur aktuálního roku** změnu STAG stavu nebo chybějící druh souboru,
- **nové práce** ve STAG (dle jména), které ještě nemáš v databázi.

Běží na vlákně; výsledek se hlásí signálem ``StagChecker.finished``. Logika
porovnání se sdílí se synchronizačním dialogem (``stag_sync_dialog``).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from ..i18n import tr
from ..models.enums import AttachmentKind, ThesisStatus
from ..services import stag_api
from .stag_import_dialog import (
    _SECTION_TO_KIND,
    STAG_STATE_TO_STATUS,
    _name_matches,
)
from .stag_sync_dialog import ROLE_OPPONENT, ROLE_SUPERVISOR, _fetch_target_state


@dataclass
class StagCheckResult:
    """Výsledek tiché kontroly. ``ok=False`` = kontrolu nešlo dokončit (offline).

    Seznamy nesou lidský popis dotčených prací (pro náhledový dialog); počty
    jsou jejich délky (zpětně kompatibilní vlastnosti).
    """

    ok: bool = False
    error: str = ""
    checked: int = 0                       # kolik existujících prací prošlo
    supervised: list[str] = field(default_factory=list)  # vedené „V řešení" se změnou
    opposing: list[str] = field(default_factory=list)    # oponentury akt. roku se změnou
    new: list[str] = field(default_factory=list)         # nové práce ve STAG (nemáš)
    up_to_date: list[str] = field(default_factory=list)  # zkontrolováno, beze změn (debug)

    @property
    def supervised_changes(self) -> int:
        return len(self.supervised)

    @property
    def opposing_changes(self) -> int:
        return len(self.opposing)

    @property
    def new_works(self) -> int:
        return len(self.new)

    @property
    def total_changes(self) -> int:
        return self.supervised_changes + self.opposing_changes + self.new_works


def _missing_kind_labels(stag_files, local_kinds: set) -> list[str]:
    """Vrátí popisky druhů souborů, které STAG nabízí, ale u práce je nemáš."""
    seen: list[str] = []
    for sf in stag_files:
        kind = _SECTION_TO_KIND.get(sf.section, AttachmentKind.OTHER)
        if kind not in local_kinds and kind.label not in seen:
            seen.append(kind.label)
    return seen


def _change_note(status_changed: bool, missing: list[str]) -> str:
    """Sestaví popis změny: změna stavu a/nebo konkrétní nové soubory."""
    parts: list[str] = []
    if status_changed:
        parts.append("změna stavu")
    if missing:
        parts.append("nový soubor: " + ", ".join(missing))
    return " · ".join(parts)


def _person_role(role: str) -> str:
    return (
        stag_api.ROLE_SUPERVISOR if role == ROLE_SUPERVISOR else stag_api.ROLE_OPPONENT
    )


def _surname_of(full_name: str) -> str:
    tokens = [t.strip(".,") for t in (full_name or "").replace(",", " ").split()
              if t.strip(".,")]
    return tokens[-1] if tokens else ""


def compute_stag_check(service, user_full_name: str = "") -> StagCheckResult:
    """Spočítá počty změn ve STAG (read-only). Vhodné volat z vlákna."""
    r = StagCheckResult()
    attempts = 0
    failures = 0
    current = service.current_academic_year()

    db_adip: set[str] = {t.adipidno for t in service.list_theses() if t.adipidno}
    db_adip |= {o.adipidno for o in service.list_opposing_theses() if o.adipidno}

    # 1) Vedené práce „V řešení" se STAG ID.
    for t in service.list_theses():
        if t.status != ThesisStatus.IN_PROGRESS or not t.adipidno:
            continue
        attempts += 1
        code, files, err = _fetch_target_state(t.adipidno)
        if err:
            failures += 1
            continue
        r.checked += 1
        local_kinds = {a.kind for a in t.attachments if a.is_current}
        mapped = STAG_STATE_TO_STATUS.get(code)
        status_changed = mapped is not None and mapped != t.status
        missing = _missing_kind_labels(files, local_kinds)
        student = service.get_student(t.student_id) if t.student_id else None
        name = student.full_name if student else "(bez studenta)"
        base = f"{name} — {t.type.value} {t.academic_year}"
        if status_changed or missing:
            r.supervised.append(f"{base} · {_change_note(status_changed, missing)}")
        else:
            r.up_to_date.append(f"{base} (vedená)")

    # 2) Oponentury aktuálního roku se STAG ID.
    for o in service.list_opposing_theses():
        if o.academic_year != current or not o.adipidno:
            continue
        attempts += 1
        code, files, err = _fetch_target_state(o.adipidno)
        if err:
            failures += 1
            continue
        r.checked += 1
        local_kinds = {a.kind for a in o.attachments if a.is_current}
        code_changed = bool(code) and code != o.stag_state_code
        missing = _missing_kind_labels(files, local_kinds)
        name = f"{o.student_last_name} {o.student_first_name}".strip() or "(student)"
        base = f"{name} — {o.type.value} {o.academic_year}"
        if code_changed or missing:
            r.opposing.append(f"{base} · {_change_note(code_changed, missing)}")
        else:
            r.up_to_date.append(f"{base} (oponentura)")

    # 3) Nové práce ve STAG (dle CELÉHO jména — ne jen příjmení, ať nepočítáme
    #    jmenovce), které v DB nemáš.
    surname = _surname_of(user_full_name)
    if surname:
        seen_new: set[str] = set()
        for role in (ROLE_SUPERVISOR, ROLE_OPPONENT):
            attempts += 1
            try:
                results = stag_api.search_theses("", surname, _person_role(role))
            except Exception:  # noqa: BLE001 — síť/parser; bereme jako neúspěch pokusu
                failures += 1
                continue
            for res in results:
                if not res.adipidno or res.adipidno in db_adip or res.adipidno in seen_new:
                    continue
                person = res.supervisor if role == ROLE_SUPERVISOR else res.reviewer
                if not _name_matches(person, user_full_name):
                    continue  # jmenovec (jiný vedoucí/oponent se stejným příjmením)
                seen_new.add(res.adipidno)
                year = res.academic_year or res.year or ""
                r.new.append(
                    f"{res.student_full} — {res.type_label or '?'} {year}".strip()
                )

    # Když selhaly úplně všechny síťové pokusy → kontrola se nezdařila (offline).
    if attempts and failures == attempts:
        r.error = "STAG nedostupný (offline?)"
        r.ok = False
    else:
        r.ok = True
    return r


class StagChecker(QObject):
    """Spustí ``compute_stag_check`` na vlákně a výsledek pošle signálem."""

    finished = Signal(object)  # StagCheckResult

    def __init__(self, service, user_full_name: str = "", parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._user = user_full_name
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            result = compute_stag_check(self._service, self._user)
        except Exception as exc:  # noqa: BLE001 — výsledek nesmí shodit vlákno
            result = StagCheckResult(ok=False, error=str(exc))
        # Signál se z vlákna doručí do hlavního vlákna (QueuedConnection).
        self.finished.emit(result)


class StagChangesPreviewDialog(QDialog):
    """Rychlý náhled, co se ve STAG změnilo / co je nového — před importem."""

    def __init__(self, result: StagCheckResult, parent=None) -> None:
        super().__init__(parent)
        self.result = result
        self.open_import = False
        self.setWindowTitle(tr("Změny ve STAG — náhled"))
        self.setMinimumSize(620, 460)

        layout = QVBoxLayout(self)
        view = QTextBrowser()
        view.setOpenExternalLinks(False)
        view.setHtml(self._build_html(result))
        layout.addWidget(view, stretch=1)

        row = QHBoxLayout()
        btn_close = QPushButton(tr("Zavřít"))
        btn_close.clicked.connect(self.reject)
        self.btn_import = QPushButton(tr("📥 Otevřít Import ze STAG…"))
        self.btn_import.clicked.connect(self._go_import)
        self.btn_import.setEnabled(result.total_changes > 0)
        row.addStretch()
        row.addWidget(btn_close)
        row.addWidget(self.btn_import)
        layout.addLayout(row)

    def _go_import(self) -> None:
        self.open_import = True
        self.accept()

    @staticmethod
    def _section(title: str, items: list[str], color: str) -> str:
        if not items:
            return ""
        lis = "".join(f"<li>{i}</li>" for i in items)
        return (
            f"<h3 style='color:{color};margin:10px 0 4px;'>{title} ({len(items)})</h3>"
            f"<ul style='margin:0 0 8px 0;'>{lis}</ul>"
        )

    def _build_html(self, r: StagCheckResult) -> str:
        if not r.ok:
            return (
                "<p>⚠ Kontrolu se nepodařilo dokončit "
                f"({r.error or 'STAG nedostupný'}).</p>"
            )
        # Sekce „zkontrolováno a aktuální" je hlavně pro kontrolu/debug — vidíš,
        # které práce kontrola opravdu prošla a jsou v souladu se STAG.
        checked_section = self._section(
            "✓ Zkontrolováno a aktuální", r.up_to_date, "#2e7d32"
        )
        if r.total_changes == 0:
            head = (
                "<p style='color:#2e7d32;'>✓ <b>Vše aktuální</b> — žádné změny "
                f"ani nové práce ve STAG (prošlo {r.checked} prací).</p>"
            )
            return head + checked_section
        body = (
            self._section("🆕 Nové práce ve STAG (nemáš v aplikaci)", r.new, "#1565c0")
            + self._section("🔄 Vedené práce se změnou", r.supervised, "#ef6c00")
            + self._section("🔄 Oponované práce se změnou", r.opposing, "#ef6c00")
        )
        return (
            "<p>Tohle STAG nabízí navíc oproti tvé databázi. Detaily a stažení "
            "provedeš v <b>Import ze STAG</b>.</p>" + body + checked_section
        )
