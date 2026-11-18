# 1.4.0.0: Increment 3, Open Questions (R15)
**Status:** Built, not opened. Includes 1.3.0.0.

## SharePoint prerequisites (do these BEFORE importing)
1. **Create the list `NPI Open Questions`** on the MTC Expansion Planning site. Create each column with exactly this name (internal name), then rename the display name if you want:

   | Column | Type | Notes |
   |---|---|---|
   | Title | (built-in) | The question or action |
   | ProjectID | Single line of text | Required |
   | Gate | Number | 0 decimals, min 1, max 4, required |
   | Owner | Person | People only |
   | DueDate | Date | Date only |
   | QStatus | Choice | `Open`, `Closed`; default `Open` |
   | Resolution | Multiple lines of text | Plain text |
   | GateMoveReason | Multiple lines of text | Plain text |
2. **NPI Activity Log, ActionType column:** add the choices `Question added`, `Question closed` and `Question moved`. If these are missing, the question still saves and you get a warning that the log entry failed.
3. Optional: index ProjectID and QStatus on the new list.

## Changes
- **Open questions (N)** button next to Documents (red when N > 0). It opens a window that:
  - lists Open / All questions for this project
  - lets you add a **New question**: text, gate (buttons), owner (search), optional due date
  - on a selected question, lets you **Close** it with a resolution, **Reopen** it, or **Move** it to another gate (reason required; saved in GateMoveReason and the Activity Log)
- The gate strip shows "· N open questions" per gate.
- The overview gets an **Open Qs** column.
- The gate sign-off block on open questions arrives in 1.5.0.0.

## Tests
1. Create the list, add the choices, import, then open the app.
2. On a project, open the questions window. Add a Gate 1 question with an owner and a due date.
3. The gate strip shows "1 open question" under Gate 1, and the overview Open Qs shows 1.
4. Move it to Gate 2 with a reason. Close it with a resolution. Reopen it.
5. Check that NPI Activity Log has an entry for each step (RequirementID `Q-<id>`).
