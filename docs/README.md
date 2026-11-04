# JQC/PWI Management

A Power Apps solution for **Job Qualification Checklists (JQC)** and **Process Work Instructions (PWI)**.
- Managers add documents, designate trainers and assign them.
- Technicians sign off PWIs.
- Managers qualify people on JQCs.
- Everyone sees one training matrix and a cross-training view.

When a PWI is revised, everyone assigned must re-sign. When a JQC is revised, everyone assigned goes back to Needs Training. The matrix only counts sign-offs on the **current revision**.

All names, emails and documents in this repository are **fictional**.

## Use it

| You are | Read |
|---|---|
| Deploying or administering | [`Admin-Guide.md`](Admin-Guide.md) |
| A technician using the app | [`Technician-Quick-Guide.md`](Technician-Quick-Guide.md) |
| Reviewing requirements | [`../SPEC.md`](../SPEC.md) (rules BR-01 to BR-49, acceptance criteria, assumptions, open questions, decisions) |
| Building or changing it | [`../CLAUDE.md`](../CLAUDE.md) (build brief) and section 9 of the Admin Guide |

**Quick start:**
1. Create the lists (`provisioning/Manual-Setup.md`).
2. Import `solution/dist/JQCPWIManagement_<version>_unmanaged.zip` at make.powerapps.com → Solutions → Import solution, and pick your site and lists.
3. Turn on the flow and add yourself as a manager in `JP_Employees`.

## What the screens look like

`docs/mockups/` has a reference image of every screen (desktop 1366×768) and of Home, My Training and Matrix on a phone. They're drawings of the intended design, with the app's layout, theme and labels and the fictional seed data, rendered by `tools/render_mockups.py`. They are not Power Apps screenshots.

## What's in the solution

| Component | Name |
|---|---|
| Canvas app | JQC/PWI Management (13 screens, responsive: phone, tablet, desktop) |
| Cloud flow | JQCPWI - Upload File (Power Apps V2 trigger; standard SharePoint file actions) |
| Connection reference | JQC/PWI - SharePoint |
| Environment variables | `jp_SiteUrl`, `jp_ListEmployees`, `jp_LibDocuments`, `jp_ListAssignments`, `jp_LibSignoffs`, `jp_ListSettings` (no values stored) |

## Repository layout

| Path | What |
|---|---|
| `provisioning/` | `Manual-Setup.md` (create lists by hand), `Create-Lists.ps1`, `Import-SeedData.ps1` |
| `seed/` | Fictional seed CSVs and `expected-results.md` |
| `app/` | `build_app.py` (generator), `screens.py` (screens), `App.fx.md` (named formulas, generated), `template/` (control definitions), `tests/` |
| `flows/` | `build_flow.py` (upload flow generator), `JQCPWI-UploadFile.md` (build spec, generated) |
| `solution/` | `JQCPWIManagement/` (pac solution project), `build.py`, `build_setup.py`, `env-vars.md`, `dist/` (importable zips) |
| `tools/` | `setup-pac-linux.sh` |

## How it was built and tested
- The solution zip is generated and packed with Microsoft's Power Platform CLI (`pac`). See CLAUDE.md Section 4 and decision D-02.
- **Packaging:** every control property is round-trip checked in the packed `.msapp`.
- **Logic:** `app/tests/test_formulas.py` runs the app's named formulas offline with `pac power-fx` against the seed data. It checks the home tiles for every role, every matrix cell and task coverage against `seed/expected-results.md`.
- **Syntax:** `app/tests/lint_formulas.py` syntax-checks every formula in every screen.
- **Not covered:** anything that needs Power Apps itself (screen actions, the flow run, layout on real devices). That has to be tested after import. See the acceptance criteria in SPEC.md Section 5.
