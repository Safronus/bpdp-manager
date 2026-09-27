"""Smoke test instalace bez interakce: ``bpdp-manager --self-test``.

Slouží hlavně k ověření ZABALENÉ aplikace (PyInstaller ``.app``) — v CI i
lokálně po buildu. Kontroluje:

1. přibalené resources (nápověda CZ/EN, komise SZZ, ikona, certifikát MyQ,
   slovník pravopisu, výchozí šablony, PDF složení komisí),
2. importy těžkých závislostí (Qt vč. WebEngine, pydantic, cryptography,
   pypdf, openpyxl, spylls) a u zabalené aplikace i helper QtWebEngineProcess,
3. že jde reálně načíst komise ze seedu, zkontrolovat pravopis a sestavit
   hlavní okno; v zabalené aplikaci navíc skutečně spustí render proces
   QtWebEngine (lokální HTML + JavaScript).

Běží VÝHRADNĚ nad dočasnou datovou složkou (``BPDPMANAGER_DATA_DIR``) — na
reálná data uživatele nesahá. Síť nepoužívá: event loop běží jen krátce pro
WebEngine test (lokální HTML) a to ještě PŘED sestavením hlavního okna, takže
žádné jeho odložené kontroly STAG ani aktualizací neproběhnou.

Návratový kód: 0 = vše v pořádku, 1 = něco chybí (vypíše co).
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path
from typing import TextIO

_PKG = Path(__file__).resolve().parent

#: Soubory, které musí být v balíčku (relativně k ``bpdpmanager/``), neprázdné.
REQUIRED_FILES = (
    "resources/napoveda.md",
    "resources/napoveda_en.md",
    "resources/komise_szz.json",
    "resources/icons/app_icon.png",
    "resources/certs/myq_ca.pem",
    "resources/dictionaries/cs_CZ.aff",
    "resources/dictionaries/cs_CZ.dic",
)
#: Složky, které musí obsahovat aspoň jeden soubor (i v podsložkách —
#: komise_pdfs jsou rozdělené po akademických rocích).
REQUIRED_DIRS = (
    "resources/default_templates",
    "resources/komise_pdfs",
)
#: Moduly, které se musí dát naimportovat (v zabalené appce = byly přibaleny).
REQUIRED_MODULES = (
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtPrintSupport",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "pydantic",
    "cryptography.hazmat.primitives.ciphers.aead",
    "pypdf",
    "openpyxl",
    "spylls",
)


#: Jak dlouho čekat na render proces QtWebEngine (první start Chromia je pomalý).
WEBENGINE_TIMEOUT_MS = 45_000


class _Report:
    def __init__(self, out: TextIO) -> None:
        self.out = out
        self.failures: list[str] = []

    def ok(self, msg: str) -> None:
        print(f"✅ {msg}", file=self.out)

    def warn(self, msg: str) -> None:
        print(f"⚠️ {msg}", file=self.out)

    def bad(self, msg: str) -> None:
        self.failures.append(msg)
        print(f"❌ {msg}", file=self.out)

    def check(self, cond: bool, msg: str) -> None:
        (self.ok if cond else self.bad)(msg)


def _check_resources(r: _Report) -> None:
    for rel in REQUIRED_FILES:
        p = _PKG / rel
        r.check(p.is_file() and p.stat().st_size > 0, f"soubor {rel}")
    for rel in REQUIRED_DIRS:
        p = _PKG / rel
        n = sum(1 for f in p.rglob("*") if f.is_file()) if p.is_dir() else 0
        r.check(n > 0, f"složka {rel} ({n} souborů)")


def _check_imports(r: _Report, frozen: bool) -> None:
    for mod in REQUIRED_MODULES:
        try:
            importlib.import_module(mod)
            r.ok(f"import {mod}")
        except Exception as exc:  # chceme vidět jakoukoli chybu
            r.bad(f"import {mod}: {type(exc).__name__}: {exc}")
    if frozen:
        # QtWebEngine potřebuje v bundlu pomocný proces (vestavěný prohlížeč
        # SZZ admin). Bez něj by import prošel, ale stránka by se nenačetla.
        meipass = Path(getattr(sys, "_MEIPASS", _PKG.parent))
        helpers = list(meipass.parent.rglob("QtWebEngineProcess"))
        r.check(bool(helpers), "helper QtWebEngineProcess v bundlu")


def _check_webengine(r: _Report) -> None:
    """Skutečně spustí render proces QtWebEngine: načte HTML a vyhodnotí JS.

    Import a přítomnost helperu nestačí — tohle ověří, že se QtWebEngineProcess
    opravdu spustí (podpis, cesty k resources, sandbox), tj. že půjde vestavěný
    prohlížeč v SZZ admin.
    """
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWebEngineCore import QWebEnginePage

    page = QWebEnginePage()
    state: dict = {}
    loop = QEventLoop()

    def _js_done(value) -> None:
        state["js"] = value
        loop.quit()

    def _loaded(ok: bool) -> None:
        state["loaded"] = ok
        if ok:
            page.runJavaScript("6 * 7", 0, _js_done)
        else:
            loop.quit()

    page.loadFinished.connect(_loaded)
    QTimer.singleShot(WEBENGINE_TIMEOUT_MS, loop.quit)
    page.setHtml("<html><body>bpdp self-test</body></html>")
    loop.exec()
    r.check(state.get("loaded") is True and state.get("js") == 42,
            f"QtWebEngine render proces (načtení={state.get('loaded')}, "
            f"JS 6*7={state.get('js')!r})")
    # Smazat hned (deleteLater bez event loopu neproběhne a Qt by při ukončení
    # varovalo „Release of profile requested but WebEnginePage still not deleted").
    import shiboken6

    shiboken6.delete(page)


def _check_app(r: _Report, data_dir: Path, webengine: bool) -> None:
    from PySide6.QtCore import QCoreApplication, Qt
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        # QtWebEngine chce sdílené OpenGL kontexty nastavené PŘED QApplication.
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    # Předáme jen argv[0] — Qt nesmí parsovat naše přepínače (--self-test).
    _app = QApplication.instance() or QApplication([sys.argv[0]])

    from .services import ThesisService, spellcheck
    from .storage import JsonRepository

    def _service(name: str) -> ThesisService:
        d = data_dir / name
        d.mkdir(parents=True, exist_ok=True)
        return ThesisService(
            JsonRepository(path=d / "db.json", backup_path=d / "db.json.bak")
        )

    seeded = _service("seed")
    seeded.maybe_seed_defaults()
    r.check(len(seeded.list_obory()) > 0,
            f"výchozí obory ({len(seeded.list_obory())})")
    seeded.load_komise_seed()
    n_kom = len(seeded.list_committees())
    r.check(n_kom > 0, f"komise SZZ ze seedu ({n_kom})")

    r.check(spellcheck.is_available() and spellcheck.check_word("práce"),
            "kontrola pravopisu (slovník cs_CZ)")

    # WebEngine PŘED hlavním oknem: jeho event loop pak nemůže spustit žádné
    # odložené akce okna (to ještě neexistuje).
    if webengine:
        _check_webengine(r)
    else:
        r.warn("QtWebEngine render proces: přeskočeno (testuje se v zabalené aplikaci)")

    # Hlavní okno nad PRÁZDNOU službou — žádné práce ani komise, takže se
    # nic nesnaží kontaktovat STAG. Okno se nezobrazuje ani nezavírá.
    from .ui import MainWindow

    window = MainWindow(_service("ui"))
    r.check(window.tabs.count() > 0, f"hlavní okno ({window.tabs.count()} záložek)")
    window.deleteLater()


def run_selftest(out: TextIO | None = None, *, webengine: bool | None = None) -> int:
    """Spustí smoke test; vrací 0 (OK) nebo 1 (selhání).

    ``webengine`` — spustit i skutečný render proces QtWebEngine. Výchozí
    ``None`` = jen v zabalené aplikaci (tam je bundlování nejrizikovější; ze
    zdrojů by v testech zbytečně startoval Chromium).
    """
    from . import __version__
    from .config import ENV_DATA_DIR

    r = _Report(out or sys.stdout)
    frozen = bool(getattr(sys, "frozen", False))
    if webengine is None:
        webengine = frozen
    r.ok(f"BPDPManager {__version__} "
         f"({'zabalená aplikace' if frozen else 'ze zdrojů'}, "
         f"Python {sys.version.split()[0]})")

    _check_resources(r)
    _check_imports(r, frozen)

    previous = os.environ.get(ENV_DATA_DIR)
    with tempfile.TemporaryDirectory(prefix="bpdp-selftest-") as td:
        os.environ[ENV_DATA_DIR] = td
        try:
            _check_app(r, Path(td), webengine)
        except Exception as exc:
            r.bad(f"běh aplikace: {type(exc).__name__}: {exc}")
        finally:
            if previous is None:
                os.environ.pop(ENV_DATA_DIR, None)
            else:
                os.environ[ENV_DATA_DIR] = previous

    if r.failures:
        print(f"\n❌ SELF-TEST SELHAL ({len(r.failures)} chyb)", file=r.out)
        return 1
    print("\n✅ SELF-TEST OK", file=r.out)
    return 0
