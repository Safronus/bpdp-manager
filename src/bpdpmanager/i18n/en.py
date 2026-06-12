# ruff: noqa: RUF001 — klíče slovníku MUSÍ přesně odpovídat zdrojovým českým
# textům (vč. „ambiguous" znaků jako ➕, –, ‚'); hodnoty je zrcadlí záměrně.
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
    "➕ Nová práce": "➕ New thesis",
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
    "Vyberte práci v seznamu nahoře, nebo přidejte novou.":
        "Select a thesis in the list above, or add a new one.",
    "Detail práce": "Thesis detail",
    "Detail oponované práce": "Opposed thesis detail",
    "Sbalí/rozbalí detail práce — sbalený detail uvolní místo seznamu prací.":
        "Collapses/expands the thesis detail — a collapsed detail frees space for the list.",
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
    "Některé soubory neexistují:": "Some files do not exist:",
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

    # ── Vlna 3: dialogy (krátké texty) ───────────────────────────────────
    '    Cílová složka': '    Target folder',
    '    Cílový profil': '    Target profile',
    '    Název profilu': '    Profile name',
    '(odvodí se z přípony oboru: -P / -K)': '(derived from programme suffix: -P / -K)',
    '(prázdné = stejné jako e-mail)': '(empty = same as e-mail)',
    '(přípona -P/-K v oboru nenalezena)': '(suffix -P/-K not found in programme)',
    '(žádná sekretářka s e-mailem)': '(no secretary with an e-mail)',
    '(žádné PDF naimportované)': '(no PDF imported)',
    '(žádný jiný profil neexistuje)': '(no other profile exists)',
    '(žádný — začít s prázdnou databází)': '(none — start with an empty database)',
    '+ Nový': '+ New',
    '+ Přidat': '+ Add',
    '+ Přidat rok': '+ Add year',
    '+ Přidat šablonu…': '+ Add template…',
    '+ Přidat…': '+ Add…',
    '+ Termín': '+ Deadline',
    '<b>Kritérium</b>': '<b>Criterion</b>',
    '<b>Váha</b>': '<b>Weight</b>',
    '<i>Co aktualizovat (přepsat z balíku):</i>': '<i>What to update (overwrite from bundle):</i>',
    'Akademický rok': 'Academic year',
    'Akademický rok:': 'Academic year:',
    'Aktivní profil': 'Active profile',
    'Aktualizace dokončena': 'Update finished',
    'Aktualizovat existující práci': 'Update existing thesis',
    'Aktuální akademický rok — zamčeno': 'Current academic year — locked',
    'Body zadání (1 řádek = 1 bod):': 'Assignment objectives (1 line = 1 item):',
    'Celkové hodnocení, připomínky a dotazy': 'Overall evaluation, comments and questions',
    'Cesta ke složce': 'Folder path',
    'Chyba načítání': 'Load error',
    'Chybí cesta': 'Missing path',
    'Chybí cíl': 'Missing target',
    'Chybí e-mail': 'Missing e-mail',
    'Chybí jméno': 'Missing name',
    'Chybí název': 'Missing title',
    'Chybí příjemce': 'Missing recipient',
    'Chybí příjmení': 'Missing surname',
    'Chybí soubor': 'Missing file',
    'Cíl importu': 'Import target',
    'Cílový profil neexistuje.': 'Target profile does not exist.',
    'Cílový soubor existuje': 'Target file exists',
    'Další': 'Next',
    'Databáze zatím neexistuje.': 'Database does not exist yet.',
    'Defaultní obory': 'Default programmes',
    'Defaultní šablony': 'Default templates',
    'Doplnit chybějící': 'Add missing',
    'Doporučený komentář': 'Suggested comment',
    'Dočasné soubory ze STAG': 'Temporary STAG files',
    'Export PDF posudků': 'Export review PDFs',
    'Export dokončen': 'Export finished',
    'Export práce do ZIP — co zahrnout': 'Export thesis to ZIP — what to include',
    'Fallback stav (vedené práce)': 'Fallback status (supervised theses)',
    'Generovat posudek z šablony': 'Generate review from template',
    'Generování posudku': 'Review generation',
    'Generování selhalo': 'Generation failed',
    'Hromadně ze STAG': 'Bulk from STAG',
    'Import dat do aktuálního profilu': 'Import data into the current profile',
    'Import dokončen': 'Import finished',
    'Import nedokončen': 'Import not finished',
    'Import práce ze ZIP': 'Import thesis from ZIP',
    'Import vrácen': 'Import rolled back',
    'Import zrušen': 'Import cancelled',
    'Jak získat CSV s prací ze STAG': 'How to get a thesis CSV from STAG',
    'Jen data (bez příloh)': 'Data only (no attachments)',
    'Jen důležité': 'Important only',
    'Jen moje práce (filtrovat dle celého jména)': 'Only my theses (filter by full name)',
    'Jméno': 'Name',
    'Jméno a příjmení': 'Full name',
    'Jméno:': 'Name:',
    'Komentář už obsahuje text. Přepsat doporučeným zněním?': 'The comment already contains text. Replace with the suggested wording?',
    'Konkrétní datum': 'Specific date',
    'Kopírovat': 'Copy',
    'Kritéria hodnocení (skóre 0–5)': 'Evaluation criteria (score 0–5)',
    'Mazání selhalo': 'Deletion failed',
    'Merge dokončen': 'Merge finished',
    'Místo, datum': 'Place, date',
    'Nahrát soubor': 'Upload file',
    'Nastavení e-mailu (SMTP)': 'E-mail settings (SMTP)',
    'Načti CSV soubor pro náhled.': 'Load a CSV file for preview.',
    'Nejdřív vyber akademický rok.': 'Select an academic year first.',
    'Nenalezena žádná práce. Zkontroluj příjmení (i diakritiku).': 'No thesis found. Check the surname (including diacritics).',
    'Nenávratně smaže posudek z databáze a všechny jeho soubory.': 'Irreversibly deletes the review from the database including all its files.',
    'Není aktivní žádný profil.': 'No profile is active.',
    'Není otevřený žádný profil.': 'No profile is open.',
    'Neočekávaná chyba': 'Unexpected error',
    'Neplatný rok': 'Invalid year',
    'Neplatný soubor': 'Invalid file',
    'Nevybral jsi žádný posudek k tisku.': 'No review selected for printing.',
    'Nevybrali jste žádnou práci.': 'No thesis selected.',
    'Nic není vybráno k opravě.': 'Nothing selected to fix.',
    'Novinky od tvé verze:': "What's new since your version:",
    'Nová budoucí práce': 'New future thesis',
    'Nový profil': 'New profile',
    'Nový…': 'New…',
    'Nyní': 'Now',
    'Náprava zařazení textu a příloh': 'Fix text/attachment classification',
    'Název': 'Title',
    'Název oboru': 'Programme name',
    'Název profilu v registry — předvyplní se z manifestu': 'Profile name in the registry — prefilled from the manifest',
    'Název tématu:': 'Topic title:',
    'Obnovit zálohu': 'Restore backup',
    'Obor (nepovinné)': 'Programme (optional)',
    'Obor / Sekretářka': 'Programme / Secretary',
    'Obor neodpovídá žádnému oboru sekretářky.': "The programme does not match any of the secretary's programmes.",
    'Obory + sekretářky': 'Programmes + secretaries',
    'Oboustranně': 'Double-sided',
    'Odebrat vybrané': 'Remove selected',
    'Odeslání': 'Sending',
    'Odeslání přes SMTP selhalo': 'Sending via SMTP failed',
    'Odesílatel': 'Sender',
    'Odkaz/URL nelze zobrazit ve správci souborů.': 'A link/URL cannot be shown in the file manager.',
    'Odklidit chybějící': 'Clean up missing',
    'Odkud stáhnout CSV ze STAG': 'Where to download the STAG CSV',
    'Odmítnutí zájemci': 'Rejected candidates',
    'Oponuje prací': 'Opposes theses',
    'Oslovení': 'Salutation',
    'Oslovení v mailu': 'E-mail salutation',
    'Osobní č.': 'Personal no.',
    'Osobní číslo (UTB)': 'Personal number (UTB)',
    'Otevře nahraný text práce (PDF), je-li k dispozici.': 'Opens the uploaded thesis text (PDF), if available.',
    'Otevře protější posudek (PDF/soubor), je-li k dispozici.': 'Opens the counterpart review (PDF/file), if available.',
    'Otevřel jsem připravený e-mail v tvém mailovém klientovi.': 'The prepared e-mail was opened in your mail client.',
    'Otevřeno v mailu': 'Opened in mail',
    'Otevřít PDF': 'Open PDF',
    'Otevřít složku': 'Open folder',
    'Otevřít stejně': 'Open anyway',
    'Ověřit TLS certifikát serveru': 'Verify the server TLS certificate',
    'Označení': 'Marking',
    'Označit jako důležitý termín': 'Mark as an important deadline',
    'Označit jako vytištěné?': 'Mark as printed?',
    'Poslední otevření': 'Last opened',
    'Posudek vygenerován': 'Review generated',
    'Posudek vyrobený': 'Review produced',
    'Potvrď smazání': 'Confirm deletion',
    'Později': 'Later',
    'Poznámka': 'Note',
    'Počkej, než doběhne odesílání na tisk.': 'Wait until printing finishes.',
    'Pracoviště': 'Department',
    'Pracoviště / firma': 'Department / company',
    'Pro tento rok není naimportované žádné PDF.': 'No PDF imported for this year.',
    'Procházet…': 'Browse…',
    'Profil je otevřený jinde': 'Profile is open elsewhere',
    'Práce': 'Thesis',
    'Práce / dokument': 'Thesis / document',
    'Přechod stavu': 'Status transition',
    'Před nahráním dokumentu nejdřív uložte rozpracovanou práci.': 'Save the thesis before uploading a document.',
    'Předmět': 'Subject',
    'Předmět:': 'Subject:',
    'Přejmenovat…': 'Rename…',
    'Přejmenování selhalo': 'Rename failed',
    'Přepnutí profilu': 'Profile switch',
    'Přepsat komentář': 'Replace comment',
    'Přeskočit revizi?': 'Skip review?',
    'Přeskočit soubory': 'Skip files',
    'Přeskočit tuto verzi': 'Skip this version',
    'Přeskočit velké': 'Skip large',
    'Převést na vedenou práci': 'Convert to a supervised thesis',
    'Přeřadit průběh obhajoby (ze STAG)': 'Reclassify defense records (from STAG)',
    'Při doplnění přepsat i lišící se STAG kódy': 'When adding, also overwrite differing STAG codes',
    'Při doplnění přepsat i stejnojmenné existující': 'When adding, also overwrite same-named existing ones',
    'Při importu nastaly chyby': 'Errors occurred during import',
    'Přidat minulou práci': 'Add a past thesis',
    'Přidání selhalo': 'Adding failed',
    'Přihlašovací jméno': 'Login name',
    'Připojit popisek o aplikaci (BPDPManager)': 'Append a note about the app (BPDPManager)',
    'Příjemce': 'Recipient',
    'Příjmení': 'Surname',
    'Příjmení studenta': "Student's surname",
    'Příjmení vedoucího/oponenta': "Supervisor's/opponent's surname",
    'Příjmení, Jméno': 'Surname, Name',
    'Příště nezobrazovat tento průvodce': "Don't show this guide again",
    'Původní název souboru ze STAG': 'Original file name from STAG',
    'Roll-back oponentského posudku': 'Opponent review roll-back',
    'Roll-back vedené práce': 'Supervised thesis roll-back',
    'Roll-back více posudků': 'Roll-back of multiple reviews',
    'Roll-back více prací': 'Roll-back of multiple theses',
    'Rozpracovaný posudek': 'Draft review',
    'Rozumím, jdeme na to': "Got it, let's go",
    'Rychlá ruční záloha aktuálního stavu databáze.': 'Quick manual backup of the current database state.',
    'STAG kód': 'STAG code',
    'STAG kód (pro import — např. knIT-KYB, volitelné)': 'STAG code (for import — e.g. knIT-KYB, optional)',
    'STAG — detaily prací': 'STAG — thesis details',
    'STAG — některé přílohy se nestáhly': 'STAG — some attachments failed to download',
    'STAG — některé soubory se nestáhly': 'STAG — some files failed to download',
    'STAG — přílohy': 'STAG — attachments',
    'Sekretářka': 'Secretary',
    'Sekretářka oboru (volitelné)': 'Programme secretary (optional)',
    'Sekretářka — hromadná úprava': 'Secretary — bulk edit',
    'Sestaví text znovu podle aktuálně vybraných prací.': 'Rebuilds the text from the currently selected theses.',
    'Skenování šablony': 'Template scan',
    'Skrýt historické studenty': 'Hide historical students',
    'Skrýt proužek': 'Hide banner',
    'Skrýt už uplynulé': 'Hide past ones',
    'Slovní zhodnocení práce, dotazy k obhajobě…': 'Verbal evaluation of the thesis, questions for the defense…',
    'Složka neexistuje': 'Folder does not exist',
    'Složka záloh ještě neexistuje.': 'Backup folder does not exist yet.',
    'Smazat návrh': 'Delete proposal',
    'Smazat práci': 'Delete thesis',
    'Smazat termín': 'Delete deadline',
    'Smazat vedoucího': 'Delete supervisor',
    'Smazat vše a nahradit': 'Delete all and replace',
    'Smazat zálohu': 'Delete backup',
    'Smazat šablonu': 'Delete template',
    'Soubor chybí': 'File missing',
    'Soubory ke stažení ze STAG': 'Files to download from STAG',
    'Souhrn exportu posudků': 'Review export summary',
    'Souhrn před importem': 'Summary before import',
    'Splnění všech bodů zadání': 'Fulfilment of all assignment objectives',
    'Správa profilů': 'Profile management',
    'Stahování ze STAG': 'Downloading from STAG',
    'Stahování zrušeno.': 'Download cancelled.',
    'Stahuji přílohy…': 'Downloading attachments…',
    'Stahuji slovník…': 'Downloading dictionary…',
    'Stav databáze byl obnoven do podoby před importem.': 'The database was restored to its pre-import state.',
    'Stažené CSV neobsahuje žádná data.': 'The downloaded CSV contains no data.',
    'Stažení slovníku': 'Dictionary download',
    'Studentů': 'Students',
    'Stáhnout práci ze STAG': 'Download thesis from STAG',
    'Systémová tiskárna': 'System printer',
    'Systémový tisk není dostupný (chybí CUPS/lp nebo tiskárna).': 'System printing is not available (missing CUPS/lp or printer).',
    'Termín v harmonogramu': 'Schedule deadline',
    'Test spojení': 'Connection test',
    'Testovací e-mail odeslán': 'Test e-mail sent',
    'Testovací e-mail otevřen': 'Test e-mail opened',
    'Text e-mailu (náhled — lze upravit):': 'E-mail text (preview — editable):',
    'Tisk posudků': 'Print reviews',
    'Tisk posudků — chyba přihlášení': 'Print reviews — login error',
    'Tisknout přes:': 'Print via:',
    'Tiskárna:': 'Printer:',
    'Tituly před': 'Titles before',
    'Tvoje jméno': 'Your name',
    'Tvoje jméno a tituly': 'Your name and titles',
    'Tvůj e-mail (odesílatel)': 'Your e-mail (sender)',
    'Typ práce': 'Thesis type',
    'Uloženo': 'Saved',
    'Uložení': 'Save',
    'Uložení dat selhalo': 'Saving data failed',
    'Uložení selhalo': 'Save failed',
    'V balíčku nejsou žádné výchozí šablony.': 'The bundle contains no default templates.',
    'Vedoucí (pro oponentské posudky)': 'Supervisors (for opponent reviews)',
    'Velké přílohy ze STAG': 'Large attachments from STAG',
    'Velké stahování příloh': 'Large attachment download',
    'Volitelná poznámka — např. zdroj, datum verze…': 'Optional note — e.g. source, version date…',
    'Volný popis data': 'Free-form date description',
    'Vráceno': 'Rolled back',
    'Vrácení selhalo': 'Rollback failed',
    'Vrátit celý import?': 'Roll back the whole import?',
    'Vyber XLSX šablonu.': 'Select an XLSX template.',
    'Vyber cílovou složku pro data profilu.': 'Select a target folder for profile data.',
    'Vyber cílový .zip soubor.': 'Select a target .zip file.',
    'Vyber cílový profil v combo boxu.': 'Select a target profile in the combo box.',
    'Vyber nejdřív CSV soubor.': 'Select a CSV file first.',
    'Vyber posudek v seznamu nahoře, nebo přidej nový.': 'Select a review in the list above, or add a new one.',
    'Vyber sekretářku.': 'Select a secretary.',
    'Vyber složku pro data profilu.': 'Select a folder for profile data.',
    'Vyber systémovou tiskárnu.': 'Select a system printer.',
    'Vyber v seznamu profil, kterému chceš nastavit e-mail.': 'Select the profile whose e-mail you want to set.',
    'Vyber v seznamu profil, kterému chceš nastavit jméno.': 'Select the profile whose name you want to set.',
    'Vybrané práce nemají PDF oponentského posudku k tisku.': 'The selected theses have no opponent review PDF to print.',
    'Vybrané práce nemají PDF posudku vedoucího k tisku.': 'The selected theses have no supervisor review PDF to print.',
    'Vybrat vše': 'Select all',
    'Vyexportuje vybraný profil do přenosného ZIP balíku.': 'Exports the selected profile into a portable ZIP bundle.',
    'Vytvoření selhalo': 'Creation failed',
    'Vytvořit novou práci': 'Create a new thesis',
    'Vytvořit profil': 'Create profile',
    'Vytvoří ruční zálohu aktuálního stavu databáze.': 'Creates a manual backup of the current database state.',
    'Vítej v BPDPManageru — Začínáme': 'Welcome to BPDPManager — Getting started',
    'Vítejte v BPDPManager': 'Welcome to BPDPManager',
    'Vítejte v BPDPManager 👋': 'Welcome to BPDPManager 👋',
    'Výsledek kontroly plagiátorství (jen pro vedoucího)': 'Plagiarism check result (supervisor only)',
    'Všechny obory': 'All programmes',
    'Všechny známky': 'All grades',
    'Všichni oponenti': 'All opponents',
    'Zabezpečení': 'Security',
    'Zadej alespoň jméno.': 'Enter at least a name.',
    'Zadej e-mail (nebo přihlašovací jméno) před testem spojení.': 'Enter an e-mail (or login name) before testing the connection.',
    'Zadej e-mail příjemce.': "Enter the recipient's e-mail.",
    'Zadej název profilu.': 'Enter a profile name.',
    'Zadej název šablony.': 'Enter a template name.',
    'Zadej přihlašovací jméno i PIN do MyQ.': 'Enter both the MyQ login name and PIN.',
    'Zadej příjmení a klikni na „Vyhledat ve STAG".': 'Enter a surname and click "Search in STAG".',
    'Založit nového studenta (vč. oboru).': 'Create a new student (incl. programme).',
    'Zarezervováno': 'Reserved',
    'Zavřít': 'Close',
    'Zdrojový XLSX': 'Source XLSX',
    'Zdůvodnění': 'Justification',
    'Zdůvodnění (% shody, kontext, …)': 'Justification (% match, context, …)',
    'letošní hotové práce': "this year's completed theses",
    'Změny byly vráceny ze zálohy.': 'Changes were restored from the backup.',
    'Změny ve STAG — náhled': 'STAG changes — preview',
    '🔄 Aktualizovat vedené ({n})…': '🔄 Update supervised ({n})…',
    '🔄 Aktualizovat oponované ({n})…': '🔄 Update opposed ({n})…',
    'Otevře aktualizaci ze STAG jen pro vedené práce se zjištěnou změnou — návrhy (stav, soubory) budou rovnou předpřipravené.': 'Opens the STAG update for the supervised theses with detected changes only — proposals (status, files) come pre-filled.',
    'Otevře aktualizaci ze STAG jen pro oponované práce se zjištěnou změnou — návrhy (stav, soubory) budou rovnou předpřipravené.': 'Opens the STAG update for the opposed theses with detected changes only — proposals (status, files) come pre-filled.',
    'Pro NOVÉ práce ze STAG, které ještě nemáš v aplikaci — otevře plný import (vyhledání + stažení).': 'For NEW theses from STAG you do not have in the app yet — opens the full import (search + download).',
    'Známka:': 'Grade:',
    'Zobrazit i práce, jejichž obor neodpovídá sekretářce': 'Also show theses whose programme does not match the secretary',
    'Zobrazit i už odeslané posudky': 'Also show already sent reviews',
    'Zobrazit i šablony jiných oborů': 'Also show templates of other programmes',
    'Zrušit': 'Cancel',
    'Zrušit vše': 'Deselect all',
    'Záloha': 'Backup',
    'Záloha selhala': 'Backup failed',
    'Záloha vytvořena': 'Backup created',
    'Zálohy databáze': 'Database backups',
    'cesta k cílovému .zip souboru': 'path to the target .zip file',
    'cílová složka, kam rozbalit data': 'target folder to extract data into',
    'filtr podle příjmení…': 'filter by surname…',
    'jméno / poznámka (volný text)': 'name / note (free text)',
    'napiš výraz a stiskni Enter…': 'type a phrase and press Enter…',
    'např. 12.3': 'e.g. 12.3',
    'např. 2024/2025': 'e.g. 2024/2025',
    'např. 2025/2026 (volitelné)': 'e.g. 2025/2026 (optional)',
    'např. A24390': 'e.g. A24390',
    'např. NSWI-P': 'e.g. NSWI-P',
    'např. Petr Novák': 'e.g. Petr Novák',
    'např. Petr Žáček': 'e.g. Petr Žáček',
    'např. Ph.D.': 'e.g. Ph.D.',
    'např. Pohanka (nepovinné při hledání dle vedoucího)': 'e.g. Smith (optional when searching by supervisor)',
    'např. Vedoucí DP — SWI 2025/2026': 'e.g. Supervisor DP — SWI 2025/2026',
    'např. Vážená paní Nováková  (prázdné = formální oslovení)': 'e.g. Dear Mrs Novak  (empty = formal salutation)',
    'např. Vážená paní Nováková (prázdné = formální)': 'e.g. Dear Mrs Novak (empty = formal)',
    'např. Zlín, 26. 5. 2026': 'e.g. Zlín, 26 May 2026',
    'např. doc. Ing.': 'e.g. doc. Ing.',
    'např. květen-červen 2027': 'e.g. May–June 2027',
    'např. prijmeni@utb.cz': 'e.g. surname@utb.cz',
    'např. Žáček (tvoje příjmení) — bez studenta najde VŠE': 'e.g. Žáček (your surname) — without a student it finds EVERYTHING',
    'např. „FAI UTB — osobní“': 'e.g. "FAI UTB — personal"',
    'příjemce@example.cz': 'recipient@example.com',
    'tvé příjmení z profilu': 'your surname from the profile',
    'uživatelské jméno MyQ': 'MyQ user name',
    'vyber .zip vytvořený přes Export profilu': 'select a .zip created via Profile export',
    'vyber CSV soubor exportovaný ze STAG': 'select a CSV file exported from STAG',
    'vyber XLSX šablonu posudku': 'select an XLSX review template',
    'vyber složku, kam se uloží db.json a další': 'select a folder where db.json and more will be stored',
    'Úklid titulů': 'Title cleanup',
    'Čas vytvoření': 'Created at',
    'Šablona': 'Template',
    'Šablona / Obor': 'Template / Programme',
    'Šablona nebyla nalezena.': 'Template not found.',
    'Šablony posudků': 'Review templates',
    'Žádné PDF není nahrané.': 'No PDF uploaded.',
    'Žádné soubory nebyly vybrány k importu.': 'No files selected for import.',
    'Žádný aktivní profil': 'No active profile',
    'Žádný db.json': 'No db.json',
    'Žádný vybraný rok.': 'No year selected.',
    'Žádný z vybraných souborů neexistuje.': 'None of the selected files exists.',
    '↕ Sbalit / rozbalit vše': '↕ Collapse / expand all',
    '↩ Vrátit celý import zpět': '↩ Roll back the whole import',
    '↩ Vrátit vše': '↩ Roll back all',
    '↩ Zrušit import (rollback)': '↩ Cancel import (rollback)',
    '↻ Přegenerovat text': '↻ Regenerate text',
    '⏳ Dotahuji seznam souborů ze STAG…': '⏳ Fetching file list from STAG…',
    '⏳ Hledám ve STAG…': '⏳ Searching STAG…',
    '⏳ Porovnávám se STAG…': '⏳ Comparing with STAG…',
    '⏳ Stahuji aktualizaci (git pull + závislosti)…': '⏳ Downloading update (git pull + dependencies)…',
    '⏳ Testuji spojení…': '⏳ Testing connection…',
    '⏳ Zjišťuji stav prací ve STAG…': '⏳ Checking thesis status in STAG…',
    'ⓘ Stahuji český slovník z LibreOffice…': 'ⓘ Downloading the Czech dictionary from LibreOffice…',
    '☑ Vše': '☑ All',
    '⚙ Nastavení e-mailu…': '⚙ E-mail settings…',
    '⚠ Neočekávaná chyba.': '⚠ Unexpected error.',
    '⚠ Přepsat existující data v cílové složce': '⚠ Overwrite existing data in the target folder',
    '⚠ Roli se nepodařilo auto-detekovat — překontroluj ji.': '⚠ The role could not be auto-detected — please check it.',
    '⚠ Smazat i složku s daty': '⚠ Also delete the data folder',
    '⚠ Stahování přerušeno, dočasné soubory uklizeny.': '⚠ Download interrupted, temporary files cleaned up.',
    '⚠ Vyhledávání se nezdařilo.': '⚠ Search failed.',
    '✉ Nastavení e-mailu (SMTP)': '✉ E-mail settings (SMTP)',
    '✉ Nastavení e-mailu (SMTP)…': '✉ E-mail settings (SMTP)…',
    '✉ Označit posudek za odeslaný sekretářce': '✉ Mark review as sent to the secretary',
    '✉ Zrušit označení odeslání': '✉ Unmark as sent',
    '✉ Zrušit označení odeslání posudku': '✉ Unmark review as sent',
    '✎ Před založením zkontrolovat / doplnit nové studenty': '✎ Check / complete new students before creating',
    '✏ Pokračovat v datech': '✏ Continue editing data',
    '✓ Aktualizovat vybrané': '✓ Update selected',
    '✓ Importovat vybrané': '✓ Import selected',
    '✓ Provést import': '✓ Run import',
    '✓ Přeřadit zaškrtnuté': '✓ Reclassify checked',
    '✓ Slovník stažen — kontrola pravopisu zapnuta.': '✓ Dictionary downloaded — spell checking enabled.',
    '✓ Spojení i přihlášení v pořádku.': '✓ Connection and login OK.',
    '✓ Uložit i tak (jen úspěšné řádky)': '✓ Save anyway (successful rows only)',
    '✓ Vytvořit novou': '✓ Create new',
    '✗ Přeskočit': '✗ Skip',
    '❌ Neočekávaná chyba.': '❌ Unexpected error.',
    '❌ Spojení selhalo.': '❌ Connection failed.',
    '❓ Odkud stáhnout': '❓ Where to download',
    '➕  Vytvořit nový profil…': '➕  Create a new profile…',
    '➕ Nový návrh': '➕ New proposal',
    '➕ Nový obor…': '➕ New programme…',
    '➕ Nový profil…': '➕ New profile…',
    '⬇ Dostáhnout vybrané': '⬇ Download selected (missing)',
    '⬇ Stáhnout i tak': '⬇ Download anyway',
    '⬇ Stáhnout přílohy': '⬇ Download attachments',
    '⬇ Stáhnout vybrané': '⬇ Download selected',
    '⬇ Stáhnout český slovník': '⬇ Download the Czech dictionary',
    '⭐ Defaultní…': '⭐ Defaults…',
    '🆕 Najít nové práce…': '🆕 Find new theses…',
    '🆕 Nový prázdný profil': '🆕 New empty profile',
    '🆕 Vytvořit nový profil': '🆕 Create a new profile',
    '🆕 Začít znovu': '🆕 Start over',
    '🇨🇿 Čeština (CZ)': '🇨🇿 Czech (CZ)',
    '🌐 Stáhnout práci ze STAG': '🌐 Download thesis from STAG',
    '🌐 Stáhnout ze STAG': '🌐 Download from STAG',
    '🎓 Moje vedené práce…': '🎓 My supervised theses…',
    '🎓 Převést na vedenou práci': '🎓 Convert to a supervised thesis',
    '🎓 Vedoucí': '🎓 Supervisor',
    '🎓 Vedu já': '🎓 Supervised by me',
    '👁 Zobrazit práci': '👁 Show thesis',
    '👋 Vítej! Pár kroků, než začneš': '👋 Welcome! A few steps before you start',
    '👤 Tvoje jméno a tituly…': '👤 Your name and titles…',
    '💾 Krátkodobá záloha db.json.bak': '💾 Short-term backup db.json.bak',
    '💾 Uložit': '💾 Save',
    '💾 Uložit (jen data)': '💾 Save (data only)',
    '💾 Zálohovat teď': '💾 Back up now',
    '💾 Zálohy…': '💾 Backups…',
    '📁  Otevřít složku…': '📁  Open folder…',
    '📂 Otevřít existující profil': '📂 Open an existing profile',
    '📂 Otevřít existující složku…': '📂 Open an existing folder…',
    '📂 Otevřít složku': '📂 Open folder',
    '📂 Otevřít složku záloh': '📂 Open backup folder',
    '📂 Otevřít v Excelu': '📂 Open in Excel',
    '📂 Ukázat ve Finderu': '📂 Show in Finder',
    '📄 Otevřít XLSX': '📄 Open XLSX',
    '📄 Otevřít text práce': '📄 Open thesis text',
    '📄 Otevřít v Excelu': '📄 Open in Excel',
    '📅 Naimportované PDF harmonogramy': '📅 Imported PDF schedules',
    '📋 Kopírovat soubor (do schránky)': '📋 Copy file (to clipboard)',
    '📋 Souhrn před importem': '📋 Summary before import',
    '📍 Místo posudku…': '📍 Review place…',
    '📎 Dokumenty (posudky, text práce, prezentace…)': '📎 Documents (reviews, thesis text, presentations…)',
    '📎 Dokumenty (přílohy k pracem)': '📎 Documents (thesis attachments)',
    '📎 Soubory práce ze STAG': '📎 Thesis files from STAG',
    '📎 Stáhnout jen soubory': '📎 Download files only',
    '📕 Otevřít PDF': '📕 Open PDF',
    '📕 Otevřít posudek oponenta': "📕 Open opponent's review",
    '📕 Otevřít posudek oponenta (můj)': "📕 Open opponent's review (mine)",
    '📖 Otevřít plnou nápovědu': '📖 Open full help',
    '📘 Otevřít posudek vedoucího': "📘 Open supervisor's review",
    '📘 Otevřít posudek vedoucího (můj)': "📘 Open supervisor's review (mine)",
    '📝 Generovat posudek z šablony': '📝 Generate review from template',
    '📝 Uložit & vyrobit XLSX (PDF chybí soffice)': '📝 Save & produce XLSX (PDF needs soffice)',
    '📝 Uložit & vyrobit XLSX + PDF': '📝 Save & produce XLSX + PDF',
    '📝 Vyplnit a připojit k práci': '📝 Fill in and attach to the thesis',
    '📝 Šablony posudků (XLSX knihovna)': '📝 Review templates (XLSX library)',
    '📤 Export profilu do ZIP balíku': '📤 Export profile to a ZIP bundle',
    '📤 Exportovat aktuální profil do ZIPu…': '📤 Export current profile to ZIP…',
    '📥 Import dat do aktuálního profilu': '📥 Import data into the current profile',
    '📥 Import ze STAG dokončen': '📥 Import from STAG finished',
    '📥 Importovat z jiného profilu do aktuálního…': '📥 Import from another profile into the current one…',
    '📥 Importovat ze ZIP balíku': '📥 Import from a ZIP bundle',
    '📥 Otevřít Import ze STAG…': '📥 Open Import from STAG…',
    '📥 Provést import': '📥 Run import',
    '📦  Importovat jako profil „Výchozí“': '📦  Import as profile "Default"',
    '📦 Exportovat práci do ZIP…': '📦 Export thesis to ZIP…',
    '🔀 Provést merge': '🔀 Run merge',
    '🔀 Sloučit s existujícím profilem (add-only merge)': '🔀 Merge into an existing profile (add-only merge)',
    '🔄 Aktualizovat práce k oponování ze STAG': '🔄 Update opposed theses from STAG',
    '🔄 Aktualizovat práce v řešení ze STAG': '🔄 Update in-progress theses from STAG',
    '🔄 Importovat (přepsat aktuální data)': '🔄 Import (overwrite current data)',
    '🔄 Obnovit vybranou zálohu': '🔄 Restore selected backup',
    '🔄 Rotující 10× zálohy (typicky netřeba — pojistka)': '🔄 Rotating 10× backups (usually not needed — safety net)',
    '🔌 Test spojení': '🔌 Connection test',
    '🔍 Nalezena stávající data': '🔍 Existing data found',
    '🔍 Načíst náhled': '🔍 Load preview',
    '🔍 Ukázat ve Finderu': '🔍 Show in Finder',
    '🔎 Detail vybraného řádku': '🔎 Selected row detail',
    '🔎 Příjmení:': '🔎 Surname:',
    '🔧 Opravit vybrané': '🔧 Fix selected',
    '🖨 Označit posudek za vytištěný': '🖨 Mark review as printed',
    '🖨 Označit posudky za vytištěné': '🖨 Mark reviews as printed',
    '🖨 Zrušit označení vytištění': '🖨 Unmark as printed',
    '🖨 Zrušit označení vytištění posudku': '🖨 Unmark review as printed',
    '🗂  db.json (hlavní databáze) — PŘEPÍŠE aktuální obsah': '🗂  db.json (main database) — OVERWRITES current content',
    '🗂 Správa profilů…': '🗂 Profile management…',
    '🗑 Po dokončení importu smazat originální CSV': '🗑 Delete the original CSV after the import finishes',
    '🗑 Roll-back — kompletní smazání': '🗑 Roll-back — complete deletion',
    '🗑 Roll-back — smazat kompletně…': '🗑 Roll-back — delete completely…',
    '🗑 Smazat kompletně': '🗑 Delete completely',
    '🗑 Smazat návrh': '🗑 Delete proposal',
    '🦴 Vložit kostru posudku': '🦴 Insert review skeleton',
    '🧪 Test — poslat jen sobě': '🧪 Test — send only to myself',

    # ── Vlna 3: dialogy (dlouhé texty) ───────────────────────────────────
    "<b>Nejrychleji:</b> použij tlačítko <b>🌐 Stáhnout ze STAG</b> — práci najde a CSV stáhne přímo (stačí příjmení studenta + vedoucího/oponenta).<hr><b>Nebo ručně z webu STAG:</b><ol><li>Otevři <a href='https://stag.utb.cz'>stag.utb.cz</a></li><li>Sekce <b>Prohlížení</b> → <b>Kvalifikační práce</b></li><li>Vyhledej práci podle <b>jména studenta</b></li><li>U nalezené práce zvol <b>stažení CSV</b></li></ol><p>Stažený soubor (<code>getKvalifikacniPrace*.csv</code>) pak vyber tlačítkem <i>Procházet…</i>.</p><p style='color:#888;font-size:11px;'>Záznam kvalifikační práce je veřejný, takže ke stažení obvykle není potřeba přihlášení.</p>":
        "<b>Fastest:</b> use the <b>🌐 Download from STAG</b> button — it finds the thesis and downloads the CSV directly (student's + supervisor's/opponent's surname is enough).<hr><b>Or manually from the STAG website:</b><ol><li>Open <a href='https://stag.utb.cz'>stag.utb.cz</a></li><li>Section <b>Browse</b> → <b>Qualification theses</b></li><li>Find the thesis by the <b>student's name</b></li><li>Choose <b>download CSV</b> for the found thesis</li></ol><p>Then select the downloaded file (<code>getKvalifikacniPrace*.csv</code>) via <i>Browse…</i>.</p><p style='color:#888;font-size:11px;'>Qualification thesis records are public, so no login is usually needed.</p>",
    '<b>⚠ Pozor:</b> Aktuální data v cílovém profilu budou přepsána (db.json) nebo doplněna (dokumenty / harmonogramy). <b>Před přepsáním se automaticky vytvoří záloha aktuálního stavu</b> se značkou <code>before-import</code> ve složce <code>backups/</code> — takže se dá vrátit přes <i>👤 → 💾 Zálohy</i>.':
        '<b>⚠ Warning:</b> Current data in the target profile will be overwritten (db.json) or extended (documents / schedules). <b>A backup of the current state is created automatically before overwriting</b> with the tag <code>before-import</code> in <code>backups/</code> — so you can roll back via <i>👤 → 💾 Backups</i>.',
    '<i>V databázi není odpovídající práce — bude vytvořena nová.</i>':
        '<i>No matching thesis in the database — a new one will be created.</i>',
    '<small><i>Add-only: do cílového profilu se přidají entity (studenti / oponenti / práce / šablony…), které tam nejsou; existující se <b>nemění</b>. Soubory se zkopírují, pokud cílový název ještě neexistuje. Před zápisem uvidíš preview, co se přidá a co se přeskočí.</i></small>':
        '<small><i>Add-only: entities missing in the target profile (students / opponents / theses / templates…) are added; existing ones are <b>not modified</b>. Files are copied if the target name does not exist yet. You will see a preview of what gets added and what gets skipped.</i></small>',
    '<small><i>Použije se jen pro řádky, kde CSV neobsahuje <code>datumZadani</code>/<code>datumOdevzdani</code>/<code>datumObhajoby</code>. Reálný stav per řádek určí heuristika nad dat z CSV (lze ručně přepsat v náhledu).</i></small>':
        '<small><i>Used only for rows where the CSV lacks <code>datumZadani</code>/<code>datumOdevzdani</code>/<code>datumObhajoby</code>. The real per-row status is determined by a heuristic over the CSV data (can be overridden in the preview).</i></small>',
    '<small><i>Použije se k auto-detekci role: pokud se najde v `vedouciJmeno` → ‚Vedu‘, v `oponentJmeno` → ‚Oponuji‘. Per řádek lze přepsat v náhledu.</i></small>':
        "<small><i>Used for role auto-detection: if found in `vedouciJmeno` → 'I supervise', in `oponentJmeno` → 'I oppose'. Can be overridden per row in the preview.</i></small>",
    '<small><i>Šablona se zkopíruje do <code>profile_dir/templates/</code>. Originál zůstane nedotčený. Stejný XLSX lze přidat víckrát s různými metadaty (např. CZ + EN varianta, nebo BP + DP).</i></small>':
        '<small><i>The template is copied into <code>profile_dir/templates/</code>. The original stays untouched. The same XLSX can be added multiple times with different metadata (e.g. CZ + EN variant, or BP + DP).</i></small>',
    '<span style="color:#1565c0">●</span> aktuální rok &nbsp;&nbsp; <span style="color:#00897b">●</span> budoucí rok &nbsp;&nbsp; <span style="color:#888">●</span> dokončeno &nbsp;&nbsp; <span style="color:#c62828">●</span> nedokončeno':
        '<span style="color:#1565c0">●</span> current year &nbsp;&nbsp; <span style="color:#00897b">●</span> future year &nbsp;&nbsp; <span style="color:#888">●</span> finished &nbsp;&nbsp; <span style="color:#c62828">●</span> not completed',
    'Aktualizuje jen STAV prací ze STAG (bez stahování souborů) u prací, které už máš v databázi. Vedené práce: stav (Obhájeno / Neobhájeno / Nedokončeno / …); oponentury: stav práce ve STAG. Rychlé — vyřeší i přeřazení Nedokončeno → Neobhájeno.':
        'Updates only the STATUS of theses from STAG (no file downloads) for theses you already have in the database. Supervised theses: status (Defended / Failed defense / Not completed / …); opposed theses: STAG status. Fast — also handles reclassifying Not completed → Failed defense.',
    'Aplikace má přibalený chybějící mezilehlý certifikát (GÉANT/HARICA), takže ověření MyQ obvykle projde. Když by přesto selhalo, tisk se automaticky připojí i bez ověření (MyQ je interní univerzitní server).':
        'The app bundles the missing intermediate certificate (GÉANT/HARICA), so MyQ verification usually passes. If it still fails, printing automatically reconnects without verification (MyQ is an internal university server).',
    'Aplikace si potřebuje vybrat, kde má uložená data. Můžeš mít víc datových profilů (např. osobní, sdílený…) a kdykoli mezi nimi přepínat.':
        'The app needs to know where its data is stored. You can have multiple data profiles (e.g. personal, shared…) and switch between them at any time.',
    'Body zadání  —  každý bod na nové řádce, číslování se přidá automaticky v Souhrnu.':
        'Assignment objectives — one item per line; numbering is added automatically in the Overview.',
    'Dokumenty k oponentskému posudku (plný text práce, posudek vedoucího, tvůj posudek oponenta, příp. další):':
        "Documents for the opponent review (full thesis text, supervisor's review, your opponent review, and more):",
    'Doplní výchozí obory FAI UTB (vč. STAG zkratek). Existující nechá být; jen se zeptá, jestli přepsat lišící se STAG kódy.':
        'Adds the default FAI UTB programmes (incl. STAG codes). Existing ones are kept; you are only asked whether to overwrite differing STAG codes.',
    'Doplní výchozí šablony posudků FAI UTB (BP/DP, vedoucí/oponent, CZ/EN, podle oboru). Existující nechá být; volitelně přepíše.':
        'Adds the default FAI UTB review templates (BP/DP, supervisor/opponent, CZ/EN, per programme). Existing ones are kept; optionally overwritten.',
    'Dotáhnu ze STAG původní názvy příloh typu <b>Jiné</b> a nabídnu přeřazení na <b>Soubor s průběhem obhajoby</b>. Soubory, které vypadají jako protokol/zápis o obhajobě, jsou předzaškrtnuté — ostatní zkontroluj a případně zaškrtni.':
        'Fetches original names of attachments of type <b>Other</b> from STAG and offers reclassification to <b>Defense record</b>. Files that look like a defense protocol are pre-checked — review the rest and tick as needed.',
    "E-mail a odchozí server pro odesílání posudků sekretářkám. Výchozí hodnoty jsou pro <b>UTB Office365</b> (<a href='https://www.utb.cz/cvt/office365-thunderbird-doc'>nastavení CVT UTB</a>). <b>Heslo se nikde neukládá</b> — zadáš ho při každém odeslání i testu.":
        "Sender e-mail and outgoing server for sending reviews to secretaries. Defaults are for <b>UTB Office365</b> (<a href='https://www.utb.cz/cvt/office365-thunderbird-doc'>UTB CVT setup</a>). <b>The password is never stored</b> — you enter it for every send and test.",
    'E-mail odesílatele a SMTP server pro odesílání posudků sekretářkám (s testem spojení). Heslo se neukládá.':
        'Sender e-mail and SMTP server for sending reviews to secretaries (with a connection test). The password is not stored.',
    'E-mail uživatele (odesílatel posudků sekretářkám). SMTP server se nastavuje v 👤 → Nastavení e-mailu.':
        'User e-mail (sender of reviews to secretaries). The SMTP server is configured in 👤 → E-mail settings.',
    'Evidence zájemců, které jsi <b>odmítl(a)</b> vést (souvisí s kapacitou vedení). Promítá se do <b>Statistik</b>.':
        'Registry of candidates you <b>rejected</b> for supervision (related to supervision capacity). Reflected in <b>Statistics</b>.',
    'Jméno se používá k auto-detekci role při importu ze STAG.\nTituly před/za se automaticky doplní do jména autora v posudku.':
        'The name is used for role auto-detection during STAG import.\nTitles before/after are automatically added to the author name in reviews.',
    'Jméno uživatele profilu — pro auto-detekci role při STAG importu a podpis v posudcích':
        'Profile user name — for role auto-detection during STAG import and the signature in reviews',
    'Když je odškrtnuto, vidíš jen aktuální verzi každého typu. Při nahrání nové verze se předchozí automaticky schová.':
        'When unchecked, you only see the current version of each type. Uploading a new version automatically hides the previous one.',
    'Když obor práce nesedí na žádný obor sekretářky (typicky odlišný kód oboru), normálně se nenabídne. Zaškrtni pro zobrazení všech připravených posudků — vybereš ručně, co poslat.':
        "When a thesis programme doesn't match any of the secretary's programmes (typically a different programme code), it is normally not offered. Tick to show all prepared reviews — pick manually what to send.",
    'Knihovna XLSX šablon posudků v rámci profilu. Šablony se kopírují do <code>profile_dir/templates/</code> a jdou s profilem v ZIP exportu. Z kontextu konkrétní práce (pravý klik) → <i>Generovat posudek z šablony…</i> šablonu vyplní daty z práce a připojí jako přílohu.':
        'Library of XLSX review templates within the profile. Templates are copied into <code>profile_dir/templates/</code> and travel with the profile in ZIP exports. From a thesis context (right-click) → <i>Generate review from template…</i> fills the template with thesis data and attaches it.',
    'LibreOffice není v PATH — PDF se nevygeneruje. Nainstaluj přes brew install --cask libreoffice nebo z libreoffice.org.':
        'LibreOffice is not in PATH — the PDF will not be generated. Install via brew install --cask libreoffice or from libreoffice.org.',
    'Literární zdroje  —  každá citace na nové řádce, číslování se přidá automaticky v Souhrnu.':
        'References — one citation per line; numbering is added automatically in the Overview.',
    'Máš na disku <code>.zip</code> exportovaný přes <i>Export profilu</i> z jiného zařízení? Otevři ho zde — rozbalí se data + dokumenty + šablony do nového profilu a aplikace ho rovnou aktivuje.':
        'Have a <code>.zip</code> exported via <i>Profile export</i> from another device? Open it here — data + documents + templates are extracted into a new profile and the app activates it right away.',
    'Místo pro podpisový blok posudku (Místo, datum). Default „Zlín".':
        'Place for the review signature block (Place, date). Default "Zlín".',
    'Najde ve STAG všechny práce, kde jsi oponent — podle tvého jména z profilu. Vybereš, co naimportovat.':
        'Finds all theses in STAG where you are the opponent — by your profile name. You choose what to import.',
    'Najde ve STAG všechny práce, kde jsi vedoucí (historické, aktuální i vypsané) — podle tvého jména z profilu. Vybereš, co naimportovat.':
        'Finds all theses in STAG where you are the supervisor (historical, current and listed) — by your profile name. You choose what to import.',
    'Najdi a stáhni CSV s prací přímo ze STAG podle příjmení studenta a vedoucího/oponenta (bez přihlášení).':
        "Find and download a thesis CSV directly from STAG by the student's and supervisor's/opponent's surname (no login).",
    'Např. „Drobné shody v citacích a standardních formulacích, žádné podezření."':
        'E.g. "Minor matches in citations and standard phrases, no suspicion."',
    'Nastudujte a popište problematiku testování softwaru.\nProzkoumejte možnosti testování pomocí umělé inteligence.\nRozeberte vhodné nástroje AI využitelné pro testování softwaru.\n…':
        'Study and describe the field of software testing.\nExplore testing possibilities using artificial intelligence.\nAnalyse suitable AI tools usable for software testing.\n…',
    'Nejdřív zvol verdikt (Posouzen — je / není plagiát). Pro „Neposouzen" se komentář negeneruje.':
        'Choose a verdict first (Assessed — plagiarism / not plagiarism). No comment is generated for "Not assessed".',
    'Nelze odebrat profil, který je právě aktivní. Přepni se nejprve jinam.':
        'Cannot remove the currently active profile. Switch to another one first.',
    'Nemáš vyplněný vlastní e-mail. Otevři „⚙ Nastavení e-mailu…“ a doplň ho.':
        'Your own e-mail is not filled in. Open "⚙ E-mail settings…" and add it.',
    'Nemáš vyplněný vlastní e-mail. Otevři „⚙ Nastavení e-mailu…“.':
        'Your own e-mail is not filled in. Open "⚙ E-mail settings…".',
    'Nemáš žádné práce k aktualizaci (vedené v řešení / oponentury aktuálního roku).\nChceš stáhnout NOVÉ práce ze STAG? Použij dole 🆕 Najít nové práce…':
        'No theses to update (supervised in progress / current-year opposed).\nWant to download NEW theses from STAG? Use 🆕 Find new theses… below',
    'Nenávratně smaže záznam práce z databáze a všechny její soubory. Vhodné po chybném importu nebo omylu při zakládání.':
        'Irreversibly deletes the thesis record from the database and all its files. Useful after a wrong import or a mistake when creating.',
    'Nepovinné — co nevyplníš, zůstane prázdné. Obor se ukládá ke zvolenému studentovi (jen pokud je zvolen).':
        'Optional — anything you leave out stays empty. The programme is stored with the selected student (only if one is selected).',
    'Náhled kontroly: co je nové/změněné + seznam zkontrolovaných a aktuálních prací (pro ověření, že kontrola proběhla).':
        'Check preview: what is new/changed + the list of checked and up-to-date theses (to verify the check ran).',
    'Náprava staršího zařazení souborů ze STAG. <b>Prohození</b>: archiv (zip) je veden jako <i>Text práce</i> a PDF jako <i>Příloha</i> — oprava druh prohodí. <b>Balík</b>: archiv jako <i>Text práce</i> bez samostatného PDF (text i přílohy v jednom zipu) — přeřadí se na <i>Text práce + přílohy</i>. Obsah souborů se nemění; před zápisem se vytvoří záloha.':
        'Fixes older classification of files from STAG. <b>Swap</b>: an archive (zip) is classified as <i>Thesis text</i> and a PDF as <i>Attachment</i> — the fix swaps the kinds. <b>Bundle</b>: an archive as <i>Thesis text</i> without a separate PDF (text and attachments in one zip) — reclassified as <i>Thesis text + attachments</i>. File contents are unchanged; a backup is created before writing.',
    'Obnoví se stav databáze ze zálohy pořízené těsně před tímto importem. <b>Vše, co tento import přidal nebo změnil, zmizí.</b><br><br>Aktuální (importovaný) stav se předtím ještě zazálohuje (<code>before-restore</code>), takže krok jde i vrátit.<br><br><small>Pozn.: soubory zkopírované do složky dokumentů zůstanou na disku jako osiřelé (bez vazby v DB) — neškodí.</small>':
        'The database state will be restored from the backup taken just before this import. <b>Everything this import added or changed will disappear.</b><br><br>The current (imported) state is backed up first (<code>before-restore</code>), so this step can also be undone.<br><br><small>Note: files copied into the documents folder remain on disk as orphans (no DB link) — harmless.</small>',
    'Obnoví stav databáze ze zálohy pořízené TĚSNĚ PŘED tímto importem — odstraní vše, co tento import přidal/změnil.':
        'Restores the database from the backup taken JUST BEFORE this import — removes everything this import added/changed.',
    'Obor studenta — uloží se ke studentovi. Dropdown nabízí evidované obory (manažer Obory).':
        "Student's programme — stored with the student. The dropdown offers registered programmes (Programmes manager).",
    'Odebere ze seznamu záznamy, jejichž soubor byl smazán mimo aplikaci (např. ručně ve Finderu). Existující soubory ani odkazy se nedotkne.':
        'Removes entries whose file was deleted outside the app (e.g. manually in Finder). Existing files and links are untouched.',
    'Odebrat ze seznamu všechny záznamy, jejichž soubor už na disku neexistuje?\n\nSmažou se jen záznamy v aplikaci — žádné existující soubory ani odkazy se nedotkne.':
        'Remove all entries whose file no longer exists on disk?\n\nOnly the in-app records are deleted — no existing files or links are touched.',
    'Odesílání e-mailem vyžaduje aktivní profil s vyplněným e-mailem (👤 → Nastavení e-mailu).':
        'Sending by e-mail requires an active profile with an e-mail filled in (👤 → E-mail settings).',
    'Odesílání e-mailem vyžaduje aktivní profil s vyplněným e-mailem.':
        'Sending by e-mail requires an active profile with an e-mail filled in.',
    'Opravdu chceš <b>nenávratně</b> smazat tuto práci včetně všech souborů?':
        'Really <b>irreversibly</b> delete this thesis including all files?',
    'Opravdu smazat VŠECHNY šablony (vč. jejich XLSX souborů) a nahradit je výchozí sadou?\n\nUž vygenerované posudky u prací zůstávají nedotčené.':
        'Really delete ALL templates (incl. their XLSX files) and replace them with the default set?\n\nAlready generated reviews attached to theses remain untouched.',
    'Opravdu smazat celý číselník oborů a nahradit ho výchozími?\n\nStudentům zůstane jejich uložený obor (je to jen text), jen se přepíše seznam oborů.':
        'Really delete the whole programme list and replace it with the defaults?\n\nStudents keep their stored programme (it is just text); only the programme list is replaced.',
    'Otevře ZIP s exportem z jiného zařízení a vytvoří nový profil.':
        'Opens a ZIP exported on another device and creates a new profile.',
    'Otevře editor posudku (auto-filtr šablon dle typu a oboru), vyplní body hodnocení a vygeneruje XLSX + PDF jako přílohu.':
        'Opens the review editor (templates auto-filtered by type and programme), fills in the scores and generates XLSX + PDF as an attachment.',
    'Otevře editor s naposledy uloženými daty posudku — navážeš tam, kde jsi přestal.':
        'Opens the editor with the last saved review data — continue where you left off.',
    'Otevře hromadné vyhledání tvých prací ve STAG podle jména (napříč roky) — odtud stáhneš a naimportuješ NOVÉ práce, které ještě nemáš v databázi (např. pro nový akademický rok).':
        "Opens a bulk STAG search of your theses by name (across years) — from there you download and import NEW theses you don't have yet (e.g. for a new academic year).",
    'Otevře tisk posudků jen s vybranými pracemi (posudek oponenta). Práce bez PDF posudku se přeskočí.':
        "Opens review printing with only the selected theses (opponent's review). Theses without a PDF review are skipped.",
    'Otevře tisk posudků jen s vybranými pracemi (posudek vedoucího). Práce bez PDF posudku se přeskočí.':
        "Opens review printing with only the selected theses (supervisor's review). Theses without a PDF review are skipped.",
    'Otevřel jsem připravený e-mail v tvém mailovém klientovi.\n\nAž ho tam odešleš, mám tyto posudky označit jako odeslané?':
        'The prepared e-mail was opened in your mail client.\n\nOnce you send it there, should I mark these reviews as sent?',
    'Otevřel jsem testovací e-mail (jen tobě) v mailovém klientovi. Posudky nebyly označeny jako odeslané.':
        'A test e-mail (only to you) was opened in the mail client. Reviews were NOT marked as sent.',
    'Po úspěšném importu (rollback se nepočítá) původní CSV soubor odstraní z disku. Kopie zůstává jako příloha typu *STAG export* u každé importované práce.':
        "After a successful import (rollback doesn't count), deletes the original CSV from disk. A copy remains attached as a *STAG export* to every imported thesis.",
    'Po úspěšném nahrání soubor odstraní z původního umístění (typicky Downloads). Kopie je bezpečně uložená v documents/ konkrétní práce, takže o nic nepřijdeš. Pro testování / opakované nahrávání odškrtni.':
        'After a successful upload, removes the file from its original location (typically Downloads). The copy is safely stored in the thesis documents/, so nothing is lost. Untick for testing / repeated uploads.',
    'Pokud máš složku s <code>db.json</code> (např. ze synchronizované složky), můžeš ji připojit jako profil.':
        'If you have a folder with <code>db.json</code> (e.g. from a synced folder), you can attach it as a profile.',
    'Porovná soubory u prací (vedených i oponovaných) se STAG a vypíše, kde STAG nabízí <b>druh dokumentu</b> (plný text / příloha / posudek), který <b>v databázi chybí</b>. Zaškrtnuté soubory můžeš rovnou <b>dostáhnout</b>. Budoucí práce (zájemci / vypsaná témata) se nekontrolují.':
        'Compares thesis files (supervised and opposed) with STAG and lists where STAG offers a <b>document kind</b> (full text / attachment / review) that is <b>missing in the database</b>. Checked files can be <b>downloaded</b> right away. Future theses (candidates / listed topics) are not checked.',
    'Porovná tuto oponenturu se STAG a nabídne dohrání chybějících souborů (a aktualizaci stavu); ukáže, co se aktualizuje.':
        'Compares this opposed thesis with STAG and offers to download missing files (and update the status); shows what will be updated.',
    'Porovná tuto práci se STAG a nabídne změnu stavu a dohrání chybějících souborů (ukáže, co se aktualizuje; lze vybrat).':
        'Compares this thesis with STAG and offers a status change and download of missing files (shows what will be updated; selectable).',
    'Porovná vybrané práce se STAG a nabídne <b>změnu stavu</b> a <b>dohrání chybějících souborů</b> (např. nový posudek nebo odevzdaná práce). Zaškrtni, co aplikovat. <b>Když je vše aktuální, nic se nenabídne.</b>':
        'Compares the selected theses with STAG and offers a <b>status change</b> and <b>download of missing files</b> (e.g. a new review or submitted thesis). Tick what to apply. <b>If everything is up to date, nothing is offered.</b>',
    'Pošle kopii na tvůj e-mail, aby byla jistota, že se mail odeslal.':
        'Sends a copy to your e-mail so you can be sure the mail went out.',
    'Pošle stejný e-mail (včetně PDF příloh) jen na tvůj e-mail — pro kontrolu, než ho pošleš sekretářce. Posudky NEoznačí jako odeslané.':
        'Sends the same e-mail (including PDF attachments) only to your address — to check before sending to the secretary. Reviews are NOT marked as sent.',
    'Pro hromadné stažení doplň své jméno v profilu (👤 → Tvoje jméno).':
        'For bulk download, fill in your name in the profile (👤 → Your name).',
    'Pro každého nového studenta (u vedených prací) otevře kartu studenta předvyplněnou daty ze STAG — můžeš doplnit e-mail, telefon, obor apod. Záznam se uloží až v rámci importu.':
        'For each new student (of supervised theses) opens a student card prefilled with STAG data — you can add e-mail, phone, programme etc. The record is saved as part of the import.',
    'Přidá do patičky e-mailu řádek o aplikaci BPDPManager s odkazem na GitHub. Projeví se v náhledu textu.':
        'Adds a footer line about the BPDPManager app with a GitHub link. Visible in the text preview.',
    'Připojí se k serveru a přihlásí (vyzve heslo) — bez odeslání e-mailu.':
        'Connects to the server and logs in (prompts for the password) — without sending an e-mail.',
    'Příjmení nemusí být jednoznačné (víc vedoucích stejného příjmení). Zaškrtnuté = ponechá jen práce, kde je tvé celé jméno z profilu.':
        'A surname may be ambiguous (several supervisors with the same surname). Checked = keeps only theses with your full profile name.',
    'Registr vedoucích cizích BP/DP. Používá se pro našeptávání při vyplňování oponentských posudků. Dvojklik upraví detail.':
        "Registry of supervisors of others' theses. Used for autocompletion when filling in opponent reviews. Double-click edits the detail.",
    'Revize tohoto studenta byla zrušena.\n\nPokračovat v importu s automaticky vyplněnými údaji (jméno, obor, osobní číslo)?':
        "This student's review was cancelled.\n\nContinue the import with automatically filled data (name, programme, personal number)?",
    'Rozparsuje jména stažená ze STAG (formát „Příjmení Jméno, tituly“) na tituly před/za + jméno. Ukáže náhled.':
        'Parses names downloaded from STAG (format "Surname Name, titles") into titles before/after + name. Shows a preview.',
    'Rozparsuje jména stažená ze STAG na tituly před/za + jméno (i u jména vedoucího uloženého u oponentur). Ukáže náhled.':
        'Parses names downloaded from STAG into titles before/after + name (incl. the supervisor name stored with opposed theses). Shows a preview.',
    'Seznam oponentů — Interní (UTB) a Externí. Dvojklik upraví detail.':
        'List of opponents — Internal (UTB) and External. Double-click edits the detail.',
    'Seznam profilů. Aktivní profil je zvýrazněn. Smazat profil z registry můžeš, data ve složce zůstanou (pokud explicitně neodklikneš jejich smazání).':
        'List of profiles. The active profile is highlighted. You can remove a profile from the registry; the data folder remains (unless you explicitly confirm its deletion).',
    'Seznam studijních oborů (např. NSWI-P, NKYB-K). U každého lze evidovat STAG zkratku pro import (např. <code>knIT-KYB</code>) a sekretářku oboru. Položky jsou agregovány podle sekretářky — <b>dvojklik na obor</b> upraví detail, <b>dvojklik na hlavičku sekretářky</b> upraví její kontakt a oslovení <b>hromadně pro všechny její obory</b>.':
        'List of study programmes (e.g. NSWI-P, NKYB-K). Each can have a STAG code for import (e.g. <code>knIT-KYB</code>) and a programme secretary. Items are grouped by secretary — <b>double-click a programme</b> to edit its detail, <b>double-click a secretary header</b> to edit her contact and salutation <b>for all her programmes at once</b>.',
    'Sjednotí form-varianty šablon (prezenční -P / kombinovaná -K téhož oboru): sloučí duplicity a přejmenuje šablony na form-neutrální názvy (bez -P/-K). Ukáže náhled.':
        'Unifies form variants of templates (full-time -P / part-time -K of the same programme): merges duplicates and renames templates to form-neutral names (without -P/-K). Shows a preview.',
    'Skryje studenty, jejichž aktuální práce je obhájená nebo nedokončená.':
        'Hides students whose current thesis is defended or not completed.',
    'Stáhne CSV s prací i její soubory — v dalším kroku zvolíš, co naimportovat.':
        'Downloads the thesis CSV and its files — in the next step you choose what to import.',
    'Stáhne jen soubory (text, přílohy, posudky) a připojí je k odpovídající práci, kterou už máš v databázi (CSV se neimportuje). Pokud práce v databázi není, upozorní.':
        'Downloads only the files (text, attachments, reviews) and attaches them to the matching thesis already in your database (the CSV is not imported). Warns if the thesis is not in the database.',
    'Stáhne český hunspell slovník (LibreOffice) do ~/.bpdpmanager/dictionaries/ a zapne kontrolu pravopisu.':
        'Downloads the Czech hunspell dictionary (LibreOffice) into ~/.bpdpmanager/dictionaries/ and enables spell checking.',
    'Tato akce <b>nevratně</b> smaže záznam práce z databáze a <b>všechny související soubory</b> ze složky <code>documents/</code>. Student / oponent / vedoucí v registru zůstanou (mohou být provázáni s jinými pracemi).':
        'This action <b>irreversibly</b> deletes the thesis record from the database and <b>all related files</b> from <code>documents/</code>. The student / opponent / supervisor stay in the registry (they may be linked to other theses).',
    'U oponovaných prací aktuálního akademického roku porovná soubory se STAG a nabídne dohrání chybějících (např. nový posudek).':
        'For opposed theses of the current academic year, compares files with STAG and offers to download missing ones (e.g. a new review).',
    'U vedených prací ve stavu „V řešení“ porovná stav a soubory se STAG a nabídne změnu stavu + dohrání chybějících souborů (např. nový posudek nebo odevzdaná práce).':
        'For supervised theses "In progress", compares status and files with STAG and offers a status change + download of missing files (e.g. a new review or submitted thesis).',
    'Uloží kompletní balík práce (data, stav, posudky, soubory) do ZIPu — lze importovat na jiném zařízení / v jiném profilu.':
        'Saves the complete thesis bundle (data, status, reviews, files) into a ZIP — can be imported on another device / in another profile.',
    'Uloží strukturovaná data posudku. XLSX a PDF nevygeneruje — stačí třeba pro rozpracovaný posudek, který chceš dokončit později.':
        'Saves the structured review data. XLSX and PDF are not generated — enough e.g. for a draft review you want to finish later.',
    'V <code>~/.bpdpmanager/</code> jsem našel existující <code>db.json</code> z předchozích verzí. Můžeme rovnou vyrobit profil „Výchozí“, který bude ukazovat na tuto složku — žádná data se nepřesouvají, jen se zaregistruje cesta.':
        'An existing <code>db.json</code> from previous versions was found in <code>~/.bpdpmanager/</code>. We can create a profile "Default" pointing to this folder right away — no data is moved, only the path is registered.',
    'Vloží doporučené znění podle verdiktu a procenta shody. Lze libovolně upravit. Rozbalovací šipka nabízí konkrétní varianty.':
        'Inserts the suggested wording based on the verdict and match percentage. Can be edited freely. The dropdown arrow offers specific variants.',
    'Vloží tematické nadpisy (kostru) pro slovní hodnocení podle role a jazyka šablony. Když už něco píšeš, vloží se za kurzor.':
        'Inserts thematic headings (a skeleton) for the verbal evaluation by role and template language. If you are already writing, it is inserted at the cursor.',
    'Vyber posudky k tisku a cíl: <b>MyQ</b> (tisková fronta univerzity) nebo <b>systémová tiskárna</b>. Tisknou se <b>oboustranně</b>. Předzaškrtnuté jsou posudky, které ještě nebyly vytištěné.':
        'Select reviews to print and the destination: <b>MyQ</b> (university print queue) or a <b>system printer</b>. Printing is <b>double-sided</b>. Reviews not printed yet are pre-checked.',
    'Vyber v seznamu profil, kterému chceš nastavit místo posudku.':
        'Select the profile whose review place you want to set.',
    'Vyber šablonu a napiš oponentský posudek k této práci (role oponent).':
        'Select a template and write an opponent review for this thesis (opponent role).',
    'Vybere se šablona z knihovny (auto-filtr dle typu a oboru), vyplní se daty z této práce a otevře se v Excelu k vyplnění bodů hodnocení. Posudek se připojí jako příloha.':
        "A template is selected from the library (auto-filtered by type and programme), filled with this thesis's data and opened in Excel to fill in the scores. The review is attached as an attachment.",
    'Vybere se šablona z knihovny, vyplní se daty z této práce a připojí se jako příloha.':
        "A template is selected from the library, filled with this thesis's data and attached as an attachment.",
    "Vyhledá veřejné záznamy kvalifikačních prací na <a href='https://stag.utb.cz'>stag.utb.cz</a> a stáhne jejich CSV. Hledat můžeš podle <b>příjmení studenta</b> (+ upřesnění vedoucím/oponentem), nebo <b>jen podle vedoucího/oponenta</b> — pak najde <b>všechny jeho práce</b> (historické i aktuální) a můžeš jich naimportovat víc najednou.":
        "Searches public qualification thesis records on <a href='https://stag.utb.cz'>stag.utb.cz</a> and downloads their CSV. You can search by the <b>student's surname</b> (+ refined by supervisor/opponent), or <b>only by supervisor/opponent</b> — then it finds <b>all their theses</b> (historical and current) and you can import several at once.",
    'Vyplnit oponentský posudek z šablony (kritéria, body, známka) a připojit jako přílohu.':
        'Fill in an opponent review from a template (criteria, scores, grade) and attach it as an attachment.',
    'Vytvoří přenosný ZIP balík profilu — db.json + dokumenty + harmonogramy. Lze otevřít na jiném zařízení přes „Importovat profil ze ZIPu…".':
        'Creates a portable profile ZIP bundle — db.json + documents + schedules. Can be opened on another device via "Import profile from ZIP…".',
    'Vytvoří se nová prázdná databáze ve složce, kterou si vybereš.':
        'A new empty database will be created in a folder you choose.',
    'Všechny řádky mají akci „Přeskočit". Nastav alespoň jeden řádek na *Vytvořit* nebo *Aktualizovat*.':
        'All rows have the action "Skip". Set at least one row to *Create* or *Update*.',
    'Z návrhu založí novou vedenou práci (název, popis, body, typ) a návrh odebere. Obor přiřadíš až se studentem.':
        'Creates a new supervised thesis from the proposal (title, description, objectives, type) and removes the proposal. The programme is assigned with the student.',
    'Z vybraného profilu se zkopíruje db.json. Volitelně přibalit i:':
        'db.json is copied from the selected profile. Optionally also include:',
    'Zadej příjmení studenta, nebo příjmení vedoucího/oponenta (hromadné vyhledání všech jeho prací).':
        "Enter the student's surname, or the supervisor's/opponent's surname (bulk search of all their theses).",
    'Zkopíruje nejnovější PDF oponentského posudku pro vybrané práce do zvolené složky (pro tisk). Práce bez PDF posudku se přeskočí.':
        'Copies the latest opponent review PDFs of the selected theses into a chosen folder (for printing). Theses without a PDF review are skipped.',
    'Zkopíruje nejnovější PDF posudku vedoucího pro vybrané práce do zvolené složky (pro tisk). Práce bez PDF posudku se přeskočí.':
        'Copies the latest supervisor review PDFs of the selected theses into a chosen folder (for printing). Theses without a PDF review are skipped.',
    'Zobrazí vybraný soubor ve správci souborů (Finder / Explorer).':
        'Shows the selected file in the file manager (Finder / Explorer).',
    'Záloha byla obnovena. Aplikace nyní pracuje nad obnovenými daty.':
        'The backup was restored. The app now works with the restored data.',
    'např. Petr Žáček — slouží k auto-detekci role při STAG importu':
        'e.g. Petr Žáček — used for role auto-detection during STAG import',
    'odkaz na práci v IS/STAG (volitelné, např. https://stag.utb.cz/portal/studium/prohlizeni.html?…)':
        'link to the thesis in IS/STAG (optional, e.g. https://stag.utb.cz/portal/studium/prohlizeni.html?…)',
    'Žádná z vybraných prací nemá vytvořený PDF posudek — není co exportovat.':
        'None of the selected theses has a generated PDF review — nothing to export.',
    'Žádné form-duplicity ani názvy se značkou -P/-K — knihovna je čistá.':
        'No form duplicates or names with the -P/-K tag — the library is clean.',
    'Žádné práce s přílohou typu „Jiné“ a STAG ID — není co přeřadit.':
        'No theses with an attachment of type "Other" and a STAG ID — nothing to reclassify.',
    'Žádné změny nebyly uloženy. Pokud chceš, můžeš upravit data v náhledu a zkusit znovu, nebo zavřít dialog.':
        'No changes were saved. You can edit the data in the preview and retry, or close the dialog.',
    'Žádný profil v registru — nejdřív vytvoř profil nebo zvol „Vytvořit nový profil".':
        'No profile in the registry — create a profile first or choose "Create a new profile".',
    '⚠ Ověření TLS certifikátu MyQ selhalo — pokračuji bez ověření (interní univerzitní server).':
        '⚠ MyQ TLS certificate verification failed — continuing without verification (internal university server).',
    '⚠ STAG obor není namapovaný na žádný evidovaný obor. Vyber existující obor, nebo zvol „Nový obor…" — předvyplní se STAG kód, takže příště se namapuje automaticky.':
        '⚠ The STAG programme is not mapped to any registered programme. Select an existing programme, or choose "New programme…" — the STAG code is prefilled, so next time it maps automatically.',
    '⚠ Specializace nebyla v šabloně vyplněna. Vyber obor z nabídky (odvozeno z listu Konfigurace) nebo nech prázdné.':
        '⚠ The specialisation was not filled in the template. Select a programme from the list (derived from the Configuration sheet) or leave empty.',
    '✓ Data posudku uložena. XLSX/PDF se nevygenerovaly — můžeš dokončit kdykoli později (z detailu práce).':
        '✓ Review data saved. XLSX/PDF were not generated — you can finish any time later (from the thesis detail).',

    # ── Vlna 3: texty bez diakritiky ─────────────────────────────────────
    '(bez oponenta)': '(no opponent)',
    '(bez studenta)': '(no student)',
    '<b>Body</b>': '<b>Points</b>',
    'Adresa': 'Address',
    'Ak. rok': 'Acad. year',
    'Akad. rok': 'Acad. year',
    'Aktualizace aplikace': 'Application update',
    'Aktualizovat ze STAG': 'Update from STAG',
    'Auto-detekce': 'Auto-detection',
    'BP i DP': 'BP and DP',
    'Bude': 'Will be',
    'CSV soubor': 'CSV file',
    'Cesta': 'Path',
    'Chyba': 'Error',
    'Chyba importu': 'Import error',
    'Co naimportovat:': 'What to import:',
    'Do': 'To',
    'Export': 'Export',
    'Export hotov': 'Export finished',
    'Export selhal': 'Export failed',
    'Exportovat': 'Export',
    'Hotovo': 'Done',
    'Import': 'Import',
    'Import PDF': 'PDF import',
    'Import dat ze STAG CSV': 'Import data from a STAG CSV',
    'Import hotov': 'Import finished',
    'Import selhal': 'Import failed',
    'Importovat': 'Import',
    'Importovat data z': 'Import data from',
    'Importovat profil ze ZIPu': 'Import profile from ZIP',
    'Interval (do)': 'Interval (to)',
    'Jazyk': 'Language',
    'Kategorie': 'Category',
    'Komu:': 'To:',
    'Kontakt': 'Contact',
    'Kontrola konzistence se STAG': 'STAG consistency check',
    'Kontrolovat aktualizace po startu aplikace': 'Check for updates on app start',
    'Literatura:': 'References:',
    'Merge selhal': 'Merge failed',
    'Nic k importu': 'Nothing to import',
    'Obnova selhala': 'Restore failed',
    'Obor / specializace': 'Programme / specialisation',
    'Od': 'From',
    'Odebrat PDF': 'Remove PDF',
    'Odebrat dokument': 'Remove document',
    'Odebrat dokumenty': 'Remove documents',
    'Odebrat odkaz': 'Remove link',
    'Odebrat profil': 'Remove profile',
    'Odebrat z registry (data zachovat)': 'Remove from registry (keep data)',
    'Odebrat z registry…': 'Remove from registry…',
    'Odeslat e-mail?': 'Send e-mail?',
    'Odeslat mailem': 'Send by e-mail',
    'Odeslat soubor e-mailem': 'Send file by e-mail',
    'Oponenti': 'Opponents',
    'Podpis': 'Signature',
    'Popis': 'Description',
    'Popis:': 'Description:',
    'Posudek': 'Review',
    'Potvrdit merge': 'Confirm merge',
    'Potvrdit tisk': 'Confirm printing',
    'Preview selhalo': 'Preview failed',
    'Procento shody:': 'Match percentage:',
    'Profil': 'Profile',
    'Rezervace': 'Reservation',
    'Role': 'Role',
    'Roll-back hotov': 'Roll-back finished',
    'STAG zkratka': 'STAG code',
    'STAG — aktualizace': 'STAG — update',
    'STAG — jen soubory': 'STAG — files only',
    'STAG — jen stavy': 'STAG — statuses only',
    'Seskupit podle:': 'Group by:',
    'Smazat data': 'Delete data',
    'Smazat obor': 'Delete programme',
    'Smazat oponenta': 'Delete opponent',
    'Smazat posudek': 'Delete review',
    'Smazat studenta': 'Delete student',
    'Soubor': 'File',
    'Souhrn tisku': 'Print summary',
    'Stav (rok)': 'Status (year)',
    'Student': 'Student',
    'Telefon': 'Phone',
    'Text e-mailu:': 'E-mail text:',
    'Tisk': 'Print',
    'Tisk posudku': 'Print review',
    'Tituly za': 'Titles after',
    'Typ': 'Type',
    'Uklidit duplicity': 'Clean duplicates',
    'Upravit': 'Edit',
    'Upravit…': 'Edit…',
    'Ve Finderu': 'In Finder',
    'Verdikt': 'Verdict',
    'Verdikt:': 'Verdict:',
    'Vyber profil': 'Select profile',
    'Vyber v seznamu profil pro export.': 'Select a profile in the list to export.',
    'Zdroj (odkud importovat)': 'Source (import from)',
    'Zobrazit:': 'Show:',
    'role:': 'role:',
    '↑ Nahoru': '↑ Top',
    '☐ Nic': '☐ None',
    '✉ E-mail…': '✉ E-mail…',
    '✉ Odeslat mailem…': '✉ Send by e-mail…',
    '✉ Odeslat soubor e-mailem': '✉ Send file by e-mail',
    '✉ Odeslat…': '✉ Send…',
    '✏ Detail': '✏ Detail',
    '🏷 Aktualizovat jen stavy': '🏷 Update statuses only',
    '💾 Exportovat na disk…': '💾 Export to disk…',
    '📂 Zobrazit ve Finderu': '📂 Show in Finder',
    '📄 Importovat PDF…': '📄 Import PDF…',
    '📎 Vybrat PDF…': '📎 Select PDF…',
    '📤 Export…': '📤 Export…',
    '📤 Exportovat': '📤 Export',
    '📥  Importovat .zip…': '📥  Import .zip…',
    '📥 Import dat ze STAG CSV': '📥 Import data from a STAG CSV',
    '📥 Importovat': '📥 Import',
    '📥 Importovat profil ze ZIPu': '📥 Import profile from ZIP',
    '📥 Importovat profil ze ZIPu…': '📥 Import profile from ZIP…',
    '🔀 Potvrdit merge': '🔀 Confirm merge',
    '🔄 Aktualizovat a restartovat': '🔄 Update and restart',
    '🔍 Hledat:': '🔍 Search:',
    '🔍 Kontrola konzistence se STAG': '🔍 STAG consistency check',
    '🔍 Vyhledat ve STAG': '🔍 Search in STAG',
    '🔎 Detaily…': '🔎 Details…',
    '🖨 Odeslat na tisk': '🖨 Send to print',
    '🖨 Tisk': '🖨 Print',
    '🗑 Odebrat': '🗑 Remove',
    '🧐 Moje oponentury…': '🧐 My opposed theses…',
    '🧐 Oponent': '🧐 Opponent',
    '🧐 Oponuji': '🧐 I oppose',
    '🧹 Uklidit duplicity': '🧹 Clean duplicates',
    '🧹 Uklidit tituly': '🧹 Clean up titles',
    '(žádné)': '(none)',
    '🎓 Posudky vedoucího': "🎓 Supervisor's reviews",
    '🧐 Posudky oponenta': "🧐 Opponent's reviews",
    '🖨 K tisku — nevytištěné': '🖨 To print — not printed yet',
    '✓ Již vytištěné (pro opětovný tisk)': '✓ Already printed (for reprint)',
    "Nápověda": "Help",
    "🌐 Otevřít ve STAG": "🌐 Open in STAG",
    "Otevře detail práce ve STAG v prohlížeči.":
        "Opens the thesis detail in STAG in your browser.",
    # ── Komise SZZ (2.3.0) ───────────────────────────────────────────────
    "🏛 Komise": "🏛 Committees",
    "📄 Importovat PDF komisí…": "📄 Import committee PDFs…",
    "Načte fakultní PDF (složení komisí i rozpis studentů — druh se "
    "rozpozná automaticky, rozpis i podle barvy nadpisů) a po náhledu "
    "uloží. PDF se ukládají do komise/<rok>/.":
        "Loads faculty PDFs (committee composition and student schedules — "
        "the kind is detected automatically, schedules also by heading "
        "colour) and saves after a preview. PDFs are stored in komise/<year>/.",
    "🌐 Otevřít web s rozpisy": "🌐 Open the schedules website",
    "Otevře stránku FAI se složením komisí a rozpisy SZZ.":
        "Opens the FAI page with committee compositions and SZZ schedules.",
    "🔄 Načíst komise znovu": "🔄 Reload committees",
    "Načíst komise znovu": "Reload committees",
    "Smaže všechny komise a načte čisté složení z aplikace. Použij na "
    "úklid starých naimportovaných komisí, které nesedí (chybí obor, "
    "duplicity). Rozpisy studentů z dříve nahraných PDF zmizí — nahraj "
    "je znovu.":
        "Deletes all committees and loads the clean composition shipped with "
        "the app. Use it to clean up old imported committees that don't match "
        "(missing programme, duplicates). Student schedules from previously "
        "uploaded PDFs disappear — import them again.",
    "Smaže VŠECHNY komise a načte čisté složení z aplikace.\n\n"
    "Použij na úklid starších naimportovaných komisí, které nesedí "
    "(chybí obor, duplicity, zmíchané barvy).\n\n"
    "⚠ Rozpisy studentů z dříve nahraných PDF zmizí — nahraj je "
    "potom znovu přes Importovat PDF komisí (napojí se už na "
    "správné komise).\n\nPokračovat?":
        "Deletes ALL committees and loads the clean composition shipped with "
        "the app.\n\nUse it to clean up older imported committees that don't "
        "match (missing programme, duplicates, mixed colours).\n\n⚠ Student "
        "schedules from previously uploaded PDFs disappear — import them again "
        "via Import committee PDFs (they will attach to the right committees).\n"
        "\nContinue?",
    "Načteno {n} komisí z aplikace. Teď nahraj PDF rozpisů studentů.":
        "Loaded {n} committees from the app. Now import the student schedule PDFs.",
    "Jen komise s mými studenty": "Only committees with my students",
    "vedený student": "supervised student",
    "oponovaný student": "opposed student",
    "tvoje komise": "your committee",
    "Komise": "Committee",
    "Moji studenti": "My students",
    "Studenti V/O": "Students S/O",
    "Vedení: {led} · Oponované: {opp}": "Supervised: {led} · Opposed: {opp}",
    "Termíny": "Dates",
    "Bakalářské (Bc)": "Bachelor (Bc)",
    "Magisterské (Mgr)": "Master (Mgr)",
    "Vyber komisi vlevo, nebo importuj PDF s komisemi.":
        "Select a committee on the left, or import committee PDFs.",
    "Složení komise": "Committee members",
    "Rozpis studentů": "Student schedule",
    "Zdrojová PDF:": "Source PDFs:",
    "Vyber PDF s komisemi / rozpisy": "Select committee / schedule PDFs",
    "nerozpoznán formát (složení/rozpis)": "unrecognised format (composition/schedule)",
    "Import komisí": "Committee import",
    "Z vybraných PDF se nepodařilo nic načíst.":
        "Nothing could be read from the selected PDFs.",
    "Hotovo: {created} nových komisí, {updated} aktualizovaných, "
    "{slots} slotů rozpisu.":
        "Done: {created} new committees, {updated} updated, "
        "{slots} schedule slots.",
    "Import komisí — náhled": "Committee import — preview",
    "Zaškrtni, co uložit (merge dle roku + barvy):":
        "Tick what to save (merged by year + colour):",
    "Položka": "Item",
    "Detail": "Detail",
    "Složení komisí": "Committee compositions",
    "Rozpisy studentů": "Student schedules",
    "🗑 Smazat komisi": "🗑 Delete committee",
    "Smazat komisi {name} ({year})? Zdrojová PDF na disku "
    "zůstanou.":
        "Delete committee {name} ({year})? Source PDFs stay on disk.",
}
