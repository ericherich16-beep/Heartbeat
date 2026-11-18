# SharePoint setup checklist (cumulative)
Site: MTC Expansion Planning. **Create each column with the exact internal name shown, with no spaces.** You can rename the display name afterwards. `schema.yaml` is the source of truth.

## Before 1.4.0.0
- [ ] **New list `NPI Open Questions`:**
  - Title (built-in): the question or action
  - ProjectID: single line of text, required
  - Gate: number, 0 decimals, min 1, max 4, required
  - Owner: person, people only
  - DueDate: date only
  - QStatus: choice `Open` / `Closed`, default `Open`
  - Resolution: multiple lines of plain text
  - GateMoveReason: multiple lines of plain text
- [ ] Optional: index ProjectID and QStatus.
- [ ] **NPI Activity Log → ActionType:** add the choices `Question added`, `Question closed`, `Question moved`.

## Before 1.5.0.0
- [ ] **NPI Projects:** add these columns:
  - Gate1SignedBy, Gate2SignedBy, Gate3SignedBy, Gate4SignedBy: person
  - Gate1SignedDate, Gate2SignedDate, Gate3SignedDate, Gate4SignedDate: date and time
  - CloseDate: date only
  - RetentionUntil: date only
- [ ] **NPI Activity Log → ActionType:** rename `Choice 8` to `Gate signed`.

## Before 1.6.0.0 (and the upload test)
- [ ] **NPIProjectFiles library:** add these columns:
  - ProjectID: text
  - RequirementID: text
  - Gate: number
  - FormNumber: text
  - FormSection: text
  - UploadedBy: person
  - UploadedDate: date and time
- [ ] NPIProjectFiles → Versioning settings: create major versions, and keep all versions if your policy allows.
- [ ] After importing: turn on the **NPIUploadFile** flow (Solutions → Cloud flows).

## Carry-over fixes from before (still open)
- [ ] Gate Requirements: Role filled on all 16 rows; remove "Choice 3" from ReqLevel; fill ApprovedBy; index Gate and SortOrder; DefaultAssignee required.
- [ ] NPI Projects: make PartRevKey indexed and unique.
- [ ] Add an AS9102 template to NPIFormTemplates, if one exists.
- [ ] Delete test solutions A–D, the NPI Upload Test solution (after 1.6.0.0 works), and any `TEST-*` projects, rows and folders.
- [ ] Trigger inputs 7–9 on NPICreateProject: remove them only after checking that no action uses them. **The app still sends them**, so update both together.
