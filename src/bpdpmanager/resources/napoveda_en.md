# Help — BPDPManager

A desktop application for managing the supervision and opposition of
**bachelor's (BP)** and **master's (DP)** theses of a single academic
supervisor.

> This help is the *single source of truth* — it is shown in the app
> (toolbar **❓ Help**) and in the repository. The Czech original lives in
> `napoveda.md`; this is its full English translation.

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
  Theses move to History **immediately after a status change**
  (defended/failed/not completed) — even mid-year; the **current academic
  year** group therefore carries the note **"this year's completed theses"**.
- **All** — all supervised theses. **Academic year headers** are coloured:
  **future** (blue), **current** (green), **past** (grey).
- **🧐 Opposed theses** — theses where you are the opponent. The tab title
  counts the current academic year. Reviews can be written here too.
- **📅 Schedule** — faculty deadlines from PDF

> **Important:** the tab placement is driven by **status**, not year.

### 📑 List + detail (collapsible)

Every thesis tab (supervised, future, History, *All* and 🧐 opposed) has the
**list on top** and the **detail of the selected thesis below**:

- **With no thesis selected the detail is hidden entirely** — the list gets
  the full tab height (no empty area with a hint message).
- Selecting a thesis opens the detail. The thin **"Thesis detail" bar**
  above it **collapses the detail downwards** (only the bar remains) —
  handy when browsing long lists (History, All). Clicking the bar again
  expands it; the collapsed state **persists** while switching theses.

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

## Thesis — detail (tabs)

The detail of the selected thesis has inner tabs:

### 📋 Overview
A read-only overview of the whole thesis — colour status badge, header
(type / title / student / opponent), annotation, assignment objectives,
references, plagiarism result, the **Grades** section (suggested from reviews
— supervisor + opponent), a **preview of saved reviews** (role, points, grade,
criteria, evaluation) and finally **Files** (current attachments). Every
section has a 📋 button to copy it to the clipboard.

> **Grades of historical theses.** The *Grades* section takes the grade
> primarily from a review written in the app. If the review exists only as an
> **uploaded file** — PDF or Word (`.doc` / `.docx`), typically for older
> theses downloaded from STAG — the app tries to **read** the suggested grade
> from it. For **Word** reviews the **selected value of the grade dropdown
> form field** takes precedence (authoritative); free text is used only as a
> fallback ("navrhuji hodnocení B…", "Navržená známka: D"). (Old binary
> `.doc` files are converted via LibreOffice in the background.) Encrypted
> STAG PDFs are read too. **Uploading/downloading a new review file
> overwrites the role's grade** (the new review is authoritative — this also
> fixes previously mis-read values). The automatic fill on opening a thesis
> only **fills empty fields** and never overwrites a manually entered grade.

### 📝 Topic & assignment
Year, student, **programme**, opponent, CZ + EN title, CZ + EN annotation,
assignment objectives and references (free text with automatic numbering),
STAG link.

> **Programme** is a dropdown of **registered programmes** (from the
> *Programmes* manager) — stored with the student. Keep it on a registered
> programme so the thesis pairs with a secretary when sending reviews.

### Notes
Free text + deadlines/consultations.

### 🔍 Plagiarism
- **Match percentage** + **verdict** (Not assessed / Plagiarism / Not
  plagiarism)
- **Automatic comment prefill** — once you fill the **percentage** and click
  a **verdict**, the comment is **prefilled** with a suggested wording (incl.
  the percentage). Changing the percentage refreshes the auto text; once you
  **edit the comment manually**, it is never overwritten. (*Not assessed*
  generates nothing.)
- **💡 Suggested comment** — inserts the suggested wording by verdict and
  percentage (the dropdown arrow offers specific variants). Fully editable.
- **PDF report** — upload and open the IS/STAG report.
- **The "Plagiarism" column** in *Currently supervised theses* shows a rounded
  badge — assessed (✓ green) or not (✗ red). Hidden in other tabs.

### 📎 Documents
Files and links of the thesis, **aggregated by type** (Thesis text,
Attachments, **Thesis text + attachments** (one zip bundle), Work journal,
Official assignment, Supervisor's review, Opponent's review, Presentation,
**Defense record**, STAG export, Other).
A *Defense record* = the defense protocol (SZZ); newly downloaded STAG files
are recognised **by the STAG section** automatically. Older such files
(classified as *Other*) can be reclassified via the **🗂 Reclassify defense
records** toolbar button (fetches original STAG names, pairs them with local
attachments and offers reclassification in a checkbox preview, with a backup).

- **Table columns:** *Type / file*, *Version*, *Size* (B / KB / MB / GB),
  *Format* (extension, or *link* for URLs) and *File path* (full path).
- **Colour categories:** each document kind has its heading colour;
  supervisor and opponent reviews are grouped under a parent **Reviews**
  group.
- **Versioning:** uploading the **same** file (same name) creates a new
  version and marks the previous one *superseded*. **Different files** of the
  same kind **coexist** (e.g. `…_part1.zip` and `…_part2.zip`). The **Show
  older versions** toggle is on by default. For reviews, the newest **XLSX
  and PDF** both count as current.
- **Auto-naming:** files are renamed to
  `{Surname}_{type}_{YYYY-MM-DD}[_qualifier][_vN].{ext}` and sorted into a
  subfolder by type. Attachments (and *Other*) get a **distinguishing part of
  the original name** so two different attachments don't look like versions.
- **Type auto-detection** from the original file name on upload.
- **🗑 Delete original after upload** (default on) — removes the source from
  Downloads; the copy stays in `documents/`.
- **📂 In Finder** — reveals the selected file in the file manager.
- **Right-click** on a document opens a context menu (also for opposed
  theses): *Open* · *📂 Show in Finder* · *Remove*, plus for **files**:
  - **🖨 Print** (PDF and XLSX) — a PDF goes straight to the default printer,
    an XLSX opens in its app for manual printing (Cmd/Ctrl+P).
  - **📋 Copy file** — copies the **file itself** to the clipboard.
  - **💾 Export to disk…** — saves a copy to a chosen location.
  - **✉ Send by e-mail…** — sends the file as an attachment via **SMTP**
    (the password is asked on send, never stored). On SMTP failure a .eml
    fallback is offered.

  > **Multiple files at once:** select several files (Cmd/Ctrl/Shift) and
  > ***Open* all of them at once** (not just one), bulk **export**, **send in
  > one e-mail** or **🗑 bulk remove** them.
- **Missing files:** deleting a file outside the app doesn't break anything —
  the record stays, shown red with *⚠ missing file*. **🧹 Clean up missing**
  removes such dead records (existing files and links are kept).

---

## Writing a review (supervisor / opponent)

The **📝 Write review…** button is in **two places**:

- on a **supervised thesis** *In progress* (thesis detail — active only in
  that status),
- on an **opposed thesis** (the *🧐 Opposed theses* tab → detail header) —
  here you fill in your **opponent** review of someone else's thesis.

Workflow:

1. **Template selection** — the dialog offers only **relevant** templates,
   **grouped by programme**. Always filtered by **thesis type** (BP vs DP)
   and **role** (supervisor for supervised, opponent for opposed). The *Also
   show templates of other programmes* toggle relaxes only the programme
   filter. The right template is pre-selected. If a saved review already
   exists, a **✏ Continue last review** button appears on top. (The
   **thesis programme** template is pre-selected — `SWI-P`/`NSWI-P` maps to
   `SWI`, `NKYB-K` to `KYB`.)
2. **Review editor** — a form (with **📄 Open thesis text** and **📕/📘 Open
   the counterpart review** buttons on top; active only when the file
   exists):
   - *Fulfilment of objectives* — options follow the **template language**
   - **Evaluation criteria** — whole points 0–5, weights from the template
   - **Live summary** — weighted points, percentages, suggested ECTS grade.
     The scale matches the template formula 1:1: **BP** (max 30 pts) A≥29,
     B≥26, C≥23, D≥20, **E≥18**, else FX; **DP** (max 35 pts) A≥33, B≥30,
     C≥27, D≥24, **E≥21**, else F. The E threshold is **60 %** for both.
   - *Plagiarism* (supervisor) — prefilled from the thesis
   - *Overall evaluation, comments and questions* — a new review gets a
     **skeleton** (thematic headings by role and template language); the
     **🦴 Insert review skeleton** button inserts it manually too. There is
     also Czech **spell checking**: unknown words are underlined red,
     right-click offers corrections. If the dictionary is missing, a
     **⬇ Download the Czech dictionary** button fetches it from LibreOffice.
   - *Place, date* — place from the profile (default Zlín), today's date
3. **Save & produce XLSX + PDF** — the data is saved into the thesis (JSON),
   the XLSX template is filled and (with LibreOffice installed) a PDF is
   generated. Both files are attached as review attachments. A progress
   window is shown during generation; it runs in the background.
4. **After generation** the window stays open with **📄 Open XLSX**,
   **📕 Open PDF** and **📂 Show in Finder** actions. The thesis document
   list refreshes immediately.

The review data is the *source of truth* in JSON — XLSX/PDF can be
regenerated any time. A review preview is in the **Overview** tab.

> **Review archiving:** exactly **one current** review is kept. On
> regeneration the previous **XLSX moves** to `posudky/archiv/` (renamed with
> a timestamp) and the older **PDF is deleted** (it's just a derivative).

> **Template fidelity 1:1:** the filled XLSX is **identical to the template**
> — only the filled cells change. The faculty logo, formatting, layout and
> print settings stay untouched.

> **PDF:** requires LibreOffice (`brew install --cask libreoffice`).
> Without it only the XLSX is generated.

> **Logo in the PDF:** if the template logo is an *"image in cell"* (Excel's
> *Place in Cell*), LibreOffice cannot render it. The app handles this
> automatically — the logo is converted to a classic image on a temporary
> copy, so the PDF looks like an Excel export. The PDF is also **polished**:
> the table stretches to the page width, the logo is centred and the
> *"Points (0–5)"* column header gets a smaller black font.

---

## Review template library

The **📝 Review templates** toolbar button manages the profile's XLSX review
templates (copies in `profile_dir/templates/`).

- **Adding a template** — after picking an XLSX the app **auto-detects** the
  type (BP/DP), role (supervisor/opponent), language (CZ/EN), programme and
  academic year from the header and the *Configuration* sheet; it also
  suggests a name. The criteria structure (weights, score cells) is scanned
  and stored.
- **Grouping** in the list: 📘 BP / 📗 DP → programme → templates
  (alphabetical). Role icon (🎓 supervisor / 🧐 opponent), 🇬🇧 EN indicator.
- Templates travel with the profile in ZIP exports.

---

## Opposed theses

A separate **🧐 Opposed theses** tab for theses you **oppose** (reviewing
someone else's BP/DP). Its own model — inline student and supervisor info
(via the supervisors registry with autocompletion), **programme** (a dropdown
of registered programmes — keep it registered so the review pairs with a
secretary), grades, documents, a generated overview. **The Overview also
shows the written review** (points, percentages, suggested grade, criteria,
comments). **Grades fill themselves:** the *opponent* grade from the written
review, the *supervisor* grade is read from the uploaded **supervisor review
PDF** — **Czech and English** (Czech "Navržená známka: D", English "suggest
the following evaluation: B" / "suggest classification with grade B").
Overview sections: Objectives → Grades → Written review → Documents.
**The document list is exactly the same as for supervised theses** —
aggregated tree by type, versioning, **📂 In Finder**, right-click menu,
missing-file indication and **🧹 Clean up missing**. Review archiving works
the same way.

---

## Topic proposals

A separate **💡 Topic proposals** tab (after *Opposed theses*) lists
**potential topic ideas** — incomplete ideas nobody works on yet. They have
**no student or status** and the **academic year is irrelevant**. The tab
title shows the **count**.

Each proposal has a **title, description, objectives, references, programme**
and **type (BP/DP)**. Optionally tick **🔒 Reserved** and note **for whom**
(free text).

- **The list** on the left is grouped into *Bachelor's* / *Master's*;
  reserved ones show 🔒 and for whom.
- **The detail** has a **📋 Overview** (with copy-to-clipboard buttons) and
  **✏ Detail** (editor; save via **💾 Save**).
- **➕ New proposal** adds an empty proposal and opens the editor.
- **🎓 Convert to a supervised thesis** creates a **real supervised thesis**
  from the proposal (title, description → annotation, objectives, references,
  type; status *Candidate with topic*, current academic year) and **removes
  the proposal**. *The programme is not carried over — it belongs to the
  student you assign later.*

---

## Sending reviews to the secretary by e-mail

Finished review PDFs can be sent to the programme secretary directly from the
app. The toolbar has **✉ Send reviews** with a choice:

- **🎓 Supervisor's reviews (supervised theses)** — reviews you wrote as the
  supervisor.
- **🧐 Opposed theses** — reviews you wrote as the opponent.

In the dialog:

1. **Pick a secretary** — secretaries filled in for programmes are offered.
   Theses are filtered by her programmes (matching the programme **name and
   STAG code**). The e-mail salutation comes from the programme.

   > When a thesis programme doesn't match the secretary, nothing is offered.
   > Tick **Also show theses of other programmes** — everything with a
   > finished review appears (programme marked red) and you pick manually.
2. **Thesis list** — only theses with a **finished review PDF** are offered.
   For supervised theses **only current ("In progress")** ones; for opposed
   theses **only the current academic year**. Unsent ones are pre-checked,
   **already sent** ones are hidden by default (tick *Also show already sent
   reviews* to resend). BP and DP can be sent together.
3. **E-mail preview** — the subject and body are composed automatically
   (greeting + the thesis list grouped into bachelor's / master's). The text
   is **editable**; *↻ Regenerate text* rebuilds it from the selection.
4. **Copy to me** (default on) — sends a copy to your address. Optionally
   tick **Append a note about the app** (a BPDPManager footer line, default
   off).
5. **🧪 Test — send only to myself** — a *dry run*: sends the exact e-mail
   (incl. PDFs) **only to you** for checking. Reviews are NOT marked as sent.
6. **✉ Send…** — after confirmation you are asked for the **password**
   (never stored) and the e-mail with **PDF attachments** is sent. Sent
   theses are marked as *sent*.

### E-mail settings (SMTP)

**👤 → ✉ E-mail settings (SMTP)** — a standalone outgoing-mail manager:
sender e-mail, **SMTP server / port / security** and a **🔌 Connection test**
button (logs in without sending). Defaults match **UTB Office365**
(`outlook.office365.com`, port 587, STARTTLS). **The password is never
stored.**

> **Note on UTB Office365:** UTB requires **OAuth2** for outgoing mail, so a
> direct SMTP password login may fail. On failure the app offers to **create
> a ready e-mail (.eml) and open it in your mail client**
> (Outlook/Thunderbird) where you are logged in via OAuth2 — just hit
> *Send*. Reviews can then be marked as sent.

---

## Printing reviews

Finished **review PDFs** print straight from the app — the **🖨 Print
reviews** toolbar button. Choose the **destination** in the dialog:

- **MyQ (`myq.utb.cz`)** — sends reviews into the university print queue
  (pick them up at any multifunction device with your card/PIN). Enter your
  MyQ **name + PIN** (never stored). MyQ used to send an **incomplete
  certificate chain** (missing GÉANT/HARICA intermediate) — it is now
  **bundled** with the app, so TLS verification usually passes. If it still
  fails, printing **automatically reconnects without verification** (MyQ is
  an internal trusted server) and says so; the manual *Verify the server TLS
  certificate* toggle remains as a safety.
- **System printer** — prints on a system-configured printer (macOS/Linux
  via CUPS). Pick the printer and optionally *Double-sided*.

In the dialog:
- **Select reviews.** Theses with a **finished PDF review** are offered from
  currently supervised (supervisor's review) and this year's opposed theses
  (opponent's review), split into **🖨 To print — not printed yet**
  (pre-checked) and **✓ Already printed** (separate list, unchecked — for
  reprints). Each group has **🎓 Supervisor's** and **🧐 Opponent's**
  sub-groups. *Select all / Deselect all* helps.
- **🖨 Send to print** first **asks for confirmation** (how many and where),
  then prints the selected PDFs one by one. A **summary** is shown at the
  end and the dialog **asks whether to mark them as printed** (reflected in
  the *Printed* column).

> **Tip — printing selected theses only.** Right-click **selected theses**
> (in *Currently supervised theses* or *Opposed theses*) and choose
> **🖨 Print review** — the same dialog opens, but **with only the chosen
> theses**. Works for one or many; theses without a finished PDF are skipped.

> **Note:** the MyQ connector talks directly to `myq.utb.cz`. If UTB
> significantly changes the interface, you can always print manually via the
> web (prepare PDFs via **📄 Export my review PDFs**) or use a system
> printer.

---

## Import from STAG (CSV)

The **📥 Import from STAG…** toolbar button can either **download a thesis
directly from STAG** or load a manually downloaded CSV export
`getKvalifikacniPrace*.csv`.

### A) Download directly from STAG (recommended)

> **All my theses in bulk:** the import dialog has **🎓 My supervised
> theses…** and **🧐 My opposed theses…** buttons. Each opens a dialog
> **locked to that role**. They find **all** theses of the role in STAG by
> your profile name (historical, current and listed for next year), sorted
> **by academic year**. A surname may be ambiguous, so the **"Only my theses
> (by full name)"** filter is on by default (can be turned off). Then just
> tick what to import.
>
> **Really all of them load.** STAG paginates search results implicitly
> (returning only the first page) — the app disables pagination and loads
> the **complete** list.
>
> **A clear table.** Found theses are listed with columns **Thesis · Type ·
> Academic year · Defense · Opponent · Status**. The defense date and status
> come straight from STAG. **Academic year and programme** are
> **auto-fetched from each thesis detail** after the search (progress
> window, can be interrupted) — so the year shows **even for unfinished**
> theses.
>
> **Grouping.** The **"Group by"** selector groups theses by **status, type
> (BP/DP), programme, academic year** (or no grouping). Ticking a group
> header (de)selects the whole group.
>
> **Attachments (📎).** The count and size of attachments appears **once you
> tick a thesis** (e.g. "📎 4 · 14.0 MB"). The **download** itself shows
> **progress** (which thesis and attachment, incl. downloaded/total MB for
> large files) and can be **interrupted** — temporary files are cleaned up.
> Failures are listed. Downloads run **in the background**, so the window
> never freezes (Cancel always works). The timeout **scales with file size**
> (a large attachment gets more time — even hundreds of MB / GB download
> fine; a small file fails fast when truly stuck). If something still times
> out, the app reminds you that **files can always be downloaded manually
> from STAG** (via the browser) and added in **📎 Documents**. Before
> downloading, the app **offers to delete leftover temporary files** from
> earlier runs. When attachments would take **a lot of space** (hundreds of
> MB+, typical for bulk downloads), it asks whether to download attachments
> or **import data only**. What gets imported (and excluding large
> attachments) is chosen in the **file preview** in the next step.
>
> **"✓ already have" — what re-downloading does (merge).** Theses already in
> the database get a **✓ already have** badge and are **unticked** by
> default. If you **tick and download** them, NO duplicate is created — the
> thesis is **paired and updated**:
> - **Pairing:** primarily via the **STAG ID (`adipidno`)**, otherwise via
>   *student + academic year + type (BP/DP)*. A repeat attempt (regular +
>   retake with the same student but a different STAG ID) stays a
>   **separate** thesis.
> - **Field merging:** **filled** STAG values are taken (CZ/EN title,
>   annotation, objectives, references, supervisor/opponent, year); where
>   STAG has nothing, **your existing value stays** (nothing is overwritten
>   with emptiness).
> - **The thesis status does NOT change** for existing theses.
> - **Attachments** are attached; two **different** attachments get
>   distinguishable names (from the original name, not `_v2`), **identical
>   content** is not added twice, and reviews are archived.
> - A `before-stag-import` backup is created and the whole import can be
>   **rolled back** via *"↩ Roll back the whole import"*.

### 🔄 Silent STAG check (in the background)

After app start (automatically **at most once a day**) the **current
academic year** is compared with STAG in the background; the result shows in
a **banner above the tabs**. You can also run it manually via
**🔄 Update theses → Check STAG changes**. It watches:

- **status changes** or a **missing document kind** for supervised theses
  *In progress*,
- the same for **current-year opposed theses**,
- **new theses in STAG** you don't have yet — paired by **full name**, so
  namesakes don't count.

The banner always shows a result — even **"✓ everything up to date"**. On
changes, a **🔄 badge** lights up on the *Currently supervised* and
*🧐 Opposed theses* tabs. **🔎 Details…** opens a **quick preview** — which
theses changed (status, thesis text, reviews, **defence record**), which new
theses STAG offers, and (for verification) the list of **checked,
up-to-date** theses. From the preview you continue directly: **🔄 Update
supervised (N)…** / **🔄 Update opposed (N)…** open the **STAG update with
the affected theses only** — proposals (status change, missing files) come
pre-filled and pre-checked, just confirm. **📥 Import from STAG** remains
for **new theses** you don't have in the app yet. The check is
**read-only**; offline it reports quietly.

### 🔍 STAG consistency (what's missing)

The **🔍 STAG consistency** toolbar button (Import group): walks theses
(supervised and opposed) with a STAG ID, compares them with STAG and lists
where **STAG offers a document kind** (full text / attachment / review)
**missing in the database**. **Future theses** are not checked. Missing
files are **pre-checked** and **⬇ Download selected (missing)** fetches and
attaches them (with a backup). **Progress** runs **inline in the list** —
each file shows downloaded/total, then **✓ downloaded** (or **✗ error**).
For large / ZIP attachments STAG first **prepares** the file (the row shows
*"STAG is preparing the file…"*) — the timeout **adapts to file size**.
Theses **without a STAG ID** and any **query errors** are listed separately.

> **Download progress.** Before STAG starts sending data, the progress shows
> **"⏳ connecting to STAG…"** — not a freeze, just waiting for the server.
> A short outage is **retried once**.

### 🧹 Cleaning duplicate attachments

**🔄 Update theses → 🧹 Clean duplicate attachments**: walks **supervised
and opposed** theses and finds **attachments** (*Thesis attachments* and
*Other*) whose **content is identical** to another attachment of the same
thesis — typically the same file downloaded from STAG **twice** under
different target names. Matching uses **size and content** (checksum), not
the name. **Thesis texts and reviews are never touched.**

A **preview** opens: for each thesis it lists **which files get deleted**
and **which copy stays**, with sizes. Everything is **pre-checked**
(adjustable). **🗑 Remove selected** deletes the chosen attachments (file +
record), always keeps one copy and marks the rest as **current**. With no
duplicates, the window reports *"✓ No duplicate attachments found."*.

> **Prevention.** Since 1.10.0 a duplicate attachment is **never created
> again**: downloading an attachment whose content the thesis already has
> does **not attach it twice**. A new attachment **version** appears only
> when the **content really changes**.

### 🔧 Fixing text/attachment classification

**🔄 Update theses → 🔧 Fix text/attachment classification** fixes two
leftovers of older STAG downloads (where the kind was determined only by
file **order**):

- **↔ Swap** — an archive (zip) classified as **Thesis text** and a PDF as
  an **Attachment**. The fix **reclassifies the PDF as Thesis text** and
  **the archive as an Attachment** (`text-prace/` ↔ `prilohy/`).
- **📦 Bundle** — an archive as **Thesis text** with **no separate PDF**
  (text and attachments in one zip). Reclassified to **Thesis text +
  attachments**.

A **preview** opens with both fix kinds, everything **pre-checked**.
**🔧 Fix selected** reclassifies and **renames/moves** files into the right
subfolder — **contents are unchanged**. A **backup** is made first. Only
**unambiguous** cases are fixed; unclear ones are **skipped**.

> **Since 1.11.0** the text vs. attachment kind is detected correctly at
> download time; this button mainly fixes theses downloaded earlier.

Or classically via **🌐 Download from STAG**:

1. Enter the **student's surname** (optional).
2. Enter the **supervisor's or opponent's surname** and switch the *role*
   (Supervisor / Opponent) — the second surname narrows the search. Your
   profile surname is prefilled.
   - **Bulk by supervisor/opponent:** leave the **student surname empty**
     and enter only the supervisor/opponent — STAG finds **all their
     theses** and you can import several at once.
3. **🔍 Search in STAG** → **tick the theses** you want. Each has a
   **🆕 new** / **✓ already have** badge — new ones are pre-checked. You can
   download e.g. a student's **BP and DP** in one step.
4. **⬇ Download selected (N)** → all ticked CSVs download and merge into one
   preview; each thesis gets its own CSV attached. The thesis's **public
   files download automatically** too (see below).

The search uses the public *Browse → Qualification theses* on
**stag.utb.cz**, so no login is usually needed.

### Updating already-registered theses from STAG

During the semester theses often gain a new file (submitted thesis, review)
or change status. Two buttons in *Import from STAG…* handle this:

- **🔄 Update in-progress theses from STAG** — walks **supervised theses
  *In progress***, finds them in STAG (by stored STAG ID, falling back to
  the **student's surname**) and offers:
  - a **status change** — when STAG reports a different status (e.g. *In
    progress → Defended*); applied **only when ticked**;
  - **downloading missing files** — files whose **kind** the thesis lacks
    are pre-checked (typically a new review / submitted thesis).
- **🔄 Update opposed theses from STAG** — the same for **current-year
  opposed theses** (files; also fills the STAG status into the *Status*
  column for previously downloaded ones).

Everything runs with a **progress window** and a tickable change list. A
**backup** is made before writing and the summary has **"↩ Roll back all"**.
Theses **without a STAG ID** that can't be found by surname are **skipped
and listed**.

> **🔄 Updating ONE thesis from STAG (right-click).** Any thesis — supervised
> (*Current / Future / History / All*) or opposed — has **"🔄 Update thesis
> from STAG…"** in its context menu. It compares **just that one** thesis,
> shows the proposed changes (status + missing files) and applies only the
> selected ones (with a backup). Works **even from History**. When
> everything is current, the dialog says so.

> **Bulk actions over multiple theses (multi-select).** Select several
> theses (**Ctrl/Shift** click); right-click offers — in supervised and
> opposed: **🔄 Update N theses from STAG** (one dialog, selected only),
> **📄 Open thesis texts**, **📘 Open supervisor's and opponent's reviews**,
> **✉ Mark / unmark as sent**, **🖨 Mark / unmark as printed** and
> **🗑 Roll-back — delete N theses** (single confirmation). With one
> selected thesis the full per-thesis menu is available.

> **Careful — "Update" only refreshes theses you already have.** New theses
> (e.g. for a **new academic year**) won't appear here. Use the **🆕 Find
> new theses…** button in the *Update…* dialog (opens the bulk search *My
> supervised theses… / My opposed theses…* with **🆕 new / ✓ already have**
> badges). When there is nothing to update, the dialog points this out.

### Thesis files (full text, attachments, reviews)

When STAG offers files for a thesis, they download with it and a **📎 file
preview** opens:

- typically the **full thesis text**, **attachments**, the **supervisor's
  review** and the **opponent's review** (not always all available),
- every file is **pre-checked** — untick what you don't want (**☑ All** /
  **☐ None** buttons),
- the **attachment kind** is estimated from STAG; override it in the last
  column if needed.

> **Large attachments.** If an attachment is large (over ~25 MB), the app
> **asks before downloading** and lists the sizes. Choose *⬇ Download
> anyway* or *Skip large* (the rest downloads normally).

The selected files are **attached to the right thesis** after import
(paired via STAG ID) as attachments of the right kind — visible in
**Documents**. For opposed theses, the **suggested grade is read** from the
supervisor review PDF — preferring the structured **"Navržená známka"
field** (the loose wording in the *Overall evaluation* is ignored); older
reviews without that field fall back to the suggestion sentence.

> **📎 Download files only:** when the thesis is already in the database and
> you only want files, use the **📎 Download files only** button in the
> search window. It downloads files and attaches them to the matching
> thesis (paired by STAG ID, else name + type). Warns if the thesis isn't
> found.
>
> **🏷 Update statuses only:** next to it, **🏷 Update statuses only**
> updates **just the status** of ticked already-known theses from STAG (no
> file downloads). Supervised theses get *Defended / Failed defense / Not
> completed / …*; opposed theses the STAG status. Fast — also fixes the
> retroactive *Not completed → Failed defense* reclassification. Shows a
> summary of changed statuses.

> **BP × DP:** BP and DP are separate records (paired by type), so importing
> a DP **never overwrites** a previously imported BP. Theses are also paired
> by the **STAG ID (`adipidno`)**, so re-importing the same thesis reliably
> *updates* it instead of duplicating.

> **Note:** the public STAG CSV export **lacks the student's name** (only
> the personal number). The app fills it from the search result.

> **Repeat attempt (regular + retake):** when a student has two theses of
> the same type (e.g. regular *Not completed* + retake *Defended*, each with
> its own STAG ID), the import **never merges or overwrites them** — they
> stay **two separate records** (each with its review and files). The app
> also **links them** (regular ↔ retake) and marks them **🔁** in the list
> and the Overview. Both live in *History* by their status. Statistics
> count *repeat attempts*.

### B) Manually downloaded CSV
1. Open **stag.utb.cz** → **Browse** → **Qualification theses**
2. Find the thesis by the student's name and choose **download CSV**
3. In the app pick the file via *Import from STAG… → Browse…*

(The same guide is under the **❓ Where to download** button in the import
dialog.)

### Import flow

- **Role auto-detection** by *Your name* (from the profile) in
  `vedouciJmeno` / `oponentJmeno` → the thesis is classified as supervised
  or opposed.
- A **preview** with per-row choice of role, programme mapping (STAG code →
  local programme), status and action (Create / Update / Skip). The status
  is prefilled from the STAG code (`R`, `DBPOO` → In progress; `DUO` →
  Defended; `DBUO`, `ND` → Not completed) or from dates. For an **unmapped
  programme** (amber row) pick an existing programme or **"➕ New
  programme…"** (the STAG code is prefilled). A newly created programme is
  **immediately offered in other rows** and pre-selected for rows **with
  the same STAG code**.
- **Students** — for supervised theses a missing student is created and
  assigned automatically. The **✎ Check / complete new students before
  creating** option opens each new student's card (e-mail, phone,
  programme…) — saved as part of the import. *(For opposed theses the
  student is stored inline, not as a separate entity.)*
- A **Summary before import** shows which entities (students, opponents,
  supervisors, programmes) will be created.
- **Transactional** — everything writes once at the end; errors roll back.
- **Emergency brake:** a `before-stag-import` backup is created just before
  the import and the summary window offers **↩ Roll back the whole import**
  (the imported state is first backed up as `before-restore`, so even the
  rollback can be undone). Backups are also managed in **👤 → 💾 Backups**.
- The original CSV is attached to every imported thesis.
- After the import the app jumps to the imported thesis.

The STAG programme code is managed in the *Programmes* dialog (the *STAG
code* field).

---

## Faculty schedule

The **📅 Schedule** tab — import of the FAI UTB PDF time plan, automatic
extraction of key deadlines (BP/DP submission, finals, graduation, exam
period). A yellow panel shows important deadlines in the next 60 days.

---

## SZZ committees

The **🏛 Committees** tab shows **state final exam committees** by academic
year: **composition** (chair, vice-chairs, secretary, members) and the
**student schedule** (when each student defends). Committees use the
faculty's **colour coding** (red, blue, yellow, green, purple…) — the tree
and detail show them in their colour. Each committee is linked to an app
**programme** (SWI / NSWI / NKYB / NUI …), which disambiguates committees of
the same colour and level (e.g. *Mgr purple* is both **NKYB** and **NUI**).

The left tree is grouped **academic year → level (Bc / Mgr) → committee
(colour)**; the **Dates** column shows the days the committee sits. The
**Students S/O** column shows how many you **supervise** (blue badge) and how
many you **oppose** (red badge). Column and panel widths fit the content.

- **Composition is pre-loaded** — **public data** (colour, programme, level,
  members, dates) ships with the app in `resources/komise_szz.json` and
  **loads on startup**. No student names live there; those come only from
  local PDF import (below). The file is in git, so it updates with the app.
- **📄 Import committee PDFs…** — loads faculty PDFs, typically the **student
  schedule** (names + personal numbers). The committee is recognised by the
  **heading colour** and **programme** (from the programme/specialization
  text), and students attach to the right pre-loaded committee. Composition
  PDFs work too (merge by year + level + **programme** + colour). A **checkbox
  preview** is shown before saving; re-imports create no duplicates.
- **Highlighting your students:** in the schedule, **🎓 supervised** students
  (matched via the **personal number** Axxxxx, name as fallback) are green
  and **🧐 opposed** ones (by name) purple. The *My students* column shows
  counts; the *Only committees with my students* filter hides the rest.
- **⭐ Your committees:** committees where you are a member (by your profile
  name) get a star in the tree, the detail title and next to your name.
- **Committee composition** colour-codes the role: **chair** (purple),
  **vice-chair** (blue), **secretary** (green), **member** (grey).
- **🔄 Reload committees** — deletes all committees and loads the clean
  composition shipped with the app. Handy to **clean up older imported
  committees** (from versions before 2.5.0) that don't match (missing
  programme, duplicates, mixed colours). Student schedules from previously
  uploaded PDFs disappear — just **import them again** via *📄 Import
  committee PDFs…* (they attach to the right committees).
- PDFs are stored **structured** in `komise/<year>/` inside the profile
  folder; links to source PDFs are in the committee detail. Right-click a
  committee → *Delete committee* (PDFs stay on disk).

> **Supervised/opposed highlighting is unchanged** — it works on the schedule
> (student slots), so it kicks in as soon as you import the schedule (personal
> number Axxxxx for supervised, name for opposed).

---

## Application language (CZ / EN)

The **🌐** toolbar button switches the app language between **Czech**
(default) and **English**. The choice is stored in the profile and takes
effect **after a restart** (offered right away). The whole UI (main surface,
details, all dialogs, tooltips) and this complete help are translated.

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
- **🌐 Open in STAG** — right-click a thesis (supervised or opposed) to open
  its STAG detail in the browser. The link is **filled automatically** for
  STAG theses (derived from the STAG ID) — retroactively too, via a silent
  startup migration. A manually entered *STAG* link is never overwritten.
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
