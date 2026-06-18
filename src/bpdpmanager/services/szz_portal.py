"""Přihlášená session do portálu IS/STAG „Zapisovatel u státnic" (QtWebEngine).

Admin funkce: data o průběhu SZZ jsou v portálu dostupná jen po přihlášení
(role *Zapisovatel státnic*). Přihlášení probíhá ve vestavěném prohlížeči
(heslo se NEUKLÁDÁ — drží se jen cookie session v profilu webview, uloženém
v **datové složce profilu aplikace**). Třetí-stranní trackery (Meta pixel, GA…)
jsou blokované.

- :class:`SzzPortalSession` — sdílený profil (perzistentní cookies) + pozaďová
  stránka pro zjištění stavu přihlášení/role a stažení dat.
- Stažení jednoho studenta řídí :class:`_StudentFetcher` (stavový automat nad
  ``loadFinished`` — vyplní hledání, vybere studenta, projede 3 záložky).

Vše je klíčované **osobním číslem**; parsování řeší ``services/szz_parser.py``.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineUrlRequestInterceptor,
)

from ..models.szz_result import SzzRecord
from .szz_parser import (
    KNOWN_PAGES,
    detect_page_name,
    has_zapisovatel_role,
    is_logged_in,
    merge_pages,
    parse_page,
)

PORTAL_URL = "https://stag.utb.cz/portal/studium/isstag/zapisovatel-statnic.html"

# Stavy přihlášení/role.
STATUS_LOGGED_OUT = "logged_out"   # 🔴 nepřihlášen / session vypršela
STATUS_NO_ROLE = "no_role"         # ⚠️ přihlášen, ale chybí role ZS
STATUS_READY = "ready"             # 🟢 přihlášen + role ZS

_TRACKER_HOSTS = (
    "facebook.com", "facebook.net", "connect.facebook.net", "fbcdn.net",
    "google-analytics.com", "analytics.google.com", "googletagmanager.com",
    "doubleclick.net", "hotjar.com", "segment.io", "googlesyndication.com",
    "fbevents",
)


class _TrackerBlocker(QWebEngineUrlRequestInterceptor):
    """Zahodí požadavky na známé trackery/reklamní sítě."""

    def interceptRequest(self, info) -> None:  # noqa: N802 (Qt API)
        host = info.requestUrl().host().lower()
        if any(t in host for t in _TRACKER_HOSTS):
            info.block(True)


def status_from_html(html_text: str) -> str:
    """Stav přihlášení/role z HTML portálu (STATUS_*)."""
    if not is_logged_in(html_text):
        return STATUS_LOGGED_OUT
    if not has_zapisovatel_role(html_text):
        return STATUS_NO_ROLE
    return STATUS_READY


class _StudentFetcher(QObject):
    """Stáhne kompletní SZZ záznam jednoho studenta (3 záložky, automaticky)."""

    finished = Signal(object, str)   # (SzzRecord|None, error)
    progress = Signal(str)

    _STEP_TIMEOUT_MS = 30000   # strop na jeden krok (navigaci) u studenta

    def __init__(self, page: QWebEnginePage, os_cislo: str) -> None:
        super().__init__()
        self.page = page
        self.os_cislo = os_cislo.strip()
        self._captured: dict = {}
        self._phase = "init"
        self._selected = False
        self._error = ""
        self._done = False   # guard proti dvojímu dokončení (timeout + callback)

    def start(self) -> None:
        from PySide6.QtCore import QTimer

        self.page.loadFinished.connect(self._on_load)
        # Timeout na krok (resetuje se po každém načtení) — když navigace u
        # studenta uvázne, neblokuje to celou dávku.
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)
        self._timer.start(self._STEP_TIMEOUT_MS)
        self.progress.emit(f"Hledám {self.os_cislo}…")
        self.page.load(QUrl(PORTAL_URL))

    def _on_load(self, ok: bool) -> None:
        if self._done:
            return
        if getattr(self, "_timer", None) is not None:
            self._timer.start(self._STEP_TIMEOUT_MS)   # progres → reset timeoutu
        self.page.toHtml(self._on_html)

    def _on_timeout(self) -> None:
        self._error = self._error or "timeout"
        self._finish()

    def _on_html(self, html_text: str) -> None:
        if self._done:
            return
        if self._phase == "init":
            self._phase = "running"
            oc = self.os_cislo
            js = (
                "(function(){var f=document.getElementById('studentSearchOsCislo');"
                "if(!f)return 'NO_FIELD';"
                f"f.value={oc!r};"
                "var b=Array.prototype.slice.call("
                "document.querySelectorAll('input[type=submit]'))"
                ".filter(function(x){return (x.value||'').indexOf('Hledat')>=0;})[0];"
                "if(b){b.click();return 'CLICK';}"
                "if(f.form){f.form.submit();return 'SUBMIT';}return 'NO_BTN';})()"
            )
            self.page.runJavaScript(js, self._after_search)
            return

        if not is_logged_in(html_text) and detect_page_name(html_text) not in KNOWN_PAGES:
            self._error = STATUS_LOGGED_OUT      # session vypršela
            return self._finish()

        page = detect_page_name(html_text)
        if page not in KNOWN_PAGES:
            if not self._selected:               # seznam výsledků → vyber studenta
                self._selected = True
                self.progress.emit("vybírám studenta…")
                js = (
                    f"(function(){{var oc={self.os_cislo!r};"
                    "var a=document.querySelectorAll('a');"
                    "for(var i=0;i<a.length;i++){if((a[i].textContent||'')"
                    ".trim()===oc){a[i].click();return 'C';}}return 'N';})()"
                )
                self.page.runJavaScript(js, self._after_select)
                return
            self._error = self._error or "not_found"
            return self._finish()

        if page not in self._captured:
            self._captured[page] = parse_page(html_text)
            self.progress.emit(f"načteno: {page} ({len(self._captured)}/3)")
        remaining = [p for p in KNOWN_PAGES if p not in self._captured]
        if not remaining:
            return self._finish()
        nxt = remaining[0]
        js = (
            f'(function(){{var a=document.querySelector(\'a[name$="X{nxt}"]\');'
            "if(!a)return null;var d=a.nextElementSibling;if(!d)return null;"
            "var l=d.querySelector('a.xg_stag_a_det')||d.querySelector('a');"
            "return l?l.href:null;})()"
        )
        self.page.runJavaScript(js, self._goto_next)

    def _after_search(self, res) -> None:
        # Když na stránce není vyhledávací pole/tlačítko, nejsme přihlášeni.
        if res in ("NO_FIELD", "NO_BTN"):
            self._error = STATUS_LOGGED_OUT
            self._finish()

    def _after_select(self, res) -> None:
        # 'N' = odkaz se jménem/os. číslem nenalezen → student není ve výsledku.
        if res != "C":
            self._error = self._error or "not_found"
            self._finish()

    def _goto_next(self, href) -> None:
        if not href:
            return self._finish()
        self.page.load(QUrl(href))

    def _finish(self) -> None:
        if self._done:
            return
        self._done = True
        if getattr(self, "_timer", None) is not None:
            self._timer.stop()
        try:
            self.page.loadFinished.disconnect(self._on_load)
        except (RuntimeError, TypeError):
            pass
        if self._error and not self._captured:
            self.finished.emit(None, self._error)
            return
        self.finished.emit(merge_pages(*self._captured.values()), "")


class SzzPortalSession(QObject):
    """Sdílený webview profil (perzistentní cookies) + pozaďová stránka."""

    def __init__(self, storage_dir: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        storage_dir = Path(storage_dir)
        storage_dir.mkdir(parents=True, exist_ok=True)
        self.profile = QWebEngineProfile("bpdp-szz", self)
        self.profile.setPersistentStoragePath(str(storage_dir))
        self.profile.setCachePath(str(storage_dir / "cache"))
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        self.profile.setHttpAcceptLanguage("cs-CZ,cs;q=0.9,en;q=0.1")
        self._blocker = _TrackerBlocker(self)
        self.profile.setUrlRequestInterceptor(self._blocker)
        # Stránky jsou děti session (ne profilu) → při zániku session se mažou
        # PŘED profilem (správné pořadí; jinak QtWebEngine varuje a hrozí pád).
        self._bg_page = QWebEnginePage(self.profile, self)
        self._login_page = QWebEnginePage(self.profile, self)
        self._fetcher: _StudentFetcher | None = None
        # QtWebEngine vyžaduje, aby stránky zanikly PŘED profilem — jinak při
        # ukončení varuje „Release of profile … Expect troubles". Při zavírání
        # appky proto stránky smažeme ručně dřív.
        from PySide6.QtCore import QCoreApplication
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._delete_pages)

    def _delete_pages(self) -> None:
        import shiboken6

        for attr in ("_login_page", "_bg_page"):
            p = getattr(self, attr, None)
            if p is not None and shiboken6.isValid(p):
                shiboken6.delete(p)
            setattr(self, attr, None)

    def login_page(self) -> QWebEnginePage:
        """Sdílená stránka pro přihlašovací okno (sdílí cookies, znovupoužitelná)."""
        return self._login_page

    def check_status(self, callback) -> None:
        """Zjistí stav přihlášení/role (STATUS_*) — načte portál na pozadí."""
        page = self._bg_page

        def on_load(ok):
            try:
                page.loadFinished.disconnect(on_load)
            except (RuntimeError, TypeError):
                pass
            page.toHtml(lambda h: callback(status_from_html(h)))

        page.loadFinished.connect(on_load)
        page.load(QUrl(PORTAL_URL))

    def fetch_student(self, os_cislo: str, on_done, on_progress=None) -> None:
        """Stáhne SZZ záznam studenta (callback ``on_done(record, error)``)."""
        self._fetcher = _StudentFetcher(self._bg_page, os_cislo)
        if on_progress:
            self._fetcher.progress.connect(on_progress)
        self._fetcher.finished.connect(on_done)
        self._fetcher.start()


class SzzBatchChecker(QObject):
    """Inkrementální kontrola seznamu os. čísel (sekvenčně, s ukládáním do cache).

    Pro každé os. číslo stáhne SZZ záznam a uloží do cache (``upsert_szz_result``).
    Při vypršení session (``STATUS_LOGGED_OUT``) se zastaví a nahlásí to
    (``finished`` s ``logged_out=True``) — UI vyzve k re-loginu a po něm se
    kontrola spustí znovu (hotové se díky cache přeskočí).
    """

    progress = Signal(int, int, str)   # done, total, current_os
    log = Signal(str)                  # řádek do detailního výpisu
    finished = Signal(dict)            # {checked, failed, total, logged_out, stopped}

    def __init__(self, session: SzzPortalSession, service,
                 oscisla, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.session = session
        self.service = service
        self.queue = list(oscisla)
        self.total = len(self.queue)
        self.done = 0
        self.checked = 0
        self.failed = 0
        self.unavailable = 0
        self.logged_out = False
        self._stop = False
        self._current = ""

    def stop(self) -> None:
        self._stop = True

    def start(self) -> None:
        self._next()

    def _next(self) -> None:
        if self._stop or not self.queue:
            return self._finish()
        self._current = self.queue.pop(0)
        self.progress.emit(self.done, self.total, self._current)
        self.session.fetch_student(self._current, self._on_one)

    def _on_one(self, rec, error: str) -> None:
        oc = self._current
        if error == STATUS_LOGGED_OUT:
            self.logged_out = True
            self.log.emit(f"{oc} — ⏳ session vypršela, kontrola pozastavena")
            return self._finish()
        if rec is not None and getattr(rec, "os_cislo", ""):
            self.service.upsert_szz_result(rec)
            self.checked += 1
            ov = getattr(rec, "overall", None)
            if ov and ov.vysledek_studia:
                self.log.emit(f"{oc} ✓ {ov.vysledek_studia}"
                              f" ({ov.vysledek_zkousek or '?'})")
            else:
                self.log.emit(f"{oc} ✓ staženo (zatím bez výsledku)")
        elif error == "not_found":
            # Nenalezen = zatím nedostupné (komise ještě neproběhla / nemáme
            # přístup) → zapamatuj jako nedostupné a příště zkus znovu.
            self.service.upsert_szz_result(SzzRecord(os_cislo=oc, unavailable=True))
            self.unavailable += 1
            self.log.emit(f"{oc} ⏳ zatím nedostupné (komise možná ještě neproběhla)")
        else:
            self.failed += 1
            reason = {"timeout": "timeout (přeskočeno)"}.get(error, "chyba")
            self.log.emit(f"{oc} ✗ {reason}")
        self.done += 1
        self._next()

    def _finish(self) -> None:
        self.finished.emit({
            "checked": self.checked, "failed": self.failed,
            "unavailable": self.unavailable, "total": self.total,
            "logged_out": self.logged_out, "stopped": self._stop,
        })
