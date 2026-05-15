# Changelog

Všechny významné změny v projektu jsou zaznamenány v tomto souboru.

Formát vychází z [Keep a Changelog](https://keepachangelog.com/cs/1.1.0/),
verzování dodržuje [Semantic Versioning](https://semver.org/lang/cs/).

## [Unreleased]

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

[Unreleased]: https://github.com/Safronus/bpdp-manager/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/Safronus/bpdp-manager/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/Safronus/bpdp-manager/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Safronus/bpdp-manager/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Safronus/bpdp-manager/releases/tag/v0.1.0
