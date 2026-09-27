from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# ── Bytecode cache mimo (potenciálně iCloud-synced) zdrojový strom ──────────
# Projekt často leží v ~/Desktop/ nebo ~/Documents/, které macOS synchronizuje
# přes iCloud Drive. iCloud nezachovává spolehlivě mtime souborů, takže sdílený
# ``__pycache__`` mezi více Macy se dostane do nekonzistentního stavu — Python
# na druhém zařízení načte starou ``.pyc`` (bez nově přidaných metod) a spadne
# s AttributeError. Přesměrujeme bytecode cache mimo zdrojový strom (do
# ~/.cache), čímž se source-adjacent ``.pyc`` ignorují. Importy heavy modulů
# jsou v ``main()`` líné, takže tohle nastavení je stihne ovlivnit.
try:
    _pyc_cache = Path.home() / ".cache" / "bpdpmanager" / "pyc"
    _pyc_cache.mkdir(parents=True, exist_ok=True)
    sys.pycache_prefix = str(_pyc_cache)
except OSError:
    pass


def _configure_tls() -> None:
    """Zabalená aplikace: HTTPS důvěřuje certifikátům z přibaleného ``certifi``.

    PyInstaller přibalí OpenSSL z build stroje (CI), který hledá certifikáty
    v tamní cestě (``/Library/Frameworks/Python.framework/…/etc/openssl``). Na
    jiném Macu neexistuje → OpenSSL nemá žádnou důvěryhodnou CA a každé HTTPS
    (STAG, kontrola aktualizací, e-mail) selže na ``CERTIFICATE_VERIFY_FAILED``
    — aplikace pak hlásí STAG jako offline. ``SSL_CERT_FILE`` čte OpenSSL při
    vytvoření každého výchozího SSL kontextu. Hodnotu nastavenou uživatelem
    nepřepisujeme; ze zdrojů se nic nemění (tam systémové úložiště funguje).
    """
    if not getattr(sys, "frozen", False) or os.environ.get("SSL_CERT_FILE"):
        return
    try:
        import certifi
    except ImportError:  # nemělo by nastat — certifi je běhová závislost
        return
    os.environ["SSL_CERT_FILE"] = certifi.where()


def _examples_dir() -> Path:
    """Složka ``examples/`` — v repu vedle ``src/``, v zabalené appce v bundlu."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", ".")) / "examples"
    return Path(__file__).resolve().parent.parent.parent / "examples"


def main() -> int:
    from . import __version__

    _configure_tls()   # musí proběhnout před prvním HTTPS spojením

    parser = argparse.ArgumentParser(
        prog="bpdp-manager",
        description="Správa vedení BP/DP prací.",
    )
    parser.add_argument(
        "--version", action="version", version=f"BPDPManager {__version__}",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Ověří instalaci (resources, závislosti, sestavení okna) nad dočasnými "
             "daty a skončí. Návratový kód 0 = OK.",
    )
    parser.add_argument(
        "--network",
        action="store_true",
        help="S --self-test navíc ověří skutečné HTTPS spojení se STAG a GitHubem.",
    )
    parser.add_argument(
        "--load-demo",
        action="store_true",
        help="Nahraje fiktivní ukázková data ze souboru examples/seed_demo.json a skončí.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Cesta k vlastnímu db.json (jinak ~/.bpdpmanager/db.json).",
    )
    # macOS při spuštění z Finderu občas předá „-psn_0_12345" (process serial
    # number) — argparse by na neznámém přepínači spadl ještě před otevřením okna.
    args = parser.parse_args([a for a in sys.argv[1:] if not a.startswith("-psn_")])

    if args.self_test:
        from .selftest import run_selftest

        return run_selftest(network=args.network)

    from .services import ThesisService
    from .storage import Database, JsonRepository

    repo = JsonRepository(path=args.db) if args.db else JsonRepository()

    if args.load_demo:
        seed_path = _examples_dir() / "seed_demo.json"
        if not seed_path.exists():
            print(f"Demo soubor nenalezen: {seed_path}", file=sys.stderr)
            return 1
        data = json.loads(seed_path.read_text(encoding="utf-8"))
        db = Database.model_validate(data)
        repo.save(db)
        print(f"Demo data uložena do: {repo.path}")
        return 0

    from .app import run

    # ujistíme se, že DB existuje
    service = ThesisService(repo)
    del service
    return run()


if __name__ == "__main__":
    sys.exit(main())
