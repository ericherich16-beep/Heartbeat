# SPEC.md — JQC/PWI Management

> Functional specification for a Power Apps canvas app delivered as an importable solution.
> **Sources:** `CLAUDE.md` (build brief) and `intake.md` (background). Where they conflict, `CLAUDE.md` wins. Section references such as "CLAUDE §7.8" point to `CLAUDE.md`.
> **No confidential data.** Every name, email, number and file in this spec is fictional (for example `Tech A`, `manager1@contoso.com`, `PWI-DEMO-001`).
> **This document contains no app code.**

---

## 0. Glossary

| Term | Meaning |
|---|---|
| **JQC** | Job Qualification Checklist. A blank template the manager fills in and signs to confirm an employee is qualified. |
| **PWI** | Process Work Instruction. The employee trains on it and signs off themselves. |
| **Document** | One JQC or PWI. It is **one item** in `JP_Documents` that keeps the same ID across revisions. |
| **Current revision** | The `Revision` value on the `JP_Documents` item. Earlier files are kept in library version history. |
| **Assignment** | One row in `JP_Assignments`: one employee, one document, one revision. |
| **Current row** | The assignment row with `IsCurrent = Yes`. Each employee has at most one current row per document. |
| **Pending** | An assignment whose `Status` is `Assigned` or `In Training`. |
| **Re-sign row** | A row created automatically by a PWI revision (`AssignmentReason = Revision Change`). |
| **Qualified** | See BR-40. |
| **Sign-off file** | Evidence uploaded to `JP_SignoffRecords`: a PWI training log or a signed JQC. |
| **Trainer** | An employee a manager designates on a document. Trainer is not an app role. |
| **Task** | One `Active` document, used as the unit in the cross-training view. |

---

## 1. User roles and permissions

### 1.1 Roles and role resolution

| Role | Who |
|---|---|
| **Manager/Supervisor** ("Manager") | Production and quality managers and supervisors |
| **Technician** | Production and quality technicians |
| **Viewer** | Anyone who needs read-only access |

- The role is stored in `JP_Employees.AppRole` (CLAUDE §5).
- The app finds the user's role by matching `User().Email` to `JP_Employees.Email`. The match ignores case.
- If there is **no match**, or the matching employee has `Active = No`, the user gets **Viewer** access.
- A user who can't read the SharePoint site gets data-source errors. The app shows a "no access" message instead of empty screens (A-17).
- Trainers keep their own role. Their names show on the document and on the assignment.

### 1.2 Capability matrix

✅ = allowed · ❌ = not allowed · **Own** = only rows where the user is the assigned employee

| # | Capability | Manager | Technician | Viewer |
|---|---|:-:|:-:|:-:|
| P01 | View the matrix, cross-training view and JQC/PWI libraries | ✅ | ✅ | ✅ |
| P02 | View and download JQC templates and PWIs (current revision) | ✅ | ✅ | ✅ |
| P03 | View and download sign-off files (training logs, signed JQCs) | ✅ all | Own | ✅ all |
| P04 | See own pending assignments, including re-signs | ✅ | ✅ | ❌ |
| P05 | Upload a PWI training log | ✅ (own, or on behalf of an employee) | Own | ❌ |
| P06 | Sign off a PWI | ✅ (own, or on behalf of an employee) | Own | ❌ |
| P07 | Sign off a JQC (upload signed JQC and confirm qualification) | ✅ **except own** | ❌ | ❌ |
| P08 | Add or edit employees and set their role, supervisor and active status | ✅ | ❌ | ❌ |
| P09 | Add documents, edit document metadata and upload new revisions | ✅ | ❌ | ❌ |
| P10 | Designate trainers on a document | ✅ | ❌ | ❌ |
| P11 | Mark a document Obsolete | ✅ | ❌ | ❌ |
| P12 | Create assignments (bulk) | ✅ | ❌ | ❌ |
| P13 | Mark an assignment Removed | ✅ | ❌ | ❌ |
| P14 | Delete any record or file | ❌ | ❌ | ❌ |

### 1.3 Screen access matrix

👁 = read-only

| Screen | Manager | Technician | Viewer |
|---|:-:|:-:|:-:|
| `scrHome` | ✅ | ✅ | ✅ |
| `scrMyTraining` | ✅ | ✅ | ❌ |
| `scrAssignmentDetail` | ✅ (any assignment) | ✅ own | ❌ |
| `scrJQCLibrary` | ✅ (edit) | 👁 | 👁 |
| `scrPWILibrary` | ✅ (edit) | 👁 | 👁 |
| `scrDocumentEdit` | ✅ | ❌ | ❌ |
| `scrPWIStatus` | ✅ | ❌ | 👁 |
| `scrEmployees` | ✅ (edit) | 👁 list | 👁 list |
| `scrEmployeeDetail` | ✅ (any employee) | 👁 own only | 👁 (any employee) |
| `scrAssign` | ✅ | ❌ | ❌ |
| `scrMatrix` | ✅ | 👁 | 👁 |
| `scrCrossTraining` | ✅ | 👁 | 👁 |
| `scrSignoffReview` | ✅ | ❌ | 👁 |

Navigation shows only the screens the role can reach. If a user reaches a screen they can't access, they are sent to `scrHome` and see a "You don't have access to that page" message.

### 1.4 SharePoint permissions (back-up to app logic)

Source: CLAUDE §9. Group names are placeholders, to be mapped at deployment.

| Group | Permissions |
|---|---|
| JQCPWI Managers | Contribute on all `JP_` lists and libraries |
| JQCPWI Technicians | Read on `JP_Employees`, `JP_Documents` and `JP_Settings`. Contribute on `JP_Assignments` and `JP_SignoffRecords` |
| JQCPWI Viewers | Read on all |

> ⚠️ Technicians have Contribute on `JP_Assignments` and `JP_SignoffRecords`. Most row-level rules, such as "own rows only" and "can't sign off JQCs", are therefore enforced **in the app only**. A technician who opens the list in SharePoint could edit rows directly. See OQ-03.

---

## 2. Screen list

Layout rules for every screen:
- Responsive containers only. No fixed X/Y layout.
- **Phone:** bottom nav bar. **Tablet and desktop:** left nav rail.
- Touch targets at least 44 px tall. Body text at least 14 pt.
- Status is shown as text **and** color.
- Every gallery has an empty-state message.

| # | Screen | Roles | Purpose |
|---|---|---|---|
| 1 | `scrHome` | All | Landing page with tiles. My Pending shows the Re-Sign Required count. My Signed Off. Team Pending (managers only). Coverage Gaps. Each tile opens the matching screen with a filter applied. |
| 2 | `scrMyTraining` | Manager, Technician | The user's own current assignments in three tabs: **Pending**, **Signed Off** and **All**. Re-sign rows show a "New Revision – Please Re-Sign" badge and the revision notes. Opens `scrAssignmentDetail`. |
| 3 | `scrAssignmentDetail` | Manager, Technician (own) | Shows the document link (view and download), the revision assigned, the revision notes (for re-signs) and the trainer. **PWI:** upload the training log, then Sign Off. **JQC:** technicians see "Waiting on Supervisor"; managers upload the signed JQC and confirm qualification. |
| 4 | `scrJQCLibrary` | All (edit: Manager) | List of JQCs with search and filters (Area, Status). Each shows trainers, current revision, template link and the number qualified. Managers can add or revise from here. |
| 5 | `scrPWILibrary` | All (edit: Manager) | The same as the JQC library, plus "X of Y signed off on current rev" for each PWI. |
| 6 | `scrDocumentEdit` | Manager | Add a document, edit its metadata, designate trainers, **Upload New Revision** (BR-30 to BR-36) and mark it Obsolete. |
| 7 | `scrPWIStatus` | Manager, Viewer | One PWI: every assigned employee with the revision they're on and their display status. Managers get an Assign More Employees button and a Remove action. |
| 8 | `scrEmployees` | Manager (edit); others read-only | Employee list with search and filters. Managers can add and edit employees and set role, supervisor and active status. |
| 9 | `scrEmployeeDetail` | All (Technicians: own only) | One employee's current assignments grouped by status, plus "Previous revisions" history with links to sign-off files. |
| 10 | `scrAssign` | Manager | Multi-select employees and Active documents, pick a trainer and due date, then preview and create the assignments. |
| 11 | `scrMatrix` | All | Training matrix of employees × documents, with cell status from `fxAssignmentDisplayStatus`. |
| 12 | `scrCrossTraining` | All | Coverage by task, single points of failure, coverage by shift, employee breadth, and tap-through to `scrAssign`. |
| 13 | `scrSignoffReview` | Manager, Viewer | Recently signed-off items, JQCs waiting on a supervisor, re-signs required and overdue items. Filters by employee, document and date. |

---

## 3. Data model

### 3.1 Relationships

```
JP_Employees (1) ──< JP_Assignments >── (1) JP_Documents
   ▲    │                │                  (one item per document; file replaced
   │    │ Supervisor     │                   in place on revision; old files in
   └────┘ (self lookup)  │                   version history)
                         │
                         └──< JP_SignoffRecords   (AssignmentID → JP_Assignments.ID)

JP_Documents.Trainers  : Person (multi) — designated trainers
JP_Assignments.Trainer : Person — chosen from that document's Trainers
JP_Settings            : single row, global settings
```

| From | To | Cardinality | Implemented as |
|---|---|---|---|
| `JP_Assignments.Employee` | `JP_Employees` | many : 1 | Lookup, with `EmployeeEmail` text copy for delegation |
| `JP_Assignments.DocumentID` | `JP_Documents.ID` | many : 1 | Number |
| `JP_Assignments.PreviousAssignmentID` | `JP_Assignments.ID` | 1 : 1 (chain) | Number |
| `JP_Assignments.SignoffFileID` | `JP_SignoffRecords.ID` | 1 : 0..1 | Number |
| `JP_SignoffRecords.AssignmentID` | `JP_Assignments.ID` | many : 1 | Number |
| `JP_Employees.Supervisor` | `JP_Employees` | many : 1 | Lookup |

Rules that apply to all lists:
- Use internal column names without spaces.
- Index every column used in a filter (CLAUDE §6).
- SharePoint system columns (`ID`, `Created`, `Created By`, `Modified`, `Modified By`) exist on every list.

### 3.2 `JP_Employees` (list)

| Column | Type | Req | Notes |
|---|---|:-:|---|
| `Title` | Single line of text | ✅ | Display name, for example `Tech A`. |
| `Email` | Single line of text | ✅ | Unique (enforce unique values) and indexed. Used for role lookup. Stored lowercase. |
| `EmployeeUser` | Person | | Optional link to the M365 user. |
| `JobTitle` | Choice | ✅ | Production Technician, Quality Technician, Supervisor, Manager, Other |
| `Department` | Choice | | Production, Quality, Other. Indexed. |
| `Shift` | Choice | | 1st, 2nd, 3rd, Days. Indexed. |
| `Supervisor` | Lookup → `JP_Employees.Title` | | Used for "My Team" filtering. Indexed. |
| `AppRole` | Choice | ✅ | Manager/Supervisor, Technician, Viewer |
| `Active` | Yes/No | ✅ | Default Yes. Never delete an employee; set `Active = No` instead. Indexed. |

### 3.3 `JP_Documents` (document library: JQC templates and PWIs)

| Column | Type | Req | Notes |
|---|---|:-:|---|
| `Name` (file) | File | ✅ | JQC: the blank template. PWI: the work instruction. |
| `DocType` | Choice | ✅ | JQC, PWI. Indexed. |
| `DocNumber` | Single line of text | ✅ | For example `JQC-DEMO-100` or `PWI-DEMO-001`. Unique (A-05). Indexed. |
| `DocTitle` | Single line of text | ✅ | |
| `Revision` | Single line of text | ✅ | Always the **current** revision. |
| `RevisionDate` | Date only | ✅ | Date the current revision was released in the app. |
| `RevisionNotes` | Multiple lines of text | | What changed. Shown to employees when they re-sign. Required when uploading a new revision (BR-30). |
| `Area` | Choice | | Production, Quality, Metrology, Other. The choice list can be edited. Indexed. |
| `Status` | Choice | ✅ | Active, Obsolete. Indexed. |
| `Trainers` | Person or Group (multiple, people only) | | Designated trainers. At least one is required before the document can be assigned. |
| `Description` | Multiple lines of text | | |

Library settings:
- Versioning on (major versions).
- A new revision **replaces the file in place**, so the item ID (`DocumentID`) never changes and earlier revision files stay in version history.

### 3.4 `JP_Assignments` (list: one row per employee per document revision)

| Column | Type | Req | Notes |
|---|---|:-:|---|
| `Title` | Single line of text | ✅ | Generated automatically as `{DocNumber} Rev {RevisionAssigned} – {Employee Title}`. |
| `Employee` | Lookup → `JP_Employees.Title` | ✅ | |
| `EmployeeEmail` | Single line of text | ✅ | Copy of the employee's email, for delegable filtering. Indexed. |
| `DocumentID` | Number | ✅ | `JP_Documents` item ID. Indexed. |
| `DocType` | Choice | ✅ | JQC, PWI. Copied from the document. Indexed. |
| `DocNumber` | Single line of text | ✅ | Copied from the document. |
| `DocTitle` | Single line of text | ✅ | Copied from the document. |
| `RevisionAssigned` | Single line of text | ✅ | The revision this row must be signed against. |
| `AssignmentReason` | Choice | ✅ | New Assignment, Revision Change |
| `PreviousAssignmentID` | Number | | Links a re-sign row to the row it replaced. |
| `IsCurrent` | Yes/No | ✅ | Yes = the employee's live row for this document. Indexed. |
| `AssignedBy` | Person | ✅ | |
| `AssignedDate` | Date only | ✅ | |
| `DueDate` | Date only | | Optional. Re-sign rows default to Today() + `ResignDueDays`. |
| `Trainer` | Person | | Chosen from the document's `Trainers`. |
| `Status` | Choice | ✅ | Assigned, In Training, Signed Off, Superseded, Removed. Indexed. |
| `SignedOffBy` | Person | | PWI: the employee or a manager. JQC: the manager or supervisor. |
| `SignedOffDate` | Date and time | | Set to `Now()` at sign-off. |
| `SignoffFileID` | Number | | `JP_SignoffRecords` item ID. |
| `Comments` | Multiple lines of text | | Holds the removal reason (A-12) and optional sign-off notes. |

### 3.5 `JP_SignoffRecords` (document library: completed evidence)

| Column | Type | Req | Notes |
|---|---|:-:|---|
| `Name` (file) | File | ✅ | JQC: the filled-out, signed template. PWI: the training log. |
| `AssignmentID` | Number | ✅ | Links back to `JP_Assignments`. Indexed. |
| `DocType` | Choice | ✅ | JQC, PWI |
| `Revision` | Single line of text | ✅ | The revision signed against. |
| `EmployeeEmail` | Single line of text | ✅ | Indexed. |
| `UploadedBy` | Person | ✅ | |

File name format: `{DocNumber}_Rev{Rev}_{EmployeeID}_{yyyyMMdd}.{ext}`. `EmployeeID` is the `JP_Employees` list ID, never the employee's name.

### 3.6 `JP_Settings` (list: single row)

| Column | Type | Default | Notes |
|---|---|---|---|
| `Title` | Single line of text | `Settings` | Required by SharePoint. |
| `MinQualifiedPerTask` | Number (integer ≥ 1) | 2 | Cross-training target. `TODO:` confirm. |
| `ResignDueDays` | Number (integer ≥ 1) | 14 | Days allowed to re-sign after a PWI revision. `TODO:` confirm. |

### 3.7 Delivery components (from CLAUDE §4, §10, §11 and §16)

**Environment variables**

| Variable | Points to |
|---|---|
| `jp_SiteUrl` | SharePoint site |
| `jp_ListEmployees` | `JP_Employees` |
| `jp_LibDocuments` | `JP_Documents` |
| `jp_ListAssignments` | `JP_Assignments` |
| `jp_LibSignoffs` | `JP_SignoffRecords` |
| `jp_ListSettings` | `JP_Settings` |

No URLs, tenant IDs, site names or GUIDs are hard-coded anywhere.

**Flow: `JQCPWI - Upload File`**

- **Trigger:** Power Apps (V2) with these inputs:
  - `File` (file)
  - `TargetLibrary` (text: `Documents` or `Signoffs`)
  - `ExistingItemID` (number, optional)
  - `MetadataJson` (text)
- **Steps:**
  1. If `ExistingItemID` is empty, create the file. Otherwise, update the file content of that item.
  2. Update the file properties from `MetadataJson`.
  3. Return the item ID and file URL to the app.
- All other writes are `Patch` calls from the app.

**Repository layout**

| Path | Contents |
|---|---|
| `/provisioning/Create-Lists.ps1` | PnP PowerShell script that creates the lists |
| `/app/App.fx.md` | App-level formulas |
| `/app/screens/*.pa.yaml` | One file per screen |
| `/flows/JQCPWI-UploadFile.md` | Upload flow spec |
| `/solution/env-vars.md` | Environment variable setup |
| `/seed/*.csv` | Fictional seed data only |
| `/docs/*` | Documentation |
| `.gitignore` | Must exclude `*.env`, `*.secrets*`, `/exports/` and any `*.zip` not built by this project |

---

## 4. Business rules (numbered, testable)

### Access
- **BR-01** The user's role is the `AppRole` on the active `JP_Employees` row whose `Email` matches `User().Email`, ignoring case. If there is no match, or the employee is inactive, the role is Viewer.
- **BR-02** Controls a role isn't allowed to use (per §1.2) are hidden or disabled, and screens it can't reach (per §1.3) don't appear in navigation.
- **BR-03** A Technician can open `scrAssignmentDetail` and `scrEmployeeDetail` only for their own records (`EmployeeEmail` = their email). Any other record shows "You can only view your own items."
- **BR-04** A Technician can open sign-off files only for their own assignments. Managers and Viewers can open all sign-off files.
- **BR-05** No screen offers a delete action for any list item or file.

### Validation and writes
- **BR-06** A form can't be submitted while any field marked required in §3 is empty. Missing fields are listed in plain language, for example "Please enter the Document Number."
- **BR-07** Every write uses `Patch` wrapped in `IfError`, shows a `Notify` message on success and on failure, and disables its button until the write finishes.
- **BR-08** Uploads accept only `.pdf`, `.docx`, `.xlsx`, `.jpg`/`.jpeg` and `.png` files (extension check ignores case), up to 25 MB each. Anything else is rejected before the flow is called, with a message that names the problem.
- **BR-09** Each upload sends exactly one file, from an Attachments control, to `JQCPWI - Upload File`.

### Employees
- **BR-10** Only Managers can add or edit employees and set their role, supervisor or active status.
- **BR-11** `Email` must be unique across all employees, active or inactive. A duplicate is rejected with a message.
- **BR-12** Employees are never deleted. Deactivating sets `Active = No`.
- **BR-13** Inactive employees are left out of the matrix, cross-training counts, the "X employees" re-sign count, re-sign row creation, and the employee and trainer pickers on `scrAssign`.
- **BR-14** Only employees with `AppRole` Technician or Manager/Supervisor can be chosen as assignees (A-08).

### Documents and trainers
- **BR-15** Only Managers can add documents, edit document metadata, designate trainers, upload revisions or mark documents Obsolete.
- **BR-16** A new document is created through the upload flow (no `ExistingItemID`) with `Status = Active`, the entered `Revision`, and `RevisionDate = Today()`.
- **BR-17** `DocNumber` must be unique across all documents (A-05).
- **BR-18** Editing metadata (title, area, description, trainers) doesn't change `Revision` and doesn't touch assignments.
- **BR-19** A document with no designated trainer can't be assigned. It can't be selected on `scrAssign`, and Assign actions are disabled with the reason shown.
- **BR-20** Documents are never deleted. Retiring one sets `Status = Obsolete`. Obsolete documents can't be assigned or revised, and they're left out of the matrix and cross-training views. Library screens show them only when the Status filter includes Obsolete.

### Assignments
- **BR-21** Only Managers can create assignments. They pick one or more employees and one or more `Active` documents, and the app creates one row per eligible pair.
- **BR-22** Each new row gets:
  - `RevisionAssigned` = the document's **current** `Revision`
  - `AssignmentReason = New Assignment`
  - `IsCurrent = Yes`
  - `Status = Assigned`
  - `AssignedBy` = current user
  - `AssignedDate = Today()`
  - copies of `EmployeeEmail`, `DocType`, `DocNumber` and `DocTitle`
- **BR-23** **No duplicates:** an employee can never have two rows with `IsCurrent = Yes` for the same `DocumentID`. Pairs that already have a current row are skipped and listed in the preview as "Already assigned".
- **BR-24** `DueDate` is optional on new assignments. `Trainer`, if set, must be one of the document's `Trainers`.
- **BR-25** Employees assigned after a revision always get the revision that is current at that time (follows from BR-22).
- **BR-26** A Manager can remove an assignment. The app sets `Status = Removed` and `IsCurrent = No`, and records the reason in `Comments`. A removed pair can then be assigned again.

### Sign-off
- **BR-27** A sign-off is allowed only on a row with `IsCurrent = Yes`, a pending `Status` (`Assigned` or `In Training`), on an `Active` document, **and** `RevisionAssigned` = the document's current `Revision`. Otherwise the sign-off control is disabled and shows "This revision is no longer current."
- **BR-28** **PWI:**
  - Only the assigned employee or a Manager can sign off.
  - **Sign Off** stays disabled until a training log has been uploaded for this row.
  - On sign-off the app sets `Status = Signed Off`, `SignedOffBy` = current user, `SignedOffDate = Now()` and `SignoffFileID`.
- **BR-29** **JQC:**
  - Only a Manager can sign off, and never on a row where they are the assigned employee.
  - The Manager uploads the signed JQC and ticks *"I verified this employee is qualified to perform this task."*
  - The confirm button stays disabled until both the upload and the tick are done.
  - On confirm the app sets `Status = Signed Off`, `SignedOffBy` = the Manager, `SignedOffDate = Now()` and `SignoffFileID`.
  - Technicians never see JQC sign-off controls.
- **BR-30** Each uploaded sign-off file creates a `JP_SignoffRecords` item with `AssignmentID`, `DocType`, `Revision` (= `RevisionAssigned`), `EmployeeEmail` and `UploadedBy`. It is named using the §3.5 format.

### PWI revision change
- **BR-31** Only a Manager can upload a new revision (`scrDocumentEdit` → **Upload New Revision**). A new file, a new `Revision` value (different from the current one, A-06) and `RevisionNotes` are all required.
- **BR-32** Before saving, the app shows *"This will require X employees to sign off on Rev {new}."* X = the number of rows for this `DocumentID` with `IsCurrent = Yes`, `Status` not `Removed`, and an active employee.
- **BR-33** On confirm, the app first replaces the file in place (upload flow with `ExistingItemID`) and updates `Revision`, `RevisionDate = Today()` and `RevisionNotes` on the document item. The item ID doesn't change.
- **BR-34** Next, for **every** row with this `DocumentID`, `IsCurrent = Yes`, `Status` in Assigned, In Training or Signed Off, and an active employee:
  - **Old row:** set `Status = Superseded` if it was `Signed Off`, otherwise keep its status. Set `IsCurrent = No`.
  - **New row:** same `Employee` and `Trainer`, with:
    - `RevisionAssigned` = the new revision
    - `AssignmentReason = Revision Change`
    - `PreviousAssignmentID` = the old row's ID
    - `Status = Assigned`
    - `IsCurrent = Yes`
    - `DueDate = Today() + ResignDueDays`
    - copies of the other columns, as in BR-22
- **BR-35** After processing, a summary shows the number re-assigned and the number of failures, with a **Retry** button. Retry processes only rows that still have `IsCurrent = Yes` on an old revision, so it never creates duplicates.
- **BR-36** Earlier sign-off records and files stay in `JP_SignoffRecords` and appear on `scrEmployeeDetail` under "Previous revisions".
- **BR-37** Re-sign rows show in **My Pending** with the badge "New Revision – Please Re-Sign" and the `RevisionNotes`.
- **BR-38** The revision process is built with `ForAll` + `Patch` in the app. It is designed for up to 500 affected rows per document; the limit is documented in Admin-Guide.md.

### JQC revision change
- **BR-39** Uploading a new JQC revision replaces the file and updates `Revision`, `RevisionDate` and `RevisionNotes`, as in BR-33. It **doesn't** create re-sign rows, and existing `Signed Off` JQC rows stay valid. A Manager can still re-assign an employee manually by removing their row (BR-26) and assigning again. How pending JQC rows are handled is covered by A-09 and OQ-01.

### Qualification and status
- **BR-40** **Qualified:**
  - **PWI:** the employee is active and their current row has `Status = Signed Off` **and** `RevisionAssigned` = the document's current `Revision`.
  - **JQC:** the employee is active and their current row has `Status = Signed Off`, on any revision (BR-39).
  - Only qualified rows count as Signed Off in the matrix, the cross-training counts and the library counts.
- **BR-41** The display status (`fxAssignmentDisplayStatus`) is the first match in this list:

  | # | Condition | Display status | Color |
  |---|---|---|---|
  | 1 | No current row | Not Assigned | Grey |
  | 2 | Qualified per BR-40 | Signed Off | Green |
  | 3 | Pending and `DueDate` set and `DueDate < Today()` | Overdue | Red |
  | 4 | Pending and `AssignmentReason = Revision Change` | Re-Sign Required | Amber |
  | 5 | JQC, `Status = In Training` | Waiting on Supervisor | Amber |
  | 6 | Pending | Pending | Amber |
  | 7 | PWI, current row `Signed Off` but on an older revision (integrity exception) | Re-Sign Required | Amber |

  The order of rows 3–6 is set out in A-10. Where an Overdue row is also a re-sign, it shows a secondary "Re-sign" badge.
- **BR-42** Colors come from theme named formulas and are never hard-coded on controls. Every status appears as a text label alongside its color.

### Cross-training
- **BR-43** **Coverage per task** = the number of active employees qualified (BR-40) on that `Active` document. The target is `JP_Settings.MinQualifiedPerTask`, or 2 if that is blank.
- **BR-44** A task is **below target** when coverage < target. Below-target tasks show in red and are listed first.
- **BR-45** A task is a **single point of failure** when coverage is exactly 1. The view names that person.
- **BR-46** **Coverage by shift** shows coverage per task for each `Shift` value that has at least one active employee. A cell with 0 marks a shift with no coverage.
- **BR-47** **Employee breadth** = the number of tasks each active employee is qualified on.
- **BR-48** The "pending re-sign" count for a task = current rows with display status Re-Sign Required, or Overdue on a re-sign row.

### Records
- **BR-49** Nothing is deleted:
  - Assignments become `Removed` (manual) or `Superseded` (revision), with `IsCurrent = No`.
  - Documents become `Obsolete`.
  - Employees become `Active = No`.
  - Sign-off files are never removed.

---

## 5. Acceptance criteria per screen

Checks use the fictional seed data, which must include at least these scenarios:
- one PWI with a revision change, such as `PWI-DEMO-001` Rev A → Rev B
- one JQC with no trainer
- one task with exactly one qualified person
- one shift with no coverage
- one overdue item
- one inactive employee

### 5.1 `scrHome`
- **AC-HOME-1** A Technician sees My Pending, with a separate Re-Sign Required count, and My Signed Off tiles. The counts match their current rows.
- **AC-HOME-2** A Manager also sees Team Pending, counted over employees whose `Supervisor` is the Manager.
- **AC-HOME-3** Every role sees a Coverage Gaps tile showing the number of tasks below target, which opens `scrCrossTraining`.
- **AC-HOME-4** A Viewer sees no My Pending, My Signed Off or Team Pending tiles.
- **AC-HOME-5** A user with no `JP_Employees` match lands here with Viewer navigation only.
- **AC-HOME-6** Phones show a bottom nav bar. Tablets and desktops show a left nav rail. Both list only the screens the role can reach.

### 5.2 `scrMyTraining`
- **AC-MYT-1** The Pending, Signed Off and All tabs show only the user's own rows with `IsCurrent = Yes`.
- **AC-MYT-2** Re-sign rows show the "New Revision – Please Re-Sign" badge and the revision notes.
- **AC-MYT-3** Overdue rows show the red Overdue label and sort first in Pending.
- **AC-MYT-4** Tapping a row opens `scrAssignmentDetail` for that row.
- **AC-MYT-5** An empty Pending tab shows "Nothing pending — you're all caught up."

### 5.3 `scrAssignmentDetail`
- **AC-ASD-1** Shows document number and title, a view/download link, `RevisionAssigned`, the trainer, the due date, the display status, and the revision notes when the row is a re-sign.
- **AC-ASD-2** **PWI, own pending row:** **Upload Training Log** is enabled. **Sign Off** stays disabled until the upload succeeds. After Sign Off, the status shows Signed Off with "Signed off by {name} on {date/time}", and a `JP_SignoffRecords` item exists with the right `AssignmentID`, `Revision` and file name.
- **AC-ASD-3** **PWI, outdated revision** (`RevisionAssigned` ≠ current): Upload and Sign Off are disabled and the screen shows "This revision is no longer current."
- **AC-ASD-4** **JQC, viewed by a Technician:** no upload or sign-off controls appear. The status shows "Waiting on Supervisor" or Pending.
- **AC-ASD-5** **JQC, a Manager viewing another employee's row:** upload control, confirmation checkbox and confirm button are shown. Confirm stays disabled until both are done. After confirming, `SignedOffBy` is the Manager.
- **AC-ASD-6** **JQC, a Manager viewing their own row:** the sign-off controls are hidden.
- **AC-ASD-7** Choosing a `.exe` file, or a file over 25 MB, is rejected with a message and the flow isn't called.
- **AC-ASD-8** If the upload or the Patch fails, a Notify error appears and the row is unchanged. The button is disabled while saving.
- **AC-ASD-9** A Technician who opens another employee's row sees "You can only view your own items."

### 5.4 `scrJQCLibrary` and `scrPWILibrary`
- **AC-LIB-1** Each row shows document number, title, current revision, trainers, template or PWI link, and the number qualified (BR-40). The PWI library also shows "X of Y signed off on current rev".
- **AC-LIB-2** Search matches document number and title. Filters for Area and Status default to Active.
- **AC-LIB-3** Managers see **Add** and **Revise/Edit**, which open `scrDocumentEdit`. Technicians and Viewers don't.
- **AC-LIB-4** Documents with no trainer show a "No trainer — can't assign" label.
- **AC-LIB-5** For `PWI-DEMO-001` after its revision, "X of Y" counts only rows signed off on Rev B.

### 5.5 `scrDocumentEdit`
- **AC-DOC-1** **Add mode** requires a file, `DocType`, `DocNumber`, `DocTitle` and `Revision`. A duplicate `DocNumber` is rejected. On save the document appears in its library with `Status = Active`.
- **AC-DOC-2** **Edit mode** lets the Manager change the title, area, description and trainers without changing the revision or any assignment.
- **AC-DOC-3** **Trainers** allows several people, chosen from active employees.
- **AC-DOC-4** **Upload New Revision** requires a new file, a new revision different from the current one, and revision notes. A confirmation shows the BR-32 message with the correct X.
- **AC-DOC-5** **PWI revision, after confirm:**
  - the document item keeps its ID, with the new `Revision`, `RevisionDate` and `RevisionNotes`
  - the previous file is in version history
  - every affected employee has a new current row matching BR-34
  - their old rows have `IsCurrent = No`, and `Status = Superseded` where they had been signed off
  - inactive employees get no new rows
  - a summary shows "{n} re-assigned, {f} failed", with Retry when f > 0
- **AC-DOC-6** **JQC revision:** no new assignment rows are created, and previously signed-off employees still count as qualified.
- **AC-DOC-7** **Mark Obsolete** asks for confirmation and sets `Status = Obsolete`. The document disappears from the default library view, the matrix and the cross-training view.

### 5.6 `scrPWIStatus`
- **AC-PWS-1** Lists every employee with a current row for the selected PWI, showing `RevisionAssigned` and the display status (Signed Off, Re-Sign Required, Overdue, Pending).
- **AC-PWS-2** Shows summary counts by status. These match AC-LIB-1.
- **AC-PWS-3** Managers see **Assign More Employees**, which opens `scrAssign` with this PWI already selected, and a **Remove** action that asks for a reason (BR-26). Viewers see neither.

### 5.7 `scrEmployees`
- **AC-EMP-1** Lists active employees by default, with name, job title, department, shift, supervisor and role. A toggle includes inactive employees, which show an "Inactive" label.
- **AC-EMP-2** Search by name or email. Filters for department, shift, supervisor and role.
- **AC-EMP-3** Managers can add and edit employees. Required fields and unique `Email` are enforced. Setting `Active = No` asks for confirmation.
- **AC-EMP-4** Technicians and Viewers see a read-only list with no add or edit controls.

### 5.8 `scrEmployeeDetail`
- **AC-EDT-1** Shows the employee's profile and their current rows grouped by display status.
- **AC-EDT-2** **Previous revisions** lists Superseded rows and their sign-off files, for example `Tech A` signed off on `PWI-DEMO-001` Rev A, with links that follow BR-04.
- **AC-EDT-3** A Technician can open only their own detail.
- **AC-EDT-4** Managers see Assign (opens `scrAssign` with this employee already selected) and Remove on current rows.

### 5.9 `scrAssign`
- **AC-ASN-1** Multi-select employees (active Technicians and Managers only) and Active documents that have at least one trainer. Documents with no trainer can't be selected, and the reason is shown.
- **AC-ASN-2** Each document can have a trainer, chosen from its `Trainers`. Due date is optional.
- **AC-ASN-3** The preview shows "{x} will be created, {y} already assigned (skipped)", listing the skipped pairs.
- **AC-ASN-4** **Create** makes exactly x rows that match BR-22. Running the same selection again creates 0 rows.
- **AC-ASN-5** A pre-selection passed in from `scrPWIStatus`, `scrEmployeeDetail` or `scrCrossTraining` is applied when the screen opens.

### 5.10 `scrMatrix`
- **AC-MTX-1** **Desktop/tablet:** employees are rows and Active documents are columns, with a frozen employee name column. Each cell shows the BR-41 status as text and color.
- **AC-MTX-2** Filters: Area, DocType, Department, Shift, Supervisor, and "Re-Sign Required only".
- **AC-MTX-3** **Phone:** choose an employee to see their documents as status chips, or choose a document to see its employees.
- **AC-MTX-4** For `PWI-DEMO-001` after Rev B, an employee who signed only Rev A shows **Re-Sign Required** (or Overdue), never Signed Off.
- **AC-MTX-5** Inactive employees and Obsolete documents don't appear.
- **AC-MTX-6** Cell values match the seed data's expected results table (in `/seed/`).

### 5.11 `scrCrossTraining`
- **AC-XT-1** **Coverage by task:** one bar per Active task showing qualified count against target. Below-target tasks are red and listed first. Each task shows its pending re-sign count.
- **AC-XT-2** **Single points of failure:** lists tasks with exactly one qualified person and names that person.
- **AC-XT-3** **Coverage by shift:** a table of tasks × shifts with qualified counts. Cells with 0 are highlighted.
- **AC-XT-4** **Employee breadth:** the number of qualifications per active employee, sorted ascending.
- **AC-XT-5** Tapping a gap opens `scrAssign` with that document pre-selected, for Managers only. For other roles the tap does nothing.
- **AC-XT-6** Counts use current-revision sign-offs only and match the seed data's expected results.
- **AC-XT-7** Built only from standard controls (galleries, shapes, labels and the built-in column chart), and readable on a phone.

### 5.12 `scrSignoffReview`
- **AC-SOR-1** Four sections or tabs: Recently Signed Off, JQCs Waiting on Supervisor, Re-Sign Required, and Overdue.
- **AC-SOR-2** Filters for employee, document and date range.
- **AC-SOR-3** Each item links to its sign-off file where one exists. Managers can open `scrAssignmentDetail` from an item.
- **AC-SOR-4** Viewers can see everything but can't change anything.

### 5.13 Cross-cutting
- **AC-X-1** Every screen works at phone portrait, tablet portrait and landscape, and desktop widths, using responsive containers.
- **AC-X-2** Every gallery has an empty-state message.
- **AC-X-3** No URL, tenant ID, site name or GUID appears in the app, the flow or the scripts. Everything comes from the environment variables.
- **AC-X-4** The repo contains only fictional data, and `.gitignore` meets CLAUDE §2.
- **AC-X-5** The solution imports into a clean environment and asks only for environment variable values and connections.
- **AC-X-6** Only standard connectors are used: SharePoint, Office 365 Users, and Power Automate with the Power Apps (V2) trigger.

---

## 6. Assumptions

| # | Assumption |
|---|---|
| A-01 | `CLAUDE.md` is authoritative. Intake details it doesn't repeat (such as Viewer scope) are kept only where they don't conflict. |
| A-02 | The app is a canvas app, built from per-screen `.pa.yaml` files pasted into Power Apps Studio. No `.msapp` is built by hand. |
| A-03 | Business rules are enforced in the app with `Patch` and `IfError`. The only server-side logic is the upload flow, so the SharePoint permissions in §1.4 are the only back-stop (see OQ-03). |
| A-04 | Settings are edited directly in the `JP_Settings` SharePoint list by Managers, since CLAUDE.md doesn't include a settings screen. If the row is missing, the app uses 2 and 14. |
| A-05 | `DocNumber` is unique across documents. CLAUDE.md doesn't say so, but `DocumentID`-based logic depends on one item per document. |
| A-06 | A new revision's label only has to differ from the current `Revision`. There is no format check. |
| A-07 | Trainers are picked from active `JP_Employees` (Technician or Manager) and stored as people in the `Trainers` Person column. |
| A-08 | Viewers can't be assigned documents. Matrix rows are active employees with `AppRole` Technician or Manager/Supervisor. |
| A-09 | On a **JQC** revision, pending JQC rows on the old revision stay as they are. Because BR-27 blocks sign-off on an outdated revision, a Manager must remove the row and re-assign it before a sign-off. `scrSignoffReview` flags these rows as "Revision changed – re-assign". See OQ-01. |
| A-10 | Status precedence when several apply: Signed Off, then Overdue, then Re-Sign Required, then Waiting on Supervisor, then Pending. |
| A-11 | `In Training` is set from `scrAssignmentDetail`. For a PWI, the employee or a Manager taps "Start Training". For a JQC, the employee or a Manager taps "Training Complete – Ready for Supervisor". A JQC row in `In Training` displays as **Waiting on Supervisor**. See OQ-02. |
| A-12 | Removing an assignment happens on `scrPWIStatus` or `scrEmployeeDetail` (Managers only). The reason is stored in `Comments`. |
| A-13 | When an employee is deactivated, their rows stay unchanged and are simply left out of views and counts (BR-13). When a document is made Obsolete, its rows stay unchanged and it is left out of views. |
| A-14 | Employees with a blank `Shift` are grouped under "Unassigned" in coverage by shift. |
| A-15 | Following CLAUDE §7.8, a row that was still pending (never signed) on the old revision also gets a **Revision Change** row, so it shows Re-Sign Required, and its due date resets to Today() + `ResignDueDays`. |
| A-16 | A Manager who signs off a PWI on an employee's behalf must still upload the training log. `SignedOffBy` is the Manager. |
| A-17 | Users without SharePoint access see a friendly "You don't have access" message, triggered when the employee lookup returns a data-source error. |
| A-18 | If two files for the same assignment are uploaded on the same day and get the same name, the flow adds `_HHmmss` to the name so the earlier file isn't overwritten. |
| A-19 | Data volumes: no more than 2,000 active employees or documents, so filtered lookups stay delegable. No more than 500 affected rows per PWI revision (BR-38). Limits are documented in Admin-Guide.md. |
| A-20 | Seed data uses only CLAUDE §2 style placeholders (`Tech A`, `manager1@contoso.com`, `JQC-DEMO-100`, `PWI-DEMO-001`) and includes an expected-results table for matrix and cross-training checks. |

## 7. Open questions

| # | Question | Default until answered |
|---|---|---|
| OQ-01 | When a **JQC** is revised, what happens to JQC rows that are still pending on the old revision? Options: leave them for manual re-assignment, or move them automatically to the new revision. Moving them isn't a re-sign, but CLAUDE §7.9 and the rule that nobody signs off an outdated revision together leave this undefined. | A-09: manual re-assign, flagged in Sign-off Review |
| OQ-02 | Who sets `In Training`, and how is "training complete" recorded for a JQC so it can show **Waiting on Supervisor**? Could the designated trainer do it, even though trainers aren't an app role? | A-11 |
| OQ-03 | Technicians have Contribute on `JP_Assignments` and `JP_SignoffRecords`, so they could edit their own (or anyone's) rows in SharePoint directly. Is in-app enforcement enough for quality records, or should sign-off writes move to a flow running under a service account? This ties to the in-app sign-off open item. | In-app enforcement plus the §1.4 permissions |
| OQ-04 | `TODO:` Confirm the default re-sign due period of **14 days**. | 14 |
| OQ-05 | `TODO:` Confirm the cross-training target of **2 qualified per task**. Should it also apply per shift? | 2, overall only |
| OQ-06 | `TODO:` Does in-app sign-off (signed-in user + timestamp, plus the confirmation checkbox for JQCs) meet quality record requirements? | Assumed yes |
| OQ-07 | `TODO:` Which real groups map to JQCPWI Managers, Technicians and Viewers? | Placeholders |
| OQ-08 | Should a pending, never-signed row on a revised PWI show **Re-Sign Required** (literal CLAUDE §7.8) or stay **Pending**, and should it keep its original due date? | A-15: literal CLAUDE |
| OQ-09 | CLAUDE §5 makes sign-off files visible to Viewers but only their own to Technicians. Is that the intended privacy level? With Technicians at Contribute (§1.4), the restriction holds in the app only. | As specified |
| OQ-10 | Is a settings screen wanted, or is editing `JP_Settings` in SharePoint acceptable? | SharePoint only (A-04) |
| OQ-11 | Must `DocNumber` be unique, and is there a required revision label scheme (A, B, C… or 01, 02…)? | Unique number, free-text revision |
| OQ-12 | When an employee is deactivated, or a document made obsolete, should their pending rows be marked `Removed` automatically? | No (A-13) |
| OQ-13 | When several documents are assigned at once, should a trainer be chosen per document, or should one trainer apply to all? | Per document, optional |
| OQ-14 | Should a Manager be prevented from changing their own role or deactivating themselves, to avoid locking everyone out? | Not enforced; noted in Admin-Guide.md |
| OQ-15 | What are the expected data volumes? This confirms the A-19 limits for the matrix and for re-assigning rows after a revision. | A-19 |
| OQ-16 | Should Technicians and Viewers be able to open superseded revision files (version history) from the app, or only the current revision? | Current revision only. Managers can use SharePoint version history. |
