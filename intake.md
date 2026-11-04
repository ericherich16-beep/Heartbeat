# intake.md — JQC/PWI Management

> Intake summary for a Power Apps solution to be built with Claude Code.
> Pair this file with `CLAUDE.md` (the full build brief). If the two conflict, `CLAUDE.md` wins.
> **No confidential data:** all names, documents, URLs and IDs used during the build must be fictional placeholders.

---

## App name
JQC/PWI Management

## Problem (what's painful today)
- JQCs (Job Qualification Checklists) and PWIs (Process Work Instructions) are stored in Teams/SharePoint folders that nobody uses.
- There is no shared matrix showing who needs which training.
- Managers can't easily see or manage their team's training status.
- When a PWI is revised, there is no reliable way to make sure everyone signs off on the new revision.

## Users & roles
| Role | Who | What they can do |
|---|---|---|
| **Manager/Supervisor** | Production and quality managers/supervisors | Everything a Technician can do, plus:<br>• add and edit employees<br>• add and revise JQCs/PWIs<br>• designate trainers<br>• assign JQCs/PWIs to employees<br>• sign off JQCs |
| **Technician** | Production and quality technicians | • Sign off on their own PWIs<br>• Upload training logs<br>• View or download documents<br>• See their pending and completed items |
| **Viewer** | Anyone needing read-only access | View the matrix, the cross-training view, documents and sign-off status |

**Trainers** aren't an app role. Managers designate one or more trainers on each JQC and PWI.

## Current process
1. An Excel matrix tracks who is signed off on what.
2. Signed JQCs are saved to SharePoint/Teams folders.
3. PWI sign-offs (training logs) are saved to separate SharePoint/Teams folders.
4. The matrix is updated by hand, and often isn't kept current.

## Target process (with the app)
1. A manager adds a JQC (template) or PWI (work instruction) to the app and designates its trainers.
2. The manager assigns JQCs/PWIs to one or more employees.
3. The employee sees the assignment as pending and can open or download the document in the app.
4. **PWI:** the employee uploads the training log and signs off themselves.
5. **JQC:** the manager/supervisor uploads the filled-out, signed JQC and confirms the employee is qualified.
6. **PWI revision:**
   - A manager uploads the new revision with change notes.
   - **Every currently assigned employee must sign off again** on the new revision.
   - Employees assigned in the future sign off on whatever revision is current at that time.
7. Everyone can see a common matrix of who can do what, plus a cross-training view showing coverage gaps.

## Data
| Item | Type | Purpose |
|---|---|---|
| `JP_Employees` | SharePoint list | Employees: role, job title, department, shift, supervisor, active flag |
| `JP_Documents` | Document library | JQC templates and PWIs: number, title, current revision, change notes, trainers, status |
| `JP_Assignments` | SharePoint list | One row per employee per document revision: status, due date, sign-off details |
| `JP_SignoffRecords` | Document library | Uploaded evidence: signed JQCs and PWI training logs |
| `JP_Settings` | SharePoint list | Cross-training target (default 2 per task) and re-sign due days (default 14) |

- All of these are new lists and libraries. Existing Excel and folder data is not migrated in this phase.
- Site and list locations are set through solution environment variables. Nothing is hard-coded.

## Business rules
**Permissions and required fields**
- Required fields are enforced before saving.
- Only Manager/Supervisor can:
  - add or edit employees
  - add or revise documents
  - designate trainers
  - assign JQCs/PWIs
- A document can't be assigned until it has at least one trainer.
- No duplicate active assignments: one current assignment per employee per document.

**Sign-offs**
- **PWI sign-off:** the assigned employee (or a manager) signs off. A training log upload is required before the Sign Off button turns on.
- **JQC sign-off:** a manager/supervisor only. They upload the signed JQC and confirm the employee is qualified. A manager can't sign off their own JQC.
- **Revisions:**
  - A new PWI revision supersedes existing sign-offs and creates a re-sign item for every active assigned employee.
  - No one can sign off on an outdated revision.
  - A new JQC revision doesn't force anyone to re-sign.
- **Qualified** means signed off on the **current** revision.

**Records and uploads**
- Nothing is deleted. Assignments are marked Removed or Superseded, documents are marked Obsolete and employees are marked Inactive. Sign-off history is kept.
- Allowed upload types are PDF, DOCX, XLSX, JPG and PNG, up to 25 MB.

## Outputs
None required. There are no Teams posts, emails or Hour by Hour rows. Pending and re-sign items show in the app only.

## Constraints
- Standard connectors only: SharePoint, Office 365 Users, and Power Automate with the Power Apps trigger. No premium connectors and no Dataverse.
- Must work on computer, tablet and phone (responsive layout).
- Must be delivered as an importable Power Apps solution, with environment variables for all site and list references.
- No confidential company data anywhere in the build. Use fictional sample data only.

## Out of scope
- Email, Teams or other notifications
- Premium connectors, Dataverse and PCF/code components
- Migrating existing Excel matrix and folder data
- Automatic re-sign on JQC revisions

## Success criteria
- It's easy to see who still needs what signed off, including re-signs after a PWI revision.
- It's easy to add JQC/PWI documents and review sign-offs.
- The cross-training view shows tasks below target coverage, single points of failure and gaps by shift.
- The matrix reflects current-revision sign-offs only.

## Open items
- [ ] Confirm the default re-sign due period (14 days).
- [ ] Confirm the cross-training target (2 qualified per task).
- [ ] Confirm that the in-app sign-off (logged-in user plus timestamp) meets quality record requirements.
- [ ] Map placeholder SharePoint groups (Managers, Technicians, Viewers) to real groups at deployment.
