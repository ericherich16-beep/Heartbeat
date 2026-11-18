# Phase 3 - Slice

**Goal:** an approved plan of thin **vertical** slices. Each slice delivers one user-visible behaviour end to end, and the user can import and test it on its own. This follows the tracer-bullet approach: the first slice goes through every layer, so problems show up early and cheaply.

## If the spec already has slices

1. Check each slice against the rules below.
2. Keep the user's order. Only propose changes where a slice breaks a rule, for example a horizontal slice, or a missing tracer bullet.

## Rules

1. **Slice 1 is the tracer bullet (SLICE-02).** It contains:
   - the solution with its environment variables
   - **one** list from `lists.json`
   - **one** screen that shows the list and adds a record
   - the flow too, if the app has one, even if it only does the simplest step

   It proves the packaging works (import, data connection, theme, screen size and flow link) before any feature work.
2. **Vertical, not horizontal (SLICE-03).** Each slice touches whatever layers it needs: list columns, screen controls, formulas, flow steps and post-import steps.
   - **Never:** "all lists", "all screens" or "all formulas".
3. **Small.** Aim for one sitting to build, and under 30 minutes for the user to import and test. Split anything bigger.
4. **Each slice must be demonstrable:** the user can see it working in the app.
5. **Order by risk and dependency.** Riskiest first: file uploads, flows, roles. Cosmetic polish comes last.
6. **Additive columns only (SLICE-05).** A slice can add columns but never rename or retype columns from earlier slices.

**Typical order:**
1. Tracer: one list + browse + add.
2. View and edit a record.
3. Status rules and validation.
4. Second list + parent–child link.
5. File upload / flow.
6. Roles and permissions.
7. Dashboard / reports.
8. Polish and phone layout.

## Slice plan format

Write a table, then a section per slice:

| # | Slice | User can now… | Lists / columns added | Screens / controls | Flows | Risk |
|---|---|---|---|---|---|---|

For each slice:
- **Covers:** the business rules and acceptance criteria from the spec (BR-xx, AC-xx).
- **SharePoint changes:** the exact columns to add (internal name, type, choices).
- **Acceptance test:** numbered steps with fictional data, and the expected result for each step.
- **Done when:** the Verify report has 0 FAIL, the import succeeds, App checker shows 0 errors, and the acceptance test passes.

**Durable decisions:** above the table, list the decisions every slice must respect: app name, publisher prefix, environment variable names, list names, colour theme and naming prefixes (`scr`, `con`, `gal`, `btn`, `lbl`, `txt`, `drp`, `gbl`, `loc`, `col`).

## Finish

1. Show the plan and ask for approval. Revise until the user approves.
2. Tell the user to save it as `<App> - Slice Plan` in their OneDrive project folder.
3. Output a PROJECT STATE with Phase: Slicing approved, Current slice: 1.
4. Move to Phase 4 - Build.
