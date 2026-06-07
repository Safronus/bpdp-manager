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
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from ..models.enums import AttachmentKind, ThesisStatus
from ..services import stag_api
from .stag_import_dialog import _SECTION_TO_KIND, STAG_STATE_TO_STATUS
from .stag_sync_dialog import ROLE_OPPONENT, ROLE_SUPERVISOR, _fetch_target_state


@dataclass
class StagCheckResult:
    """Výsledek tiché kontroly. ``ok=False`` = kontrolu nešlo dokončit (offline)."""

    ok: bool = False
    error: str = ""
    supervised_changes: int = 0   # vedené práce „V řešení" se změnou
    opposing_changes: int = 0     # oponentury akt. roku se změnou
    new_works: int = 0            # práce ve STAG, které nemáš v DB
    checked: int = 0              # kolik existujících prací prošlo

    @property
    def total_changes(self) -> int:
        return self.supervised_changes + self.opposing_changes + self.new_works


def _has_missing_kind(stag_files, local_kinds: set) -> bool:
    """True, když STAG nabízí druh souboru, který u práce (aktuálně) nemáš."""
    for sf in stag_files:
        kind = _SECTION_TO_KIND.get(sf.section, AttachmentKind.OTHER)
        if kind not in local_kinds:
            return True
    return False


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
        if status_changed or _has_missing_kind(files, local_kinds):
            r.supervised_changes += 1

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
        if code_changed or _has_missing_kind(files, local_kinds):
            r.opposing_changes += 1

    # 3) Nové práce ve STAG (dle jména), které v DB nemáš.
    surname = _surname_of(user_full_name)
    if surname:
        new_adip: set[str] = set()
        for role in (ROLE_SUPERVISOR, ROLE_OPPONENT):
            attempts += 1
            try:
                results = stag_api.search_theses("", surname, _person_role(role))
            except Exception:  # noqa: BLE001 — síť/parser; bereme jako neúspěch pokusu
                failures += 1
                continue
            for res in results:
                if res.adipidno and res.adipidno not in db_adip:
                    new_adip.add(res.adipidno)
        r.new_works = len(new_adip)

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
