"""Admin okno SZZ — ovládací panel nad portálem „Zapisovatel u státnic".

Vestavěný prohlížeč pro přihlášení (heslo se neukládá — jen cookie session
v profilu), indikátor stavu přihlášení/role a:
- ruční stažení jednoho studenta dle os. čísla (📂 i z cache, bez STAG),
- hromadná **inkrementální kontrola** komisí (zbývající / všechny / Stop) +
  tichá kontrola dnešních po přihlášení, s re-login flow při vypršení session.

Stažené záznamy se ukládají do cache (``ThesisService.upsert_szz_result``) a
zobrazují se v záložce „Průběh SZZ" ve Statistice obhajob.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..services.szz_parser import szz_to_check
from ..services.szz_portal import (
    PORTAL_URL,
    STATUS_LOGGED_OUT,
    STATUS_NO_ROLE,
    STATUS_READY,
    SzzBatchChecker,
    SzzPortalSession,
)

_MUTED = "#9aa0a6"

_STATUS_UI = {
    STATUS_LOGGED_OUT: ("🔴", "Nepřihlášen — přihlas se ve STAG", "#e53935"),
    STATUS_NO_ROLE: ("⚠️", "Přihlášen, ale chybí role ZAPISOVATEL STÁTNIC", "#fb8c00"),
    STATUS_READY: ("🟢", "Přihlášen (Zapisovatel státnic)", "#43a047"),
}


def _format_record(rec) -> str:
    lines = [f"os. číslo: {rec.os_cislo or '—'}", ""]
    if rec.subjects:
        lines.append(f"PŘEDMĚTY SZZ ({len(rec.subjects)}):")
        for s in rec.subjects:
            lines += [
                f"  • {s.katedra}/{s.predmet}: {s.znamka_text or '—'} "
                f"— {s.zkousejici or '—'} (id {s.ucitidno})",
                f"      pokus {s.pokus or '—'}, {s.datum or '—'}, {s.jazyk or '—'}",
                f"      otázky/průběh: {(s.prubeh[:160] + '…') if s.prubeh else '—'}",
            ]
    if rec.defense:
        d = rec.defense
        lines += [
            "", "OBHAJOBA:",
            f"  hodnocení {d.znamka_text or '—'}, vedoucí {d.znamka_vedouci or '—'}, "
            f"oponent {d.znamka_oponent or '—'}",
            f"  zkoušející {d.zkousejici or '—'} (id {d.ucitidno}), adipidno {d.adipidno or '—'}",
        ]
    if rec.overall:
        o = rec.overall
        lines += [
            "", "CELKOVÝ VÝSLEDEK SZZ:",
            f"  zkoušky {o.vysledek_zkousek_text or '—'}, studium {o.vysledek_studia or '—'}",
            f"  komise {o.komise or '—'}, {o.datum or '—'} {o.cas or ''}",
        ]
    return "\n".join(lines)


class SzzAdminDialog(QDialog):
    def __init__(self, session: SzzPortalSession, service,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Státnice (admin) — Zapisovatel u státnic"))
        self.resize(1300, 860)
        self.session = session
        self.service = service
        self._alive = True   # async callbacky nesmí sáhnout na zavřený dialog
        self._batch = None
        self._auto_done = False   # tichá kontrola dnešních proběhla?

        root = QVBoxLayout(self)

        bar = QHBoxLayout()
        self.lbl_status = QLabel("⏳ " + tr("Zjišťuji stav…"))
        self.lbl_status.setStyleSheet("font-weight:bold;")
        bar.addWidget(self.lbl_status)
        bar.addStretch(1)
        self.btn_refresh = QPushButton("🔄 " + tr("Obnovit stav"))
        self.btn_refresh.clicked.connect(self._refresh_status)
        bar.addWidget(self.btn_refresh)
        bar.addWidget(QLabel("  " + tr("os. číslo") + ":"))
        self.os_input = QLineEdit()
        self.os_input.setPlaceholderText("A12345")
        self.os_input.setMaximumWidth(110)
        self.os_input.returnPressed.connect(self._fetch)
        bar.addWidget(self.os_input)
        self.btn_fetch = QPushButton("▶ " + tr("Načíst studenta"))
        self.btn_fetch.clicked.connect(self._fetch)
        bar.addWidget(self.btn_fetch)
        self.btn_cache = QPushButton("📂 " + tr("Z cache"))
        self.btn_cache.setToolTip(tr("Zobrazit uložený záznam (bez STAG)."))
        self.btn_cache.clicked.connect(self._from_cache)
        bar.addWidget(self.btn_cache)
        root.addLayout(bar)

        # Druhý řádek — hromadná inkrementální kontrola komisí.
        bar2 = QHBoxLayout()
        bar2.addWidget(QLabel(tr("Hromadná kontrola komisí:")))
        self.btn_remaining = QPushButton("🔄 " + tr("Zkontrolovat zbývající"))
        self.btn_remaining.setToolTip(tr(
            "Stáhne SZZ studentů komisí, kteří ještě nemají hotový výsledek "
            "(hotové v cache se přeskočí)."))
        self.btn_remaining.clicked.connect(lambda: self._start_batch(force=False))
        bar2.addWidget(self.btn_remaining)
        self.btn_all = QPushButton("🔁 " + tr("Zkontrolovat všechny"))
        self.btn_all.setToolTip(tr("Znovu stáhne VŠECHNY studenty komisí (i hotové)."))
        self.btn_all.clicked.connect(lambda: self._start_batch(force=True))
        bar2.addWidget(self.btn_all)
        self.btn_stop = QPushButton("⏹ " + tr("Stop"))
        self.btn_stop.clicked.connect(self._stop_batch)
        self.btn_stop.setEnabled(False)
        bar2.addWidget(self.btn_stop)
        self.lbl_progress = QLabel("")
        self.lbl_progress.setStyleSheet(f"color:{_MUTED};")
        bar2.addWidget(self.lbl_progress)
        bar2.addStretch(1)
        root.addLayout(bar2)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.view = QWebEngineView()
        self.view.setPage(self.session.login_page())
        self.view.load(QUrl(PORTAL_URL))
        split.addWidget(self.view)
        self.out = QPlainTextEdit()
        self.out.setReadOnly(True)
        self.out.setPlaceholderText(
            tr("Přihlas se vlevo, pak otestuj stažení zadáním os. čísla nahoře."))
        split.addWidget(self.out)
        split.setSizes([900, 380])
        root.addWidget(split, 1)

        # POZOR: nespouštět kontrolu stavu automaticky při otevření — skrytá
        # bg_page by načítala portál SOUČASNĚ s viditelným webview, dva souběžné
        # redirecty na login portál vyhodnotí jako „neautorizovaný požadavek".
        # Stav se zjistí až tlačítkem „Obnovit stav" (po přihlášení).
        self.btn_fetch.setEnabled(False)
        self._set_batch_enabled(False)
        self.lbl_status.setText(
            "⏳ " + tr("Přihlas se vlevo, pak klikni 🔄 Obnovit stav"))
        self.out.setPlainText(self._cache_summary())

    def _cache_summary(self) -> str:
        n = len(self.service.load_szz_results())
        if not n:
            return "📂 " + tr("Cache je zatím prázdná.")
        return (f"📂 {tr('V cache')}: {n} {tr('záznamů')}. "
                + tr("Zadej os. číslo a klikni 📂 Z cache."))

    # ── stav přihlášení/role ──────────────────────────────────────────────
    def _refresh_status(self) -> None:
        self.lbl_status.setText("⏳ " + tr("Zjišťuji stav…"))
        self.session.check_status(self._set_status)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self._alive = False
        super().closeEvent(event)

    def _set_status(self, status: str) -> None:
        if not self._alive:
            return
        icon, text, color = _STATUS_UI.get(
            status, ("⏳", tr("Neznámý stav"), _MUTED))
        self.lbl_status.setText(f"{icon} {tr(text)}")
        self.lbl_status.setStyleSheet(f"font-weight:bold; color:{color};")
        ready = status == STATUS_READY
        self.btn_fetch.setEnabled(ready)
        self._set_batch_enabled(ready)
        # Tichá kontrola dnešních studentů po prvním přihlášení (jednou).
        if ready and not self._auto_done:
            self._auto_done = True
            self._start_batch(force=False, today_only=True, silent=True)

    # ── hromadná inkrementální kontrola ───────────────────────────────────
    def _set_batch_enabled(self, enabled: bool) -> None:
        self.btn_remaining.setEnabled(enabled)
        self.btn_all.setEnabled(enabled)

    def _committee_oscisla(self, today_only: bool = False) -> list:
        import re
        from datetime import date

        cur = self.service.current_academic_year()
        today = date.today()
        out: list[str] = []
        for c in self.service.list_committees():
            if c.academic_year and c.academic_year != cur:
                continue
            for s in c.slots:
                pn = (s.personal_number or "").strip()
                if not pn:
                    continue
                if today_only:
                    nums = re.findall(r"\d+", s.date or "")
                    if len(nums) < 3 or (int(nums[2]), int(nums[1]),
                                         int(nums[0])) != (today.year,
                                                           today.month, today.day):
                        continue
                out.append(pn.upper())
        return out

    def _start_batch(self, force: bool, today_only: bool = False,
                     silent: bool = False) -> None:
        if self._batch is not None:
            return
        oscisla = self._committee_oscisla(today_only=today_only)
        to_check = szz_to_check(oscisla, self.service.load_szz_results(), force)
        if not to_check:
            if not silent:
                self.lbl_progress.setText("✅ " + tr("Nic ke kontrole (vše hotové)."))
            return
        self._set_batch_enabled(False)
        self.btn_stop.setEnabled(True)
        self.lbl_progress.setText(f"⏳ 0/{len(to_check)}")
        self._batch = SzzBatchChecker(self.session, self.service, to_check, self)
        self._batch.progress.connect(self._batch_progress)
        self._batch.finished.connect(self._batch_done)
        self._batch.start()

    def _batch_progress(self, done: int, total: int, oc: str) -> None:
        if self._alive:
            self.lbl_progress.setText(
                f"⏳ {tr('Kontroluji SZZ')} {done}/{total}…")

    def _batch_done(self, stats: dict) -> None:
        self._batch = None
        if not self._alive:
            return
        self.btn_stop.setEnabled(False)
        n = len(self.service.load_szz_results())
        if stats.get("logged_out"):
            self._auto_done = False          # po re-loginu plynule pokračovat
            self.lbl_progress.setText("⏳ " + tr("Session vypršela"))
            self.out.setPlainText("⏳ " + tr(
                "Session vypršela během kontroly — přihlas se vlevo a klikni "
                "🔄 Obnovit stav (kontrola plynule pokračuje, hotové se přeskočí)."))
            self._set_status(STATUS_LOGGED_OUT)
            return
        self._set_batch_enabled(True)
        self.lbl_progress.setText(
            f"✅ {tr('Hotovo')}: {stats['checked']} {tr('zkontrolováno')}, "
            f"{stats['failed']} {tr('chyb')} · 💾 {tr('v cache')}: {n}")

    def _stop_batch(self) -> None:
        if self._batch is not None:
            self._batch.stop()
            self.lbl_progress.setText("⏹ " + tr("Zastavuji…"))

    # ── ruční stažení jednoho studenta ────────────────────────────────────
    def _fetch(self) -> None:
        oc = self.os_input.text().strip()
        if not oc:
            self.out.setPlainText(tr("Zadej os. číslo."))
            return
        self.btn_fetch.setEnabled(False)
        self.out.setPlainText(f"▶ {tr('Načítám')} {oc}…")
        self.session.fetch_student(oc, self._fetch_done, self._fetch_progress)

    def _from_cache(self) -> None:
        oc = self.os_input.text().strip()
        if not oc:
            self.out.setPlainText(tr("Zadej os. číslo."))
            return
        rec = self.service.load_szz_results().get(oc)
        if rec is None:
            self.out.setPlainText(
                "📂 " + tr("Pro toto os. číslo není nic v cache."))
            return
        tag = tr("hotovo") if rec.terminal else tr("neúplné")
        stamp = f" ({rec.fetched_at}, {tag})" if rec.fetched_at else f" ({tag})"
        self.out.setPlainText(
            "📂 " + tr("Z cache") + stamp + "\n\n" + _format_record(rec))

    def _fetch_progress(self, msg: str) -> None:
        if not self._alive:
            return
        self.out.setPlainText(self.out.toPlainText() + "\n" + msg)

    def _fetch_done(self, rec, error: str) -> None:
        if not self._alive:
            return
        self.btn_fetch.setEnabled(True)
        if error == STATUS_LOGGED_OUT:
            self.out.setPlainText(
                "⏳ " + tr("Session vypršela — přihlas se znovu vlevo a zkus to znova."))
            self._set_status(STATUS_LOGGED_OUT)
            return
        if rec is None:
            self.out.setPlainText("⚠️ " + tr("Student nenalezen nebo se nepodařilo načíst."))
            return
        self.service.upsert_szz_result(rec)
        n = len(self.service.load_szz_results())
        self.out.setPlainText(
            "✅ " + tr("Hotovo") + f" — 💾 {tr('uloženo do cache')} ({n})\n\n"
            + _format_record(rec))
