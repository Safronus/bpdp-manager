"""Tichá kontrola na pozadí — jsou ve STAG změny pro aktuální akademický rok?

Zjišťuje (read-only, bez zápisu do DB):
- u **vedených prací „V řešení"** změnu stavu nebo chybějící druh souboru,
- u **oponentur aktuálního roku** změnu STAG stavu nebo chybějící druh souboru,
- **nové práce** ve STAG (dle jména), které ještě nemáš v databázi.

Běží na vlákně; výsledek se hlásí signálem ``StagChecker.finished``. Logika
porovnání se sdílí se synchronizačním dialogem (``stag_sync_dialog``).
"""

from __future__ import annotations

import re
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
    # ID dotčených prací — z náhledu lze rovnou otevřít aktualizaci (subset).
    supervised_ids: list[str] = field(default_factory=list)
    opposing_ids: list[str] = field(default_factory=list)

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

    def change_keyset(self) -> set:
        """Množina „klíčů" změn (ID prací + popisy nových) — pro detekci, zda
        další kontrola přinesla **něco nového** (vs. už zobrazené)."""
        return set(self.supervised_ids) | set(self.opposing_ids) | set(self.new)

    def to_pending(self) -> dict:
        """Serializace pending změn pro uložení na disk (přežití restartu)."""
        return {
            "supervised": self.supervised,
            "supervised_ids": self.supervised_ids,
            "opposing": self.opposing,
            "opposing_ids": self.opposing_ids,
            "new": self.new,
            "checked": self.checked,
        }

    @classmethod
    def from_pending(cls, d: dict) -> StagCheckResult:
        """Rekonstrukce z uložených pending změn (po restartu) — vždy ``ok``."""
        return cls(
            ok=True,
            checked=int(d.get("checked", 0) or 0),
            supervised=list(d.get("supervised", [])),
            opposing=list(d.get("opposing", [])),
            new=list(d.get("new", [])),
            supervised_ids=list(d.get("supervised_ids", [])),
            opposing_ids=list(d.get("opposing_ids", [])),
        )


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
            r.supervised_ids.append(t.id)
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
            r.opposing_ids.append(o.id)
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

    def __init__(self, result: StagCheckResult, parent=None, *, on_sync=None) -> None:
        super().__init__(parent)
        self.result = result
        # on_sync(opposing: bool) -> bool — spustí aktualizaci subsetu (vedené
        # nebo oponované) a vrátí, zda se něco změnilo. Okno se NEzavírá, takže
        # jde aplikovat obě role po sobě. Když je None (testy / fallback),
        # tlačítka se chovají po staru (nastaví flag + zavřou).
        self._on_sync = on_sync
        self.open_import = False
        self.did_sync = False            # proběhla aspoň jedna aktualizace
        self._sup_done = False
        self._opp_done = False
        # Zpětná kompatibilita (jednorázové chování bez callbacku).
        self.open_sync_supervised = False
        self.open_sync_opposing = False
        self.setWindowTitle(tr("Změny ve STAG — náhled"))
        self.setMinimumSize(620, 460)

        layout = QVBoxLayout(self)
        self._view = QTextBrowser()
        self._view.setOpenExternalLinks(False)
        self._view.setHtml(self._build_html(result))
        layout.addWidget(self._view, stretch=1)

        row = QHBoxLayout()
        btn_close = QPushButton(tr("Zavřít"))
        btn_close.clicked.connect(self.reject)
        self.btn_sync_sup = QPushButton(
            tr("🔄 Aktualizovat vedené ({n})…").format(n=result.supervised_changes)
        )
        self.btn_sync_sup.setToolTip(tr(
            "Otevře aktualizaci ze STAG jen pro vedené práce se zjištěnou "
            "změnou — návrhy (stav, soubory) budou rovnou předpřipravené."
        ))
        self.btn_sync_sup.clicked.connect(lambda: self._do_sync(opposing=False))
        self.btn_sync_sup.setEnabled(result.supervised_changes > 0)
        self.btn_sync_opp = QPushButton(
            tr("🔄 Aktualizovat oponované ({n})…").format(n=result.opposing_changes)
        )
        self.btn_sync_opp.setToolTip(tr(
            "Otevře aktualizaci ze STAG jen pro oponované práce se zjištěnou "
            "změnou — návrhy (stav, soubory) budou rovnou předpřipravené."
        ))
        self.btn_sync_opp.clicked.connect(lambda: self._do_sync(opposing=True))
        self.btn_sync_opp.setEnabled(result.opposing_changes > 0)
        self.btn_import = QPushButton(tr("📥 Otevřít Import ze STAG…"))
        self.btn_import.setToolTip(tr(
            "Pro NOVÉ práce ze STAG, které ještě nemáš v aplikaci — otevře "
            "plný import (vyhledání + stažení)."
        ))
        self.btn_import.clicked.connect(self._go_import)
        self.btn_import.setEnabled(result.new_works > 0)
        row.addStretch()
        row.addWidget(btn_close)
        row.addWidget(self.btn_import)
        row.addWidget(self.btn_sync_opp)
        row.addWidget(self.btn_sync_sup)
        layout.addLayout(row)

    def _go_import(self) -> None:
        self.open_import = True
        self.accept()

    def _do_sync(self, opposing: bool) -> None:
        """Spustí aktualizaci dané role **bez zavření** okna (lze i druhou roli).

        Bez callbacku (``on_sync`` = None) spadne na staré jednorázové chování
        (nastaví flag a zavře) — kvůli zpětné kompatibilitě a testům.
        """
        if self._on_sync is None:
            if opposing:
                self.open_sync_opposing = True
            else:
                self.open_sync_supervised = True
            self.accept()
            return
        # Předáme ID z VLASTNÍHO výsledku dialogu (ne z hlavního okna) — kdyby
        # mezitím doběhla nová kontrola, aktualizujeme přesně to, co vidíš.
        ids = self.result.opposing_ids if opposing else self.result.supervised_ids
        changed = bool(self._on_sync(opposing, ids))
        if not changed:
            return   # uživatel nic neaplikoval → tlačítko necháme aktivní
        self.did_sync = True
        if opposing:
            self._opp_done = True
            self.btn_sync_opp.setEnabled(False)
            self.btn_sync_opp.setText(tr("✓ Oponované vyřízeno"))
        else:
            self._sup_done = True
            self.btn_sync_sup.setEnabled(False)
            self.btn_sync_sup.setText(tr("✓ Vedené vyřízeno"))
        self._view.setHtml(self._build_html(self.result))

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
        done_note = (
            "<h3 style='color:#2e7d32;margin:10px 0 4px;'>✓ {what} — aktualizováno</h3>"
        )
        sup_section = (
            done_note.format(what="Vedené práce")
            if self._sup_done
            else self._section("🔄 Vedené práce se změnou", r.supervised, "#ef6c00")
        )
        opp_section = (
            done_note.format(what="Oponované práce")
            if self._opp_done
            else self._section("🔄 Oponované práce se změnou", r.opposing, "#ef6c00")
        )
        body = (
            self._section("🆕 Nové práce ve STAG (nemáš v aplikaci)", r.new, "#1565c0")
            + sup_section + opp_section
        )
        return (
            "<p>Tohle STAG nabízí navíc oproti tvé databázi. Změny u "
            "existujících prací aplikuješ rovnou tlačítky "
            "<b>🔄 Aktualizovat vedené / oponované</b> dole — <b>okno zůstane "
            "otevřené</b>, takže můžeš po sobě vyřídit obě role (každé se otevře "
            "jen s dotčenými pracemi a předpřipravenými návrhy — stav, text "
            "práce, posudky i průběh obhajoby). Nové práce stáhneš přes "
            "<b>📥 Import ze STAG</b>.</p>"
            + body + checked_section
        )


# ── tichá kontrola stavu obhajob (pro vizualizaci v záložce Komise) ──────────

def _fold_name(s: str) -> str:
    import unicodedata
    nfd = unicodedata.normalize("NFD", s or "")
    return "".join(ch for ch in nfd if not unicodedata.combining(ch)).lower().strip()


def fetch_defense_states(service) -> dict:
    """Síťově zjistí STAG stav vedených (V řešení) a oponentur akt. roku se STAG
    ID — **bez zápisu do DB**. Vrátí ``{klíč: stav}``: klíč = osobní číslo
    (Axxxxx uppercase) i foldované jméno; stav = ``ThesisStatus.value``
    (``defended`` / ``failed`` / …). Slouží k vizualizaci „kdo už dokončil"
    v rozpisu komisí (párování přes osobní číslo / jméno)."""
    out: dict[str, str] = {}

    def record(code, *keys) -> None:
        mapped = STAG_STATE_TO_STATUS.get(code)
        if mapped is None:
            return
        for k in keys:
            if k:
                out[k] = mapped.value

    for t in service.list_theses():
        if t.status != ThesisStatus.IN_PROGRESS or not t.adipidno:
            continue
        code, _files, err = _fetch_target_state(t.adipidno)
        if err:
            continue
        student = service.get_student(t.student_id) if t.student_id else None
        keys = []
        if student:
            if student.university_id:
                keys.append(student.university_id.strip().upper())
            keys.append(_fold_name(f"{student.first_name} {student.last_name}"))
        record(code, *keys)

    current = service.current_academic_year()
    for o in service.list_opposing_theses():
        if o.academic_year != current or not o.adipidno:
            continue
        code, _files, err = _fetch_target_state(o.adipidno)
        if err:
            continue
        record(code, _fold_name(f"{o.student_first_name} {o.student_last_name}"))
    return out


class KomiseStateChecker(QObject):
    """Na vlákně zjistí STAG stav obhajob mých studentů; výsledek pošle signálem."""

    finished = Signal(object)  # dict {klíč: stav}

    def __init__(self, service, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            states = fetch_defense_states(self._service)
        except Exception:  # výsledek nesmí shodit vlákno
            states = {}
        self.finished.emit(states)


# ── statistika obhajob komisí (všichni studenti, párování dle jména) ─────────

def _needs_committee_query(slot_dt, now, grace_min: int = 30) -> bool:
    """Má smysl se STAG ptát na tento slot? Až **po čase obhajoby + grace**.

    Dřív student logicky nemá výsledek (čeká), takže dotaz je zbytečný. Neznámý
    čas → dotaz povolíme (radši zjistit).
    """
    if slot_dt is None:
        return True
    from datetime import timedelta

    return now >= slot_dt + timedelta(minutes=grace_min)


def _match_committee_result(results, slot, committee):
    """Z výsledků STAG (hledání dle příjmení) napáruje práci jednoho slotu.

    Páruje **podle jména** (množina tokenů jména/příjmení, bez diakritiky),
    zpřesněno **typem** (Bc=bakalářská / Mgr=diplomová) a **akademickým rokem**
    komise. Rok obhajoby (``r.year``) musí spadat do akademického roku komise
    (``RRRR/RRRR`` → kterýkoli z obou roků — podzimní i jarní termín); záznam
    z **prokazatelně jiného roku** se zahodí (ochrana proti jmenovcům z minulých
    let). Vrací :class:`StagThesisResult` nebo ``None``.
    """
    slot_set = set(_fold_name(slot.student_name).split())
    if not slot_set:
        return None
    level = (committee.level or "").strip().lower()
    type_kw = "bakal" if level == "bc" else "diplom" if level == "mgr" else ""
    target_years = set(re.findall(r"\d{4}", committee.academic_year or ""))

    candidates = []
    for r in results:
        res_set = set(_fold_name(f"{r.surname} {r.name}").split())
        if not res_set or not (res_set <= slot_set or slot_set <= res_set):
            continue
        if type_kw and r.type_label and type_kw not in r.type_label.lower():
            continue
        # Známý rok obhajoby mimo akademický rok komise → jmenovec z jiných let.
        if target_years and r.year and r.year not in target_years:
            continue
        candidates.append(r)

    if not candidates:
        return None
    # Preferuj práci s rokem obhajoby PŘÍMO v akademickém roce komise, pak se
    # stavem; bez vyplněného roku ber až jako poslední (nelze rozlišit jistě).
    exact = [r for r in candidates if r.year in target_years]
    pool = exact or candidates
    return next((r for r in pool if r.status_code), pool[0])


def fetch_committee_defense_states(
    service, committees, now, prior=None, *, grace_min: int = 30,
    progress=None, force: bool = False
) -> dict:
    """Síťově (read-only) zjistí kategorie obhajob studentů ``committees``.

    Vrací ``{klíč: kategorie}`` (klíč = osobní číslo / foldované jméno; kategorie
    z :mod:`services.komise_stats`). Šetří STAG:

    - **terminální** stavy z ``prior`` (cache) se znovu nedotazují,
    - **tichá kontrola** (``force=False``) řeší **jen aktuální den** a až po
      **času obhajoby + ``grace_min``**. Předchozí dny se znovu neptají (jsou
      v cache z minula), budoucí ještě neobhájili — díky tomu po startu
      nezatěžuje STAG kontrolou všech studentů,
    - **ruční „Aktualizovat"** (``force=True``) časové okno ignoruje a dotáže
      **všechny zbývající** (ne-terminální) studenty, **jejichž obhajoba je dnes
      nebo dříve** (budoucí dny se přeskočí); průběh totiž může jít rychleji, než
      je v harmonogramu,
    - na každé **příjmení** jeden STAG dotaz (sdílený mezi jmenovci).

    Studenty bez napárování ponechá tak, jak byli (typicky „bez obhajoby").
    """
    from ..services import stag_api
    from ..services.komise_stats import TERMINAL, category_from_code, slot_key
    from ..services.thesis_service import ThesisService

    out = dict(prior or {})
    pending: dict[str, list] = {}
    for c in committees:
        for s in c.slots:
            key = slot_key(s.personal_number, s.student_name)
            if out.get(key) in TERMINAL:
                continue
            dt = ThesisService._parse_slot_dt(s.date, s.time)
            if force:
                # Vynucená kontrola: jen aktuální den (a dříve), ne budoucí dny
                # — ty studenti logicky ještě neobhájili.
                if dt is not None and dt.date() > now.date():
                    continue
            else:
                # Tichá kontrola: JEN aktuální den a až po čase obhajoby + grace.
                # Předchozí dny jsou v cache, budoucí ještě neobhájili.
                if (dt is None or dt.date() != now.date()
                        or not _needs_committee_query(dt, now, grace_min)):
                    continue
            surname = _surname_of(s.student_name)
            if not surname:
                continue
            pending.setdefault(_fold_name(surname), []).append((key, s, c, surname))

    total = sum(len(items) for items in pending.values())
    done = 0
    if progress is not None:
        progress(done, total)
    for items in pending.values():
        surname = items[0][3]
        try:
            results = stag_api.search_theses(surname, "", stag_api.ROLE_OPPONENT)
        except Exception:  # offline/parser; necháme studenta „bez obhajoby"
            results = []
        for key, slot, committee, _sn in items:
            match = _match_committee_result(results, slot, committee)
            if match is not None:
                out[key] = category_from_code(match.status_code)
        done += len(items)
        if progress is not None:
            progress(done, total)
    return out


class StagConnectivityChecker(QObject):
    """Na vlákně ověří dostupnost STAGu; výsledek pošle signálem (pro indikátor)."""

    finished = Signal(bool, str)  # (dostupný, popis chyby)

    def __init__(self, timeout: float = 5.0, parent=None) -> None:
        super().__init__(parent)
        self._timeout = timeout
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        from ..services import stag_api

        try:
            ok, detail = stag_api.check_reachable(self._timeout)
        except Exception as exc:  # výsledek nesmí shodit vlákno
            ok, detail = False, str(exc)
        self.finished.emit(ok, detail)


class KomiseStatsChecker(QObject):
    """Na vlákně zjistí kategorie obhajob studentů zadaných komisí (s cache)."""

    finished = Signal(object)   # dict {klíč: kategorie}
    progress = Signal(int, int)  # (zkontrolováno, celkem)

    def __init__(self, service, committees, now, prior=None, parent=None, *,
                 force: bool = False) -> None:
        super().__init__(parent)
        self._service = service
        self._committees = list(committees)
        self._now = now
        self._prior = dict(prior or {})
        self._force = force
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            states = fetch_committee_defense_states(
                self._service, self._committees, self._now, self._prior,
                force=self._force,
                progress=lambda done, total: self.progress.emit(done, total))
        except Exception:  # výsledek nesmí shodit vlákno
            states = self._prior
        self.finished.emit(states)
