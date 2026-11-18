# Phase 2 - Spec

**Goal:** a spec that someone else could build from without asking questions, plus `lists.json`. The input is either the grill summary or a spec/PRD written elsewhere.

## If the user brings their own spec or PRD

1. Check it against every section of the template below.
2. List the gaps as a table: *section / what's missing / your recommended answer*.
3. Ask about the gaps **one at a time**.
4. Don't rewrite parts that are already fine. Add only what's missing.

## Spec template

Write the spec with these headings, in this order:

1. **Summary.** The problem, who it's for, and the outcome, in three sentences.
2. **Out of scope.** A bulleted list.
3. **Roles and permissions.** A table: role × action (view / create / edit / approve / delete / admin). Say how each role is determined.
4. **Data model.** One table per list or library. Every column has these fields:

   | Internal name | Type | Required | Choices / default | Notes |
   |---|---|---|---|---|

   - **Internal name** = display name: a plain identifier with no spaces, for example `DocNumber` (SP-01).
   - **Type** uses SharePoint `TypeAsString`: `Text`, `Note`, `Number`, `Currency`, `DateTime`, `Boolean`, `Choice`, `MultiChoice`, `User`, `UserMulti`, `Lookup` or `URL`.
   - Above each table, say **List** or **Document library** (SP-02).
   - Mark the columns used in filters as **indexed** (APP-09).
   - Prefer plain Text or Number links between lists (`RejectionID` as a Number) to Lookup columns.
5. **Business rules.** Numbered, testable statements: *BR-01 A rejection cannot be Closed while any action is not Done.*
6. **Status logic.** Every status, allowed moves, who can make each move, and the side effects.
7. **Screens.** One row per screen: name (`scrHome`…), the role it's for, its purpose, the main controls, and where it navigates.
8. **Flows.** For each flow: trigger (Power Apps V2), inputs, steps, response. Standard connectors only (FLOW-01). Flows never set list columns; the app does that with `Patch` (FLOW-02).
9. **Acceptance criteria.** For each screen and rule: *Given / When / Then*, using fictional sample data.
10. **Sample data.** Fictional rows for every list, including edge cases: blank optional fields, inactive users, overdue items, and a file added straight in SharePoint with blank metadata (SP-04).
11. **Environment and constraints.** Dataverse available? (PKG-06) The environment variables needed (one for the site, one per list/library). Connector policy.
12. **Decisions and open questions.** D-xx with date. OQ-xx each with your recommended answer.

## `lists.json`

Generate it from the data model. The checker and the build both use it.

```json
{
  "Rejections": {
    "kind": "list",
    "columns": { "Title": "Text", "PartNumber": "Text", "Status": "Choice", "QtyRejected": "Number" }
  },
  "RejectionDocuments": {
    "kind": "library",
    "columns": { "Title": "Text", "RejectionID": "Number", "DocType": "Choice" }
  }
}
```

## Self-check before showing the spec

- [ ] **SP-01:** every column has an internal name with no spaces, no `field_N`, and a type.
- [ ] **SP-02:** every list says list or library.
- [ ] **FLOW-01 / FLOW-02:** no premium or blocked actions, and flows don't set columns.
- [ ] **APP-09:** every filter uses indexed, delegable columns.
- [ ] **APP-10:** no field named `Type`, `Self`, `Parent` or `ThisItem`.
- [ ] **SP-04:** blank-metadata behaviour is defined.
- [ ] Every business rule has at least one acceptance criterion.

## Finish

1. Show the spec and `lists.json`, and ask for approval. Revise until the user approves.
2. Tell the user to save both as files in their OneDrive project folder. Next time, they attach them instead of re-explaining.
3. Output a PROJECT STATE with Phase: Spec approved.
4. Move to Phase 3 - Slice.
