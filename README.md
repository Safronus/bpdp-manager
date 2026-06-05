<p align="center">
  <img src="src/bpdpmanager/resources/icons/app_icon_256.png" width="160" alt="BPDPManager logo">
</p>

# BPDPManager

Jednoduchá desktopová aplikace v Pythonu (PySide6) pro správu vedení a zadávání témat
**bakalářských (BP)** a **diplomových (DP)** prací. Umožňuje vedoucím přehledně sledovat
jednotlivé akademické roky, studenty, stav prací, body zadání, oponenty a zájemce
o budoucí témata.

**Aktuální verze: 0.46.0** — viz [CHANGELOG.md](CHANGELOG.md) pro historii.

📖 **[Kompletní nápověda](src/bpdpmanager/resources/napoveda.md)** — popis všech funkcí a jak to funguje. Stejný obsah je dostupný i přímo v aplikaci přes toolbar **❓ Nápověda** (nebo klávesu **F1**). Nápověda je *jediný zdroj pravdy* — udržuje se v souboru [`src/bpdpmanager/resources/napoveda.md`](src/bpdpmanager/resources/napoveda.md), takže in-app okno i tento odkaz vždy ukazují aktuální stav.

> **Pozor — soukromí:** Repozitář obsahuje pouze zdrojový kód a fiktivní ukázková data.
> Reálná data o studentech a pracích zůstávají lokálně v `~/.bpdpmanager/` a nikdy nejsou
> commitnuta do Gitu.

## Funkce

- **Evidence prací** strukturovaná podle akademického roku, typu (BP/DP) a stavu
- **6 stavů toku**: *Zájemce bez tématu → Zájemce s tématem → Vypsané téma → V řešení → Obhájeno → Nedokončeno*, s validací přechodů. *Schválené téma* bylo v 0.15.0 sloučeno do *V řešení* (po schválení tématu už se na práci pracuje). *Druhý pokus obhajoby* je podporovaný — z *Nedokončeno* se práce dá vrátit do *V řešení* nebo (oprava omylu) přímo do *Obhájeno*.
- **Studenti**: jméno, obor (forma studia se odvozuje z přípony `-P` / `-K`), osobní číslo UTB (např. A24390), email, telefon, poznámka. Správa studentů: strom *BP/DP → obor → studenti*, řazeno dle příjmení, barevné odlišení aktuálních/budoucích/dokončených, filtr „Skrýt dokončené".
- **Oponenti** rozdělení na **interní** (jméno + email) a **externí** (jméno + email + telefon + adresa)
- **Studijní obory + sekretářky** jako spravovatelný číselník (toolbar *Obory + sekretářky*) — přidat, přejmenovat (synchronizuje studenty), smazat. U každého oboru lze evidovat **STAG zkratku** (pro import) a **sekretářku oboru** (jméno, email, telefon, oslovení v mailu). Manažer **seskupuje obory podle sekretářky** (sloupec *Oslovení*); **dvojklik na hlavičku sekretářky** upraví její kontakt i oslovení **hromadně pro všechny její obory**. Tlačítko **⭐ Defaultní** doplní předpřipravené obory FAI UTB i s STAG kódy (nebo umožní kompletní výměnu číselníku); nový profil je dostane rovnou.
- **📋 Souhrn práce**: první záložka detailu — formátovaný read-only přehled celé práce (velký barevný badge stavu, hlavička s typem/názvem/studentem/oponentem, anotace, body zadání, literární zdroje, sekce **Známky** vedoucí + oponent). Každá sekce má malé tlačítko 📋 pro zkopírování do schránky. Ideální pro rychlý vizuální audit nebo přepis do oficiálního systému. **Známky** se počítají z posudku napsaného v aplikaci; u **historických prací**, kde je posudek jen jako nahrané PDF, se navržená známka **vyčte z PDF** (rozpozná i starší formulace „navrhuji hodnocení B…") a doplní automaticky — ručně zadanou hodnotu nikdy nepřepíše.
- **Vypsané téma**: název CZ + anotace
- **Oficiální zadání**: navíc název EN, body zadání a literární zdroje (volný text s vlastním číslováním 1./2./3., styl odpovídá oficiálnímu zadání UTB)
- **Našeptávání** ve výběru studenta a oponenta — stačí napsat část jména/příjmení malými/velkými písmeny, combo automaticky filtruje
- **Dokumenty k práci**: nahrávání souborů s typem (Text práce, Přílohy práce, Pracovní deník, Oficiální zadání, Posudek vedoucího, Posudek oponenta, Prezentace, Jiné) + externí URL/odkazy. Při nahrávání se jméno souboru **automaticky přejmenuje** na ``{Příjmení}_{typ}_{YYYY-MM-DD}[_vN].{ext}`` (např. ``Novák_posudek-vedouciho_2026-05-30.pdf``) a roztřídí se do **podsložky podle typu** (``text-prace/``, ``prilohy/``, ``denik/``, ``zadani/``, ``posudky/``, ``prezentace/``, ``plagiat/``, ``ostatni/``). Z původního názvu souboru se navíc auto-detekuje typ. **Pravý klik** na dokument nabídne *Otevřít / 📂 Zobrazit ve Finderu / Odebrat*, a u souborů navíc **📋 Kopírovat soubor** (samotný soubor do schránky, ne cestu), **💾 Exportovat na disk…** a **✉ Odeslat mailem…** (soubor jako příloha přes SMTP s dotazem na heslo, fallback .eml) — u všech druhů prací i u oponentur.
- **🔍 Plagiátorství**: u každé práce verdikt (*Neposouzen* / *Posouzen — je plagiát* / *Posouzen — není plagiát* s barevným odlišením), procento shody, komentář k výsledku a PDF protokol s odkazem na otevření v systémové aplikaci
- **Pohledy**: *Aktuální rok*, *Budoucí zájemci*, *Historie*, *Vše* — vertikální rozvržení: nahoře strom prací grupovaný *Akademický rok → BP/DP* s sloupci (Student / Téma / Stav / Oponent / Obor) a barevně odlišenými stavy, dole detail vybrané práce
- **🔍 Globální vyhledávání a navigace** — pole nad záložkami najde práci napříč vedenými pracemi i oponenturami podle **jména studenta**, **názvu práce** nebo **osobního čísla (Axxxxx)**. Při jediné shodě rovnou skočí na práci (přepne záložku a vybere ji), při více shodách nabídne výběr (práce v *Aktuální* jsou první).
- **Stav posudku barevně** — v *Aktuální* se buňka názvu práce podbarví podle posudku vedoucího (🟢 vyrobený · 🟡 jen rozpracovaná data · 🔴 chybí); v *🧐 Oponentské posudky* obdobně podle oponentského posudku. Stav je i jako **barevný puntík přímo v názvu** (vidíš ho i u vybraného řádku, který by jinak pozadí překryl), vedle je **✉** u **odeslaných** posudků (info je i v Souhrnu). **Dolní lišta** ukazuje barevný souhrn *kolik posudků chybí / je hotových* (vedoucí i oponentury) — rychlý přehled, co ještě musíš posoudit.
- **Obor jako rozbalovací seznam** — v *📝 Téma zadání* (vedené práce, uloží se ke studentovi) i u oponentur je obor combobox **evidovaných oborů** (z manažeru *Obory*); drží obor na platné hodnotě, aby se práce správně spárovala na sekretářku při odesílání posudků (ručně zadaná hodnota zůstane).
- **Tituly před/za** u uživatele profilu i u oponentů/vedoucích v registrech (ukládají se jako string). Tituly uživatele se **automaticky skládají do jména autora** v posudku („doc. Ing. Petr Novák, Ph.D.").
- **🧐 Oponentské posudky** — samostatná záložka pro práce, kde vystupuješ jako oponent (recenzuješ cizí BP/DP). Vlastní datový model — typ, rok, STAG odkaz, student + vedoucí (vedoucí přes registr s našeptáváním a auto-doplněním emailu), název CZ, body zadání, **známky vedoucího + oponenta s barevným badge**, dokumenty (plný text práce, posudek vedoucího, můj posudek oponenta), automaticky generovaný Souhrn.
- **Registr vedoucích** (toolbar *Vedoucí*) pro oponentské posudky — analogický k registru oponentů, používá se pro našeptávání při vyplňování.
- **📝 Šablony posudků** — knihovna XLSX šablon vedoucího/oponenta v rámci profilu. Toolbar *Šablony posudků* spravuje knihovnu (přidat / upravit / smazat / otevřít v Excelu), pravým klikem na práci → *Generovat posudek z šablony…* aplikace vyplní šablonu daty (student, vedoucí/oponent, název CZ/EN, akademický rok) a připojí jako přílohu typu *Posudek vedoucího* nebo *Posudek oponenta*. Heuristický filler nad popisky v sloupci A funguje pro běžné FAI UTB šablony (BP + DP, CZ + EN, varianty KYB/SWI/UI). Tlačítko **⭐ Defaultní** doplní kompletní sadu šablon FAI UTB (BP/DP, vedoucí/oponent, CZ/EN, podle oboru; akademický rok se propíše z hlavičky) — nebo umožní **kompletní výměnu** (smazat vše a nahradit). Nový profil je dostane rovnou. Dialog generování nabídne **jen šablony pasující na typ práce a roli** (u BP žádné DP; u vedené práce jen vedoucího, u oponentury jen oponenta), **seskupené podle oboru**; přepínač uvolní jen filtr oboru. **Vyplněný posudek je 1:1 se šablonou** — zapisují se jen hodnoty buněk přímo do XML listu, takže logo fakulty (i v záhlaví), formátování a tisková nastavení zůstávají beze změny (`services/xlsx_cell_writer.py`). **Posudek lze psát i u oponovaných prací** — tlačítko *📝 Napsat posudek…* je i v záložce *🧐 Oponentské posudky* (nabídnou se šablony role oponent).
- **✉ Odeslání posudků e-mailem sekretářce** — toolbar *✉ Odeslat posudky* (posudky vedoucího u vedených prací) a tlačítko *✉ Odeslat sekretářce…* v záložce *Oponentské posudky*. Dialog vybere sekretářku (podle e-mailů u oborů), nabídne práce s **hotovým PDF posudku** (nezaslané předzaškrtnuté, už odeslané volitelně), sestaví **editovatelný náhled** e-mailu (pozdrav + seznam prací seskupený na BP/DP s jménem, osobním číslem a názvem), přiloží **PDF posudky poslední verze** a volitelně pošle **kopii sobě** (default zapnuto). Odeslané práce se označí (pole `*_review_sent_at`). Odesílá se z e-mailu uživatele (v profilu); **heslo se nikde neukládá**, vždy se na něj ptá. SMTP server se spravuje v **👤 → ✉ Nastavení e-mailu (SMTP)** (samostatný správce s **testem spojení**, výchozí UTB Office365 `outlook.office365.com:587` STARTTLS). Protože UTB vyžaduje OAuth2, při selhání přímého SMTP aplikace nabídne **fallback přes hotový e-mail (.eml)** otevřený v Outlooku/Thunderbirdu. Síťová/skládací vrstva je izolovaná v `services/email_sender.py`.
- **📥 Import ze STAG** — toolbar *Import ze STAG…*. Práci lze **stáhnout přímo ze STAG** (tlačítko *🌐 Stáhnout ze STAG*): vyhledá veřejný záznam na stag.utb.cz podle příjmení studenta + vedoucího/oponenta (přepínač role, druhé příjmení předvyplněné z profilu), zobrazí seznam shod a po výběru stáhne CSV — bez přihlášení, jen přes standardní knihovnu (síťová vrstva izolovaná v `services/stag_api.py`). Ve výsledcích lze **zaškrtnout víc prací najednou** (např. BP i DP téhož studenta) s odznakem **🆕 nové / ✓ už máš** (nové předzaškrtnuté); stáhnou se a sloučí do jednoho náhledu, ke každé práci se připojí její vlastní CSV. Práce nesou **STAG ID (`adipidno`)**, takže opětovný import téže práce ji přesně spáruje a aktualizuje (BP a DP zůstávají oddělené záznamy). Veřejný CSV neobsahuje jméno studenta (jen osobní číslo), proto se jméno doplní z výsledku vyhledávání. Alternativně lze načíst ručně stažený CSV export `getKvalifikacniPrace*.csv` (encoding cp1250/utf-8 auto-detect), parsuje HTML body zadání `<ol><li>` na plain text a v náhledové tabulce zobrazí každý řádek s **auto-detekovanou rolí** (Vedu / Oponuji — podle jména uživatele v `vedouciJmeno` / `oponentJmeno`), mapováním STAG kódu oboru (`knIT-KYB`) na lokální obor, výchozím stavem práce a akcí (Vytvořit / Aktualizovat / Přeskočit). Pod tabulkou je detail panel s kompletním obsahem parsovaného řádku (názvy CZ/EN, anotace CZ/EN, vedoucí, oponent, body zadání, literatura, známky, datumy). Před importem se zobrazí **souhrn před importem** s výčtem nových studentů, oponentů, vedoucích a oborů, které se založí; uživatel může zrušit. U vedených prací se chybějící student automaticky založí a přiřadí; volitelně lze zaškrtnout **✎ Před založením zkontrolovat / doplnit nové studenty** a doplnit jejich kartu (e-mail, telefon, obor). **Import je transakční** — všechna data se zapíšou jednou na konci a v případě jakékoli chyby se automaticky rolluje zpět (žádné polovičaté stavy). Po úspěchu se původní CSV soubor připojí ke každé dotčené práci jako příloha typu *STAG export*. Před zápisem se vytvoří záloha `before-stag-import`. Aplikace se **rovnou přepne na importovanou práci** v GUI. Pro auto-detekci se používá *Tvoje jméno* z profilu (`Profile.user_name`); STAG kód oboru lze evidovat v dialogu *Obor*. Spolu s prací se navíc **automaticky stáhnou i její veřejné soubory** (plný text, přílohy, posudek vedoucího a oponenta) — v **náhledu souborů** se vybere, co naimportovat (vše předzaškrtnuté, lze odznačit), a u každého se potvrdí/přepíše **typ přílohy** (odhadnutý ze STAG). Vybrané soubory se po importu připojí k odpovídající práci (párováno přes STAG ID) a u oponentur se z PDF posudku vedoucího dosynchronizuje navržená známka. Tlačítko **📎 Stáhnout jen soubory** doplní soubory k práci, kterou už v databázi máš (bez CSV importu).
- **📅 Harmonogram fakulty**: import PDF časového plánu výuky FAI UTB, automatická extrakce klíčových termínů (odevzdání BP/DP, SZZ, promoce, zkouškové období…), žlutý panel s nadcházejícími důležitými termíny v následujících 60 dnech
- **Termíny a poznámky** z konzultací u každé práce
- **Autosave** na pozadí — změny v detailu práce se samy uloží 1,5 s po poslední úpravě (debounce), s 30s pojistkou, plus flush při přepnutí práce a zavření okna
- **Profily — pojmenované datové sady**: víc datových profilů (osobní / sdílený / pro různé instituce), libovolná složka, přepínání za chodu. Welcome dialog při prvním spuštění, toolbar 👤 menu pro přepínání. **Nový profil může startovat s daty importovanými z existujícího profilu** (db.json, dokumenty, harmonogramy — volitelně). Vhodné pro sdílení přes iCloud mezi více Macy téhož uživatele.
- **📤 Export / 📥 Import profilu jako ZIP** (toolbar 👤 menu). Vytvoří přenosný balík `{název}_{datum}.zip` obsahující `manifest.json` + `db.json` (volitelně + dokumenty, harmonogramy, rotující zálohy). Na druhém zařízení se přes *Importovat profil ze ZIPu…* otevře — ukáže manifest preview (profil, app verze, schema, počty souborů), uživatel zvolí název + cílovou složku, rozbalí a aplikace se rovnou přepne na nový profil. Vhodné pro reinstalaci, migraci na nový notebook, sdílení mezi kolegy.
- **Rotující zálohy (10×)** v každém profilu — vytváří se po každém uloženi (s dedupe podle hash), dialog *Zálohy* umožní obnovit libovolný stav, před každou obnovou se vytvoří záloha aktuálního stavu jako `before-restore`.
- **Lock soubor** proti dvojímu otevření profilu na různých zařízeních — pokud detekuje souběžný přístup, varuje uživatele (s detaily kdo/kde/kdy) a nabídne pokračovat nebo zrušit.
- **Lokální JSON úložiště** s atomickými zápisy a automatickou zálohou `db.json.bak`

## Požadavky

- Python ≥ 3.11
- macOS / Linux / Windows

## Instalace

```bash
git clone https://github.com/safronus/bpdp-manager.git
cd bpdp-manager
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

> **zsh tip:** pokud chceš nainstalovat i dev závislosti, napiš `pip install -e ".[dev]"` v uvozovkách — zsh by jinak `[dev]` interpretoval jako glob a hlásil `no matches found`.

## Venv mimo synchronizovanou složku (iCloud, Dropbox, OneDrive…)

Pokud máš projekt v **iCloud-synchronizované složce** (typicky `~/Desktop/` nebo `~/Documents/` na macOS s defaultním nastavením), **nedávej do něj `.venv` přímo**. iCloud Drive
nezvládá tisíce malých souborů ve virtualenvu konzistentně — občas některé soubory přes noc
„odlehčí" (offload) nebo úplně smaže s předpokladem, že je znovu stáhne, čímž rozbije pip
i samotný balíček. Stejné riziko platí pro Dropbox a OneDrive.

**Řešení: venv mimo iCloud + symlink z projektu.** iCloud nesynchronizuje obsah symlinku,
jen samotný odkaz, takže projektová struktura zůstane synchronní mezi zařízeními a každé
zařízení má svůj vlastní venv lokálně.

### Setup (jednorázový na každém zařízení)

```bash
# 1) Mimo iCloud připrav složku pro venvy
mkdir -p ~/.venvs

# 2) Postav venv mimo projekt
/opt/homebrew/bin/python3.12 -m venv ~/.venvs/bpdp-manager     # macOS s Homebrew
# Linux / jiné:  python3.12 -m venv ~/.venvs/bpdp-manager

# 3) V projektu vytvoř symlink na ten venv (pokud .venv existuje, nejdřív ho smaž)
cd <cesta-k-projektu>
rm -rf .venv
ln -s ~/.venvs/bpdp-manager .venv

# 4) Aktivuj a nainstaluj jako obvykle — všechno funguje, jen reálné soubory leží mimo iCloud
source .venv/bin/activate
pip install -e ".[dev]"
python -m bpdpmanager
```

### Použití z druhého zařízení

Na dalším Macu (po iCloud synchronizaci projektu) **stačí znova udělat jen krok 1–3**:
symlink `.venv` je už nasynchronizovaný, jen na něj připrav cíl:

```bash
mkdir -p ~/.venvs
/opt/homebrew/bin/python3.12 -m venv ~/.venvs/bpdp-manager
cd <cesta-k-projektu>
source .venv/bin/activate
pip install -e ".[dev]"
```

Ověření, že to sedí:

```bash
ls -la .venv          # → /Users/<ty>/.venvs/bpdp-manager
readlink .venv        # → /Users/<ty>/.venvs/bpdp-manager
which python          # → cesta přes .venv/bin/python (přes symlink)
```

### Volitelně: ochrana .git/

Adresář `.git/` má taky tisíce malých souborů a iCloud mu může lokálně způsobovat
zpomalení nebo občasné `unable to read tree` chyby. Pokud na to narazíš, vyřeší to
stejný trik:

```bash
mv .git ~/.gitstores/bpdp-manager
ln -s ~/.gitstores/bpdp-manager .git
```

Jinak je `.git` díky content hashům odolnější než venv a většinou nepotřebuje řešit.

## Spuštění

```bash
bpdp-manager
# nebo
python -m bpdpmanager
```

Při prvním spuštění se vytvoří složka `~/.bpdpmanager/` s prázdnou databází.

## Demo data

Pro vyzkoušení aplikace bez reálných dat lze nahrát fiktivní vzorek:

```bash
python -m bpdpmanager --load-demo
```

Demo data jsou v souboru [`examples/seed_demo.json`](examples/seed_demo.json) a obsahují
pouze smyšlené postavy.

## Struktura projektu

```
src/bpdpmanager/
├── models/        # datové třídy (pydantic): Student, Opponent, Thesis, Harmonogram, …
├── storage/       # JSON úložiště s atomickými zápisy
├── services/      # business logika (ThesisService) a PDF parser harmonogramu
├── ui/            # PySide6 okna, dialogy, widgety
│   └── widgets/   # znovupoužitelné komponenty (DocumentsWidget, StatusBadge, …)
└── resources/     # statické zdroje (styly, defaultní obory…)
```

## Datové soubory

Reálná data nikdy nejsou v repozitáři. Sídlí v `~/.bpdpmanager/`:

```
~/.bpdpmanager/
├── db.json                       # hlavní databáze (JSON)
├── db.json.bak                   # automatická záloha
├── harmonograms/
│   └── 2026-2027.pdf             # naimportované PDF harmonogramy
└── documents/
    └── {thesis_id}/
        └── posudek_vedouciho.pdf # nahrané dokumenty
```

Cestu lze přepsat env proměnnou `BPDPMANAGER_DATA_DIR` (např. pro testování).

## Vývoj

```bash
pip install -e .[dev]
pytest
ruff check src tests
```

## Ikona

Aplikační ikona je **vlastní výtvor** generovaný skriptem `scripts/make_icon.py`
(Pillow). Žádné externí stock obrázky — 100% MIT-kompatibilní.

Regenerace všech velikostí a `.icns` (na macOS):

```bash
python scripts/make_icon.py
```

Výstup: `src/bpdpmanager/resources/icons/app_icon{.png,_512.png,_256.png,_128.png,.icns}`.

## Licence

[MIT](LICENSE)
