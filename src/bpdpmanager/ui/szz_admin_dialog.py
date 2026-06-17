"""Admin okno SZZ — přihlášení do portálu „Zapisovatel u státnic" + stav.

F1: vestavěný prohlížeč pro přihlášení (heslo se neukládá), indikátor stavu
přihlášení/role a testovací stažení jednoho studenta (ověření pipeline v appce).
Tahání do statistik a tichá kontrola přijdou v dalších fázích.
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
from ..services.szz_portal import (
    PORTAL_URL,
    STATUS_LOGGED_OUT,
    STATUS_NO_ROLE,
    STATUS_READY,
    SzzPortalSession,
)

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
            status, ("⏳", tr("Neznámý stav"), "#9aa0a6"))
        self.lbl_status.setText(f"{icon} {tr(text)}")
        self.lbl_status.setStyleSheet(f"font-weight:bold; color:{color};")
        self.btn_fetch.setEnabled(status == STATUS_READY)

    # ── testovací stažení jednoho studenta ────────────────────────────────
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
