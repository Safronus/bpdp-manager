# Nápověda — BPDPManager

Desktopová aplikace pro správu vedení a oponování **bakalářských (BP)**
a **diplomových (DP)** prací jednoho akademického vedoucího.

> Tato nápověda je *jediný zdroj pravdy* — zobrazuje se v aplikaci
> (toolbar **❓ Nápověda**) i v repozitáři
> (`src/bpdpmanager/resources/napoveda.md`). Při změně funkcí se
> aktualizuje tady a promítne se na obou místech.

---

## 🚀 Začínáme (první spuštění)

Než začneš importovat ze STAG nebo psát posudky, projdi tento checklist.
Postupuj odshora dolů.

### 1. Datový profil a složka s daty
Při prvním spuštění tě uvítá okno, kde zvolíš, **kam se ukládají data**:

- **🆕 Nový prázdný profil** — vyber složku pro `db.json`, dokumenty,
  šablony a zálohy. Pokud chceš data synchronizovat mezi víc Macy,
  vyber složku v **iCloud Drive** (např.
  `~/Library/Mobile Documents/com~apple~CloudDocs/BPDPManager`).
- **📂 Otevřít existující profil** — pokud už složku s `db.json` máš.
- **📥 Importovat ze ZIP balíku** — pokud přenášíš profil z jiného
  zařízení (export z druhého Macu).

> Profil lze kdykoli přepnout / přidat přes toolbar **👤** menu.
> Více profilů = oddělené datové sady (osobní / sdílený …).

### 2. Tvoje jméno a místo posudku (v profilu)
V **👤 → 🗂 Správa profilů**:

- **👤 Tvoje jméno…** — celé jméno vč. titulů (např.
  „doc. Ing. Petr Žáček, Ph.D."). Slouží k **auto-detekci role** při
  STAG importu (rozpozná, jestli jsi u práce vedoucí nebo oponent)
  a jako **podpis v posudku**.
- **📍 Místo posudku…** — město pro podpisový blok posudku
  (default *Zlín*).

### 3. Studijní obory (+ STAG zkratky)
V toolbaru **Obory** přidej obory, které vedeš. U každého můžeš vyplnit:

- **STAG kód** (např. `knIT-KYB`) — **důležité pro STAG import**:
  podle něj se obor automaticky namapuje. Bez něj tě import upozorní,
  že obor není namapovaný (a budeš ho muset doplnit ručně).
- volitelně sekretářku oboru (jméno, email, telefon).

### 4. Šablony posudků
V toolbaru **📝 Šablony posudků → + Přidat šablonu…** nahraj XLSX
šablony posudků (vedoucího / oponenta, BP / DP, CZ / EN). Aplikace
z šablony **sama rozpozná** typ, roli, jazyk, obor, rok i strukturu
kritérií. Bez šablon nelze generovat posudky.

### 5. (Volitelně) LibreOffice pro PDF
Pro generování **PDF** posudku z XLSX je potřeba LibreOffice:

```bash
brew install --cask libreoffice
```

Bez něj se vygeneruje jen XLSX (PDF si vyrobíš v Excelu přes Export).

### 6. Hotovo — můžeš pracovat
Teď můžeš:

- **📥 Importovat ze STAG** vedené i oponované práce (toolbar
  *Import ze STAG…*),
- nebo **ručně přidat práci** (toolbar *+ Nová práce*),
- u práce *V řešení* kliknout **📝 Napsat posudek…**.

---

## Přehled obrazovky

Hlavní okno má nahoře **toolbar** a pod ním **záložky** (taby):

- **Aktuální** — práce ve stavu *V řešení*
- **Budoucí** — *Zájemce bez tématu*, *Zájemce s tématem*, *Vypsané téma*
- **Historie** — *Obhájeno*, *Nedokončeno*
- **Vše** — všechny vedené práce
- **🧐 Oponentské posudky** — práce, kde jsi oponent (ne vedoucí)
- **📅 Harmonogram** — fakultní termíny z PDF

> **Důležité:** zařazení práce do tabu se řídí **stavem**, ne rokem.
> Rok ovlivňuje jen řazení a grupování uvnitř tabu.

Každý tab prací má nahoře **strom** (rok → BP/DP → práce) a dole
**detail** vybrané práce. Po startu se automaticky otevře první práce
v *Aktuální*.

---

## Stavy práce a přechody

Práce prochází 6 stavy:

1. **Zájemce bez tématu** — student má zájem, téma zatím není
2. **Zájemce s tématem** — domluvené téma
3. **Vypsané téma** — oficiálně vypsané (vyžaduje název CZ + anotaci)
4. **V řešení** — schválené zadání, aktivní práce (vyžaduje název EN,
   body zadání a literaturu)
5. **Obhájeno** — úspěšná obhajoba
6. **Nedokončeno** — neúspěšná obhajoba / nedokončeno

**Druhý pokus obhajoby:** z *Nedokončeno* se práce dá vrátit do
*V řešení* (znovuotevření) nebo přímo do *Obhájeno*. Posudky a text
práce mohou být verzované (viz Dokumenty).

Přechody mezi stavy jsou validované — tlačítka *Přechod do stavu*
v detailu práce nabízejí jen povolené cíle.

---

## Práce — detail (záložky)

Detail vybrané práce má vnitřní záložky:

### 📋 Souhrn
Read-only přehled celé práce — barevný badge stavu, hlavička
(typ / název / student / oponent), anotace, body zadání, literatura,
výsledek plagiátorství a **náhled uložených posudků** (role, body,
známka, kritéria, hodnocení). Každá sekce má tlačítko 📋 pro zkopírování
do schránky.

### 📝 Téma zadání
Název CZ + EN, anotace CZ + EN, body zadání a literární zdroje
(volný text s vlastním číslováním), odkaz na STAG.

### Poznámky
Volný text + termíny/konzultace.

### 🔍 Plagiátorství
- **Procento shody** + **verdikt** (Neposouzen / Je plagiát / Není plagiát)
- **💡 Doporučený komentář** — tlačítko vloží doporučené znění podle
  verdiktu a procenta shody (rozbalovací menu nabízí konkrétní varianty).
  Plně editovatelné.
- **PDF protokol** — nahrání a otevření protokolu z IS/STAG.

### 📎 Dokumenty
Soubory a odkazy k práci, **agregované podle typu** (Text práce,
Přílohy, Pracovní deník, Oficiální zadání, Posudek vedoucího, Posudek
oponenta, Prezentace, STAG export, Jiné).

- **Verzování:** nahrání dalšího souboru téhož typu vytvoří novou verzi;
  předchozí se schová jako *superseded*. Toggle **Zobrazit starší verze**
  je rozbalí.
- **Auto-pojmenování:** soubor se přejmenuje na
  `{Příjmení}_{typ}_{YYYY-MM-DD}[_vN].{ext}` a roztřídí do podsložky.
- **Auto-detekce typu** z původního názvu při nahrání.
- **🗑 Smazat originál po nahrání** (default zapnuto) — odstraní zdroj
  z Downloads, kopie zůstává v `documents/`.

---

## Psaní posudku (vedoucí / oponent)

V detailu *V řešení* práce je tlačítko **📝 Napsat posudek…** (tlačítko
je aktivní jen pro práci ve stavu *V řešení*).

Workflow:

1. **Výběr šablony** — dialog nabídne šablony z knihovny. Správná se
   předvybere podle typu (BP/DP), oboru a role. Pokud už pro práci
   existuje uložený posudek, nahoře je tlačítko
   **✏ Pokračovat v posledním posudku**.
2. **Editor posudku** — formulář:
   - *Splnění bodů zadání* (splnil / nesplnil)
   - **Kritéria hodnocení** — body 0–5 po celých bodech, váhy ze šablony
   - **Živý souhrn** — vážené body, procenta, navržená známka (ECTS)
   - *Plagiátorství* (u vedoucího) — předvyplní se z práce
   - *Celkové hodnocení, připomínky a dotazy*
   - *Místo, datum* — místo z profilu (default Zlín), datum dnešní
3. **Uložit & vyrobit XLSX + PDF** — data se uloží do práce (JSON),
   vyplní se XLSX šablona a (pokud je nainstalován LibreOffice)
   vygeneruje PDF. Oba soubory se připojí jako příloha typu posudek.

Data posudku jsou *zdrojem pravdy* v JSON — XLSX/PDF lze kdykoli
přegenerovat. Náhled posudku je v záložce **Souhrn**.

> **PDF:** vyžaduje LibreOffice (`brew install --cask libreoffice`
> nebo z libreoffice.org). Bez něj se vygeneruje jen XLSX.

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

## Oponentské posudky

Samostatná záložka **🧐 Oponentské posudky** pro práce, kde vystupuješ
jako **oponent** (recenzuješ cizí BP/DP). Vlastní model — inline údaje
o studentovi a vedoucím (přes registr vedoucích s našeptáváním),
známky, dokumenty, generovaný souhrn.

---

## Import ze STAG (CSV)

Toolbar **📥 Import ze STAG…** načte CSV export `getKvalifikacniPrace*.csv`.

- **Auto-detekce role** podle *Tvého jména* (z profilu) v poli
  `vedouciJmeno` / `oponentJmeno` → práce se zařadí jako vedená nebo
  oponentská.
- **Náhled** s per-řádkovou volbou role, mapování oboru (STAG kód →
  lokální obor), stavu a akce (Vytvořit / Aktualizovat / Přeskočit).
  Stav se předvyplní podle STAG kódu (`R`, `DBPOO` → V řešení;
  `DUO` → Obhájeno; `DBUO`, `ND` → Nedokončeno) nebo podle datumů.
- **Souhrn před importem** ukáže, které entity (studenti, oponenti,
  vedoucí, obory) se založí.
- **Transakční** — vše se zapíše jednou na konci; při chybě rollback.
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

## Profily a data

Aplikace podporuje **víc datových profilů** (osobní / sdílený / pro
různé instituce). Přepínání přes toolbar **👤** menu.

- **Nový profil** — libovolná složka pro data; volitelně import dat
  z existujícího profilu.
- **Tvoje jméno** (pro STAG auto-detekci role a podpis v posudku)
  a **📍 Místo posudku** (default Zlín) se nastavují v *🗂 Správa profilů*.
- **🔒 Lock soubor** — varuje, když je profil otevřený na jiném zařízení
  (např. přes iCloud), aby nedošlo k přepsání.
- **💾 Zálohy** — 10 rotujících záloh, obnovitelných z dialogu.
- **📤 Export profilu do ZIPu** — přenosný balík (db + dokumenty +
  šablony + harmonogramy). Na druhém zařízení **📥 Import profilu ze
  ZIPu** (i z welcome okna při prvním spuštění). Lze i **sloučit**
  ZIP do existujícího profilu (add-only merge s preview).

### Data na cloudu
`data_dir` profilu může být v iCloud / Dropbox / OneDrive složce —
data se synchronizují mezi zařízeními. Lock soubor hlídá souběžný
přístup. Bytecode cache (`.pyc`) aplikace ukládá mimo synchronizovaný
strom (`~/.cache/bpdpmanager/`), aby se předešlo problémům s iCloud
synchronizací.

---

## Tipy

- **Řazení** prací a studentů je české abecední (s diakritikou),
  akademické tituly se při řazení ignorují.
- **Sloupec Posudky** ve stromu prací ukazuje, jestli je nahraný
  posudek vedoucího (📘 V) a/nebo oponenta (📕 O).
- **Autosave** — změny v detailu práce se ukládají automaticky
  (1,5 s po poslední úpravě) + při přepnutí práce a zavření okna.
- **Roll-back** — pravý klik na práci ve stromu → kompletní smazání
  záznamu i souborů (s náhledem a potvrzením).

---

## Spuštění

```bash
python -m bpdpmanager            # spustí aplikaci
python -m bpdpmanager --load-demo  # nahraje fiktivní demo data
```

Reálná data nikdy nejsou v Gitu — zůstávají lokálně ve složce profilu.
