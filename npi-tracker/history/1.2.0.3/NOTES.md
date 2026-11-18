# 1.2.0.3: rebase on tenant export
**Status:** Built, not opened. **Base:** `base/tenant_export_1_2_0_1.zip`. The app inside that export is byte-for-byte the 1.2.0.0 app, so the Studio edits weren't saved into the solution. Their effect is rebuilt here from source.

## Changes since the tenant copy
- QE and QM are matched by email **or** sign-in claims (U-number address). The header shows a "You: QE / QM / Team member" badge.
- Percentages are shown as whole numbers (x100) on the Overview and in the gate strip.
- **Independent Review:** the assignee, the uploader and the last submitter can't review the row. Rows without Independent Review allow self-review by the QE or QM.
- **Reassign**, **Change date** (with +1 week, +2 weeks and +30 days shortcuts) and **Mark N/A** are now on the main panel, for the QE or QM.
- View details is a read-only, two-column grid.

## SharePoint prerequisites
None. The lists and columns are unchanged from 1.1.0.3.

## Tests
1. Import as an Update and open the app.
2. Check the badge says You: QE.
3. Check the percentages look right.
4. On a normal row: Submit, then Mark reviewed (self-review is allowed).
5. On an Independent Review row that you submitted: you get "Waiting for review" and the reason.
6. Reassign and Change date from the panel. Activity shows both.
7. Mark N/A on an "If required" row, then Restore.
