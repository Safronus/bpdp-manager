# Changelog

Všechny významné změny v projektu jsou zaznamenány v tomto souboru.

Formát vychází z [Keep a Changelog](https://keepachangelog.com/cs/1.1.0/),
verzování dodržuje [Semantic Versioning](https://semver.org/lang/cs/).

## [Unreleased]

## [2.5.37] - 2026-06-15

### Added
- **Indikátor připojení ke STAG v toolbaru.** Vpravo nahoře ukazatel **STAG**
  (🟢 dostupný / 🔴 nedostupný / ⚪⏳ zjišťuje se). Aplikace lehce „pingne"
  `stag.utb.cz` po startu a pak **každých 5 minut** (jen HEAD, nic se nestahuje);
  **klik** ověří hned. Tooltip ukáže čas posledního ověření a u nedostupnosti
  i důvod (offline / TLS-certifikát / timeout).

## [2.5.36] - 2026-06-15

### Fixed
- **Aplikace nespadne, když selže zápis do cloudové složky (iCloud/Dropbox).**
  Když je `db.json` v iCloud/Dropbox a soubor je „odlehčený" (offloaded), bez
  sítě se zápis zasekne na timeout (`Errno 60`). Dřív to shodilo celou
  aplikaci (typicky při přepnutí profilu / migraci). Nově je krátkodobá `.bak`
  záloha **best-effort** (selhání neshodí vlastní uložení dat), migrace verze
  i `reset` profilu to ustojí a přepnutí profilu místo pádu **oznámí chybu**
  dialogem.

## [2.5.35] - 2026-06-15

### Changed
- **Tichá kontrola obhajob řeší jen aktuální den.** Po restartu se na pozadí
  nekontrolují všichni studenti napříč všemi dny (předchozí dny jsou v lokální
  cache, nedotazují se znovu) — jen studenti **dnešního dne** po čase obhajoby
  bez výsledku. Tím STAG po startu nezatěžuje opakovanou kontrolou všech.
  Předchozí (i nedořešené „bez obhajoby") z minulých dní dořešíš ručním
  tlačítkem **🔄 Aktualizovat** (to dál bere dnešek i dříve).

## [2.5.34] - 2026-06-15

### Fixed
- **Rozpis studentů: poslední studenti 2. dne se přiřadí ke správnému datu.**
  Když měl řádek dvousloupcového rozpisu jen pravou část (delší den), spadli
  tito studenti chybně do 1. dne (např. Liasnichy/Mlynár z 16.6. skončili na
  15.6.). Sloupec (= datum) osamoceného řádku se nově určí podle **odsazení**
  (levý sloupec začíná na okraji, osamocený pravý má odsazení navíc), takže to
  funguje i pro delší levý i delší pravý sloupec.

## [2.5.33] - 2026-06-15

### Fixed
- **Stav obhajoby se nepřiřadí podle jmenovce z jiného roku.** Párování na STAG
  podle jména nově odmítne práci, jejíž **rok obhajoby spadá mimo akademický rok
  komise** (např. `Kubíček Daniel 2019/2020` se už nepřiřadí studentovi
  `Daniel Václav Kubíček` v komisi `2025/2026`). Z kandidátů se preferuje práce
  s rokem obhajoby přímo v akademickém roce komise; podzimní i jarní termín
  (oba roky `RRRR/RRRR`) jsou platné. Chrání to i proti **vlastní starší práci**
  téhož studenta.

## [2.5.32] - 2026-06-15

### Added
- **Statistika obhajob se ukládá lokálně a po startu načte z disku.** Zjištěné
  stavy obhajob (`komise_defense_states.json` ve složce profilu) se uchovají
  mezi spuštěními, takže po startu se **tabulky i graf ukáží hned** a tichá
  kontrola **nezatěžuje STAG** opakovaným dotazováním na už zjištěné studenty —
  dotáže jen ty, kteří ještě nemají výsledek. Cache je vázaná na akademický rok
  (nový rok začíná čistý).

## [2.5.31] - 2026-06-15

### Changed
- **Ruční „🔄 Aktualizovat" kontroluje jen aktuální den a dříve.** Vynucená
  kontrola zbývajících *bez obhajoby* nově **přeskočí budoucí dny** (ti studenti
  logicky ještě neobhájili) — dotáže jen ty, jejichž obhajoba je dnes nebo už
  proběhla. Tichá kontrola beze změny.

## [2.5.30] - 2026-06-15

### Changed
- **Tlačítko „🔄 Aktualizovat" ve statistice obhajob vynutí kontrolu všech
  zbývajících.** Ruční aktualizace teď zkontroluje ze STAG **všechny** studenty
  se stavem *Bez obhajoby* — i ty, na které podle harmonogramu ještě nepřišla
  řada (průběh SZZ může jít rychleji, než je v plánu). Co doplní, se uloží do
  cache, takže **tichá kontrola** na pozadí to už znovu neřeší. Tichá kontrola
  se nemění — dál drží časové okno (~30 min po plánované obhajobě).

## [2.5.29] - 2026-06-15

### Fixed
- **Záložka Státnice ukazuje jen aktuální studenty** (regrese z 2.5.28). Párování
  jména bez titulů omylem navázalo i studenty, které jsi vedl **v minulosti**
  (např. tvá stará BP práce se přes `Bc. Jméno` v aktuálním Mgr rozpisu tvářila
  jako aktuálně vedená). Nově `komise_student_roles` bere — stejně jako tichá
  STAG kontrola — jen **vedené ve stavu V řešení** a **oponované z aktuálního
  akademického roku**; historické práce se nezapočítávají.

## [2.5.28] - 2026-06-15

### Fixed
- **Oponovaní studenti se v záložce Státnice párují přes osobní číslo.** Dřív
  se oponovaní (a fallback i vedení) párovali jen jménem, takže když měl student
  v rozpisu PDF **titul** (`Ing. Matěj Suchánek`), ale v práci ne
  (`Matěj Suchánek`), nepropojil se a v komisi/harmonogramu/statistice chyběl.
  Nově je primární klíč **osobní číslo Axxxxx** (jednoznačné u vedených
  i oponovaných — `OpposingThesis.student_university_id`) a fallback je **jméno
  bez titulů** (Ing./Bc./Mgr./Ph.D./… i „et" se ignorují).

### Removed
- Nepoužitý interní helper `_komise_fold` (sjednoceno na párování bez titulů).

## [2.5.27] - 2026-06-14

### Added
- **🔎 Filtr komisí podle jména** (pole nad stromem v záložce Komise) — část
  jména **člena** nebo **studenta** (i osobní číslo) nechá ve stromu jen
  odpovídající komise; nezáleží na velikosti písmen ani diakritice.

### Changed
- **Stav obhajoby u jednotlivých studentů v rozpisu komise.** Badge
  ✅/❌/⚠ se v rozpisu (i v harmonogramu) nově ukazuje pro **všechny** studenty
  komise z kompletní STAG kontroly (dříve jen tvoji vedení/oponovaní); tvé práce
  zůstávají přesné přes STAG ID.
- **Čitelnější sloupcový graf** statistiky — **osa Y s mřížkou** a popisky
  hodnot, **větší písmo**, přehledná **legenda** stavů, počet nad sloupci.

## [2.5.26] - 2026-06-14

### Added
- **Sloupcový graf obhajob** pod tabulkou komisí: per komise 4 sloupce (4 stavy
  vedle sebe), barva sloupců = barva komise, odstín dle stavu (tmavší =
  obhájeno → světlejší = bez obhajoby), nad sloupci počet, vlevo legenda.
- **Průběh kontroly** vedle tlačítka *🔄 Aktualizovat* — „kontroluji X/Y" během
  zjišťování stavů ze STAG a po dokončení „✓ hotovo".
- **Procenta v tabulce komisí** — u každé kategorie počet i podíl z celku komise.

### Changed
- **Statistika obhajob: dvě tabulky vedle sebe (na poloviny)** — vlevo podle
  barvy komise (+ graf pod ní), vpravo podle členů komise.
- **Členové komise se řadí podle příjmení** vzestupně s respektem k české
  diakritice (č za c, ž za z, …; tituly před i za jménem se ignorují).

## [2.5.25] - 2026-06-14

### Changed
- **Statistika obhajob flexibilně využije výšku panelu.** V záložce Státnice
  se horní detail komise (členové + rozpis studentů) výškově **přizpůsobí
  obsahu** a sekce **📊 Statistika obhajob** dole zabere **zbývající výšku**
  prostředního panelu (delší detail je zastropovaný na ~65 % s vlastním
  posuvníkem, aby na statistiku vždy zbylo místo).

## [2.5.24] - 2026-06-14

### Added
- **📊 Statistika obhajob komisí** (Státnice → spodní samostatná sekce
  prostředního panelu). Dvě tabulky: **podle barvy komise** a **podle členů
  komise**, v kategoriích **Obhájeno / Neobhájeno / Nedokončeno / Bez obhajoby**
  (+ řádek Σ). Rozsah se řídí výběrem vlevo: vybraná komise → jen ona,
  vybraný rok/stupeň → celý rok, jinak všechny roky.
- **Kontrola stavu obhajob všech studentů komisí.** Tichá STAG kontrola
  (jen v období státnic) nově zjišťuje stav **všech** studentů ze všech komisí
  (ne jen vedených/oponovaných) **podle jména** (zpřesněno typem Bc/Mgr a rokem
  obhajoby). Šetří STAG: dotazuje se až **~30 min po plánovaném čase** obhajoby
  a jen u studentů **bez výsledku** (hotové se cachují). Mimo období jen ručně
  tlačítkem **🔄 Aktualizovat**. Než se stav zjistí, je student „Bez obhajoby".

## [2.5.23] - 2026-06-13

### Added
- **📆 Přidat do kalendáře** (Státnice → panel *Můj harmonogram obhajob*).
  Tlačítko nad harmonogramem vyexportuje **nadcházející** obhajoby vybraného
  roku do kalendáře. V dialogu volíš **vedené/oponované** (defaultně obojí),
  **připomínku** (defaultně 15 min předem, lze 5/10/15/30/60 i žádnou) a cílový
  kalendář: **Apple Kalendář** / **Microsoft Outlook** (otevřou `.ics` rovnou),
  **Google Kalendář** (uloží `.ics` do *Downloads*, zobrazí ve Finderu a otevře
  stránku importu) nebo **jen uložit `.ics`**. Generuje se jeden `.ics`
  (iCalendar) s `VALARM` připomínkou; délka události dle stupně **Bc 45 min /
  Mgr 60 min**, místo = komise (barva + obor). Počet vybraných obhajob se
  v dialogu přepočítává živě; tlačítko je aktivní jen když je co přidat.

## [2.5.22] - 2026-06-13

### Changed
- **Sbalený detail práce se rozbalí při výběru jiné práce.** V záložkách se
  seznamem prací (vedené/budoucí/historie/vše/oponované): po sbalení detailu
  se kliknutím na **jinou** práci detail **automaticky znovu rozbalí** (sbalení
  je na listování — jakmile práci vybereš, ukáže se). Překreslení téže práce
  (autosave/refresh) sbalení respektuje.

## [2.5.21] - 2026-06-13

### Changed
- **Barevně odlišené „informační" záložky.** Titulky záložek **💡 Návrhy témat**
  (oranžová), **📅 Harmonogram** (tyrkysová), **🏛 Státnice** (fialová) a
  **📊 Statistiky** (modrá) jsou barevné, ať se vizuálně oddělí od pracovních
  záložek (ty zůstávají beze změny, barví se dle stavu posudků/kapacity).

## [2.5.20] - 2026-06-13

### Fixed
- **Klik na zdrojové PDF v detailu komise už neukazuje změť.** Odkaz se nově
  **otevře systémově** (výchozí prohlížeč PDF), místo aby QTextBrowser PDF
  načetl jako text. Web odkazy se otevřou v prohlížeči.
- **Zdrojová PDF u komise jsou správná.** Import nově přilepí zdrojový soubor
  **jen ke komisím, které daný PDF opravdu obsahuje** (dřív se při importu více
  PDF najednou přilepily všechny ke všem). Detail komise ukáže její **složení**
  (dodané v gitu dle stupně+oboru) **a její rozpis** — ne cizí.

## [2.5.19] - 2026-06-13

### Fixed
- **Levý panel: stabilní šířka dle stromu komisí.** Šířka se počítá jen
  z obsahu stromu (``sizeHintForColumn``), takže za seznamem komisí už není
  mezera a panel se s opakovaným klikáním nerozšiřuje (dřív zpětná vazba přes
  ``columnWidth``). Dlouhé názvy PDF se elidují (plný název v tooltipu) místo
  roztahování panelu.
- **Čitelné zvýraznění nejbližší obhajoby.** Nejbližší řádek harmonogramu se
  značí oranžovým časem „▶ HH:MM" a odpočtem „⏳ za X" (čitelné na světlém
  i tmavém motivu) — bez světlého podbarvení řádku, které dělalo text na
  tmavém motivu nečitelným.

## [2.5.18] - 2026-06-13

### Changed
- **Státnice & průběh — tři samostatné panely.** Vlevo strom komisí + PDF,
  **uprostřed** detail vybrané komise (členové + studenti) nebo přehled roku,
  **vpravo samostatný panel 📅 Můj harmonogram obhajob** — vždy kompletní pro
  vybraný rok (default aktuální), **nezávislý na vybrané komisi**. Šířka
  levého i pravého panelu se **automaticky přizpůsobí obsahu** (prostřední
  bere zbytek; ruční přetahování není potřeba).

### Added
- **Odpočet u nejbližší obhajoby.** V harmonogramu se nejbližší nadcházející
  student zvýrazní a ukáže se **živý odpočet** („za X min / h / dní").

## [2.5.17] - 2026-06-13

### Added
- **Komise — upozornění pro rok bez složení.** Když pro akademický rok ještě
  není v aplikaci kurátorované složení komisí (typicky nový rok, kde máš jen
  naimportovaný rozpis studentů), ukáže se v přehledu roku i v detailu komise
  **upozornění**, že složení bude doplněno aktualizací aplikace. Komise i tak
  fungují pro rozpis a zvýraznění, jen bez seznamu členů.

## [2.5.16] - 2026-06-13

### Fixed
- **Komise — čitelnost na tmavém motivu.** Datumy, časy, osobní čísla a počty
  vedené/oponované v přehledu i harmonogramu používaly tmavé barvy nečitelné
  na tmavém pozadí; nově jsou v odstínech čitelných na světlém i tmavém.
- **Detail komise opět ukazuje zdrojový rozpis (PDF)** — který soubor
  z „Rozpisy studentů" byl pro komisi použit (jen existující, s aktuálním
  názvem a proklikem).

### Changed
- **Přehled roku/stupně je dvousloupcový** — vlevo komise, vpravo
  **📅 Můj harmonogram obhajob** jako samostatná sekce (oddělená čárou, ať
  není přilepený ke komisím).

## [2.5.15] - 2026-06-13

### Changed
- **Záložka „Komise" přejmenována na „🏛 Státnice & průběh"** — v titulku nově
  i **rozmezí termínů** komisí (např. *15. 6. - 19. 6. 2026*).

### Fixed
- **Parser rozpisu: dlouhé jméno se slévalo s dalším sloupcem.** Když jméno
  studenta v levém sloupci doléhalo přímo na čas pravého sloupce (PDF bez
  mezery, např. „…Al-Zamili11:00 A24397…"), oba studenti splynuli do jednoho
  řádku a druhý skončil ve špatném dni. Lookahead na další slot teď povoluje
  nulovou mezeru — studenti se rozdělí správně, každý do svého dne.

## [2.5.14] - 2026-06-13

### Added
- **Komise — stav obhajoby naživo během státnic.** V rozmezí termínů komisí
  aplikace **každých 15 minut tiše** zkontroluje STAG stav vedených
  a oponovaných prací (**jen čte, nic nezapisuje**) a v rozpisu i harmonogramu
  ukáže u studenta **✅ Obhájeno / ❌ Neobhájeno / ⚠ Nedokončeno** (párování
  přes osobní číslo Axxxxx, záložně jméno). Mimo období se nespouští.

## [2.5.13] - 2026-06-13

### Changed
- **Komise — panel PDF přejmenován na „PDF soubory"** a doplněn odkaz
  **⬇ Stáhnout z webu FAI** (otevře oficiální stránku s PDF ke stažení;
  obecný odkaz, každý rok stejný).

## [2.5.12] - 2026-06-13

### Added
- **Připomínka 10 minut před obhajobou.** Když aplikace běží, 10 minut před
  obhajobou tvého **vedeného / oponovaného** studenta (dle harmonogramu
  komisí) vyskočí **oznámení** (systémová bublina, jinak okno) — kdo, kdy
  a u které komise jde na řadu. Kontrola běží každou minutu; každý slot
  oznámí jednou za běh aplikace.

## [2.5.11] - 2026-06-13

### Changed
- **Komise — chytřejší pravý panel.** Klik na **rok** nebo **stupeň (Bc/Mgr)**
  ve stromu ukáže **přehled všech komisí** dané skupiny a pod ním **📅 Můj
  harmonogram obhajob** pro daný rok (přepíná se podle vybraného roku). Po
  otevření je vybraný nejnovější rok, takže přehled i harmonogram jsou hned
  vidět. Klik na konkrétní komisi ukáže její složení a rozpis.

### Fixed
- **Komise — odstraněny staré „Zdrojová PDF" z detailu.** Stale rel-cesty se
  špatnými názvy už ve detailu komise nevisí; zdrojová PDF jsou v panelu
  „PDF souborů komisí" vlevo.

## [2.5.10] - 2026-06-13

### Added
- **Komise — 📅 Můj harmonogram obhajob.** Nové tlačítko otevře chronologický
  přehled (po dnech a časech), **kdy a kde** obhajují studenti, které **vedeš**
  (🎓) i **oponuješ** (🧐) — osobní rozvrh, kdy a u které komise máš být.
  „Kde" je komise (barva + obor). Naplní se z naimportovaných rozpisů.

## [2.5.9] - 2026-06-13

### Changed
- **Komise — role členů jako zaoblené rámečky.** Role ve složení (předseda /
  místopředseda / tajemník / člen) jsou nově **barevné zaoblené rámečky
  stejné šířky** s textem na střed (jako badge známek u prací).

## [2.5.8] - 2026-06-12

### Fixed
- **Komise — levý panel se vejde na obsah.** Šířka levé sekce (strom +
  termíny) se teď spočítá z obsahu sloupců a dopočítá při prvním zobrazení,
  takže sloupec **Termíny** je vidět celý bez vodorovného posuvníku.

## [2.5.7] - 2026-06-12

### Fixed
- **Komise — úklid seznamu PDF.** Stará PDF z první verze importu (uložená
  přímo v `komise/<rok>/`, často se špatným názvem) se už nemíchají mezi
  rozpisy — jsou ve vlastní skupině **⚠ Nezařazené (starší import)**. Pravý
  klik → **🗑 Smazat soubor z disku** (i více najednou) je odstraní; PDF
  dodaná v gitu smazat nelze.

## [2.5.6] - 2026-06-12

### Added
- **Komise — seznam PDF souborů + PDF složení v gitu.** Pod stromem je nový
  panel **📎 PDF souborů komisí** po akademických rocích, rozdělený na
  **Složení komisí** a **Rozpisy studentů**. Pravý klik → **📂 Otevřít**
  otevře vybrané PDF (i **více najednou**), dvojklik jedno. PDF **složení
  komisí** pro 2025/2026 jsou nově **součástí aplikace** (veřejná data v gitu,
  `resources/komise_pdfs/`) — načtou se do seznamu samy, bez importu.

## [2.5.5] - 2026-06-12

### Changed
- **Komise — přejmenované tlačítko a hezčí ukládání PDF.** Tlačítko
  *Importovat PDF komisí* → **📄 Import PDF rozpisu studentů**. Nahraná PDF
  se **přejmenují** (např. `rozpis-studentu_Bc_SWI_2025-2026.pdf`) a uloží do
  podsložek **`komise/<rok>/rozpisy/`** (rozpisy studentů) a
  **`komise/<rok>/slozeni/`** (složení komisí).

## [2.5.4] - 2026-06-12

### Added
- **Komise — barevné role ve složení.** V detailu komise je role každého
  člena jako barevná „pilulka": **předseda** (fialová), **místopředseda**
  (modrá), **tajemník** (zelená), **člen** (šedá).

## [2.5.3] - 2026-06-12

### Added
- **Komise — sloupec „Studenti V/O" s počty.** U každé komise je hned vidět,
  kolik v ní **vedeš** (číslo v modrém zaobleném badge) a kolik **oponuješ**
  (číslo v červeném badge) — stejný styl jako známky u prací.

## [2.5.2] - 2026-06-12

### Changed
- **Komise — přehlednější strom.** Levý strom je nově členěný **rok → stupeň
  (Bc / Mgr) → komise (barva)**; přibyl sloupec **Termíny** (dny zasedání).
  Šířka sloupců i levého panelu se přizpůsobí obsahu. Tlačítko *Otevřít web
  s rozpisy* odebráno.

## [2.5.1] - 2026-06-12

### Added
- **Komise: tlačítko „🔄 Načíst komise znovu" (úklid starých dat).** Po
  upgradu na 2.5.0 mohou v profilu zůstat **starší naimportované komise**
  (z verzí 2.3–2.4) bez oboru — duplicity nebo zmíchané barvy vedle nových
  předpřipravených komisí. Tlačítko smaže všechny komise a načte čistý seed
  z aplikace; rozpisy studentů se pak naimportují znovu z PDF (napojí se už
  na správné komise). **Zvýraznění vedených/oponovaných studentů zůstává
  beze změny** — pracuje nad rozpisem, takže funguje hned po importu.

## [2.5.0] - 2026-06-12

### Added
- **Komise SZZ: předpřipravené složení z gitu + navázání na obory.** Složení
  komisí (barva, **obor**, stupeň, členové, termíny) je nově **veřejná data
  v gitu** (`resources/komise_szz.json`) a **načte se samo po startu** —
  bez parsování PDF a bez nutnosti cokoli importovat. Žádná jména studentů
  tu nejsou (respektuje pravidlo „žádná reálná data studentů v gitu"). Pokrývá
  ak. rok 2025/2026 (11 komisí: Bc SWI ×5, Mgr NSWI ×4, Mgr NKYB, Mgr NUI).

### Fixed
- **Komise/obory už „sedí".** Každá komise je navázaná na **obor** aplikace
  (SWI/NSWI/NKYB/NUI). Slučovací klíč rozpisů je teď **(rok, stupeň, obor,
  barva)** místo jen (rok, barva, stupeň) — to opravuje míchání komisí stejné
  barvy: *Mgr fialová* je zároveň **NKYB** (kyber. bezpečnost) i **NUI**
  (učitelství informatiky), dříve se rozpisy slévaly dohromady. Rozpis se
  z PDF napojí na správnou komisi podle barvy nadpisů **a oboru** (z názvu
  programu/specializace). Starší naimportované komise bez oboru se doplní,
  ne zduplikují.

### Changed
- Schéma úložiště **v16**: `Committee.obor` + `Committee.from_seed`
  (default „"/False, bez datové migrace).

## [2.4.3] - 2026-06-12

### Fixed
- **„Otevřít" nad více vybranými dokumenty otevře všechny.** V dokumentech
  práce šlo dokumenty multi-selectovat, ale kontextová akce *Otevřít*
  (i tlačítko / dvojklik) otevřela jen jeden (aktivní řádek). Nově otevře
  **všechny vybrané** soubory i odkazy; chybějící soubory se shrnou do
  jednoho upozornění. Platí pro vedené práce i oponentury.

## [2.4.2] - 2026-06-12

### Fixed
- **Načítání známky z anglických posudků.** Vedoucí i oponentský posudek
  v **anglické šabloně FAI UTB** uvádí navrženou známku jen v závěrové větě
  („…suggest the following evaluation: B - Very Good", „…suggest
  classification with grade B"), případně s hodnotou na dalším řádku
  (oponent). Parser znal jen české fráze a „Proposed/suggested grade", takže
  u EN posudků známku **nenačetl** (zůstala prázdná). Nově rozpozná i tyto
  anglické fráze — kotveno na „suggest/propose", aby se nechytly boilerplate
  zmínky „F" („In the case of an evaluation grade of F – Insufficient…",
  „Grade F also means…") ani legenda ECTS škály.

## [2.4.1] - 2026-06-12

### Fixed
- **Aplikace hlásila špatnou verzi (zaseklá na 2.3.0).** Konstanta
  ``__version__`` v ``src/bpdpmanager/__init__.py`` se při vydáních 2.3.1,
  2.3.2 a 2.4.0 nebumpovala (měnil se jen ``pyproject.toml``), takže okno
  nápovědy, kontrola aktualizací, zámek profilu i exporty hlásily 2.3.0.
  Tichá kontrola pak donekonečna nabízela „aktualizaci na 2.4.0", která ale
  jen narážela na varování o rozpracovaných změnách. **Verze má teď jediný
  zdroj pravdy** — ``__version__`` v ``__init__.py`` (``pyproject.toml`` ji
  čte přes ``[tool.hatch.version]``), takže se aplikace a balíček nemůžou
  rozejít. README i okno nápovědy ukazují správné číslo.
- **Tichá Qt varování o fontech v terminálu.** „OpenType support missing
  for .AppleSystemUIFont…" (systémová písma macOS) se ztišují přes
  ``qt.text.font.db.warning=false``. „Populating font family aliases…
  Menlo, Monaco, …" zmizelo opravou v přehledu oborů: CSS-style seznam
  rodin se předával do ``QFont.setFamily()`` (kam nepatří) — nahrazeno
  ``setFamilies([...])`` + ``StyleHint.Monospace``.

## [2.4.0] - 2026-06-12

### Added
- **Sbalitelný detail práce ve všech záložkách s pracemi** (vedené, budoucí,
  Historie, Vše i 🧐 oponované). **Bez vybrané práce je detail úplně
  skrytý** — seznam má celou výšku záložky (zmizel prázdný prostor s hláškou
  „Vyberte práci…“). Po výběru práce se detail otevře a **tenkou lištou
  „Detail práce“** ho lze kdykoli **sbalit dolů** (zůstane jen lišta) — hodí
  se při listování dlouhými seznamy (Historie, Vše). Stav sbalení se drží
  i při přepínání prací.

### Changed
- Texty prázdného detailu aktualizovány: „ve stromu vlevo“ → „v seznamu
  nahoře“ (seznam je nad detailem).

## [2.3.2] - 2026-06-12

### Fixed
- **Změna stavu ze STAG se propíše hned do všech záložek.** Po aplikované
  aktualizaci ze STAG (jednotlivé i hromadné) se obnoví **všechny záložky**,
  ne jen ta, odkud akce běžela — obhájená práce se okamžitě objeví
  v **Historii** a záložka **Vše** ukazuje nový stav. Dříve zůstával starý
  stav vidět až do restartu aplikace.

- **Testy/stabilita: auto-kontroly bez profilu.** Tichá kontrola aktualizací
  aplikace a auto-kontrola STAG po startu se nespouští, když aplikace běží
  bez profilu (např. v testech) — modální dialog aktualizace jinak dokázal
  zablokovat testovací běh.

### Added
- **Historie: poznámka u letošního roku.** Hotové práce (obhájené /
  neobhájené / nedokončené) letošního akademického roku se v Historii
  seskupují jako ostatní roky a skupina aktuálního roku nese v titulku
  poznámku **„letošní hotové práce“**.

## [2.3.1] - 2026-06-12

### Added
- **Z detailů tiché kontroly STAG rovnou na aktualizaci.** Dialog **🔎
  Detaily…** (proužek tiché kontroly) má nová tlačítka **🔄 Aktualizovat
  vedené (N)…** a **🔄 Aktualizovat oponované (N)…** — otevřou dialog
  *Aktualizace ze STAG* **jen s dotčenými pracemi** (subset jako u
  kontextové akce) s **předpřipravenými a předzaškrtnutými návrhy** (změna
  stavu, text práce, posudky, průběh obhajoby). Odpadá ruční výběr prací
  v Importu ze STAG. Tlačítko **📥 Import ze STAG** zůstává pro **nové
  práce** (aktivní jen, když kontrola nějaké našla). Po aplikaci změn se
  obnoví všechny záložky a tichá kontrola se přepočítá (banner + odznaky 🔄).

### Fixed
- Kontrola i aktualizace **nabízejí také „Soubor s průběhem obhajoby“** —
  ověřeno a pokryto testem: chybějící průběh obhajoby se v náhledu hlásí
  jmenovitě a v aktualizaci je předzaškrtnutý.

## [2.3.0] - 2026-06-11

### Added
- **Nová záložka 🏛 Komise (SZZ).** Komise státních závěrečných zkoušek po
  akademických rocích — **složení** (role + jména) a **rozpis studentů**
  (datum · čas · osobní číslo · jméno), vše v **fakultních barvách komisí**.
  Import z fakultních PDF (**📄 Importovat PDF komisí…**): druh dokumentu se
  rozpozná automaticky, u rozpisů se komise pozná **podle barvy nadpisů**
  (extrakce barev z PDF content streamů). Náhled s checkboxy; merge dle
  roku + barvy + stupně (bez duplicit). **Zvýraznění:** 🎓 vedení studenti
  (přes osobní číslo, záložně jméno), 🧐 oponovaní (jméno), ⭐ komise, kde
  jsi členem; filtr *Jen komise s mými studenty*. PDF se ukládají
  strukturovaně do `komise/<rok>/`; tlačítko 🌐 otevře oficiální web FAI.
  Schéma úložiště v15 (pole `committees`).

## [2.2.0] - 2026-06-11

### Added
- **Odkaz na práci ve STAG — automaticky a pro všechny.** Práce stažené nebo
  aktualizované ze STAG dostávají **automaticky vyplněný odkaz** na svůj detail
  ve STAG (deterministicky odvozený ze STAG ID,
  `…CleanUrl?urlid=prohlizeni-prace-detail&praceIdno=…`) — bez zásahu
  uživatele. **Existující práce** se STAG ID dostanou odkaz **zpětně při
  startu aplikace** (tichá idempotentní migrace, bez sítě). Ručně zadaný
  odkaz se nikdy nepřepisuje.
- **Kontextová akce „🌐 Otevřít ve STAG"** — pravý klik na práci (vedené
  všech záložek i oponentury) otevře detail práce ve STAG v prohlížeči.
  Aktivní, když má práce odkaz nebo STAG ID.
- STAG sync (Aktualizovat ze STAG) nově **ukládá dohledané STAG ID** (dle
  příjmení) i odkaz k práci — dřív se dohledání zahodilo.

## [2.1.1] - 2026-06-11

### Fixed
- **Tutorial (první spuštění) v EN režimu.** Texty tutorialu byly přeložené už
  od vlny 3, ale sekce „Začínáme" se z nápovědy vytahovala podle českého
  nadpisu — v EN režimu se proto zobrazila celá nápověda místo úvodní sekce.
  Nově se hledá i anglický nadpis „Getting started". Přeložen i titulek okna
  plné nápovědy („Help — BPDPManager …").

## [2.1.0] - 2026-06-11

### Added
- **Jazyk CZ/EN — dokončeno (vlna 4c).** Přeložena poslední kapitola nápovědy
  **Import from STAG (CSV)** — anglická nápověda `napoveda_en.md` je tím
  **kompletní** (1035 řádků). Celá aplikace (UI, dialogy, tooltipy, nápověda)
  je teď plně dvojjazyčná CZ/EN; čeština zůstává výchozí.

## [2.0.4] - 2026-06-11

### Added
- **Jazyk CZ/EN — vlna 4b: anglická nápověda (část 2).** Přeloženy kapitoly
  **Thesis — detail**, **Writing a review**, **Review template library**,
  **Opposed theses**, **Topic proposals**, **Sending reviews by e-mail**,
  **Printing reviews** a **Faculty schedule**. V EN nápovědě zbývá česky už
  jen kapitola *Import ze STAG* (přijde v další vlně).

## [2.0.3] - 2026-06-11

### Added
- **Jazyk CZ/EN — vlna 4: anglická nápověda (část 1).** Nový soubor
  `napoveda_en.md` — v EN režimu ho zobrazí okno Nápovědy (F1) místo českého.
  Přeložené jsou orientační sekce: úvod, **Začínáme**, **Přehled obrazovky**,
  **Stavy práce**, **Jazyk**, **Aktualizace**, **Statistiky**, **Profily
  a data**, **Tipy** a **Spuštění**. Zbylé kapitoly (detail práce, posudky,
  šablony, odesílání, tisk, STAG import, harmonogram) jsou v EN souboru zatím
  česky s poznámkou a doloží se v dalších vlnách.

## [2.0.2] - 2026-06-11

### Added
- **Jazyk CZ/EN — vlna 3: všechny dialogy.** V EN režimu jsou nově přeložené
  dialogy napříč aplikací: STAG import/sync/konzistence, tisk posudků (MyQ),
  odesílání posudků, šablony a editor posudků, profily (správa/export/import/
  merge), zálohy, e-mail (SMTP), správa studentů/oponentů/vedoucích/oborů,
  odmítnutí zájemci, roll-backy, návrhy témat, harmonogram, exporty, welcome
  dialog i kontextová menu. Slovník vzrostl na ~900 položek; pokryté jsou
  i texty bez diakritiky a skupinové hlavičky.

## [2.0.1] - 2026-06-11

### Added
- **Jazyk CZ/EN — vlna 2: detaily a tooltipy.** V EN režimu je nově přeložený
  **detail práce** (záložky Souhrn/Téma zadání/Poznámky/Plagiátorství/Dokumenty,
  Základní info, stavová tlačítka, ukládání), **detail oponentury** (Známky,
  tlačítka), **widget Dokumenty** (tlačítka, hlavičky sloupců) a **tooltipy
  hlavního toolbaru**. Slovník má ~170 položek; zbývají dialogy a EN nápověda
  (další vlny).

## [2.0.0] - 2026-06-10

### Added
- **Přepínání jazyka CZ / EN (vlna 1).** Nové tlačítko **🌐** v toolbaru přepne
  jazyk aplikace; volba se ukládá do profilu a projeví se **po restartu**
  (nabídne se rovnou). Čeština zůstává výchozí a chování CZ režimu se nemění.
  V EN režimu je přeložená **hlavní plocha**: záložky, toolbar, globální
  hledání, hlavičky stromů prací i oponentur, kontextové akce, dashboard
  Statistik a všechny stavy/typy/formy/druhy dokumentů (enumy).
  Nepřeložené texty (detaily, dialogy) zatím zůstávají česky a doplní se
  v dalších vlnách (2.0.x) — stejně jako anglická nápověda.
- Infrastruktura překladu: modul `bpdpmanager.i18n` (`tr()`, `set_language`),
  slovník `i18n/en.py`. Čeština = zdrojový text, angličtina = překladová
  vrstva s tichým fallbackem.

## [1.18.0] - 2026-06-10

### Added
- **Automatická kontrola aktualizací.** Po startu proběhne tichá kontrola nové
  verze proti GitHubu (čte `CHANGELOG.md` z main; offline = ticho). Při nové
  verzi se otevře dialog s **changelogem všech verzí mezi** nainstalovanou a
  nejnovější; **🔄 Aktualizovat a restartovat** provede `git pull` +
  `pip install -e .` (doinstaluje nové závislosti) a aplikaci restartuje.
  K dispozici je „Přeskočit tuto verzi", „Později" i vypínač kontroly.
  Lokální neuložené změny v klonu se nikdy nepřepisují (ff-only + kontrola
  čistoty předem).

### Fixed
- **CHANGELOG.md:** doplněny omylem smazané nadpisy verzí `1.17.1` a `1.16.15`
  (jejich obsah byl slitý do sousedních sekcí).

## [1.17.4] - 2026-06-10

### Added
- **Indikace „známka bez posudku" (⚠).** Když má práce známku, ale posudek dané
  role chybí (např. po smazání přílohy), zobrazí se ve sloupci *Známky V/O*
  vedle známky oranžové **⚠** s tooltipem „Známka bez posudku: …". Platí ve
  vedených pracích (vč. historie a Vše) i v oponenturách; u budoucích prací se
  nekreslí (známky tam nehrají roli).

## [1.17.3] - 2026-06-10

### Fixed
- **Stará (špatně vyčtená) známka držela navždy.** Známka vyčtená z posudku se
  ukládala jen do prázdného pole — když se jednou uložila špatná hodnota
  (např. „B" z volného textu před opravou 1.17.2), nešlo ji obnovit: smazání
  posudku ani nové stažení ze STAG ji nepřepsalo. Nově **nahrání/stažení nového
  souboru posudku známku dané role přepíše** (nový posudek je autoritativní) —
  u vedených prací (vedoucí i oponent) i u oponentur (doplněna i větev pro
  posudek oponenta). Automatický sync při otevření práce dál jen doplňuje
  prázdné (ruční úpravy nepřepisuje).

## [1.17.2] - 2026-06-10

### Fixed
- **Načtení známky ze starších Wordových posudků (.doc/.docx).** U těchto
  posudků je navržená známka **formulářové rozevírací pole** („…navrhuji
  hodnocení [A–F]") — jeho hodnota se do textu nedostane, takže se známka
  nenačetla (a volný text typu „s hodnocením B-C" dával i špatný výsledek).
  Nově se čte **přímo vybraná hodnota dropdownu** a má **přednost** před volným
  textem. Starý binární `.doc` se kvůli tomu převádí na `.docx` (LibreOffice),
  ne na txt — `.docx` zachová formulářová pole.

### Changed
- Úklid: `extract_grade_from_file` sjednoceno (Word přes `.docx` XML), odstraněn
  původní `.doc → txt` převod (`_read_doc_text`).

## [1.17.1] - 2026-06-10

### Fixed
- **Načtení navržené známky z PDF posudku staženého ze STAG.** Tyto posudky jsou
  **AES-šifrované** (prázdné heslo, jen omezení práv) a `pypdf` je bez knihovny
  `cryptography` neuměl přečíst — extrakce textu tiše selhala a známka se
  nenačetla. Přidána závislost **`pypdf[crypto]`** (cryptography); čtení PDF teď
  funguje i u šifrovaných posudků. Selhání čtení PDF se navíc loguje (debug),
  ať je příště dohledatelné.

## [1.17.0] - 2026-06-09

### Added
- **Kontextová akce „🖨 Tisk posudku" nad vybranými pracemi.** Pravým klikem na
  vybrané práce v *Aktuálně vedené práce* (posudek vedoucího) nebo *Oponované
  práce* (posudek oponenta) se otevře dialog **Tisk posudků jen se zvolenými
  pracemi**. Funguje pro jednu i více vybraných prací (multi-select); práce bez
  hotového PDF posudku se přeskočí. Dialog `MyQPrintDialog` dostal volitelné
  zúžení `only_thesis_ids` / `only_opposing_ids`.

## [1.16.19] - 2026-06-09

### Changed
- **Statistiky — „Soubory / Největší práce" ve dvou sloupcích:** žebříček je teď
  **TOP 10** rozdělený na dva sloupce — 1.–5. vycentrované v levé polovině,
  6.–10. v pravé.

## [1.16.18] - 2026-06-09

### Changed
- **Statistiky — panel „Soubory" převeden do grafického stylu:** místo textových
  pruhů jsou teď nahoře **souhrn** (počet · velikost · počet prací), „Podle
  druhu dokumentu" jako **dva zaoblené sloupcové grafy** (vlevo počet, vpravo
  velikost) se sdílenou dot-legendou druhů, a dole **slim žebříček TOP 5
  největších prací**.

### Removed
- Mrtvý kód po převodu Souborů na grafy: `_files` (HTML), `_size_bar`,
  `_make_card`.

## [1.16.17] - 2026-06-09

### Changed
- **Statistiky — „Podle akademického roku":** panel rozdělen na dvě poloviny —
  data (tabulka stavů) jsou vycentrovaná v **levé polovině**, graf v **pravé**.

## [1.16.16] - 2026-06-09

### Changed
- **Statistiky — panel „Odměny" jako dva sloupcové grafy:** tabulka nahrazena
  dvěma **zaoblenými sloupcovými grafy** ve stylu ostatních — vlevo **odměna za
  vedení po letech** (modře), vpravo **odměna za oponentury po letech**
  (fialově). Čísla nad sloupci jsou v **tisících Kč** (např. „36k", „7,2k"),
  v titulku každého grafu je celkový součet.

### Removed
- Mrtvý kód po převodu Odměn na grafy: `_finance` (HTML tabulka) a větev
  `center` v `_make_card`.

## [1.16.15] - 2026-06-09

### Changed
- **Statistiky — „Podle akademického roku" a „Známky" jako sloupcové grafy:**
  koláče/donut nahrazeny **zaoblenými sloupci** ve stejném stylu jako ostatní
  grafy (stavy obarvené barvou stavu; známky A–F barvou známky s písmenem pod
  sloupcem).
- **Statistiky — režim „Porovnání":** sloupce **vedené** jsou nově obarvené
  **kapacitním gradientem** (zeleně < 15 < červeně, 15 žlutě) i v porovnání;
  oponované zůstávají fialové, legenda to rozlišuje.

### Removed
- Závislost na **QtCharts** ve Statistikách úplně odstraněna (všechny grafy jsou
  teď kreslené sloupce) — smazán mrtvý kód `_chart_view`, `_style_chart` a
  všechny QtCharts importy.

## [1.16.14] - 2026-06-09

### Changed
- **Statistiky — čísla nad sloupci** ve všech grafech jsou výrazně **větší**
  (zhruba 2×).
- **Statistiky — prohozeny řádky:** graf **Vývoj počtu prací po letech** je teď
  v **prvním řádku** (přes celou šířku), panely *Obory · typ · forma* / *Podle
  roku* / *Známky* ve **druhém**.
- **Statistiky — Kapacita vedení** je teď jen **text vedle Souhrnu** (bez karty
  i titulku, který „rozbíjel" vzhled): vlevo *Aktuálně vedených*, vpravo
  *Budoucí*.

## [1.16.13] - 2026-06-09

### Changed
- **Statistiky — Kapacita vedení nahoru:** přesunuta z prvního panelu **nad
  panely, vpravo vedle Souhrnu** (jako karta). Počet **odmítnutých** z ní
  vypadl — ti jsou v Souhrnu.
- **Statistiky — první panel přeorganizován na 3 sloupce:** vlevo graf **BP**,
  uprostřed graf **DP**, vpravo nahoře **Typ prací** a dole **Forma studia**
  (vše na střed). Titulek panelu je nově „Obory · typ · forma prací".
- **Statistiky — „Vývoj počtu prací po letech":** překreslen jako zaoblené
  sloupce (jako v prvním panelu) a přibyl **výchozí režim „Porovnání"** —
  vedené (modře) a oponované (fialově) vedle sebe pro každý rok, s legendou.
  Samostatné režimy *Vedené* / *Oponované* zůstávají s kapacitním gradientem.

## [1.16.12] - 2026-06-09

### Changed
- **Statistiky — graf „Vývoj počtu prací po letech":** překreslen jako zaoblené
  sloupce s rokem pod sloupcem a počtem nad ním, **bez osy Y a mřížky**. Barva
  sloupce je **kapacitní gradient** — pod 15 zeleně (čím méně, tím tmavší
  zelená), přesně **15 žlutě**, nad 15 červeně (čím více, tím tmavší červená).
- Sloupcové grafy ve Statistikách už nemají **osu Y ani vodorovné linie**
  (počty jsou na/nad sloupci).

### Removed
- Mrtvý kód po přechodu na kreslené sloupce: `_apply_axis_font` a QtCharts
  importy sloupcových grafů (`QBarSeries`, `QBarSet`, `QBarCategoryAxis`,
  `QValueAxis`).

## [1.16.11] - 2026-06-09

### Changed
- **Statistiky — panel „Obory · typ prací · kapacita":**
  - Graf oborů **rozdělen na dva** vedle sebe: vlevo **BP**, vpravo **DP**.
  - Obory se už **nesjednocují přes prefix N** — z kódu se odřízne jen forma
    (*-P/-K*) a jazyk (*-EN*); prefix *N* (DP) i specializace (*-M/-T*)
    zůstávají, takže `NSWI` ≠ `SWI` a `BTSM-M` ≠ `BTSM-T`.
  - Sloupce mají **zaoblené rohy** (kreslené ručně — QtCharts to neumí) a
    **barvu oboru**; legenda pod grafem je řada **barevných puntíků** (místo
    vestavěné, která se v úzkém panelu ořezávala na „I…").
  - **Kapacita vedení** ukazuje navíc **budoucí** počet (vypsaná/rezervovaná
    témata) z maxima 15.
- **Statistiky — panel „Odměny":** titulky sloupců tabulky se zarovnaly **nad
  své sloupce** (Qt rich-text `<th>` centroval → „plavaly" mezi sloupci).

## [1.16.10] - 2026-06-09

### Changed
- **Statistiky — Souhrn:** jednotlivé KPI bloky (počty) jsou nově skutečné
  **zaoblené pilulky** (stejný styl jako badge známek v seznamu prací). Dřív
  to byly přes HTML pravoúhlé obdélníky — Qt rich-text `border-radius`
  nerenderuje, proto jsou teď kreslené jako widgety se stylesheetem.

## [1.16.9] - 2026-06-09

### Added
- **Statistiky — panel „Obory · typ prací · kapacita":**
  - Sloupce grafu jsou nově **obarvené barvou oboru** (s legendou) — barvy
    `OBOR_COLORS` (SWI modrá, KYB fialová, UI tyrkysová, ITA oranžová, BTSM
    červená).
  - Obory se **sjednocují stejně jako v Šablonách** (`discipline_from_app_code`:
    forma *-P/-K*, jazyk *-EN* i prefix *N* se ignorují → `NKYB-P` i `NKYB-K`
    spadnou pod *KYB*).
  - Dole **třetí část — forma studia** (prezenční / kombinovaná) vedle počtů
    BP/DP a kapacity.

## [1.16.8] - 2026-06-09

### Changed
- **Statistiky — doladění panelů:**
  - **Podle akademického roku:** data (rozpad stavů) a **koláč** jsou nově
    vedle sebe **vycentrované** doprostřed panelu (dřív se rozlézaly do rohů);
    řádek „Celkem · BP · DP" se nezalamuje.
  - **Známky:** koláč má teď **legendu** (A–F s barvou a počtem) místo popisků
    natěsno v dílcích.
  - **Vývoj počtu prací po letech:** popisky osy X **vodorovně, větší a tučně**
    (řádek je přes celou šířku, je na ně místo).
  - **Obory · typ prací · kapacita:** graf nahoře přes celou šíři, dole dvě
    poloviny — vlevo **počty BP/DP**, vpravo **kapacita vedení**, obě na střed.
  - **Odměny:** tabulka vyplní **šířku i výšku** panelu (zarovnání na střed
    zachováno).
  - Přepínače (comboboxy) u panelů *Podle roku* a *Známky* jsou nově spolehlivě
    **na řádku titulku** v pravém horním rohu.

### Removed
- Mrtvý kód po úpravách: `_bar` (vodorovné HTML pruhy BP/DP).

## [1.16.7] - 2026-06-08

### Changed
- **Statistiky — reorganizace dashboardu (6 panelů):**
  - **Podle akademického roku** má teď vedle dat **koláčový graf** stavů, který se
    mění s přepínačem roku (bez legendy — popis je v datech vlevo).
  - **Podle stavu** jako samostatný panel **zrušen** (jeho koláč je teď v *Podle
    roku*).
  - **Vývoj počtu prací po letech** je **přes celou druhou řadu** (roky mají
    místo); prohozen s **Obory · typ · kapacita**, který je nově první v 1. řadě.
  - **Známky** jsou třetí v 1. řadě jako **koláčový graf** barevně dle známky
    (`GRADE_TINTS`, A zelená → F červená) — místo vodorovných pruhů.

### Removed
- Mrtvý kód po reorganizaci: `_chart_by_status`, `_chart_card`.

## [1.16.6] - 2026-06-08

### Changed
- **Statistiky — panel Známky:** sloupce jsou teď **barevně odstupňované podle
  známky** stejně jako ve sloupci *V/O* v tabulce prací (zelená A → červená F,
  `GRADE_TINTS`) a délka pruhu odpovídá počtu. Přepínač pohledu je v **pravém
  horním rohu** vedle titulku (jednotně s ostatními kartami).

## [1.16.5] - 2026-06-08

### Changed
- **Statistiky — kompaktnější dashboard:**
  - **Známky**: čísla **nad sloupci** (ne uvnitř).
  - **Vývoj počtu po letech**: přepínač *Vedené/Oponované* je teď **combobox**
    v pravém horním rohu (stejný styl jako rok).
  - **Úspěšnost obhajob** jako samostatná dlaždice **zrušena** a začleněna do
    **Podle akademického roku** (výchozí volba **„Všechny roky"**, s řádkem
    *Úspěšnost obhajob: X %*). Tato karta je teď **třetí v první řadě**.
  - Díky tomu jsou ve druhé řadě jen **Obory · typ · kapacita** a **Známky** —
    obě **širší**.

### Removed
- Mrtvý kód po sloučení: metoda `_chart_success` a nevyužité větve `_chart_card`.

## [1.16.4] - 2026-06-08

### Changed
- **Statistiky — čitelnost a layout:**
  - **Vývoj po letech**: roky na ose X zkráceny na **„YY/YY"** (17/18…) — čitelné,
    už se neořezávají.
  - **Obory**: jen **TOP 10** + „ostatní" (méně sloupců → čitelné kódy) a **čísla
    nad sloupci** (ne uvnitř).
  - **Přepínače** (rok, známky, vedené/oponované) jsou teď v **pravém horním
    rohu** karty vedle vycentrovaného titulku.
  - **Obsah karet *Odměny* a *Podle akademického roku*** je **vycentrovaný**;
    rok je navíc kompaktní seznam s barevnými tečkami stavů.

## [1.16.3] - 2026-06-08

### Removed
- **Úklid mrtvého kódu ve Statistikách.** Po přechodu na grafový dashboard se
  odstranily nepoužité HTML generátory sekcí (`_led_trend`, `_by_status`,
  `_by_type`, `_by_year`, `_by_obor`, `_defense_success`, `_grades`,
  `_grade_table`, `_opposing_summary`, `_reviews`) a osiřelá konstanta
  `_GRADE_COLORS` — `stats_tab.py` je o ~216 řádků kratší. Bez změny chování.

## [1.16.2] - 2026-06-08

### Changed
- **Statistiky — další ladění dashboardu:**
  - **Menší grafy** (nejsou „gigantické") a **menší/šikmé popisky os** (poslední
    rok u *Vývoje* už není uťatý).
  - **Obory** mají teď **svislý** sloupcový graf — popisky oborů jsou čitelné
    (dřív se na ose ukazovalo jen „…"). Karta je nižší.
  - **Titulky karet vycentrované.**
  - **Podle akademického roku**: automaticky se předvolí **aktuální** rok a
    ukazují se **jen relevantní stavy** daného roku (budoucí → vypsaná témata
    apod., historický → bez „V řešení").
  - **Obory · typ · kapacita**, **Podle roku** a **Známky** jsou vedle sebe.
  - **Známky** jsou kompaktní karta s **přepínačem 4 pohledů**: *Vedu já /
    Jsem oponent / Oponent mých vedených / Vedoucí mých oponovaných*.
  - **Soubory** a **Odměny** jsou vedle sebe; karta **Posudky** odstraněna
    (stav posudků je jinde v GUI).

## [1.16.1] - 2026-06-08

### Changed
- **Statistiky — dotažený grafový dashboard.** Podle zpětné vazby:
  - **Souhrn** (KPI) je teď **vycentrovaný banner** nahoře (ne karta).
  - **Vývoj počtu po letech** má **šikmé popisky** osy X a **přepínač Vedené /
    Oponované** (sjednocen i počet oponovaných prací).
  - **Úspěšnost obhajob** rozlišuje **Obhájeno / Neobhájeno / Nedokončeno**
    a procento je menší uprostřed donutu.
  - Nová sloučená karta **Obory · typ · kapacita**: nahoře BP/DP, uprostřed
    **vodorovný graf oborů**, dole **kapacita vedení** přes celou šířku.
  - **Podle akademického roku** je menší karta s **přepínačem roku** a rozpadem
    včetně *Neobhájeno* a *Nedokončeno*.
  - **Známky** sjednoceny do jednoho grafu se **4 sériemi**: vedené (já /
    oponent) a oponované (já / vedoucí).
  - **Soubory**, **Odměny** a **Posudky** jsou karty přes celou šířku pod sebou.

## [1.16.0] - 2026-06-08

### Changed
- **Statistiky — grafový dashboard (1. fáze).** Karty se teď rovnají do **mřížky
  s řádky stejné výšky** (v rámci řádku sjednocené, různé řádky různě vysoké) —
  konec „co pes, jiná ves". První řada jsou **reálné grafy** (QtCharts):
  **Vývoj počtu po letech** (sloupcový), **Podle stavu** (donut s legendou) a
  **Úspěšnost obhajob** (gauge-donut s procentem uprostřed). Zbylé karty zatím
  tabulkové — postupně se převedou na grafy.

### Changed
- **Statistiky jako dlaždicový dashboard.** Záložka *📊 Statistiky* už není dlouhý
  svislý seznam — jednotlivé sekce jsou teď **karty (dlaždice)**, které se
  **zalamují podle šířky okna**, takže se využije i prostor do šířky (na širokém
  monitoru víc karet vedle sebe). KPI *Souhrn* je banner přes celou šířku nahoře.
  Obsah, styl i barvy zůstávají; mění se jen rozložení.

### Fixed
- **TLS certifikát MyQ tisku.** MyQ (`myq.utb.cz`) posílal **neúplný řetězec**
  certifikátu (chyběl mezilehlý **GÉANT TLS RSA 1** / HARICA), takže Python ho
  neuměl ověřit (`CERTIFICATE_VERIFY_FAILED`). Chybějící mezičlánek (+ kořen
  HARICA) je teď **přibalený** (`resources/certs/myq_ca.pem`) a doplní se do TLS
  contextu — ověření tak **projde bez vypínání bezpečnosti**.
- **Auto-fallback.** Kdyby ověření přesto selhalo (rotace certifikátu apod.),
  tisk se **automaticky připojí i bez ověření** (MyQ je interní důvěryhodný
  server) a v dialogu to oznámí. Ruční přepínač *Ověřit TLS certifikát serveru*
  zůstává jako pojistka.

## [1.14.6] - 2026-06-08

### Changed
- **Našeptávač hledá bez diakritiky a velikosti písmen.** Napsání `gol` (i `golan`
  nebo `GOLÁŇ`) najde studenta **Goláň**. Hledá se i podle **oboru**.
- **Obor ve výsledcích našeptávače.** Každý řádek nabídky končí **oborem**
  (`… — název · NSWI-P`).

## [1.14.5] - 2026-06-08

### Changed
- **Hezčí rozbalovací tlačítka v toolbaru.** Nativní šipka menu (která na macOS
  vypadala jako „chyba") je skrytá; místo ní je za názvem tlačítka čistý znak
  **⌄** s mezerami (*🔄 Aktualizace prací ⌄*, *✉ Odeslat posudky ⌄*, *👤 profil ⌄*).

## [1.14.4] - 2026-06-08

### Removed
- **Tlačítko „✉ Odeslat sekretářce…" v záložce *Oponované práce*** — bylo
  duplicitní; odesílání oponentských posudků se řeší toolbarem **✉ Odeslat
  posudky** (skupina) v hlavním okně.

## [1.14.3] - 2026-06-08

### Added
- **Real-time našeptávač v horním vyhledávání.** Stačí napsat **kousek** příjmení
  studenta nebo názvu (i ID Axxxxx) a hned se rozbalí seznam pasujících prací.
  Každý řádek ukazuje **[záložku] · Vedená/Oponovaná · BP/DP · jméno studenta —
  název**; výběrem (Enter/klik) na práci rovnou skočíš. Tlačítko **Najít** /
  Enter bez výběru fungují jako dřív (jedna shoda skočí, víc nabídne menu).

## [1.14.2] - 2026-06-08

### Changed
- **Záložka „Vše" — barevné roky.** Hlavičky akademických roků se barevně odlišují
  podle období: **budoucí** (modře), **aktuální** (zeleně) a **minulé** (šedě).
- **Záložka „Vše" — Posudky u budoucích prací.** U prací v budoucích stavech
  (*Zájemce / Vypsané téma*) se ve sloupci **Posudky** nezobrazuje žádná hodnota
  (je tam irelevantní).

## [1.14.1] - 2026-06-08

### Added
- **Hromadné odebrání dokumentů.** V záložce *Dokumenty* lze označit více
  souborů/odkazů (Ctrl/Shift) a pravým klikem je **🗑 Odebrat vybrané** naráz
  (s jedním dotazem, zda smazat i soubory ze složky). Hromadný **export do
  složky** a **odeslání mailem** už fungovaly dřív.

### Fixed
- **Šířky sloupců v Dokumentech.** Poslední sloupec **Cesta k souboru** se teď
  roztáhne do zbývající šířky — za ním už nezůstává prázdné („černé") místo.
  Ostatní sloupce se dál přizpůsobují obsahu.

## [1.14.0] - 2026-06-08

### Added
- **Hromadné (multi-select) kontextové akce** ve stromu *vedených* i *oponovaných*
  prací. Po označení více prací (Ctrl/Shift) nabídne pravý klik:
  - **🔄 Aktualizace N prací ze STAG** — v jednom dialogu (porovná jen vybrané).
  - **📄 Otevřít texty prací** a **📘 Otevřít posudky vedoucího i oponenta** —
    otevře dostupné soubory u všech vybraných.
  - **✉ Označit / zrušit odeslání** posudků a **🖨 Označit / zrušit vytištění**.
  - **🗑 Roll-back — smazat N prací** s jedním potvrzením.
- **Otevření obou posudků.** Kontextové menu teď umí otevřít **posudek vedoucího
  i oponenta** (dřív jen jeden) — ve vedených i oponovaných pracích.

## [1.13.0] - 2026-06-08

### Added
- **Nová kategorie dokumentu „Text práce + přílohy".** Když STAG nabízí v sekci
  „elektronická podoba" jen **archiv (zip)** a žádné samostatné PDF textu (text
  i přílohy jsou v jednom balíku), zařadí se nově jako **Text práce + přílohy**
  — místo aby se tvářil jako *Text práce*. Při stahování/aktualizaci ze STAG se
  tak zobrazí správně.
- **Náprava balíků v opravném nástroji.** Tlačítko **🔄 Aktualizace prací →
  🔧 Náprava zařazení textu/příloh** (dřív „Náprava prohozeného textu/přílohy")
  teď řeší dvě věci: **prohození** (zip jako text + PDF jako příloha) i **balík**
  (zip jako text bez PDF → přeřadí na *Text práce + přílohy*). Náhled, výběr,
  záloha. Týká se prací jako Kopas BP / Jakuba DP / Jelínek BP, kde je text
  i přílohy v jednom zipu.

## [1.12.2] - 2026-06-08

### Changed
- **Počty v titulcích záložek.** Záložky **Historie**, **Vše** a **💡 Návrhy
  témat** nově ukazují v titulku **počet** (prací, resp. návrhů) v závorce —
  stejně jako už dřív *Aktuálně vedené* / *Budoucí* / *Oponované práce*. Počty
  se aktualizují i po přidání/smazání.

## [1.12.1] - 2026-06-08

### Changed
- **Oponované práce — sloupec Stav.** Stav se teď zobrazuje jako **zaoblený
  barevný badge** ve stejném stylu jako v ostatních záložkách (dřív obyčejný
  text).
- **Oponované práce — pořadí sloupců.** Sloupec **Vedoucí** je přesunut až
  **před sloupec Obor** (na konec, jako poslední údaj před oborem).
- **Dokumenty — sloupce.** Sloupec *Zdroj* nahrazen sloupcem **Formát**
  (přípona souboru — PDF / ZIP / …, nebo *odkaz* u URL). Sloupec *Cesta / URL*
  přejmenován na **Cesta k souboru** a ukazuje **celou cestu od kořene**.
  Šířky sloupců se přizpůsobují obsahu.
- **Dokumenty — barevné kategorie.** Každý druh dokumentu má barevně odlišený
  nadpis; **posudky vedoucího/oponenta** jsou sdruženy do nadřazené skupiny
  **Posudky** a dělí se až v ní.

## [1.12.0] - 2026-06-08

### Changed
- **Rozlišitelné názvy příloh.** Dvě **různé** přílohy téže práce už nedostanou
  matoucí názvy `…_prilohy_datum.zip` a `…_prilohy_datum_v2.zip` (jako by šlo
  o verze jednoho souboru). Do názvu se nově vloží **rozlišovací část z původního
  názvu** (`…_prilohy_datum_zdrojove-kody.zip`, `…_prilohy_datum_dataset.zip`).
  Týká se **příloh** a *Jiné*; text práce a posudky beze změny. Generický původní
  název (např. `prilohy.zip`) se chová jako dřív (kolize → `_v2`).

### Fixed
- **Pojistka proti prohození textu a přílohy při stahování.** Doplněny testy a
  potvrzeno, že v sekci „el. podoba" je plný text **vždy PDF** a archiv (zip…)
  vždy příloha (ani když STAG vrátí zip jako první). Jediný zip-balík (text +
  přílohy pohromadě) zůstává textem — není co povýšit, takže k prohození
  zip↔PDF nedojde. (Navazuje na opravu detekce z 1.11.0.)

## [1.11.0] - 2026-06-08

### Fixed
- **Rozpoznání plného textu vs. přílohy při stahování ze STAG.** V sekci
  „elektronická podoba" se druh už neurčuje jen **pořadím** souborů (kvůli němu
  se archiv stažený jako první ukládal jako *Text práce* a PDF textu jako
  *Příloha*). Nově platí, že **archiv (.zip/.rar/…) není nikdy plný text** a text
  je **PDF** — bere se první PDF bez „příloha" v názvu; teprve když žádné není,
  padá se zpět na pořadí.

### Added
- **Náprava prohozeného textu a přílohy.** Nové tlačítko **🔄 Aktualizace prací →
  🔧 Náprava prohozeného textu/přílohy** najde práce (vedené i oponované), kde je
  **archiv veden jako Text práce** a **PDF jako Příloha** — pozůstatek staršího
  stahování. V náhledu ukáže, co se přeřadí; po potvrzení **prohodí druh** a
  soubory **přejmenuje/přesune** do správné složky (obsah se nemění). Před
  zápisem se vytvoří záloha. Opravují se jen **jednoznačné páry** (právě jeden
  archiv-text a jedno PDF); nejasné případy se přeskočí pro ruční kontrolu.

## [1.10.0] - 2026-06-08

### Added
- **Úklid duplicitních příloh.** Nové tlačítko **🔄 Aktualizace prací → 🧹 Úklid
  duplicitních příloh** projde vedené i oponované práce a najde **přílohy**
  (druh *Příloha práce* a *Jiné*) se **shodným obsahem** — typicky tentýž soubor
  stažený ze STAG dvakrát pod různými názvy. Shoda se pozná podle **velikosti
  a kontrolního součtu**, ne podle názvu. Náhled ukáže, **co a proč** se smaže
  (vždy zůstane jedna kopie); smazání je předzaškrtnuté a potvrzuje se ručně.
  **Text práce ani posudky se neřeší.**

### Changed
- **Prevence duplicitních příloh při stahování.** Když připojuješ přílohu (nebo
  *Jiné*), jejíž **obsah** už u práce existuje, soubor se **nepřipojí podruhé** —
  zůstane stávající kopie. Nová **verze** přílohy vznikne jen při **změně
  obsahu**. Tím se odstraňuje vedlejší efekt verzování podle názvu z 1.9.0, kdy
  opětovné stažení pod jiným cílovým názvem vytvořilo duplikát.

## [1.9.0] - 2026-06-08

### Added
- **Sloupec Velikost v Dokumentech.** U vedených i oponovaných prací (ve všech
  záložkách) ukazuje seznam dokumentů velikost každého souboru (B/KB/MB/GB).

### Fixed
- **Více příloh stejného typu už se nepřepisuje.** Dvě různé přílohy stažené ze
  STAG (např. `…_part1.zip` a `…_part2.zip`) zůstanou **obě aktuální** — dřív
  druhá nahradila první jako „starší verzi". Verzování se u příloh (a typu
  *Jiné*) řeší podle **názvu souboru**, takže stejný soubor se verzuje, ale
  různé soubory koexistují. (Text práce, posudky atd. zůstávají jednoinstanční.)

## [1.8.0] - 2026-06-08

### Changed
- **Dlouhé slovní hodnocení se v PDF rozdělí do dvou polí (jen když je nutné).**
  Když se komentář nevejde na jednu stránku (sloučená buňka se v tisku nezalomí
  → dřív skočil celý na další stránku nebo se ořízl), generátor **automaticky
  rozdělí** sloučenou buňku komentáře na dva řádky a text rozdělí na hranici
  odstavce — každá část pak teče přes stránky samostatně. Druhá buňka přebírá
  styl té první (zalamování/font/okraje). Krátký komentář zůstává v jedné buňce.
  Šablony se nemění.

## [1.7.2] - 2026-06-08

### Fixed
- **Dlouhý text posudku se v PDF už neusekne.** U buněk s volným textem
  (slovní zhodnocení, zdůvodnění plagiátu) se nově **dopočítá a nastaví výška
  řádku** podle délky textu a šířky (sloučené) buňky. Dřív měla buňka pevnou
  výšku ze šablony, takže LibreOffice při exportu do PDF delší text ořízl.

## [1.7.1] - 2026-06-08

### Changed
- **Tisk: potvrzení a souhrn podle cíle.** Před tiskem se dialog zeptá na
  **potvrzení** („Vytisknout N posudků …?"). Souhrn i průběh mají znění podle
  cíle — u **systémové tiskárny** „vytištěno", u **MyQ** „odesláno do fronty".
  Platí pro obě volby.

## [1.7.0] - 2026-06-08

### Added
- **Tisk posudků i na systémovou tiskárnu.** Tlačítko v toolbaru přejmenováno
  na **🖨 Tisk posudků** a v dialogu se volí **cíl tisku**: *MyQ* (jako dosud)
  nebo *systémová tiskárna*. U systémové tiskárny vybereš zařízení z nabídky
  (CUPS, macOS/Linux) a volitelně *Oboustranně*; tiskne se přes `lp` (původní
  PDF, plná kvalita). Výběr prací, podskupiny a označení „Vytištěno" fungují
  pro oba cíle stejně.

## [1.6.1] - 2026-06-08

### Fixed
- **Tisk na MyQ — rotující bezpečnostní token.** WSF po každé odpovědi vrací
  nový `requestHash` + `requestID`, které musí použít další požadavek; jinak
  server odpoví `Bad request. Your request is probably expired.` (HTTP 400).
  Konektor je teď z odpovědí přebírá, takže nahrávací sekvence (fronta → dialog
  → odeslání souboru) projde. (Login byl opraven v 1.5.6.)

## [1.6.0] - 2026-06-08

### Added
- **Stažení českého slovníku na klik.** Když kontrola pravopisu nejede, protože
  slovník chybí nebo se nenačetl (typicky po přenosu na jiný počítač / Windows
  git `autocrlf`), v editoru posudku je tlačítko **⬇ Stáhnout český slovník** —
  stáhne ho z LibreOffice do `~/.bpdpmanager/dictionaries/` a kontrolu pravopisu
  rovnou zapne (bez restartu). Slovník se nově hledá i v tomto uživatelském
  adresáři (fallback k přibalenému).

### Fixed
- **`.gitattributes`:** hunspell slovníky (`*.aff`/`*.dic`) jsou označené jako
  binární, aby je git na jiném OS nerozbil konverzí konců řádků (to byla příčina
  hlášky „slovník se nepodařilo načíst").

## [1.5.6] - 2026-06-08

### Fixed
- **Přihlášení do MyQ — prefix „*" u stavových hodnot.** WSF dekóduje řetězec
  ve `wsfState` bez prefixu `*` jako **ID controlu** (ne jako text), takže
  jméno/PIN bez něj byly serverem brány jako prázdné. Hodnoty se nově posílají
  jako `*<jméno>` / `*<PIN>` (zjištěno z dekodéru `ControlStateCoder` v JS
  frameworku MyQ). Tím je pure-HTTP login bez závislosti na prohlížeči funkční.

## [1.5.5] - 2026-06-08

### Fixed
- **Přihlášení do MyQ — správné odeslání formuláře.** Login stránka má dvě
  záložky (přihlášení / reset PINu); server čte hodnoty, jen když je ve
  `wsfState` označená **aktivní záložka** (`CtrlMenu.selIDs`). Konektor nově
  posílá výběr záložky, jméno dává jen do `wsfState` (jeho pole je `data-nopost`)
  a jako pojmenovaná pole posílá pouze **PIN** a **jazyk** (combobox). Dřív
  server hlásil „jméno i PIN nesmí být prázdné".

## [1.5.4] - 2026-06-08

### Fixed
- **Přihlášení do MyQ.** Konektor nově **parsuje živý přihlašovací formulář**
  (pole `user` / `pwd` / `domain`, control ID se mezi sezeními liší, takže je
  nelze natvrdo) místo dřívějšího odhadu zachyceného z HARu. Vyplní jen jméno
  a PIN, ostatní pole (např. `domain`) nechá ve výchozí hodnotě.

## [1.5.3] - 2026-06-08

### Added
- **Přepínač „Ověřit TLS certifikát serveru" v tiskovém dialogu MyQ.** MyQ
  server posílá certifikát, který Python neumí ověřit (neúplný řetězec /
  interní univerzitní CA, kterou má jen keychain prohlížeče) → `CERTIFICATE_
  VERIFY_FAILED`. Odznačením se na **interní, důvěryhodný** server připojíš
  i bez ověření. Default je **zapnuto** (bezpečně). Chybová hláška na tuto
  možnost nově odkazuje.

## [1.5.2] - 2026-06-08

### Changed
- **Srozumitelnější chyba spojení s MyQ.** Rozlišuje timeout / DNS / TLS a
  zdůrazňuje, že `myq.utb.cz` je **interní služba** dostupná jen z univerzitní
  sítě (fakultní síť nebo VPN) — místo obecného „zkontroluj připojení
  k internetu".

## [1.5.1] - 2026-06-08

### Changed
- **Tiskový dialog MyQ:** uvnitř skupin „K tisku" i „Již vytištěné" jsou
  posudky nově seskupené do podskupin **🎓 Posudky vedoucího** a
  **🧐 Posudky oponenta**.

## [1.5.0] - 2026-06-08

### Added
- **Indikátor „Vytištěno".** Nový sloupec **Vytištěno** (✓/✗, vedle „Odesláno")
  v *Aktuálně vedené práce* a u **letošních** v *Oponované práce* (jinde skrytý
  — pro ostatní práce není relevantní). Přepínáš ho ručně přes pravý klik na
  práci → **🖨 Označit posudek za vytištěný** (a zpět).
- **Tiskový dialog MyQ s tím počítá.** Posudky jsou rozdělené na **K tisku —
  nevytištěné** (předzaškrtnuté) a **Již vytištěné** (samostatný seznam,
  nezaškrtnuté, pro opětovný tisk). Po úspěšném odeslání se dialog **zeptá, zda
  odeslané označit jako vytištěné**. Sloupce dialogu se přizpůsobí obsahu
  a šířka okna se odvíjí od obsahu.

### Changed
- Schéma úložiště **v14**: `Thesis.supervisor_review_printed_at` a
  `OpposingThesis.opponent_review_printed_at` (default `None`, bez datové
  migrace — stará data se načtou jako nevytištěná).

## [1.4.0] - 2026-06-08

### Added
- **Tisk posudků přes MyQ (`myq.utb.cz`).** Nové tlačítko v toolbaru
  **🖨 Tisk posudků (MyQ)** otevře dialog, kde zaškrtneš posudky z **aktuálně
  vedených** i **oponovaných** prací (nabízejí se jen ty s hotovým PDF), zadáš
  přihlašovací **jméno + PIN** (nikam se neukládají) a odešleš je do tiskové
  fronty na MyQ — **oboustranně**. Na konci souhrn (kolik odesláno / případné
  chyby). Konektor je postavený na čistém stdlib (žádné nové závislosti) a je
  záměrně izolovaný (`services/myq_client.py` + dialog + jediné napojení), aby
  šel snadno odebrat nebo rozšířit o další způsoby tisku.

## [1.3.1] - 2026-06-08

### Changed
- **Kontextové menu při výběru více prací ukazuje jen „📄 Export PDF mých
  posudků…".** Ostatní akce (aktualizace ze STAG, napsat/generovat posudek,
  otevřít posudek, Roll-back, export do ZIP…) jsou per-práce, takže se zobrazí
  jen když je vybraná **jedna** práce. Platí pro „Aktuálně vedené práce" i
  „Oponované práce".

## [1.3.0] - 2026-06-07

### Added
- **Hromadný export PDF mých posudků pro tisk.** V záložkách „Aktuálně vedené
  práce" a „Oponované práce" lze ve stromu označit více prací (Ctrl/Shift) a
  přes pravý klik → **📄 Export PDF mých posudků…** zkopírovat nejnovější PDF
  posudku (vedoucího, resp. oponenta) do zvolené složky. Práce bez vytvořeného
  PDF posudku se přeskočí; na konci se zobrazí souhrn (kolik exportováno, co
  přeskočeno). Soubor stejného názvu ve cílové složce se přepíše.

## [1.2.6] - 2026-06-07

### Changed
- **Okno „Posudek…" přizpůsobuje výšku obsahu.** Otevře se přesně tak vysoké,
  jak je potřeba (méně kritérií = nižší okno, žádné zbytečné prázdné místo);
  když se obsah nevejde na obrazovku, zastropuje se výškou obrazovky a zůstane
  posuvník.

## [1.2.5] - 2026-06-07

### Fixed
- **Odznak změn STAG 🔄 na záložce nezmizel** po vyřešení / zavření proužku
  (držel se až do restartu). Zavření proužku „tiché kontroly" (✕) ho teď
  **smaže** ze záložek (vedené i oponentury) a obnoví titulky.

## [1.2.4] - 2026-06-07

### Changed
- **Titulky sloupců v seznamech jsou vycentrované** (vedené práce — Aktuální /
  Budoucí / Historie / Vše — i Oponované práce).
- **Sjednocený styl podskupiny BP/DP na „📚 Bakalářská práce (N)" (tučně)**
  ve všech záložkách (vedené i oponentury) — vrácena ikona 📚 a tučné písmo.

## [1.2.3] - 2026-06-07

### Changed
- **Sjednocený styl podskupiny BP/DP v *Oponovaných pracích*** — nadpis
  (např. *„Bakalářská práce"*) je teď kurzívou bez ikony, stejně jako
  podskupiny ve vedených pracích.

## [1.2.2] - 2026-06-07

### Changed
- **Oponované práce: seskupení podle typu (BP / DP)** uvnitř každého roku
  (jako u vedených prací) — prázdná podskupina se nezobrazuje. Z názvu studenta
  zmizel prefix *„BP · "* (typ teď nese podskupina).

## [1.2.1] - 2026-06-07

### Changed
- **Sloupec *Odesláno*: ✓ / ✗ místo obálky** (jasnější — ✓ zeleně odesláno,
  ✗ červeně neodesláno).
- **Výraznější gradient barev u sloupce *Známky V/O*** — A sytě zelená,
  C žlutá, E červenooranžová, F/FX sytě červená; text se kreslí kontrastně
  (čitelný i na sytých barvách).
- **Sloupec plagiátorství přesunut za *Posudky*** a přejmenován na
  **„Plagiát posouzen"** (✓ = kontrola proběhla; dřív matoucí, jako by ✓
  znamenalo „je plagiát").

## [1.2.0] - 2026-06-07

### Added
- **Sloupec „Plagiát" v záložce *Aktuálně vedené práce*.** Zaoblený barevný
  badge (jako Známky): **✓ zeleně** = kontrola plagiátorství proběhla (verdikt
  je jiný než *Neposouzen*), **✗ červeně** = zatím neproběhla. Sloupec je
  jen v *Aktuálně vedených* — v Budoucích / Historii / Vše je skrytý
  (tam je irelevantní).

## [1.1.3] - 2026-06-07

### Changed
- **Ikona obálky ✉ ve sloupci *Odesláno* je větší** (čitelná obálka místo
  drobného obdélníčku); badge mírně zvětšen.

## [1.1.2] - 2026-06-07

### Changed
- **„Aktualizace práce ze STAG": pozitivní oznámení, když není co aktualizovat.**
  Dialog nyní zeleně hlásí *„✓ Vše je aktuální"* místo matoucího „1 se změnami",
  když jediným nálezem je soubor druhu, který už máš. **Za změnu se počítá jen
  něco nového** (změna stavu nebo chybějící druh souboru); soubory, jejichž
  druh už máš, jsou označené jen jako *volitelné přestažení* (nezaškrtnuté).
  Když se práce ve STAG nenajde, dialog to oznámí oranžově.

## [1.1.1] - 2026-06-07

### Added
- **Automatické předvyplnění komentáře plagiátorství.** Ve vedené práci v
  záložce *Plagiátorství* se po vyplnění **Procenta shody** a kliknutí na
  **verdikt** (je/není plagiát) komentář **sám předvyplní** doporučeným zněním
  (vč. procenta). Změna procenta auto-text obnoví. **Ruční úpravu** komentáře
  to nikdy nepřepíše (přepisuje jen prázdné pole nebo dřívější auto-text);
  *Neposouzen* nic negeneruje.

## [1.1.0] - 2026-06-07

### Added
- **Kontextová akce „🔄 Aktualizace práce ze STAG" nad vybranou prací.**
  Funguje u **vedených prací** (Aktuální / Budoucí / Historie / Vše) i
  **oponentur** — pravý klik na práci. Porovná **tu jednu práci** se STAG,
  ukáže **co se aktualizuje** (změna stavu + dohrání chybějících souborů)
  s možností volby (zaškrtávátka), a aplikuje jen vybrané (se zálohou). Když
  je vše aktuální, jasně to oznámí (nic k aktualizaci). Funguje i z Historie
  (na rozdíl od hromadné aktualizace, která bere jen práce „V řešení").

### Removed
- **Tlačítko „➕ Nový oponentský posudek…"** v záložce *Oponované práce* —
  pozbylo smysl (ruční záznam nešlo po zrušení záložky *Detail* vyplnit;
  oponentury vznikají importem ze STAG).

## [1.0.11] - 2026-06-07

### Changed
- **Oponované práce: zrušena záložka *Detail*.** U oponentur nemá smysl
  editovat body zadání, anotaci ani další „autorská" pole (práce není tvoje).
  Detail se proto odebral; **známky V/O** (jediné, co se ručně mění) se editují
  přímo v záložce **Souhrn**. Ostatní údaje (student, název, vedoucí, obor, rok)
  se plní importem ze STAG / vyčtením z posudku; jejich oprava se řeší
  **STAG re-importem**. Záložky oponentury jsou nyní **Souhrn** + **Dokumenty**.

## [1.0.10] - 2026-06-07

### Fixed
- **Odeslání oponentských posudků nabízelo i práce z předchozích let.** Dialog
  *✉ Odeslat sekretářce* (oponentury) nyní nabízí **jen posudky aktuálního
  akademického roku** — starší oponentury se sekretářce neposílají (jejich stav
  „odesláno" je irelevantní). U vedoucích posudků filtr existoval už dřív (jen
  práce *V řešení*).

## [1.0.9] - 2026-06-07

### Added
- **Kontrola pravopisu (čeština) v editoru posudku.** V poli *Celkové
  hodnocení* (a *Zdůvodnění plagiátorství*) se **podtrhnou neznámá slova**
  červenou vlnovkou; **pravý klik** na podtržené slovo nabídne **návrhy oprav**
  (uživatel vybere — žádná autokorekce). Engine je **spylls** (čistě pythonní
  hunspell, bez systémové instalace) s **přibaleným českým slovníkem**
  (LibreOffice cs_CZ). Když by spylls/slovník chyběl, funkce se ladně vypne
  a v editoru se zobrazí informační hláška.

## [1.0.8] - 2026-06-07

### Added
- **Kostra posudku ve volném hodnocení.** U **nového** posudku se do sekce
  *Celkové hodnocení, připomínky a dotazy* předvyplní tematické nadpisy
  (kostra), pod které autor píše — podle **role** (vedoucí má navíc *„Přístup,
  samostatnost a spolupráce studenta"*) a **jazyka šablony** (CZ/EN). V editoru
  je i tlačítko **🦴 Vložit kostru posudku** pro ruční vložení (do prázdného
  pole rovnou, jinak za kurzor). Rozpracovaný text se nikdy nepřepíše.

## [1.0.7] - 2026-06-07

### Fixed
- **Vyčítání známky z posudku: přednost má strukturované pole „Navržená
  známka", ne závěrová věta.** U FAI šablon se mohla v *Celkovém hodnocení*
  objevit orientační formulace (např. „navrhuji hodnocení A"), která se
  rozcházela s tabulkou — aplikace pak ukazovala špatnou známku. Nově se
  čte **hodnota z tabulkového pole** (i když ji PDF extrakce „rozhodí" na
  samostatný řádek); závěrová věta slouží jen jako **fallback u starších
  posudků bez strukturovaného pole**. Když je pole prázdné, známka se
  nehádá (zůstane nevyplněná k ručnímu doplnění).

## [1.0.6] - 2026-06-07

### Fixed
- **Oponentury: po vygenerování posudku se obnoví seznam dokumentů** v detailu
  (dřív se po vyrobení posudku přílohy nepřekreslily, dokud uživatel nepřeklikl
  na jinou práci).
- **Oponentury: Souhrn ukazuje jen aktuální přílohy, ne archiv** starších verzí
  posudků — stejně jako u vedených prací (filtr `is_current`).

## [1.0.5] - 2026-06-07

### Fixed
- **KRITICKÉ: generování posudku (XLSX + PDF) zamrzávalo na progресu.** Worker
  posudek vyrobil, ale progress dialog se nezavřel (volal se `reset()`, který
  při `autoClose=False` modální `exec()` neukončí) — aplikace „běžela a
  nedoběhla" a musela se násilně ukončit. Progress se nyní zavírá po doběhnutí
  vlákna (`finished → close()`).
- **LibreOffice převod nezamrzne ani s otevřeným LO GUI.** Konverze XLSX→PDF
  (i `.doc`→text) běží s **izolovaným uživatelským profilem**
  (`-env:UserInstallation`), takže ji neblokuje běžící instance LibreOffice.
- **Špatně doporučená šablona posudku.** U práce s oborem např. `SWI-P` se
  předvybírala cizí šablona (abecedně první, `ITA`). Předvýběr i filtr nyní
  obor **normalizují stejně jako šablony** (`SWI-P`/`NSWI-P` → `SWI`,
  `NKYB-K` → `KYB`) a přednostně volí šablonu **oboru práce**.
- **Seznam prací se po nahrání posudku obnoví** (sloupce *Známky V/O* a
  *Posudky*) — u vedených prací i oponentur, vč. dotažení známky z PDF.

### Added
- **Editor posudku: tlačítka 📄 Otevřít text práce a 📕/📘 Otevřít opačný
  posudek** (u psaného posudku vedoucího → posudek oponenta a naopak) — pro
  rychlé nahlédnutí do podkladů během psaní.
- **Kontextová akce „📝 Napsat posudek…" v záložce *Oponované práce*** (role
  oponent).

### Changed
- **Editor posudku: volba „Stav" (splnění zadání) respektuje jazyk šablony** —
  CZ šablona nabízí `splnil(a)/nesplnil(a)`, EN `fulfilled/not fulfilled`
  (ne všechny 4 najednou).
- **Světlejší zelená/červená v indikátorech posudků** (čitelné i v dark theme).
- **Odebrán duplicitní souhrn posudků vpravo nahoře v *Oponovaných pracích*** —
  totéž (pro vedené i oponentury) ukazuje barevný souhrn v dolní liště.

## [1.0.4] - 2026-06-07

### Fixed
- **„Uklidit duplicity" u šablon nyní opravdu sjednotí form-varianty.** Dřívější
  varianta slučovala jen **bajtově identické** šablony, takže u starších profilů
  zůstávaly v názvech značky `-P/-K` a EN duplicity s drobně odlišným obsahem
  (např. *NKYB-K-EN* i *NKYB-P-EN*) se nesloučily. Nově se šablony se stejným
  typem/rolí/jazykem/oborem, jejichž **název se liší jen značkou `-P/-K`**,
  **sloučí do jedné** a přeživší se **přejmenuje na form-neutrální název**
  (zmizí `-P`/`-K` i redundantní `-EN` v kódu, např. *„Vedoucí DP — NKYB (EN)"*).

## [1.0.3] - 2026-06-07

### Changed
- **Šablony posudků jsou form-neutrální.** Prezenční (`-P`) a kombinovaná
  (`-K`) forma téhož oboru nově **sdílí jednu šablonu** — posudek se liší jen
  oborem, ne formou (značky `-P/-K` jsou jen STAG rozlišení). Vestavěná
  defaultní sada se tím zredukovala z **32 na 16** šablon; názvy už nenesou
  formu (např. „Vedoucí DP — NSWI"). Výběr šablon i tak fungoval form-agnosticky
  (matchuje se na obor), takže se generování nijak nemění.

### Added
- **🧹 Uklidit duplicity** ve správci šablon — sloučí redundantní `-P/-K`
  duplicity do jedné. **Bezpečně:** sloučí jen **bajtově identické** šablony se
  shodným typem/rolí/jazykem/oborem (s náhledem), takže o odlišnou šablonu
  nepřijdeš. Určeno pro profily, které mají z dřívějška nasázených 32 šablon.

## [1.0.2a] - 2026-06-07

### Changed
- **Ladění tutoriálu / nápovědy.** Krok *Obory* nově doporučuje **nahrát
  defaultní obory** (⭐ Defaultní) a zbytek případně doplnit při importu.
  Krok *Šablony posudků* doporučuje **stáhnout defaultní šablony** a nově
  **uvádí, které obory/typy defaultní sada pokrývá a které chybí** — chybí
  zejména **BTSM (BP + DP)**, **IŘT (BP)** a anglické varianty ITA/NUI
  (doplnit ručně). Stejná poznámka doplněna do README. Jen dokumentace.

## [1.0.2] - 2026-06-07

### Changed
- **Tutoriál (Začínáme / nápověda + README):** prvnotní **import ze STAG** je
  nově prezentován jako **hlavní krok onboardingu**. STAG import sám zakládá
  **studenty, oponenty i vedoucí**, takže je nový uživatel **nemusí vytvářet
  ručně**. Krok *Studijní obory* je přeřazen na *doporučené* nastavení (kvůli
  správnému mapování a sekretářkám), kroky přečíslovány.

## [1.0.1] - 2026-06-07

### Changed
- Správce *Studenti*: checkbox **Skrýt dokončené studenty** přejmenován na
  **Skrýt historické studenty** a nově skryje i studenty s prací ve stavu
  **Nedokončeno** (dosud jen *Obhájeno*).

## [1.0.0] - 2026-06-07

První **stabilní verze (1.0.0)**. Aplikace pokrývá kompletní workflow vedení
a oponování BP/DP prací (evidence, STAG import/sync, posudky, přenos prací,
správa číselníků). Od této verze pokračuje verzování: drobné změny/fixy `0.0.1`,
větší featury `0.1.0`.

### Added
- **Real-time filtr podle příjmení** ve správci *Studenti* (necitlivý na
  diakritiku) — okamžitě zužuje strom při psaní.
- **Podskupiny podle Pracoviště** ve správci *Oponenti* — uvnitř skupin
  *Interní / Externí* se oponenti dále seskupí podle pracoviště (s mezisoučtem
  oponovaných prací u každého pracoviště).
- **Kontrolní součet oponovaných prací (Σ)** u skupin *Interní / Externí* ve
  správci *Oponenti*; souhrn dole nově uvádí i počet oponovaných prací.

## [0.88.0] - 2026-06-07

### Added
- **Export práce do ZIP s výběrem „co zahrnout".** Před uložením balíku se
  zobrazí dialog: náhled dat práce (exportují se vždy), navázané entity
  (**student / oponent / obor**) a **soubory seskupené po kategoriích** —
  odznačit lze i **jednotlivý soubor**. Defaultně vše zaškrtnuté.
- **Import práce ze ZIP umí aktualizovat existující práci.** Import **pozná,
  zda práce už existuje** (podle ID z balíku, fallback student + typ +
  akademický rok). Když existuje, nabídne *vytvořit novou* / **aktualizovat
  existující**; u aktualizace si uživatel zvolí, **co se přepíše** (data práce,
  jednotlivé entity, vybrané soubory). Když neexistuje, vytvoří novou práci
  jako dosud.

## [0.87.0] - 2026-06-07

### Added
- **Počet oponovaných prací ve správci *Oponenti*.** Nový sloupec *Oponuje prací*
  ukazuje, kolik prací daný oponent oponuje / oponoval (přes vazbu na práce).

### Changed
- **Sloupec *Téma* se už barevně nepodbarvuje.** Stav posudku vedoucího
  (u *Aktuálně vedených*) i oponentského posudku (u *Aktuálně oponovaných*)
  indikuje nadále jen barevná tečka (🟢/🟡/🔴) před názvem tématu; popis stavu
  zůstává v tooltipu buňky.

## [0.86.0] - 2026-06-07

### Added
- **Filtr podle oboru a typu (BP/DP) v záložce *Historie*.** Obory jsou
  **agregované** do skupin (**BTSM** = jakákoli BTSM varianta, **SWI**, **NSWI**,
  **NKYB**, **IRT**, **ITA**, **NUI**, **Jiné**). Filtry se kombinují se
  stávajícími (stav, oponent, známka).

## [0.85.0] - 2026-06-07

### Changed
- **Sloupec „Stav" je zaoblený barevný badge** (jako známky) — label stavu
  v zaobleném rámečku, barva textu se volí podle jasu pozadí (čitelná v light
  i dark theme). Platí v záložkách *Aktuálně vedené*, *Historie*, *Vše*.
- **„Nedokončeno" má světle šedou barvu** (s černým textem) — odlišuje opuštěné
  práce od neúspěšné obhajoby (*Neobhájeno* zůstává červené).

## [0.84.0] - 2026-06-07

### Changed
- **Rozbalovací tlačítko „Kontroly" přejmenováno na „🔄 Aktualizace prací".**
- **Tichá kontrola STAG běží automaticky jen jednou denně** (ne při každém
  startu) — zbytečně nezatěžuje STAG. Ruční spuštění (přes *Aktualizace prací
  → Zkontrolovat změny ve STAG*) běží vždy.

### Fixed
- **Drag&drop v manažeru *Oponenti* správně obnoví seznam.** Po přetažení mezi
  Interní/Externí se přesunutý oponent hned objeví v cílové skupině (refresh se
  odkládá za drop event).

## [0.83.0] - 2026-06-07

### Added
- **Kontextová akce „📄 Otevřít text práce".** Pravým klikem na práci
  v záložkách *Aktuálně vedené*, *Historie*, *Vše* i *Oponované práce* otevřeš
  plný text práce (PDF), pokud je k dispozici — jinak je akce neaktivní.

## [0.82.0] - 2026-06-07

### Added
- **Barevné odlišení oborů ve sloupci „Obor".** Obor je v barevném badge podle
  programu (BTSM, SWI, NSWI, NKYB, ITA, NUI, IRT — každý jinou barvou, ostatní
  dostanou stálou barvu z palety). U **anglických variant** (-EN) je navíc
  **🇬🇧 vlaječka**. Forma (-P/-K) na barvu nemá vliv. Platí v záložkách, kde je
  sloupec Obor (*Aktuálně vedené*, *Historie*, *Vše*, *Oponované práce*).

## [0.81.0] - 2026-06-07

### Added
- **Drag&drop v manažeru *Oponenti*.** Oponenta lze přetáhnout mezi skupinami
  **Interní** a **Externí** — tím se mu změní typ.

## [0.80.1] - 2026-06-07

### Changed
- **Sloupec „Odesláno" má styl jako známky** — obálka ✉ v zaobleném barevném
  čtverečku (zelená odesláno / červená neodesláno) místo podbarvení celé buňky.
- **Hlavička sloupce známek je „Známky V/O"** (místo jen „V/O").

## [0.80.0] - 2026-06-07

### Added
- **Kontextová akce „Otevřít posudek".** U **vedených prací** pravý klik →
  **📕 Otevřít posudek oponenta** (otevře PDF posudku oponenta, je-li
  k dispozici; jinak je akce neaktivní). U **oponovaných prací aktuálního
  roku** pravý klik → **📘 Otevřít posudek vedoucího** (obdobně).

## [0.79.0] - 2026-06-07

### Changed
- **Sloupec „Posudky" má nový styl — barevné V/O.** Místo ikonek je dvojice
  písmen **V** (vedoucí) / **O** (oponent) na **zeleném pozadí (k dispozici)**
  nebo **červeném (chybí)** — v záložkách *Aktuálně vedené*, *Vše* i *Oponované
  práce*.

### Added
- **Sloupec „Posudky" i v záložce *Oponované práce*** (V = posudek vedoucího,
  O = posudek oponenta).

## [0.78.0] - 2026-06-07

### Changed
- **Sloupec „Odesláno" je názornější — obálka ✉ na barevném pozadí.** Místo
  textu *✉ ✓ / ✉ ✗* je v záložkách *Aktuálně vedené*, *Vše* i *Oponované
  práce* obálka s **pozadím zeleně (odesláno) / červeně (neodesláno)**.

## [0.77.0] - 2026-06-07

### Changed
- **Rozbalovací tlačítko „🔎 Kontroly" v toolbaru (vpravo).** Sloučí akce
  *Zkontrolovat změny ve STAG*, *Kontrola se STAG (chybějící soubory)* a
  *Přeřadit průběh obhajoby* do jednoho menu. Tlačítko *Zkontrolovat* zmizelo
  z proužku (je v menu).
- **Proužek tiché kontroly se po 15 s sám skryje**, když je vše aktuální
  (žádné novinky → nepřekáží). Při změnách zůstává.
- **Sloupec „Obor" je v záložce *Oponované práce* poslední** — stejně jako
  v ostatních záložkách.

## [0.76.0] - 2026-06-07

### Added
- **Parsování titulů u vedoucích/oponentů ze STAG.** STAG dává jména ve formátu
  *„Příjmení Jméno, tituly"* (vše za jménem). Při stahování práce se nově
  **rozparsuje** na *tituly před / jméno / tituly za* (např.
  `Novák Jan, prof. Ing. Ph.D.` → před `prof. Ing.`, jméno `Jan Novák`, za
  `Ph.D.`). Tituly se třídí podle známých seznamů (nehádá se).
- **Tlačítko „🧹 Uklidit tituly"** v manažeru *Oponentů* i *Vedoucích* — projde
  existující záznamy (i denormalizované jméno vedoucího u oponentur) a po
  **náhledu** je rozparsuje do polí. Vyřeší nepořádek u dříve stažených.

### Changed
- **Tituly za jménem se zobrazují s čárkou.** `compose_titled_name` teď vždy
  oddělí post-nominální tituly čárkou (`Jan Novák, Ph.D.`) — sjednoceno
  bez ohledu na to, jak byly uloženy.

## [0.75.1] - 2026-06-07

### Fixed
- **Čitelnost zelené v titulku budoucích prací (dark theme).** Prahové barvy
  počtu jsou světlejší (zelená/žlutá/červená), čitelné i v tmavém motivu.

### Added
- **Barva titulku podle dokončenosti posudků.** *Aktuálně vedené práce* a
  *🧐 Oponované práce* mají počet **zeleně, když jsou všechny posudky hotové
  i odeslané**, jinak **oranžově** (něco chybí) — vidíš stav na první pohled.

## [0.75.0] - 2026-06-07

### Added
- **Počty prací v titulcích záložek.** *Aktuálně vedené práce*, *Práce v dalším
  akademickém roce* a *🧐 Oponované práce* (aktuální rok) ukazují u názvu počet.
  U **budoucích** prací je počet **barevný podle kapacity**: pod 15 zeleně,
  rovných 15 žlutě, nad 15 červeně. Počty se průběžně aktualizují a kombinují
  se s odznakem 🔄 tiché kontroly STAG.

## [0.74.3] - 2026-06-07

### Changed
- **Panel „Přechod do stavu" se skrývá u historických prací všude.** Dosud jen
  v záložce Historie; nově i v záložce *Vše* (a kdekoli jinde) — panel se
  ukáže jen u rozpracovaných prací (*Aktuálně vedené* / budoucí), u
  *Obhájeno / Neobhájeno / Nedokončeno* se skryje.
- **Záložka „Práce v dalším akademickém roce" skrývá nepotřebné sloupce.**
  Budoucí práce ještě nemají známky ani posudky, takže se v ní nezobrazují
  sloupce **V/O** (známky), **Posudky** ani **Odesláno**.

## [0.74.2] - 2026-06-07

### Added
- **Náhled tiché kontroly ukazuje i seznam „zkontrolováno a aktuální".** Pro
  ověření/debug, že kontrola opravdu proběhla a které práce prošla. Tlačítko
  **🔎 Detaily…** v proužku je dostupné **i když je vše aktuální** (otevře
  náhled se jmenným seznamem zkontrolovaných prací).

## [0.74.1] - 2026-06-07

### Fixed
- **Soubory s průběhem obhajoby se rozpoznají spolehlivě podle STAG sekce.**
  STAG má tyto soubory označené přímo (sekce „Soubor s průběhem obhajoby"),
  takže se nově kategorizují podle **STAG sekce**, ne podle názvu — funguje
  i u generických názvů (např. `botek.pdf`). Týká se nově stahovaných souborů
  i přeřazení už stažených (🗂 Přeřadit průběh obhajoby je předzaškrtne).

## [0.74.0] - 2026-06-07

### Changed
- **Záložka „Historie" skrývá panel „Přechod do stavu".** U hotových prací není
  potřeba; přeřazení (např. Nedokončeno → Neobhájeno) řeš přes STAG nebo
  kontextové menu. V ostatních záložkách zůstává.
- **Náhled změn ze STAG jmenuje konkrétní soubor.** Místo generického
  „nový soubor" ukáže, který **druh** STAG nabízí navíc (např. „nový soubor:
  Posudek oponenta").

## [0.73.0] - 2026-06-07

### Added
- **Náhled změn ze STAG před importem.** Proužek tiché kontroly má tlačítko
  **🔎 Zobrazit změny…**, které otevře rychlý přehled — *které* vedené práce
  a oponentury mají změnu a *které* nové práce STAG nabízí (jmenovitě), teprve
  odtud se přejde na Import. Konec hádání „26 nových".

### Fixed
- **Počet „nových prací" počítal i jmenovce.** Tichá kontrola nově páruje nové
  práce podle **celého jména** (křestní + příjmení), ne jen příjmení — práce
  jiných vedoucích/oponentů se stejným příjmením se už nezapočítají.
- **Čitelnost tlačítek v proužku STAG (dark theme).** Tlačítka *Zobrazit
  změny… / Zkontrolovat / ✕* měla světlý text na světlém pozadí; mají teď
  natvrdo tmavý text a viditelný rámeček.

## [0.72.0] - 2026-06-07

### Changed
- **„🗂 Přeřadit průběh obhajoby" nově dotahuje původní názvy ze STAG.** Při
  stažení se název souboru přejmenuje (`Příjmení_jine_datum.pdf`), takže
  přeřazení podle názvu nefungovalo. Nový dialog **znovu dotáhne seznam souborů
  ze STAG**, obnoví původní názvy, spáruje je s lokálními přílohami *Jiné*
  a v **náhledu s checkboxy** nabídne přeřazení (protokoly/zápisy obhajoby
  předzaškrtnuté; generické názvy zaškrtneš ručně). Se zálohou.
- **Nově stahované soubory ze STAG si pamatují původní název** (ukládá se do
  popisku přílohy) — Dokumenty tak ukazují skutečný název ze STAG a budoucí
  rozpoznání typu funguje spolehlivě.

## [0.71.2] - 2026-06-07

### Changed
- **Přejmenované záložky** pro srozumitelnost: *Aktuální* → **Aktuálně vedené
  práce**, *Budoucí* → **Práce v dalším akademickém roce R/R** (s konkrétním
  rokem), *🧐 Oponentské posudky* → **🧐 Oponované práce**.

## [0.71.1] - 2026-06-07

### Fixed
- **Čitelnost proužku tiché kontroly STAG v dark theme.** Proužek má vždy
  světlé pozadí, ale text dědil světlou barvu z tmavého motivu → nečitelný
  („Kontroluji změny…" apod.). Text je nově natvrdo tmavý.

## [0.71.0] - 2026-06-07

### Added
- **Nový typ přílohy „Soubor s průběhem obhajoby".** Protokol / zápis o
  průběhu obhajoby (SZZ). Při stahování ze STAG se rozpozná podle názvu
  (`obhajoba_…`, `…zapis_o_statni_zaverecne_…`, „protokol/záznam o obhajobě")
  a zařadí automaticky; je i v nabídce typů v náhledu souborů a v auto-detekci
  při ručním nahrání.
- **Toolbar „🗂 Přeřadit průběh obhajoby" (skupina Import).** Najde už stažené
  přílohy typu *Jiné*, které vypadají jako průběh obhajoby, ukáže **náhled**
  a po potvrzení je **přeřadí** na nový typ (se zálohou).

## [0.70.0] - 2026-06-07

### Added
- **Tichá kontrola STAG na pozadí.** Krátce po startu (a kdykoli ručně
  tlačítkem **🔄 Zkontrolovat** v proužku) aplikace na pozadí porovná aktuální
  rok se STAG a v **proužku nad záložkami** ukáže výsledek — i stav
  **„✓ vše aktuální"**, takže máš jistotu, že kontrola proběhla. Hlídá:
  - **změnu stavu / chybějící soubor** u vedených prací *V řešení*,
  - **změnu stavu / chybějící soubor** u oponentur aktuálního roku,
  - **nové práce ve STAG** (dle jména), které ještě nemáš v databázi.
  Při změnách svítí **odznak 🔄 na záložkách** *Aktuální* a *🧐 Oponentské
  posudky* a v proužku je tlačítko **Otevřít Import ze STAG…**. Offline kontrola
  tiše oznámí, že se nezdařila (data se nemění — kontrola je jen pro čtení).

## [0.69.3] - 2026-06-07

### Changed
- **Manažer odmítnutých zájemců seskupuje podle akademického roku.** Místo
  plochého seznamu jsou nyní práce sbalitelné skupiny *📅 rok (počet)*
  (roky sestupně, „bez roku" na konci).

## [0.69.2] - 2026-06-07

### Fixed
- **Tiché Qt hlášky v terminálu.** Odstraněn nevalidní `font-family:
  -apple-system` ze stylů Souhrnu (Qt ho nezná → varování + zdržení při
  startu); QTextBrowser teď dědí systémové písmo aplikace. Neškodné hlášky
  `qt.accessibility.table … out of bounds` (macOS VoiceOver se ptá stromů
  během přestavby) ztišeny cíleným pravidlem logování — ostatní Qt varování
  zůstávají.

## [0.69.1] - 2026-06-07

### Added
- **Tlačítko „🆕 Najít nové práce…" v dialogu *Aktualizovat … ze STAG*.**
  „Aktualizovat" jen osvěžuje práce, které už máš v DB — nové práce (např. pro
  nový akademický rok) se v něm neobjeví. Nové tlačítko otevře hromadné
  vyhledání *Moje vedené práce… / Moje oponentury…* (podle jména, s odznaky
  🆕 nové / ✓ už máš). Dialog navíc na tuto možnost upozorní, když není co
  aktualizovat, a v úvodu vysvětlí rozdíl.

## [0.69.0] - 2026-06-07

### Added
- **Tlačítko „🏷 Aktualizovat jen stavy"** v dialogu *Moje vedené práce /
  Moje oponentury* (vedle *📎 Stáhnout jen soubory*). U zaškrtnutých prací,
  které už máš v databázi, aktualizuje **jen stav** ze STAG — bez stahování
  souborů. Vedené práce: *Obhájeno / Neobhájeno / Nedokončeno / …*; oponentury:
  STAG stav práce. Stav se bere přímo z výsledku vyhledávání (žádné dotazy
  navíc). **Vyřeší i zpětné přeřazení** dříve naimportovaných prací
  *Nedokončeno → Neobhájeno*. Na konci ukáže přehled změn.

## [0.68.0] - 2026-06-07

### Added
- **Nový stav „Neobhájeno"** (neúspěšná obhajoba) odlišený od „Nedokončeno"
  (práce nikdy nedotažená k obhajobě). Vlastní barva a badge, vlastní
  **checkbox v Historii** (defaultně zaškrtnutý). Ze STAG se naplní
  automaticky: *DBUO* / *OPUNO* → **Neobhájeno**, *ND* → **Nedokončeno**.
  Statistika *Úspěšnost obhajob* rozlišuje Obhájeno / Neobhájeno / Nedokončeno.

### Changed
- **Přechody stavů** rozšířeny: *V řešení* → *Neobhájeno*; druhý pokus
  obhajoby i z *Neobhájeno* (→ *V řešení* / *Obhájeno*); mezi *Nedokončeno*
  a *Neobhájeno* lze přepnout (oprava klasifikace).

### Migrace
- Existující práce ve stavu *Nedokončeno* se **nepřeřadí automaticky** —
  u vedených prací se dřív surový STAG kód neukládal, takže nelze zpětně
  rozlišit neúspěšnou obhajobu od nedotažené práce. Oprav je buď **ručně**
  (*Přechod do stavu*), nebo **znovu naimportuj ze STAG** (stav se dorovná).

## [0.67.4] - 2026-06-07

### Removed
- **Vývojový skript `tools/bench_stag_downloads.py`.** Posloužil ke kalibraci
  timeoutů stahování (viz 0.67.1) a dál není potřeba. Nastavení timeoutů
  v `services/stag_api.py` zůstává.

## [0.67.3] - 2026-06-07

### Changed
- **Souhrn historické práce už neukazuje „Odeslání posudku".** U prací ve
  stavu *Obhájeno* / *Nedokončeno* je odeslání posudku sekretářce irelevantní,
  takže se sekce v Souhrnu vůbec nezobrazí — i kdyby práce dříve byla
  „V řešení".

## [0.67.2] - 2026-06-07

### Changed
- **Sloupec známek „V/O" i v záložce „Oponentské posudky".** Použije stejnou
  vizualizaci jako vedené práce — barevně podbarvená dvojice písmen
  (vedoucí / oponent) místo dřívějšího textu „V: A / O: B".

## [0.67.1] - 2026-06-07

### Changed
- **Timeout stahování doladěn podle reálného benchmarku** (≈585 souborů celé
  knihovny). Model `base + 1,2 s/MB` (strop 30 min) dává i u největší
  948MB přílohy ~3× rezervu; fallback pro neznámou velikost zvýšen na 900 s.
- **Při timeoutu aplikace poradí ruční cestu.** Hláška nově vždy uvádí, že
  *„Soubor jde vždy stáhnout ze STAGu ručně a přidat k práci v sekci
  Dokumenty."* — platí všude, kde se soubory stahují (Kontrola se STAG,
  hromadné stažení, Aktualizovat…, Stáhnout jen soubory).

## [0.67.0] - 2026-06-07

### Added
- **Filtry nad záložkou „Historie" — podle oponenta a podle známky.** Vedle
  checkboxů stavů přibyla dvě rozbalovací menu: **Oponent** (seznam oponentů
  vyskytujících se v historii + *Všichni*) a **Známka** (A–F/FX + *Všechny*).
  Filtr známky propustí práci, když vybrané známce odpovídá **vedoucí NEBO
  oponent**. Filtry se kombinují se zaškrtnutými stavy.

### Changed
- **Hezčí sloupec známek „V/O".** Hlavička je nově **„V/O"** (vlevo známka
  vedoucího, vpravo oponenta) a obsah tvoří **barevně podbarvená dvojice
  písmen** (zelená A → červená F/FX) místo dřívějšího textu „V: A / O: B".
  Platí ve všech záložkách.
- **Záložka „Historie" skrývá nepotřebné sloupce.** U hotových prací jsou
  indikace **„Posudky"** a **„Odesláno"** irelevantní, takže se v Historii
  vůbec nezobrazují (v ostatních záložkách zůstávají).

## [0.66.1] - 2026-06-07

### Fixed
- **Dev benchmark `tools/bench_stag_downloads.py` četl špatnou databázi.**
  Defaultoval na `~/.bpdpmanager/db.json` (kde u profilové instalace nejsou
  data → „Prací s STAG ID: 0"). Nově bere **db.json naposledy otevřeného
  profilu** (stejná data jako v aplikaci). Přidán přepínač `--list-profiles`
  pro výpis profilů a cest k jejich `db.json`.

## [0.66.0] - 2026-06-07

### Added
- **Filtr stavů v záložce „Historie".** Nad seznamem přibyly checkboxy
  *Obhájeno* a *Nedokončeno* — defaultně obě zaškrtnuté. Odškrtnutím lze
  zobrazit jen jeden stav. **Nastavení se pamatuje i po zavření aplikace.**
- **Vyčtení navržené známky i z posudků ve Wordu (`.doc` / `.docx`).** Dosud
  uměla aplikace přečíst navrženou známku jen z PDF; nově zpracuje i wordové
  posudky (vedoucího i oponenta) — `.docx` čte přímo, starý binární `.doc`
  převede na pozadí přes LibreOffice. Funguje všude, kde se známky doplňují
  (nahrání posudku, *Kontrola se STAG*, zpětné dosynchronizování).

### Changed
- **Rozšířené rozpoznávání navržené známky** o formulaci typu *„doporučuji
  k obhajobě s hodnocením B"* (vedle dosavadních *„navrhuji hodnocení…"*,
  *„hodnotit stupněm…"* apod.).

## [0.65.0] - 2026-06-07

### Changed
- **Flexibilní timeout stahování podle velikosti přílohy.** Místo pevného
  limitu se timeout odvozuje z velikosti souboru (větší příloha = víc času,
  malá selže rychleji, když opravdu visí): zhruba *120 s + 1 s/MB*, strop
  30 min, u neznámé velikosti velkorysý fallback.
- **Jednotná indikace timeoutu při stahování příloh.** Když stahování spadne
  na timeout, ukáže se to **srozumitelně a všude**, kde se soubory stahují —
  v *Kontrole se STAG* přímo v řádku souboru (*„✗ … — STAG neodpověděl
  včas…"*), i ve výpisu chyb u hromadného stažení, *Aktualizovat …* a
  *Stáhnout jen soubory*. *Aktualizovat …* nově stahuje stejným (delším)
  způsobem jako ostatní místa.

### Added
- **Dev nástroj `tools/bench_stag_downloads.py`** — nanečisto stáhne soubory
  prací ze STAG do dočasné složky, změří časy (TTFB, průtok) a **hned smaže**;
  z naměřeného navrhne timeout. Databázi pouze čte (neovlivní ji).

### Fixed
- **Velké / ZIP přílohy ze STAG se nedařilo stáhnout** (hláška „Nepodařilo se
  spojit se STAG"). STAG velké přílohy a ZIP balíčky **generuje až na
  vyžádání**, takže než začne posílat data, trvá to i desítky sekund až minuty
  — krátký 30s timeout je shazoval, i když připojení fungovalo. Timeout pro
  **stahování souborů** je teď výrazně delší (10 min) a při jeho překročení se
  ukáže srozumitelná hláška místo „zkontroluj připojení".

### Changed
- Během čekání na server se v průběhu stahování ukazuje **„⏳ STAG připravuje
  soubor (čekám)…"** — než dorazí první data, příprava velkého souboru na
  serveru může chvíli trvat (stejně jako v prohlížeči).

### Changed
- **Kontrola se STAG: průběh stahování přímo v seznamu.** Při dostahování se
  u každého souboru ukazuje **průběh** (⏳ staženo/celkem MB) přímo v jeho
  řádku a po dokončení se označí **✓ staženo** (nebo **✗ chyba**); UI nezamrzá.
- **Oponentské posudky: starší roky sbalené.** Ve stromu seskupeném dle
  akademického roku je defaultně rozbalený **jen aktuální rok**, starší roky
  jsou sbalené.

### Added
- **Kontrola se STAG umí chybějící soubory rovnou dostáhnout.** V dialogu
  *🔍 Kontrola se STAG* jsou chybějící soubory předzaškrtnuté a tlačítkem
  **⬇ Dostáhnout vybrané** je stáhneš a připojíš k práci (před zápisem záloha).

### Changed
- **Kontrola se STAG přeskakuje budoucí práce.** Zájemci a vypsaná témata se
  neověřují (ve STAG ještě soubory nemají).
- **Aktualizace oponentur doplní STAG stav.** *🔄 Aktualizovat práce
  k oponování ze STAG* nově doplní STAG stav práce (sloupec *Stav*) i u dříve
  stažených oponentur, které ho ještě neměly.

### Fixed
- **Známka oponenta se u stažených oponentur nedoplnila.** Doplnění známky
  oponenta bralo hodnotu jen z *napsaného* posudku, ne ze **staženého PDF**
  posudku oponenta. Nově se u oponentur bez známky **vyčte i z nahraného PDF**
  posudku oponenta (jako u posudku vedoucího). U existujících oponentur se
  doplní automaticky při otevření záložky *Oponentské posudky*.

### Added
- **Sloupec „Stav" v oponenturách.** Tabulka oponentur ukazuje stav práce ze
  STAG (např. *nedokončeno* / *obhájeno*) — užitečné hlavně u nedokončených.
  Stav se ukládá při importu ze STAG (`stag_state_code`); u dříve stažených
  oponentur ho doplníš opětovným stažením přes *🧐 Moje oponentury…*.

### Changed
- **Indikace posudků jen pro aktuální akademický rok.** V seznamu oponentur
  se barevný puntík stavu posudku, podbarvení i sloupec *Odesláno* zobrazují
  **jen u aktuálního roku** (u starších let jsou irelevantní). Souhrn
  *hotovo / chybí* dole se počítá také za aktuální rok.

### Changed
- **Úvodní průvodce doporučí prvotní stažení prací ze STAG.** Po nastavení
  jména a oborů průvodce (i sekce *Začínáme* v nápovědě) navádí jako první
  krok na **📥 Import ze STAG → 🎓 Moje vedené práce… / 🧐 Moje oponentury…**
  — databáze se naplní během chvíle (u velkého objemu příloh stačí *„Jen
  data"*).

### Added
- **Sloupec „Známky" v seznamu vedených prací.** Ve všech záložkách s pracemi
  (*Aktuální / Budoucí / Historie / Vše*) je nový sloupec **Známky** (před
  *Posudky*) se známkou **vedoucího i oponenta** (`V: A / O: B`, „—" když
  chybí; plný popis v tooltipu). Záložka *Oponentské posudky* známky ve sloupci
  už měla.

### Added
- **Statistiky: přehled souborů.** Nová sekce **Soubory (přílohy)** — kolik
  máš celkem souborů a kolik zabírají, rozpad **podle druhu dokumentu**
  (text práce / přílohy / posudky / …) a **největší práce** podle objemu
  (top 10). Počítá se z reálných souborů na disku (vč. starších verzí).

## [0.60.0] - 2026-06-06

### Added
- **Statistiky: známky oponentů + souhrn oponentur.** Sekce známek obhájených
  prací nově ukazuje vedle známek **vedoucího** i známky **oponenta**. Přibyla
  sekce **Oponentury** — počet posudků, rozpad BP/DP, po letech a **mnou
  navržené známky** (jako oponent).

### Fixed
- **Čitelnost Statistik na tmavém motivu.** Šedý text na tmavém pozadí byl
  špatně čitelný — barvy se teď přizpůsobí světlému/tmavému motivu.
- **Tišší terminál.** Potlačena neškodná opakovaná hlášení `pypdf`
  („Ignoring wrong pointing object …") při čtení některých PDF posudků.

### Added
- **🔍 Kontrola se STAG (toolbar).** Nové tlačítko v liště *Import* — read-only
  audit: projde práce (vedené i oponentury) s STAG ID, porovná se STAG a vypíše,
  u kterých **STAG nabízí dokument** (plný text / příloha / posudek), který
  **v databázi chybí**. Práce bez STAG ID i chyby dotazu vypíše zvlášť. Nic
  nestahuje — soubory dohraješ přes *Import ze STAG → 🔄 Aktualizovat …*.

### Changed
- **Stahování příloh ze STAG: poctivější průběh.** Než STAG začne posílat
  data (server soubor generuje / přiškrtí), ukazuje progres **„⏳ připojuji
  k STAG…"** místo zavádějícího `0 B`. Při **přechodném selhání** se stažení
  souboru **jednou zopakuje** (2. pokus), ať se kvůli krátkému výpadku
  zbytečně nepřeskočí.

### Fixed
- **Pád při stahování velkého objemu příloh ze STAG (`OverflowError`).** Když
  celková velikost příloh napříč vybranými pracemi přesáhla ~2 GB, progres
  okno přeteklo 32-bitový rozsah a aplikace spadla hned po „Stáhnout i tak".
  Průběh stahování se nově **škáluje** (promile), takže funguje pro libovolný
  objem.

### Added
- **U velkého objemu příloh (nad ~300 MB) nabídka „jen data".** Před stažením
  se zobrazí celková velikost a počet souborů a můžeš zvolit **stáhnout
  přílohy**, **naimportovat jen data prací (bez příloh)**, nebo **zrušit** —
  ať se omylem netáhnou gigabajty (typicky u hromadného stažení mnoha prací).

### Fixed
- **Aplikace už při stahování příloh ze STAG nezamrzá.** Stahování souborů
  běželo na hlavním (UI) vlákně, takže když STAG odpovídal pomalu (server
  generuje PDF / přiškrtí spojení), aplikace „zamrzla" i u malé přílohy
  (např. posudku). Stahování teď běží na **pracovním vlákně**, UI jen
  překresluje průběh — okno zůstává živé a **Přerušit** funguje i během
  pomalé odpovědi.

### Added
- **Nabídka vyčištění dočasných souborů před stahováním.** Pokud po
  přerušeném stahování (nebo pádu aplikace) zůstanou ve složce dočasných
  souborů zbytky ze STAG, aplikace je **před dalším stahováním** vypíše
  (počet + velikost) a nabídne smazání.

### Changed
- **Plynulý průběh stahování příloh ze STAG.** Soubory se nově stahují
  **po blocích** a progres okno ukazuje **kolik z kolika MB** se u dané
  přílohy stáhlo (`3.2 / 14.0 MB`). U velkých příloh už to nevypadá, že
  aplikace zamrzla.

### Fixed
- **Úklid dočasných souborů po přerušení.** Když stahování **přerušíš**,
  všechny dočasně stažené soubory (CSV i přílohy) se **smažou** a operace
  se korektně ukončí (nepokračuje se do náhledu).
- **Nestažené přílohy se vypíšou.** Pokud se nějakou přílohu nepodaří
  stáhnout, aplikace to **oznámí** (dřív se tiše přeskočila, což budilo
  dojem, že stahování skončilo předčasně).

### Added
- **Nová záložka „💡 Návrhy témat".** Seznam vymyšlených potenciálních témat
  (BP/DP) — nekompletní nápady **bez studenta a bez stavu**. U každého návrhu:
  **název, popis, body zadání, literatura, obor a typ (BP/DP)**; akademický rok
  je tu irelevantní. Volitelně lze označit **🔒 Zarezervováno** a komu (volný
  text). Záložka má **seznam** (seskupený BP/DP) a **detail** se **Souhrnem**
  (tlačítka 📋 do schránky jako u ostatních záložek) a editorem. Tlačítko
  **🎓 Převést na vedenou práci** z návrhu založí skutečnou práci (přenese
  název, popis, body, literaturu a typ; stav *Zájemce s tématem*, aktuální
  akademický rok) a návrh odebere. Záložka je vložená **za „Oponentské
  posudky"**.

### Changed
- Schéma úložiště povýšeno na **v12** (`Database.proposals`). Starší databáze
  se načtou beze změny (chybějící pole se doplní jako prázdný seznam).

### Fixed
- **Nový obor v importu ze STAG se hned propíše do dalších řádků.** Při importu
  více prací se stejným **nenamapovaným** oborem se nově založený obor („➕ Nový
  obor…") okamžitě nabídne i v ostatních řádcích a u všech řádků **se stejným
  STAG kódem** se rovnou předvybere — nemusíš ho zakládat znovu. (Dřív se nový
  obor objevil jen v tom jednom řádku; opětovné založení stejného oboru by ho
  jen přepsalo, ne zdvojilo, ale bylo to matoucí.) Ručně zvolené obory v jiných
  řádcích zůstávají beze změny.

## [0.57.0] - 2026-06-06

### Added
- **Aktualizace už evidovaných prací ze STAG.** Dvě nová tlačítka v dialogu
  *Import ze STAG…*:
  - **🔄 Aktualizovat práce v řešení ze STAG** — projde vedené práce ve stavu
    *V řešení*, dohledá je ve STAG (podle STAG ID, jinak dle příjmení studenta)
    a nabídne **změnu stavu** (např. *V řešení → Obhájeno*, k potvrzení) a
    **dohrání chybějících souborů** (předzaškrtne soubory, jejichž *druh* u
    práce ještě není — typicky nový posudek nebo odevzdaná práce).
  - **🔄 Aktualizovat práce k oponování ze STAG** — totéž pro oponentury
    **aktuálního akademického roku** (jen soubory; oponentury stav nemají).

  Vše proběhne s **progres oknem**, přehledem změn k zaškrtnutí, **zálohou**
  před zápisem a tlačítkem **„↩ Vrátit vše"**. Práce bez STAG ID, které se
  nepodaří dohledat dle příjmení, se přeskočí a vypíšou.

## [0.56.1] - 2026-06-06

### Fixed
- **Šířka okna hromadného stažení ze STAG dle obsahu.** Sloupec „Práce" se
  zastropoval (dlouhé názvy se zkrátí, celé jsou v tooltipu) a okno se po
  načtení **roztáhne tak, aby se vešly všechny sloupce** (až do šířky
  obrazovky) — už není potřeba vodorovně rolovat.

### Docs
- Nápověda nově popisuje **merge při opětovném stažení prací „✓ už máš"**
  (párování přes STAG ID, slučování polí, zachování stavu, zálohu a vrácení).

### Added
- **Počet a velikost příloh v tabulce (lazy).** Nový sloupec **„📎 Přílohy"** se
  u práce vyplní, jakmile ji **zaškrtneš** — dotáhne počet souborů a jejich
  celkovou velikost z detailu práce (např. „📎 4 · 14.0 MB"). Načítá se jen pro
  zaškrtnuté práce (ne pro všechny nalezené), takže tabulka zůstává rychlá.
  Velké přílohy se i nadále vylučují ve **výběru souborů v náhledu** před
  importem (a varování u velkých příloh).

## [0.55.2] - 2026-06-06

### Fixed
- **Hromadné stažení ze STAG padalo, když měla práce velkou přílohu.** Dialog
  s varováním o velkých přílohách volal neexistující metodu (`_cs_plural`) a
  import se po dotočení kolečka tiše zastavil — práce se nikdy nedostala do
  okna „Import dat ze STAG (CSV)". Opraveno; import nyní doběhne do náhledu
  souborů a předá práce k dokončení tlačítkem **Provést import**.

### Added
- **Vizualizace průběhu stahování ze STAG.** Místo neurčitého kolečka je teď
  **progress okno** ukazující, která práce se zpracovává (CSV + seznam příloh)
  a poté **stahování jednotlivých příloh** po jedné (student → název přílohy +
  velikost), s možností **přerušit**.

## [0.55.1] - 2026-06-06

### Fixed
- **Nápověda se zavírala při hledání.** Stisk Enter ve vyhledávacím poli
  nápovědy spouštěl tlačítko „Zavřít" (výchozí) a okno se zavřelo. Nově je
  výchozí tlačítko „Další" — Enter hledá dál, okno zůstane otevřené.
- **Dialog hromadného stažení ze STAG: sloupec „Práce" dle obsahu.** Sloupec
  s názvem práce se už neořezává na šířku okna, ale roztáhne se podle nejdelšího
  názvu (a lze ho ručně doladit). Dialog je výrazně širší a o ~50 % vyšší, ať
  se dlouhé názvy i všechny sloupce vejdou.

### Added
- **Hromadné stažení ze STAG: tabulka s rokem, obhajobou, oponentem a stavem.**
  Seznam nalezených prací je teď přehledná tabulka se sloupci **Práce · Typ ·
  Akademický rok · Obhajoba · Oponent · Stav**. Datum obhajoby se bere z tabulky
  výsledků STAG; **akademický rok a obor** (které tabulka výsledků neobsahuje)
  se po vyhledání **automaticky dotáhnou z detailu každé práce** — s progress
  oknem a možností přerušit. Akademický rok je tak vidět **i u nedokončených
  prací** (odvozuje se z data zadání).
- **Seskupení nalezených prací.** Nový výběr **„Seskupit podle"** — Stav práce
  / Typ (BP/DP) / Obor / Akademický rok / Žádné. Hlavička skupiny lze
  zaškrtnout/odškrtnout naráz (hromadný výběr celé skupiny).

### Changed
- Dialog hromadného stažení používá místo prostého seznamu **stromovou tabulku**
  s odznakem 🆕 nové / ✓ už máš a tooltipem (STAG ID, stav, rok, obor, vedoucí,
  oponent).

## [0.54.0] - 2026-06-06

### Fixed
- **STAG stránkování — načtou se všechny vedené/oponované práce.** STAG
  ve výsledcích vyhledávání implicitně **stránkuje** (vrací jen první stránku,
  ~20 záznamů), takže se část prací do hromadného stažení vůbec nedostala.
  Nově aplikace automaticky následuje odkaz **„Vypnout stránkování"** a načte
  kompletní seznam (u testovacího vedoucího 31 → 116 prací). Platí pro vedené
  i oponované práce.

### Added
- **Stav práce ze STAG v seznamu výsledků.** U každé práce se vedle roku
  zobrazí i stav (obhájeno / čeká na obhajobu / nedokončeno / neúsp. obhajoba)
  vyčtený přímo z tabulky výsledků STAG (kódy DUO / DBPOO / ND / OPUNO…).
  Plný popis stavu je v tooltipu položky.

## [0.53.1] - 2026-06-06

### Changed
- **Dialog stahování ze STAG je větší** (vyšší o ~70 %, širší) a v seznamu
  výsledků je teď **akademický rok napřed** — přehlednější u hromadného
  stažení mnoha prací.

## [0.53.0] - 2026-06-06

### Added
- **Ruční záloha kdykoliv.** Nová položka **👤 → 💾 Zálohovat teď** vytvoří
  zálohu aktuálního stavu databáze jedním klikem. Stejné tlačítko je i v
  manažeru záloh (**👤 → 💾 Zálohy**), který už uměl seznam, obnovu a mazání.

## [0.52.0] - 2026-06-06

### Added
- **Záchranná brzda pro import ze STAG.** Po dokončení importu nabízí souhrnné
  okno tlačítko **↩ Vrátit celý import zpět** — obnoví databázi ze zálohy
  pořízené těsně před importem (`before-stag-import`). Importovaný stav se
  předtím ještě zazálohuje (`before-restore`), takže i vrácení jde vrátit.
  Vhodné zejména u velkých hromadných importů.

## [0.51.0] - 2026-06-06

### Fixed
- **Repetent — ochrana proti přepsání v DB.** Když má student dvě práce
  stejného typu/roku, ale s **jiným STAG ID** (řádný + opravný pokus), import
  je už **nikdy nespojí ani nepřepíše** — zůstanou jako dva samostatné záznamy
  (každý se svým posudkem a soubory). Doplněn STAG kód **OPUNO** (ukončeno po
  neúspěšné obhajobě → Nedokončeno).

### Added
- **Automatická vazba repetentů.** Po importu se řádný a opravný pokus
  (stejný student + typ, jeden *Obhájeno* + jeden *Nedokončeno*; u oponentur
  dvojice stejného studenta) **automaticky propojí**. V seznamu i Souhrnu je
  označí **🔁**; ve Statistikách přibyl počet opravných pokusů. (Pole
  `related_thesis_id`, schéma v11.)

## [0.50.1] - 2026-06-06

### Changed
- **Hromadné stažení ze STAG má zamčenou roli.** „Moje vedené práce" a „Moje
  oponentury" otevřou dialog **bez přepínače Vedoucí/Oponent** (každé tlačítko
  = jedna role) — odstraněn matoucí mix.

## [0.50.0] - 2026-06-06

### Added
- **Hromadný import všech mých prací ze STAG.** V dialogu *Import ze STAG* jsou
  nová tlačítka **🎓 Moje vedené práce…** a **🧐 Moje oponentury…** — najdou
  podle jména z profilu všechny práce dané role (historické, aktuální i vypsané)
  seřazené dle akademického roku, vybereš co naimportovat.
- **Filtr dle celého jména** („past" se jmenovci): protože ze samotného
  příjmení může být víc vedoucích (Petr vs Pavel Žáček), výsledky se filtrují
  na práce s **celým jménem** uživatele (diakritika-necitlivě). Filtr lze vypnout.

## [0.49.0] - 2026-06-06

### Added
- **Tisk dokumentu** — kontextová akce **🖨 Tisk** u souborů PDF a XLSX
  (pravý klik na dokument). PDF jde rovnou na výchozí tiskárnu (CUPS / Windows
  print), XLSX se otevře v aplikaci k ručnímu tisku.

## [0.48.1] - 2026-06-06

### Changed
- **Sjednocená indikace odeslání posudku** v seznamu prací — místo dosavadní
  odlišné značky u *Aktuální* a *Oponentských posudků* je nově jednotný
  **sloupec „Odesláno"** v obou seznamech (✉ ✓ odesláno / ✉ ✗ neodesláno).

## [0.48.0] - 2026-06-06

### Changed
- **Dialog „🌱 Zájemce" doladěn.** Studenta lze rovnou založit tlačítkem
  **+ Nový** (vč. oboru). Pole **Obor je vždy editovatelné** (nepovinné, není
  podmíněné výběrem studenta) — při výběru studenta se předvyplní jeho oborem.

## [0.47.0] - 2026-06-06

### Added
- **Ruční označení posudku za odeslaný sekretářce.** Pravý klik na práci
  *V řešení* s hotovým posudkem (i na oponentský posudek) → *✉ Označit posudek
  za odeslaný sekretářce* (a zpět). Doplňuje automatické označení při odeslání
  e-mailem.
- **Indikátor odeslání v seznamu** *Aktuální* i *Oponentské posudky*: u prací
  s hotovým posudkem **✉✓ odesláno** / **✉✗ neodesláno** (s tooltipem).

## [0.46.0] - 2026-06-06

### Added
- **Evidence odmítnutých zájemců o vedení** (toolbar **🚫 Odmítnutí**): jméno,
  obor, akademický rok. Souvisí s kapacitou vedení a promítá se do statistik.
  (Schéma v10 — `Database.rejected_students`.)
- **Statistiky rozšířeny:** sekce **Kapacita vedení** (vedených z max. 15 +
  odmítnutí po letech), **Vývoj počtu vedených prací po letech** (graf),
  **Odměny (orientačně)** — vedení 3 000 Kč/obhájenou práci (max 12/rok),
  oponentury 600 Kč/posudek, s ročními i celkovými součty. KPI karta
  *Odmítnutí*.

## [0.45.0] - 2026-06-06

### Added
- **Export / import jedné práce jako ZIP balík.** Pravý klik na práci →
  *📦 Exportovat práci do ZIP* uloží kompletní balík (data, stav, posudky,
  známky, soubory + navázaný student / oponent / obor). Toolbar **📦 Import
  práce ze ZIP…** ho naimportuje jako novou práci (obnoví entity i soubory).
  Vhodné pro přesun jedné práce mezi profily/zařízeními.

## [0.44.0] - 2026-06-06

### Added
- **Hromadné vyhledání ze STAG dle vedoucího/oponenta.** V dialogu
  *🌐 Stáhnout ze STAG* lze nechat příjmení studenta prázdné a zadat jen
  vedoucího/oponenta — STAG vrátí **všechny jeho práce** (historické
  i aktuální), které pak naimportuješ víc najednou (multi-výběr).

## [0.43.0] - 2026-06-06

### Added
- **Hromadné akce nad soubory.** V seznamu dokumentů lze označit více souborů
  (Cmd/Ctrl/Shift) a přes pravý klik je **hromadně exportovat** do zvolené
  složky nebo **odeslat jedním e-mailem** (všechny jako přílohy). Dialog
  odeslání souboru nově umí více příloh.

## [0.42.1] - 2026-06-06

### Fixed
- **Kumulace „_archiv_" v názvech archivních posudků.** Při generování nového
  posudku se archivní přípona připisovala i už dříve archivovaným souborům,
  takže se `_archiv_<ts>` zanořovalo (`…_archiv_…_archiv_…`). Nově se
  archivují jen soubory, které ještě nejsou v `archiv/`. Při startu navíc
  proběhne **jednorázová oprava názvů** existujících archivů (sloučí zanořené
  segmenty; idempotentní).

## [0.42.0] - 2026-06-06

### Changed
- **„Obory" → „Obory + sekretářky".** Toolbarové tlačítko i manažer se
  přejmenovaly. Manažer (už dřív seskupený podle sekretářky) má nově sloupec
  **Oslovení** a **dvojklik na hlavičku sekretářky** otevře **hromadnou úpravu**
  jejího kontaktu i oslovení **pro všechny obory dané sekretářky** najednou
  (dvojklik na obor upravuje jen ten obor).

## [0.41.0] - 2026-06-06

### Added
- **Záložka 📊 Statistiky** (za Harmonogramem) — souhrnný přehled napříč
  budoucími, aktuálními i historickými pracemi: KPI karty (vedené / V řešení /
  budoucí / historie / oponentury / studenti), rozpady podle stavu, BP vs DP,
  akademického roku, oboru, úspěšnost obhajob, rozložení známek a přehled
  posudků (hotové / chybí / odesláno). Přepočítá se při otevření i tlačítkem.

## [0.40.0] - 2026-06-06

### Changed
- **Tlačítko „🌱 Zájemce" otevře dialog nové budoucí práce.** Lze rovnou
  (volitelně) vyplnit **studenta, obor, název a anotaci** — nic není povinné,
  co nevyplníš zůstane prázdné. Stav je defaultně **Vypsané téma** (lze změnit).
  Obor se uloží ke zvolenému studentovi. (Dřív přidalo rovnou prázdného
  „zájemce bez tématu".)

## [0.39.0] - 2026-06-06

### Added
- **Kontextové akce nad soubory** (pravý klik na dokument): **📋 Kopírovat
  soubor** do schránky (samotný soubor, ne cestu — vložíš do Finderu/mailu),
  **💾 Exportovat na disk…** (kopie na zvolené místo) a **✉ Odeslat mailem…**
  (soubor jako příloha — volba příjemce, předmětu a textu; odesílá z e-mailu
  uživatele přes SMTP s dotazem na heslo, fallback přes .eml).
- **Indikace odeslání posudku** v seznamu prací i v Souhrnu — značka **✉**
  u odeslaných a v Souhrnu sekce *Odeslání posudku* (✓ s datem / ✗ neodesláno).
  Platí pro posudky vedoucího i oponentské.

### Changed
- **Stav posudku jako barevný puntík v názvu práce** (🟢🟡🔴) — viditelný
  i u vybraného řádku (výběr dřív barevné pozadí překryl). Platí pro vedené
  i oponentské.

## [0.38.0] - 2026-06-06

### Added
- **Editace oboru přímo u práce.** V záložce *📝 Téma zadání* (vedené práce) je
  nový **rozbalovací seznam Obor** (evidované obory z manažeru) — uloží se ke
  studentovi. U **oponentur** je obor nově také rozbalovací seznam evidovaných
  oborů. Cíl: aby obor seděl na sekretářku při odesílání posudků a nevznikal
  konflikt kódů oborů. Ručně zadaná / importovaná hodnota zůstane zachovaná.

### Changed
- **Vybraný řádek v seznamu prací už nepřekryje barevný stav.** Výběr je nově
  poloprůhledný + tučný, takže ve sloupci *Téma* zůstane vidět barevné pozadí
  stavu posudku (🟢🟡🔴).

### Fixed
- **Příčina nenabízených oponentských posudků.** Práce vznikla nad oborem,
  který po synchronizaci výchozích oborů přestal odpovídat evidovaným kódům —
  proto se nepárovala na sekretářku. Combobox oboru tomu předchází; navíc lze
  použít přepínač *Zobrazit i práce z jiných oborů* (z 0.37.0).

## [0.37.0] - 2026-06-06

### Added
- **Oslovení sekretářky v e-mailu** — nové pole u oboru (manažer oborů →
  Sekretářka → *Oslovení v mailu*, např. „Vážená paní Nováková"). Použije se
  v textu odesílaných posudků; prázdné = formální výchozí oslovení.
  (Schéma v9 — `Obor.secretary_greeting`.)
- **Zobrazit i práce z jiných oborů** — přepínač v dialogu odesílání posudků.
  Když obor práce nesedí na žádný obor sekretářky (časté u oponentur s odlišným
  kódem oboru), normálně se nenabídne; po zapnutí se ukážou všechny připravené
  posudky (s červeně označeným oborem) a vybereš ručně. Pod tabulkou je navíc
  počet skrytých prací s nesouhlasícím oborem.

### Changed
- Dialog odesílání má nový sloupec **Obor**, ať je vidět, proč se práce páruje
  (či nepáruje) na sekretářku.

## [0.36.4] - 2026-06-06

### Fixed
- **K odeslání se nabízejí jen aktuální vedené práce („V řešení").** Práce
  z Historie (obhájeno / nedokončeno) už se v dialogu odesílání posudků
  vedoucího neobjeví. (Oponentury stav nemají, odesílají se beze změny.)

### Added
- **Volitelný popisek o aplikaci v patičce e-mailu** — zaškrtávátko *Připojit
  popisek o aplikaci (BPDPManager)* přidá řádek „Odesláno s podporou aplikace
  BPDPManager" + odkaz na GitHub. Default vypnuto, projeví se v náhledu textu.

## [0.36.3] - 2026-06-06

### Fixed
- **Oponentské posudky šly teď opravdu odeslat.** Dialog je dříve nenašel,
  protože `student_obor` u oponentur bývá STAG kód (např. „NSWI-K"), ale
  párovalo se jen proti názvu oboru. Nově se obor práce matchuje proti
  **názvu i STAG kódu** oboru sekretářky (case-insensitive).

### Changed
- **Sjednocené odesílání posudků.** Toolbarové tlačítko **✉ Odeslat posudky**
  je teď rozbalovací s volbou *Posudky vedoucího (vedené práce)* /
  *Oponentské posudky* (dřív poslalo rovnou jen vedoucího). Přímé tlačítko
  v záložce *Oponentské posudky* zůstává.
- **Předmět e-mailu přes celou šířku** dialogu (popisek vlevo nad polem).

## [0.36.2] - 2026-06-06

### Added
- **Testovací odeslání posudků (dry run).** V dialogu odesílání nové tlačítko
  **🧪 Test — poslat jen sobě**: pošle stejný e-mail včetně PDF příloh jen na
  vlastní e-mail (předmět „[TEST] …", v těle upozornění s ostrým příjemcem).
  Posudky **neoznačí** jako odeslané a dialog nechá otevřený — pro kontrolu,
  než se pošle sekretářce.

## [0.36.1] - 2026-06-05

### Changed
- **Verze aplikace v titulku okna** — např. „BPDPManager 0.36.1 — Profil".

## [0.36.0] - 2026-06-05

### Added
- **Odesílání posudků e-mailem sekretářce.** Nové tlačítko **✉ Odeslat
  posudky** (vedené práce, toolbar) a **✉ Odeslat sekretářce…** (záložka
  *Oponentské posudky*). Dialog: výběr sekretářky → podle jejích oborů se
  nabídnou práce s **hotovým PDF posudku** (nezaslané předzaškrtnuté, už
  odeslané volitelně), editovatelný **náhled** předmětu a textu (pozdrav +
  seznam prací seskupený na BP/DP: jméno, osobní číslo, název), **kopie sobě**
  (default zapnuto). Odeslání připojí **PDF posudky poslední verze** a označí
  práce jako odeslané (pole `supervisor_review_sent_at` /
  `opponent_review_sent_at`, schéma v8).
- **Samostatný správce e-mailu (SMTP)** — **👤 → ✉ Nastavení e-mailu (SMTP)**:
  e-mail odesílatele, server/port/zabezpečení a **🔌 Test spojení**. Výchozí
  hodnoty pro **UTB Office365** (outlook.office365.com:587, STARTTLS).
  **Heslo se nikde neukládá** — zadává se při každém odeslání i testu.
- **Fallback přes mailového klienta.** Když přímé odeslání přes SMTP selže
  (UTB Office365 vyžaduje OAuth2, Basic Auth bývá vypnutý), aplikace nabídne
  vytvořit hotový e-mail **.eml** s přílohami a otevřít ho v Outlooku/
  Thunderbirdu, kde stačí kliknout Odeslat.
- **E-mail uživatele v profilu** (👤 → Správa profilů → ✉ E-mail…).
- **Sekce „Soubory" v souhrnu vedené práce** — přehled aktuálních příloh
  (text práce, posudky, přílohy…) u aktuálních i historických prací.

## [0.35.0] - 2026-06-05

### Added
- **Varování u velkých příloh ze STAG.** Než se stáhnou soubory práce,
  aplikace přečte jejich velikost z výpisu STAG a u velkých (nad ~25 MB —
  typicky objemný plný text či přílohy) se **zeptá**: *⬇ Stáhnout i tak*,
  nebo *Přeskočit velké* (ostatní se stáhnou normálně). Platí pro
  *Stáhnout vybrané* i *Stáhnout jen soubory*.

## [0.34.0] - 2026-06-05

### Added
- **Známky z PDF posudků i u vedených prací.** Sekce *Známky* v souhrnu vedené
  práce nově zobrazí navrženou známku i tehdy, když posudek existuje jen jako
  nahrané PDF (historické práce) — známka se z PDF vyčte. In-app posudek má
  přednost, ručně zadanou známku to nikdy nepřepíše. Doplnění probíhá
  automaticky při otevření práce i po stažení posudku ze STAG (nová pole
  `grade_supervisor` / `grade_opponent` u práce, schéma v7).

### Changed
- **Spolehlivější čtení známky z PDF posudku.** Parser navíc rozpozná
  historické formulace FAI UTB („navrhuji hodnocení B - velmi dobře",
  „doporučuji hodnotit stupněm A", „navrhuji klasifikovat stupněm C") — vedle
  dosavadního „Navržená známka: D". Záměrně se vyhýbá boilerplate větě
  „…v případě hodnocení stupněm F – nedostatečně…", aby nehlásil falešné F.
  Týká se i čtení známky vedoucího u oponentur.

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
