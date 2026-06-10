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
  > bulk **export**, **send in one e-mail** or **🗑 bulk remove** them.
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
PDF**. Overview sections: Objectives → Grades → Written review → Documents.
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

> **🌐 Translation in progress.** The following section (STAG import) is
> not translated yet and is shown in Czech. It will be translated in an
> upcoming update.

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

---

## Faculty schedule

The **📅 Schedule** tab — import of the FAI UTB PDF time plan, automatic
extraction of key deadlines (BP/DP submission, finals, graduation, exam
period). A yellow panel shows important deadlines in the next 60 days.

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
