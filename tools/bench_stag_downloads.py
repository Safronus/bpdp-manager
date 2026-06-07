#!/usr/bin/env python3
"""Diagnostický benchmark stahování příloh ze STAG (NEovlivní databázi).

Projde práce z databáze (vedené i oponentury) s STAG ID, **nanečisto** stáhne
jejich soubory ze STAG do dočasné složky, změří čas a soubory **hned smaže**.
Z naměřených hodnot navrhne vhodný timeout (s rezervou).

Nezapisuje do DB ani do složky dokumentů aplikace — databázi jen čte.

Použití:
    python tools/bench_stag_downloads.py [cesta/k/db.json] [--limit N] [--role all|supervisor|opponent]
    python tools/bench_stag_downloads.py --list-profiles

Když cesta není zadaná, použije se **db.json naposledy otevřeného profilu**
(stejná data jako vidíš v aplikaci). Konkrétní profil/DB lze zadat cestou
k jeho ``db.json`` (viz ``--list-profiles`` pro výpis složek profilů).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

# Umožni spuštění bez instalace balíčku (src/ layout).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bpdpmanager.config import app_data_dir
from bpdpmanager.services import stag_api
from bpdpmanager.services.profile_manager import ProfileManager
from bpdpmanager.storage import JsonRepository


def _resolve_default_db() -> Path:
    """db.json naposledy otevřeného profilu; fallback na app data dir.

    Čte jen rejstřík profilů (neotvírá profil, nebere zámek) — pro diagnostiku.
    """
    try:
        pm = ProfileManager()
        prof = None
        last = pm.last_opened_id()
        if last:
            prof = pm.get(last)
        if prof is None:
            profiles = pm.all_profiles()
            prof = profiles[0] if profiles else None
        if prof is not None:
            return Path(prof.data_dir) / "db.json"
    except Exception:  # noqa: BLE001 — diagnostika, fallback níž
        pass
    return app_data_dir() / "db.json"


def _list_profiles() -> int:
    pm = ProfileManager()
    profs = pm.all_profiles()
    if not profs:
        print("Žádné profily. Použije se app data dir:", app_data_dir() / "db.json")
        return 0
    last = pm.last_opened_id()
    print("Profily (★ = naposledy otevřený):")
    for p in profs:
        mark = "★" if p.id == last else " "
        db = Path(p.data_dir) / "db.json"
        exists = "ok" if db.exists() else "CHYBÍ"
        print(f"  {mark} {p.name:24.24}  {db}  [{exists}]")
    return 0


def _human(n: float) -> str:
    for unit in ("B", "kB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def _measure_one(client: stag_api.StagClient, sf: stag_api.StagFile) -> dict:
    """Stáhne jeden soubor do tempu, změří a smaže. Vrací metriky / chybu."""
    times = {"start": None, "first": None}

    def cb(downloaded, total, _t=times):
        now = time.monotonic()
        if _t["start"] is None:
            _t["start"] = now
        if downloaded > 0 and _t["first"] is None:
            _t["first"] = now
        return True

    t0 = time.monotonic()
    try:
        data = client.download_file_streamed(
            sf.download_path, cb, timeout=stag_api._DOWNLOAD_TIMEOUT_MAX
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc), "elapsed": time.monotonic() - t0}
    end = time.monotonic()
    # Ulož a hned smaž (nanečisto, mimo DB).
    tmp = Path(tempfile.gettempdir()) / f"bench_stag_{sf.soubidno}.bin"
    try:
        tmp.write_bytes(data)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
    ttfb = (times["first"] or end) - t0
    size = len(data)
    transfer = max(1e-6, end - (times["first"] or t0))
    return {
        "ok": True, "size": size, "ttfb": ttfb, "elapsed": end - t0,
        "mbps": (size / (1024 * 1024)) / transfer,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("db", nargs="?", help="cesta k db.json (default: poslední profil)")
    ap.add_argument("--limit", type=int, default=0, help="max počet souborů (0 = vše)")
    ap.add_argument("--role", choices=["all", "supervisor", "opponent"], default="all")
    ap.add_argument("--list-profiles", action="store_true",
                    help="jen vypíše profily a cesty k jejich db.json")
    args = ap.parse_args()

    if args.list_profiles:
        return _list_profiles()

    db_path = Path(args.db) if args.db else _resolve_default_db()
    if not db_path.exists():
        print(f"DB nenalezena: {db_path}")
        return 1
    db = JsonRepository(path=db_path, backup_path=db_path.with_suffix(".bak")).load()

    targets: list[tuple[str, str]] = []  # (adipidno, label)
    if args.role in ("all", "supervisor"):
        for t in db.theses:
            if t.adipidno:
                targets.append((t.adipidno, f"vedená {t.adipidno}"))
    if args.role in ("all", "opponent"):
        for o in db.opposing_theses:
            if o.adipidno:
                targets.append((o.adipidno, f"oponentura {o.adipidno}"))

    print(f"DB: {db_path}")
    print(f"Prací s STAG ID: {len(targets)}  (role={args.role})\n")

    results: list[dict] = []
    errors: list[str] = []
    count = 0
    for adip, label in targets:
        client = stag_api.StagClient()
        try:
            files = client.list_thesis_files(adip)
        except Exception as exc:
            errors.append(f"{label}: výpis — {exc}")
            continue
        for sf in files:
            if args.limit and count >= args.limit:
                break
            m = _measure_one(client, sf)
            count += 1
            if m["ok"]:
                results.append(m)
                print(f"  ✓ {label} {sf.filename:32.32} "
                      f"{_human(m['size']):>9}  TTFB={m['ttfb']:5.1f}s  "
                      f"celkem={m['elapsed']:6.1f}s  {m['mbps']:5.2f} MB/s")
            else:
                errors.append(f"{label}: {sf.filename} — {m['error']}")
                print(f"  ✗ {label} {sf.filename:32.32}  {m['error']}")
        if args.limit and count >= args.limit:
            break

    print("\n── Souhrn ──")
    print(f"Staženo (nanečisto): {len(results)} souborů, chyb: {len(errors)}")
    if results:
        max_ttfb = max(r["ttfb"] for r in results)
        max_elapsed = max(r["elapsed"] for r in results)
        min_mbps = min(r["mbps"] for r in results)
        big = max(results, key=lambda r: r["size"])
        print(f"Max TTFB (příprava na serveru): {max_ttfb:.1f} s")
        print(f"Nejdelší celkové stažení:       {max_elapsed:.1f} s")
        print(f"Nejpomalejší průtok:            {min_mbps:.2f} MB/s")
        print(f"Největší soubor:                {_human(big['size'])} "
              f"(TTFB {big['ttfb']:.1f}s, {big['elapsed']:.1f}s)")
        # Návrh: base pokryje TTFB s rezervou, per-MB z nejpomalejšího průtoku.
        base = max(120, round(max_ttfb * 2 + 30))
        per_mb = round(1.0 / max(0.2, min_mbps) * 1.5, 2)
        print("\nNávrh timeoutu (s rezervou ~2×):")
        print(f"  _DOWNLOAD_TIMEOUT_BASE ≈ {base} s")
        print(f"  per-MB ≈ {per_mb} s/MB  (tj. base + size_MB × {per_mb})")
    if errors:
        print("\nChyby:")
        for e in errors[:20]:
            print(f"  • {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
