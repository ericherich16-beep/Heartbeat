# 1.5.0.0: Increment 4, gate sign-off (R16 to R19)
**Status:** Built, not opened. Includes 1.4.0.0, so do the 1.4.0.0 SharePoint steps first.

## SharePoint prerequisites (BEFORE importing)
1. **NPI Projects:** add these columns, using these exact internal names:

   | Column | Type |
   |---|---|
   | Gate1SignedBy, Gate2SignedBy, Gate3SignedBy, Gate4SignedBy | Person (people only) |
   | Gate1SignedDate, Gate2SignedDate, Gate3SignedDate, Gate4SignedDate | Date and time (include time) |
   | CloseDate | Date only |
   | RetentionUntil | Date only |
2. **NPI Activity Log, ActionType:** rename the choice `Choice 8` to **`Gate signed`**.
3. **Existing projects:** the current gate is now worked out from the signed dates, not the CurrentGate column. Projects with no signatures start at Gate 1. The app still writes CurrentGate when a gate is signed, for SharePoint views.

## Changes
- The **Sign Gate N** button is enabled only when all of these are true (spec 4.6):
  - every Gate N row is Reviewed or N/A
  - no open question is tagged Gate N or earlier
  - every Gate N row marked **IsGateDoc** has a linked file (Gate 4 "Final signoff document", decision N2; this needs upload from 1.6.0.0)
  - you are the project QE or the QM
  - the gate isn't already signed. Gates are signed in order.
- **Two-step confirm:** the first click shows "Confirm: sign Gate N" and Cancel.
- **Signing records** GateNSignedBy (you) and GateNSignedDate (now), and writes an Activity Log entry ("Gate signed").
- **Gate 4** also sets ProjectStatus = Closed, CloseDate = today, and RetentionUntil = today + 30 years. The retention label itself isn't enforced (spec non-goal).
- **Blocked message in plain language**, for example: "Gate 2 blocked: 3 requirements are not Reviewed or N/A; 1 open question at this gate or earlier."
- **Signed gates are locked.** Status buttons, Reassign, Change date and Mark N/A are disabled on their rows.
- The **gate strip** shows "Signed Nov 20 · Name" for each signed gate.
- The **overview** current gate also comes from the signed dates.

## Tests
1. Add the columns, rename the choice, import, then open the app.
2. On a test project, Review or N/A every Gate 1 row. Sign Gate 1 is enabled once there are no open Gate 1 questions.
3. Add an open Gate 1 question. Sign is blocked and the message says why. Close the question.
4. Sign Gate 1 (two clicks). Check the gate strip, the NPI Projects columns, the Activity Log, and that Gate 1 rows are locked.
5. As a non-QE user: Sign stays disabled with "Only the project QE or the QM can sign it".
6. Gate 4 needs the gate document file, so test it after 1.6.0.0 upload. To test early, paste any URL into FileLink on the Gate 4 IsGateDoc row in SharePoint.
