# Changelog

Všechny významné změny v projektu jsou zaznamenány v tomto souboru.

Formát vychází z [Keep a Changelog](https://keepachangelog.com/cs/1.1.0/),
verzování dodržuje [Semantic Versioning](https://semver.org/lang/cs/).

## [Unreleased]

## [0.4.3] - 2026-05-16

### Changed
- **Správa studentů** přerobena z plochého seznamu na **strom s grupováním**:
  *Typ práce (BP/DP) → Obor → studenti*. Studenti bez přiřazené práce
  jsou v sekci „Bez přiřazené práce" na konci.
- V rámci skupiny seřazeno **abecedně dle příjmení** (a podle jména
  jako sekundární klíč). Zobrazení jména ve tvaru *Příjmení, Jméno*.
- Tři sloupce: *Příjmení, Jméno | Osobní č. | Stav (rok)*.
- **Barevné odlišení** podle aktuálnosti práce:
  - modrá tučná = běží v aktuálním ak. roce
  - tyrkysová = budoucí rok / zájemce
  - šedá kurzíva = obhájeno
  - červená kurzíva = nedokončeno
- Sloupec *Stav* má barevné pozadí podle ``ThesisStatus.color`` jako jinde.
- Tooltip u jména studenta ukazuje historii všech jeho prací.
- Legenda barev pod tlačítky.

### Added
- Checkbox **„Skrýt dokončené studenty"** — odfiltruje studenty, jejichž
  primární práce je obhájena. Počet skrytých se objeví v info pruhu.
- Helper `_thesis_priority()` v `manage_dialogs.py` — vybere
  „nejaktuálnější" práci studenta (aktivní > zájemce > obhájeno > nedokončeno;
  uvnitř tier preferuje vyšší ak. rok).

## [0.4.2] - 2026-05-16

### Changed
- **Grupování v seznamu prací se vrátilo** — místo ploché tabulky je strom
  *Akademický rok → BP/DP → práce*, ale **se zachovanými 5 sloupci**
  (Student | Téma | Stav | Oponent | Obor) a barevným pozadím sloupce *Stav*.
- Řádky se sekcemi (rok, typ) jsou roztažené přes celou šířku, tučné/kurzíva.
- Defaultní výchozí proporce vertikálního splitteru: **strom 260 px / detail 640 px**.
  Detail dostává dvojnásobek místa, aby se formulářová pole pohodlně vlezla.
- Výchozí velikost okna zvětšena na **1400×960** (minimum 1100×760), takže detail
  má dost místa i bez ručního přetahování splitteru.
- Splitter má vypnuté collapsible — žádná z částí nemůže být kompletně skryta.
- Tree drží rozbalený stav let i přes refresh.

### Removed
- `src/bpdpmanager/ui/theses_table.py` (nahrazeno `theses_tree.py`).

## [0.4.1] - 2026-05-16

### Fixed
- `NameError: name 'QVBoxLayout' is not defined` při startu — v 0.4.0
  jsem v `_ThesesTab.__init__` přepsal `QHBoxLayout` na `QVBoxLayout`,
  ale opomněl jsem aktualizovat importy v `main_window.py`. App neběžela.

## [0.4.0] - 2026-05-16

### Changed
- **Hlavní okno přerozděleno vertikálně**: tabulka prací nahoře, detail dole
  (dříve strom vlevo, detail vpravo). Tabulka má více místa na šířku,
  detail dostává plnou šířku okna pro formulářová pole.
- **Strom prací nahrazen plnohodnotnou tabulkou** se sloupci:
  *Student | Téma | Stav | Oponent | Obor*. Sloupec *Stav* má **barevné
  pozadí** odpovídající stavu (šedá zájemce, oranžová rezervace, modré
  vypsané/zadané, fialová v řešení, zelená obhájeno, červená nedokončeno)
  s bílým bold textem.
- Šířka sloupců se automaticky přizpůsobuje obsahu; sloupec *Téma* vyplní
  zbývající prostor. Tabulka je tříditelná kliknutím na hlavičku
  (defaultní řazení: akademický rok ↓, stav v procesním pořadí, název).
- Tooltipy u buněk: student → osobní číslo + forma, téma → plný název,
  oponent → pracoviště + interní/externí.

### Removed
- `src/bpdpmanager/ui/tree_view.py` (nahrazeno `theses_table.py`).

## [0.3.2] - 2026-05-16

### Changed
- **Forma studia se odvozuje z přípony oboru** — pole *Forma* už není potřeba
  vyplňovat ručně. Obor končící na `-P` = prezenční, `-K` = kombinovaná.
  Property `Student.form` to vrátí na čtení; v JSON úložišti se nic neukládá.
  Dialog studenta má pod oborem **živý indikátor** odvozené formy
  (zelený ✓ při detekci, červená hláška „přípona -P/-K nenalezena" jinak).
- `Student.model_config` má `extra='ignore'`, takže staré JSON soubory
  s polem `form` se načtou bez chyby (pole je tiše zahozeno).
- Demo data v `examples/seed_demo.json` čistá bez `form` polí.

### Added
- README: sekce *Venv mimo synchronizovanou složku (iCloud, Dropbox, OneDrive…)*
  s návodem, jak provozovat projekt synchronizovaný v iCloud Drive, aniž by
  iCloud rozbil `.venv`. Řešení: venv leží v `~/.venvs/bpdp-manager/`, v projektu
  je jen symlink.
- README: zsh tip k uvozovkám u `pip install -e ".[dev]"`.
- Helper `derive_form_from_obor()` v `models/student.py` — sdílený mezi
  modelem a UI dialogem pro konzistentní detekci.
- Testy pro odvození formy (`test_form_derived_*`) a pro zpětnou
  kompatibilitu načtení JSON se starým `form` polem.

## [0.3.1] - 2026-05-15

### Fixed
- **Rozložení polí v detailu práce** — pole v záložkách *Základní info*,
  *Vypsané téma*, *Oficiální zadání* a *Poznámky* už nestrčí ve středu okna,
  ale roztáhnou se na celou šířku panelu. QFormLayout nyní používá
  `AllNonFixedFieldsGrow` field growth policy a komponenty mají `Expanding`
  size policy.
- **Anotace** (Vypsané téma) a **Poznámky** vyplní celou volnou výšku
  panelu, ne jen sizeHint.
- *Body zadání* a *Literární zdroje* (Oficiální zadání) si rovnoměrně rozdělí
  svislý prostor.

## [0.3.0] - 2026-05-15

### Added
- **Autosave na pozadí** detailu práce. Po každé změně pole se po **1,5 s**
  (debounce) zápis sám uloží — nemůžeš tak přijít o rozepsanou anotaci, body
  zadání ani poznámky. Bezpečnostní timer každých **30 s** uloží pro jistotu,
  i kdyby debounce nezvládl.
- Při **přepnutí na jinou práci** se nejdřív flushne rozpracovaná verze té
  předchozí, aby se nic neztratilo.
- Při **zavření okna** (`closeEvent`) se ještě jednou flushnou všechny detaily.
- Vizuální indikátor stavu ukládání v hlavičce detailu:
  *✓ Uloženo HH:MM:SS* (zelený), *● Ukládám…* (oranžový),
  *⚠ Chyba ukládání: …* (červený).
- Ruční tlačítko *Uložit změny* zůstává — vynutí okamžitý zápis (přeskočí debounce).

### Changed
- `_loading` flag v `ThesisDetail` chrání před falešnými dirty signály při
  programovém naplnění formuláře (`set_thesis`, `refresh_combos`, atd.).

## [0.2.1] - 2026-05-15

### Added
- **Aplikační ikona** — vlastní vektorově generovaná (Pillow) v macOS rounded-square stylu.
  Modrá kniha s usměvavou absolventskou tváří, černou čepicí se žlutým střapcem
  a červenou záložkou. 100% MIT-kompatibilní (žádné externí stock obrázky).
- Generátor `scripts/make_icon.py` — vyrobí master 1024×1024 PNG, doplňkové
  velikosti (128/256/512), macOS iconset a `.icns` přes `iconutil`.
- Pillow přidán do dev závislostí (`pip install -e ".[dev]"`).
- Ikona se aplikuje na všechna okna přes `QApplication.setWindowIcon`.

## [0.2.0] - 2026-05-15

### Added
- **Záložka Harmonogram** s importem PDF rozhodnutí děkana (časový plán výuky FAI UTB).
  PDF se zkopíruje do `~/.bpdpmanager/harmonograms/` a parser z něj automaticky vytěží
  klíčové termíny (data, intervaly i fuzzy popisy typu „květen-červen 2027").
  Žlutý panel zobrazuje důležité nadcházející termíny v následujících 60 dnech.
- **Správa studijních oborů**: nové tlačítko *Obory* v toolbaru — přidávat, přejmenovat
  (zachová synchronizaci u studentů), smazat (vyprázdní obor u dotčených studentů).
- **Oponenti rozděleni na interní a externí**: dialog se přepíná podle typu,
  externí mají navíc telefon a adresu. Správa oponentů má dvě záložky.
- **Dokumenty k práci**: záložka *Dokumenty* v detailu práce umožňuje nahrát soubory
  (posudek vedoucího, posudek oponenta, text práce, oficiální zadání, prezentace, jiné)
  a otevřít je v defaultní aplikaci OS. Soubory se ukládají do
  `~/.bpdpmanager/documents/{thesis_id}/`. Lze přidat i externí URL/odkaz.
- Env proměnná `BPDPMANAGER_DATA_DIR` pro přepsání cesty k datovému adresáři (testy).
- Testy pro správu oborů, oponentů, dokumentů, harmonogram parser (21 testů).
- `CHANGELOG.md`.

### Changed
- **A-číslo (např. A24390) přesunuto** z `Thesis.assignment_number` na
  `Student.university_id` — je to osobní identifikační číslo studenta UTB,
  ne číslo zadání. Sloupec stromu „Číslo zadání" se přejmenoval na „Osobní č.".
- Validace přechodu na *Oficiálně zadané* už nevyžaduje samostatné číslo zadání.
- Dialog studenta má nové pole „Osobní číslo (UTB)".

### Fixed
- Padání při startu kvůli `EmailStr` — nahrazeno obyčejným stringem
  (nepotřebujeme strict email validaci, navíc to vyžadovalo extra balíček).

## [0.1.0] - 2026-05-15

### Added
- První verze aplikace BPDPManager — PySide6 GUI pro správu vedení BP/DP prací.
- Datové modely (pydantic): Student, Opponent, Thesis, AcademicYear.
- JSON úložiště s atomickými zápisy a automatickou zálohou `db.json.bak`.
- 7 stavů toku práce: Zájemce → Rezervace → Vypsané → Zadané → V řešení → Obhájeno / Nedokončeno.
- Validace přechodů mezi stavy.
- Stromové zobrazení (Akademický rok → BP/DP → práce) s barevnými stavovými štítky.
- Záložky Aktuální / Budoucí / Historie / Vše.
- Správa studentů a oponentů (jednoduché dialogy).
- Fiktivní demo data v `examples/seed_demo.json`.
- MIT licence, README, CLAUDE.md (pokyny pro budoucí Claude práci v repu).

[Unreleased]: https://github.com/Safronus/bpdp-manager/compare/v0.4.3...HEAD
[0.4.3]: https://github.com/Safronus/bpdp-manager/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/Safronus/bpdp-manager/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/Safronus/bpdp-manager/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/Safronus/bpdp-manager/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/Safronus/bpdp-manager/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/Safronus/bpdp-manager/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Safronus/bpdp-manager/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/Safronus/bpdp-manager/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Safronus/bpdp-manager/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Safronus/bpdp-manager/releases/tag/v0.1.0
