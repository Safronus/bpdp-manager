"""Anglické překlady UI (zdroj = český text v kódu).

Slovník se doplňuje po vlnách — nepřeložený text zůstává česky (bez pádu).
Vlna 1 (2.0.0): hlavní plocha — záložky, toolbar, stromy prací, statistiky,
stavy/enumy.
"""

from __future__ import annotations

EN: dict[str, str] = {
    # ── Enumy: stavy, typy, formy, druhy ─────────────────────────────────
    "Bakalářská práce": "Bachelor's thesis",
    "Diplomová práce": "Master's thesis",
    "Prezenční": "Full-time",
    "Kombinovaná": "Part-time",
    "Interní": "Internal",
    "Externí": "External",
    "Zájemce bez tématu": "Candidate without topic",
    "Zájemce s tématem": "Candidate with topic",
    "Vypsané téma": "Listed topic",
    "V řešení": "In progress",
    "Obhájeno": "Defended",
    "Nedokončeno": "Not completed",
    "Neobhájeno": "Failed defense",
    "Text práce": "Thesis text",
    "Přílohy práce": "Thesis attachments",
    "Text práce + přílohy": "Thesis text + attachments",
    "Pracovní deník": "Work journal",
    "Oficiální zadání": "Official assignment",
    "Posudek vedoucího": "Supervisor's review",
    "Posudek oponenta": "Opponent's review",
    "Prezentace": "Presentation",
    "Soubor s průběhem obhajoby": "Defense record",
    "STAG export (CSV)": "STAG export (CSV)",
    "Jiné": "Other",
    "Neposouzen": "Not assessed",
    "Posouzen — je plagiát": "Assessed — plagiarism",
    "Posouzen — není plagiát": "Assessed — not plagiarism",

    # ── Hlavní okno: záložky ─────────────────────────────────────────────
    "Aktuálně vedené práce": "Currently supervised theses",
    "Práce v dalším akademickém roce": "Theses in the next academic year",
    "Historie": "History",
    "Vše": "All",
    "🧐 Oponované práce": "🧐 Opposed theses",
    "💡 Návrhy témat": "💡 Topic proposals",
    "📅 Harmonogram": "📅 Schedule",
    "📊 Statistiky": "📊 Statistics",

    # ── Hlavní okno: toolbar ─────────────────────────────────────────────
    "➕ Nová práce": "➕ New thesis",  # noqa: RUF001
    "🌱 Zájemce": "🌱 Candidate",
    "🕘 Minulá práce": "🕘 Past thesis",
    "🎓 Studenti": "🎓 Students",
    "🧐 Oponenti": "🧐 Opponents",
    "👔 Vedoucí": "👔 Supervisors",
    "🏷 Obory + sekretářky": "🏷 Programmes + secretaries",
    "🚫 Odmítnutí": "🚫 Rejected",
    "📝 Šablony posudků": "📝 Review templates",
    "✉ Odeslat posudky": "✉ Send reviews",
    "🎓 Posudky vedoucího (vedené práce)…": "🎓 Supervisor's reviews (supervised)…",
    "🧐 Oponentské posudky…": "🧐 Opponent's reviews…",
    "🖨 Tisk posudků": "🖨 Print reviews",
    "📥 Import ze STAG…": "📥 Import from STAG…",
    "📦 Import práce ze ZIP…": "📦 Import thesis from ZIP…",
    "🔄 Aktualizace prací": "🔄 Update theses",
    "🔄 Zkontrolovat změny ve STAG": "🔄 Check STAG changes",
    "🔍 Kontrola se STAG (chybějící soubory)": "🔍 STAG consistency (missing files)",
    "🗂 Přeřadit průběh obhajoby": "🗂 Reclassify defense records",
    "🧹 Úklid duplicitních příloh": "🧹 Clean duplicate attachments",
    "🔧 Náprava zařazení textu/příloh": "🔧 Fix text/attachment classification",
    "🔄 Obnovit": "🔄 Refresh",
    "❓ Nápověda": "❓ Help",
    "Přepnout jazyk aplikace (CZ/EN) — projeví se po restartu.":
        "Switch application language (CZ/EN) — applies after restart.",
    "🔍 Najít práci: stačí kousek jména studenta · názvu · ID (Axxxxx)":
        "🔍 Find thesis: part of student name · title · ID (Axxxxx)",
    "Najít": "Find",

    # ── Stromy prací: hlavičky sloupců ───────────────────────────────────
    "Student / Skupina": "Student / Group",
    "Téma": "Topic",
    "Stav": "Status",
    "Známky V/O": "Grades S/O",
    "Posudky": "Reviews",
    "Plagiát posouzen": "Plagiarism assessed",
    "Odesláno": "Sent",
    "Vytištěno": "Printed",
    "Oponent": "Opponent",
    "Obor": "Programme",
    "Vedoucí": "Supervisor",

    # ── Kontextové akce ──────────────────────────────────────────────────
    "🔄 Aktualizace práce ze STAG…": "🔄 Update thesis from STAG…",
    "📝 Generovat posudek z šablony…": "📝 Generate review from template…",
    "✉ Označit posudky za odeslané": "✉ Mark reviews as sent",

    # ── Statistiky ───────────────────────────────────────────────────────
    "🔄 Přepočítat": "🔄 Recalculate",
    "Souhrn": "Summary",
    "Obory · typ · forma prací": "Programmes · type · form",
    "Podle akademického roku": "By academic year",
    "Známky": "Grades",
    "Vývoj počtu prací po letech": "Theses per year over time",
    "Soubory (přílohy)": "Files (attachments)",
    "Odměny (orientačně)": "Remuneration (estimate)",
    "Všechny roky": "All years",
    "Porovnání": "Comparison",
    "Vedené": "Supervised",
    "Oponované": "Opposed",
    "Vedu já": "Supervised by me",
    "Jsem oponent": "I am the opponent",
    "Oponent mých vedených": "Opponents of my supervised",
    "Vedoucí mých oponovaných": "Supervisors of my opposed",
    "Vedené práce": "Supervised theses",
    "Budoucí": "Future",
    "Oponentury": "Opposed reviews",
    "Studenti": "Students",
    "Odmítnutí": "Rejected",
    "Bakalářské (BP)": "Bachelor's (BP)",
    "Diplomové (DP)": "Master's (DP)",
    "Typ prací": "Thesis types",
    "Forma studia": "Study form",
    "Počet souborů": "File count",
    "Velikost": "Size",
    # ── Vlna 2: detail práce / oponentury ────────────────────────────────
    "Vyberte práci ve stromu vlevo, nebo přidejte novou.":
        "Select a thesis in the tree on the left, or add a new one.",
    "Přechod do stavu": "Transition to status",
    "📋 Souhrn": "📋 Overview",
    "📝 Téma zadání": "📝 Topic & assignment",
    "Poznámky": "Notes",
    "🔍 Plagiátorství": "🔍 Plagiarism",
    "📎 Dokumenty": "📎 Documents",
    "Uložit změny": "Save changes",
    "📝 Napsat posudek…": "📝 Write review…",
    "Smazat": "Delete",
    "Základní info": "Basic info",
    "Typ:": "Type:",
    "Rok:": "Year:",
    "Student:": "Student:",
    "Obor:": "Programme:",
    "Oponent:": "Opponent:",
    "Vypsané téma (název CZ/EN, anotace CZ/EN)":
        "Listed topic (title CZ/EN, annotation CZ/EN)",
    "Název (CZ)": "Title (CZ)",
    "Název (EN)": "Title (EN)",
    "Anotace (CZ)": "Annotation (CZ)",
    "Anotace (EN)": "Annotation (EN)",
    "Anotace": "Annotation",
    "Body zadání": "Assignment objectives",
    "Literární zdroje": "References",
    "Oficiální zadání (body zadání, literatura)":
        "Official assignment (objectives, references)",
    "Poznámky a deník konzultací": "Notes and consultation journal",
    "Dokumenty k práci (posudky, text práce, prezentace, odkazy…)":
        "Thesis documents (reviews, thesis text, presentations, links…)",
    "Komentář k výsledku plagiátorství:": "Plagiarism result comment:",
    "💡 Doporučený komentář": "💡 Suggested comment",
    "PDF protokol o plagiátorství:": "Plagiarism PDF report:",
    "(žádný soubor)": "(no file)",
    "📂 Otevřít": "📂 Open",
    "● Ukládám…": "● Saving…",
    "✓ Uloženo": "✓ Saved",
    "⚠ Chyba ukládání:": "⚠ Save error:",
    "Aktuálně:": "Currently:",
    'Posudek lze psát jen pro práci ve stavu „V řešení".':
        'A review can only be written for a thesis "In progress".',
    "Vedoucí:": "Supervisor:",
    "Oponent (moje):": "Opponent (mine):",

    # ── Vlna 2: dokumenty (widget) ───────────────────────────────────────
    "Zobrazit starší verze (superseded)": "Show older versions (superseded)",
    "📎 Nahrát soubor…": "📎 Upload file…",
    "🔗 Přidat odkaz/URL…": "🔗 Add link/URL…",
    "🗑 Smazat originál po nahrání": "🗑 Delete original after upload",
    "Otevřít": "Open",
    "📂 Ve Finderu": "📂 Show in Finder",
    "Odebrat": "Remove",
    "🧹 Odklidit chybějící": "🧹 Clean up missing",
    "Typ / soubor": "Type / file",
    "Verze": "Version",
    "Formát": "Format",
    "Cesta k souboru": "File path",

    # ── Vlna 2: tooltipy toolbaru ────────────────────────────────────────
    "Vytvoří novou práci. Výchozí stav se odvodí z aktuálního tabu:\n"
    "  Aktuální → V řešení\n  Budoucí → Vypsané téma\n"
    "  Historie → Obhájeno\n  Vše → Vypsané téma":
        "Creates a new thesis. Default status follows the current tab:\n"
        "  Current → In progress\n  Future → Listed topic\n"
        "  History → Defended\n  All → Listed topic",
    "Nová budoucí práce — volitelně rovnou vyplníš studenta, obor, "
    "název a anotaci (nic není povinné). Stav default Vypsané téma.":
        "New future thesis — optionally fill in student, programme, title and "
        "annotation right away (nothing is required). Default status Listed topic.",
    "Rychlý formulář pro historickou práci (vlastní rok + stav).":
        "Quick form for a historical thesis (custom year + status).",
    "Registr vedoucích cizích BP/DP — pro oponentské posudky":
        "Registry of supervisors of others' theses — for opponent reviews",
    "Číselník oborů + sekretářky oborů. Dvojklik na hlavičku sekretářky "
    "upraví její kontakt a oslovení hromadně pro všechny její obory.":
        "Programme list + programme secretaries. Double-click a secretary "
        "header to edit her contact and salutation for all her programmes at once.",
    "Evidence odmítnutých zájemců o vedení (jméno, obor, rok) — "
    "promítá se do Statistik (kapacita vedení).":
        "Registry of rejected supervision candidates (name, programme, year) — "
        "reflected in Statistics (supervision capacity).",
    "Knihovna XLSX šablon posudků (vedoucího / oponenta) — "
    "z kontextu konkrétní práce lze vygenerovat předvyplněný posudek.":
        "Library of XLSX review templates (supervisor / opponent) — a prefilled "
        "review can be generated from a thesis context.",
    "Odeslání připravených posudků sekretářce e-mailem — vyber, zda "
    "posudky vedoucího (vedené práce) nebo oponentské.":
        "Send prepared reviews to the secretary by e-mail — choose supervisor's "
        "reviews (supervised theses) or opponent's reviews.",
    "Vytisknout PDF posudků (vedoucího i oponentské) — přes MyQ "
    "(myq.utb.cz) nebo na systémovou tiskárnu. Vybereš práce a cíl "
    "tisku. Tiskne oboustranně.":
        "Print review PDFs (supervisor's and opponent's) — via MyQ (myq.utb.cz) "
        "or a system printer. Choose theses and destination. Prints double-sided.",
    "Import dat z CSV exportu STAG (getKvalifikacniPrace*.csv) — "
    "vytvoří nebo aktualizuje vedené BP/DP a oponentské posudky.":
        "Import data from a STAG CSV export (getKvalifikacniPrace*.csv) — "
        "creates or updates supervised theses and opponent reviews.",
    "Naimportuje práci z dříve vyexportovaného ZIP balíku (data, stav, "
    "posudky, soubory) — vytvoří novou práci.":
        "Imports a thesis from a previously exported ZIP bundle (data, status, "
        "reviews, files) — creates a new thesis.",
    "Tichá kontrola: změny stavu/souborů + nové práce.":
        "Silent check: status/file changes + new theses.",
    "Najde přílohy se shodným obsahem (duplikáty z opětovného stažení) "
    "a nabídne jejich smazání — s náhledem, co a proč.":
        "Finds attachments with identical content (duplicates from re-download) "
        "and offers to delete them — with a preview of what and why.",
    "Najde práce, kde je archiv (zip) veden jako Text práce — buď "
    "prohozený s PDF přílohou, nebo balík (text+přílohy v zipu) — a "
    "nabídne nápravu.":
        "Finds theses where an archive (zip) is classified as Thesis text — "
        "either swapped with a PDF attachment, or a bundle (text+attachments) — "
        "and offers a fix.",
    "Popis funkcí a jak aplikace funguje (F1).":
        "Description of features and how the app works (F1).",
}
