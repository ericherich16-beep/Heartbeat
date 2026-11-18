# Phase 5 - Test

**Goal:** prove the slice works in the user's real environment, fix it until it does, then decide what's next. You can't run anything, so get exact results from the user.

## Test loop for one slice

1. **Verify report.** Go through each FAIL, then each WARN. For each one: what it means in one line, the exact fix, where to make it, and whether it needs a new zip or can be fixed in Studio. Repeat until there are 0 FAIL.
2. **Import.** If the import fails, ask for the exact message and match it:

   | Message contains | Rule | Fix |
   |---|---|---|
   | "manifest file could not be found" | PKG-01 | Use Solutions → Import solution with the solution zip |
   | "Cannot add a Root Component … type 300" | PKG-02 | Add `<CanvasApps>` to Customizations.xml, then repack |
   | "parameter 'item/…'" | FLOW-02 | Remove column parameters from the flow; the app sets them with `Patch` |
   | "Advanced Connector Policy" / "HttpRequest" | FLOW-01 | Remove the blocked action |
   | "flows may not have turned on" | FLOW-07 | Pick the connection, then turn the flow on |

3. **Open the app.** Ask what the user sees:

   | Symptom | Rule |
   |---|---|
   | `ErrOpeningDocument_UnknownError` | PKG-04 (template not from a real app) |
   | Blank screens | APP-03 |
   | Black controls | APP-04 |
   | Lists running sideways | APP-05 |
   | Hundreds of errors | SP-01 / SP-03 / APP-14: Refresh the data sources, then compare the columns to `lists.json` |

4. **App checker.** Ask for each error as **control + property + message**. Fix it by rule ID. If none matches, explain the cause and give the fix.
   - **Small fixes:** give paste-in-Studio steps. Then record the change, so it goes into the source before the next build (RUN-02).
   - **Large fixes:** build a new zip (back to Phase 4 for this slice).
5. **Acceptance test.** The user runs each step and reports pass or fail, with what they saw.
   - **Common runtime causes:** a control wired to the wrong pair (APP-08), a filter hiding blank rows (SP-04), a query SharePoint won't run (APP-09), a flow the app waits on that hangs (FLOW-05), a hidden button with a formula error.
6. **When stuck after two attempts on the same problem:** stop guessing. Design the smallest test that isolates it, for example a tiny test app, a one-screen version, or a demo copy on sample data with no SharePoint.

## When the slice passes

1. Update the slice log: status Done, the version, the test date, and any Studio changes copied back into the source.
2. Output a PROJECT STATE.
3. If slices remain, move to Phase 4 - Build for the next one.

## Completion checklist (after the last slice)

Go through each item with the user:

- [ ] Every slice is Done, and the full set of acceptance criteria passes in one final run on fresh sample data.
- [ ] Each role has been tested with a real account set to that role.
- [ ] Phone, tablet and desktop widths checked (if in scope).
- [ ] Edge cases: blank metadata, inactive users, overdue items, more rows than the delegation limit (if relevant).
- [ ] The final Verify report has 0 FAIL, with `-Docs` pointing at the final README/POST_IMPORT.
- [ ] README and POST_IMPORT match the final app, and an admin guide covers lists, permissions and upgrades.
- [ ] Sample data is removed or marked, and the app is shared with the right people or groups.
- [ ] The source, spec, slice plan and final zip are saved together in the project folder.

Finish with a short release note: what the app does, the version, known limits, and what wasn't tested.
