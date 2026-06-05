# Pokyny pro Claude Code v repozitáři bpdp-manager

## Kontext

BPDPManager je desktopová PySide6 aplikace pro správu vedení BP/DP prací jednoho
akademického vedoucího. Komunikace v češtině, kód a identifikátory v angličtině.

## Pravidla

1. **Žádná reálná data v Gitu.** Nikdy nepřidávej do commitů reálné jméno studenta,
   konkrétní zadání práce, ani číslo zadání. Demo data v `examples/` musí být zjevně
   fiktivní.
2. **Vrstvená architektura.** Drž oddělené `models/`, `storage/`, `services/`, `ui/`.
   UI komponenty nesmí přímo sahat do JSON souboru — vždy přes `services`.
3. **Validace přes pydantic.** Datové třídy jsou pydantic modely. Změny schématu
   provázej zvýšením `version` v JSON úložišti a doplň migraci.
4. **Stavy práce.** Přechody mezi stavy validuj v `services/thesis_service.py`,
   nesvazuj je s UI vrstvou.
5. **Před většími změnami se ptej.** Uživatel preferuje konzultaci nad iterací.
6. **Nápověda je jediný zdroj pravdy.** Při každé změně funkcí aktualizuj
   `src/bpdpmanager/resources/napoveda.md` — renderuje ji in-app okno
   (toolbar ❓ Nápověda / F1) i odkaz v README. Drž ji aktuální se stavem
   aplikace.

## Spouštění

```bash
pip install -e .[dev]
python -m bpdpmanager           # spustí aplikaci
python -m bpdpmanager --load-demo  # nahraje fiktivní demo data
pytest                          # spustí testy
ruff check src tests            # lint
```

## Cesty k datům

- Reálná data: `~/.bpdpmanager/db.json` (mimo repo)
- Záloha: `~/.bpdpmanager/db.json.bak`
- Konfigurace: `~/.bpdpmanager/config.toml`
