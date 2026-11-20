# NPI Tracker: overnight build handoff (2026-11-18)

**Start here.** Every package below is **Built, not opened**. None has been imported into the tenant. Import them **in order**, and open the app after each one before testing (working rule 2). Each folder in `history/<version>/` holds the zip, a `NOTES.md` (SharePoint steps first, then tests) and the generated `src/` YAML for that version.

## Packages, in import order

| # | Package | Increment | SharePoint work before import | Risk |
|---|---|---|---|---|
| 1 | `history/1.2.0.3/` | Rebase on your export, plus the Independent Review fix, inline reassign/due date/N/A, details grid and % fix | none | Low. Same controls and data sources as 1.2.0.0 |
| 2 | `history/1.3.0.0/` | 5: My tasks, Overdue, QE / overall % / next due / overdue columns | none | Low. App only |
| 3 | `history/1.4.0.0/` | 3: Open Questions (F-Q-08) | new list **NPI Open Questions**, plus 3 ActionType choices | Medium. First new list |
| 4 | `history/1.5.0.0/` | 4: gate sign-off, Gate 4 close, retention | 10 new columns on **NPI Projects**; rename "Choice 8" to "Gate signed" | Medium. New columns |
| 5a | `history/uploadtest/` | Test for 2b: one-screen app plus the NPIUploadFile flow | 7 columns on **NPIProjectFiles** (optional for the test) | **Unproven**: file picker type and new flow |
| 5b | `history/1.6.0.0/` | 2b: upload / replace / remove | NPIProjectFiles columns; versioning on | Same as 5a. Import only after 5a works |

**If a package won't open:** go back to the previous one and send me the first error. Packages 1–4 don't use the file picker or the new flow. If the picker type is wrong, 5a fails on its own without touching the main app.

Cumulative SharePoint steps are in `SETUP_CHECKLIST.md`.

## Spec coverage after 1.6.0.0

| ID | Requirement | Where | Status |
|---|---|---|---|
| R1, R2, R4 | Create project, duplicate block, revision link | Increment 1 flow | Tenant-tested |
| R3 | Default assignee by role | Increment 1 flow | Built. Confirm Role on all 16 Gate Requirements rows |
| R5 | Project list: gate bar, % done, open OFQ, overdue, QE, next due | 1.3.0.0 / 1.4.0.0 | Built, not opened |
| R6 | Filters All / My Tasks / Overdue / Closed, plus search | 1.3.0.0 | Built, not opened |
| R7 | % done = (Reviewed + N/A) ÷ total | 1.2.0.3 (per gate), 1.3.0.0 (overall) | Built, not opened |
| R8 | Project Detail with gate bar and gate cards | 1.2.0.x | Built. 1.2.0.0 opened in the tenant |
| R9 | QE reassigns and sets due dates | 1.2.0.3 (main panel) | Built, not opened |
| R10 | Upload from the row, stamped, real uploader | 1.6.0.0 | Built, not opened (unproven pieces) |
| R11 | Re-upload = new version | 1.6.0.0 (Replace uses UpdateFile) | Built, not opened. Needs versioning on |
| R12 | Status flow with rework | 1.2.0.x | Built. 1.2.0.0 opened |
| R13 | N/A only on "If required" rows, with reason | 1.2.0.3 | Built, not opened |
| R14 | Independent Review: no self-review | 1.2.0.3 (assignee, uploader, submitter) | Built, not opened |
| R15 | F-Q-08 items with gate, moves logged | 1.4.0.0 | Built, not opened |
| R16–R19 | Sign-off rules, blocked messages, order, Gate 4 close and retention | 1.5.0.0 | Built, not opened |
| R20–R21 | Config change control; applies to new projects only | `INCREMENT6_CONFIG_CONTROL.md` | SharePoint configuration. R21 is already true by design (rows are copied at creation) |
| R22 | Library permissions and versioning | Decision N1 | Not built. Versioning check is in the 1.6.0.0 notes |

**Decisions applied:** N1–N3, U4 (a new file on Reviewed goes back to Done, and uploads close at sign-off), U5 (self-service fixes, logged; Remove goes to `_Removed`), everyone can upload/replace/remove, no forced naming (only the requirement-ID prefix on duplicates), self-review allowed except on Independent Review rows.

**Spec non-goals still not built:** re-entering form content, in-app signing, document sets and content types, direct upload, config approval workflow, enforced retention label, swimlane graphic, Spec Tools sync, scan or signature checking, notifications.

## Things I could not verify here
1. **`Attachments@2.3.0`.** The YAML type name for the classic file picker comes from a third-party source and was never opened in your tenant. Package 5a exists to test it.
2. **New flow wiring.** Studio may want NPIUploadFile removed and re-added in the app (Power Automate pane). The steps are in the 1.6.0.0 notes.
3. **`JSON(file, IncludeBinaryData)` for PDFs from the picker.** This is a widely used pattern, but it's untested here. Package 5a tests it.
4. **SharePoint connector behaviour:** UpdateFile keeping version history, and MoveFileAsync with nameConflictBehavior 2 (rename). If remove fails with a name conflict, the flow's run history shows it.
5. **Power Fx semantics.** I checked YAML safety, brackets, data source names, column names on Patch/varRow/varProject/varQ, control references and control types/properties. I can't run Studio's type checker here, so a formula error may still show in Studio. Errors like that don't stop the app opening. Note the control and the message and I'll fix it.

## Your Studio edits
Your export (`base/tenant_export_1_2_0_1.zip`) contained the 1.2.0.0 app unchanged, so the Claims and percentage edits weren't saved into the solution. Both are rebuilt in source. **After each import, export the solution and send it back.** Future builds start from your latest export.

## How to rebuild
```
cd npi-tracker
python3 -I build.py releases/<version>.yaml      # e.g. releases/1.6.0.0.yaml
python3 -I build_uploadtest.py
```
- Sources: `src/` (screens; `*.template.yaml` has placeholders filled in by `build.py`), `schema.yaml` (SharePoint lists and columns, with `since` versions), `flows/NPIUploadFile/`, `releases/*.yaml`.
- Older versions: check out the commit for that version. Its zip is also kept in `history/`.

## Tenant results (2026-11-18 morning)
- 1.6.0.0 **opened**. `Attachments@2.3.0` is confirmed working in the tenant.
- Upload failed with no flow run: the app→flow binding (guessed workflowName) doesn't resolve. Fix: in Studio, remove and re-add NPIUploadFile in the Power Automate pane. **Next build must start from the user's export taken after this fix**, so the real binding is kept.
- Activity gallery "Detail isn't recognized": source now binds galActivity directly to NPI Activity Log (hand fix given).
- Source change: the upload/remove failure message now includes FirstError.Message.
- 2026-11-20: JSON(..., IncludeBinaryData) sends only an appres://blobmanager reference for PDFs, even through an Image control. NPIUploadFile now takes an **optional File input** (`file`), and the app passes `{file: {contentBytes: f.Value, name: f.Name}}` as the last argument. My WADL generator only writes text inputs, so **1.6.0.1 must be built from a tenant export taken after the flow was re-added in Studio**. The build then keeps the tenant's data source definition for the flow.
