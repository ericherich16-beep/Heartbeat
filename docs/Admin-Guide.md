# JQC/PWI Management — Admin Guide

For the person who deploys and looks after the app. Everything in this guide uses **fictional** examples (`contoso.com`, `PWI-DEMO-001`, `Tech A`). Replace them with your own values in your tenant only. Never put real values in the repository.

## 1. What gets deployed

| Piece | Where it lives | Notes |
|---|---|---|
| 5 SharePoint lists and libraries | One SharePoint site you choose | `JP_Employees`, `JP_Documents`, `JP_Assignments`, `JP_SignoffRecords`, `JP_Settings` |
| Solution **JQC/PWI Management** | A Power Platform environment | Contains the canvas app, the flow **JQCPWI - Upload File**, the SharePoint connection reference and 6 environment variables |

- **Connectors:** SharePoint, Office 365 Users and Power Automate (Power Apps V2 trigger), all **standard**. No premium connectors and no Dataverse tables.
- **Dataverse:** the environment must still have Dataverse turned on, because solutions are stored there.
- **Outputs:** the app sends no emails or Teams posts. Pending and re-sign items appear in the app only.

## 2. Before you start

- [ ] A Power Platform environment **with Dataverse** (most are, including the default one).
- [ ] You have **Environment Maker** (or System Customizer) in that environment.
- [ ] You're a **Site Owner** of the SharePoint site.
- [ ] Every app user has a Microsoft 365 account and a licence that covers standard connectors.
- [ ] The latest solution zip from `solution/dist/` (for example `JQCPWIManagement_1_0_0_0_unmanaged.zip`).

> **Data policy note:** in this tenant, the data policy "Advanced Connector Policy" blocks the SharePoint action *Send an HTTP request to SharePoint*. Nothing in the main solution uses it. That's why the lists are created by hand (step 3.1) rather than by the optional setup flow.

## 3. Deploy (first time)

### 3.1 Create the lists
Follow **`provisioning/Manual-Setup.md`**, a checklist that takes about 30–40 minutes. Type every column name exactly as shown. The app relies on those names.

Alternatives, if your tenant allows them:
- `provisioning/Create-Lists.ps1`: PowerShell 7 with PnP.PowerShell and a PnP app registration.
- The setup solution `JQCPWISetup_*.zip`: this needs the HTTP action, which is blocked here.

### 3.2 Set up permissions (CLAUDE.md Section 9)
Create three SharePoint groups, then **stop inheriting permissions** on each list and grant:

| Group (placeholder name, `TODO:` map to your groups) | JP_Employees | JP_Documents | JP_Settings | JP_Assignments | JP_SignoffRecords |
|---|---|---|---|---|---|
| JQCPWI Managers | Contribute | Contribute | Contribute | Contribute | Contribute |
| JQCPWI Technicians | Read | Read | Read | Contribute | Contribute |
| JQCPWI Viewers | Read | Read | Read | Read | Read |

**Known limitation (SPEC.md OQ-03):** technicians have Contribute on `JP_Assignments` and `JP_SignoffRecords`, so they could edit rows directly in SharePoint, outside the app's rules. If your quality system needs stronger protection, raise it before go-live. One option is to move sign-off writes into a flow that runs under a service account.

### 3.3 Import the solution
1. **make.powerapps.com** → choose the environment (top right) → **Solutions** → **Import solution** → **Browse** → pick the zip → **Next**.
2. **Connections:** pick or create a **SharePoint** connection for *JQC/PWI - SharePoint*, and connections for SharePoint and Office 365 Users if asked.
3. **Environment variables:** pick the site, then each list:

| Variable | Pick |
|---|---|
| JQC/PWI - SharePoint site | Your site |
| JQC/PWI - JP_Employees list | JP_Employees |
| JQC/PWI - JP_Documents library | JP_Documents |
| JQC/PWI - JP_Assignments list | JP_Assignments |
| JQC/PWI - JP_SignoffRecords library | JP_SignoffRecords |
| JQC/PWI - JP_Settings list | JP_Settings |

4. **Import**, and wait for the success message.

More detail: `solution/env-vars.md`.

### 3.4 After import
1. Open the solution → **Cloud flows** → **JQCPWI - Upload File** → make sure it's **On**. If it won't turn on, the message says why, for example a data policy.
2. Open the app → **Edit** (Studio).
   - **Data** pane: if any list shows a warning, use **⋯ → Refresh**. The likeliest is `JP_Documents`, because of its multi-person *Trainers* column (SPEC.md A-29).
   - Fix any red formula errors, or send screenshots to the developer.
   - **Save** → **Publish**.
3. **Share** the app with your users or groups (**Share** → add people). They don't need edit rights.
   - The flow runs with each user's own SharePoint connection. Power Apps asks users to allow it the first time they upload.

### 3.5 First data
1. In `JP_Employees`, add **yourself** with *AppRole* = **Manager/Supervisor**, *Active* = Yes, and *Email* exactly as you sign in, in lowercase.
2. Open the app. Your name and role appear in the navigation.
3. From the app, add the other employees (**Employees → + Add employee**).
4. Check the single settings row in `JP_Settings`:
   - *MinQualifiedPerTask* = 2 and *ResignDueDays* = 14.
   - `TODO:` confirm both values (CLAUDE.md Section 19). Edit them directly in the list; there's no settings screen.

Optional test data: `provisioning/Import-SeedData.ps1` loads the fictional seed (`seed/`). `seed/expected-results.md` lists what every screen should show. Use a **test site** only.

## 4. Roles

The role comes from `JP_Employees.AppRole`, matched on the signed-in user's email.

| Role | Can |
|---|---|
| Manager/Supervisor | Everything below, plus: add and edit employees, add and revise documents, designate trainers, assign, remove assignments, put employees into training on JQCs, sign off JQCs (never their own) |
| Technician | See own items, upload PWI training logs, sign off own PWIs, view documents, matrix and cross-training |
| Viewer | Read-only: matrix, cross-training, libraries, PWI status, sign-off review |

People with no employee record, or with *Active* = No, get **Viewer** access.

## 5. Everyday administration

| Task | How |
|---|---|
| Someone leaves | Employees → open them → **Edit** → *Active* = No. **Never delete.** Their history stays. |
| Retire a document | Library → **Edit** → **Mark obsolete**. It disappears from assigning, the matrix and cross-training; history stays. |
| Revise a PWI | Library → **New revision**. Everyone currently assigned (active employees) gets a **Re-Sign Required** item, due in *ResignDueDays*. Old sign-offs show as Superseded under Previous revisions. |
| Revise a JQC | Library → **New revision**. Everyone currently assigned goes back to **Needs Training** (decision D-01). A manager puts them into training, then signs them off. |
| A revision reports failures | The result card lists who failed. Select **Retry failures**; it never creates duplicates (SPEC.md A-37). |
| Change the target or re-sign period | Edit the one row in `JP_Settings`. |
| Change choice values (Area, Shift, …) | Edit the column's choices in SharePoint. Don't rename the columns. |

**Never delete** list items or files. Assignments become *Removed* or *Superseded*, documents become *Obsolete*, employees become inactive.

## 6. Limits and delegation (read before you grow)

SharePoint returns large lists in pages. Power Apps can only push some filters to SharePoint ("delegation"); everything else runs on the rows already loaded. The app's **data row limit is 2,000**.

| Area | What's delegated to SharePoint | Limit in the app |
|---|---|---|
| Role lookup | `Email =` on `JP_Employees` (indexed) | none |
| Current assignments (status logic, matrix, cross-training, home tiles) | `IsCurrent = true` (indexed) | Status logic runs on the first **2,000 current assignment rows**. Superseded and removed rows don't count. |
| Employees and documents lists | `Active`, `Status`, `DocType` (indexed) | 2,000 each |
| Revision re-assign | `DocumentID` + `IsCurrent` (indexed) | Built and tested for up to **500** affected rows per document. It runs row by row, so larger revisions are slow. |
| Search boxes | `StartsWith` on text columns | Combined with other filters, may only search the first 2,000 rows |

Signs you're near a limit: counts that look too low, or Power Apps showing a blue delegation warning in Studio. Options then are archiving old documents (mark obsolete), splitting by site, or raising the data row limit (Studio → Settings, maximum 2,000). Talk to the developer before going beyond about 1,500 current assignments.

## 7. Updating to a new version
1. Import the newer zip into the same environment. Choose **Upgrade** if offered, and keep the existing environment variable values and connections.
2. Check the flow is still **On**, then open the app → **Publish**.
- Data in SharePoint is never touched by an import.

## 8. Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Everyone sees "Read-only access" | Their email in `JP_Employees` doesn't match their sign-in, or *Active* = No. Fix the email (lowercase). |
| A data source shows a warning in Studio | Data pane → the list → **⋯ → Refresh** (SPEC.md A-29). |
| Upload says the flow can't be found | Studio → **Power Automate** pane → remove and re-add **JQCPWI - Upload File**. It keeps the same name (SPEC.md A-33). |
| Upload fails with a message | The message comes from the flow. Common causes: wrong file type, over 25 MB, or the user can't write to that library (check permissions, 3.2). |
| Flow won't turn on | Read the message. A data policy may block a connector or action. Only standard SharePoint file actions are used. |
| "This revision is no longer current" | The document was revised after the item was opened. The person signs the new item from My Training. |
| Columns missing or named wrong | A column was mistyped during setup. In SharePoint → List settings → the column → check the internal name at the end of the address bar (`Field=JobTitle`). |

## 9. Rebuilding from source (developers)

```bash
tools/setup-pac-linux.sh                    # Linux without .NET; on Windows/macOS install pac normally
export PAC="python3 $HOME/.pac-local/bin/pac.py"
python3 flows/build_flow.py                 # upload flow -> solution
python3 app/build_app.py                    # app -> .msapp (round-trip checked) -> solution
python3 app/tests/test_formulas.py          # named formulas vs seed/expected-results.md
python3 app/tests/lint_formulas.py          # syntax check of every formula
python3 solution/build.py                   # -> solution/dist/JQCPWIManagement_<version>_unmanaged.zip
```
Bump `SOLUTION_VERSION` in `solution/build.py` for every release.

## 10. Open items (`TODO:` until confirmed)
- [ ] Default re-sign period: 14 days
- [ ] Cross-training target: 2 qualified per task
- [ ] Does in-app sign-off (signed-in user + timestamp) meet quality record requirements? (SPEC.md OQ-06)
- [ ] Map the placeholder SharePoint groups to real groups
- [ ] Decide whether technicians' direct edit rights in SharePoint are acceptable (SPEC.md OQ-03)
