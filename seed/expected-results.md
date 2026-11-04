# Seed data — expected results

All data in `/seed/` is **fictional** (`contoso.com` is Microsoft's fictional domain).
Use these tables to check the app after you import the seed data with `/provisioning/Import-SeedData.ps1`. They cover SPEC.md acceptance criteria AC-MTX-6 and AC-XT-6.

- Dates in the seed files are **relative to the import day**, so "overdue" stays overdue whenever you import.
- All results assume the default settings: `MinQualifiedPerTask = 2` and `ResignDueDays = 14`.
- Status names follow SPEC.md BR-41.

## Files

| File | Contents |
|---|---|
| `employees.csv` | 9 employees: 2 managers, 6 technicians (Tech F is **inactive**), 1 viewer |
| `documents.csv` | 7 documents. **PWI-DEMO-001** and **JQC-DEMO-100** were revised from Rev A to Rev B. **JQC-DEMO-102** has no trainer. **PWI-DEMO-004** is Obsolete. |
| `assignments.csv` | 29 assignment rows (K01–K29), including superseded history rows and one removed row |
| `settings.csv` | The single settings row |
| `user-map.example.csv` | Template that maps seed emails to real **test** accounts. Copy it to `user-map.csv`, which is git-ignored and must not be committed. |

### How the CSV columns work
- `TrainerEmails` holds several trainers separated by semicolons (`;`).
- `PreviousRevision`: when set, the import uploads that revision first, then the current revision over it in place. This puts Rev A in the library's version history.
- `*DaysAgo` and `DueInDays` are day offsets from the import date. A negative `DueInDays` means the due date is already past.
- `PreviousKey` links a Revision Change row to the row it replaced. It becomes `PreviousAssignmentID` on import.
- Every row with `SignedOffByEmail` gets a placeholder sign-off PDF in `JP_SignoffRecords`, and its `SignoffFileID` is set.

## Scenarios covered

| Scenario | Where |
|---|---|
| PWI revision: everyone re-signs (CLAUDE §7.8) | PWI-DEMO-001, rows K01–K08 |
| PWI revision: someone already re-signed on the new rev | Tech A, K02 |
| PWI revision: inactive employee is skipped | Tech F, K09 (left on Rev A, excluded from views) |
| Assigned after revision gets the current rev | Tech E, K10 (Rev B, New Assignment) |
| JQC revision: everyone back to Needs Training (D-01) | JQC-DEMO-100, rows K18–K23 |
| JQC revision: one person put into training, one already re-qualified | Tech B, K21 (In Training). Tech C, K23 (Signed Off by Supervisor Two) |
| Manager's own JQC (they can't put themselves into training or sign off) | Supervisor Two, K24. Manager One, K27 |
| Overdue | K14 (PWI), K28 (JQC) |
| Removed assignment | K17 |
| Document with no trainer (can't be assigned) | JQC-DEMO-102 |
| Obsolete document excluded | PWI-DEMO-004, K29 |
| Single point of failure | PWI-DEMO-001 (Tech A), JQC-DEMO-100 (Tech C) |
| Shift with no coverage | Days shift: 0 qualified on every task |
| Inactive employee | Tech F |
| Viewer | Viewer One |

## 1. Training matrix (`scrMatrix`)

The rows are active Technicians and Managers (7). The columns are Active documents (6). Tech F, Viewer One and PWI-DEMO-004 must **not** appear.

| Employee | Shift | PWI-DEMO-001 | PWI-DEMO-002 | PWI-DEMO-003 | JQC-DEMO-100 | JQC-DEMO-101 | JQC-DEMO-102 |
|---|---|---|---|---|---|---|---|
| Manager One | Days | Re-Sign Required | Not Assigned | Not Assigned | Not Assigned | In Training | Not Assigned |
| Supervisor Two | Days | Not Assigned | Not Assigned | Not Assigned | Needs Training ¹ | Not Assigned | Not Assigned |
| Tech A | 1st | **Signed Off** | Not Assigned | Not Assigned ² | Needs Training ¹ ³ | Not Assigned | Not Assigned |
| Tech B | 1st | Re-Sign Required | **Signed Off** | Not Assigned | In Training ³ | Not Assigned | Not Assigned |
| Tech C | 2nd | Re-Sign Required ⁴ | **Signed Off** | Not Assigned | **Signed Off** | Overdue | Not Assigned |
| Tech D | 2nd | Not Assigned | **Signed Off** | **Signed Off** | Not Assigned | **Signed Off** | Not Assigned |
| Tech E | 3rd | Pending ⁵ | Overdue | **Signed Off** | Not Assigned | **Signed Off** | Not Assigned |

1. Supervisor Two's row is a New Assignment, so it has no badge. Tech A's row is a Revision Change and shows the "New Revision" badge.
2. K17 was Removed, so there is no current row.
3. Tech A and Tech B were Signed Off on JQC-DEMO-100 Rev A. Under D-01, that no longer counts.
4. K06 has `Status = In Training`, but a PWI Revision Change row displays as Re-Sign Required.
5. Assigned after the revision, on Rev B, with no due date.

**"Re-Sign Required only" filter:** shows Manager One, Tech B and Tech C on PWI-DEMO-001.

## 2. Cross-training (`scrCrossTraining`)

Target = 2. **Below target: 3 tasks** (Coverage Gaps tile = 3).

| Task | Qualified | Target status | Who is qualified | Pending after revision (BR-48) |
|---|---:|---|---|---:|
| JQC-DEMO-102 | 0 | **No coverage** (below target) | — | 0 |
| PWI-DEMO-001 | 1 | **Below target, single point of failure** | Tech A | 3 (Tech B, Tech C, Manager One) |
| JQC-DEMO-100 | 1 | **Below target, single point of failure** | Tech C | 2 (Tech A, Tech B) |
| PWI-DEMO-002 | 3 | OK | Tech B, Tech C, Tech D | 0 |
| PWI-DEMO-003 | 2 | OK | Tech D, Tech E | 0 |
| JQC-DEMO-101 | 2 | OK | Tech D, Tech E | 0 |

### Coverage by shift

| Task | 1st | 2nd | 3rd | Days |
|---|---:|---:|---:|---:|
| PWI-DEMO-001 | 1 | **0** | **0** | **0** |
| PWI-DEMO-002 | 1 | 2 | **0** | **0** |
| PWI-DEMO-003 | **0** | 1 | 1 | **0** |
| JQC-DEMO-100 | **0** | 1 | **0** | **0** |
| JQC-DEMO-101 | **0** | 1 | 1 | **0** |
| JQC-DEMO-102 | **0** | **0** | **0** | **0** |

### Employee breadth (ascending)

| Employee | Qualifications |
|---|---:|
| Manager One | 0 |
| Supervisor Two | 0 |
| Tech A | 1 |
| Tech B | 1 |
| Tech C | 2 |
| Tech E | 2 |
| Tech D | 3 |

## 3. Library counts (`scrPWILibrary` / `scrJQCLibrary`)

- **Y** = current rows (`IsCurrent = Yes`, not Removed) for active employees.
- **X** = qualified (BR-40).
- **Needs Training** = JQC current rows with `Status = Assigned`, including overdue ones.

| Document | X of Y on current rev | Needs Training | Trainers |
|---|---|---:|---|
| PWI-DEMO-001 (Rev B) | 1 of 5 | — | Tech A, Manager One |
| PWI-DEMO-002 (Rev A) | 3 of 4 | — | Tech B, Manager One |
| PWI-DEMO-003 (Rev A) | 2 of 2 | — | Tech D, Supervisor Two |
| JQC-DEMO-100 (Rev B) | 1 of 4 | 2 (Tech A, Supervisor Two) | Manager One |
| JQC-DEMO-101 (Rev A) | 2 of 4 | 1 (Tech C, overdue) | Supervisor Two |
| JQC-DEMO-102 (Rev A) | 0 of 0 | 0 | *none: "No trainer — can't assign"* |
| PWI-DEMO-004 (Obsolete) | shown only when the Status filter includes Obsolete | — | — |

## 4. Home tiles (`scrHome`)

My Pending and My Signed Off count only current rows on Active documents.

| Signed in as | My Pending | of which Re-Sign Required | My Signed Off | Team Pending | Team JQCs Needing Training |
|---|---:|---:|---:|---:|---:|
| Manager One | 2 | 1 | 0 | 6 ⁶ | 3 ⁶ |
| Supervisor Two | 1 | 0 | 0 | 2 ⁷ | 0 |
| Tech A | 1 | 0 | 1 | — | — |
| Tech B | 2 | 1 | 1 | — | — |
| Tech C | 2 | 1 | 2 | — | — |
| Tech D | 0 | 0 | 3 | — | — |
| Tech E | 2 | 0 | 2 | — | — |
| Viewer One | — | — | — | — | — |

6. Manager One's direct reports are Supervisor Two, Tech A, Tech B, Tech C (Tech F is inactive). Their pending rows are K24, K19, K04, K21, K06 and K28. The JQCs needing training are K24, K19 and K28.
7. Supervisor Two's direct reports are Tech D and Tech E. Their pending rows are K10 and K14.

All four Coverage Gaps tiles show **3**.

## 5. Sign-off Review (`scrSignoffReview`)

| Section | Rows |
|---|---|
| Recently signed off (last 7 days) | K23 Tech C JQC-DEMO-100 Rev B (1 day ago). K02 Tech A PWI-DEMO-001 Rev B (2 days ago). |
| JQCs Needing Training | K19 Tech A JQC-DEMO-100 (New Revision). K24 Supervisor Two JQC-DEMO-100. K28 Tech C JQC-DEMO-101 (overdue). |
| JQCs In Training | K21 Tech B JQC-DEMO-100. K27 Manager One JQC-DEMO-101. |
| PWI Re-Sign Required | K04 Tech B. K06 Tech C. K08 Manager One. All on PWI-DEMO-001. |
| Overdue | K14 Tech E PWI-DEMO-002 (3 days). K28 Tech C JQC-DEMO-101 (10 days). |

## 6. Permission checks

| Check | Expected |
|---|---|
| Supervisor Two opens K24 (own JQC) | No Put Into Training, no sign-off controls |
| Manager One opens K24 | Put Into Training available |
| Manager One opens K27 (own JQC) | No sign-off controls |
| Supervisor Two opens K27 | Can sign off (row is In Training) |
| Tech A opens K19 | Shows "Needs Training", with no controls |
| Tech B opens K04 | Upload Training Log, then Sign Off |
| Tech B opens Tech C's K06 by deep link | "You can only view your own items." |
| Any manager tries to assign JQC-DEMO-102 | Blocked: no trainer |
| Viewer One | Read-only matrix, cross-training, libraries, PWI Status and Sign-off Review. Can open all sign-off files. |
| Sign in as an account not in `JP_Employees` | Viewer access |

## 7. Revision tests to run by hand

| Test | Expected |
|---|---|
| Upload PWI-DEMO-002 Rev B | Confirmation says **4** employees. K11–K14 become IsCurrent = No; K11–K13 become Superseded and K14 stays Assigned. 4 new Re-Sign rows are created, due today + 14. Qualified count drops to 0. |
| Upload JQC-DEMO-101 Rev B | Confirmation says **4** employees ("back to Needs Training"). 4 new Needs Training rows are created. K25 and K26 become Superseded. Qualified drops to 0, and the task becomes No coverage. |
| Assign PWI-DEMO-001 to Tech D | 1 row is created on **Rev B**. |
| Assign PWI-DEMO-001 to Tech A again | Skipped: already assigned. |
