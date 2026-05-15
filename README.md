# BPDPManager

Jednoduchá desktopová aplikace v Pythonu (PySide6) pro správu vedení a zadávání témat
**bakalářských (BP)** a **diplomových (DP)** prací. Umožňuje vedoucím přehledně sledovat
jednotlivé akademické roky, studenty, stav prací, body zadání, oponenty a zájemce
o budoucí témata.

> **Pozor — soukromí:** Repozitář obsahuje pouze zdrojový kód a fiktivní ukázková data.
> Reálná data o studentech a pracích zůstávají lokálně v `~/.bpdpmanager/` a nikdy nejsou
> commitnuta do Gitu.

## Funkce

- Strukturovaná evidence prací podle akademického roku, typu (BP/DP) a stavu
- 7 stavů toku: *Zájemce → Rezervace s tématem → Vypsané téma → Oficiálně zadané → V řešení → Obhájeno → Nedokončeno*
- Sledování studentů (jméno, obor, forma studia, kontakt) a oponentů
- Pole pro vypsané téma (název CZ, anotace) i oficiální zadání (název EN, body, literatura)
- Termíny, poznámky z konzultací a přílohy/odkazy
- Tři pohledy: **Historie**, **Aktuální** rok, **Budoucí** zájemci
- Lokální JSON úložiště s atomickými zápisy a automatickou zálohou

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
├── models/      # datové třídy (pydantic)
├── storage/     # perzistence (JSON repository)
├── services/    # business logika
└── ui/          # PySide6 okna a widgety
```

## Vývoj

```bash
pip install -e .[dev]
pytest
ruff check src tests
```

## Licence

[MIT](LICENSE)
