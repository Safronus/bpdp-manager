# Changelog

Všechny významné změny v projektu jsou zaznamenány v tomto souboru.

Formát vychází z [Keep a Changelog](https://keepachangelog.com/cs/1.1.0/),
verzování dodržuje [Semantic Versioning](https://semver.org/lang/cs/).

## [Unreleased]

## [0.7.8] - 2026-05-16

### Changed
- **Anotace CZ a Anotace EN vedle sebe** v sekci *Vypsané téma* —
  místo dvou ``QPlainTextEdit`` pod sebou jsou nyní v ``QHBoxLayout``
  s rovnoměrným rozdělením šířky 50/50. Šetří svislé místo, plně
  funkční zachováno.

## [0.7.7] - 2026-05-16

### Changed
- **Rozsah hodnot v comboboxu *Rok* závisí na záložce, ve které se práce
  zobrazuje**:
  - **Aktuální**: combobox **zamčený** (disabled), vždy aktuální rok,
    nelze měnit. Tooltip: „Aktuální akademický rok — zamčeno".
  - **Budoucí**: jen 2 hodnoty — *aktuální + 1* a *aktuální + 2*
    (např. 2026/2027, 2027/2028). Nelze měnit jiné roky — dropdown only.
  - **Historie**: 2009/2010 až *aktuální − 1* (sestupně). Dropdown only.
  - **Vše**: 2009/2010 až *aktuální + 2*. Editovatelné, kdyby uživatel
    potřeboval extrémní hodnotu.
- ``ThesisDetail`` má nový konstrukční parametr ``year_mode``
  (``current`` / ``future`` / ``history`` / ``all``).
- ``_ThesesTab`` ``year_mode`` propaguje, ``MainWindow`` ho zadává podle
  záložky.
- Helper ``_set_year`` zajistí, že rok mimo standardní rozsah
  (legacy data, např. 2005/2006) se v non-editable combu zobrazí —
  dočasně se vloží do dropdownu.

## [0.7.6] - 2026-05-16

### Changed
- **Sekce *Základní info* na jeden kompaktní řádek**. Místo 4 řádků
  (Typ / Akademický rok / Student / Oponent) je teď vše vedle sebe
  v jednom horizontálním layoutu — šetří svislé místo, zůstává plně
  funkční.
- **Typ práce přepnut na radio buttony** ``BP`` / ``DP`` (přes
  ``QButtonGroup``) — rychlejší přepnutí než combobox.
- **Akademický rok je teď editovatelný combobox** s pevně definovaným
  rozsahem od ``2009/2010`` po ``(aktuální + 2)`` (aktuální + 2 budoucí
  roky pro plánování zájemců). Sestupně, takže nejaktuálnější rok je
  nahoře. Pole zůstává editovatelné, kdyby si uživatel potřeboval doplnit
  ručně exotický rok.
- Helper ``_academic_year_choices()`` počítá rozsah dynamicky podle
  ``date.today()`` — žádný hardcode budoucnosti.

## [0.7.5] - 2026-05-16

### Fixed
- **Nově přidaný student/oponent se hned objeví v rozbalovači** u záložky
  *Téma zadání*. Dříve se sice úspěšně uložil, ale combo box detailu
  zůstal s původním seznamem, dokud uživatel nevybral jinou práci.
  ``MainWindow._refresh_all()`` teď po každé akci managementu (Studenti /
  Oponenti / Obory) zavolá také ``detail.refresh_combos()``.

### Changed
- ``ThesisDetail.refresh_combos()`` **zachovává aktuální výběr** —
  zachytí ID studenta/oponenta před clearem combo a po refilll je znovu
  nastaví. Tím se ztratí cyklus, kdy refresh „odhlasil" právě
  rozeditovaného studenta práce.

## [0.7.4] - 2026-05-16

### Changed
- **Hlavní okno se spouští maximalizované** (``window.showMaximized()``
  místo ``window.show()``). Šetří klikání po každém startu.
- **Správa oponentů přepsána** z taby + dvou ``QListWidget`` na jeden
  přehledný ``QTreeWidget`` s:
  - dvěma top-level skupinami **📍 Interní (UTB)** a **🏢 Externí**
  - **čtyřmi sloupci**: *Jméno | Pracoviště | Email | Telefon*
  - **abecedním řazením** uvnitř skupin (při řazení se ignorují akademické
    tituly typu ``doc.``, ``prof.``, ``Ing.``, ``Mgr.``, ``MUDr.``,
    ``RNDr.``, ``JUDr.``, ``PhDr.``, ``PaedDr.``, ``Bc.``, ``DiS.``,
    ``Ph.D.``, ``CSc.``, ``DSc.``, ``Th.D.``, ``MgA.``)
  - tooltipem s adresou u externích oponentů
  - info pruhem na spodku se souhrnnými počty.
- Pro „+ Nový oponent" se default kind určí podle aktuálního výběru
  ve stromu (jsi-li v sekci Externí → default = Externí).

## [0.7.3] - 2026-05-16

### Changed
- **Combo pro výběr studenta/oponenta nemá sentinel položku** „— bez
  studenta —" / „— bez oponenta —". Při kliknutí do prázdného pole už
  uživatel nemusí nic mazat, aby spustil našeptávání. Místo sentinel
  položky se používá ``QLineEdit.setPlaceholderText("(bez studenta)")``,
  který se chová standardně — světle šedý text vidíš dokud nezačneš psát,
  pak zmizí.
- ``_resolve_combo_id`` má jasnější sémantiku:
  - prázdný text → ``None`` (explicitní „bez přiřazení"),
  - přesná shoda s položkou → ID té položky,
  - text se neshoduje (uživatel ještě dopisuje) → poslední vybraná
    položka přes ``currentData()`` (nemažeme vazbu během psaní).
- Helper ``_set_combo_to_id`` v ``ThesisDetail`` — kompaktní logika pro
  „buď nastav na položku s daným ID, nebo vyčisti".

## [0.7.2] - 2026-05-16

### Added
- **Pole *Anotace (EN)*** v sekci *Vypsané téma* (pod *Anotace*) — volitelný
  anglický překlad anotace. Nový field ``Thesis.annotation_en: str = ""``
  (default prázdný; staré JSON se načtou bez problémů).
- Souhrn zobrazuje sekci *Anotace (EN)* jen pokud je vyplněná, vlastní
  📋 tlačítko pro kopírování do schránky.

### Fixed
- **Žádné skoky při autosavu**:
  - Strom blokuje signály **po celou dobu** ``refresh()`` (clear + build
    + re-select), ne jen v okamžiku re-selectu. Tím se zamezí emisi
    ``itemSelectionChanged`` z ``clear()``, která dříve vedla k re-loadu
    detailu a přeskoku na záložku *Souhrn* uprostřed psaní.
  - Po autosavu zůstává aktuální záložka i pozice kurzoru tam, kde jsi byl.

### Changed
- **Pevná hlavička + taby**: outer ``QScrollArea`` v detailu odstraněna.
  Hlavička (status badge, název, save state, smazat), transition tlačítka,
  taby a save row jsou nyní fixed a nikam se nescrollují. Scrolluje **jen
  obsah tabu *Téma zadání*** přes vlastní ``QScrollArea``.

## [0.7.1] - 2026-05-16

### Changed
- **Pole „Název EN" přesunuto do sekce *Vypsané téma*** (pod *Název CZ*).
  V sekci *Oficiální zadání* zůstávají jen body zadání a literatura.
- **Body zadání + literární zdroje zadávej bez ručního číslování** —
  každý bod / citace na samostatnou řádku. Číslování (1., 2., 3., …)
  se automaticky vygeneruje v záložce *📋 Souhrn* (HTML ``<ol>``)
  i v exportu do schránky.
- Pro zpětnou kompatibilitu: jakákoli stávající ručně zadaná čísla
  na začátku řádků (např. ``"1. text"``) jsou při zobrazení regexem
  odstraněna, takže se nečísluje dvakrát.
- Editor má aktualizovaný placeholder bez čísel a popisku, který
  vysvětluje, že číslování přibyde automaticky.

### Fixed
- **Kurzor v body zadání / literatura už neskáče na začátek**
  při autosavu. Příčina: po každém uložení strom `refresh()` volal
  `select_thesis()`, což vyvolalo `itemSelectionChanged` → tab znovu
  načetl detail a `setPlainText` resetoval pozici kurzoru. Strom teď
  blokuje signály při programovém re-výběru (uživatelské kliky
  fungují normálně).

## [0.7.0] - 2026-05-16

### Changed
- **Záložky detailu sloučeny** — z dosavadních *Základní info* + *Vypsané téma*
  + *Oficiální zadání* je nyní **jedna záložka „📝 Téma zadání"** se třemi
  vizuálně oddělenými sekcemi (`QGroupBox`). Méně klikání mezi taby při
  vyplňování práce, vše na jedné stránce s vnitřním skrolováním.
- **Po výběru práce v seznamu se aktivuje záložka 📋 Souhrn** — uživatel
  dostane nejdříve celkový přehled, teprve potom přepne na úpravy.
- **Přejmenování stavů** (jen popisky, JSON hodnoty zůstávají kompatibilní):
  - `Zájemce` → **„Zájemce bez tématu"**
  - `Rezervace s tématem` → **„Zájemce s tématem"**
  - `Oficiálně zadané` → **„Schválené téma"**

### Removed
- `_build_basic_tab`, `_build_listing_tab`, `_build_assignment_tab` —
  nahrazeno `_build_topic_tab` + tři sekce (`_build_basic_section`,
  `_build_listing_section`, `_build_assignment_section`).

## [0.6.0] - 2026-05-16

### Changed
- **Obor je entita**, ne jen řetězec. ``Database.obory: list[Obor]``
  (dříve ``list[str]``). Stará JSON data se automaticky migrují přes
  ``model_validator(mode="before")``. Aplikace tak může u každého oboru
  evidovat **sekretářku oboru** (jméno, email, telefon, poznámka).
- **Body zadání a literární zdroje** jsou nyní **volný text** (``str``)
  místo ``list[str]``. Uživatel si čísluje sám (``1. ... \n 2. ...``) —
  styl odpovídá oficiálnímu zadání UTB. Stará data se automaticky
  konvertují na číslovaný text.
- ``ThesisDetail``: pole *Body zadání* a *Literární zdroje* jsou
  ``QPlainTextEdit`` s placeholder příkladem.
- Souhrn renderuje body zadání + literaturu s `<br>` mezi řádky a
  zachovává uživatelův formát; clipboard copy vrací plain text 1:1.
- ``StringListEditor`` widget odstraněn (nepoužívaný).
- ``Thesis.is_ready_for_assignment()`` testuje ``objectives.strip()``
  a ``references.strip()`` místo prázdné kolekce.

### Added
- **Sekretářka oboru** — v ``Obor`` modelu pole ``secretary_name``,
  ``secretary_email``, ``secretary_phone``, ``note``.
- **OborDialog** — nový dialog pro editaci oboru včetně kontaktu na
  sekretářku.
- **OboryManageDialog** přepsán z plochého seznamu na tabulku se sloupci
  *Obor | Studentů | Sekretářka | Kontakt*. Dvojklik otevře OborDialog.
- ``ThesisService``: ``list_obor_objects()``, ``get_obor()``,
  ``upsert_obor()``.
- **Našeptávání ve výběru studenta a oponenta** v záložce *Základní info*:
  combo boxy jsou editovatelné, ``QCompleter`` s ``MatchContains`` +
  ``CaseInsensitive`` filtruje podle libovolné části jména/příjmení malými
  i velkými písmeny.
- ``_resolve_combo_id`` helper — robustně získá ID z editovatelného combo
  porovnáním textu s itemy (i když Qt nestihne updatovat currentIndex).
- Testy pro Obor s sekretářkou, migraci ``list[str] → list[Obor]``,
  migraci ``list[str] → numbered text`` pro objectives/references.

### Removed
- ``src/bpdpmanager/ui/widgets/list_editor.py`` (StringListEditor) —
  nahrazen QPlainTextEdit.

## [0.5.2] - 2026-05-16

### Added
- **Copy-to-clipboard tlačítka** 📋 v záložce *Souhrn* — jedním klikem
  zkopíruje do schránky:
  - název práce (CZ)
  - název práce (EN)
  - anotaci (čistý text)
  - body zadání (každý bod jako "• ..." na nové řádce)
  - literární zdroje (každý bibliografický záznam jako "• ..." na nové řádce)
- Po kliknutí se zobrazí krátký tooltip *📋 Zkopírováno: {název pole}*.
- Použita technika anchor-link `copy:<field>` v QTextBrowseru s vlastním
  handlerem na `anchorClicked` (žádná interakce s externími prohlížeči).

## [0.5.1] - 2026-05-16

### Added
- **Tlačítko „+ Minulá práce"** v toolbaru pro přidávání historických
  prací (např. pro doplnění zpětně do evidence). Otevře dialog s poli:
  - *Akademický rok* (default: rok před aktuálním)
  - *Typ* (BP/DP)
  - *Stav* (Obhájeno / V řešení / Oficiálně zadané / Nedokončeno)
  Nová práce se automaticky vyfokusuje v záložce, kde patří (typicky
  *Historie*).
- `ThesisService.previous_academic_year()` helper — počítá rok před
  aktuálním AR.

## [0.5.0] - 2026-05-16

### Added
- **Záložka „📋 Souhrn"** jako **první** v detailu práce. Zobrazuje
  formátovaný read-only přehled celé práce ve stylu připomínajícím
  textový zápisník — ideální pro rychlý vizuální audit a tisk.
  Obsahuje:
  - **Velký barevný stavový pruh** na vrchu — stav práce je hned
    patrný (akademický rok v pravém rohu).
  - **Varování** pokud chybí pole pro oficiální zadání (žluté
    upozornění s výpisem chybějících položek).
  - Nadpisovou řádku: `BP/DP — Název CZ — Jméno studenta (Obor)
    → Osobní č. (Oponent - …)` v barvě stavu.
  - Anglický název v kurzívě pod nadpisem.
  - Sekce **Anotace** (odsazený odstavec).
  - Sekce **Body zadání** (bulletový seznam).
  - Sekce **Literární zdroje** (bulletový seznam).
- Souhrn se **automaticky aktualizuje**:
  - při přepnutí na záložku Souhrn,
  - při změně vybrané práce (`set_thesis`),
  - po každém autosavu (1.5 s po editaci),
  - po ručním uložení.

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

[Unreleased]: https://github.com/Safronus/bpdp-manager/compare/v0.7.8...HEAD
[0.7.8]: https://github.com/Safronus/bpdp-manager/compare/v0.7.7...v0.7.8
[0.7.7]: https://github.com/Safronus/bpdp-manager/compare/v0.7.6...v0.7.7
[0.7.6]: https://github.com/Safronus/bpdp-manager/compare/v0.7.5...v0.7.6
[0.7.5]: https://github.com/Safronus/bpdp-manager/compare/v0.7.4...v0.7.5
[0.7.4]: https://github.com/Safronus/bpdp-manager/compare/v0.7.3...v0.7.4
[0.7.3]: https://github.com/Safronus/bpdp-manager/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/Safronus/bpdp-manager/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/Safronus/bpdp-manager/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/Safronus/bpdp-manager/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/Safronus/bpdp-manager/compare/v0.5.2...v0.6.0
[0.5.2]: https://github.com/Safronus/bpdp-manager/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/Safronus/bpdp-manager/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/Safronus/bpdp-manager/compare/v0.4.3...v0.5.0
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
