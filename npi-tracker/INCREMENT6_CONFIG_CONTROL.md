# Increment 6: config change control (R20, R21)
No app package is needed. The spec's config approval workflow is a non-goal, so change control lives in the **Gate Requirements** list.

## R21: changes apply to new projects only
This is already true. `NPICreateProject` copies the active Gate Requirements rows into Project Requirements when a project is created. Editing Gate Requirements later never changes an existing project's rows.

## R20: controlled edits (SharePoint settings)
1. **Versioning:** Gate Requirements → List settings → Versioning settings → **Create a version each time you edit an item: Yes**, and keep all versions. This gives a full before/after history for every config row.
2. **Required columns:** make **ChangeReason** (multiple lines of text) and **ApprovedBy** (person) required. Every edit then has to say why and who approved it. Fill in the existing rows first (ApprovedBy is currently blank).
3. **Who can edit:** break permission inheritance on Gate Requirements. Give the **QM (Config Admin)** Edit, and everyone else Read. Decision N1 keeps the other lists as they are.
4. **No deleting required rows:** set Active (Y/N) to No to retire a row instead of deleting it (spec user story: "nobody can remove a required signoff"). Removing Delete from the QM's permission level on this list, using a custom "Edit without delete" level, enforces this.
5. **Optional view:** a "Change history" view sorted by Modified, showing ChangeReason, ApprovedBy and Modified By.

## Revision test run (end-to-end check after 1.6.0.0)
1. As QM: edit one Gate Requirements row, for example change a Role, filling in ChangeReason and ApprovedBy. Confirm a new version appears in Version history.
2. Create a **Revision** project for an existing part (PreviousProjectId = the old project's numeric ID). Confirm:
   - the new project links to the previous one (R4)
   - its rows reflect the edited config
   - the **old** project's rows are unchanged (R21)
3. Run the new project through Gate 1:
   - upload a PDF on each row (1.6.0.0)
   - Submit, then Review (on Independent Review rows, use a second person)
   - add and close an open question
   - Sign Gate 1
4. Check that the Activity Log has every step and that the Gate 1 rows are locked.
5. Optional: carry on to Gate 4 to check that the project closes and RetentionUntil = CloseDate + 30 years.
