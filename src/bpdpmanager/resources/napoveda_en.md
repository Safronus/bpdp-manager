# Help — BPDPManager

A desktop application for managing the supervision and opposition of
**bachelor's (BP)** and **master's (DP)** theses of a single academic
supervisor.

> This help is the *single source of truth* — it is shown in the app
> (toolbar **❓ Help**) and in the repository. The English version is being
> translated in waves; sections not translated yet are shown in Czech below.

---

## 🚀 Getting started (first run)

**The fastest and recommended path is an initial bulk import from STAG.** It
**creates students, opponents and supervisors for you** directly from STAG
data — **no manual entry needed**. So: pick a **data profile** (step 1), fill
in **your name** (step 2, for role auto-detection) and run the **STAG import**
(step 3), which fills the database. Programmes, review templates and
LibreOffice are supplementary settings (steps 4–6).

### 1. Data profile and data folder
On first run a welcome window asks **where to store the data**:

- **🆕 New empty profile** — choose a folder for `db.json`, documents,
  templates and backups. To sync between several Macs, pick a folder in
  **iCloud Drive** (e.g.
  `~/Library/Mobile Documents/com~apple~CloudDocs/BPDPManager`).
- **📂 Open an existing profile** — if you already have a folder with `db.json`.
- **📥 Import from a ZIP bundle** — when moving a profile from another device.

> Profiles can be switched / added any time via the **👤** toolbar menu.
> Multiple profiles = separate data sets (personal / shared …).

### 2. Your name, e-mail and review place (in the profile)
In **👤 → 🗂 Profile management**:

- **👤 Your name and titles…** — name + **titles before/after** (e.g.
  "doc. Ing." and "Ph.D."). The name is used for **role auto-detection**
  during STAG import (supervisor / opponent); the titles are **automatically
  composed into the author name in reviews**.
- **✉ E-mail…** — your e-mail (e.g. `surname@utb.cz`). Used as the **sender
  when e-mailing reviews to secretaries**. The SMTP server is configured in
  **👤 → ✉ E-mail settings (SMTP)**.
- **📍 Review place…** — the city for the review signature block
  (default *Zlín*).

> Titles before/after can also be set for **opponents** and **supervisors**
> in their registries — stored as text and shown with their name (also in
> reviews written on their behalf).
>
> The **Opponents manager** groups opponents into **Internal** / **External**
> (drag & drop between groups) and into **sub-groups by Department**. The
> **Opposes theses** column shows the count of opposed theses, with subtotals
> per department and a **checksum Σ** per group.
>
> The **Students manager** has a real-time, diacritics-insensitive
> **🔎 surname filter** and a *Hide historical students* checkbox (hides
> students with a **defended** or **not completed** thesis).
>
> **Titles from STAG.** STAG provides names as *"Surname Name, titles"*. When
> downloading a thesis, the app **parses** them into titles before / name /
> titles after. Older records can be fixed with **🧹 Clean up titles** in the
> *Opponents* / *Supervisors* manager (with a preview; also parses supervisor
> names stored with opposed theses).

### 3. 🌟 Initial STAG import — the main step
Once your **name** is set (step 2), the fastest start is a **bulk download of
your theses directly from STAG**:

1. Toolbar **📥 Import from STAG…**
2. **🎓 My supervised theses…** — finds and pre-selects all your supervised
   theses (historical and current) by your profile name.
3. **🧐 My opposed theses…** — the same for theses where you are the opponent.
4. Tick what you want and **⬇ Download selected**. For large attachment
   volumes choose *"Data only (no attachments)"* — gigabytes of full texts can
   be fetched later via *🔄 Update…* and checked with *🔍 STAG consistency*.

Before writing, a **📋 Summary before import** lists the **new students,
opponents, supervisors and programmes that will be created automatically** —
so you **don't have to create them by hand** (opponents are created as
*internal*; kind and contact can be edited later). Your database is filled in
minutes.

### 4. Study programmes (+ STAG codes) — recommended
The easiest way is to load the **default programmes** via **⭐ Defaults…**
(toolbar **Programmes + secretaries**) — adds the whole FAI UTB set including
STAG codes. Anything extra can be added right during import. Having programmes
ready matters for **correct mapping** and for assigning a **secretary**
(needed for e-mailing reviews).

Each programme can have:

- a **STAG code** (e.g. `knIT-KYB`) — **important for STAG import**: the
  programme is mapped automatically by it. Without it the import warns you.
- optionally a programme secretary (name, e-mail, phone) and her **e-mail
  salutation** (e.g. "Vážená paní Nováková") — used when sending reviews;
  empty = a formal default.

> The manager **groups programmes by secretary**; the **Salutation** column
> shows her salutation. **Double-click a secretary header** to edit her
> contact and salutation **for all her programmes at once**.

> **⭐ Default programmes:** the **Defaults…** button offers either **adding
> the missing** FAI UTB defaults incl. STAG codes (NSWI, NKYB, NUI, SWI, ITA —
> full-time/part-time, incl. English variants), or **replacing the whole
> list with the defaults**. A new (empty) profile gets them automatically.

### 5. Review templates
**Download the default templates** via **⭐ Defaults…** in the template
library (toolbar **📝 Review templates**) — adds the ready FAI UTB set so you
can write reviews immediately. Without templates, reviews cannot be generated.

> **What the default set covers (and what not).** The built-in templates
> **do not cover all programmes**:
>
> | Programme | BP | DP |
> |------|----|----|
> | **SWI** | ✅ (incl. EN) | — |
> | **ITA** | ✅ (CZ only) | — |
> | **NSWI** | — | ✅ (incl. EN) |
> | **NKYB** | — | ✅ (incl. EN) |
> | **NUI** | — | ✅ (CZ only) |
> | **BTSM** | ❌ missing | ❌ missing |
> | **IŘT** | ❌ missing | ❌ missing |
>
> Missing ones (esp. **BTSM**, **IŘT**, EN variants of ITA/NUI) can be added
> via **📝 Review templates → + Add template…** (the app auto-detects type,
> role, language, programme, year and the criteria structure from the XLSX).

> **Templates are form-neutral.** Full-time (**-P**) and part-time (**-K**)
> forms of the same programme **share one template** (`-P/-K` tags are STAG
> distinctions only).

> **⭐ Default templates:** the **Defaults…** button offers **adding the
> missing** built-in FAI UTB templates, or **replacing all templates** with
> the default set. A new profile gets them automatically.

> **🧹 Clean duplicates:** if you have legacy duplicate `-P`/`-K` templates,
> the **Clean duplicates** button **merges** them and renames survivors to
> form-neutral names. Shows a preview; generated reviews stay untouched.

### 6. (Optional) LibreOffice for PDF
Generating the review **PDF** from XLSX requires LibreOffice:

```bash
brew install --cask libreoffice
```

Without it only the XLSX is generated. LibreOffice is also used to **read the
suggested grade from old `.doc`** reviews. PDF and `.docx` work without it.

### 7. What next
Students, opponents and supervisors are already in the database (the STAG
import created them). You can also:

- **add a thesis manually** (toolbar *+ New thesis*) — for cases not in STAG,
- **🌱 Candidate** — a new future thesis with an optional quick form
  (student, programme, title, annotation; nothing is required). Default
  status is *Listed topic*.
- click **📝 Write review…** on a thesis *In progress*.

---

## Screen overview

The main window has a **toolbar** at the top (buttons grouped by colour:
green *Create*, blue *Manage*, purple *Review templates*, teal *STAG import*,
grey *Profile / Refresh / Help*), a **🔍 search field** below it and then the
**tabs**:

- **Currently supervised theses** — theses *In progress*. The tab title shows
  the **count**.
- **Theses in the next academic year Y/Y** — *Candidate without/with topic*,
  *Listed topic*. The count is **coloured by capacity**: under 15 green,
  exactly 15 yellow, over 15 red. Future theses have no grades or reviews, so
  the **S/O**, *Reviews* and *Sent* columns are hidden.
- **History** — *Defended*, *Failed defense*, *Not completed*. Filters above
  the list: **status checkboxes** (remembered across restarts), **Opponent**,
  **Grade** (matches supervisor **or** opponent), **Programme** (aggregated)
  and **Type** (BP/DP). Filters combine. Irrelevant columns are hidden.
- **All** — all supervised theses. **Academic year headers** are coloured:
  **future** (blue), **current** (green), **past** (grey).
- **🧐 Opposed theses** — theses where you are the opponent. The tab title
  counts the current academic year. Reviews can be written here too.
- **📅 Schedule** — faculty deadlines from PDF

> **Important:** the tab placement is driven by **status**, not year.

### 🔍 Search and navigation
Type a **student name**, **thesis title** or **personal number (Axxxxx)** into
the field above the tabs — searches across supervised and opposed theses.

**Real-time suggestions:** a **fragment** of a surname or title is enough,
**diacritics- and case-insensitive** (`gol` finds **Goláň**), programme works
too. Each row shows `[tab]  Supervised/Opposed · BP/DP · student — title ·
programme`; selecting it **jumps straight to the thesis**.

Pressing **Enter** without picking a suggestion (or clicking **Find**) keeps
the original behaviour: one match jumps, several offer a menu.

### 🟢🟡🔴 Review status colours
In **Current**, a **coloured dot in the thesis title** shows the supervisor
review status: 🟢 produced file · 🟡 draft data only · 🔴 nothing. The same in
**🧐 Opposed theses** for the opponent review. The **bottom bar** shows a
coloured *done / missing* summary.

The thesis lists have an **S/O column** with the supervisor (left) and
opponent (right) grade as a **colour-tinted letter pair** (green A → red
F/FX). When a grade exists but the **role's review file is missing**, an
orange **⚠** appears next to the grade (not drawn for future theses).

> **Opposed theses** are grouped by academic year and **BP / DP**; only the
> current year is expanded by default. The **Status** column is a rounded
> colour badge; the review-status dot and *Sent* column only show for the
> current academic year. The opponent grade is auto-read from the uploaded
> review (PDF and Word `.doc`/`.docx`).

The *Current* and *Opposed theses* lists share the **Sent** column
(**✉ ✓ sent** / **✉ ✗ not sent** for theses with a finished review). A review
is marked as sent **automatically** when e-mailed, or **manually** via
right-click → *✉ Mark review as sent to the secretary*. Historical theses
don't track sending.

Next to it is the **Printed** column (✓ / ✗) — whether the review went to
print. Relevant only for **currently supervised** theses and **this year's
opposed** ones. Toggle manually via right-click → *🖨 Mark review as printed*,
or the dialog asks after a successful MyQ print. The print dialog pre-checks
unprinted reviews based on this flag.

Each thesis tab has a **tree** (year → BP/DP → thesis) at the top and the
**detail** of the selected thesis below. The first thesis in *Current* opens
automatically on start.

---

## Thesis statuses and transitions

A thesis passes through 7 statuses:

1. **Candidate without topic** — interested student, no topic yet
2. **Candidate with topic** — topic agreed
3. **Listed topic** — officially listed (requires CZ title + annotation)
4. **In progress** — approved assignment, active work (requires EN title,
   objectives and references)
5. **Defended** — successful defense
6. **Failed defense** — completed but the defense **failed**
   (STAG codes *DBUO* / *OPUNO*)
7. **Not completed** — **never brought** to a defense (STAG code *ND*)

> **Failed defense vs Not completed.** *Failed defense* = the student
> defended and failed; *Not completed* = never finished. STAG import tells
> them apart automatically; older records can be fixed manually via
> *Transition to status*.

**Second defense attempt:** from *Not completed* and *Failed defense* a thesis
can return to *In progress* (reopening) or go straight to *Defended*.

Transitions are validated — the *Transition to status* buttons offer only
allowed targets, and the panel is shown **only for work-in-progress theses**.

---

> **🌐 Translation in progress.** The following sections are not
> translated to English yet and are shown in Czech. They will be
> translated in upcoming updates.

## Práce — detail (záložky)

Detail vybrané práce má vnitřní záložky:

### 📋 Souhrn
Read-only přehled celé práce — barevný badge stavu, hlavička
(typ / název / student / oponent), anotace, body zadání, literatura,
výsledek plagiátorství, sekce **Známky** (navržené z posudků — vedoucí +
oponent), **náhled uložených posudků** (role, body, známka, kritéria,
hodnocení) a na konci **Soubory** (přehled aktuálních příloh — text práce,
posudky, přílohy…). Každá sekce má tlačítko 📋 pro zkopírování do schránky.

> **Známky u historických prací.** Sekce *Známky* bere známku primárně
> z posudku napsaného v aplikaci. Pokud posudek existuje jen jako **nahraný
> soubor** — PDF i Word (`.doc` / `.docx`), typicky u starších prací stažených
> ze STAG — aplikace se z něj pokusí navrženou známku **vyčíst** a doplní ji.
> U **Wordových** posudků se přednostně bere **vybraná hodnota formulářového
> rozevíracího pole** se známkou (autoritativní), a teprve když chybí, použije
> se volný text („navrhuji hodnocení B…", „Navržená známka: D", „doporučuji
> k obhajobě s hodnocením B"). (Starý binární `.doc` se na pozadí převede přes
> LibreOffice — viz krok 5 v *Začínáme*.) Šifrovaná PDF ze STAG se taky čtou.
> **Nahrání/stažení nového souboru posudku známku dané role přepíše** (nový
> posudek je autoritativní — tím se i opraví dřív špatně vyčtená hodnota).
> Automatické doplnění při otevření práce naopak jen **doplňuje prázdné**
> a ručně zadanou známku nikdy nepřepíše.

### 📝 Téma zadání
Rok, student, **obor**, oponent, název CZ + EN, anotace CZ + EN, body zadání
a literární zdroje (volný text s vlastním číslováním), odkaz na STAG.

> **Obor** je rozbalovací seznam **evidovaných oborů** (z manažeru *Obory*) —
> uloží se ke studentovi. Drž ho na některém z evidovaných oborů, ať se práce
> správně spáruje na sekretářku při odesílání posudků. Ručně zadanou hodnotu
> lze ponechat, ale nemusí sednout na žádnou sekretářku.

### Poznámky
Volný text + termíny/konzultace.

### 🔍 Plagiátorství
- **Procento shody** + **verdikt** (Neposouzen / Je plagiát / Není plagiát)
- **Automatické předvyplnění komentáře** — jakmile vyplníš **procento shody**
  a klikneš na **verdikt**, komentář se **sám předvyplní** doporučeným zněním
  (vč. procenta). Změna procenta auto-text obnoví; jakmile komentář **ručně
  upravíš**, už ho to nepřepíše. (*Neposouzen* nic negeneruje.)
- **💡 Doporučený komentář** — tlačítko vloží doporučené znění podle
  verdiktu a procenta shody (rozbalovací menu nabízí konkrétní varianty).
  Plně editovatelné.
- **PDF protokol** — nahrání a otevření protokolu z IS/STAG.
- **Sloupec „Plagiát"** v seznamu *Aktuálně vedených prací* ukazuje zaobleným
  badgem, zda kontrola **proběhla** (✓ zeleně = verdikt jiný než *Neposouzen*)
  nebo **ne** (✗ červeně). V ostatních záložkách je skrytý (tam je irelevantní).

### 📎 Dokumenty
Soubory a odkazy k práci, **agregované podle typu** (Text práce,
Přílohy, **Text práce + přílohy** (balík v jednom zipu), Pracovní deník,
Oficiální zadání, Posudek vedoucího, Posudek oponenta, Prezentace,
**Soubor s průběhem obhajoby**, STAG export, Jiné).
*Soubor s průběhem obhajoby* = protokol / zápis o průběhu obhajoby (SZZ);
u nově stahovaných ze STAG se rozpozná **podle STAG sekce** automaticky
(STAG je tak značí přímo, takže to funguje i u obecných názvů; původní
název se navíc zachová). Už **dříve stažené** takové soubory (vedené jako *Jiné*)
přeřadíš toolbarem **🗂 Přeřadit průběh obhajoby**: ten **dotáhne ze STAG
původní názvy** (které se při dřívějším stažení ztrácely), spáruje je
s lokálními přílohami a v **náhledu s checkboxy** nabídne přeřazení
(protokoly/zápisy obhajoby předzaškrtnuté; se zálohou).

- **Sloupce tabulky:** *Typ / soubor*, *Verze*, *Velikost* (B / KB / MB / GB),
  *Formát* (přípona — PDF / ZIP / …, nebo *odkaz* u URL) a *Cesta k souboru*
  (**celá cesta od kořene** disku). Šířky sloupců se přizpůsobí obsahu.
- **Barevné kategorie:** každý druh dokumentu má svou barvu nadpisu; **posudky
  vedoucího a oponenta** jsou navíc sdruženy do nadřazené skupiny **Posudky**
  a dělí se až v ní.
- **Verzování:** nahrání **stejného** souboru (téhož názvu) vytvoří novou
  verzi a předchozí se označí jako *superseded*. **Různé soubory** stejného
  typu ale **koexistují** — např. dvě přílohy `…_part1.zip` a `…_part2.zip`
  zůstanou obě aktuální (jedna nenahradí druhou). Toggle **Zobrazit starší
  verze** je defaultně **zapnutý** (vidíš i archiv). U posudku se **XLSX i PDF**
  nejnovější verze berou jako aktuální — PDF se ukáže hned, ne až po
  zapnutí starších verzí.
- **Auto-pojmenování:** soubor se přejmenuje na
  `{Příjmení}_{typ}_{YYYY-MM-DD}[_rozlišení][_vN].{ext}` a roztřídí do podsložky.
  U **příloh** (a *Jiné*) se do názvu vloží **rozlišovací část z původního názvu**
  (`…_prilohy_2026-06-08_zdrojove-kody.zip` vs. `…_prilohy_2026-06-08_dataset.zip`),
  aby dvě **různé** přílohy nevypadaly jako verze (`_v2`) téhož souboru.
- **Auto-detekce typu** z původního názvu při nahrání.
- **🗑 Smazat originál po nahrání** (default zapnuto) — odstraní zdroj
  z Downloads, kopie zůstává v `documents/`.
- **📂 Ve Finderu** — označí vybraný soubor přímo ve správci souborů
  (Finder / Explorer), ať se k němu snadno dostaneš na disku.
- **Pravý klik** na dokument otevře kontextové menu (funguje i u oponentur):
  *Otevřít* · *📂 Zobrazit ve Finderu* · *Odebrat*, a u **souborů** navíc:
  - **🖨 Tisk** (u PDF a XLSX) — PDF se pošle rovnou na výchozí tiskárnu,
    XLSX se otevře v aplikaci k ručnímu tisku (Cmd/Ctrl+P).
  - **📋 Kopírovat soubor** — zkopíruje **samotný soubor** do schránky
    (vložíš ho do Finderu, mailu apod.) — ne jen cestu.
  - **💾 Exportovat na disk…** — uloží kopii souboru na zvolené místo.
  - **✉ Odeslat mailem…** — pošle soubor jako přílohu: zvolíš příjemce,
    předmět a text; odesílá se z tvého e-mailu přes **SMTP** (heslo se ptá při
    odeslání, neukládá se — viz *Nastavení e-mailu*). Při selhání SMTP nabídne
    fallback přes .eml.

  > **Více souborů najednou:** označ více souborů (Cmd/Ctrl/Shift klik) a přes
  > pravý klik je můžeš **hromadně exportovat** do zvolené složky,
  > **odeslat jedním e-mailem** (všechny jako přílohy) nebo **🗑 hromadně
  > odebrat** (s jedním dotazem, zda smazat i soubory ze složky).
- **Chybějící soubory:** když soubor smažeš ručně mimo aplikaci (např.
  ve Finderu), aplikace se nerozbije — záznam zůstane, ale zobrazí se
  červeně s *⚠ chybí soubor*. Tlačítko **🧹 Odklidit chybějící** odebere
  takové mrtvé záznamy ze seznamu (existující soubory ani odkazy nechá).

---

## Psaní posudku (vedoucí / oponent)

Tlačítko **📝 Napsat posudek…** je na **dvou místech**:

- u **vedené práce** *V řešení* (záložka detailu práce — aktivní jen ve
  stavu *V řešení*),
- u **oponovaného posudku** (záložka *🧐 Oponované práce* → v hlavičce
  detailu) — vyplníš tu svůj **oponentský** posudek cizí práce.

Workflow:

1. **Výběr šablony** — dialog nabídne jen **relevantní** šablony,
   **seskupené podle oboru**. Vždy se filtruje podle **typu práce** (u BP
   se nenabízí DP a naopak) a **role**: u vedené práce jen posudek
   *vedoucího*, u oponentury jen *oponenta*. Přepínač *Zobrazit i šablony
   jiných oborů* uvolní už jen filtr oboru. Správná šablona se předvybere.
   Pokud už pro práci existuje uložený posudek, nahoře je tlačítko
   **✏ Pokračovat v posledním posudku**. (Předvybere se šablona **oboru
   práce** — `SWI-P`/`NSWI-P` se mapuje na `SWI`, `NKYB-K` na `KYB`.)
2. **Editor posudku** — formulář (nahoře tlačítka **📄 Otevřít text práce**
   a **📕/📘 Otevřít opačný posudek** — u posudku vedoucího nabídne posudek
   oponenta a naopak; aktivní, jen když soubor existuje):
   - *Splnění bodů zadání* — volby **dle jazyka šablony** (CZ
     *splnil(a)/nesplnil(a)*, EN *fulfilled/not fulfilled*)
   - **Kritéria hodnocení** — body 0–5 po celých bodech, váhy ze šablony
   - **Živý souhrn** — vážené body, procenta, navržená známka (ECTS).
     Stupnice je 1:1 se vzorcem v šabloně: **BP** (max 30 b) A≥29, B≥26,
     C≥23, D≥20, **E≥18**, jinak FX; **DP** (max 35 b) A≥33, B≥30, C≥27,
     D≥24, **E≥21**, jinak F. Hranice E je u obou na **60 %** — cokoli pod
     60 % je FX (BP) / F (DP).
   - *Plagiátorství* (u vedoucího) — předvyplní se z práce
   - *Celkové hodnocení, připomínky a dotazy* — u **nového** posudku se sem
     předvyplní **kostra** (tematické nadpisy podle role a jazyka šablony),
     pod kterou píšeš; tlačítkem **🦴 Vložit kostru posudku** ji vyvoláš
     i ručně (rozepsaný text nepřepíše). Je tu i **kontrola pravopisu** (CZ):
     neznámá slova se **podtrhnou** červeně, **pravý klik** nabídne návrhy
     oprav (žádná autokorekce). Když by slovník chyběl nebo se nenačetl
     (např. po přenosu na jiný počítač), ukáže se hláška s tlačítkem
     **⬇ Stáhnout český slovník** — stáhne ho z LibreOffice do
     `~/.bpdpmanager/dictionaries/` a kontrolu rovnou zapne.
   - *Místo, datum* — místo z profilu (default Zlín), datum dnešní
3. **Uložit & vyrobit XLSX + PDF** — data se uloží do práce (JSON),
   vyplní se XLSX šablona a (pokud je nainstalován LibreOffice)
   vygeneruje PDF. Oba soubory se připojí jako příloha typu posudek.
   Během generování (pár sekund — hlavně převod do PDF) se ukáže okno
   s **ukazatelem průběhu**; běží na pozadí, takže aplikace nezamrzne.
4. **Po vygenerování** zůstane otevřené okno s akcemi **📄 Otevřít XLSX**,
   **📕 Otevřít PDF** a **📂 Ukázat ve Finderu** — můžeš otevřít obojí
   z jednoho místa, okno se zavře až tlačítkem *Zavřít*. Seznam dokumentů
   práce se rovnou aktualizuje (nový posudek je hned vidět).

Data posudku jsou *zdrojem pravdy* v JSON — XLSX/PDF lze kdykoli
přegenerovat. Náhled posudku je v záložce **Souhrn**.

> **Archivace posudků:** vždy se drží **jeden aktuální** posudek.
> Při novém vygenerování se předchozí **XLSX přesune** do podsložky
> `posudky/archiv/` (přejmenovaný s časovým razítkem) a starší **PDF se
> smaže** (je jen odvozeninou). V seznamu tak máš čistě 1 aktuální posudek
> + archiv starších verzí.

> **Věrnost šablony 1:1:** vyplněný XLSX je **totožný se šablonou** —
> mění se jen vyplněné buňky. Logo fakulty (i v záhlaví), formátování,
> rozvržení a tisková nastavení zůstávají beze změny.

> **PDF:** vyžaduje LibreOffice (`brew install --cask libreoffice`
> nebo z libreoffice.org). Bez něj se vygeneruje jen XLSX.

> **Logo v PDF:** pokud je logo v šabloně vložené jako *„obrázek
> v buňce"* (Excel funkce *Umístit do buňky*), LibreOffice ho sám neumí
> vykreslit (v PDF by chybělo a objevilo by se `#VALUE!`). Aplikace to
> řeší automaticky — při převodu do PDF logo na dočasné kopii převede na
> klasický obrázek, takže PDF vypadá stejně jako export z Excelu.
> Uložený XLSX zůstává beze změny. Při převodu se navíc PDF **vyladí**:
> tabulka se roztáhne na šířku stránky (menší mezera vpravo, levý okraj
> zůstává), **vycentruje se logo** a hlavička sloupce *„Body (0–5)"*
> dostane menší černý font (na jeden řádek).

---

## Knihovna šablon posudků

Toolbar **📝 Šablony posudků** spravuje XLSX šablony posudků v rámci
profilu (kopie v `profile_dir/templates/`).

- **Přidání šablony** — po výběru XLSX aplikace **auto-detekuje** typ
  (BP/DP), roli (vedoucí/oponent), jazyk (CZ/EN), obor a akademický rok
  z hlavičky a listu *Konfigurace*; navrhne i název. Strukturu kritérií
  (váhy, buňky pro body) nascanuje a uloží.
- **Grupování** v přehledu: 📘 BP / 📗 DP → obor → šablony (abecedně).
  Ikona role (🎓 vedoucí / 🧐 oponent), indikace 🇬🇧 EN.
- Šablony jdou s profilem v ZIP exportu.

---

## Oponované práce

Samostatná záložka **🧐 Oponované práce** pro práce, kde vystupuješ
jako **oponent** (recenzuješ cizí BP/DP). Vlastní model — inline údaje
o studentovi a vedoucím (přes registr vedoucích s našeptáváním),
**obor** (rozbalovací seznam evidovaných oborů — drž ho na evidovaném oboru,
ať se posudek spáruje na sekretářku; ručně zadaná hodnota zůstane),
známky, dokumenty, generovaný souhrn. **Souhrn nově ukazuje i napsaný
posudek** (body, procenta, navržená známka, kritéria, komentář) — stejně
jako u vedených prací posudek vedoucího. **Známky se doplní samy:** známka
*oponenta* z napsaného posudku, známka *vedoucího* se vyčte z nahraného **PDF
posudku vedoucího** (z textu „Navržená známka / Proposed grade"). Sekce Souhrnu
jsou v pořadí: Body zadání → Známky → Napsaný posudek → Dokumenty.
**Seznam dokumentů je úplně stejný
jako u vedených prací** — agregovaný strom podle typu, verzování, **📂 Ve
Finderu**, pravý klik (Otevřít / Finder / Odebrat), indikace chybějících
souborů i **🧹 Odklidit chybějící**. Archivace posudků (1 aktuální + archiv
starších) funguje shodně.

---

## Návrhy témat

Samostatná záložka **💡 Návrhy témat** (za *Oponentskými posudky*) je seznam
**vymyšlených potenciálních témat** — nekompletních nápadů, které ještě nikdo
nevede. **Nemají studenta ani stav** a **akademický rok je tu irelevantní**.
V titulku záložky je **počet návrhů**.

U každého návrhu vyplníš **název, popis, body zadání, literaturu, obor** a
**typ (BP/DP)**. Volitelně zaškrtni **🔒 Zarezervováno** a doplň **komu**
(volný text — jméno či poznámka, bez vazby na evidované studenty).

- **Seznam** vlevo je seskupený na *Bakalářské* / *Diplomové*; u rezervovaných
  je 🔒 a komu. Nahoře je počet návrhů a kolik je rezervovaných.
- **Detail** má **📋 Souhrn** (s tlačítky do schránky — název, popis, body,
  literatura, nebo celý návrh) a **✏ Detail** (editor; ulož tlačítkem
  **💾 Uložit**).
- **➕ Nový návrh** přidá prázdný návrh a otevře editor.
- **🎓 Převést na vedenou práci** z návrhu založí **skutečnou vedenou práci**
  (přenese název, popis → anotace, body zadání, literaturu a typ; stav
  *Zájemce s tématem*, aktuální akademický rok) a **návrh odebere**. Aplikace
  se rovnou přepne na nově založenou práci. *Obor se nepřenáší — drží ho až
  student, kterého k práci přiřadíš.*

---

## Odeslání posudků e-mailem sekretářce

Připravené posudky (PDF) pošleš sekretářce oboru přímo z aplikace.
V toolbaru je tlačítko **✉ Odeslat posudky** s volbou:

- **🎓 Posudky vedoucího (vedené práce)** — posudky, které jsi napsal(a) jako
  vedoucí.
- **🧐 Oponované práce** — posudky, které jsi napsal(a) jako oponent.

V dialogu:

1. **Vyber sekretářku** — nabízejí se sekretářky vyplněné u oborů (👤 e-mail
   u oboru). Podle jejích oborů se vyfiltrují práce (matchuje se **název i
   STAG kód** oboru). Oslovení v mailu se převezme z oboru (viz výše).

   > Když obor práce nesedí na žádný obor sekretářky (typicky u oponentur, kde
   > je kód oboru jiný), nic se nenabídne. Zaškrtni **Zobrazit i práce z jiných
   > oborů** — ukáže se vše s hotovým posudkem (s červeně označeným oborem),
   > vybereš ručně. Počet skrytých prací aplikace napoví pod tabulkou.
2. **Seznam prací** — nabídnou se jen práce s **hotovým PDF posudku**.
   U vedených prací **jen ty aktuální („V řešení")** — z Historie (obhájeno /
   nedokončeno) se posudky nenabízejí. U **oponentur** se nabízí **jen aktuální
   akademický rok** (starší oponentury se sekretářce neposílají). Nezaslané jsou předzaškrtnuté,
   **už odeslané** se defaultně skryjí (zaškrtni *Zobrazit i už odeslané*,
   pokud chceš poslat znovu). BP i DP můžeš poslat naráz.
3. **Náhled e-mailu** — předmět a tělo se sestaví automaticky (pozdrav +
   seznam prací seskupený na **bakalářské / diplomové**, u každé jméno,
   osobní číslo a název). Text **lze upravit**; *↻ Přegenerovat text* ho
   sestaví znovu dle výběru.
4. **Kopie mně** (default zapnuto) — pošle kopii na tvůj e-mail, abys měl(a)
   jistotu, že mail odešel. Volitelně lze zaškrtnout **Připojit popisek
   o aplikaci** — do patičky se přidá řádek o BPDPManageru s odkazem na
   GitHub (default vypnuto, projeví se v náhledu).
5. **🧪 Test — poslat jen sobě** — *dry run*: pošle úplně stejný e-mail
   (včetně PDF příloh) **jen na tvůj e-mail**, abys ho zkontroloval(a), než
   ho pošleš sekretářce. Posudky **neoznačí** jako odeslané a dialog nechá
   otevřený.
6. **✉ Odeslat…** — po potvrzení tě aplikace vyzve k **heslu** (nikam se
   neukládá) a odešle e-mail s **PDF posudky v příloze**. Odeslané práce se
   označí jako *odeslané*.

### Nastavení e-mailu (SMTP)

**👤 → ✉ Nastavení e-mailu (SMTP)** — samostatný správce odchozí pošty:
e-mail odesílatele, **SMTP server / port / zabezpečení** a tlačítko
**🔌 Test spojení** (přihlásí se, bez odeslání). Výchozí hodnoty odpovídají
**UTB Office365** (`outlook.office365.com`, port 587, STARTTLS) — viz
[nastavení CVT UTB](https://www.utb.cz/cvt/office365-thunderbird-doc).
**Heslo se nikde neukládá.**

> **Pozn. k UTB Office365:** UTB vyžaduje pro odchozí poštu **OAuth2**, takže
> přímé přihlášení heslem přes SMTP nemusí projít. Když odeslání selže,
> aplikace nabídne **vytvořit hotový e-mail (.eml) a otevřít ho v tvém
> mailovém klientovi** (Outlook/Thunderbird), kde jsi přihlášený přes OAuth2 —
> stačí kliknout *Odeslat*. Posudky pak můžeš nechat označit jako odeslané.

---

## Tisk posudků

Hotové **PDF posudky** vytiskneš přímo z aplikace — tlačítko **🖨 Tisk posudků**
v toolbaru. V dialogu zvolíš **cíl tisku**:

- **MyQ (`myq.utb.cz`)** — odešle posudky do tiskové fronty univerzity (vyzvedneš
  je u libovolné multifunkce kartou/PINem). Zadáš přihlašovací **jméno + PIN**
  (nikam se neukládají). MyQ posílal **neúplný řetězec certifikátu** (chyběl
  mezičlánek GÉANT/HARICA) — ten je teď v aplikaci **přibalený**, takže ověření
  TLS **obvykle projde samo**. Kdyby přesto selhalo, tisk se **automaticky
  připojí i bez ověření** (MyQ je interní důvěryhodný server) a oznámí to;
  ruční přepínač *Ověřit TLS certifikát serveru* tu zůstává jako pojistka.
- **Systémová tiskárna** — vytiskne na **vybranou tiskárnu** nastavenou v systému
  (macOS/Linux přes CUPS). Vybereš tiskárnu z nabídky a volitelně *Oboustranně*.

V dialogu:
- **Vybereš posudky.** Nabízejí se práce s **hotovým PDF posudkem** z aktuálně
  vedených (posudek vedoucího) i letošních oponentur (posudek oponenta),
  rozdělené na **🖨 K tisku — nevytištěné** (předzaškrtnuté) a **✓ Již
  vytištěné** (samostatný seznam, nezaškrtnuté — pro případný opětovný tisk).
  V každé skupině jsou posudky seskupené do podskupin **🎓 Posudky vedoucího**
  a **🧐 Posudky oponenta**. Tlačítka *Vybrat vše / Zrušit vše* usnadní výběr.
- **🖨 Odeslat na tisk** se nejdřív **zeptá na potvrzení** (kolik a kam), pak
  postupně vytiskne vybraná PDF (do MyQ fronty, nebo na systémovou tiskárnu).
  Na konci se zobrazí **souhrn** (znění podle cíle — *vytištěno* u tiskárny /
  *odesláno do MyQ fronty*) a dialog se **zeptá, zda označit jako vytištěné**
  (promítne se do sloupce *Vytištěno*).

> **Tip — tisk jen vybraných prací.** Pravým klikem na **vybrané práce**
> (v *Aktuálně vedené práce* nebo v *Oponentury*) zvolíš **🖨 Tisk posudku** —
> otevře tentýž dialog, ale **jen se zvolenými pracemi** (posudek vedoucího
> u vedených, posudek oponenta u oponovaných). Funguje i pro jednu práci i pro
> více vybraných najednou; práce bez hotového PDF posudku se přeskočí.

> **Pozn.:** MyQ konektor komunikuje přímo s webem `myq.utb.cz`. Když UTB MyQ
> výrazně změní rozhraní, lze tisk vždy provést i ručně přes web (posudky si
> připravíš přes **📄 Export PDF mých posudků**), nebo použít systémovou
> tiskárnu.

---

## Import ze STAG (CSV)

Toolbar **📥 Import ze STAG…** umí práci buď **stáhnout přímo ze STAG**,
nebo načíst ručně stažený CSV export `getKvalifikacniPrace*.csv`.

### A) Stáhnout přímo ze STAG (doporučeno)

> **Hromadně všechny moje práce:** v import dialogu jsou tlačítka
> **🎓 Moje vedené práce…** a **🧐 Moje oponentury…**. Každé otevře dialog
> **uzamčený na danou roli** (žádné přepínání). Najdou ve STAG podle
> tvého jména z profilu **všechny** práce dané role (historické, aktuální
> i vypsané na další rok), seřazené **dle akademického roku**. Příjmení nemusí
> být jednoznačné (víc vedoucích stejného příjmení) — proto je zapnutý filtr
> **„Jen moje práce (dle celého jména)"**, který ponechá jen práce s tvým
> celým jménem. Filtr lze vypnout. Pak jen zaškrtneš, co naimportovat.
>
> **Načtou se opravdu všechny.** STAG výsledky vyhledávání implicitně
> stránkuje (vrací jen první stránku), takže by se část prací do seznamu
> nedostala. Aplikace proto stránkování automaticky vypne a načte
> **kompletní** seznam.
>
> **Přehledná tabulka.** Nalezené práce jsou v tabulce se sloupci
> **Práce · Typ · Akademický rok · Obhajoba · Oponent · Stav**. Datum
> obhajoby a stav (obhájeno / čeká na obhajobu / nedokončeno / neúspěšná
> obhajoba) jsou přímo z výsledků STAG. **Akademický rok a obor** se po
> vyhledání **automaticky dotáhnou z detailu** každé práce (progress okno,
> lze přerušit) — akademický rok je proto vidět **i u nedokončených** prací.
>
> **Seskupení.** Výběrem **„Seskupit podle"** můžeš práce seskupit dle
> **stavu, typu (BP/DP), oboru, akademického roku** (nebo bez seskupení).
> Zaškrtnutím hlavičky skupiny vybereš/zrušíš celou skupinu naráz.
>
> **Přílohy (📎).** Počet a velikost příloh se u práce zobrazí, **jakmile ji
> zaškrtneš** (např. „📎 4 · 14.0 MB") — dotahuje se z detailu jen u
> zaškrtnutých prací. Samotné **stahování** ukazuje **průběh** (která práce a
> která příloha se zrovna stahuje, **vč. staženo/celkem MB** u velkých příloh)
> a lze ho **přerušit** — po přerušení se **dočasně stažené soubory uklidí**.
> Pokud se nějaká příloha nestáhne, aplikace to vypíše. Stahování běží
> **na pozadí**, takže okno **nezamrzne** ani když STAG odpovídá pomalu
> (Přerušit funguje pořád). Timeout je **odstupňovaný podle velikosti**
> (velká příloha dostane víc času — i stovky MB / GB se v klidu stáhnou,
> malý soubor naopak selže rychle, když opravdu visí). Kdyby se i tak něco
> nestáhlo včas, aplikace to řekne a připomene, že **soubor jde vždy stáhnout
> ze STAGu ručně** (přes webový prohlížeč) a přidat k práci v sekci
> **📎 Dokumenty**. Před stahováním aplikace **nabídne smazání
> zbylých dočasných souborů** z dřívějška (po přerušení / pádu). Když by
> přílohy zabraly **hodně místa** (stovky MB a víc, typicky u hromadného
> stažení mnoha prací), zeptá se, jestli stáhnout přílohy, nebo
> **naimportovat jen data prací bez příloh**. Co se nakonec naimportuje
> (a vyloučení velkých příloh) vybereš v **náhledu souborů** v dalším kroku.
>
> **„✓ už máš" — co se stane při opětovném stažení (merge).** Práce, které už
> v databázi jsou, mají odznak **✓ už máš** a jsou **předem odškrtnuté** (ve
> výchozím stavu se přeskočí). Když je ale **zaškrtneš a stáhneš**, NEvznikne
> duplikát — práce se **spáruje a aktualizuje**:
> - **Párování:** primárně přes **STAG ID (`adipidno`)**, jinak přes
>   *student + akademický rok + typ (BP/DP)*. Repetent (řádný + opravný pokus
>   se stejným studentem, ale jiným STAG ID) zůstává jako **samostatná** práce.
> - **Slučování polí:** ze STAG se převezmou **vyplněné** údaje (název CZ/EN,
>   anotace, body zadání, literatura, vedoucí/oponent, rok); kde STAG nic nemá,
>   **zůstane tvá stávající hodnota** (nic se nepřepíše prázdnem).
> - **Stav práce se NEmění** — u existující práce zůstává tvůj aktuální stav
>   (z dialogu se bere jen u nově zakládaných).
> - **Přílohy** se připojí; dvě **různé** přílohy dostanou rozlišitelné názvy
>   (podle původního názvu, ne `_v2`), **shodný obsah** se nepřidá podruhé
>   a posudky se archivují.
> - Před importem se vytvoří záloha `before-stag-import` a celý import jde
>   **vrátit** tlačítkem *„↩ Vrátit celý import zpět"*.

### 🔄 Tichá kontrola STAG (na pozadí)

Po startu aplikace (automaticky **nejvýš jednou denně** — ať zbytečně
nezatěžuje STAG) porovná na pozadí **aktuální akademický rok** se STAG a
výsledek ukáže v **proužku nad záložkami**. Kdykoli ji spustíš i ručně přes
toolbar **🔄 Aktualizace prací → Zkontrolovat změny ve STAG**. Smysl: máš
jistotu, že je vše aktuální, a **víš, kdy je potřeba aktualizovat**. Kontrola
hlídá:

- **změnu stavu** nebo **chybějící druh souboru** u vedených prací *V řešení*,
- totéž u **oponentur aktuálního roku**,
- **nové práce ve STAG**, které ještě nemáš v databázi — páruje se podle
  **celého jména** (křestní + příjmení), takže se **nezapočítají jmenovci**
  (jiní vedoucí/oponenti se stejným příjmením).

Proužek vždy ukáže výsledek — i **„✓ vše aktuální (žádné změny ani nové
práce)"**. Při změnách svítí **odznak 🔄 na záložkách** *Aktuálně vedené práce*
a *🧐 Oponované práce*. Tlačítkem **🔎 Detaily…** otevřeš **rychlý
náhled** — jmenovitě, které práce mají změnu, které nové práce STAG nabízí,
a (pro kontrolu/debug) i seznam **zkontrolovaných a aktuálních** prací; teprve
odtud přejdeš na **Import ze STAG**. Tlačítko **Detaily…** je dostupné i když
je vše aktuální (ať si můžeš ověřit, co kontrola prošla). Kontrolu lze kdykoli **ručně
zopakovat** tlačítkem **🔄 Zkontrolovat**; **proužek skryješ** křížkem.
Kontrola je **jen pro čtení** (nic nemění); offline tiše oznámí neúspěch.

### 🔍 Kontrola se STAG (co chybí)

Toolbarové tlačítko **🔍 Kontrola se STAG** (skupina *Import*): projde práce
(vedené i oponentury) s STAG ID, porovná je se STAG a vypíše, kde **STAG
nabízí druh dokumentu** (plný text / příloha / posudek), který **v databázi
ještě nemáš**. **Budoucí práce** (zájemci / vypsaná témata) se nekontrolují
(ve STAG ještě soubory nemají). Chybějící soubory jsou **předzaškrtnuté** a
tlačítkem **⬇ Dostáhnout vybrané** je rovnou stáhneš a připojíš k práci (před
zápisem se vytvoří záloha). **Průběh** stahování běží **přímo v seznamu** —
u každého souboru se ukazuje staženo/celkem a po dokončení **✓ staženo**
(nebo **✗ chyba**). U velkých / ZIP příloh STAG soubor teprve **připravuje**,
takže než začne stahování, chvíli to trvá (řádek ukazuje *„STAG připravuje
soubor…"*) — časový limit se **přizpůsobí velikosti** souboru. Když přesto
vyprší, ukáže se to v řádku jako *„✗ … — STAG neodpověděl včas…"* (stejně
srozumitelně i u ostatních způsobů stahování). Zvlášť se vypíšou práce
**bez STAG ID** (nelze ověřit) a případné **chyby dotazu**.

> **Průběh stahování.** Než STAG začne posílat data (server soubor občas
> teprve generuje nebo přiškrtí spojení při mnoha souborech po sobě), ukazuje
> progres **„⏳ připojuji k STAG…"** — není to zamrznutí, jen čekání na server.
> Při krátkém výpadku se stažení **jednou zopakuje**.

### 🧹 Úklid duplicitních příloh

Toolbarové tlačítko **🔄 Aktualizace prací → 🧹 Úklid duplicitních příloh**:
projde **vedené i oponované** práce a najde **přílohy** (druh *Příloha práce*
a *Jiné*), které mají **shodný obsah** jako jiná příloha téže práce — typicky
když se tentýž soubor stáhl ze STAG **dvakrát** (např. 6. a 8. 6.) a uložil se
pod různými cílovými názvy. Shoda se pozná podle **velikosti a obsahu**
(kontrolní součet), ne podle názvu, takže odhalí i duplikáty s odlišným
pojmenováním. **Text práce ani posudky se nikdy neřeší** — u nich může být
stejný obsah legitimní.

Otevře se **náhled**: pro každou práci je vypsáno, **které soubory se smažou**
a **která kopie zůstane**, včetně velikosti. Vše ke smazání je **předzaškrtnuté**
(můžeš odškrtnout); tlačítky *Vybrat vše / Zrušit vše* hromadně. **🗑 Smazat
vybrané** odstraní vybrané přílohy (soubor i evidenci), ponechá vždy jednu
kopii a zbylé přílohy práce označí jako **aktuální**. Když nic shodného není,
okno hlásí *„✓ Žádné duplicitní přílohy nenalezeny."*.

> **Prevence.** Od verze 1.10.0 se duplicitní příloha **nevytvoří znovu**:
> když stahuješ přílohu (nebo *Jiné*), jejíž obsah už u práce je, soubor se
> **nepřipojí podruhé** — zůstane stávající. Nová **verze** přílohy vznikne jen
> tehdy, když se její **obsah opravdu změní**.

### 🔧 Náprava zařazení textu a příloh

Toolbarové tlačítko **🔄 Aktualizace prací → 🔧 Náprava zařazení textu/příloh**
řeší dva pozůstatky staršího stahování ze STAG (kde se druh v sekci „elektronická
podoba" určoval jen **pořadím** souborů):

- **↔ Prohození** — archiv (zip) je veden jako **Text práce** a PDF jako
  **Příloha**. Oprava **PDF přeřadí na Text práce** a **archiv na Přílohu**
  (`text-prace/` ↔ `prilohy/`).
- **📦 Balík** — archiv jako **Text práce**, ke kterému **není žádné samostatné
  PDF** (text i přílohy jsou v jednom zipu, např. *Kopas BP / Jakuba DP /
  Jelínek BP*). Přeřadí se na novou kategorii **Text práce + přílohy**.

Otevře se **náhled** s oběma druhy oprav; vše je **předzaškrtnuté**.
**🔧 Opravit vybrané** druhy přeřadí a soubory **přejmenuje a přesune** do správné
podsložky — **obsah se nemění**. Před zápisem se vytvoří **záloha**. Opravují se
jen **jednoznačné případy** (prohození = právě jeden archiv-text a jedno PDF;
balík = archiv-text bez PDF přílohy); nejasné případy (víc kandidátů) se
**přeskočí**.

> **Od verze 1.11.0** se text vs. příloha při stahování rozpozná správně:
> archiv (.zip/.rar/…) **není nikdy** plný text, text je **PDF**; a jediný zip
> bez PDF textu je **Text práce + přílohy** (balík). Toto tlačítko
> je hlavně na nápravu prací stažených dřív.

Nebo klasicky přes **🌐 Stáhnout ze STAG**:

1. Zadej **příjmení studenta** (nepovinné).
2. Zadej **příjmení vedoucího nebo oponenta** a přepni *role* (Vedoucí /
   Oponent) — druhé příjmení hledání zpřesní. Předvyplní se tvé příjmení
   z profilu.
   - **Hromadně dle vedoucího/oponenta:** nech **příjmení studenta prázdné**
     a zadej jen vedoucího/oponenta — STAG najde **všechny jeho práce**
     (historické i aktuální) a můžeš jich naimportovat víc najednou.
3. **🔍 Vyhledat ve STAG** → ve výsledcích **zaškrtni práce**, které chceš.
   U každé je odznak **🆕 nové** / **✓ už máš** (podle toho, co je v DB) —
   nové jsou předzaškrtnuté. Můžeš tak v jednom kroku stáhnout třeba **BP
   i DP** stejného studenta.
4. **⬇ Stáhnout vybrané (N)** → všechna zaškrtnutá CSV se stáhnou a sloučí
   do jednoho náhledu; ke každé práci se připojí její vlastní CSV. Spolu
   s prací se **automaticky stáhnou i její veřejné soubory** (viz níže).

Hledá se ve veřejném *Prohlížení → Kvalifikační práce* na **stag.utb.cz**,
takže přihlášení obvykle není potřeba.

### Aktualizace už evidovaných prací ze STAG

V průběhu semestru často přibyde u práce nový soubor (odevzdaná práce,
posudek) nebo se změní stav. K tomu slouží dvě tlačítka v *Import ze STAG…*:

- **🔄 Aktualizovat práce v řešení ze STAG** — projde **vedené práce ve stavu
  *V řešení***, dohledá je ve STAG (podle uloženého STAG ID, a když chybí, zkusí
  **dle příjmení studenta**) a nabídne:
  - **změnu stavu** — když STAG hlásí jiný stav (např. *V řešení → Obhájeno*),
    návrh se zobrazí a **aplikuje jen po zaškrtnutí**;
  - **dohrání chybějících souborů** — předzaškrtnou se soubory, jejichž **druh**
    u práce ještě nemáš (typicky nový posudek / odevzdaná práce). Soubory, jejichž
    druh už máš, jsou ponechané neoznačené (můžeš si je přidat ručně).
- **🔄 Aktualizovat práce k oponování ze STAG** — totéž pro **oponentury
  aktuálního akademického roku** (soubory; navíc **doplní STAG stav** do
  sloupce *Stav* i u dříve stažených oponentur).

Vše běží s **progres oknem** a přehledem změn k zaškrtnutí. Před zápisem se
udělá **záloha** a v souhrnu je tlačítko **„↩ Vrátit vše"**. Práce **bez STAG
ID**, které se nepodaří dohledat podle příjmení, se **přeskočí a vypíšou**
(doimportuj je klasicky přes hledání).

> **🔄 Aktualizace JEDNÉ práce ze STAG (pravý klik).** Nad libovolnou prací —
> vedenou (*Aktuální / Budoucí / Historie / Vše*) i oponenturou — je
> v kontextovém menu **„🔄 Aktualizace práce ze STAG…"**. Porovná **jen tu
> jednu** práci se STAG, ukáže navrhované změny (stav + chybějící soubory)
> k zaškrtnutí a aplikuje jen vybrané (se zálohou). Funguje **i z Historie**
> (na rozdíl od hromadné aktualizace, která bere jen práce *V řešení*). Když
> je vše aktuální, dialog to oznámí (nic k aktualizaci).

> **Hromadné akce nad více pracemi (multi-select).** Označ víc prací
> (**Ctrl/Shift** klik) a pravý klik nabídne hromadně — ve vedených i
> oponovaných: **🔄 Aktualizace N prací ze STAG** (jeden dialog, jen vybrané),
> **📄 Otevřít texty prací**, **📘 Otevřít posudky vedoucího i oponenta**,
> **✉ Označit / zrušit odeslání**, **🖨 Označit / zrušit vytištění** a
> **🗑 Roll-back — smazat N prací** (s jedním potvrzením). U jedné vybrané práce
> je k dispozici plné per-práce menu (vč. otevření **obou** posudků).

> **Pozor — „Aktualizovat" jen osvěžuje práce, které už máš.** Nové práce
> (např. pro **nový akademický rok**), které v databázi ještě nemáš, se zde
> **neobjeví**. Na ně je v dialogu *Aktualizovat…* tlačítko **🆕 Najít nové
> práce…** (otevře hromadné vyhledání *Moje vedené práce… / Moje oponentury…*
> podle tvého jména, s odznaky **🆕 nové / ✓ už máš**). Když není co
> aktualizovat, dialog na tuto možnost rovnou upozorní.

### Soubory práce (plný text, přílohy, posudky)

Pokud STAG u práce nabízí soubory, stáhnou se spolu s ní a otevře se
**📎 náhled souborů**:

- typicky **plný text práce**, **přílohy**, **posudek vedoucího** a
  **posudek oponenta** (ne vždy jsou všechny k dispozici),
- každý soubor je **předzaškrtnutý** — odznač, co nechceš importovat
  (tlačítka **☑ Vše** / **☐ Nic**),
- **typ přílohy** je odhadnutý ze STAG; pokud nesedí (nebo se nepodařilo
  rozpoznat), přepiš ho v posledním sloupci.

> **Velké přílohy.** Pokud je některá příloha velká (nad ~25 MB — typicky
> objemný plný text nebo přílohy), aplikace se **před stažením zeptá** a vypíše
> velikosti. Můžeš zvolit *⬇ Stáhnout i tak*, nebo *Přeskočit velké* (ostatní
> soubory se stáhnou normálně).

Vybrané soubory se po importu **připojí k té správné práci** (párováno přes
STAG ID) jako přílohy příslušného typu — objeví se v záložce **Dokumenty**.
Z PDF posudku vedoucího se navíc u oponentur zkusí **vyčíst navržená známka** —
přednostně z **tabulkového pole „Navržená známka"** (orientační formulace
v *Celkovém hodnocení* se ignoruje); u starších posudků bez toho pole se
použije návrhová věta („navrhuji hodnocení …").

> **📎 Stáhnout jen soubory:** když práci už v databázi máš a chceš jen
> doplnit soubory, použij ve vyhledávacím okně tlačítko **📎 Stáhnout jen
> soubory**. Stáhne soubory a připojí je k odpovídající práci (párováno přes
> STAG ID, jinak jméno + typ). Pokud práci v databázi nenajde, upozorní tě.
>
> **🏷 Aktualizovat jen stavy:** vedle něj je tlačítko **🏷 Aktualizovat jen
> stavy** — u zaškrtnutých prací, které už v databázi máš, **aktualizuje jen
> stav** ze STAG (bez stahování souborů). U vedených prací nastaví stav
> (*Obhájeno / Neobhájeno / Nedokončeno / …*), u oponentur stav práce ve STAG.
> Je to rychlé a **vyřeší i zpětné přeřazení** dříve naimportovaných prací
> *Nedokončeno → Neobhájeno* (kde se dřív neúspěšná obhajoba neodlišovala).
> Ukáže přehled, u koho se stav změnil.

> **BP × DP:** BP a DP jsou samostatné záznamy (párují se podle typu),
> takže import DP **nepřepíše** dříve naimportovanou BP. Práce se navíc
> párují přes **STAG ID (`adipidno`)**, takže opětovný import téže práce ji
> spolehlivě *aktualizuje* místo zdvojení.

> **Pozn.:** Veřejný CSV export STAG **neobsahuje jméno studenta**
> (jen osobní číslo). Aplikace ho proto doplní z výsledku vyhledávání.

> **Repetent (řádný + opravný pokus):** když má student dvě práce stejného
> typu (např. řádný pokus *Nedokončeno* + opravný *Obhájeno*, každá s vlastním
> STAG ID), import je **nikdy nespojí ani nepřepíše** — zůstanou jako **dva
> samostatné záznamy** (každý se svým posudkem a soubory). Aplikace je navíc
> **automaticky propojí** (vazba řádný ↔ opravný) a v seznamu i Souhrnu je
> označí **🔁**. Obě jsou v *Historii* podle svého stavu (Obhájeno / Nedokončeno).
> Ve Statistikách je počet *opravných pokusů (repetentů)*.

### B) Ručně stažený CSV
1. Otevři **stag.utb.cz** → **Prohlížení** → **Kvalifikační práce**
2. Vyhledej práci podle jména studenta a u ní zvol **stažení CSV**
3. V aplikaci vyber soubor přes *Import ze STAG… → Procházet…*

(Stejný návod je i pod tlačítkem **❓ Odkud stáhnout** v import dialogu.)

### Průběh importu

- **Auto-detekce role** podle *Tvého jména* (z profilu) v poli
  `vedouciJmeno` / `oponentJmeno` → práce se zařadí jako vedená nebo
  oponentská.
- **Náhled** s per-řádkovou volbou role, mapování oboru (STAG kód →
  lokální obor), stavu a akce (Vytvořit / Aktualizovat / Přeskočit).
  Stav se předvyplní podle STAG kódu (`R`, `DBPOO` → V řešení;
  `DUO` → Obhájeno; `DBUO`, `ND` → Nedokončeno) nebo podle datumů.
  U **nenamapovaného oboru** (jantarový řádek) zvol existující obor, nebo
  **„➕ Nový obor…"** (předvyplní STAG kód). Nově založený obor se **hned
  nabídne i v ostatních řádcích** a u všech řádků **se stejným STAG kódem**
  se rovnou předvybere — nemusíš ho zakládat znovu.
- **Studenti** — u vedených prací se chybějící student automaticky
  založí a přiřadí k práci. Volba **✎ Před založením zkontrolovat /
  doplnit nové studenty** otevře pro každého nového studenta jeho kartu
  (e-mail, telefon, obor…) k doplnění — zapíše se až v rámci importu.
  *(U oponovaných prací se student neeviduje jako samostatná entita,
  ukládá se inline u posudku.)*
- **Souhrn před importem** ukáže, které entity (studenti, oponenti,
  vedoucí, obory) se založí.
- **Transakční** — vše se zapíše jednou na konci; při chybě rollback.
- **Záchranná brzda:** těsně před importem se vytvoří záloha
  `before-stag-import` a po dokončení nabídne souhrnné okno tlačítko
  **↩ Vrátit celý import zpět** — obnoví stav databáze do podoby před importem
  (importovaný stav se předtím ještě zazálohuje jako `before-restore`, takže
  i vrácení jde vrátit). Zálohy spravuješ i v **👤 → 💾 Zálohy**.
- Originální CSV se připojí ke každé importované práci.
- Po importu se aplikace přepne na importovanou práci.

STAG kód oboru lze evidovat v dialogu *Obory* (pole *STAG kód*).

---

## Harmonogram fakulty

Záložka **📅 Harmonogram** — import PDF časového plánu FAI UTB,
automatická extrakce klíčových termínů (odevzdání BP/DP, SZZ, promoce,
zkouškové). Žlutý panel ukazuje nadcházející důležité termíny
v následujících 60 dnech.

---

---

## Application language (CZ / EN)

The **🌐** toolbar button switches the app language between **Czech**
(default) and **English**. The choice is stored in the profile and takes
effect **after a restart** (offered right away). The main surface, details
and dialogs are translated; this help is being translated in waves — sections
not translated yet are shown in Czech.

---

## Application updates

A **silent update check** against GitHub runs after start (reads
`CHANGELOG.md` from the main branch; offline or on error nothing is shown).
When a newer version exists, the **Application update** dialog opens:

- shows the **new version** and the **changelog of all versions between**
  yours and the latest,
- **🔄 Update and restart** runs `git pull`, installs any new dependencies
  (`pip install -e .`) and **restarts** the app,
- **Skip this version** — this version won't be offered again (the next will),
- **Later** — the dialog appears again on the next start,
- the **Check for updates on app start** checkbox turns the check off
  entirely (re-enable in `profiles.json` → `ui_prefs.update_check_enabled`).

> **Note:** updating only works when the app runs from a **git clone**
> (standard `pip install -e .` setup). Local uncommitted changes are never
> overwritten — the dialog asks you to clean them up instead.

---

## Statistics

The **📊 Statistics** tab (after Schedule) is a summary **dashboard** across
future, current and historical theses. It recalculates on every open (or via
*🔄 Recalculate*). A **KPI banner** on top, then **6 panels** in three rows:

- **Summary** — KPI pills: supervised theses, in progress, future, history,
  opposed reviews, students, rejected candidates. **Supervision capacity** is
  shown as text beside the Summary: *currently supervised* (left) and
  *future* (right) out of the maximum 15.

First row:

- **Theses per year over time** — full-width bar chart (years keep growing),
  year below each bar, count above (no Y axis or grid). The combo offers
  **Comparison** (default: supervised + opposed side by side per year, with a
  legend; supervised bars use the capacity gradient) and **Supervised** /
  **Opposed** separately — coloured by the **capacity gradient**: under 15
  green (darker = fewer), **15 yellow**, over 15 red (darker = more).

Second row:

- **Programmes · type · form** — three columns: left a bar chart of
  **bachelor's (BP)** programmes, middle **master's (DP)**, right **Thesis
  types** (top) and **Study form** (bottom). Bars have **rounded corners**
  and **programme colours** with a dot legend. Only the form (*-P/-K*) and
  language (*-EN*) tags are stripped — the *N* prefix and specialisations
  (*-M/-T*) stay, so BP and DP programmes don't mix.
- **By academic year** — year combo top-right (default *All years*); status
  breakdown + *Defense success rate* on the left, **status bars** on the
  right, both reflecting the combo.
- **Grades** — a 4-view combo top-right (*Supervised by me* / *I am the
  opponent* / *Opponents of my supervised* / *Supervisors of my opposed*);
  **A–F grade bars** coloured like the grades in the thesis list (green A →
  red F), letter below each bar.

Third row:

- **Files (attachments)** — summary (count · size · theses), two bar charts
  **by document kind** (count left, size right; kind colours in the legend)
  and a **TOP 10 largest theses** ranking in two columns. Computed from real
  files on disk (incl. older versions).
- **Remuneration (estimate)** — two bar charts by year: **supervision
  remuneration** (left) and **opponent-review remuneration** (right).
  Numbers above bars are in **thousands of CZK**, totals in the captions.

> **Rejected candidates** are tracked via the **🚫 Rejected** toolbar button
> (name, programme, year) — they relate to supervision capacity and appear in
> Statistics. The list is **grouped by academic year**.

---

## Profiles and data

The app supports **multiple data profiles** (personal / shared / different
institutions). Switch via the **👤** toolbar menu.

- **New profile** — any folder for the data; optional import from an
  existing profile.
- **Your name** (for STAG role auto-detection and the review signature) and
  **📍 Review place** (default Zlín) are set in *🗂 Profile management*.
- **🔒 Lock file** — warns when the profile is open on another device
  (e.g. via iCloud) to prevent overwriting.
- **💾 Backups** — 10 rotating backups + manual ones. **👤 → 💾 Back up now**
  creates a backup with one click; **👤 → 💾 Backups** opens the manager
  (list, **restore**, delete, open folder). Restoring first saves the current
  state as `before-restore`, so even a restore can be undone.
- **📤 Profile export to ZIP** — a portable bundle (db + documents +
  templates + schedules). On another device use **📥 Import profile from
  ZIP** (also from the welcome window). A ZIP can also be **merged** into an
  existing profile (add-only merge with a preview).

### Data in the cloud
The profile `data_dir` may live in iCloud / Dropbox / OneDrive — data syncs
between devices. The lock file guards concurrent access. The bytecode cache
(`.pyc`) is stored outside the synced tree (`~/.cache/bpdpmanager/`).

---

## Tips

- **Sorting** of theses and students is Czech alphabetical (with diacritics);
  academic titles are ignored when sorting.
- **The Reviews column** in the thesis tree shows whether the supervisor
  (📘 S) and/or opponent (📕 O) review is uploaded.
- **Autosave** — thesis detail changes save automatically (1.5 s after the
  last edit) + on switching theses and closing the window.
- **Roll-back** — right-click a thesis in the tree → complete deletion of the
  record and files (with a preview and confirmation).
- **Open review** — right-click: on a **supervised thesis** *📕 Open
  opponent's review*, on a **current-year opposed thesis** *📘 Open
  supervisor's review*.
- **📄 Open thesis text** — right-click opens the full text, if available.
- **📄 Export my review PDFs…** — right-click (in *Currently supervised* and
  *Opposed theses*). Select **multiple theses** first (Ctrl/Shift) to bulk
  copy the latest PDFs of **your** review into a chosen folder — supervisor's
  for supervised, opponent's for opposed. Theses without a PDF are skipped;
  a summary is shown. With multiple theses selected, the context menu offers
  only bulk actions.
- **🖨 Print review…** — right-click opens the **Print reviews** dialog
  **with only the selected theses** (supervisor's review for supervised,
  opponent's for opposed). Works for one or **many selected**; theses without
  a finished PDF are skipped.
- **📦 Thesis export / import (ZIP)** — right-click → *Export thesis to ZIP*
  shows a "what to include" picker (thesis data, linked student / opponent /
  programme, files by category — individual files can be unticked). On
  another device use the toolbar **📦 Import thesis from ZIP…**; the import
  detects whether the thesis exists (by bundle ID, else student + type +
  year) and creates a new one or offers an **update of the existing one**
  with the same picker.

---

## Running

```bash
python -m bpdpmanager            # start the app
python -m bpdpmanager --load-demo  # load fictional demo data
```

Real data is never in Git — it stays locally in the profile folder.
