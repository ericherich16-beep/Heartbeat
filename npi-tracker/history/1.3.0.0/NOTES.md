# 1.3.0.0: Increment 5, overview (R5, R6, R7)
**Status:** Built, not opened. **Base:** tenant export 1.2.0.1. Includes everything in 1.2.0.3.

## Changes
- **Filters:** Open / All / Closed / **My tasks** / **Overdue**.
  - **My tasks:** every open requirement row in an open project assigned to you (matched by email or sign-in), soonest due first.
  - **Overdue:** every open row in an open project whose due date has passed, for anyone.
  - Selecting a task opens its project with that row selected and its gate shown.
- **Project table columns:** Project, Customer, Part/Rev, **QE**, Progress (current gate % plus **overall %**), **Next due**, **Overdue** count (red when above 0).
- `varMe` is now set at app start, so My tasks works before you open a project.

## SharePoint prerequisites
None.

## Tests
1. Open the app. The overview shows the new columns.
2. Check a project's overall % against its rows: (Reviewed + N/A) ÷ all rows.
3. Select My tasks. Only your open rows are listed. Click one and the project opens on that row.
4. Select Overdue. Only past-due open rows are listed.
5. Search works in every view.
