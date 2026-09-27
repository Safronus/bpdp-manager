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
- **Podpis:** ad-hoc (bez Apple Developer účtu). Staženo prohlížečem → karanténa →
  macOS 15+ blokuje („nelze otevřít", jen Hotovo/Koš; „pravý klik → Otevřít" už
  nefunguje — ověřeno uživatelem na macOS 27) → *Nastavení → Soukromí a zabezpečení
  → Přesto otevřít*. Aktualizace proto stahuje aplikace sama (bez karantény).
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
- ✅ **Fáze 2 — GitHub Actions** (`.github/workflows/build.yml`): ruff ratchet
  (≤ 335, ruff zafixován 0.15.15) + testy + build + artefakt; release když tag
  `v<verze>` neexistuje (`scripts/release_notes.py` bere sekci z CHANGELOGu).
  **Vydáno v2.30.0** (tag → `d4941e6`, `BPDPManager-2.30.0-macos-arm64.dmg`, 235 MB).
  Ověřeno: self-test na runneru vč. WebEngine; stažený `.dmg` z Release (checksum,
  arm64, podpis, self-test přímo z DMG); živé API nabídne update starší `.app`.

- ✅ **Segfault testovacího běhu** (commit `d4941e6`) — 1. běh CI odhalil, že
  pytest končí exit 139 i při 753/753 zelených (starý problém, bez CI neviditelný).
  Příčina: offscreen Qt + `QMimeData` ve schránce při ukončení. Opraveno v testech.

### Důležité technické poznámky
- **Testy ověřovat podle exit kódu, ne jen podle „N passed"** (`tail` ho skryje).
- `.venv` je symlink na `~/.venvs/bpdp-manager` (Python 3.11.7, srovnáno — viz
  sekce Venv). Instalovat vždy přes `.venv/bin/python -m pip`. Build skript volá
  Python přes rozřešenou cestu (`pwd -P`), jinak PyInstaller vyrobí neúplný
  `QtWebEngineCore.framework` a `codesign` selže („bundle format unrecognized").
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

### Stav
Úkol „spustitelná a udržovaná verze" je hotový. Každý push do `main` = automatický
build + testy; bump verze = automatický Release s `.dmg`.

### Stahování aktualizace v aplikaci (2.30.1)
- `update_checker.ReleaseInfo` (verze, url, **sha256 digest z GitHub API**, size),
  `download_update()` → `.part`, průběžný SHA-256, zahození při neshodě/zrušení,
  jen z `releases/download/` tohoto repa. Dialog: „Uložit jako…" s naposledy
  zvolenou složkou (ui_pref `update_download_dir`, napoprvé Stažené), průběh,
  zrušení, otevření `.dmg`. Bez digestu → záloha přes prohlížeč.
- Ověřeno živě: stažení 235,8 MB z Release v2.30.0, SHA-256 OK, soubor ani
  zkopírovaná `.app` **bez karantény**.
- ⚠️ Úplné proklikání aktualizace z běžící `.app` jde až s vydáním novějším než
  nainstalované (mechanismus ověřen skutečným stažením + testy dialogu).

### Instalace u uživatele
- `/Applications/BPDPManager.app` **v2.30.2** (Finder → Aplikace, Launchpad,
  Spotlight). 2.30.1 hlásila STAG offline (v `.app` chyběly CA certifikáty —
  OPENSSLDIR z CI neexistuje) → 2.30.2 přibaluje certifi (`SSL_CERT_FILE`).
  2.30.1 se sama aktualizovat neuměla (stejná TLS chyba) → 2.30.2 nainstalována
  ručně: `gh release download`, SHA-256 = digest z Release, bez karantény,
  `codesign --verify` OK; `--self-test --network` na nainstalované appce:
  CA 121, přibalené certifikáty, STAG ✅, GitHub ✅ (CI běh 36327433000).
  Otevírá stávající
  profil „Petr Žáček" (sdílený registr `~/Library/Application Support/BPDPManager/
  profiles.json`, stejný jako verze ze zdrojů). Nespouštět obě verze současně.

### Venv (srovnáno 2026-09-27)
- ✅ Nový čistý venv `~/.venvs/bpdp-manager` z **MacPorts Python 3.11.7**
  (`/opt/local/bin/python3.11`; stejná minor verze jako CI, ne-conda → PyInstaller
  bez varování). `python`, `pip`, `lib/` = jen 3.11. Ověřeno: pytest exit 0
  (753), ruff 335, `--self-test`, lokální build + self-test `.app` vč. WebEngine.
- Příčina směsi: README radilo `python3.12 -m venv` nad existující venv → opraveno.
- Starý venv (záloha 1,3 GB) smazán po ověření, že na něm nic jiného nezávisí;
  odstraněn i iCloud duplikát symlinku `.venv 2`. Ze starého chybí jen ručně
  doinstalovaný profiler `py-spy` — **rozhodnuto nedoinstalovávat** (projekt ho
  nepotřebuje; při ladění záseku `python -m pip install py-spy`, na macOS se sudo).
- ruff zafixován v `pyproject.toml` (0.16.9) jako jediný zdroj pro lokál i CI.
  Ověřeno během CI `36324372577`: ruff 0.16.9 z pyproject, ratchet 335, verze
  balíčků v CI = lokální venv.

### Naplánováno
- **Upgrade Pythonu před 10/2027** (konec podpory 3.11). Doporučeno **3.13**
  (podpora do 10/2029). K 2026-09-27 ověřeno: všechny binární závislosti
  (PySide6, shiboken6, pydantic-core, cryptography, cffi, pyinstaller, pillow)
  mají kola pro 3.12–3.14 na macOS arm64. Postup: nový venv + `python-version`
  v CI + ověřit testy/build/self-test + nová verze. Uživatel zatím zvolil zůstat na 3.11.

## Hotovo: sloučení „Nová práce" + „Zájemce" + „Minulá práce", výběr studenta (2.31.0)
Odsouhlaseno 2026-09-27 (interaktivně): jeden dialog pro vše (i Minulá práce);
stav v dialogu, výchozí dle záložky; rok budoucích stavů výchozí dle měsíce
(září až prosinec letošní, jinak příští); výběrový dialog studenta s tabulkou +
detail v novém dialogu i v detailu práce; „Nový záznam z vybraného (BP → DP)";
upozornění na neukončenou práci stejného typu a na DP zakládanou na záznam s BP.
- ✅ Fáze A `e0db94c` — detail na tabu Budoucí: rok letošní + 2 další.
- ✅ Fáze B `05bf219` — `services/student_lookup.py`, `ui/student_picker_dialog.py`,
  tlačítko „…" v detailu; oprava `_resolve_combo_id` (stejné jméno → bral první
  záznam; regresní test ověřen, že bez opravy padá).
- ✅ Fáze C `511c401` — `services/new_thesis.py`, `ui/new_thesis_dialog.py`, jediné
  tlačítko ➕ Nová práce; smazány `_new_thesis*`, `_new_future_thesis`,
  `_new_past_thesis` + nepoužité EN klíče a importy (ruff 335 → 334, baseline v CI 334).
- ✅ Fáze D — nápověda CZ/EN (nová sekce „Nová práce a výběr studenta"), README,
  CHANGELOG [2.31.0], verze 2.31.0. 801 testů, self-test OK.
- Vizuálně ověřeno offscreen renderem (fiktivní data): výběr studenta, dialog nové
  práce (oprava: `QFormLayout` na macOS neroztahoval pole → AllNonFixedFieldsGrow).
- ⚠️ Neověřeno ručním proklikáním v běžící aplikaci (jen testy + render).
- ✅ **Vydáno v2.31.0** (CI 36331245057: ruff 334, 801 testů, self-test .app OK;
  digest sha256:e7ee176b…). Uživatel má zatím 2.30.2 — aktualizace přes „⬇ Stáhnout"
  v aplikaci = první ostrý E2E test updateru (zatím neproběhl).

## Hotovo: přechod budoucích prací do „V řešení", přísné STAG ID (2.31.1)
Ověřeno v kódu (2026-09-27): záložky se řídí stavem; tichá kontrola hlídá stav jen
u „V řešení"; import páruje ručně založenou práci (STAG ID / student+rok+typ), ale
stav existující práce IGNOROVAL (náhled ho přitom ukazoval); „Aktualizace ze STAG"
hledala STAG ID jen podle příjmení (podřetězec) + typu, brala 1. shodu a ID hned
ukládala. Odsouhlaseno: import mění stav schválené budoucí práce + ruční volba
zůstává; zpřísnit dohledání.
- ✅ `4c98b3b` titulek tabu Budoucí „Zájemci a vypsaná témata" (bez roku);
  smazány mrtvé parametry `_build_toolbar` a `ThesisService.previous_academic_year`.
- ✅ `d80ec12` `services/stag_status_rules.py` + import: budoucí práce + STAG dokládá
  v řešení/dál → předvybraný stav ze STAG (oranžový rámeček, tooltip), ruční volba
  v náhledu se uplatní vždy, souhrn „z toho N se změnou stavu"; párování náhledu =
  párování importu (jiné STAG ID = jiná práce). Regresní testy ověřeny (bez změny 6 padá).
- ✅ `074444e` `services/stag_match.py`: jen práce uživatele (příjmení z profilu),
  přesné příjmení + křestní + typ, ověření os. čísla a roku z CSV, ID jen při 1 shodě.
- ✅ Vydání 2.31.1 (verze, README, CHANGELOG, RUFF_BASELINE 333). 828 testů.
- ⚠️ Neověřeno proti živému STAGu ani proklikáním (jen testy s podvrženými daty).
- ✅ v2.31.1 vydána (CI 36336675795; ruff 333, 828 testů, self-test OK).

## Hotovo: párování „nových" v tiché kontrole (2.31.2) — na žádost uživatele
- `stag_match.pair_new_result`: „nová" STAG práce vs. evidované práce BEZ STAG ID
  (jméno + typ, pak os. číslo + rok z CSV; CSV se stahuje jen při shodě jména).
  Jednoznačně → mezi změnami („spárovat", případně „stav ve STAG: …"), nejednoznačně
  → zůstává v nových s „⚠ možná už evidováno". Vedené i oponentury.
- Tichá kontrola hlídá stav i u budoucích prací se STAG ID.
- `ThesisService.adopt_stag_status`: budoucí → mimo Budoucí bez ručního grafu
  (Zájemce bez tématu → V řešení), doplní jen PRÁZDNÁ pole zadání; jinak `transition`.
  Sync dialog ji používá (`_fetch_target_detail` drží CSV záznam).
- Testy `tests/test_stag_pairing_new.py` (vč. celého toku subset → spárování →
  V řešení + zadání); bez změn padají (4 / 3). 837 testů.
- ⚠️ Neověřeno proti živému STAGu (jen podvržená data).
- ✅ v2.31.2 vydána (CI 36337109973) a **uživatel ji aktualizoval v aplikaci —
  funguje** (první ostrý E2E test updateru ✅; STAG ✅, GitHub ✅ v self-testu).

## Hotovo: podpis po přetažení Finderem (2.31.3)
- Zjištěno na nainstalované 2.31.2: `codesign` „sealed resource is missing or
  invalid". Příčina ověřena pokusem: Finder při kopii převádí názvy s diakritikou
  NFC → NFD (cp/ditto ne); 8 šablon „… - Vedoucí.xlsx". DMG z Release byl v pořádku.
- Odsouhlaseno: ASCII názvy (`… - Vedouci.xlsx`; zobrazované názvy beze změny,
  soubor v profilu se jmenuje dle zobrazovaného názvu → existující profily OK)
  + hlídač v `build_macos.sh` (find non-ASCII → exit 1) + test ve zdrojích.
- Ověřeno: lokální build → kopie Finderem → `codesign --verify` OK + self-test OK.
- Uživatel počká na 2.31.3 a aktualizuje v aplikaci (ověří opravu v reálném postupu).
- 1. CI běh 2.31.3 (36343714548) padl na hlídači: `find … | head -5` + `pipefail`
  → „find: stdout: Undefined error: 0" (příčina v CI nevysvětlena, lokálně 0 nálezů
  ve všech locale). Nahrazeno kontrolou v Pythonu (`ec46dd3`) — v CI „✅ jen ASCII".
- ✅ **Vydáno v2.31.3** (CI 36343947794; 839 testů, ruff 333). Ověřeno: stažený .dmg
  (SHA-256 = digest) → kopie Finderem → `codesign --verify` OK.

### Otevřené body (neřešeno, čeká na rozhodnutí uživatele)
- Lint dluh 335 chyb ruff (ratchet brání růstu; po snížení upravit `RUFF_BASELINE`).
- Pillow je runtime-volitelný, ale jen v `dev` závislostech (bez něj se nespočítá
  velikost loga v posudku) — zvážit přesun do hlavních závislostí.
