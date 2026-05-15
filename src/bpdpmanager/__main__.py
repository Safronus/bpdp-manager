from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="bpdp-manager",
        description="Správa vedení BP/DP prací.",
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
    args = parser.parse_args()

    from .services import ThesisService
    from .storage import Database, JsonRepository

    repo = JsonRepository(path=args.db) if args.db else JsonRepository()

    if args.load_demo:
        seed_path = Path(__file__).resolve().parent.parent.parent / "examples" / "seed_demo.json"
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
