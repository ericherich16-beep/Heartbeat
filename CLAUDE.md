# CLAUDE.md — JQC/PWI Management (Power Apps Solution)

> Build brief for Claude Code. Read `intake.md` for background. If the two conflict, **this file wins**.
> `SPEC.md` holds the detailed functional spec (numbered business rules, acceptance criteria, assumptions, open questions) and the product owner decision log. Keep the two in step.

## 1. Project Summary
**App name:** JQC/PWI Management

**Problem today**
- JQCs (Job Qualification Checklists) and PWIs (Process Work Instructions) are stored in Teams/SharePoint folders that nobody uses.
- An Excel matrix is the only record of who is signed off on what, and it is updated by hand.
- There is no shared view of who needs which training, and managers can't easily manage their team's training.
- When a PWI is revised, there is no reliable way to make sure everyone signs off on the new revision.

**Goal**
One app where:
- managers add JQCs and PWIs, designate trainers and assign them to employees
- technicians view their documents, sign off on PWIs and see what is still pending
- everyone assigned to a PWI must sign off again whenever it is revised
- everyone can see who is qualified to do what, including cross-training coverage

**Success means**
- It is easy to see who still needs what signed off, including re-signs after a PWI revision.
- It is easy to add documents and review sign-offs.
- Cross-training gaps are visible at a glance.
- The matrix reflects sign-offs on the **current revision** only.

---

## 2. HARD RULES — No Confidential Data
These rules override everything else in this file.
- **Never** include real employee names, emails, IDs, customer names, part numbers, JQC/PWI titles or content, or company URLs.
- All sample/seed data must be **fictional**, e.g. `JQC-DEMO-100`, `PWI-DEMO-001`, `Tech A`, `manager1@contoso.com`.
- **No hard-coded URLs, tenant IDs, site names or list/library GUIDs.** Use **environment variables** only (Section 10).
- No credentials, secrets, keys or tokens anywhere in the repo.
- If a task appears to need real data, use a placeholder marked `TODO:` instead.
- `.gitignore` must exclude `*.env`, `*.secrets*`, `/exports/` and any `*.zip` not built by this project.

---

## 3. Constraints
- **Standard connectors only:** SharePoint, Office 365 Users, and Power Automate with the Power Apps (V2) trigger. No premium connectors, no Dataverse, no custom connectors, no PCF/code components.
- **Responsive on all devices:** phone (portrait), tablet (both orientations) and desktop. Use responsive containers only; don't use fixed X/Y positions for layout.
- **No required outputs:** no Teams posts, emails or Hour by Hour rows. Pending and re-sign items show in the app only.
- **Deliverable:** an importable Power Apps solution with environment variables for all site and list references.

---

## 4. Build Approach
Claude Code builds the **importable solution `.zip` itself** with the Power Platform CLI (`pac`), the same method that produced a working app in an earlier project (product owner decision D-02 in `SPEC.md` §8).
- `pac canvas pack` is marked deprecated by Microsoft, but it still ships in `pac` 2.14.
- Every generated `.msapp` is checked by a round trip (`pac canvas unpack`, then compare) before it goes into the solution.
- If Studio ever refuses the generated app, the fallback is to paste per-screen `.pa.yaml` into Studio.

| Component | Claude Code produces | User does |
|---|---|---|
| Toolchain | `/tools/setup-pac-linux.sh`, which gets `pac` and the .NET runtime from nuget.org in a container with no .NET | On a PC: install `pac` normally (only needed to rebuild) |
| SharePoint lists and libraries | **Manual guide** `/provisioning/Manual-Setup.md` (the user's tenant blocks the SharePoint `HttpRequest` action, so the setup flow can't be turned on there). Also available: the **setup solution** `/solution/dist/JQCPWISetup_*.zip`, built by `/solution/build_setup.py`. It holds one flow, "JQCPWI - Setup SharePoint Lists", which uses only the standard SharePoint connector. **Or** the PnP PowerShell script `/provisioning/Create-Lists.ps1`. Both build the same schema; `build_setup.py` checks that they match | Import the setup zip and run its flow once with the site address (or run the script) |
| Solution project | `/solution/JQCPWIManagement/` (from `pac solution init`, publisher prefix `jp`) and `/solution/build.py`, which generates components and runs `pac solution pack` | — |
| Environment variables | Defined in the solution by `build.py` with **no values**. Documented in `/solution/env-vars.md` | Pick the site and lists in the import wizard |
| Canvas app | Generator `/app/build_app.py`. It writes `.fx.yaml` sources using control templates from a Microsoft sample `.msapp`, runs `pac canvas pack`, and adds the app to `CanvasApps/` with SharePoint data sources bound to the environment variables. `/app/App.fx.md` documents the named formulas, role logic, status logic and theme | Open in Studio after import, check, publish |
| File upload flow | Flow definition in the solution's `Workflows/`, using a SharePoint connection reference and the environment variables. Build spec `/flows/JQCPWI-UploadFile.md` | Turn the flow on after import |
| Seed data | `/seed/*.csv`, **fictional only**, plus `/seed/expected-results.md` and `/provisioning/Import-SeedData.ps1` | Optional import to a test site |
| Docs | `README.md`, `Admin-Guide.md`, `Technician-Quick-Guide.md` | — |

**Output:** `/solution/dist/JQCPWIManagement_<version>_unmanaged.zip`. The user imports it at make.powerapps.com → **Solutions** → **Import solution**. Each build step bumps the version and rebuilds the zip.

---

## 5. Roles
The role is stored on the employee record (`JP_Employees.AppRole`).

| Capability | Manager/Supervisor | Technician | Viewer |
|---|:-:|:-:|:-:|
| View the matrix, cross-training view and document libraries | ✔ | ✔ | ✔ |
| View and download JQC templates, PWIs and sign-off files | ✔ | All templates/PWIs; own sign-off files | ✔ |
| See own pending assignments (including re-sign-offs) | ✔ | ✔ | — |
| Sign off on an assigned PWI (self sign-off) | ✔ | ✔ | — |
| Upload the PWI training log on own assignment | ✔ | ✔ | — |
| Add or edit employees and set their role | ✔ | — | — |
| Add or revise JQCs and PWIs and upload their documents | ✔ | — | — |
| Designate trainers for each JQC/PWI | ✔ | — | — |
| Assign JQCs/PWIs to employees | ✔ | — | — |
| Put an employee into training on a JQC (Needs Training → In Training) | ✔ (not own) | — | — |
| Sign off on a JQC (verify qualification and upload the signed JQC) | ✔ (not own) | — | — |

**Trainer is not an app role.** Trainers are employees that a manager designates on each JQC/PWI (Section 6.2). Their names show on the document and the assignment so trainees know who to go to.

**Role resolution:** match `User().Email` to `JP_Employees.Email`.
- If there is no match, or the employee is inactive, the user gets Viewer access.
- Controls are hidden or disabled by role. The SharePoint permissions in Section 9 back this up.

---

## 6. Data Model
All list and library names use the prefix `JP_`. Use internal column names without spaces, and make each **display name the same as the internal name** (`Title` keeps its default name). Index every column used in filters.
**Never use the SharePoint action "Send an HTTP request to SharePoint" (`HttpRequest`)**: the tenant's data policy blocks it (`SPEC.md` A-28).
In the two document libraries, ✔ columns are enforced by the app and the upload flow rather than set as required in SharePoint (`SPEC.md` A-21).

### 6.1 `JP_Employees` (list)
| Column | Type | Req | Notes |
|---|---|:-:|---|
| Title | Text | ✔ | Display name |
| Email | Text | ✔ | Unique; used for role lookup |
| EmployeeUser | Person | | Optional link to M365 user |
| JobTitle | Choice | ✔ | Production Technician, Quality Technician, Supervisor, Manager, Other |
| Department | Choice | | Production, Quality, Other |
| Shift | Choice | | 1st, 2nd, 3rd, Days |
| Supervisor | Lookup → JP_Employees | | Used for "My Team" filtering |
| AppRole | Choice | ✔ | Manager/Supervisor, Technician, Viewer |
| Active | Yes/No | ✔ | Default Yes. Never delete employees; set Active = No instead |

### 6.2 `JP_Documents` (document library: JQC templates and PWIs)
| Column | Type | Req | Notes |
|---|---|:-:|---|
| Name (file) | File | ✔ | JQC: the blank template. PWI: the work instruction |
| DocType | Choice | ✔ | JQC, PWI |
| DocNumber | Text | ✔ | e.g. `JQC-DEMO-100`, `PWI-DEMO-001` |
| DocTitle | Text | ✔ | |
| Revision | Text | ✔ | Always the **current** revision |
| RevisionDate | Date | ✔ | Date the current revision was released in the app |
| RevisionNotes | Multi-line text | | What changed (shown to employees when they re-sign) |
| Area | Choice | | Production, Quality, Metrology, Other (editable list) |
| Status | Choice | ✔ | Active, Obsolete |
| Trainers | Person (multi) | | Designated trainers. Required before the document can be assigned |
| Description | Multi-line text | | |

Turn on library versioning (major versions). A new revision **replaces the file in place** (same item ID), so DocumentID stays the same across revisions and older files stay in version history.

### 6.3 `JP_Assignments` (list: one row per employee per document **revision**)
| Column | Type | Req | Notes |
|---|---|:-:|---|
| Title | Text | ✔ | Auto-generated: `DocNumber Rev X – Employee` |
| Employee | Lookup → JP_Employees | ✔ | |
| EmployeeEmail | Text | ✔ | Copy kept for delegable filtering |
| DocumentID | Number | ✔ | ID of the JP_Documents item |
| DocType | Choice | ✔ | JQC, PWI (copied from the document) |
| DocNumber / DocTitle | Text | ✔ | Copied from the document |
| RevisionAssigned | Text | ✔ | Revision this row must be signed against |
| AssignmentReason | Choice | ✔ | New Assignment, Revision Change (PWI or JQC revision) |
| PreviousAssignmentID | Number | | Links a re-sign row to the row it replaced |
| IsCurrent | Yes/No | ✔ | Yes = the employee's live row for this document. Exactly one current row per employee per document |
| AssignedBy | Person | ✔ | |
| AssignedDate | Date | ✔ | |
| DueDate | Date | | Optional; Revision Change rows (PWI and JQC) default to Today() + `ResignDueDays` (Section 7 rules 8–9) |
| Trainer | Person | | Picked from the document's Trainers |
| Status | Choice | ✔ | Assigned, In Training, Signed Off, Superseded, Removed |
| SignedOffBy | Person | | PWI: the employee (or a manager). JQC: the manager/supervisor |
| SignedOffDate | Date/Time | | |
| SignoffFileID | Number | | ID of the file in JP_SignoffRecords |
| Comments | Multi-line text | | |

Index: EmployeeEmail, DocumentID, Status, DocType, IsCurrent.

### 6.4 `JP_SignoffRecords` (document library: completed evidence)
| Column | Type | Req | Notes |
|---|---|:-:|---|
| Name (file) | File | ✔ | JQC: the filled-out, signed template. PWI: the training log |
| AssignmentID | Number | ✔ | Links back to JP_Assignments |
| DocType | Choice | ✔ | JQC, PWI |
| Revision | Text | ✔ | Revision signed against |
| EmployeeEmail | Text | ✔ | |
| UploadedBy | Person | ✔ | |

File naming convention: `{DocNumber}_Rev{Rev}_{EmployeeID}_{yyyyMMdd}_{HHmmss}.{ext}`. Use the employee's list ID, never their name. The time keeps names unique when evidence is replaced on the same day.

### 6.5 `JP_Settings` (list: single row)
| Column | Type | Notes |
|---|---|---|
| MinQualifiedPerTask | Number | Cross-training target. Default 2 |
| ResignDueDays | Number | Days allowed to re-sign after a PWI revision, or to requalify after a JQC revision. Default 14 |

---

## 7. Business Rules
1. **Required fields** are the ones marked ✔ in Section 6. Validate them in the form before submit and show the missing fields in plain language.
2. **Only Manager/Supervisor** can add or edit employees, add or revise documents, designate trainers and create assignments.
3. **Assign:** a manager picks one or more employees and one or more Active documents, which bulk-creates `JP_Assignments` rows.
   - Each new row gets `RevisionAssigned` = the document's **current** revision, `AssignmentReason` = New Assignment and `IsCurrent` = Yes.
   - Block duplicates: an employee cannot have two current (`IsCurrent` = Yes) rows for the same DocumentID.
   - Documents with no designated trainer cannot be assigned.
   - Employees assigned in the future always sign off against whatever revision is current at that time.
4. **PWI sign-off (self):**
   - Only the assigned employee (or a manager) can sign.
   - The employee opens the PWI, uploads the training log and then taps **Sign Off**.
   - The app sets Status = Signed Off, SignedOffBy = current user, SignedOffDate = Now() and SignoffFileID.
   - The Sign Off button stays disabled until the training log is uploaded.
   - **Sign Off is blocked if `RevisionAssigned` ≠ the document's current revision.**
5. **JQC sign-off (manager only):**
   - A manager/supervisor uploads the filled-out, signed JQC and confirms: *"I verified this employee is qualified to perform this task."*
   - The app sets SignedOffBy = the manager.
   - A technician can never sign off a JQC. A manager cannot sign off their own JQC.
6. **Upload file types:** PDF, DOCX, XLSX, JPG, PNG. Maximum file size 25 MB.
7. **Never delete records.**
   - Assignments: set Status = Removed (manual) or Superseded (revision change), and `IsCurrent` = No.
   - Documents: set Status = Obsolete.
   - Employees: set Active = No.
8. **PWI revision change — mandatory re-sign-off for everyone assigned:**
   - Only a manager can upload a new PWI revision (`scrDocumentEdit` → **Upload New Revision**). New Revision and RevisionNotes are required.
   - Before saving, show a confirmation: *"This will require X employees to sign off on Rev {new}."* X = count of current rows for this DocumentID (active employees, Status not Removed).
   - On confirm:
     1. Replace the file and update Revision, RevisionDate and RevisionNotes on the `JP_Documents` item.
     2. For **every** current assignment on this DocumentID with Status in Assigned, In Training or Signed Off (active employees only):
        - Patch the old row: Status = **Superseded** if it was Signed Off, otherwise keep its status; set `IsCurrent` = No.
        - Create a new row: same Employee and Trainer, `RevisionAssigned` = new revision, `AssignmentReason` = Revision Change, `PreviousAssignmentID` = old row ID, Status = Assigned, `IsCurrent` = Yes, DueDate = Today() + `ResignDueDays`.
     3. Show a result summary: number re-assigned and any failures, with a retry button for failures.
   - Old sign-off records and files stay in `JP_SignoffRecords`; they show on `scrEmployeeDetail` under "Previous revisions".
   - Employees see re-sign items in **My Pending** with a "New Revision – Please Re-Sign" badge and the RevisionNotes.
   - Implement with `ForAll` + `Patch` in the app (no notifications). Comment the delegation/row-limit assumption; if more than 500 rows are expected, document the limit in Admin-Guide.md.
9. **JQC revision change — everyone assigned goes back to Needs Training** (product owner decision D-01 in `SPEC.md` §8):
   - Upload works the same as rule 8 (`scrDocumentEdit` → **Upload New Revision**; New Revision and RevisionNotes required).
   - Before saving, show: *"This will put X employees back to Needs Training on Rev {new}. Their current qualification will no longer count."* X is counted the same way as in rule 8.
   - On confirm, apply rule 8 steps 1–3 exactly (same old-row/new-row patching, same DueDate default, same result summary and retry).
   - The new rows have Status = Assigned, which displays as **Needs Training** with a "New Revision" badge and the RevisionNotes.
   - Earlier JQC sign-offs no longer count as qualified (rule 10). Old rows and files stay in history.
   - **The manager is responsible for putting them into training:** only a manager (never on their own row) can tap **Put Into Training**, which sets Status = In Training and lets them set or confirm the Trainer. A JQC can be signed off (rule 5) only from In Training.
   - This applies to every JQC row in Status = Assigned, whether from a new assignment or a revision.
10. **Qualified = current revision only.** For PWIs **and JQCs**, an employee counts as signed off only when their current row is Signed Off on the document's current revision. This drives the matrix, cross-training counts and pending lists.
11. **Writes:**
    - Every write uses `Patch`, wrapped in `IfError`.
    - Show a `Notify` message on both success and failure.
    - Disable the button while saving so it can't be submitted twice.

---

## 8. Status Logic (named formula `fxAssignmentDisplayStatus`)
| Condition | Display status | Color |
|---|---|---|
| Current row, Signed Off, rev = current | Signed Off | Green |
| PWI, current row, Assigned/In Training, AssignmentReason = Revision Change | Re-Sign Required | Amber |
| PWI, current row, Assigned/In Training | Pending | Amber |
| JQC, current row, Status = Assigned | Needs Training ("New Revision" badge if AssignmentReason = Revision Change) | Amber |
| JQC, current row, Status = In Training | In Training (technicians see "In Training – Waiting on Supervisor") | Amber |
| Any pending status and DueDate < Today() | Overdue | Red |
| No current row | Not Assigned | Grey |

Precedence when more than one row applies: Signed Off → Overdue → Re-Sign Required → Needs Training → In Training → Pending. Full rules: `SPEC.md` BR-41.

---

## 9. SharePoint Permissions (document in Admin-Guide.md)
| Group | Lists/Libraries |
|---|---|
| JQCPWI Managers | Contribute on all JP_ lists/libraries |
| JQCPWI Technicians | Read on JP_Employees, JP_Documents, JP_Settings. Contribute on JP_Assignments and JP_SignoffRecords |
| JQCPWI Viewers | Read on all |

Group names are placeholders. The user maps them to real groups at deployment.

---

## 10. Environment Variables
| Name | Type | Purpose |
|---|---|---|
| `jp_SiteUrl` | Data source (SharePoint site) | Target site |
| `jp_ListEmployees` | Data source (list) | JP_Employees |
| `jp_LibDocuments` | Data source (list) | JP_Documents |
| `jp_ListAssignments` | Data source (list) | JP_Assignments |
| `jp_LibSignoffs` | Data source (list) | JP_SignoffRecords |
| `jp_ListSettings` | Data source (list) | JP_Settings |

---

## 11. File Upload (standard connectors)
Canvas apps can't write directly to a document library. Use one instant flow:
- **Flow:** `JQCPWI - Upload File`
  - Trigger: Power Apps (V2) with inputs:
    - `File` (file)
    - `TargetLibrary` (text: Documents or Signoffs)
    - `ExistingItemID` (number; `0` = new file, otherwise the item whose content is replaced for a new revision)
    - `MetadataJson` (text)
  - Actions:
    1. If `ExistingItemID` is empty: SharePoint **Create file**. Otherwise: **Update file** content on the existing item (keeps the same ID; versioning keeps the old revision).
    2. **Update file properties** from MetadataJson.
    3. **Respond to Power Apps** with the item ID and file URL.
  - All site and library values come from environment variables. `Create file` needs a folder path, so it uses the fixed library folders `/JP_Documents` and `/JP_SignoffRecords` (`SPEC.md` A-31).
  - Generated by `flows/build_flow.py` into the solution. `flows/JQCPWI-UploadFile.md` documents every step.
- **In the app:** use an Attachments control (inside a form) to pick the file, then pass `First(att.Attachments)` to the flow.
- After the flow returns, Patch the assignment with SignoffFileID and status, or run the revision re-assign logic (Section 7 rule 8).

---

## 12. Screens
Navigation:
- **Phone:** bottom nav bar.
- **Tablet and desktop:** left nav rail.

Show only the items the user's role allows.

| Screen | Purpose | Roles |
|---|---|---|
| `scrHome` | Tiles: My Pending (incl. Re-Sign Required count), My Signed Off, Team Pending (managers, incl. JQCs Needing Training count), Coverage Gaps | All |
| `scrMyTraining` | Current user's current assignments in three tabs: Pending, Signed Off, All. Re-sign items show a "New Revision" badge. Tapping one opens `scrAssignmentDetail` | Manager, Technician |
| `scrAssignmentDetail` | Document link (view/download), revision, RevisionNotes (for re-signs) and trainer. PWI: upload training log, then Sign Off. JQC: technicians see "Needs Training" or "In Training – Waiting on Supervisor"; managers tap **Put Into Training**, then upload the signed JQC and confirm | Manager, Technician |
| `scrJQCLibrary` | JQCs with search and filters (Area, Status). Shows trainers, current rev, template link, "X of Y qualified on current rev" and Needs Training count. Managers can add or revise | All (edit: Manager) |
| `scrPWILibrary` | Same as JQC Library, for PWIs. Also shows "X of Y signed off on current rev" per PWI | All (edit: Manager) |
| `scrDocumentEdit` | Add a document, edit metadata, designate trainers, **Upload New Revision** (Section 7 rule 8) | Manager |
| `scrPWIStatus` | For one PWI: every assigned employee, the revision they're on and their status (Signed Off / Re-Sign Required / Overdue). Button to assign more employees | Manager, Viewer |
| `scrEmployees` | List, add and edit employees; set role, supervisor and active status | Manager (others: read-only list) |
| `scrEmployeeDetail` | One employee's current assignments by status, plus "Previous revisions" history with links to sign-off files | All (technicians: own only) |
| `scrAssign` | Multi-select employees and documents, pick a trainer and due date, then preview and create | Manager |
| `scrMatrix` | Training matrix (Section 13) | All |
| `scrCrossTraining` | Cross-training view (Section 13) | All |
| `scrSignoffReview` | Recently signed off, JQCs needing training (with **Put Into Training** for managers), JQCs in training, PWI re-signs required and overdue items. Filter by employee, document and date | Manager, Viewer |

---

## 13. Matrix & Cross-Training Visualization
Use standard controls only (galleries, shapes, labels and the built-in column chart).

**Training matrix (`scrMatrix`)**
- Rows are employees and columns are JQCs/PWIs. Cells use `fxAssignmentDisplayStatus` (Section 8).
- Filters: Area, DocType, Department, Shift, Supervisor and "Re-Sign Required only".
- Every cell shows a text label as well as the color, for accessibility.
- **Desktop/tablet:** grid layout (outer gallery of employees, inner horizontal gallery of documents) with a frozen employee name column.
- **Phone:** pick an employee to see their documents with status chips, or pick a document to see its employees.

**Cross-training (`scrCrossTraining`)** — counts use current-revision sign-offs only (Section 7 rule 10).
1. **Coverage by task:** a bar per JQC/PWI showing the number qualified versus `MinQualifiedPerTask`. Tasks below target are red and listed first. Also show how many are pending after a revision (PWI re-signs and JQC Needs Training).
2. **Single points of failure:** tasks with exactly one qualified person, showing who that person is.
3. **Coverage by shift:** number qualified per task per shift, to show shifts without coverage.
4. **Employee breadth:** number of qualifications per employee, so managers can spot who to cross-train next.
5. **Tap-through:** tapping a gap opens `scrAssign` with that document pre-selected.

---

## 14. UI Standards
- Touch targets at least 44 px tall. Body text at least 14 pt.
- Status always shows as text plus color.
- Technician-friendly labels: "Sign Off", "Upload Training Log", "New Revision – Please Re-Sign", "Needs Training", "Put Into Training", "In Training – Waiting on Supervisor". No jargon.
- Theme colors live in named formulas. Don't hard-code colors in individual controls.
- Every gallery has an empty-state message, e.g. "Nothing pending — you're all caught up."

---

## 15. Power Fx Conventions
| Prefix | Use |
|---|---|
| `scr` | Screens |
| `con` | Containers |
| `gal` | Galleries |
| `btn` | Buttons |
| `lbl` | Labels |
| `txt` | Text inputs |
| `drp` | Dropdowns |
| `cmb` | Combo boxes |
| `col` | Collections |
| `loc` | Context variables |
| `gbl` | Global variables |

- Named formulas: `fxMe`, `fxRole`, `fxIsManager`, `fxIsTechnician`, `fxAssignmentDisplayStatus`, plus theme colors.
- **Delegation:** filter on indexed Text, Number, Choice and Yes/No columns (EmployeeEmail, DocumentID, Status, DocType, IsCurrent). Comment wherever a function isn't delegable, and note row limits for the matrix and revision re-assign.

---

## 16. Repository Layout
```
/provisioning/Create-Lists.ps1
/app/App.fx.md
/app/build_app.py      (generates .fx.yaml sources and packs the .msapp)
/app/screens/*.pa.yaml (fallback only)
/flows/JQCPWI-UploadFile.md
/solution/env-vars.md
/solution/build.py
/solution/JQCPWIManagement/   (pac solution project: src/Other, environmentvariabledefinitions, CanvasApps, Workflows)
/solution/dist/*.zip   (built solution, importable)
/tools/setup-pac-linux.sh
/seed/*.csv            (fictional only; include one PWI and one JQC with a revision-change scenario)
/seed/expected-results.md
/provisioning/Import-SeedData.ps1
SPEC.md
/docs/README.md
/docs/Admin-Guide.md
/docs/Technician-Quick-Guide.md
.gitignore
```

---

## 17. Build Order
1. Provisioning script and fictional seed CSVs
2. Environment variable table
3. `App.fx.md`: named formulas, role logic, status logic, theme, navigation
4. Upload flow spec (new file + new revision)
5. Screens, in this order: Home → Employees → JQC/PWI Libraries → Document Edit (incl. Upload New Revision) → Assign → PWI Status → My Training → Assignment Detail → Sign-off Review → Matrix → Cross-Training
6. Docs

After each step, rebuild the solution (`python3 solution/build.py`) and then list:
- the files created
- the assumptions made
- any `TODO:` placeholders

---

## 18. Out of Scope
- Teams, email or Hour by Hour outputs and notifications
- Premium connectors, Dataverse and PCF/code components
- Employee self-sign-off on JQCs (JQC revisions do reset everyone to Needs Training per Section 7 rule 9, but only a manager moves them forward)
- Migrating existing Excel matrix and folder data (can be done later using the seed CSV format)

---

## 19. Open Items (leave as `TODO:` until confirmed)
- [ ] Default re-sign due period (14 days)
- [ ] Cross-training target (2 qualified per task)
- [ ] Whether in-app sign-off (logged-in user + timestamp) meets quality record requirements
- [ ] Mapping of placeholder SharePoint groups to real groups at deployment

---

## 20. Definition of Done
- [ ] No real names, emails, URLs, IDs or document content in the repo
- [ ] All site references go through environment variables
- [ ] Only standard connectors are used
- [ ] Every screen works at phone, tablet and desktop widths
- [ ] The role matrix (Section 5) and business rules (Section 7) are enforced
- [ ] PWI self sign-off and JQC manager-only sign-off both work end to end, with files saved to JP_SignoffRecords
- [ ] Uploading a new PWI revision creates a re-sign row for **every** currently assigned active employee, supersedes old sign-offs and keeps history
- [ ] Uploading a new JQC revision puts **every** currently assigned active employee back to Needs Training on the new revision, removes their old qualification from the counts and keeps history; only a manager can put them into training and sign them off
- [ ] Employees assigned after a revision get the current revision
- [ ] Nobody can sign off an outdated revision
- [ ] Matrix and cross-training views show correct counts against the seed data (current revision only)
- [ ] The solution imports into a clean environment and only asks for environment variable values and connections
- [ ] `/solution/dist/` holds the current importable solution zip, built by `solution/build.py`
