# BPDPManager

Jednoduchá desktopová aplikace v Pythonu (PySide6) pro správu vedení a zadávání témat
**bakalářských (BP)** a **diplomových (DP)** prací. Umožňuje vedoucím přehledně sledovat
jednotlivé akademické roky, studenty, stav prací, body zadání, oponenty a zájemce
o budoucí témata.

**Aktuální verze: 0.2.0** — viz [CHANGELOG.md](CHANGELOG.md) pro historii.

> **Pozor — soukromí:** Repozitář obsahuje pouze zdrojový kód a fiktivní ukázková data.
> Reálná data o studentech a pracích zůstávají lokálně v `~/.bpdpmanager/` a nikdy nejsou
> commitnuta do Gitu.

## Funkce

- **Evidence prací** strukturovaná podle akademického roku, typu (BP/DP) a stavu
- **7 stavů toku**: *Zájemce → Rezervace s tématem → Vypsané téma → Oficiálně zadané → V řešení → Obhájeno → Nedokončeno*, s validací přechodů
- **Studenti**: jméno, obor, forma studia, osobní číslo UTB (např. A24390), email, telefon, poznámka
- **Oponenti** rozdělení na **interní** (jméno + email) a **externí** (jméno + email + telefon + adresa)
- **Studijní obory** jako spravovatelný číselník — přidat, přejmenovat (synchronizuje studenty), smazat
- **Vypsané téma**: název CZ + anotace
- **Oficiální zadání**: navíc název EN, body zadání, literární zdroje
- **Dokumenty k práci**: nahrávání souborů s typem (Posudek vedoucího, Posudek oponenta, Text práce, Oficiální zadání, Prezentace, Jiné) + externí URL/odkazy
- **Pohledy**: *Aktuální rok*, *Budoucí zájemci*, *Historie*, *Vše*
- **📅 Harmonogram fakulty**: import PDF časového plánu výuky FAI UTB, automatická extrakce klíčových termínů (odevzdání BP/DP, SZZ, promoce, zkouškové období…), žlutý panel s nadcházejícími důležitými termíny v následujících 60 dnech
- **Termíny a poznámky** z konzultací u každé práce
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

## Licence

[MIT](LICENSE)
