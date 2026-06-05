# Changelog

Všechny významné změny v projektu jsou zaznamenány v tomto souboru.

Formát vychází z [Keep a Changelog](https://keepachangelog.com/cs/1.1.0/),
verzování dodržuje [Semantic Versioning](https://semver.org/lang/cs/).

## [Unreleased]

## [0.33.1] - 2026-06-05

### Fixed
- **Náhled importu více prací padal.** Při stažení BP i DP stejného studenta
  (obecně více prací najednou) skončil import výjimkou `TypeError` ještě před
  zobrazením náhledu. Opraveno.

## [0.33.0] - 2026-06-05

### Added
- **Stahování souborů práce ze STAG.** Při „🌐 Stáhnout ze STAG" se spolu
  s prací automaticky stáhnou i její veřejné soubory — **plný text**,
  **přílohy**, **posudek vedoucího** a **posudek oponenta** (pokud jsou
  k dispozici).
- **Náhled stažených souborů** s výběrem (vše předzaškrtnuté, lze odznačit,
  tlačítka *☑ Vše* / *☐ Nic*) a **typem přílohy** odhadnutým ze STAG —
  pokud detekce selže, typ lze ručně přepsat.
- Vybrané soubory se po importu **připojí k odpovídající práci** (párováno
  přes STAG ID) jako přílohy příslušného typu; u oponentur se z PDF posudku
  vedoucího dosynchronizuje navržená známka.
- Nové tlačítko **📎 Stáhnout jen soubory** — stáhne jen soubory a připojí
  je k práci, kterou už máš v databázi (párování přes STAG ID, jinak jméno +
  typ); pokud práce v DB není, upozorní.

## [0.32.1] - 2026-06-05

### Changed
- **Známky v Souhrnu jsou vycentrované** (vedoucí i oponent, u oponentur i
  vedených prací).
- **U vedených prací má Souhrn novou sekci „Známky"** (navržené z posudků)
  hned nad sekcí „📝 Posudky" — stejně jako u oponentur.

### Fixed
- **Známky se doplní i zpětně.** Při otevření oponentury se chybějící známky
  dopočítají z dříve napsaného posudku (oponent) a z dříve nahraného PDF
  posudku vedoucího — ruční hodnoty se nepřepisují.

## [0.32.0] - 2026-06-05

### Added
- **Indikátor průběhu při generování posudku.** Při „Uložit & vyrobit XLSX +
  PDF" se ukáže okno *Generování posudku…* s animovaným ukazatelem. Generování
  (vč. blokujícího převodu do PDF přes LibreOffice) běží v **odděleném vlákně**,
  takže se UI nezasekne a ukazatel se hýbe.

### Changed
- **Přehlednější toolbar.** Tlačítka mají emoji ikony a jsou **barevně
  seskupená** (jemné podbarvení): zelená *Vytvořit* (➕ Nová práce · 🌱 Zájemce ·
  🕘 Minulá práce), modrá *Správa* (🎓 Studenti · 🧐 Oponenti · 👔 Vedoucí ·
  🏷 Obory), fialová 📝 *Šablony posudků*, tyrkysová 📥 *Import ze STAG*, šedá
  👤 Profil · 🔄 Obnovit · ❓ Nápověda. Funguje i v tmavém režimu (průhledné
  podbarvení).

## [0.31.8] - 2026-06-05

### Added
- **Známky u oponentur se doplňují automaticky.** Známka *oponenta (moje)*
  se vezme z navržené známky napsaného posudku. Známka *vedoucího* se vyčte
  z **nahraného PDF posudku vedoucího** (externí vedoucí dodá hotové PDF) —
  z textu „Navržená známka / Proposed grade" (CZ i EN).

### Changed
- **Pořadí sekcí v Souhrnu oponentury**: Body zadání → Známky → 📝 Napsaný
  posudek → 📎 Dokumenty.

## [0.31.7] - 2026-06-05

### Fixed
- **PDF posudku přetékalo na další stránku.** Roztažení tabulky na šířku
  (0.31.4) se dělalo měřítkem tisku (`scale`), které zvětšovalo i výšku → obsah
  se posunul o stránku navíc. Nově se na šířku roztáhnou **jen sloupce tabulky**
  (vodorovně), takže výška a počet stran zůstávají (ověřeno 2 strany u BP/DP,
  CZ/EN). Volná textová pole (zdůvodnění, komentář) tím přestala posouvat obsah.
- README ukazoval starou verzi (0.25.2) — synchronizováno.

## [0.31.6] - 2026-06-05

### Changed
- **Dokumenty u oponentur mají stejný vzhled jako u vedených prací.** Místo
  ploché tabulky se nově používá stejný **agregovaný strom** (skupiny podle
  typu, verzování, otevřít / 📂 Finder / odebrat, pravý klik, indikace
  chybějících souborů, úklid). `DocumentsWidget` umí oba režimy (Thesis i
  OpposingThesis).

## [0.31.5] - 2026-06-05

### Added
- **Souhrn oponentského posudku ukazuje napsaný posudek.** V záložce
  *🧐 Oponentské posudky* → *📋 Souhrn* je nově sekce **📝 Napsaný posudek**
  se strukturovanými daty (body, procenta, navržená známka, kritéria,
  komentář, vygenerované soubory) — stejně jako u vedených prací posudek
  vedoucího.

## [0.31.4] - 2026-06-05

### Changed
- **Šířka tabulky v PDF posudku.** Centrování z 0.31.3 zvětšovalo okraje
  (prázdné sloupce vpravo dělaly velkou mezeru). Nově se tisk **omezí na
  sloupce s obsahem** (A–D) a tabulka se **měřítkem roztáhne na šířku
  stránky** — levý okraj zůstává, mezera vpravo se zmenší. Funguje na CZ/EN
  i BP/DP šablonách (hlavička bodů „Body/Points (0–5)" se detekuje obecně).

## [0.31.3] - 2026-06-05

### Changed
- **Hezčí PDF posudku.** Při převodu do PDF (na dočasné kopii, uložený XLSX
  zůstává 1:1 se šablonou) se nově: **vyváží okraje** (tisk se vycentruje, takže
  vpravo je stejná mezera jako vlevo), **vycentruje logo** a hlavička sloupce
  **„Body (0–5)"** dostane menší a černý font (vejde se na jeden řádek). Týká
  se jen vzhledu PDF; data ani XLSX se nemění.

### Fixed
- **Robustnější přepojení šablony posudku.** Předchozí oprava (0.31.1)
  přepojovala jen podle názvu — to nestačilo, když byl původní posudek
  vyrobený z *vlastní* šablony (jiný název) a pak se knihovna nahradila
  defaultními. Nově se při stalém ID dohledá vhodná šablona i podle
  **typu práce + role + jazyka + oboru** (z kontextu práce) — generování
  uspěje, kdykoli existuje aspoň jedna pasující šablona. Není potřeba
  nic mazat; posudek se opraví sám při dalším vygenerování.

### Fixed
- **„Šablona posudku nebyla nalezena" při generování.** Po „Smazat vše a
  nahradit" (nebo přegenerování defaultů) dostaly šablony nová ID a uložené
  posudky mířily na stará → generování spadlo, i když byla zvolená správná
  šablona. Generování teď stalé ID **automaticky přepojí** podle uloženého
  názvu šablony (sekundárně podle role+jazyka+počtu kritérií) a posudek
  opraví.
- **Plagiátorská sekce v editoru posudku** (verdikt + zdůvodnění) je nově
  zarovnaná doleva a pole *Zdůvodnění* se roztáhne na celou šířku dialogu.

## [0.31.0] - 2026-06-05

### Added
- **Stažení ze STAG — vícevýběr.** Když STAG vrátí víc prací jednoho
  studenta (např. BP i DP), můžeš jich **zaškrtnout víc a stáhnout je
  najednou**; sloučí se do jednoho náhledu a ke každé práci se připojí
  její vlastní CSV.
- **Odznaky „🆕 nové / ✓ už máš".** U výsledků hledání aplikace ukáže, co
  už v databázi máš a co je nové — nové jsou předzaškrtnuté. Tím poznáš,
  že stahuješ novou DP, i když už máš starou BP téhož studenta.
- **STAG ID práce (`adipidno`) se ukládá** na práci i oponenturu →
  opětovný import téže práce se přesně spáruje (aktualizuje, nezaloží
  duplikát). BP a DP se nadále nemíchají (jsou to oddělené záznamy).

### Changed
- Schéma `version` zvýšeno na 6 (přidané volitelné `adipidno`; bez migrace
  dat — staré záznamy mají prázdné).

## [0.30.0] - 2026-06-05

### Added
- **Kontextové menu nad dokumenty** (pravý klik) — *Otevřít* · *📂 Zobrazit
  ve Finderu* · *Odebrat*. Funguje v seznamu dokumentů u všech druhů prací
  (Aktuální / Budoucí / Historie / Vše) i u oponentských posudků.
- **„⭐ Defaultní…" nově nabízí i kompletní výměnu** — vedle *Doplnit
  chybějící* je i *Smazat vše a nahradit* (číselník oborů i knihovna
  šablon) s potvrzením. U doplnění lze zaškrtnout přepis lišících se
  položek.

### Changed
- **Dialog generování posudku — chytřejší nabídka šablon.** Vždy se
  filtruje podle **typu práce** (u BP se nenabízí DP a naopak) a **role**
  (u vedené práce jen posudek *vedoucího*, u oponentury jen *oponenta*).
  Seznam je navíc **seskupený podle oboru**. Přepínač uvolní už jen filtr
  oboru.

### Fixed
- **Výchozí šablony nově propíšou akademický rok** (čte se z hlavičky
  šablony) — v manažeru šablon už sloupec *Akad. rok* není prázdný.

## [0.29.0] - 2026-06-05

### Added
- **🔍 Globální vyhledávání a navigace.** Pole nad záložkami najde práci
  napříč vedenými pracemi i oponenturami podle jména studenta, názvu práce
  nebo osobního čísla (Axxxxx). Při jediné shodě skočí na práci (přepne
  záložku a vybere ji), při více shodách nabídne výběr (práce v *Aktuální*
  jsou první).
- **Barevné odlišení stavu posudku.** V *Aktuální* se buňka názvu práce
  podbarví podle posudku vedoucího (🟢 vyrobený soubor · 🟡 jen rozpracovaná
  data · 🔴 chybí), v *🧐 Oponentské posudky* obdobně podle oponentského
  posudku. **Dolní lišta** ukazuje barevný souhrn hotovo/chybí (vedoucí
  i oponentury).
- **Tituly před/za** u uživatele profilu i u oponentů a vedoucích v
  registrech (ukládají se jako string). Tituly uživatele se automaticky
  skládají do jména autora v posudku („doc. Ing. Petr Novák, Ph.D.").

### Changed
- **PDF posudku se v seznamu dokumentů zobrazuje jako aktuální** (vedle
  XLSX) — ne až po zapnutí starších verzí. Toggle *Zobrazit starší verze*
  je nově defaultně zapnutý.

## [0.28.1] - 2026-06-05

### Fixed
- **Špatná známka u BP pod 60 %.** Aplikace navrhovala u bakalářské práce
  známku **E** už od 17 bodů (56,7 %), ale XLSX šablony FAI UTB mají hranici
  **E ≥ 18 bodů = 60 %** (cokoli pod 60 % je FX). Např. 58,3 % (17,5 b) se
  ukazovalo jako E, správně je **FX**. Práh E u BP opraven 17 → 18, takže
  živý náhled v editoru je nově 1:1 se vzorcem v šabloně. DP (E ≥ 21 = 60 %)
  bylo správně. Pokryto testy pro celou stupnici BP i DP.

## [0.28.0] - 2026-06-05

### Added
- **Výchozí obory a šablony posudků dodávané v aplikaci.** 16 oborů FAI UTB
  se STAG zkratkami a 32 prázdných XLSX šablon (BP/DP, vedoucí/oponent,
  CZ/EN, podle oboru). Tlačítko **⭐ Defaultní…** v manažeru oborů i v
  knihovně šablon je doplní (chybějící přidá, u existujících se zeptá na
  přepis). Nový (prázdný) profil je dostane automaticky.

### Fixed
- `derive_form_from_obor` nově zvládá anglické obory se suffixem `-EN`
  (např. `NSWI-P-EN` → prezenční).
- Oprava STAG kódu `NUI-K` (`knUI`) — dřív kolidoval s `NUI-P` (`pnUI`).

## [0.27.0] - 2026-06-05

### Fixed
- **Logo chybělo v PDF u šablon s „obrázkem v buňce".** Když je logo v
  šabloně vložené jako Excel rich-value („Umístit do buňky"), LibreOffice
  ho neumí vykreslit a v PDF se navíc objevilo `#VALUE!`. Při převodu do PDF
  se nově na dočasné kopii „obrázek v buňce" převede na klasický plovoucí
  obrázek a chybová buňka se vyčistí — PDF pak vypadá stejně jako export
  z Excelu. Uložený XLSX zůstává s nativním obrázkem v buňce.

## [0.26.0] - 2026-06-05

### Added
- **Zobrazit ve Finderu** v seznamu dokumentů (vedené práce i oponentury).
- **Indikace chybějících souborů** (smazaných mimo aplikaci) + tlačítko
  **Odklidit chybějící** pro úklid mrtvých záznamů.
- Dokončovací dialog po vygenerování posudku nově nezavírá okno po prvním
  kliknutí — z jednoho místa jde otevřít XLSX i PDF a ukázat ve Finderu.

### Changed
- **Archivace posudků:** vždy se drží 1 aktuální posudek; starší XLSX se
  přesune do `posudky/archiv/` s časovým razítkem a stará PDF se smaže.

### Fixed
- Seznam dokumentů se po vygenerování posudku správně obnoví (dřív podmínka
  na vždy-prázdné `generated_attachment`).

## [0.25.2] - 2026-06-05

### Fixed
- **Celkové body, procenta a známka v posudku se nepřepočítaly.** Šablona je
  počítá vzorci a má v sobě uloženou starou cache hodnotu (z prázdné šablony).
  Při 1:1 kopii zůstávala cache stará a Excel ani LibreOffice (při exportu do
  PDF) vzorce nepřepočítaly → špatné body/%/známka v XLSX i PDF. Nově se při
  zápisu **cache vzorců zahodí** (vzorce zůstávají) a nastaví se
  `fullCalcOnLoad="1"`, takže se vše při otevření spočítá znovu z vyplněných
  bodů (ověřeno přes LibreOffice). Přesně tak se choval i původní openpyxl.

## [0.25.1] - 2026-06-05

### Fixed
- **Vygenerovaný posudek šel poškozený — Excel ho neotevřel.** Zápis buněk
  přes XML re-serializaci (ElementTree) zahazoval z kořene listu deklarace
  namespace, které sice nebyly „použité" elementem, ale byly odkazované v
  `mc:Ignorable` (např. `x14ac`, `xr`) — výsledek pak Excel odmítl otevřít.
  Nově se cílové buňky upravují **čistě textově** (najdi/nahraď `<c r="…">`)
  a zbytek XML zůstává byte-za-byte; soubor je tak validní a otevíratelný.
- **Logo chybělo i v PDF.** Důsledek téhož poškození — z opraveného (1:1)
  XLSX teď LibreOffice vyrenderuje logo i do PDF. Ověřeno end-to-end.
- **Potlačeno neškodné varování** `Data Validation extension is not
  supported and will be removed` při čtení šablon (openpyxl ho hlásí jen
  pro svůj model; šablonu pouze čteme, zápis ji nemění). Načítání šablon
  jde nově přes `load_template_workbook()`.

## [0.25.0] - 2026-06-05

### Fixed
- **Posudek se generuje 1:1 se šablonou — logo zůstává.** Dřív se při
  vyplnění posudku přepisoval celý sešit přes openpyxl, což zahazovalo
  obrázky (logo fakulty „nahoře", i v záhlaví). Nově se zapisují **jen
  hodnoty buněk** přímo do XML aktivního listu a zbytek šablony (logo,
  kresby, styly, tisková nastavení) se zkopíruje beze změny. Nový modul
  `services/xlsx_cell_writer.py`.

### Added
- **Psaní posudku i u oponovaných prací.** Záložka *🧐 Oponentské posudky*
  má v hlavičce detailu tlačítko **📝 Napsat posudek…** — otevře výběr
  šablony (jen role *oponent*) a editor posudku. Posudek + XLSX/PDF se
  připojí k oponovanému posudku stejně jako u vedených prací.
  `GenerateReviewDialog` nyní přijímá `Thesis` i `OpposingThesis`.

## [0.24.0] - 2026-06-05

### Added
- **Přímé stažení práce ze STAG do import dialogu.** Nové tlačítko
  **🌐 Stáhnout ze STAG** vedle výběru CSV:
  - vyhledá veřejný záznam kvalifikační práce na **stag.utb.cz** podle
    **příjmení studenta** + **příjmení vedoucího/oponenta** (přepínač
    role; druhé příjmení se předvyplní z profilu),
  - zobrazí seznam shod (student, název, typ, rok), po výběru stáhne CSV
    a rovnou otevře náhled importu,
  - vše bez přihlášení (záznam je veřejný), pouze přes standardní
    knihovnu (žádná nová závislost).
  - Síťová vrstva je izolovaná v `services/stag_api.py` (UI nesahá na
    HTTP přímo).
- **Doplnění jména studenta z vyhledávání.** Veřejný CSV export STAG
  jméno studenta neobsahuje (jen osobní číslo) — při přímém stažení se
  jméno doplní z výsledku vyhledávání, takže se student správně založí
  i přiřadí.
- **Revize / doplnění nových studentů při importu.** Volba
  **✎ Před založením zkontrolovat / doplnit nové studenty** otevře pro
  každého nového studenta (u vedených prací) jeho kartu předvyplněnou
  daty ze STAG; zápis proběhne až v rámci (transakčního) importu.

### Notes
- U **oponovaných** prací se student i nadále neeviduje jako samostatná
  entita — ukládá se inline u posudku (proto se „nevytvoří student").
- `*.har` přidáno do `.gitignore` (síťové zachytávky mohou obsahovat
  reálná data ze STAG).

## [0.23.1] - 2026-06-05

### Added
- **Návod „odkud stáhnout CSV ze STAG"**:
  - V import dialogu tlačítko **❓ Odkud stáhnout** vedle výběru souboru
    — ukáže kroky (stag.utb.cz → Prohlížení → Kvalifikační práce →
    vyhledat dle jména studenta → stažení CSV) s klikatelným odkazem.
  - V nápovědě (sekce *Import ze STAG*) přibyl pododdíl *Odkud stáhnout
    CSV* se stejným postupem.

## [0.23.0] - 2026-06-05

### Added
- **STAG import upozorňuje na nenamapovaný obor.** Když STAG kód oboru
  (např. `knIT-KYB`) nemá protějšek mezi evidovanými obory:
  - obor combo v náhledu se **jantarově zvýrazní** + tooltip s návodem,
  - info řádek pod tabulkou ukazuje *„⚠ N× nenamapovaný obor"*,
  - souhrn před importem má **výraznou žlutou výstrahu** s výčtem
    nenamapovaných STAG kódů a doporučením je doplnit.
  Doplnit lze přímo v náhledu — výběrem existujícího oboru, nebo
  *„➕ Nový obor…"* (předvyplní STAG kód, takže příští import se
  namapuje automaticky).
- **First-run tutorial „Začínáme"** — po prvním nastavení profilu se
  zobrazí uvítací průvodce s checklistem (datová složka, tvoje jméno
  a místo posudku, obory + STAG kódy, šablony posudků, LibreOffice pro
  PDF). Tlačítko *📖 Otevřít plnou nápovědu* a checkbox *Příště
  nezobrazovat*. Zobrazí se jen jednou (flag v registry profilů).
- **Sekce „🚀 Začínáme (první spuštění)"** v nápovědě — detailní
  getting-started checklist. First-run tutorial čte stejnou sekci
  (single-source).

### Notes
- Nenamapovaný obor (volba „Nemapováno") se i nadále uloží jako prostý
  název ze STAG kódu — ale teď je to jednoznačně vidět a uživatel může
  obor založit pořádně (s `stag_code`) pro automatické mapování příště.

## [0.22.0] - 2026-06-05

### Added
- **Okno nápovědy ❓** (toolbar *❓ Nápověda* nebo klávesa **F1**).
  Renderuje markdown s popisem všech funkcí a jak aplikace funguje —
  rozcestník po sekcích (přehled, stavy, detail práce, psaní posudku,
  šablony, oponentské posudky, STAG import, harmonogram, profily,
  tipy). Obsahuje vyhledávací pole (Enter / *Další*) a tlačítko *Nahoru*.
- **Jediný zdroj pravdy pro nápovědu** — obsah žije v
  ``src/bpdpmanager/resources/napoveda.md``. In-app okno ho renderuje
  přes ``QTextBrowser.setMarkdown`` a README na něj odkazuje, takže
  se nikde neduplikuje. Při změně funkcí se aktualizuje jen tento soubor.
- README dostal sekci s odkazem na nápovědu (in-app i markdown).
- CLAUDE.md: nové pravidlo č. 6 — udržovat ``napoveda.md`` aktuální
  se změnami funkcí.

## [0.21.4] - 2026-06-05

### Fixed
- **Vyplnění místa a data v posudku rozbíjelo podpisový blok.** Buňka
  „Místo, datum:" v šabloně obsahuje v jednom textu i pole pro podpis
  (např. ``„Místo, datum: ........  Podpis: ........"``). Filler hodnotu
  zapisoval přes celou buňku → zmizel label „Místo, datum:", tečkovaná
  linka i celá sekce „Podpis:" (a tedy i v PDF). Nově se nahradí jen
  **první tečkovaná linka** za „Místo, datum:" — label i podpisový blok
  zůstanou zachované. Výsledek:
  ``„Místo, datum:  Zlín, 4. 6. 2026   …   Podpis: ........"``.

### Changed
- **Dokumenty u práce jsou agregované podle typu souboru.** Místo ploché
  tabulky je strom seskupený podle ``AttachmentKind`` (Text práce,
  Přílohy, Pracovní deník, Oficiální zadání, Posudek vedoucího, Posudek
  oponenta, Prezentace, STAG export, Jiné). Posudky (XLSX/PDF generované
  z šablony) jsou tak rovnou viditelné pod vlastní skupinou. Skupina
  ukazuje počet souborů a počet starších verzí; toggle *Zobrazit starší
  verze* je rozbalí. Pořadí skupin podle pracovního flow.

## [0.21.3] - 2026-06-05

### Fixed
- **Dialog „Generovat posudek" defaultně neukazoval žádné šablony.**
  Auto-filtr podle oboru byl příliš striktní — kód odvozený ze
  studentova oboru (např. „NSWI-P" → „NSWI") se netrefil do oboru
  šablony („SWI"), takže filtrovaný seznam byl prázdný. Checkbox
  *Zobrazit všechny šablony* je nyní **defaultně zaškrtnutý** —
  uživatel vidí všechny šablony a tu správnou mu i nadále auto-vybereme.

### Added
- **Tlačítko „✏ Pokračovat v posledním posudku"** v dialogu pro
  napsání posudku. Pokud pro práci existuje uložený posudek, tlačítko
  (s rolí, navrženou známkou a datem poslední úpravy) otevře editor
  přímo s uloženými daty — bez nutnosti znovu vybírat šablonu.
  Naváže tam, kde uživatel přestal.

## [0.21.2] - 2026-06-05

### Fixed
- **Crash „AttributeError: no attribute _build_reviews_summary_html"
  při výběru práce na druhém Macu.** Příčina: projekt leží v
  iCloud-synced složce (``~/Desktop/``) a sdílený ``__pycache__`` se
  mezi Macy dostal do nekonzistentního stavu — iCloud nezachovává
  spolehlivě mtime, takže Python na druhém zařízení načetl starou
  ``.pyc`` (bez metody přidané v 0.21.1) místo aktuálního zdroje.
- **Prevence**: entry point (``__main__.py``) nově přesměruje bytecode
  cache mimo zdrojový strom — ``sys.pycache_prefix`` na
  ``~/.cache/bpdpmanager/pyc``. Source-adjacent ``.pyc`` v iCloud
  složce se tím ignorují; každý Mac má vlastní lokální cache mimo sync.
  Heavy moduly se importují líně v ``main()``, takže nastavení je
  stihne ovlivnit.

### Notes
- Pokud na nějakém zařízení přetrvává starý stav, jednorázově pomůže
  smazat cache: ``find . -name __pycache__ -type d -exec rm -rf {} +``.
  Od 0.21.2 už by se ale nový ``.pyc`` do iCloud stromu neměl psát.
- ``__pycache__`` a ``*.pyc`` jsou v ``.gitignore`` (nikdy nebyly
  verzované) — šlo čistě o iCloud sync, ne o git.

## [0.21.1] - 2026-06-04

### Added
- **Auto-výběr šablony** v dialogu *Generovat posudek z šablony*.
  Předvybere se nejvhodnější šablona:
  1. Pokud pro práci existuje uložený posudek → jeho šablona.
  2. Jinak jediná pasující šablona (typ + obor).
  3. Jinak první šablona role *vedoucí* (u vedené práce je uživatel
     vedoucí — nejčastější případ).
  Tlačítko *Vyplnit a připojit* je rovnou aktivní.
- **Náhled posudku v záložce 📋 Souhrn** u práce. Uložené posudky
  (current verze) se zobrazí jako sekce *📝 Posudky*: role (🎓/🧐),
  body / max, navržená známka (barevný badge), kompaktní výpis kritérií
  se skóre, celkové hodnocení, indikace vygenerovaných souborů
  (XLSX/PDF) + místo a datum.
- **Auto-návrh „pokračovat v rozpracovaných datech"**. Když pro práci
  + roli + šablonu už existuje uložený posudek, dialog se zeptá:
  *✏ Pokračovat v datech* (body z minula) / *🆕 Začít znovu* / *Zrušit*.
  Ukáže aktuální body, známku a datum poslední úpravy.

### Changed
- **Body v dílčích kritériích jsou nyní po celých bodech** (0–5),
  ne po půlkách. ``QDoubleSpinBox`` → ``QSpinBox`` (krok 1, bez
  desetinných míst). Vážený součet může být díky vahám stále desetinný
  (např. 0,5 × 4 = 2,0).
- **Editor posudku se otevírá ve větší velikosti** (960 × 940, minimum
  900 × 600) — uživatel už nemusí dialog ručně zvětšovat, aby viděl
  všechny sekce (kritéria, plagiátorství, hodnocení).

## [0.21.0] - 2026-06-04

### Added
- **Doporučené komentáře ke kontrole plagiátorství**. V záložce
  *🔍 Plagiátorství* je tlačítko *💡 Doporučený komentář* (rozbalovací):
  - **Hlavní klik** vloží doporučené znění podle aktuálního verdiktu
    + procenta shody.
  - **Rozbalovací menu** nabízí konkrétní varianty:
    - *Nízká shoda — není plagiát*:
      „Práce byla posouzena na plagiátorství s maximální shodou X %
      a nejedná se o plagiát."
    - *Vyšší shoda — není plagiát (očekávané soubory)*:
      „… Vyšší míra shody je zapříčiněná soubory, u kterých se shoda
      dá očekávat (citace, šablony, běžné odborné formulace)."
    - *Je plagiát*: „… Na základě posouzení se jedná o plagiát."
  - Procento se interpoluje z pole shody. Práh pro delší vysvětlení
    je 20 % (``HIGH_SIMILARITY_THRESHOLD``). Komentář je plně
    editovatelný; pokud už něco obsahuje, ptá se na přepis.
- **Plagiátorství se předvyplní do posudku**. Při tvorbě posudku
  (vedoucího) se z práce načte verdikt + komentář:
  - ``thesis.plagiarism_verdict`` → text verdiktu v editoru
  - ``thesis.plagiarism_comment`` → zdůvodnění plagiátorství
- **Místo a datum podpisu se předvyplní**:
  - **Místo** z profilu (nové pole ``Profile.review_place``,
    default „Zlín"). Nastavitelné v *🗂 Správa profilů… → 📍 Místo
    posudku…*.
  - **Datum** dnešní, české formátování „D. M. YYYY".
  - Výsledek: ``place_date = "Zlín, 4. 6. 2026"``.
- Service: ``_guess_review_place()`` + ``build_place_date(place)``.
  ``ProfileManager.set_review_place()``.

### Notes
- Modul ``services/plagiarism_comments.py`` (``suggest_comment`` +
  ``comment_variants``) je bez závislosti na PySide6 — snadno
  testovatelný, znění lze upravit na jednom místě.
- Předvyplnění plagiátorství i místa/data se aplikuje jen na *nový*
  posudek. Při editaci existujícího se data zachovají (uživatel je
  mezitím mohl upravit).

## [0.20.0] - 2026-06-04

### Added
- **Nabídka voleb z listu „Konfigurace" při prázdných polích**. Když
  šablona nemá vyplněnou specializaci (B11 = „-"), dialog *Nová šablona*
  nabídne:
  - **Obor combo** obohacený o specializace z listu *Konfigurace*
    šablony (s odvozeným kódem, např. „SWI — Softwarové inženýrství",
    „KYB — Kybernetická bezpečnost", „BTSM — Bezpečnostní technologie").
    Hint upozorní, že specializace nebyla vyplněna a uživatel má vybrat.
  - **Akademický rok** je nyní editable combo box naplněný platnými
    roky z *Konfigurace* (např. 2025/2026 … 2028/2029) — nemusíš psát
    ručně, ale můžeš.
- ``extract_template_metadata`` čte list *Konfigurace* a vrací
  ``available_programs`` / ``available_specializations`` /
  ``available_years``.

### Changed
- **Správce šablon posudků — hierarchické grupování**. Místo ploché
  tabulky je strom:
  - **Úroveň 0**: 📘 Bakalářské práce (BP) / 📗 Diplomové práce (DP)
  - **Úroveň 1**: 🗂 obor (abecedně, „— bez oboru —" na konci)
  - **Úroveň 2**: jednotlivé šablony (abecedně podle názvu)
  - **Role ikona**: 🎓 vedoucí / 🧐 oponent
  - **Jazyk indikace**: anglické šablony mají v názvu „🇬🇧 EN"
    + sloupec Role ukazuje „· EN"
  - Tooltip nad šablonou: poznámka, cesta k souboru, počet kritérií
    + max bodů
  - Sloupce zredukovány na *Šablona · Role · Ak. rok* (typ a obor
    jsou nyní v grupovacích uzlech).

### Notes
- Heuristika kódu oboru rozšířena o ``BTSM`` (Bezpečnostní technologie),
  ``AIPA`` (Aplikovaná informatika v průmyslové automatizaci) a
  ``ARI`` (Automatické řízení a informatika v průmyslu).
- Editable obor combo: pokud vybereš nabídnutou položku ve formátu
  „KÓD — název", uloží se jen krátký kód. Ručně psaný text se uloží
  tak, jak je.

## [0.19.3] - 2026-06-04

### Added
- **File picker pro import šablony posudku si pamatuje poslední složku.**
  Při přidávání nové šablony (*Šablony posudků → + Přidat šablonu… →
  Procházet…*) se dialog otevře v poslední použité složce — typicky tam,
  kde máš celou sadu XLSX šablon (např. „Šablony 2026"). Po výběru se
  cesta uloží pro příště.
- Nové pole ``ProfileRegistry.last_template_import_dir`` (persistované
  v ``profiles.json``, napříč profily — stejně jako
  ``last_stag_import_dir`` pro STAG import). Metody
  ``ProfileManager.last_template_import_dir`` / ``set_last_template_import_dir``.

### Notes
- ``ReviewTemplatesDialog`` + ``ReviewTemplateEditDialog`` nově přijímají
  volitelný ``profile_manager`` pro přístup k uloženým UI předvolbám.
  Pokud není dostupný (např. v testech), graceful fallback na domovský
  adresář.

## [0.19.2] - 2026-06-04

### Fixed
- **Dark-mode čitelnost v dialogu *Generovat posudek z šablony***
  — kontextový panel s informacemi o práci (typ · rok · student ·
  téma) měl natvrdo světlé pozadí ``#f5f5f5`` → na dark theme světlý
  text na světlém pozadí. Přepnuto na ``palette(base)`` /
  ``palette(text)`` / ``palette(mid)``.
- **Žlutý panel nadcházejících termínů v Harmonogramu** měl světlé
  žluté pozadí ``#fff9c4`` bez explicitní barvy textu → na dark theme
  zděděný světlý ``palette(text)`` na světle žlutém pozadí (špatně
  čitelné). Přidán explicitní tmavě hnědý text ``#5d4037``, který
  je čitelný na žluté v obou tématech.

### Notes
- Proběhl audit všech hardcoded barev pozadí v ``ui/``. Zbylé dva
  výskyty jsou záměrné a čitelné: červené destructive tlačítko
  (rollback, bílý text) a jantarový warning combo pro nedetekovanou
  roli v STAG importu (explicitní tmavý text).

## [0.19.1] - 2026-06-04

### Added
- **Auto-detekce metadat z XLSX při přidávání šablony**. V dialogu
  *Nová šablona posudku* po výběru souboru aplikace okamžitě naskenuje:
  - **Typ + role + jazyk** z A6 titulu (např. „POSUDEK VEDOUCÍHO
    DIPLOMOVÉ PRÁCE" → DP / supervisor / cs)
  - **Studijní program** (B10) a **specializaci** (B11)
  - **Akademický rok** (B12)
  - **Kód oboru** heuristicky z programu/specializace
    (regex mapování *Softwarové inženýrství* → `SWI`,
    *Kybernetická bezpečnost* → `KYB`, *Učitelství informatiky* → `UI`,
    EN ekvivalenty atd.)
  - **Schema kritérií** (řádek/váha/skóre/cell mapping) + speciální pole
    (assignment_fulfilled, plagiarism_*, overall_comment, place_date)
- **Auto-pojmenování** šablony — generuje návrh typu
  *„Vedoucí DP — SWI — 2025/2026"* / *„Supervisor BP — SWI — 2025/2026"*.
  Pokud má uživatel ručně nastavený jiný název, respektuje to.
- **Auto-předvyplnění form polí** (typ, role, jazyk, obor, rok)
  na základě detekce. Uživatel může všechno opravit ručně před uložením.
- **Eager schema cache** — při registraci šablony se schema (criteria
  + field_cells) **uloží hned**, ne lazy. ReviewEditor nemusí už nikdy
  rescanovat (rychlejší otevření, žádná latence při psaní posudku).

### Notes
- Ověřeno na všech 14 FAI UTB šablonách — auto-detekce trefuje
  obor (SWI/KYB/UI), typ (BP/DP), roli (supervisor/opponent), jazyk
  (cs/en) i rok korektně.
- Custom obor (např. pro neznámou specializaci) se přidá do combo
  jako editable text — uživatel ho může ručně vyplnit.

## [0.19.0] - 2026-06-04

### Added
- **Strukturovaný editor posudku** — workflow „Napsat posudek" je
  nyní plnohodnotný formulář s body hodnocení per kritérium, ne jen
  předvyplnění XLSX. Klik na *📝 Napsat posudek…* → vyber šablonu
  → **ReviewEditorDialog** se sekcemi:
  - **Splnění bodů zadání** (combo: splnil(a) / nesplnil(a) / EN ekvivalenty)
  - **Kritéria hodnocení** — tabulka dle šablony s váhou (read-only)
    a spin boxem pro skóre 0–5 (krok 0,5)
  - **Live souhrn**: vážené body / max / % / navržená známka (ECTS stupnice
    barevně podle hodnoty) — okamžitý feedback při změně
  - **Plagiátorství** (jen vedoucího): verdikt + zdůvodnění
  - **Celkové hodnocení, připomínky a dotazy** — text area
  - **Místo, datum** — string pro podpisový blok
- **Strukturovaný model ``Review``** v ``models/review.py``:
  - `CriterionScore`: `row`, `label`, `weight`, `score`, `weight_cell`,
    `score_cell` — propaguje identitu mezi XLSX cells a JSON
  - `Review`: id, template_id, role, language, basic fields, criteria,
    assignment_fulfilled, plagiarism_*, overall_comment, place_date,
    xlsx_filename, pdf_filename, version, is_current
  - Auto-counted properties: `total_weighted_points`, `max_points`,
    `percentage`, `suggested_grade` (ECTS A/B/C/D/E/FX|F dle BP/DP)
- **Auto-extrakce schématu šablony** — ``services/review_schema.py``:
  - Walk XLSX, najde řádky s pattern A=label + C=numeric (váha)
    + D=numeric (skóre)
  - Detekuje speciální pole (assignment_fulfilled, plagiarism_*,
    overall_comment, place_date) heuristicky z popisků
  - Cachuje schéma do ``ReviewTemplate.criteria`` + ``field_cells``
    (zero-config pro standardní FAI UTB šablony)
- **PDF generování přes LibreOffice headless** —
  ``soffice --headless --convert-to pdf``. Detekce na běžných cestách:
  - Linux/macOS PATH (``shutil.which("soffice")``)
  - macOS app bundle (``/Applications/LibreOffice.app/Contents/MacOS/soffice``)
  - Linux distro (``/usr/bin/soffice``)
  
  Pokud LibreOffice chybí → tlačítko v editoru se přejmenuje na
  *„Uložit & vyrobit XLSX (PDF chybí soffice)"* a generuje jen XLSX.
- **Service metody** v ``ThesisService``:
  - ``ensure_template_schema(tmpl)`` — lazy schema extraction
  - ``list_reviews / get_current_review / upsert_review / delete_review``
  - ``generate_review_files(thesis_id, review, *, opposing, also_pdf)``
    — XLSX i PDF, auto-versioning attachmentů
  - ``libreoffice_available`` property
- **Visibility constraint na tlačítku „Napsat posudek"**: aktivní
  pouze pro práci se stavem ``IN_PROGRESS`` (Aktuální tab). Pro Budoucí
  i Historii deaktivováno s tooltipem vysvětlujícím proč.

### Changed
- ``SCHEMA_VERSION`` bumped na **v4** (přidáno
  ``Thesis.reviews``, ``OpposingThesis.reviews``, ``ReviewTemplate.criteria``
  + ``field_cells``). Auto-migrace na load — staré profily se otevřou
  bez problémů, jen prázdné `reviews` listy.
- ``GenerateReviewDialog._generate()`` nyní místo přímého fillu otevírá
  ``ReviewEditorDialog``. Pokud pro danou práci + roli už existuje
  current Review se stejnou šablonou, editor se otevře *pre-filled*
  s předchozími body — uživatel může postupně doplňovat.
- ``ReviewEditorDialog`` po Save & Generate ukáže done dialog
  s tlačítky *📄 Otevřít XLSX* a *📕 Otevřít PDF* (pokud bylo vygenerováno).

### Notes
- **Workflow editace**: data v JSON jsou *zdrojem pravdy*. XLSX/PDF
  lze kdykoli regenerovat. Pokud uživatel ručně upraví XLSX v Excelu,
  další generování z editoru ho přepíše — pro průběžnou editaci proto
  doporučujeme editor (data zůstanou v JSON, XLSX/PDF se přegeneruje).
- **Multiple reviews per thesis**: Review má `version` a `is_current`
  pole jako Attachment. Druhý pokus obhajoby → nový Review v2 (`is_current=True`),
  předchozí v1 (`is_current=False`). Historie zůstává v JSON pro audit.
- **LibreOffice na macOS**: nainstaluj přes ``brew install --cask libreoffice``
  nebo dmg z libreoffice.org. PDF generace bez něj nefunguje, ale
  XLSX cesta funguje samostatně.

## [0.18.1] - 2026-06-04

### Added
- **Welcome dialog (první spuštění) má novou volbu *📥 Importovat .zip…***.
  Fresh installation na novém zařízení nyní podporuje rovnou import
  exportovaného ZIPu — bez nutnosti nejdřív vytvořit prázdný profil
  a teprve potom otevřít *Importovat profil ze ZIPu…* z toolbar menu.
  
  Welcome workflow nyní:
  1. 🔍 Nalezena stávající data (legacy ``~/.bpdpmanager/``, pokud existuje)
  2. 🆕 Nový prázdný profil
  3. 📂 Otevřít existující profil (složka s db.json)
  4. **📥 Importovat ze ZIP balíku** ← nová volba
  
  V tomto kontextu se v ``ImportProfileDialog`` automaticky disabluje
  radio *🔀 Sloučit s existujícím profilem* (žádné profily k mergi
  zatím nejsou) — uživatel rovnou vidí jen variantu *Vytvořit nový profil*.

### Notes
- Migrace na nový laptop má nyní 2-click flow: spustit appku → klik
  *Importovat .zip…* → vybrat soubor + cílová složka → hotovo. Aplikace
  se otevře s plně funkčním importovaným profilem.

## [0.18.0] - 2026-06-04

### Added
- **Merge ZIPu do existujícího profilu** (add-only sémantika).
  ``ImportProfileDialog`` má nyní radio výběr cíle:
  - 🆕 *Vytvořit nový profil* (default, jako dosud)
  - 🔀 *Sloučit s existujícím profilem* — combo box s vyberem registrovaného
    profilu (aktivní zvýrazněn `●`)
  
  Merge sémantika: do cílového profilu se přidají entity, které tam nejsou
  (podle identity klíče); existující se **nemění**. Soubory se kopírují,
  pokud cílový název ještě neexistuje.

  Identity klíče per entita:
  - **Student**: ``id`` nebo ``university_id`` (univerzitní číslo)
  - **Opponent** / **Supervisor** / **Obor**: ``name``
  - **Thesis** / **OpposingThesis** / **ReviewTemplate**: ``id``
  - **AcademicYearInfo**: ``label``

- **Pre-merge confirmation dialog** s detailním preview:
  - Tabulka „Entita → Přidá se → Konflikty"
  - Per typ entity počet **přidaných** (zelené `+N`) a **přeskočených**
    (šedé `N přeskočeno`)
  - Souhrn: *„Celkem: +N nových položek, M přeskočeno"*
  - Pokud `total_new == 0` → varování „Žádná data k přidání, merge
    nepřinese změnu" a tlačítko *Provést merge* je disabled
  - Před zápisem se vytvoří záloha ``before-merge`` v cílovém profilu
- **Závěrečný sumární dialog** po úspěšném merge — rich-text tabulka
  s počty přidaných/přeskočených entit a souborů (vč. byte size).
  Po zavření se aplikace přepne na sloučený profil; pokud je už
  aktivní, provede ``service.reload()`` + ``_refresh_all()`` (uživatel
  ihned vidí přidané položky).

### Added (API)
- ``services/profile_export.py``:
  - ``compute_merge_preview(source_zip, target_data_dir) → (MergePreview, src_db_dict)``
  - ``merge_zip_into_profile(source_zip, target_data_dir) → dict``
  - Nový dataclass ``MergePreview`` s počty per entita + soubory
- ``ProfileManager``:
  - ``merge_zip_into_profile(source_zip, target_profile_id) → dict``
  - ``compute_merge_preview(source_zip, target_profile_id) → tuple``

### Notes
- **Add-only nikdy nepřepíše**, takže merge ZIPu z jednoho zdroje
  vícekrát je idempotentní — druhý merge nic nepřidá (vše už tam je).
- **Konflikty se počítají per identity klíče** — pokud má ZIP studenta
  se stejným ``university_id`` ale jiným jménem, merge ho přeskočí
  (target verze zůstane). Pro overwrite-merge by bylo potřeba samostatný
  mód (zatím není v plánu).
- **Path-traversal ochrana** při kopírování souborů: každý entry
  z ZIPu se validuje, že stay-within cílového ``target_data_dir``
  (defenze proti adversariálním ZIPům).
- Bezpečnostní záloha ``before-merge`` se vytvoří automaticky před
  zápisem db.json — pro případný rollback z dialogu *Zálohy*.

## [0.17.2] - 2026-06-04

### Fixed
- **Dark-mode čitelnost preview boxu v Export profilu** — sumární
  tabulka „db.json / dokumenty / harmonogramy / …" měla natvrdo
  zafixované světlé pozadí ``#f5f5f5`` + světlý border ``#ddd``,
  takže v dark theme bylo světlý text na světlém pozadí (špatně
  čitelné). Přepnuto na ``palette(base)`` / ``palette(text)`` /
  ``palette(mid)`` — Qt nyní automaticky volí barvy podle systémového
  light/dark módu.

## [0.17.1] - 2026-06-04

### Added
- **Tlačítko *📝 Napsat posudek…* přímo v hlavičce detail panelu práce**
  (vedle *Smazat*). Klik → ``GenerateReviewDialog`` → vyber šablonu
  → vyplnit & otevřít. Jeden klik z aktuálně otevřené práce, bez
  pravého kliknutí ve stromu. Tlačítko se automaticky deaktivuje
  v prázdném stavu (žádná práce vybrána).
- **Auto-open režim v *GenerateReviewDialog***. Nový checkbox
  *🚀 Po vyplnění hned otevřít v Excelu (přeskočit sumární dialog)*
  default zapnuto. Workflow:
  1. Klik na *📝 Napsat posudek…* v detail panelu
  2. Vyber šablonu (auto-filtr dle typu + oboru)
  3. *📝 Vyplnit a připojit k práci*
  4. Vyplněný XLSX se rovnou otevře v Excelu — můžeš začít vyplňovat
     body hodnocení. Krátká informace v dialogu potvrdí, že soubor
     je připojen jako příloha (všechny změny v Excelu se ukládají
     přímo do něj).
  
  Pokud checkbox odškrtneš, ukáže se původní sumární dialog s ručními
  tlačítky *📄 Otevřít v Excelu* / *📂 Ukázat ve Finderu*.

### Changed
- ``ThesisDetail`` má nové attributy ``btn_generate_review`` (button v
  header rowi) a signal ``generate_review_requested``. ``MainWindow``
  signál odchytí stejným handlerem jako u kontextového menu z stromu —
  jeden code path pro oba vstupní body.
- Před emitnutím signálu se volá ``self.flush()`` aby šablona dostala
  i čerstvě zadaná data (např. právě dopsaný *Název EN*) bez nutnosti
  čekat na autosave debounce.

## [0.17.0] - 2026-06-04

### Added
- **📝 Knihovna šablon posudků** v rámci profilu. Toolbar *Šablony
  posudků* otevře ``ReviewTemplatesDialog`` s tabulkou registrovaných
  XLSX šablon (Název / Typ / Role / Jazyk / Obor / Ak. rok). Akce:
  *Přidat / Upravit / Otevřít v Excelu / Ukázat ve Finderu / Smazat*.
- **📝 Generovat posudek z šablony** — pravým klikem na práci ve stromu
  → *Generovat posudek z šablony…*. ``GenerateReviewDialog`` nabídne
  auto-filtrovaný seznam šablon pasujících k práci (typ BP/DP + obor
  studenta). Toggle *Zobrazit všechny šablony* zruší filtr.
- **Heuristický XLSX filler** (`services/review_template_filler.py`):
  - Otevře šablonu přes ``openpyxl``, projde sloupec A, hledá popisky:
    *Student* / *Vedoucí práce* / *Oponent práce* / *Téma bakalářské /
    diplomové práce* / *Akademický rok* (+ EN ekvivalenty *Supervisor* /
    *Opponent* / *Thesis Topic* / *Academic Year*).
  - Pro každý match vyplní sloupec B na stejném řádku.
  - **Respektuje předvyplněné defaulty** šablony (např. *Studijní program:
    Informační technologie*) — přepisuje JEN prázdné buňky. Výjimka:
    *Akademický rok* se vždy přepíše hodnotou z práce (volatile).
  - Ověřeno na všech 14 FAI UTB šablonách (BP + DP, CZ + EN, varianty
    KYB/SWI/UI).
- Vygenerovaný XLSX se ukládá jako příloha přes
  ``attach_document(kind=SUPERVISOR_REVIEW|OPPONENT_REVIEW)`` s
  auto-versioning (druhý pokus posudku → v2, předchozí je
  *superseded*). Po dokončení dialog nabídne tlačítka
  *📄 Otevřít v Excelu* / *📂 Ukázat ve Finderu*.
- Nový model ``models/review_template.py`` (``ReviewTemplate``) +
  service metody ``list_review_templates / get_review_template /
  register_review_template / update_review_template /
  delete_review_template / generate_review_from_template``.
- **Šablony jsou součástí profilu** — fyzicky leží v
  ``profile_dir/templates/`` a jdou s profilem v ZIP exportu (default
  zapnuto, lze odškrtnout v *Export profilu*). Manifest obsahuje
  ``stats.templates_count`` a ``contents.templates``.

### Changed
- ``SCHEMA_VERSION`` bumped na **v3**: ``Database.review_templates``
  (default prázdný list). Stará data se automaticky migrují přidáním
  prázdného pole.
- Toolbar má nové tlačítko *📝 Šablony posudků* vedle *Studenti / Oponenti
  / Vedoucí / Obory*.
- Kontextové menu na práci ve stromu má novou položku
  *📝 Generovat posudek z šablony…* (nad *Roll-back*).

### Added (dependencies)
- Nová runtime dependency: ``openpyxl >= 3.1`` (pro čtení/zápis XLSX
  šablon). Standardní balík, snadno instalovatelný přes ``pip``.

### Notes
- **Filename šablon**: aplikace generuje FS-safe název typu
  ``{8-znak-id}_{name}.xlsx`` (např.
  ``0442b3cb_Vedoucí_DP_—_SWI_20252026.xlsx``). Stejný XLSX lze přidat
  vícekrát s různými metadaty (např. CZ + EN varianta, BP + DP).
- **Versioning posudků**: každý další generated posudek stejného typu
  (vedoucí / oponent) k téže práci dostane vyšší verzi a stane se
  *current*. Předchozí verze zůstává viditelná pod toggle „Zobrazit
  starší verze" v Dokumenty widget (od 0.15.0).
- **Co heuristika neumí**: pokud šablona má hodnoty v jiném sloupci než B,
  nebo používá merged buňky atypicky, filler nemusí trefit cíl. Pro tyto
  případy lze šablonu otevřít přímo v Excelu a hodnoty doplnit ručně
  (Generovat → otevři v Excelu → uprav → ulož = stejný soubor zůstává
  jako příloha v0.17.0+).

## [0.16.1] - 2026-06-04

### Added
- **Smazat originál po nahrání** — odstraní zdrojový soubor z původního
  umístění (typicky `~/Downloads`), aby na disku nezůstával nepořádek
  s duplikáty. Default zapnuto, čitelná opt-out cesta:
  - ``DocumentsWidget`` má vedle tlačítek upload/URL nový checkbox
    *🗑 Smazat originál po nahrání*. Sticky per session, default ✓.
  - ``StagImportDialog`` má v hlavičkovém formuláři checkbox
    *🗑 Po dokončení importu smazat originální CSV*. Default ✓.
    Smazání proběhne jednorázově až *po* úspěšném dokončení všech
    příloh (CSV se zkopíruje do každé importované práce).
  - Service API: nové parametry ``attach_document(delete_source=False)``
    a ``opposing_attach_document(delete_source=False)``.
    Implementace: copy2 → upsert → optional unlink (kopie je safe-first,
    smaže až poté co target existuje).
- **Auto-select první práce po startu aplikace**. ``MainWindow`` po
  inicializaci najde první (top-most) práci v Aktuální záložce a vybere
  ji — detail panel se rovnou zobrazí, nemusíš klikat. Pokud je Aktuální
  prázdná, zkusí Budoucí, pak Historie. Žádná práce v žádné záložce →
  nic neděláme.
- **Sloupec *Posudky* v stromu prací**. Mezi *Stav* a *Oponent*
  přibyl nový sloupec, který indikuje nahrané posudky:
  - `📘 V · 📕 O` — oba posudky (vedoucí + oponent)
  - `📘 V` — jen vedoucí
  - `📕 O` — jen oponent
  - `—` — žádný posudek nahrán
  
  Tooltip ukazuje **počet verzí** každého typu (např. „📘 Posudek
  vedoucího (2×)" pokud máš dva pokusy obhajoby). Kritérium: existuje
  alespoň jedna příloha daného `AttachmentKind` (i superseded).

### Notes
- Smazání originálu je **silent** (žádný confirm dialog), protože
  checkbox sám slouží jako explicit opt-in. Selhání unlink (např.
  permission denied) je tichá — kopie je už v `documents/`, tak
  o data nepřijdeš.
- Tooltip nad checkboxem v `DocumentsWidget` vysvětluje proč to
  default zapnuté je („typicky nechce duplikáty mezi Downloads
  a documents/…").

## [0.16.0] - 2026-06-04

### Added
- **📤 Export profilu jako přenosný ZIP**. V toolbar 👤 menu nová akce
  *Exportovat aktuální profil do ZIPu…*. Dialog s checkboxy:
  - 📎 Dokumenty (přílohy k pracem) — default ✓
  - 📅 Naimportované PDF harmonogramy — default ✓
  - 💾 Krátkodobá záloha db.json.bak — default ✓
  - 🔄 Rotující 10× zálohy — default ✗ (typicky netřeba, jen pojistka)
  
  Před zápisem zobrazí preview velikosti per kategorii + celkem.
  Po dokončení sumář s kompresí + tlačítko *📂 Ukázat ve Finderu*.
  Default cílová cesta `~/Downloads/{název}_{YYYY-MM-DD}.zip`.
- **📥 Import profilu ze ZIPu**. V toolbar 👤 menu nová akce
  *Importovat profil ze ZIPu…*. Dialog s file pickerem na ZIP →
  okamžitý preview manifestu (jméno původního profilu, app verze,
  schema verze, exportováno kdy, počty souborů, celková velikost). 
  Validace:
  - Chybějící/neplatný manifest → uživatelská chyba.
  - Export verze novější než aplikace → blokace s hláškou.
  - Schema novější → warning, ale povolí (Database.model_validate
    rozhodne).
  - Path traversal v ZIP entries → odmítnuto.
  
  Po importu se aplikace **automaticky přepne na nový profil**.
  Pokud cílová složka už obsahuje `db.json`, vyžaduje explicitní
  potvrzení přes checkbox *⚠ Přepsat existující data*.
- **Per-profile export v *Správa profilů***. ``ProfileManageDialog``
  má nové tlačítko *📤 Export…* — exportuje konkrétní vybraný profil
  (nemusí být aktivní). Užitečné pro archivaci historických profilů
  nebo bulk export více profilů najednou.

### Added (API)
- Nový modul ``services/profile_export.py``:
  - ``export_profile_to_zip(profile, source_data_dir, target_zip, opts)``
  - ``read_zip_manifest(source_zip) → ImportPreview``
  - ``import_profile_from_zip(source_zip, target_data_dir, overwrite_existing)``
  - ``compute_export_preview(source_data_dir, opts) → ExportPreview``
  - Dataclasses ``ExportOptions``, ``ExportPreview``, ``ImportPreview``.
  - Exception ``ProfileExportError`` pro chyby formátu/validace.
- ``ProfileManager.export_profile_to_zip()`` a
  ``ProfileManager.import_profile_from_zip()`` — wrapper nad service
  modulem s integrací do registry (vytvoří záznam v
  ``ProfileRegistry`` s unikátním ID a deduplikací jména
  „Profil (2)" / „Profil (3)" …).
- Konstanta ``EXPORT_FORMAT_VERSION = 1`` v manifestu pro budoucí
  evoluci formátu (forward compatibility check).

### Notes
- **Manifest schema (v1)**:
  ```json
  {
    "bpdp_manager_export_version": 1,
    "exported_at": "2026-06-04T12:34:56",
    "app_version": "0.16.0",
    "schema_version": 2,
    "profile": { "name": "...", "original_id": "uuid", "user_name": "..." },
    "contents": { "db_json": true, "documents": true, ... },
    "stats": { "documents_count": N, "total_uncompressed_bytes": N }
  }
  ```
- ZIP používá ``zipfile.ZIP_DEFLATED`` — typická komprese 50–80 %
  pro text v db.json, PDF dokumenty se moc nezmenší.
- **Bezpečnost**: extrakce ZIPu validuje, že každý entry stay-within
  cílového adresáře (defenze proti `../` path traversal v adversariálním
  ZIPu).
- Atomic write: ZIP se nejdřív píše do `.zip.tmp`, na konci se
  přejmenuje. Pokud zápis selže, tmp se uklidí.
- **Užití**: ideální pro migraci na nový laptop, archivaci ukončeného
  ak. roku, sdílení mezi kolegy / s vedoucím katedry. Lze přenášet
  přes USB, iCloud Drive, email (do limitu velikosti přílohy).

## [0.15.0] - 2026-06-04

### BREAKING / Architektura
- **Status-driven taby + sloučení ASSIGNED**. Stavy práce zredukovány
  ze 7 na 6 — *Schválené téma* (`ASSIGNED`) sloučeno do *V řešení*
  (`IN_PROGRESS`). Po schválení tématu se de facto začíná na práci,
  samostatný stav přidával jen šum.
- **Filtrace tabů Aktuální / Budoucí / Historie je nově plně status-driven**.
  Rok ovlivňuje pouze řazení a grupování uvnitř tabu, ne příslušnost:
  
  | Tab        | Stavy                                                   |
  |------------|---------------------------------------------------------|
  | Budoucí    | Zájemce bez tématu, Zájemce s tématem, Vypsané téma     |
  | Aktuální   | V řešení                                                |
  | Historie   | Obhájeno, Nedokončeno                                   |
  
  Tab labely už nepoužívají rok v záhlaví (např. „Aktuální (2025/2026)"
  → jen „Aktuální").
- **SCHEMA_VERSION bumped v1 → v2**. Automatická migrace na load:
  - Všechny `Thesis` se statusem `"assigned"` se přepíšou na `"in_progress"`
    (zachová se identita práce, jen status se reklasifikuje).
  - Všechny `Attachment` bez polí `version`/`is_current` se backfillnou
    (per kind: chronologicky verze 1, 2, …, N; poslední je current).
- **ALLOWED_TRANSITIONS** aktualizováno:
  - `RESERVED → IN_PROGRESS` (přeskočit vypsání tématu — pokud uživatel
    má rovnou hotové oficiální zadání).
  - `LISTED → IN_PROGRESS` (původně to bylo přes ASSIGNED).
  - `CANCELLED → IN_PROGRESS` (re-open + 2. pokus obhajoby).
  - `CANCELLED → DEFENDED` (oprava omylu / shortcut: 2. pokus
    proběhl úspěšně, V řešení už nepotřebujeme).
  - Vstup do `IN_PROGRESS` ze zadávacích stavů vyžaduje úplné
    oficiální zadání (titul EN, body zadání, literatura). Z `CANCELLED`
    se vyžadavek nekontroluje — zadání už jednou bylo.

### Added
- **Verzování posudků a textu práce**. `Attachment` má dvě nová pole:
  - `version: int = 1` — pořadové číslo verze v rámci daného `kind` u
    konkrétní práce / posudku.
  - `is_current: bool = True` — true u poslední nahrané; ostatní téhož
    kindu se automaticky přepnou na false.
  Nahrání další přílohy stejného typu (např. druhý posudek vedoucího)
  spustí auto-versioning: dostane `version = max+1`, předchozí
  current se stane *superseded*. Funguje pro vedené práce
  (`attach_document`) i pro oponentské posudky (`opposing_attach_document`).
- **DocumentsWidget verze UI**:
  - Nový sloupec *Verze* (např. `v3 ✓   (+1 starší)`).
  - Toggle *Zobrazit starší verze (superseded)* — default skryté,
    UI nepřetížíš historickými verzemi. Po zapnutí jsou *superseded*
    řádky šedě + kurzívou.
  - Řazení: kind asc → current first → version desc. UI tedy
    vizuálně odděluje *„aktuální podle typu"* od historie.
- **Tab-aware *+ Nová práce***. Tlačítko v toolbaru čte aktuální tab
  a předvolí odpovídající status:
  - Aktuální → *V řešení* (rok = aktuální)
  - Budoucí → *Vypsané téma* (rok = příští)
  - Historie → *Obhájeno* (rok = minulý)
  - Vše / Oponentury → *Vypsané téma* (rok = aktuální)
  Tooltip vysvětluje mapping.
- Druhý pokus obhajoby flow je nyní *first-class*: z karty *Historie*
  (CANCELLED) lze stav přepnout zpět na *V řešení* (vrátit do
  Aktuální) nebo přímo na *Obhájeno*. Druhý posudek a/nebo nový text
  práce se nahrají standardně — automaticky dostane verze 2 a stane
  se current; první verze zůstává viditelná pod *Zobrazit starší verze*.

### Changed
- `_ACTIVE_STATES` v ``manage_dialogs`` aktualizováno (bez ASSIGNED).
- STAG import: `_smart_status_for_record` mapuje `datumZadani`
  vyplněno → `IN_PROGRESS` (předtím `ASSIGNED`). Heuristika i
  STAG kódy nadále fungují, jen cíl je sloučený.
- `_new_past_thesis` formulář pro Minulou práci: status combo už
  neobsahuje *Schválené téma*.

### Notes
- **Zachování dat:** existující soubory na disku se nepřejmenovávají
  ani nepřeřazují. Pouze metadata v `db.json` se přepisují automatickou
  migrací při prvním načtení.
- **Backup před migrací:** automatický `before-restore` se nevytváří,
  ale `db.json.bak` se updatuje při každém save jako vždy. Pro
  jistotu doporučuji spustit *Zálohy → Vytvořit zálohu* před prvním
  otevřením 0.15.0 (nebo si nechat git tag/working copy verze 0.14.x).

## [0.14.2] - 2026-06-04

### Added
- **STAG `stavPrace` kódy jsou nyní autoritativním zdrojem stavu**
  při importu. Tabulka mapování:
  
  | STAG kód | Popis (STAG)                              | → BPDPManager       |
  |----------|-------------------------------------------|---------------------|
  | `R`      | Rozpracovaná                              | *V řešení*          |
  | `DBPOO`  | Dokončená bez pokusu o obhajobu           | *V řešení*          |
  | `DUO`    | Dokončená s úspěšnou obhajobou            | *Obhájeno*          |
  | `DBUO`   | Dokončená, neúspěšná obhajoba             | *Nedokončeno*       |
  | `ND`     | Nedokončená práce                         | *Nedokončeno*       |
  
  Per-row default stavu v náhledu STAG importu se nyní určuje takto:
  1. **Známý STAG kód** → přímé mapování (autoritativní zdroj).
  2. Neznámý nebo prázdný kód → datumová heuristika (jako v 0.14.1).
  3. Žádné datumy → fallback z hlavičkového formuláře.
- Tooltip nad combo boxem stavu vypisuje **plné mapování STAG → BPDPManager**
  + jaký kód byl detekován + jeho lidský popis (např. *„DBPOO = Dokončená
  bez pokusu o obhajobu"*).
- Detail panel pod tabulkou vedle STAG kódu nově zobrazuje i lidsky
  čitelný popis kódu (kurzívou).

### Fixed
- BP/DP s ``stavPrace = DBPOO`` se už nezařadí defaultně jako
  *Obhájeno* (a tím pádem do *Historie*), ale jako *V řešení* —
  protože STAG explicitně říká, že obhajoba ještě neproběhla.
  Ověřeno nad reálnými CSV soubory (BP i DP s `DBPOO`).

### Notes
- `DBUO` (neúspěšná obhajoba) a `ND` (nedokončená) se mapují na
  stejný interní stav *Nedokončeno*. Nuanci „failed defense"
  vs „abandoned" lze dohledat v originálním STAG kódu — záznam
  parseru ho zachovává v ``record.stag_state_code``, který je
  viditelný v detail panelu STAG dialogu.
- Pokud STAG dodá kód, který v tabulce nemáme (např. nová verze
  STAG), import na něj nepadne — použije datumovou heuristiku
  a tooltip uživatele upozorní *„neznámý kód, použita datumová
  heuristika"*. Stačí tabulku doplnit v
  ``STAG_STATE_TO_STATUS`` a `STAG_STATE_LABELS`.

## [0.14.1] - 2026-06-04

### Changed
- **Smart per-řádkový default stavu v STAG importu**. Místo globálního
  „Obhájeno" dialog teď zvolí stav podle datumů v CSV per řádek:
  - ``datumObhajoby`` vyplněno → ``Obhájeno``
  - ``datumOdevzdani`` vyplněno (ale ne obhajoba) → ``V řešení``
  - ``datumZadani`` vyplněno (ale ne odevzdání) → ``Schválené téma``
  - jinak → fallback z formuláře (default *Schválené téma*).

  Tooltip nad combo boxem stavu vysvětluje, proč se daný stav zvolil.
  Uživatel může samozřejmě každý řádek ručně přepsat. Tím se BP/DP
  s neukončenou obhajobou už nezařazují do *Historie*, ale správně do
  *Aktuální* podle akademického roku.
- Hlavička dialogu: pole *„Default stav"* přejmenováno na *„Fallback stav"*
  + krátký help text, že reálný stav per řádek určí heuristika z dat CSV.

### Added (Roll-back nad pracemi)
- **Kontextové menu nad pracemi v stromu** — pravý klik na práci ve
  všech čtyřech vedených záložkách (*Aktuální / Budoucí / Historie / Vše*)
  i v záložce *🧐 Oponentské posudky* nabídne akci
  **🗑 Roll-back — smazat kompletně…**.
- Nový dialog ``RollbackThesisDialog`` (a varianta
  ``RollbackOpposingDialog``):
  - **Fáze 1 (Preview):** ukáže záznam práce (typ, rok, stav, student,
    oponent, název) + tabulku všech evidovaných příloh
    (štítek / název souboru / velikost / *exists*-flag), plagiátorský
    PDF protokol pokud existuje, a *orphan* soubory ve složce
    ``documents/{thesis_id}/`` (= soubory na disku, na které žádný
    záznam v DB neukazuje — typický artefakt z neúspěšného importu).
    Celková velikost k odstranění je sumarizována.
  - **Druhotné potvrzení** — *„Opravdu nenávratně smazat?"* yes/no.
  - **Fáze 2 (Summary):** počty smazaných souborů, info, že záznam
    z ``db.json`` byl odstraněn; student / oponent / vedoucí
    v registrech zůstávají (mohou být provázáni s jinými pracemi).
- Nové service API:
  - ``ThesisService.rollback_thesis(thesis_id)`` — smaže záznam +
    rekurzivně celou složku ``documents/{thesis_id}/``. Vrací
    statistiky (počet souborů, plagiat PDF, removal flag).
  - ``ThesisService.rollback_opposing_thesis(op_id)`` — analog pro
    oponentské posudky (``documents/opposing-{id}/``).
  - ``ThesisService.rollback_preview(thesis_id)`` a
    ``rollback_opposing_preview(op_id)`` — read-only pre-flight pro
    UI dialog (přílohy, plagiat PDF, orphan soubory, celková velikost).
- ``ThesesTreeWidget`` má nový signál ``rollback_requested`` (str)
  emitovaný z kontextového menu; ``_ThesesTab`` ho po flushi detailu
  obslouží otevřením příslušného dialogu.

### Verified (bez změny)
- Klíč ``temaHlavniAn`` v STAG CSV je již správně použit pro
  ``title_en`` — ověřeno smoke testem nad reálnými CSV soubory
  (DP i BP). Pokud existující importovaná data mají prázdný EN
  název, šlo o starší verzi importéru — nový import dat doplní.

### Notes
- Roll-back **neodstraní** studenta/oponenta/vedoucího z registru
  ani obor — tyto entity mohou být provázány s dalšími pracemi.
  Pokud chceš jejich úklid, spusť dialogy *Studenti / Oponenti /
  Vedoucí / Obory* a smaž jednotlivě.
- Transitní pravidla stavů (``ALLOWED_TRANSITIONS``) zůstávají
  beze změny — ``Obhájeno`` je terminální stav (neumožňuje
  vrácení na předchozí). Pro nápravu chybného stavu použij
  Roll-back a importuj/založ práci znovu.

## [0.14.0] - 2026-06-04

### Added
- **Transakční STAG import** — celý import probíhá nově v rámci
  ``ThesisService.batch()`` context manageru. Žádná data se nezapíšou
  na disk dokud import úspěšně nedokončí. Při výjimce v jakémkoli kroku
  se in-memory změny zahodí a databáze se znovu načte z disku
  (rollback). Pokud při per-řádkovém importu nastanou chyby, uživatel
  se rozhodne mezi *Zrušit import (rollback)* a *Uložit i tak (jen
  úspěšné řádky)*.
- **Pre-flight souhrn před importem** — před vlastním zápisem se ukáže
  dialog se seznamem nových entit, které se založí (studenti, oponenti,
  vedoucí, obory) i s jejich detaily (osobní číslo, obor, info, že
  oponent jde do registru jako *interní*, atd.). Uživatel může zrušit.
- **STAG CSV se připojí ke každé dotčené práci** jako příloha typu
  *STAG export*. Nový ``AttachmentKind.STAG_EXPORT`` (label „STAG
  export (CSV)"), uložení do podsložky ``stag/``, soubor pojmenovaný
  ``{Příjmení}_stag-export_{YYYY-MM-DD}.csv``. Funguje pro vedené práce
  i pro oponentské posudky.
- **Auto-navigace po importu** — po úspěšném importu se aplikace
  rovnou přepne na poslední importovanou práci v GUI (vedenou nebo
  oponentský posudek). Sumární dialog má tlačítko *👁 Zobrazit práci*.
- **Závěrečný sumář** v rich-textovém dialogu — tabulka s počty
  vytvořených/aktualizovaných prací, posudků, studentů, oponentů,
  vedoucích, přiložených CSV a přeskočených řádků. Chyby (pokud
  uživatel zvolil *Uložit i tak*) v seznamu pod tabulkou.

### Added (API)
- ``ThesisService.batch()`` — context manager pro transakční zápis.
  Save se odkládá na ``__exit__``, při výjimce se zahodí in-memory
  ``_db`` a znovu načte z disku. Bezpečné pro vnořené volání
  (depth counter).
- Nový ``AttachmentKind.STAG_EXPORT`` (+ mapování v ``file_naming``:
  kód ``stag-export``, podsložka ``stag``).

### Notes
- *Orphan souborové soubory:* pokud import skončí rollbackem až po
  připojení CSV (např. neočekávaná výjimka mezi kroky), CSV soubor
  zůstane fyzicky v ``documents/{thesis_id}/stag/`` ale bez záznamu
  v ``_db``. Aplikace ho neuvidí — z hlediska uživatele je
  neexistující. Promazání těchto orphanů je out-of-scope (nekritické,
  místa zabírají málo).
- Při importu *jednoho* řádku se aplikace přepne přímo na danou
  práci. Pokud řádků více, přepne se na *poslední* úspěšně
  importovanou — pro hromadné importy je to očekávané chování
  (uživatel chce verifikovat, že vše proběhlo, a pak prochází
  v seznamu).

## [0.13.3] - 2026-06-04

### Changed (správce oborů)
- **``OboryManageDialog`` agreguje obory podle sekretářky**. Tree
  má dvě úrovně: parent = skupina podle sekretářky (jméno + email
  + telefon), child = jednotlivé obory. Skupina „— bez sekretářky —"
  padá na konec. V hlavičce skupiny je 👤 jméno sekretářky, sumární
  počet oborů a studentů (česká plurály: *1 obor / 2-4 obory / 5+
  oborů*; *1 student / 2-4 studenti / 5+ studentů*) a kontakt
  (✉ email · ☎ telefon).
- **Nový sloupec *STAG zkratka*** vedle jména oboru — ukazuje
  ``Obor.stag_code`` (např. ``knIT-KYB``) v monospace fontu pro
  čitelnost. Obory bez vyplněného STAG kódu mají „—".
- Nové tlačítko **↕ Sbalit / rozbalit vše** pro hromadné rozbalení
  všech skupin sekretářek.
- Status bar pod tabulkou navíc zobrazuje STAG kód aktuálně
  vybraného oboru.

## [0.13.2] - 2026-06-04

### Added (STAG import — doladění UX)
- **„Tvoje jméno" je editovatelné v profilu**:
  - Pole *Tvoje jméno* v ``NewProfileDialog`` (vyplní se při vytváření
    nového profilu — používá se v STAG importu k auto-detekci role).
  - V ``ProfileManageDialog`` nový sloupec *Tvoje jméno* + tlačítko
    *👤 Tvoje jméno…* pro úpravu u existujícího profilu.
  - Nová metoda ``ProfileManager.set_user_name(profile_id, user_name)`` —
    veřejné API místo dosavadního ručního zápisu přes ``_save_registry``.
- **Pamatování poslední složky importu**:
  - Nové pole ``ProfileRegistry.last_stag_import_dir`` (persistované
    v ``profiles.json``). File dialog v STAG importu otevírá tuto
    složku, místo aby vždy začínal v ``~``. Po výběru se uloží.
- **Rozšířený náhled v STAG dialogu** — pod tabulkou je teď
  *Detail vybraného řádku* (``QSplitter``, ``QTextBrowser``), který
  pro aktuálně vybraný řádek ukáže kompletní obsah parsovaného
  záznamu: role, akce, student (vč. titulů a osobního čísla), obor
  STAG → cíl, typ + rok, STAG ID práce, zvolený stav + STAG kód
  stavu, vedoucí, oponent, známky vedoucího + oponenta, datumy
  (zadání / odevzdání / obhajoba), název CZ + EN, anotace CZ + EN,
  číslovaný seznam *Zásady pro vypracování* a *Seznam doporučené
  literatury*. Detail se obnoví při změně řádku, role, stavu i mapování
  oboru.
- **Nové sloupce v tabulce náhledu**: *Vedoucí* a *Oponent*
  (zobrazují parsované hodnoty z STAG; pro rychlou kontrolu, že
  auto-detekce role sedí na správnou osobu).

### Changed
- **Combo boxy v tabulce** mají nově neutrální čitelný styling
  s explicitními ``palette(base)`` / ``palette(text)`` barvami —
  předtím transparentní pozadí kolidovalo se zebra-rows i s tmavými
  systémovými tématy. *Role* s nedetekovanou hodnotou si zachovává
  jantarové varovné odlišení (``#fff3e0`` + hnědý text + tlustý
  rámeček), ale text je nyní viditelně tmavší (``#5d4037``).

## [0.13.1] - 2026-06-04

### Fixed
- **Opravena testovací suite** — dva pre-existing failing testy v
  `tests/test_storage.py` a `tests/test_management.py`:
  - `test_creates_db_on_first_load` nyní porovnává názvy oborů přes
    `{o.name for o in db.obory}`, protože `Database.obory` je
    `list[Obor]`, nikoli `list[str]`.
  - `test_list_obor_objects_sorted_by_name` nyní filtruje výsledek
    `list_obor_objects()` jen na přidané obory (ALPHA / MIKE / ZULU)
    a teprve nad nimi kontroluje abecední řazení — default obory
    (`NSWI-P`, `NIB-K`, `NAI-K`, …) z fixture DB jinak rozbíjely
    porovnání prvních tří položek.
- Produkční kód se nemění, oprava se týká pouze testů.

## [0.13.0] - 2026-06-04

### Added
- **Import dat ze STAG CSV exportu**. Toolbar tlačítko *📥 Import ze
  STAG…* otevře wizard:
  - Načte CSV soubor (`getKvalifikacniPrace*.csv`) s automatickým
    fallbackem encodingů (`utf-8-sig`, `utf-8`, `cp1250`, `windows-1250`,
    `iso-8859-2`) a delimiterem `;`.
  - Parsuje HTML `<ol><li>…</li></ol>` z polí `zasady` a `seznamLiter`
    na plain text (každý bod na samostatný řádek), dekóduje HTML entity
    včetně `&#x202f;` / `&nbsp;`.
  - **Auto-detekce role** uživatele per řádek: pokud se *Tvoje jméno*
    najde v `vedouciJmeno` → role *Vedu* (vytvoří/aktualizuje
    `Thesis`), pokud v `oponentJmeno` → *Oponuji* (vytvoří/aktualizuje
    `OpposingThesis`). Token-based match ignoruje akademické tituly
    a interpunkci.
  - **Náhledová tabulka** s 8 sloupci (Role / Student / Typ / Rok /
    Téma / Obor mapování / Stav / Akce). Per řádek lze přepsat roli,
    mapování oboru (kombo s lokálními obory + *Nemapováno* + *Nový obor…*),
    výchozí stav i akci (*Vytvořit* / *Aktualizovat* / *Přeskočit*).
    Akce se předvyplňuje podle toho, jestli práce s daným `adipidno`
    už existuje.
  - **Bezpečnostní záloha `before-stag-import`** se vytvoří před
    samotným zápisem — případný špatný import lze vrátit z dialogu
    👤 → 💾 Zálohy.
  - Při importu se automaticky vytvoří/aktualizují související entity
    (`Student`, `Opponent`, `Supervisor`, `Obor`), pokud chybí.
- Nový pydantic model field **`Profile.user_name`** — uložené jméno pro
  detekci role v STAG importu (per profil, např. „Petr Žáček").
- Nový pydantic model field **`Obor.stag_code`** — STAG kód oboru
  (např. `knIT-KYB`). `OborDialog` má nové pole *STAG kód*, používá se
  pro automatické mapování STAG oboru na lokální obor během importu.
- Service: `get_obor_by_stag_code()` pro lookup oboru podle STAG kódu.
- Nové soubory: `services/stag_csv_importer.py` (parser + dataclasses
  `ParsedRecord`, `ImportFile`, enum `ImportRole`), `ui/stag_import_dialog.py`
  (UI wizard).

### Notes
- Import je idempotentní — při akci *Aktualizovat* se v existujícím
  záznamu přepisují pouze prázdná pole nebo pole, která STAG dodal.
  Existující dokumenty, poznámky a stav pracovního flow se nemění.
- STAG export typicky nevrací stav práce v textu, ale jako kód
  (`DBPOO`, …). Uživatel zvolí stav per řádek (default *Obhájeno* pro
  typický historický import).

### Added (organizace dokumentů)
- **Automatické pojmenování a roztřídění souborů** do podsložek.
  Nový modul ``services/file_naming.py`` generuje cílový název
  ``{Příjmení}_{typ}_{YYYY-MM-DD}[_vN].{přípona}`` (např.
  ``Novák_posudek-vedouciho_2026-05-30.pdf``) a roztřídí soubory podle
  ``AttachmentKind`` do podsložek (``text-prace/``, ``prilohy/``,
  ``denik/``, ``zadani/``, ``posudky/``, ``prezentace/``, ``plagiat/``,
  ``ostatni/``). Versioning suffixem ``_v2``, ``_v3`` při kolizi
  ve stejný den. Diakritika v příjmení zůstává; strippují se jen
  znaky problematické na souborových systémech.
- **Auto-detekce typu při uploadu** podle původního názvu souboru
  (např. ``posudek-vedoucího.pdf`` → ``Posudek vedoucího``). Pokud
  uživatel ručně přepne ComboBox typu, jeho volba se respektuje.
- Nové ``AttachmentKind`` hodnoty: **``THESIS_APPENDIX``** (*Přílohy
  práce*) a **``WORK_JOURNAL``** (*Pracovní deník*). Pořadí enumerace
  upraveno na chronologii pracovního flow (text → přílohy → deník →
  zadání → posudky → prezentace → jiné).
- ``ThesisService.attach_document()`` a ``set_plagiarism_pdf()`` nově
  ukládají soubory pod novým názvem a do podsložky; ``url_or_path``
  resp. ``plagiarism_pdf_filename`` se ukládá vč. relativní cesty
  podsložky. Stará data (flat layout) zůstávají kompatibilní —
  ``document_absolute_path`` / ``plagiarism_pdf_path`` fungují
  pro oba způsoby zápisu.

### Notes (organizace dokumentů)
- Historické záznamy se neeskaluje — nové názvy a podsložky platí
  pouze pro nově nahrané soubory. Stávající soubory zůstávají
  v původním rozložení a pod původními názvy.

## [0.12.0] - 2026-05-17

### Added
- **Registr vedoucích** pro oponentské posudky. Nový model
  ``Supervisor`` (``models/supervisor.py``) s poli *Jméno*, *Email*,
  *Pracoviště*, *Telefon*, *Poznámka*. Drží se v ``Database.supervisors``.
- **Toolbar tlačítko *Vedoucí*** vedle *Oponenti* — otevírá
  ``SupervisorsManageDialog`` (4 sloupce: Jméno / Pracoviště / Email /
  Telefon, řazeno česky podle příjmení s ignorováním akademických titulů).
- ``SupervisorDialog`` pro vytvoření/úpravu jednoho vedoucího.
- **OpposingDetail integruje registry**: pole *Vedoucí* je nyní
  searchable ``QComboBox`` s našeptáváním z registru. Po výběru se
  **automaticky doplní email** z registry. Tlačítko `+` vedle vytvoří
  nového vedoucího a hned ho předvybere.
- Service: ``list_supervisors / get_supervisor / get_supervisor_by_name
  / upsert_supervisor / delete_supervisor``.

### Notes
- Inline pole ``OpposingThesis.supervisor_name`` a ``supervisor_email``
  zůstávají — jsou to *kopie*, ne FK. Smazání vedoucího z registry tedy
  neovlivní existující posudky.
- Vedoucí a oponenti jsou v dvou oddělených registrech (i když v praxi
  může jít o tutéž osobu v různých rolích) — zachovává to roli
  z perspektivy uživatele.

## [0.11.0] - 2026-05-17

### Added
- **Nová záložka 🧐 Oponentské posudky** — práce, kde uživatel vystupuje
  jako **oponent** (recenzuje cizí BP/DP). Oddělená od vedených prací.
- Datový model ``OpposingThesis`` (``models/opposing_thesis.py``):
  - Typ (BP/DP) + akademický rok + STAG URL
  - Inline údaje o studentovi (jméno, příjmení, obor, osobní číslo)
  - Inline údaje o vedoucím (jméno, email)
  - Název CZ + body zadání (volný text, čísluje se v Souhrnu)
  - Známka vedoucího + známka oponenta (moje) — text/combo s předvyplněnými
    hodnotami (A-F, 1-4)
  - Dokumenty: plný text práce / posudek vedoucího / posudek oponenta /
    jiné (přes ``Attachment``, soubory ve ``documents/opposing-{id}/``)
- ``Database.opposing_theses: list[OpposingThesis]`` (zpětně kompatibilní,
  default ``[]``).
- ``ThesisService`` rozšířen o:
  - ``list_opposing_theses() / get_opposing_thesis() / upsert_opposing_thesis() / delete_opposing_thesis()``
  - ``opposing_attach_document() / opposing_remove_document() / opposing_document_absolute_path()``
- ``OpposingDetail`` widget se 3 záložkami uvnitř (Souhrn / Detail / Dokumenty),
  vlastní autosave s debounce, vlastní generovaný Souhrn.
- ``OpposingTab`` widget — strom kategorizovaný podle akademických roků
  (uvnitř seřazeno česky podle příjmení studenta), 5 sloupců
  (Student / Téma / Vedoucí / Známky / Obor) + tlačítko *➕ Nový oponentský posudek*.
- **Souhrn oponentského posudku** odvozený automaticky: velký modrý header bar
  *„📋 OPONENTSKÝ POSUDEK"*, nadpisová řádka s typem + názvem + studentem,
  vedoucí + jeho email, STAG link, **velké barevné badge známky**
  (zelená A/1, žlutá C, oranžová D, červená F…), body zadání číslované,
  seznam dokumentů.
- Status bar zobrazí počty *Vedené práce: X · Oponentury: Y · …*.

### Notes
- Pole **STAG URL** je u oponentských posudků obzvlášť užitečné — typicky
  budeš mít odkaz na zadání práce v IS/STAG s posudky.
- Dokumenty oponentského posudku leží odděleně od dokumentů vedených prací
  (``documents/opposing-{id}/`` vs ``documents/{thesis_id}/``).
- Po výběru ve stromu se auto-přepne na *📋 Souhrn*; editace v *📝 Detail*.

## [0.10.0] - 2026-05-17

### Added
- **STAG URL** u každé vedené BP/DP. Nové pole ``Thesis.stag_url: str``
  (default ``""``). Editor v záložce *Téma zadání → Základní info* jako
  samostatný řádek pod hlavní lištou. Default placeholder s ukázkou
  ``https://stag.utb.cz/portal/studium/prohlizeni.html?...``.
- V **Souhrnu** se odkaz zobrazí jako klikatelný ``<a>`` link nad sekcí
  *Anotace* — kliknutí otevře v defaultním systémovém prohlížeči přes
  ``QDesktopServices.openUrl``. 📋 tlačítko pro zkopírování URL do schránky.
- Anchor handler v Souhrnu rozlišuje ``copy:`` (clipboard) a http/https/
  file/mailto schémata (otevření v prohlížeči).

### Notes
- Pole je volitelné. Pokud je prázdné, v Souhrnu se vůbec neobjevuje.
- Pro budoucí verzi (0.11.0): nová záložka „Oponentské posudky"
  pro práce, kde uživatel vystupuje jako oponent (cizí BP/DP), s vlastním
  datovým modelem (známky vedoucího + oponenta, dokumenty: plný text,
  posudek vedoucího, posudek oponenta, STAG odkaz).

## [0.9.2] - 2026-05-17

### Added
- **Akce „📥 Importovat z jiného profilu do aktuálního"** v toolbar
  👤 menu. Otevře dialog ``ImportIntoCurrentDialog``:
  - Výběr zdroje (combobox s ostatními profily, aktivní vyloučen)
  - Volitelné checkboxy: ☑ Dokumenty, ☑ Harmonogramy (db.json je vždy)
  - Žluté varování s vysvětlením, že aktuální data budou přepsána
- **Automatická záloha „before-import"** se vytvoří v ``backups/``
  PŘED přepsáním. Dá se tak vrátit přes 👤 → 💾 Zálohy.
- Po importu: flush rozdělaných změn → záloha → kopie → reload service
  → refresh UI → potvrzení se statistikou zkopírovaných položek.

### Notes
- Menu položka je disabled, pokud neexistuje žádný jiný profil
  (kromě aktivního).
- Tato akce **přepisuje** aktuální data; není to merge (sloučení).
  Pro merge bys potřeboval rozhodovat o konfliktech ID/timestampů
  jednotlivých prací — to zůstává opt-in pro budoucí verze.

## [0.9.1] - 2026-05-17

### Added
- **Import dat z jiného profilu při vytváření nového**. Toolbar
  👤 → ➕ Nový profil otevře vylepšený dialog s polem
  *Importovat data z* — combobox s nabídkou existujících profilů
  („žádný" = prázdná databáze, jinak výběr libovolného existujícího).
  - Voliteľně **přibalit dokumenty** (posudky, text práce, prezentace)
    a **PDF harmonogramy**.
  - Po vytvoření se ukáže potvrzení s počty zkopírovaných položek.
- ``ProfileManager.copy_data_into_profile(source_id, target_id, …)``
  — kopíruje ``db.json``, volitelně ``documents/`` a ``harmonograms/``.
  Nekopíruje ``backups/`` (každý profil má vlastní historii) ani
  ``.bpdpmanager.lock``.

## [0.9.0] - 2026-05-17

### Added
- **Profily — pojmenované datové sady**. Místo jediné fixované cesty
  ``~/.bpdpmanager/`` může uživatel mít víc profilů (osobní, sdílený,
  pro různé instituce…) a kdykoli mezi nimi přepínat.
  - Welcome dialog při prvním spuštění s 3 cestami:
    *Import z legacy ``~/.bpdpmanager/``* (pokud detekováno) /
    *Nový profil* / *Otevřít existující složku*.
  - **Toolbar 👤 button** s rozbalovací nabídkou:
    seznam profilů ● aktivní, *Nový profil*, *Otevřít existující*,
    *Správa profilů*, *Zálohy*.
  - **Správa profilů**: tabulka, přejmenování, otevření složky ve Finderu,
    odebrání z registry (volitelně i smazání dat).
  - Registry profilů uložen v user-config dir
    (``~/Library/Application Support/BPDPManager/profiles.json`` na macOS,
    ``~/.config/bpdpmanager/profiles.json`` na Linuxu,
    ``%APPDATA%\BPDPManager\profiles.json`` na Windows).
- **Rotující zálohy (10×)** v ``<data_dir>/backups/``:
  - Vytvořeny po každém úspěšném save (autosave / manual / transition).
  - **Dedupe podle obsahu hash** — pokud se nic nezměnilo od poslední
    zálohy, žádný nový soubor nevznikne.
  - **Rotace**: nejstarší se mažou, max 10 souborů.
  - **Před každou obnovou** se vytvoří záloha aktuálního stavu jako
    ``before-restore``, takže se dá vrátit i obnova.
- **Dialog Zálohy** (toolbar 👤 → 💾 Zálohy…): seznam s časem, označením
  a velikostí, akce *Obnovit / Otevřít složku / Smazat*.
- **Lock soubor proti dvojímu otevření profilu**: ``.bpdpmanager.lock``
  v data_dir s hostname + uživatelem + PID + timestamp + verzí.
  - Otevření profilu z **téhož Macu** (stale lock po pádu) → automaticky
    převzato.
  - Otevření profilu z **jiného zařízení** → varování s detaily lock info,
    user může pokračovat (force) nebo zrušit.
- ``ThesisService.reset(repo)`` — umožňuje přepnout profil bez nového
  service instance.
- ``JsonRepository`` umí volitelně dostat ``BackupManager`` —
  po každém save vytvoří rotující zálohu.

### Changed
- ``config.app_data_dir()`` se nyní řídí prioritou:
  1. env ``BPDPMANAGER_DATA_DIR`` (test/power-user override) →
  2. aktivní profil (přes ``set_active_data_dir``) →
  3. legacy ``~/.bpdpmanager/`` (backward compat).
- Spuštění bez ProfileManageru (env override / pytest) zůstává plně
  funkční — `app.py` rozhodne podle ``BPDPMANAGER_DATA_DIR``.
- Title aplikace ukazuje aktivní profil:
  ``BPDPManager — FAI UTB (osobní)``.

### Notes
- Pro **sdílení mezi vlastními zařízeními přes iCloud Drive**: vytvoř
  profil v iCloud složce. Lock soubor varuje, pokud je profil otevřený
  jinde. Pokud se chceš vyhnout iCloud problémům s ``.venv``-style daty,
  složka s daty profilu je čistě JSON + PDF + nahrané dokumenty —
  bezpečné pro iCloud sync. (Venv aplikace dál drž mimo iCloud, viz
  návod v README.)
- Export profilu do ``.zip`` (snapshot pro kolegy) přijde v ``0.9.1``.

## [0.8.3] - 2026-05-17

### Changed
- **Práce ve stromu se řadí česky abecedně dle příjmení studenta**
  (dříve dle stavu a názvu). Sekundárně dle křestního jména. Práce
  bez přiřazeného studenta jdou na konec skupiny.
- Řazení respektuje **českou diakritiku** přes ``locale.strxfrm``
  s ``cs_CZ.UTF-8``:
  - ``A → B → C → Č → D → Ď → E → … → H → CH → I → … → R → Ř → S → Š → … → Ž``
  - Příklad: *Aplikace, Cerný, Černý, Hájek, Chrást, Vrána, Vzorník, Žák*
- Pokud cs_CZ locale není k dispozici (Windows/exotické prostředí),
  fallback na ASCII fold přes NFD — diakritika se ignoruje, ale alespoň
  case-insensitive řazení funguje.

## [0.8.2] - 2026-05-17

### Added
- **Verdikt plagiátorství** v záložce *🔍 Plagiátorství* — 3 možnosti
  jako radio buttony s defaultem **Neposouzen**:
  - ⚪ *Neposouzen* (šedá)
  - 🔴 *Posouzen — je plagiát* (červená)
  - 🟢 *Posouzen — není plagiát* (zelená)
- Pod radio buttony je **velký barevný badge** s aktuální hodnotou
  v uppercase — rychlý vizuální feedback.
- V Souhrnu se Verdikt zobrazí jako menší barevný badge nahoře v
  sekci 🔍 Plagiátorství (zobrazí se i pokud ostatní pole nejsou
  vyplněná, ale verdikt je jiný než *Neposouzen*).
- ``PlagiarismVerdict`` enum v ``models/enums.py`` s ``label`` a
  ``color`` properties.
- ``Thesis.plagiarism_verdict: PlagiarismVerdict`` field
  (default ``NOT_ASSESSED``, JSON value ``"not_assessed"``).

## [0.8.1] - 2026-05-17

### Changed
- **Pole *Procento shody* je nyní ``QLineEdit``** s placeholderem
  („např. 12.3") a ``QDoubleValidator`` (rozsah 0–100, 2 desetinná místa).
  Žádný spinbox, který bránil přímému psaní. Klikneš, placeholder zmizí,
  napíšeš číslo (akceptuje tečku i čárku jako desetinný oddělovač).
  Prázdné pole = „nezadáno" (ukládá se jako ``None``).
- Hodnota v Souhrnu se zobrazí přes ``%g`` formátování — bez zbytečných
  nul (např. ``15`` místo ``15.0`` či ``15.30``).

### Added
- **Copy 📋 tlačítka v Souhrnu** vedle:
  - **Shoda** → zkopíruje text typu „15.3 %"
  - **Komentář** → zkopíruje plný text komentáře
  Tlačítka se zobrazí jen pokud je dané pole vyplněné.

## [0.8.0] - 2026-05-17

### Added
- **Nová záložka „🔍 Plagiátorství"** v detailu práce (pořadí: Souhrn,
  Téma zadání, Poznámky, **Plagiátorství**, Dokumenty) s třemi poli:
  - **Procento shody** (``QDoubleSpinBox``, 0–100 % s krokem 0.5 a
    desetinou). Hodnota 0 zobrazí „(nezadáno)" a do JSON se zapíše jako
    ``None``.
  - **Komentář** k výsledku (``QPlainTextEdit``).
  - **PDF protokol** s tlačítky *Vybrat PDF…*, *Otevřít*, *Odebrat*.
    Soubor se kopíruje do ``~/.bpdpmanager/documents/{thesis_id}/``.
- Souhrn práce má novou sekci **🔍 Plagiátorství**, která se zobrazí
  jen pokud je vyplněné aspoň jedno z polí (procento / komentář / PDF).
- ``Thesis`` model: ``plagiarism_similarity_pct: float | None``,
  ``plagiarism_comment: str``, ``plagiarism_pdf_filename: str | None``.
- ``ThesisService`` metody ``set_plagiarism_pdf``, ``remove_plagiarism_pdf``,
  ``plagiarism_pdf_path``.

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

[Unreleased]: https://github.com/Safronus/bpdp-manager/compare/v0.12.0...HEAD
[0.12.0]: https://github.com/Safronus/bpdp-manager/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/Safronus/bpdp-manager/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/Safronus/bpdp-manager/compare/v0.9.2...v0.10.0
[0.9.2]: https://github.com/Safronus/bpdp-manager/compare/v0.9.1...v0.9.2
[0.9.1]: https://github.com/Safronus/bpdp-manager/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/Safronus/bpdp-manager/compare/v0.8.3...v0.9.0
[0.8.3]: https://github.com/Safronus/bpdp-manager/compare/v0.8.2...v0.8.3
[0.8.2]: https://github.com/Safronus/bpdp-manager/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/Safronus/bpdp-manager/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/Safronus/bpdp-manager/compare/v0.7.8...v0.8.0
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
