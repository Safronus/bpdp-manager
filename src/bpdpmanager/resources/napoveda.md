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

### 2. Tvoje jméno, e-mail a místo posudku (v profilu)
V **👤 → 🗂 Správa profilů**:

- **👤 Tvoje jméno a tituly…** — jméno + **tituly před/za** (např.
  „doc. Ing." a „Ph.D."). Jméno slouží k **auto-detekci role** při STAG
  importu (vedoucí / oponent); tituly se **automaticky složí do jména
  autora v posudku** („doc. Ing. Petr Žáček, Ph.D.").
- **✉ E-mail…** — tvůj e-mail (např. `prijmeni@utb.cz`). Slouží jako
  **odesílatel při posílání posudků sekretářkám** (viz *Odeslání posudků
  e-mailem*). SMTP server se nastavuje v **👤 → ✉ Nastavení e-mailu (SMTP)**.
- **📍 Místo posudku…** — město pro podpisový blok posudku
  (default *Zlín*).

> Tituly před/za jdou nastavit i u **oponentů** a **vedoucích** v jejich
> registrech — uloží se jako text a zobrazí se u jejich jména (i v posudku,
> když píšeš za ně).

### 3. Studijní obory (+ STAG zkratky)
V toolbaru **Obory + sekretářky** přidej obory, které vedeš. U každého můžeš vyplnit:

- **STAG kód** (např. `knIT-KYB`) — **důležité pro STAG import**:
  podle něj se obor automaticky namapuje. Bez něj tě import upozorní,
  že obor není namapovaný (a budeš ho muset doplnit ručně).
- volitelně sekretářku oboru (jméno, email, telefon) a její **oslovení
  v mailu** (např. „Vážená paní Nováková") — použije se při odesílání posudků;
  prázdné = formální výchozí „Dobrý den, paní {jméno},".

> Manažer **seskupuje obory podle sekretářky**; ve sloupci **Oslovení** vidíš
> její oslovení. **Dvojklik na hlavičku sekretářky** upraví její kontakt
> i oslovení **hromadně pro všechny její obory** (dvojklik na obor upraví
> jen ten obor).

> **⭐ Defaultní obory:** tlačítko **Defaultní…** v manažeru oborů nabídne
> buď **doplnit chybějící** výchozí obory FAI UTB i s STAG zkratkami (NSWI,
> NKYB, NUI, SWI, ITA — prezenční/kombinované, vč. anglických variant; lze
> přepsat lišící se STAG kódy), nebo **smazat celý číselník a nahradit ho
> výchozími**. Nový (prázdný) profil obory dostane rovnou.

### 4. Šablony posudků
V toolbaru **📝 Šablony posudků → + Přidat šablonu…** nahraj XLSX
šablony posudků (vedoucího / oponenta, BP / DP, CZ / EN). Aplikace
z šablony **sama rozpozná** typ, roli, jazyk, obor, rok i strukturu
kritérií. Bez šablon nelze generovat posudky.

> **⭐ Defaultní šablony:** tlačítko **Defaultní…** v knihovně šablon nabídne
> buď **doplnit chybějící** z kompletní sady FAI UTB (BP/DP, vedoucí/oponent,
> CZ/EN, podle oboru; volitelně přepsat stejnojmenné), nebo **smazat všechny
> šablony a nahradit je výchozí sadou**. Nový profil je dostane rovnou — můžeš
> hned psát posudky bez ručního nahrávání. (Akademický rok se propíše z hlavičky
> šablony.)

### 5. (Volitelně) LibreOffice pro PDF
Pro generování **PDF** posudku z XLSX je potřeba LibreOffice:

```bash
brew install --cask libreoffice
```

Bez něj se vygeneruje jen XLSX (PDF si vyrobíš v Excelu přes Export).
LibreOffice se použije i k **vyčtení navržené známky ze starých `.doc`**
posudků (převede je na pozadí na text). PDF a `.docx` fungují i bez něj.

### 6. Doporučený první krok — stáhnout své práce ze STAG
Jakmile máš nastavené **jméno** (krok 2) a **obory s STAG zkratkami**
(krok 3), je nejrychlejší start **hromadně stáhnout své práce přímo ze STAG**:

1. Toolbar **📥 Import ze STAG…**
2. **🎓 Moje vedené práce…** — najde a předvybere všechny tvé vedené práce
   (historické i aktuální) podle jména z profilu.
3. **🧐 Moje oponentury…** — totéž pro práce, kde jsi oponent.
4. Zaškrtni, co chceš, a **⬇ Stáhnout vybrané**. U velkého objemu příloh
   zvol *„Jen data (bez příloh)"* — gigabajty plných textů dotáhneš později
   cíleně. Stav a chybějící soubory pak průběžně doplníš přes
   *🔄 Aktualizovat …* a zkontroluješ tlačítkem *🔍 Kontrola se STAG*.

Tím máš databázi naplněnou během chvíle. (Detaily importu viz sekce
*Import ze STAG* níže.)

### 7. Co dál
Dále můžeš:

- nebo **ručně přidat práci** (toolbar *+ Nová práce*),
- **🌱 Zájemce** — nová budoucí práce s dialogem, kde rovnou (volitelně)
  vyplníš **studenta, obor, název a anotaci** (nic není povinné — co
  nevyplníš, zůstane prázdné). Studenta lze rovnou **založit tlačítkem
  „+ Nový"** (vč. oboru). Obor je **vždy editovatelný**; při výběru studenta se
  předvyplní jeho oborem a (je-li student zvolen) se k němu uloží. Stav je
  defaultně *Vypsané téma* (lze změnit na *Zájemce s tématem* / *bez tématu*).
- u práce *V řešení* kliknout **📝 Napsat posudek…**.

---

## Přehled obrazovky

Hlavní okno má nahoře **toolbar** (tlačítka jsou barevně seskupená:
zelená *Vytvořit*, modrá *Správa*, fialová *Šablony posudků*, tyrkysová
*Import ze STAG*, šedá *Profil / Obnovit / Nápověda*), pod ním
**🔍 vyhledávací pole** a pak **záložky** (taby):

- **Aktuální** — práce ve stavu *V řešení*
- **Budoucí** — *Zájemce bez tématu*, *Zájemce s tématem*, *Vypsané téma*
- **Historie** — *Obhájeno*, *Nedokončeno*. Nad seznamem jsou filtry:
  **checkboxy stavů** (*Obhájeno* / *Nedokončeno*, defaultně obě zaškrtnuté;
  volba se **pamatuje i po zavření aplikace**), rozbalovací **Oponent**
  (jen oponenti z historie) a **Známka** (A–F/FX) — práce projde, když známce
  odpovídá vedoucí **nebo** oponent. Filtry se kombinují. U hotových prací jsou
  sloupce *Posudky* a *Odesláno* irelevantní, proto se v Historii **nezobrazují**.
- **Vše** — všechny vedené práce
- **🧐 Oponentské posudky** — práce, kde jsi oponent (ne vedoucí).
  I tady lze psát posudek — v hlavičce detailu **📝 Napsat posudek…**.
- **📅 Harmonogram** — fakultní termíny z PDF

> **Důležité:** zařazení práce do tabu se řídí **stavem**, ne rokem.
> Rok ovlivňuje jen řazení a grupování uvnitř tabu.

### 🔍 Vyhledávání a navigace
Do pole nad záložkami napiš **jméno studenta**, **název práce** nebo
**osobní číslo (Axxxxx)** a stiskni Enter. Hledá napříč vedenými pracemi
i oponenturami. Při jediné shodě aplikace rovnou **skočí na práci**
(přepne záložku a vybere ji), při více shodách nabídne **výběr** (práce
v *Aktuální* jsou nahoře).

### 🟢🟡🔴 Stav posudku barevně
V **Aktuální** se buňka *názvu práce* podbarví podle posudku vedoucího:
🟢 vyrobený soubor · 🟡 jen rozpracovaná data (uložená bez XLSX) · 🔴 nic.
Stav je navíc jako **barevný puntík přímo v názvu**, takže ho vidíš i
u **vybraného** řádku (výběr by jinak pozadí překryl). V **🧐 Oponentské
posudky** stejně podle oponentského posudku. **Dolní lišta** ukazuje barevný
souhrn *hotovo / chybí* (vedoucí i oponentury), ať máš přehled, kolik práce
tě ještě čeká.

Seznam vedených prací (*Aktuální / Budoucí / Historie / Vše*) má sloupec
**V/O** se známkou **vedoucího i oponenta** — vlevo známka vedoucího (V),
vpravo oponenta (O), jako **barevně podbarvená dvojice písmen** (zelená A →
červená F/FX; „—" když chybí obě, plný popis v tooltipu). **Stejně vypadající
sloupec V/O** je i v záložce *Oponentské posudky*.

> **Oponentury — řazení dle roku.** Práce jsou seskupené dle akademického roku;
> defaultně je rozbalený **jen aktuální rok**, starší roky jsou sbalené.
>
> **Oponentury — sloupec Stav a indikace dle roku.** Tabulka oponentur má
> sloupec **Stav** (ze STAG, např. *nedokončeno / obhájeno*). Barevný puntík
> stavu posudku, podbarvení a sloupec *Odesláno* se ukazují **jen u aktuálního
> akademického roku** (u starších je to irelevantní). Známka oponenta se
> u stažených oponentur doplní z nahraného **posudku** (PDF i Word `.doc`/
> `.docx`) automaticky.

Seznam prací v *Aktuální* i *Oponentské posudky* má jednotný sloupec
**Odesláno**: u prací s **hotovým posudkem** ukazuje **✉ ✓ odesláno** /
**✉ ✗ neodesláno** (stejná informace je i v Souhrnu — *Odeslání posudku:
✓/✗*). Posudek se označí jako odeslaný **automaticky** při odeslání e-mailem,
nebo **ručně** přes pravý klik na práci → *✉ Označit posudek za odeslaný
sekretářce* (a zpět).

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
výsledek plagiátorství, sekce **Známky** (navržené z posudků — vedoucí +
oponent), **náhled uložených posudků** (role, body, známka, kritéria,
hodnocení) a na konci **Soubory** (přehled aktuálních příloh — text práce,
posudky, přílohy…). Každá sekce má tlačítko 📋 pro zkopírování do schránky.

> **Známky u historických prací.** Sekce *Známky* bere známku primárně
> z posudku napsaného v aplikaci. Pokud posudek existuje jen jako **nahraný
> soubor** — PDF i Word (`.doc` / `.docx`), typicky u starších prací stažených
> ze STAG — aplikace se z něj pokusí navrženou známku **vyčíst** („navrhuji
> hodnocení B…", „Navržená známka: D", „doporučuji k obhajobě s hodnocením B"
> apod.) a doplní ji. (Starý binární `.doc` se na pozadí převede přes
> LibreOffice — viz krok 5 v *Začínáme*.) Děje se to automaticky při otevření
> práce i po stažení posudku ze STAG; ručně zadanou známku nikdy nepřepíše.

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
- **💡 Doporučený komentář** — tlačítko vloží doporučené znění podle
  verdiktu a procenta shody (rozbalovací menu nabízí konkrétní varianty).
  Plně editovatelné.
- **PDF protokol** — nahrání a otevření protokolu z IS/STAG.

### 📎 Dokumenty
Soubory a odkazy k práci, **agregované podle typu** (Text práce,
Přílohy, Pracovní deník, Oficiální zadání, Posudek vedoucího, Posudek
oponenta, Prezentace, STAG export, Jiné).

- **Verzování:** nahrání dalšího souboru téhož typu vytvoří novou verzi;
  předchozí se označí jako *superseded*. Toggle **Zobrazit starší verze**
  je defaultně **zapnutý** (vidíš i archiv). U posudku se **XLSX i PDF**
  nejnovější verze berou jako aktuální — PDF se ukáže hned, ne až po
  zapnutí starších verzí.
- **Auto-pojmenování:** soubor se přejmenuje na
  `{Příjmení}_{typ}_{YYYY-MM-DD}[_vN].{ext}` a roztřídí do podsložky.
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
  > pravý klik je můžeš **hromadně exportovat** do zvolené složky nebo
  > **odeslat jedním e-mailem** (všechny jako přílohy).
- **Chybějící soubory:** když soubor smažeš ručně mimo aplikaci (např.
  ve Finderu), aplikace se nerozbije — záznam zůstane, ale zobrazí se
  červeně s *⚠ chybí soubor*. Tlačítko **🧹 Odklidit chybějící** odebere
  takové mrtvé záznamy ze seznamu (existující soubory ani odkazy nechá).

---

## Psaní posudku (vedoucí / oponent)

Tlačítko **📝 Napsat posudek…** je na **dvou místech**:

- u **vedené práce** *V řešení* (záložka detailu práce — aktivní jen ve
  stavu *V řešení*),
- u **oponovaného posudku** (záložka *🧐 Oponentské posudky* → v hlavičce
  detailu) — vyplníš tu svůj **oponentský** posudek cizí práce.

Workflow:

1. **Výběr šablony** — dialog nabídne jen **relevantní** šablony,
   **seskupené podle oboru**. Vždy se filtruje podle **typu práce** (u BP
   se nenabízí DP a naopak) a **role**: u vedené práce jen posudek
   *vedoucího*, u oponentury jen *oponenta*. Přepínač *Zobrazit i šablony
   jiných oborů* uvolní už jen filtr oboru. Správná šablona se předvybere.
   Pokud už pro práci existuje uložený posudek, nahoře je tlačítko
   **✏ Pokračovat v posledním posudku**.
2. **Editor posudku** — formulář:
   - *Splnění bodů zadání* (splnil / nesplnil)
   - **Kritéria hodnocení** — body 0–5 po celých bodech, váhy ze šablony
   - **Živý souhrn** — vážené body, procenta, navržená známka (ECTS).
     Stupnice je 1:1 se vzorcem v šabloně: **BP** (max 30 b) A≥29, B≥26,
     C≥23, D≥20, **E≥18**, jinak FX; **DP** (max 35 b) A≥33, B≥30, C≥27,
     D≥24, **E≥21**, jinak F. Hranice E je u obou na **60 %** — cokoli pod
     60 % je FX (BP) / F (DP).
   - *Plagiátorství* (u vedoucího) — předvyplní se z práce
   - *Celkové hodnocení, připomínky a dotazy*
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

## Oponentské posudky

Samostatná záložka **🧐 Oponentské posudky** pro práce, kde vystupuješ
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
- **🧐 Oponentské posudky** — posudky, které jsi napsal(a) jako oponent.

(Oponentské posudky lze poslat i přímo z jejich záložky tlačítkem
**✉ Odeslat sekretářce…**.)

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
   nedokončeno) se posudky nenabízejí. Nezaslané jsou předzaškrtnuté,
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
> - **Přílohy** se připojí; stejnojmenný soubor dostane verzi `_vN`
>   (nepřepisuje), posudky se archivují.
> - Před importem se vytvoří záloha `before-stag-import` a celý import jde
>   **vrátit** tlačítkem *„↩ Vrátit celý import zpět"*.

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
Z PDF posudku vedoucího se navíc u oponentur zkusí **vyčíst navržená známka**.

> **📎 Stáhnout jen soubory:** když práci už v databázi máš a chceš jen
> doplnit soubory, použij ve vyhledávacím okně tlačítko **📎 Stáhnout jen
> soubory**. Stáhne soubory a připojí je k odpovídající práci (párováno přes
> STAG ID, jinak jméno + typ). Pokud práci v databázi nenajde, upozorní tě.

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

## Statistiky

Záložka **📊 Statistiky** (za Harmonogramem) je souhrnný přehled napříč
budoucími, aktuálními i historickými pracemi. Přepočítá se při každém otevření
(nebo tlačítkem *🔄 Přepočítat*). Obsahuje:

- **Souhrn** — KPI karty: vedené práce, V řešení, budoucí, historie,
  oponentury, studenti, odmítnutí zájemci.
- **Kapacita vedení** — aktuálně vedených prací z maxima (15) + počet
  odmítnutých zájemců (po letech).
- **Vývoj počtu vedených prací po letech** — sloupcový přehled (trend).
- **Podle stavu** — kolik prací je v jednotlivých stavech (barevné pruhy).
- **Bakalářské vs diplomové** — poměr BP/DP.
- **Podle akademického roku** — tabulka rok → celkem / BP / DP / V řešení /
  obhájeno / nedokončeno.
- **Podle oboru** — rozložení prací mezi obory.
- **Úspěšnost obhajob** — z dokončených prací (obhájeno vs nedokončeno) + %.
- **Známky obhájených vedených prací** — rozložení navržených známek
  **vedoucího** i **oponenta** (A–F).
- **Oponentury** — souhrn oponovaných prací: počet, rozpad BP/DP, po letech
  a **mnou navržené známky** (jako oponent).
- **Soubory (přílohy)** — kolik máš celkem souborů a kolik zabírají, rozpad
  **podle druhu dokumentu** (text práce / přílohy / posudky / …) a **největší
  práce** podle objemu (top 10). Počítá se z reálných souborů na disku
  (vč. starších verzí).
- **Odměny (orientačně)** — per rok: odměna za vedení (3 000 Kč/obhájenou
  práci, max 12/rok) a oponentury (600 Kč/posudek) + celkový součet.
- **Posudky** — hotové / rozpracované / chybí (vedoucí), hotové / chybí
  (oponentské) a kolik jich bylo odesláno sekretářce.

> **Odmítnutí zájemci** se evidují v toolbaru **🚫 Odmítnutí** (jméno, obor,
> akademický rok) — souvisí s kapacitou vedení a promítají se do statistik.

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
- **💾 Zálohy** — 10 rotujících záloh + ruční zálohy. **👤 → 💾 Zálohovat teď**
  vytvoří zálohu kdykoliv jedním klikem; **👤 → 💾 Zálohy** otevře manažer
  (seznam, **obnova**, mazání, *Zálohovat teď*, otevřít složku). Při obnově se
  aktuální stav předtím uloží jako `before-restore`, takže i obnova jde vrátit.
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
- **📦 Export / import práce (ZIP)** — pravý klik na práci → *Exportovat práci
  do ZIP* uloží **kompletní balík** (data, stav, posudky, známky a všechny
  soubory). Na jiném zařízení / v jiném profilu ho přes toolbar **📦 Import
  práce ze ZIP…** naimportuješ jako **novou práci** (obnoví se i navázaný
  student, oponent a obor; soubory se přenesou). Vhodné pro přesun jediné
  práce mezi profily nebo zálohu jedné práce.

---

## Spuštění

```bash
python -m bpdpmanager            # spustí aplikaci
python -m bpdpmanager --load-demo  # nahraje fiktivní demo data
```

Reálná data nikdy nejsou v Gitu — zůstávají lokálně ve složce profilu.
