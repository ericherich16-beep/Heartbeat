# SPEC.md — JQC/PWI Management

> Functional specification for a Power Apps canvas app, delivered as an importable solution.
> Source: `intake.md`. `CLAUDE.md` (the build brief) was not provided with this request; where the two disagree, `CLAUDE.md` wins and this spec must be updated.
> **No confidential data.** Every name, number, URL and ID in this spec is a fictional placeholder.
> **This document contains no app code.**

---

## 0. Glossary

| Term | Meaning |
|---|---|
| **JQC** | Job Qualification Checklist. A template that a manager fills out and signs to confirm an employee is qualified for a job or task. |
| **PWI** | Process Work Instruction. A work instruction that an employee reads, trains on, and signs off themselves. |
| **Document** | A JQC or PWI, identified by its **Document Number** (for example `PWI-0001`). A document has one or more revisions. |
| **Revision** | One version of a document. Exactly one revision of each non-obsolete document is **current**. |
| **Assignment** | One employee's training requirement on one specific revision of one document. |
| **Active assignment** | An assignment with status `Pending` or `Completed`. |
| **Re-sign item** | A `Pending` assignment created automatically because a new PWI revision superseded an earlier one. |
| **Qualified** | See BR-40. In short: a `Completed` assignment that is still valid for the document's current revision. |
| **Evidence** | An uploaded file that supports a sign-off: a PWI training log or a signed JQC. |
| **Trainer** | An employee a manager has designated on a document. This is not an app role. |
| **Task** | One current, non-obsolete document, used as the unit of coverage in the cross-training view. |

---

## 1. User roles and permissions

### 1.1 Roles

| Role | Who | How the app decides the role |
|---|---|---|
| **Manager/Supervisor** ("Manager") | Production and quality managers and supervisors | Signed-in user's email matches an **active** `JP_Employees` row with `AppRole = Manager/Supervisor`. |
| **Technician** | Production and quality technicians | Signed-in user's email matches an **active** `JP_Employees` row with `AppRole = Technician`. |
| **Viewer** | Anyone who needs read-only access | Signed-in user's email matches an active `JP_Employees` row with `AppRole = Viewer`, **or** the user has no active `JP_Employees` row but can read the site (member of the placeholder `JP Viewers` SharePoint group). |
| *(no access)* | Everyone else | The user can't read the SharePoint site. The app shows the No Access screen (S15). |

Trainers are not a role. A trainer keeps whatever role they already have.

### 1.2 Permissions matrix

✅ = allowed · ❌ = not allowed · "Own" = only on records where the user is the assigned employee

| # | Capability | Manager | Technician | Viewer |
|---|---|:-:|:-:|:-:|
| P01 | Open the app and see Home | ✅ | ✅ | ✅ (no personal items) |
| P02 | See own pending, re-sign and completed items | ✅ | ✅ | ❌ (Viewers aren't assignable) |
| P03 | View and download **current** revisions of documents | ✅ | ✅ | ✅ |
| P04 | View document revision history (metadata) | ✅ | ✅ | ✅ |
| P05 | Open or download **superseded/obsolete** revision files | ✅ | ✅ (with "Not for use" banner) | ✅ (with "Not for use" banner) |
| P06 | Add a document (JQC or PWI) | ✅ | ❌ | ❌ |
| P07 | Edit document metadata and designate trainers | ✅ | ❌ | ❌ |
| P08 | Upload a new revision with change notes | ✅ | ❌ | ❌ |
| P09 | Mark a document Obsolete | ✅ | ❌ | ❌ |
| P10 | Assign documents to employees | ✅ | ❌ | ❌ |
| P11 | Mark an assignment Removed | ✅ | ❌ | ❌ |
| P12 | Upload a PWI training log | ✅ (any employee) | Own | ❌ |
| P13 | Sign off a PWI | ✅ (any employee, including self) | Own | ❌ |
| P14 | Upload a signed JQC and confirm qualification | ✅ (anyone **except self**) | ❌ | ❌ |
| P15 | Open evidence files (training logs, signed JQCs) | ✅ (all) | Own | ❌ (status only) |
| P16 | View the training matrix | ✅ | ✅ | ✅ |
| P17 | View the cross-training view | ✅ | ✅ | ✅ |
| P18 | View the Team Status screen | ✅ | ❌ | ❌ |
| P19 | View the employee list and employee training records (read-only) | ✅ | ✅ | ✅ |
| P20 | Add or edit employees, including marking them Inactive | ✅ | ❌ | ❌ |
| P21 | Change **own** `AppRole` or mark **self** Inactive | ❌ | ❌ | ❌ |
| P22 | Edit settings (cross-training target, re-sign due days) | ✅ | ❌ | ❌ |
| P23 | Delete any record or file | ❌ | ❌ | ❌ |

### 1.3 Security model (recommended)

- Every app user gets **Read** permission on all five lists and libraries through the placeholder SharePoint groups `JP Managers`, `JP Technicians` and `JP Viewers`. The `JP_SignoffRecords` permission is still an open question (OQ-07).
- **All writes go through Power Automate flows** that use the Power Apps (V2) trigger and run under a non-personal service-account SharePoint connection (a connection reference in the solution). The flows check the caller's role and every business rule again on the server side. Users never need Contribute rights, so nobody can change quality records outside the app.
- The app only hides or disables controls as a convenience. The flows are what actually enforce the rules.

---

## 2. Screen list

Every screen has a responsive layout for phone (< 640 px wide), tablet (640–1023 px) and desktop (≥ 1024 px), plus a shared header with role-filtered navigation.

| ID | Screen | Roles | Purpose |
|---|---|---|---|
| S01 | **Home / My Items** | All | Landing page. Technicians and Managers see their own Pending, Re-sign and Overdue items and their Completed history. Managers also see team counts. Viewers see quick links to the matrix, cross-training view and documents. |
| S02 | **Assignment Detail / Sign-Off** | Manager, Technician (own) | Open the assigned revision, upload evidence, and sign off (PWI) or confirm qualification (JQC). Shows the full history of the assignment when it's read-only. |
| S03 | **Documents** | All | Search and filter JQCs and PWIs (type, status, department, trainer). Opens S04. Managers can add a document from here. |
| S04 | **Document Detail** | All | Current revision metadata, file preview and download, trainers, revision history with change notes, and assignment and sign-off status per employee. Managers get Edit, Revise, Assign and Mark Obsolete actions here. |
| S05 | **Document Form (Add / Edit)** | Manager | Create a new document (first revision plus file) or edit the metadata and trainers of the current revision. |
| S06 | **Revise Document** | Manager | Upload a new revision with a revision label and change notes, and preview who will get re-sign items before confirming. |
| S07 | **Assign** | Manager | Assign one or more documents to one or more employees with a due date. Shows duplicates and ineligible employees before saving. |
| S08 | **Training Matrix** | All | Grid of employees by documents showing each cell's qualification state for the current revision, with filters. On phone it becomes a pivoted list. |
| S09 | **Cross-Training** | All | Coverage per task: qualified count against target, tasks below target, single points of failure, and gaps by shift. |
| S10 | **Team Status** | Manager | The manager's direct reports, or any filtered team: pending, re-sign, overdue and completed items, with Remove and Assign actions. |
| S11 | **Employees** | All (read-only) / Manager (edit) | Searchable employee directory with filters (department, shift, supervisor, role, active). Managers can add employees from here. |
| S12 | **Employee Detail** | All | One employee's profile and training record: active assignments and sign-off history. |
| S13 | **Employee Form (Add / Edit)** | Manager | Create or edit an employee, including role, job title, department, shift, supervisor and the active flag. |
| S14 | **Settings** | Manager | Edit the cross-training target and the re-sign due days. |
| S15 | **No Access / Not Registered** | Anyone the app can't resolve | Explains why the user has no access or only Viewer access, and whom to contact. No data is shown. |

---

## 3. Data model

### 3.1 Overview and relationships

```
JP_Employees (1) ──< (many) JP_Assignments >── (1) JP_Documents [one row per revision]
     │  ▲                         │
     │  └── Supervisor (self-lookup)        └──< (many) JP_SignoffRecords
     └──< Trainers (multi-lookup from JP_Documents)

JP_Settings: standalone key/value list
```

- `JP_Documents` stores **one row per revision**. Every revision of a document shares the same `DocumentNumber`. Exactly one row per `DocumentNumber` has `IsCurrentRevision = Yes`. Older revision files stay in the library for audit.
- `JP_Assignments.Document` points to a **specific revision** row. `DocumentNumber` is copied onto the assignment so lookups by document are delegable.
- `JP_SignoffRecords.Assignment` links each piece of evidence to the assignment it supports.
- SharePoint system columns (`ID`, `Created`, `Created By`, `Modified`, `Modified By`) exist on every list. Because flows write as a service account, the **acting user** is always stored in explicit Person columns as well.

### 3.2 `JP_Employees` (SharePoint list)

| Column (internal) | Display name | Type | Required | Rules / notes |
|---|---|---|:-:|---|
| `Title` | Full Name | Single line of text (255) | ✅ | Display name, for example "Alex Rivera". |
| `EmployeeNumber` | Employee Number | Single line of text (20) | ✅ | Unique (enforce unique values = Yes). Fictional, for example `E-1001`. |
| `UserAccount` | User Account | Person (single, people only) | ✅ | The Microsoft 365 account, picked with Office 365 Users search. |
| `UserEmail` | User Email | Single line of text (255) | ✅ | Unique, stored in lowercase. Copied from `UserAccount` and used for delegable lookup of the signed-in user. |
| `AppRole` | App Role | Choice: `Manager/Supervisor`, `Technician`, `Viewer` | ✅ | Default `Technician`. |
| `JobTitle` | Job Title | Single line of text (255) | ✅ | |
| `Department` | Department | Choice: `Production`, `Quality`, `Other` | ✅ | Choice values can be extended at deployment. |
| `Shift` | Shift | Choice: `1st`, `2nd`, `3rd`, `Weekend` | ✅ | Used for gaps by shift. |
| `Supervisor` | Supervisor | Lookup → `JP_Employees.Title` (single) | ❌ | Must be an active employee with `AppRole = Manager/Supervisor`. Can't be the employee themselves. |
| `IsActive` | Active | Yes/No | ✅ | Default Yes. Inactive employees are never deleted. |
| `InactiveDate` | Inactive Date | Date only | ❌ | Set when `IsActive` changes to No. Cleared when it changes back. |
| `LastChangedBy` | Last Changed By | Person | ✅ (system) | Set by the flow to the acting user. |

### 3.3 `JP_Documents` (document library, one item per revision)

| Column (internal) | Display name | Type | Required | Rules / notes |
|---|---|---|:-:|---|
| *(file)* `Name` | File Name | File | ✅ | PDF, DOCX, XLSX, JPG or PNG, ≤ 25 MB. Renamed by the flow to `{DocumentNumber}_Rev{Revision}.{ext}`. |
| `Title` | Document Title | Single line of text (255) | ✅ | |
| `DocumentNumber` | Document Number | Single line of text (30) | ✅ | Unique **across documents**, not across revisions. Stored in uppercase. Example: `PWI-0001`, `JQC-0001`. Can't be changed after creation. |
| `DocumentType` | Type | Choice: `JQC`, `PWI` | ✅ | Can't be changed after creation. |
| `Revision` | Revision | Single line of text (10) | ✅ | Label such as `A`, `B` or `01`. Unique within a `DocumentNumber`. |
| `RevisionSequence` | Revision Sequence | Number (integer, ≥ 1) | ✅ (system) | 1 for the first revision, then +1 for each new revision. Used for ordering. |
| `ChangeNotes` | Change Notes | Multiple lines of text (plain) | ✅ when `RevisionSequence > 1` | Optional on the first revision ("Initial release" by default). |
| `Trainers` | Trainers | Lookup → `JP_Employees.Title` (**multiple**) | ❌ to save, ✅ to assign | Active employees only. Copied forward to each new revision. |
| `Department` | Department | Choice (same values as employees) | ❌ | Used as a filter on S03, S08 and S09. |
| `CrossTrainingTarget` | Cross-Training Target | Number (integer, 1–50) | ❌ | Overrides the global target for this task. Blank means use `JP_Settings.CrossTrainingTarget`. |
| `DocStatus` | Status | Choice: `Active`, `Superseded`, `Obsolete` | ✅ (system) | |
| `IsCurrentRevision` | Current Revision | Yes/No | ✅ (system) | Exactly one row per `DocumentNumber` is Yes. That row's `DocStatus` is `Active` or `Obsolete`. |
| `EffectiveDate` | Effective Date | Date only | ✅ (system) | Date the revision was uploaded. |
| `UploadedBy` | Uploaded By | Person | ✅ (system) | Acting manager. |
| `SupersededDate` | Superseded Date | Date only | ❌ (system) | |
| `ObsoleteDate` / `ObsoleteBy` / `ObsoleteReason` | — | Date only / Person / Multiple lines | ❌ (system) | Set when the document is marked Obsolete. `ObsoleteReason` is required at that point. |

Library settings: versioning on (major versions), content approval off, no folders, check-out not required.

### 3.4 `JP_Assignments` (SharePoint list)

| Column (internal) | Display name | Type | Required | Rules / notes |
|---|---|---|:-:|---|
| `Title` | Title | Single line of text | ✅ (system) | `{DocumentNumber} Rev {Revision} – {EmployeeNumber}`. |
| `Employee` | Employee | Lookup → `JP_Employees.Title` | ✅ | |
| `EmployeeEmail` | Employee Email | Single line of text | ✅ (system) | Copied for delegable "my items" queries. |
| `Document` | Document Revision | Lookup → `JP_Documents.Title` (revision row) | ✅ | Always the revision that was current when the row was created. |
| `DocumentNumber` | Document Number | Single line of text | ✅ (system) | Copied from the document. |
| `DocumentType` | Type | Choice: `JQC`, `PWI` | ✅ (system) | Copied from the document. |
| `Revision` | Revision | Single line of text | ✅ (system) | Copied from the document. |
| `AssignmentStatus` | Status | Choice: `Pending`, `Completed`, `Superseded`, `Removed` | ✅ | Default `Pending`. |
| `AssignmentReason` | Reason | Choice: `Initial`, `Re-sign` | ✅ | |
| `DueDate` | Due Date | Date only | ✅ | Must be today or later when created. |
| `AssignedBy` | Assigned By | Person | ✅ (system) | |
| `AssignedOn` | Assigned On | Date and time | ✅ (system) | |
| `SignedOffBy` | Signed Off By | Person | On Completed | The signed-in user who completed the sign-off. |
| `SignedOffOn` | Signed Off On | Date and time | On Completed | Server time (UTC) from the flow. |
| `Attestation` | Attestation Accepted | Yes/No | On Completed | PWI: "I have been trained on and understand this revision." JQC: "I confirm this employee is qualified." |
| `EvidenceRecord` | Evidence | Lookup → `JP_SignoffRecords.Title` | On Completed | The evidence file used for the sign-off. |
| `PreviousAssignment` | Previous Assignment | Lookup → `JP_Assignments.ID` | ❌ | Set on rows created by a revision. Points to the row that was superseded. |
| `SupersededOn` | Superseded On | Date and time | On Superseded | |
| `RemovedBy` / `RemovedOn` / `RemovedReason` | — | Person / Date and time / Multiple lines | On Removed | `RemovedReason` is required. |
| `Comments` | Comments | Multiple lines of text (plain, 2,000) | ❌ | Optional note at sign-off. |

Calculated in the app, not stored: **Overdue** = `AssignmentStatus = Pending` and `DueDate < Today`.

### 3.5 `JP_SignoffRecords` (document library)

| Column (internal) | Display name | Type | Required | Rules / notes |
|---|---|---|:-:|---|
| *(file)* `Name` | File Name | File | ✅ | PDF, DOCX, XLSX, JPG or PNG, ≤ 25 MB. Renamed to `{DocumentNumber}_Rev{Revision}_{EmployeeNumber}_{yyyyMMddHHmmss}.{ext}`. |
| `Title` | Title | Single line of text | ✅ (system) | Same as the file name without its extension. |
| `RecordType` | Record Type | Choice: `PWI Training Log`, `Signed JQC` | ✅ | Must match the document type of the assignment. |
| `Assignment` | Assignment | Lookup → `JP_Assignments.Title` | ✅ | |
| `Employee` | Employee | Lookup → `JP_Employees.Title` | ✅ (system) | Copied from the assignment. |
| `DocumentNumber` / `Revision` | — | Single line of text | ✅ (system) | Copied from the assignment. |
| `UploadedBy` | Uploaded By | Person | ✅ (system) | |
| `UploadedOn` | Uploaded On | Date and time | ✅ (system) | |
| `RecordStatus` | Record Status | Choice: `Uploaded`, `Final`, `Replaced` | ✅ (system) | `Uploaded` until sign-off, then `Final`. If a newer file is uploaded for the same assignment before sign-off, the older one becomes `Replaced`. |

### 3.6 `JP_Settings` (SharePoint list, key/value)

| Column | Type | Required | Notes |
|---|---|:-:|---|
| `Title` (Setting Key) | Single line of text, unique | ✅ | |
| `NumberValue` | Number (integer) | ✅ | |
| `Description` | Multiple lines of text | ❌ | |

Seed rows:

| Title | NumberValue | Allowed range | Description |
|---|---|---|---|
| `CrossTrainingTarget` | 2 | 1–50 | Qualified employees required per task (global default). |
| `ResignDueDays` | 14 | 1–365 | Days from revision date until a re-sign item is due. Also used as the default due date offset on the Assign screen. |

### 3.7 Solution components (for reference, not code)

- **Environment variables:** `jp_SiteUrl` (Data source / Site), and one Data source / List variable for each of `JP_Employees`, `JP_Documents`, `JP_Assignments`, `JP_SignoffRecords` and `JP_Settings`. Nothing is hard-coded.
- **Connection references:** SharePoint (user) for app reads, SharePoint (service account) for flows, Office 365 Users.
- **Flows (Power Apps V2 trigger):** Save Employee, Save Document, Revise Document, Mark Document Obsolete, Create Assignments, Remove Assignment, Upload Evidence, Complete Sign-Off, Save Settings. Each one returns `{ success, message, ids }`.

---

## 4. Business rules (numbered, testable)

### Access and roles
- **BR-01** The app resolves the signed-in user's role by matching their lowercase email to an **active** `JP_Employees.UserEmail` and reading `AppRole`.
- **BR-02** A user with no active `JP_Employees` row who can read the site is treated as a Viewer. A user who can't read the site sees S15 and no data.
- **BR-03** Every write flow checks the caller's role again on the server. A call from a role that isn't allowed by §1.2 is rejected with the message "You don't have permission to perform this action." and nothing is written.
- **BR-04** No role can delete list items or files through the app. No flow contains a delete action.

### Required fields and validation
- **BR-05** A form can't be saved while any required field (marked ✅ in §3) is blank. The Save button is disabled and each missing field shows an inline message.
- **BR-06** `EmployeeNumber` and `UserEmail` are each unique across all employees, active or inactive. A duplicate is rejected with a message that names the existing employee.
- **BR-07** `DocumentNumber` is unique across documents. Creating a document whose number already exists, in any status, is rejected.
- **BR-08** A new revision label must differ from every earlier revision label of the same `DocumentNumber`, compared without regard to case.
- **BR-09** `ChangeNotes` is required for every revision after the first.
- **BR-10** `DueDate` can't be earlier than today when an assignment is created.

### Employees
- **BR-11** Only Managers can create or edit employees.
- **BR-12** A Manager can't change their own `AppRole` or set their own `IsActive` to No.
- **BR-13** `Supervisor` must be an active employee with `AppRole = Manager/Supervisor` and can't be the employee themselves.
- **BR-14** Setting an employee to Inactive marks all of their `Pending` assignments `Removed`, with reason "Employee inactive". Their `Completed` assignments are kept unchanged for history.
- **BR-15** Inactive employees don't appear in the matrix, the cross-training counts, trainer pickers or assignee pickers. They do appear in S11 when the "Show inactive" filter is on.
- **BR-16** Reactivating an employee doesn't restore any assignments that were Removed.
- **BR-17** Only employees with `AppRole` Technician or Manager/Supervisor can be assigned documents or designated as trainers.

### Documents and trainers
- **BR-18** Only Managers can add documents, edit document metadata, designate trainers, upload revisions or mark documents Obsolete.
- **BR-19** A new document is created as revision sequence 1 with `DocStatus = Active` and `IsCurrentRevision = Yes`.
- **BR-20** A document can be saved with no trainers, but it can't be assigned until its current revision has at least one active trainer. The Assign action is disabled and the flow rejects the call.
- **BR-21** Editing metadata (title, trainers, department, cross-training target) changes the current revision row only. It doesn't create a revision and doesn't affect assignments.
- **BR-22** `DocumentNumber` and `DocumentType` can't be changed after creation. The file can be replaced only by uploading a revision.
- **BR-23** Marking a document Obsolete requires a reason, sets `DocStatus = Obsolete` on the current revision, and marks all `Pending` assignments for that `DocumentNumber` `Removed` with reason "Document obsolete". `Completed` assignments are kept.
- **BR-24** Obsolete documents can't be assigned, revised or edited, and they're left out of the matrix and cross-training view. They stay visible on S03 when the "Show obsolete" filter is on.

### Assignments
- **BR-25** Only Managers can create or remove assignments.
- **BR-26** A new assignment always points to the document's **current** revision.
- **BR-27** **No duplicate active assignments:** an employee can have at most one assignment with status `Pending` or `Completed` per `DocumentNumber`. Assigning a document to an employee who already has one is skipped and reported as "already assigned". It isn't an error for the rest of the batch.
- **BR-28** A batch assignment from S07 creates one row per eligible (employee, document) pair with `AssignmentReason = Initial`, `AssignedBy` = the current user and `AssignedOn` = server time.
- **BR-29** Removing an assignment requires a reason and sets `AssignmentStatus = Removed`, `RemovedBy` and `RemovedOn`. Both `Pending` and `Completed` assignments can be removed.
- **BR-30** After an assignment is Removed, the same document can be assigned to that employee again. The new row points to the current revision.

### Sign-offs
- **BR-31** A sign-off is allowed only on an assignment that is `Pending` **and** points to a revision with `IsCurrentRevision = Yes` and `DocStatus = Active`. Any other sign-off attempt is rejected, both in the UI and in the flow.
- **BR-32** **PWI:** the assigned employee or any Manager can sign off.
- **BR-33** **PWI:** the Sign Off button stays disabled until a `PWI Training Log` evidence file with status `Uploaded` exists for that assignment **and** the attestation checkbox is ticked.
- **BR-34** **JQC:** only a Manager can sign off, and only when the Manager isn't the assigned employee. A Manager viewing their own JQC assignment sees it as read-only, with the message "Another manager must sign off your JQC."
- **BR-35** **JQC:** the Confirm Qualified button stays disabled until a `Signed JQC` evidence file with status `Uploaded` exists for that assignment **and** the "I confirm this employee is qualified" checkbox is ticked.
- **BR-36** On sign-off, the flow sets `AssignmentStatus = Completed`, `SignedOffBy` = the signed-in user, `SignedOffOn` = server UTC time, `Attestation = Yes` and `EvidenceRecord`, and changes that evidence record to `Final`.
- **BR-37** A `Completed` assignment can't be signed off again or edited. The only change allowed is Remove (BR-29), or Superseded through a revision.

### Revisions
- **BR-38** **New PWI revision:** the flow, as a single logical operation, (a) creates the new revision row (`Active`, current), copying trainers forward; (b) sets the old current row to `Superseded`, not current, and fills in `SupersededDate`; (c) for each active assignment on that `DocumentNumber`:
  - if the employee is **active** and the assignment was `Completed`: marks it `Superseded` and creates a new `Pending` row on the new revision with `AssignmentReason = Re-sign`, `DueDate = today + ResignDueDays`, and `PreviousAssignment` set;
  - if the employee is **active** and the assignment was `Pending`: marks it `Superseded` and creates a new `Pending` row on the new revision that keeps its original `AssignmentReason` and `DueDate` (or today + `ResignDueDays`, whichever is later), with `PreviousAssignment` set;
  - if the employee is **inactive**: marks it `Superseded` and creates nothing.
- **BR-39** **New JQC revision:** the flow does (a) and (b) from BR-38. `Completed` JQC assignments stay `Completed` and remain valid (see BR-40). `Pending` JQC assignments are moved to the new revision in the same way as pending PWI assignments, so nobody can sign off an outdated revision. No re-sign items are created.
- **BR-40** **Qualified** means:
  - PWI: the employee is active and has a `Completed` assignment on the **current** revision.
  - JQC: the employee is active and has a `Completed` assignment on any revision of the document, and the document isn't Obsolete. A JQC revision doesn't invalidate earlier qualifications (assumption A-08 / OQ-01).
- **BR-41** Employees assigned after a revision is issued are always assigned the revision that is current at that time (follows from BR-26).
- **BR-42** If a revision flow fails partway, it reports failure, and running it again for the same new revision label finishes the remaining steps without creating duplicate rows. In other words, the flow is idempotent and keyed on `DocumentNumber` + `Revision` + employee.

### Matrix and cross-training
- **BR-43** Each matrix cell shows exactly one state, chosen in this order of precedence:
  1. **Qualified** (BR-40)
  2. **Re-sign due**: `Pending` with reason `Re-sign`
  3. **Overdue**: `Pending` and past the due date
  4. **Pending**
  5. **Not assigned**: no active assignment

  Re-sign due and Overdue can both apply. In that case the cell shows Re-sign with an overdue marker.
- **BR-44** Matrix rows are active employees with `AppRole` Technician or Manager/Supervisor. Matrix columns are current, non-obsolete documents.
- **BR-45** The effective cross-training target for a task is `JP_Documents.CrossTrainingTarget` if set, otherwise `JP_Settings.CrossTrainingTarget`, otherwise 2.
- **BR-46** **Below target:** a task where the count of qualified active employees is less than the effective target.
- **BR-47** **Single point of failure:** a task with exactly 1 qualified active employee.
- **BR-48** **Shift gap:** for a task and a shift that has at least one active Technician or Manager employee, there are 0 qualified employees on that shift.
- **BR-49** A task with 0 qualified employees is flagged **No coverage**. It also counts as below target.

### Uploads
- **BR-50** Only `.pdf`, `.docx`, `.xlsx`, `.jpg`, `.jpeg` and `.png` files are accepted, checked by extension in the app and again in the flow, case-insensitively.
- **BR-51** Files larger than 25 MB (26,214,400 bytes) are rejected with a message showing the file's size.
- **BR-52** Each upload, of a document revision or of evidence, accepts exactly one file.
- **BR-53** Uploading a new evidence file for a `Pending` assignment that already has an `Uploaded` evidence file marks the earlier file `Replaced`. Neither file is deleted.

### Records and audit
- **BR-54** Nothing is ever deleted. Status changes replace deletion: assignments become `Removed` or `Superseded`, documents become `Obsolete`, employees become Inactive.
- **BR-55** Every write records the acting user (an explicit Person column) and a server timestamp.
- **BR-56** The full sign-off history of an employee (every assignment, including Superseded and Removed) and of a document (every revision and assignment) can be viewed on S12 and S04.

### Settings
- **BR-57** Only Managers can edit settings. Values outside the allowed ranges in §3.6 are rejected.
- **BR-58** Changing `ResignDueDays` affects only re-sign items created afterwards. Existing due dates don't change.
- **BR-59** Changing `CrossTrainingTarget` updates the cross-training view the next time data is refreshed. Nothing stored is recalculated.

---

## 5. Acceptance criteria per screen

Format: **AC-Sxx-n**. Each one should pass with the fictional sample data set (§5.16).

### S01 Home / My Items
- **AC-S01-1** A Technician sees three tabs or sections: **To Do** (Pending, with re-sign items labelled "Re-sign" and overdue items highlighted), **Completed**, and a count badge for each.
- **AC-S01-2** To Do is sorted by overdue first, then by due date ascending.
- **AC-S01-3** Only the signed-in user's own assignments with status `Pending`/`Completed` appear. Superseded and Removed items don't.
- **AC-S01-4** Selecting an item opens S02 for that assignment.
- **AC-S01-5** A Manager also sees team tiles (Pending, Re-sign, Overdue counts for their direct reports) that open S10 with that filter applied.
- **AC-S01-6** A Viewer sees no personal items section, only navigation tiles to S03, S08 and S09.
- **AC-S01-7** On a phone, the sections stack in one column with no horizontal scrolling.

### S02 Assignment Detail / Sign-Off
- **AC-S02-1** Shows employee, document number and title, type, revision, status, reason, due date, assigned by and on, and an Open/Download button for the assigned revision's file.
- **AC-S02-2** For a PWI assignment that is `Pending` on the current revision, the assigned Technician sees Upload Training Log, an attestation checkbox and a Sign Off button. Sign Off stays disabled until both an upload exists and the checkbox is ticked (BR-33).
- **AC-S02-3** After a successful PWI sign-off, the status shows `Completed` with "Signed off by {name} on {local date/time}", and the item moves from To Do to Completed on S01.
- **AC-S02-4** For a JQC assignment, a Technician sees status and document only, with no upload or sign-off controls.
- **AC-S02-5** For a JQC assignment of another employee, a Manager sees Upload Signed JQC, a "I confirm this employee is qualified" checkbox and a Confirm Qualified button, which follows the same enable rules (BR-35).
- **AC-S02-6** For a Manager's **own** JQC assignment, the sign-off controls are hidden and the message from BR-34 is shown.
- **AC-S02-7** Trying to upload a `.exe`, or a PDF larger than 25 MB, shows a validation message and uploads nothing.
- **AC-S02-8** If the document was revised while the screen was open, pressing Sign Off fails with "This revision is no longer current. Open your new item from Home." and nothing is written.
- **AC-S02-9** A `Completed`, `Superseded` or `Removed` assignment is read-only and shows its history: evidence link (P15 visibility applies), who signed and when, superseded or removed info, and a link to the next or previous assignment.
- **AC-S02-10** A Manager can open S02 for any employee. A Technician who opens another employee's assignment (for example through a deep link) sees "You can only view your own items."

### S03 Documents
- **AC-S03-1** Lists current revisions only by default, showing number, title, type, revision, effective date, trainer count and status.
- **AC-S03-2** Search matches document number or title. Filters: type, department, status (Active by default, Obsolete optional), "I'm a trainer".
- **AC-S03-3** Documents with no trainers show a "No trainer — can't assign" badge (Managers only).
- **AC-S03-4** The **+ New Document** button is visible only to Managers and opens S05 in Add mode.
- **AC-S03-5** Selecting a row opens S04.

### S04 Document Detail
- **AC-S04-1** Shows current revision metadata, trainers, change notes, and Open/Download.
- **AC-S04-2** **Revision history** lists every revision, newest first, with label, effective date, uploaded by and change notes. Opening a superseded or obsolete file shows the banner "Superseded — not for use".
- **AC-S04-3** **Assignments** tab lists the current status of each assigned employee (Qualified, Re-sign due, Pending, Overdue), with counts. Managers can also show Removed and Superseded rows.
- **AC-S04-4** Managers see **Edit**, **Revise**, **Assign** and **Mark Obsolete**. Technicians and Viewers see none of these.
- **AC-S04-5** **Assign** is disabled, with the tooltip "Add at least one trainer first", when the current revision has no active trainers.
- **AC-S04-6** **Mark Obsolete** asks for a required reason and confirmation. Afterwards the document shows status Obsolete and all its pending assignments show Removed (BR-23).
- **AC-S04-7** For an Obsolete document, Edit, Revise and Assign are hidden.

### S05 Document Form (Add / Edit)
- **AC-S05-1** Add mode requires a file, document number, title, type and revision label. Trainers, department and target are optional.
- **AC-S05-2** Saving with a duplicate document number shows "Document number PWI-0001 already exists." and saves nothing.
- **AC-S05-3** File type and size rules (BR-50, BR-51) are enforced before the save is sent.
- **AC-S05-4** The trainer picker lists only active Technician and Manager employees and allows more than one choice.
- **AC-S05-5** Edit mode shows document number, type, revision and file as read-only. Only title, trainers, department and cross-training target can be edited.
- **AC-S05-6** After saving, the user returns to S04 for that document and sees the saved values.

### S06 Revise Document
- **AC-S06-1** Requires a new file, a new revision label (BR-08) and change notes (BR-09). Trainers are pre-filled from the current revision and can be edited.
- **AC-S06-2** Before confirming, the screen shows an impact preview. For a **PWI**: "{n} employees will need to re-sign; {m} pending items move to the new revision; {k} inactive employees' items will be superseded." For a **JQC**: "Existing qualifications stay valid; {m} pending items move to the new revision."
- **AC-S06-3** After confirming a PWI revision, S04 shows the new revision as current. Every previously Completed active employee has a `Pending`/`Re-sign` item due today + `ResignDueDays`, and their old row is `Superseded`.
- **AC-S06-4** After a PWI revision, the matrix shows those employees as **Re-sign due**, not Qualified.
- **AC-S06-5** After a JQC revision, previously qualified employees are still shown as Qualified in the matrix, and no re-sign items exist.
- **AC-S06-6** A revision label that's already been used shows "Revision B already exists for PWI-0001." and nothing is saved.

### S07 Assign
- **AC-S07-1** The manager picks one or more current, active documents that have at least one trainer, and one or more active Technician or Manager employees. Filters by department, shift and supervisor help with the selection.
- **AC-S07-2** Due date is required. It defaults to today + `ResignDueDays` and can't be in the past.
- **AC-S07-3** Before saving, a summary shows "{x} new assignments, {y} already assigned (skipped)", listing who is skipped.
- **AC-S07-4** Saving creates exactly {x} rows, each pointing to the current revision. Running the same assignment again creates 0 new rows (BR-27).
- **AC-S07-5** Documents with no trainer can't be selected and show the reason.
- **AC-S07-6** Only Managers can reach this screen. A deep link from another role redirects to S01 with a permission message.

### S08 Training Matrix
- **AC-S08-1** On desktop and tablet, rows are employees (BR-44) and columns are documents, with sticky headers. Each cell shows one state from BR-43, using an icon **and** a text label or tooltip, so color isn't the only cue.
- **AC-S08-2** Filters: department, shift, supervisor ("My team" shortcut for Managers), document type, employee search and document search. A legend is always visible.
- **AC-S08-3** A PWI cell is Qualified only when the sign-off is on the current revision. A cell that was Qualified before a PWI revision shows **Re-sign due** after it.
- **AC-S08-4** JQC cells qualified on an older revision show Qualified with the tooltip "Signed on Rev {x}".
- **AC-S08-5** Selecting a cell opens S02 for that assignment, read-only unless permissions allow sign-off. Selecting an empty cell does nothing for Technicians and Viewers. For Managers it offers "Assign".
- **AC-S08-6** On a phone, the matrix becomes a list grouped by employee, with a toggle to group by document. Each entry shows the state label.
- **AC-S08-7** Totals are shown per row (qualified/assigned) and per column (qualified count against target).
- **AC-S08-8** The matrix loads correctly with the sample data at test scale (NFR-02), and nothing is missing because of delegation limits.

### S09 Cross-Training
- **AC-S09-1** Lists every task (current, non-obsolete document) with qualified count, effective target and a status of OK, Below target, Single point of failure or No coverage (BR-45–BR-49).
- **AC-S09-2** Has quick filters for **Below target**, **Single point of failure** and **No coverage**, plus filters for type and department.
- **AC-S09-3** **Gaps by shift**: a task × shift table with qualified counts, where cells with 0 are marked as a gap (BR-48). Only shifts that have active employees appear.
- **AC-S09-4** Each task shows the names of its qualified employees and how many are in progress (Pending/Re-sign), so managers can see who will soon close the gap.
- **AC-S09-5** Changing `CrossTrainingTarget` in S14 changes the Below target results the next time the screen is opened.
- **AC-S09-6** On a phone, the task list and the shift table display as cards.

### S10 Team Status
- **AC-S10-1** Defaults to the signed-in manager's direct reports (`Supervisor` = me). The manager can pick another supervisor, department or shift.
- **AC-S10-2** Shows each employee with Pending, Re-sign and Overdue counts. Expanding an employee shows their items.
- **AC-S10-3** Has a filter for Overdue only and Re-sign only.
- **AC-S10-4** **Remove** on an item asks for a required reason. Afterwards the item disappears from the active list and shows as Removed on S12.
- **AC-S10-5** **Assign** opens S07 with the selected employees already chosen.

### S11 Employees
- **AC-S11-1** Lists active employees by default, with name, employee number, job title, department, shift, supervisor and role. "Show inactive" includes inactive employees with an Inactive badge.
- **AC-S11-2** Search matches name or employee number. There are filters for department, shift, supervisor and role.
- **AC-S11-3** **+ New Employee** is visible only to Managers.
- **AC-S11-4** Selecting a row opens S12.

### S12 Employee Detail
- **AC-S12-1** Shows the profile fields and a training record: active assignments with their BR-43 state, and a History tab with every Superseded, Removed and Completed assignment.
- **AC-S12-2** Evidence links follow P15: Managers see every file, the employee sees their own, and Viewers see none.
- **AC-S12-3** Managers see **Edit** and **Assign**. **Edit** opens S13.
- **AC-S12-4** For an inactive employee, a banner shows "Inactive since {date}" and Assign is hidden.

### S13 Employee Form (Add / Edit)
- **AC-S13-1** The user account is picked with an Office 365 Users search. Choosing it fills in full name and email, and the full name can be edited.
- **AC-S13-2** The required fields (BR-05) are enforced. Duplicate employee number or email is rejected (BR-06).
- **AC-S13-3** The Supervisor picker lists only active Manager employees and excludes the employee being edited.
- **AC-S13-4** When a Manager edits their own record, AppRole and Active are read-only (BR-12).
- **AC-S13-5** Setting Active to No shows a confirmation: "{n} pending items will be marked Removed." After confirming, those items are Removed (BR-14).

### S14 Settings
- **AC-S14-1** Shows `CrossTrainingTarget` and `ResignDueDays` with their descriptions and allowed ranges.
- **AC-S14-2** Values that are out of range or not whole numbers are rejected inline.
- **AC-S14-3** Saving shows a confirmation and records who changed it and when.
- **AC-S14-4** Only Managers can reach this screen.

### S15 No Access / Not Registered
- **AC-S15-1** A user who can't read the site sees "You don't have access to JQC/PWI Management. Contact your supervisor or site owner." and no data or navigation.
- **AC-S15-2** A user with read access but no employee record gets Viewer access, and a dismissible notice says "You have read-only access. Ask a manager to add you as an employee to receive assignments."

### 5.16 Cross-cutting acceptance criteria
- **AC-X-1** Every screen works with no horizontal page scrolling at 360 px, 768 px and 1366 px widths. The matrix grid may scroll inside its own container.
- **AC-X-2** Every write shows a busy indicator, then a success or error notification that uses the flow's message. A failed write leaves the screen data unchanged.
- **AC-X-3** No SharePoint site URL or list name appears as a literal in the app or flows. All of them come from environment variables.
- **AC-X-4** The solution imports into a clean environment, and after the environment variables and connection references are set, it runs against freshly created lists with sample data.
- **AC-X-5** The sample data set uses only fictional names, numbers and files, for example employees "Alex Rivera (E-1001)" and "Sam Patel (E-1002)", documents "PWI-0001 Widget Torque Check" and "JQC-0001 Line 1 Operator". It covers every state in BR-43 and every flag in BR-46 to BR-49.
- **AC-X-6** Controls have accessible labels, a logical tab order, and color contrast of at least 4.5:1. Status is never shown by color alone.

### Non-functional requirements
- **NFR-01** Standard connectors only: SharePoint, Office 365 Users, and Power Automate with the Power Apps trigger. No premium connectors, Dataverse, PCF or code components.
- **NFR-02** Test scale: 300 active employees, 300 current documents and 10,000 assignment rows. Data screens must load within 5 s on desktop over a normal corporate network, and must not drop records because of the 2,000-row delegation limit.
- **NFR-03** Times are stored in UTC and shown in the user's local time zone.

---

## 6. Assumptions

| # | Assumption |
|---|---|
| A-01 | `CLAUDE.md` wasn't available. This spec is based only on `intake.md` and must be reconciled with `CLAUDE.md` when it's provided. |
| A-02 | The app is a **canvas** app (model-driven needs Dataverse, which is out of scope). |
| A-03 | Every Technician and Manager has a Microsoft 365 account and a Power Apps license that covers standard connectors. |
| A-04 | The app role is stored in `JP_Employees.AppRole`. The SharePoint groups only control read access to the site and lists. |
| A-05 | All writes run through Power Automate flows that use a service-account connection, so users only need Read permissions (§1.3). This needs a non-personal service account. |
| A-06 | `JP_Documents` stores one item per revision, so superseded files stay available for audit. This differs from a literal reading of the intake ("current revision" as a column on one item). |
| A-07 | "Task" in the cross-training view means one current, non-obsolete document, either JQC or PWI. |
| A-08 | After a JQC revision, existing JQC qualifications stay valid (Qualified = Completed on any non-obsolete revision of that JQC). This reconciles "a new JQC revision doesn't force anyone to re-sign" with "qualified means signed off on the current revision". |
| A-09 | Pending items on a revised document, PWI or JQC, are moved to the new revision because "no one can sign off on an outdated revision". A moved pending PWI item keeps its reason and the later of its original due date and today + `ResignDueDays`. |
| A-10 | Any Manager can sign off any employee's PWI or JQC (except their own JQC). The signer doesn't have to be the employee's supervisor or a designated trainer. |
| A-11 | Trainers don't have to be qualified on the document themselves. |
| A-12 | Trainers are chosen from active Technician or Manager employees in `JP_Employees`, using a multi-value lookup. |
| A-13 | An initial assignment needs a due date, which defaults to today + `ResignDueDays`. |
| A-14 | Employees with `AppRole = Viewer` can't be assigned and don't appear as matrix rows. Users with no employee record who can read the site are Viewers. |
| A-15 | Making an employee inactive removes their pending items. Making a document obsolete removes its pending items. Completed items are kept for history in both cases. Reactivating restores nothing, and obsolete documents can't be reactivated. |
| A-16 | A Manager can't change their own role or deactivate themselves. The first Manager is added directly in SharePoint by the site owner at deployment. |
| A-17 | The same allowed file types and 25 MB limit apply to both document files and evidence files. |
| A-18 | The JQC has a single sign-off: the manager uploads the already-signed paper or electronic JQC and confirms. The employee doesn't also sign in the app. |
| A-19 | Department and Shift are choice columns with placeholder values (`Production`/`Quality`/`Other`; `1st`/`2nd`/`3rd`/`Weekend`) that can be edited at deployment. |
| A-20 | The cross-training target can be overridden per document. The global setting is the default. |
| A-21 | A shift gap means 0 qualified employees on a shift that has active employees. The target isn't applied per shift. |
| A-22 | Superseded and obsolete revision files can be opened by every role but are clearly marked "not for use". |
| A-23 | Excel export of the matrix isn't required. Users can see everything in the app. |
| A-24 | Sign-off in the app records the signed-in user and a server UTC timestamp. No separate electronic signature or password re-entry is required (pending OQ-03). |
| A-25 | `EmployeeNumber` is added as a unique business key, although the intake doesn't list it. |
| A-26 | Volumes stay within NFR-02 for the first phase. |

## 7. Open questions

| # | Question | Why it matters | Default if unanswered |
|---|---|---|---|
| OQ-01 | After a **JQC** revision, should employees qualified on the earlier revision still count as Qualified, or become "not qualified" until a manager manually re-qualifies them? | The intake says both "JQC revision doesn't force re-sign" and "Qualified = current revision". This changes the matrix and the cross-training counts. | A-08: they stay Qualified. |
| OQ-02 | Confirm the default re-sign due period of **14 days**. *(intake open item)* | Seed value for `ResignDueDays`. | 14 |
| OQ-03 | Does in-app sign-off (signed-in user + timestamp + attestation) meet quality record requirements, or is an electronic signature, re-authentication or 21 CFR Part 11-style control needed? *(intake open item)* | Could need extra steps or a different approach. | A-24 |
| OQ-04 | Confirm the cross-training target of **2 qualified per task**. *(intake open item)* Should it apply per shift as well as overall? | Changes BR-46 and BR-48. | 2, overall only |
| OQ-05 | Which real SharePoint groups map to `JP Managers`, `JP Technicians` and `JP Viewers`? *(intake open item)* | Needed at deployment. | Placeholders |
| OQ-06 | Is a service account available for the flow connection (A-05)? If not, users would need Contribute on the lists, and rules could be bypassed through SharePoint directly. | Record integrity. | Service account required |
| OQ-07 | Who may open evidence files (signed JQCs, training logs)? Should Technicians be blocked from opening other people's evidence at the SharePoint level, not just in the app? | Privacy. App-only restrictions can be bypassed by anyone with Read permission. | UI restriction only; library readable by Managers and Technicians groups, not Viewers. |
| OQ-08 | Should only the employee's own supervisor, or a designated trainer, be allowed to sign off JQCs (and PWIs on behalf of others), instead of any Manager? | Changes BR-32 and BR-34. | Any Manager (A-10) |
| OQ-09 | Must a trainer be qualified on the document before being designated? | Changes trainer picker validation. | No (A-11) |
| OQ-10 | Should a PWI sign-off also need trainer confirmation, for example the trainer named on the training log? | Possible extra field or step. | No |
| OQ-11 | What are the real department, shift and job title values? Should job titles be a controlled list? | Choice column values. | A-19 |
| OQ-12 | Do revision labels follow a set scheme (A, B, C… or 01, 02…)? Should the app suggest the next label? | Validation of `Revision`. | Free text, unique per document |
| OQ-13 | When an employee is deactivated or a document made obsolete, should their pending items be Removed automatically (A-15), or left for a manager to decide? | Data cleanliness compared with control. | Automatic |
| OQ-14 | Should Viewers be able to open superseded or obsolete revision files (A-22)? | Risk of someone using outdated instructions. | Yes, with a banner |
| OQ-15 | Is an Excel or CSV export of the matrix needed for audits or meetings (A-23)? | Scope. | Not in phase 1 |
| OQ-16 | What are the expected data volumes (employees, documents, assignments per year)? | Delegation design and performance (NFR-02). | NFR-02 figures |
| OQ-17 | Can a JQC or PWI apply to people outside Production and Quality, and do those people need app access? | Role and department values. | No |
| OQ-18 | Should the matrix show only current employees, or offer a historical "as of date" view for audits? | Scope and complexity. | Current only |
