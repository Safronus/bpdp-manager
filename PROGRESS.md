# PROGRESS — průběžný stav práce

Záchytný bod pro navázání (i v nové session). Aktualizuje se po každé fázi.
Bez reálných dat (repo je veřejné).

## Aktuální úkol: spustitelná a udržovaná verze aplikace

Cíl: samostatná macOS aplikace (`.app` / `.dmg`), která se po změnách sama
sestaví a vydá, a umí uživateli nabídnout aktualizaci.

### Klíčová rozhodnutí (odsouhlaseno 2026-09-27)
- **Platforma:** jen macOS Apple Silicon (arm64).
- **Nástroj:** PyInstaller (onedir `.app`), spec `packaging/bpdpmanager.spec`.
- **Auto-build:** GitHub Actions při každém pushi do `main` (testy + build + artefakt).
- **Release:** automaticky při změně verze — když tag `vX.Y.Z` pro aktuální
  `__version__` neexistuje, CI vytvoří tag + GitHub Release s `.dmg` a sekcí
  z `CHANGELOG.md`.
- **Podpis:** ad-hoc (bez Apple Developer účtu) → na cizím Macu „pravý klik → Otevřít".
- **Aktualizace v zabalené appce:** místo `git pull` nabídnout stažení nového `.dmg`
  z GitHub Releases (verzi brát z posledního *vydaného* Release, ne z CHANGELOGu).
- **Časované testy:** opravit testy (zafixovat akademický rok), ne logiku aplikace.

### Fáze
- ✅ **Oprava časovaných testů** — commit `8708968` (6 testů padalo od 1. 9. 2026).
- ✅ **Fáze 1 — lokální build** — `scripts/build_macos.sh`, `packaging/`, `--self-test`,
  `--version`, oprava restartu ve zmražené appce. Ověřeno: build, podpis, self-test
  zabalené appky (vč. skutečného startu QtWebEngine), ostré spuštění (Cocoa okno),
  DMG (checksum, obsah, podpis). 744 testů zelených, ruff baseline 335.
- ✅ **Fáze 3 — aktualizace v zabalené appce** (pořadí prohozeno s Fází 2: první
  vydaná `.app` musí umět updaty, jinak by se uživatel o dalších verzích nedozvěděl).
  `check_for_frozen_update` (verze z posledního vydaného Release, changelog jen
  ≤ release), dialog „⬇ Stáhnout novou verzi", validace URL z API, nápověda CZ/EN.
  Ověřeno i proti živému GitHub API.
- 🔄 **Fáze 2 — GitHub Actions** (`.github/workflows/build.yml`): ruff ratchet
  (≤ 335, ruff zafixován 0.15.15) + testy + build + artefakt; release když tag
  `v<verze>` neexistuje (`scripts/release_notes.py` bere sekci z CHANGELOGu).
  Bump na **2.30.0**, README (instalace z `.dmg`), nápověda *Spuštění* CZ/EN.
  Čeká na ověření prvním během CI + vydáním v2.30.0.

### Důležité technické poznámky
- `.venv` je symlink na `~/.venvs/bpdp-manager` a má namíchané Pythony
  (`.venv/bin/python` = 3.11, `.venv/bin/pip` = 3.12!). Instalovat vždy přes
  `.venv/bin/python -m pip`. Build skript volá Python přes rozřešenou cestu
  (`pwd -P`), jinak PyInstaller vyrobí neúplný `QtWebEngineCore.framework`
  a `codesign` selže („bundle format unrecognized").
- Velikost: `.app` ~531 MB / `.dmg` ~235 MB — z toho ~285 MB je Chromium
  (QtWebEngine, nutný pro prohlížeč SZZ admin). Nepoužívané Qt moduly jen ~40 MB → neořezáváme.
- Pillow je v `excludes` záměrně NE — `xlsx_image_in_cell` ho volitelně používá.
- iCloud: před commitem ověřit index (`git diff --cached --stat`), po commitu
  `git diff HEAD --stat` musí být prázdné.
- Nesouvisející netrackovaný soubor `zaloha_videa.mp4` v kořeni — necommitovat.

### Jak vydat novou verzi (od 2.30.0)
1. Bump `__version__` v `src/bpdpmanager/__init__.py` + README ř. 12 „Aktuální verze".
2. Sekce `## [X.Y.Z] - datum` v CHANGELOG.md (bez ní spadne už test `test_release_notes`).
3. Commit + push do `main` → CI sestaví, otestuje a vydá Release s `.dmg`.

### Další krok
Ověřit první běh CI (lint, testy, build, self-test vč. WebEngine na runneru)
a vydání v2.30.0 s `.dmg`; stáhnout `.dmg` z Release a ověřit ho.
