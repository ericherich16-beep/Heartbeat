# NPI Tracker 1.2.0.2: Overview and Project details redesign

**Package:** `dist/EricP_NPITrackerIncrement1_1_2_0_2.zip` (same solution `EricP_NPITrackerIncrement1`, same app `ericp_npitracker_i1`)
**Built from:** `EricP_NPITrackerIncrement2a_1_1_0_3.zip` (tenant-tested: imports and opens)
**Status:** Built, not opened

## How it was built (rules carried over from 1.1.0.0 to 1.1.0.3)
- Built from the last package that opened. Only `Src\*.pa.yaml`, plus version and description metadata, changed. The flow JSON, data sources, connection references, templates and themes are byte-for-byte the same.
- No new connectors or data sources. It uses the same four SharePoint lists and the `NPICreateProject` flow. Office 365 Users is not used.
- It uses only control types that opened in 1.1.0.3 (Label, Rectangle, Gallery, Classic Button, Classic Text input). `build.py` rejects any other control type or an unknown property. It also catches YAML quoting errors, unbalanced formulas and references to unknown controls.
- The msapp entry names and order are unchanged. The msapp still loads from YAML (`LoadFromYaml: true`).
- One setting changed: the data row limit went from 500 to 2000, so the overview counts can read all requirement rows.

Rebuild: `python3 -I build.py <1.1.0.3 zip> dist`

## What's in it
**Overview:** Open projects, Upcoming items (due in the next 14 days) and Awaiting review (Done, not reviewed) tiles. Search by project, part or customer. Open, All and Closed filters. Table with a progress bar and "Gate N · %" for the current gate. New Project works as before.

**Project details**
- Header with project ID, customer, part number, revision, QE and type. Back, Project folder and Refresh buttons.
- Gate strip showing % and status for Gates 1–4. Click a gate to view it.
- Documents list with All, Open and Needed for current gate filters, plus an items-remaining count. Reviewed and N/A items are hidden in the filtered views.
- Action panel: status pill, instruction, assignee, due date, PDF area, Notes, and buttons that change with the status:
  - Not started or Draft: **Submit for review** (to Done) and **Save draft**
  - Done: **Mark reviewed** or **Send back** for the QE or QM (the Independent Review rule applies). Anyone else gets **Back to draft**.
  - Reviewed: **Reopen** for the QE or QM
  - N/A: **Restore** for the QE or QM
- Notes are saved to `NPI Activity Log` (Reason column) with each action.
- **View details** shows all row fields, plus Reassign, Due date and N/A with reason for the QE or QM.
- **Activity** shows the log entries for the row.

## Not in this package (and why)
| Item | Reason |
|---|---|
| Add PDF upload (2b) | Needs a new flow data source and a file-picker control. Neither has been proven in the tenant yet (rule 3: test in a small app first). The button is shown but disabled. `varPdfRequired` (App OnStart) is `false` until upload ships. |
| Sign Gate (Increment 4) | NPI Projects has no Gate Signed By or Signed Date columns yet. The button stays disabled. The hint text says when a gate's requirements are met. |
| Open Questions check (Increment 3) | The `NPI Open Questions` list doesn't exist yet. |

## Tenant test list
1. Export the current solution as a backup. Import this zip as an **Update**, and click **Allow** if asked about SharePoint.
2. Open the app from **Solutions**. **It must open.** If it doesn't, stop and note the first error.
3. Overview: check the tile numbers, search, the Open/All/Closed filters, and that the progress bars and "Gate 1 · x%" values look right.
4. Click a project. Check the header, the gate strip, and that the first open Gate 1 item is selected.
5. Try the All, Open and Needed filters. Click Gate 2 in the strip.
6. Run **Save draft** with a note, then **Submit for review**. Check the pill and list update and that Activity shows both entries with the note.
7. As the QE: run **Mark reviewed** on a Done row. On an Independent Review row assigned to you, the button must say "Waiting for review".
8. As the QE: run **Send back**, **Reopen**, and N/A with a reason from View details (only on "If required" rows), then **Restore**.
9. View details: test reassign and setting a due date. Check that the overdue date turns red.
10. As a non-QE user: check that review, N/A, reassign and due-date controls are hidden.
11. Create a new project and check that it appears with 0%.

## 1.2.0.1 changes
- **QE and QM matching:** the app now recognises the QE or QM by email **or** by sign-in name (the SharePoint Claims value), because the two can differ. The same applies to the Independent Review assignee and uploader check.
- **Role badge:** the header shows "You: QE", "You: QM" or "You: Team member".
- **Clearer hints:** when Mark reviewed isn't offered, the panel says why and shows the email you're signed in with. Not started and Draft rows now say to submit first.

## 1.2.0.2 changes
- **Independent Review rule fixed.** Mark reviewed is blocked for the row's assignee, its uploader, **and the person who last submitted it** (taken from the Activity Log). Assignee and uploader now match by email or sign-in name. Before this, a QE could submit and then review their own Independent Review row.
- **Reassign, due date and N/A moved onto the main panel** (QE/QM only):
  - **Reassign** and **Change date** buttons sit next to "Assigned to" and "Due". Each opens an editor in the panel with Save and Cancel.
  - The due date editor has +1 week, +2 weeks and +30 days shortcuts and shows the date you entered back to you.
  - A **Mark N/A** link appears on "If required" rows that are Not started or Draft.
- **View details is now a read-only, two-column grid** of labelled fields (status, gate, assignee, due date, type, level, role, independent review, gate document, file, uploaded by, reviewed by, N/A reason, requirement ID).
- **The panel shows an INDEPENDENT REVIEW or GATE DOCUMENT flag** under the title.
- **Not included:** your hand fix for the percentages in the tenant. See the chat.
