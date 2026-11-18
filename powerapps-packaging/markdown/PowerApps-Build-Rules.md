# Power Apps build rules

Rules for building a Power Apps canvas app on SharePoint and packaging it as an importable solution `.zip`. Each one comes from a real failure in an earlier build (Quality Rejection, Laser Shift Checklist, JQC/PWI Management).

Each rule has:
- **Seen:** what the user saw.
- **Rule:** what must be true.
- **AI check:** what the assistant (Copilot or Claude) checks itself in pasted source, formulas or steps.
- **Script:** the matching line in the `Verify-PowerAppsPackage.ps1` / `verify_package.py` report (same ID).

Report statuses: **FAIL** must be fixed before delivery. **WARN**: review it and fix or explain. **MANUAL**: confirm it by hand and say so.

## Workflow

1. **Spec first:** take the spec or PRD (from any source), then slice it into vertical slices or use its slices (section F). Write `lists.json`.
2. **Generate the source,** starting from a real Studio-saved app (PKG-04).
3. **Pack on the PC:** `pac canvas pack`, then `pac solution pack`.
4. **Run the checker** on the zip and fix every FAIL. Run it again.
   Steps 2–6 repeat for **each slice**.
5. **Import** at **Solutions → Import solution**, then follow POST_IMPORT. App checker must show 0 errors.
6. **Report problems exactly.** Copy any import message or App checker error word for word: control name + property + message.

---

## A. Package and import

### PKG-01: Deliver a solution zip, and send the user to the right import button
- **Seen:** the user zipped the `.msapp` and used **Apps → Import canvas app**, which failed with "manifest file could not be found". Studio no longer has a File → Open menu.
- **Rule:** deliver a solution zip built with `pac solution pack`, imported at **Solutions → Import solution**. **Don't unzip it.**
  - A bare `.msapp` opens only from **Apps → Import app → From file (.msapp)**.
  - Never use *Import canvas app*. It only takes packages exported from another environment, which contain `manifest.json`.
- **AI check:** instructions never mention *Import canvas app*, except to say not to use it.
- **Script:** `solution.xml`, `customizations.xml` and `[Content_Types].xml` are at the zip root, with no nested zip.

### PKG-02: Every root component must really be in the zip
- **Seen:** "Cannot add a Root Component `<name>` of type 300 because it is not in the target system."
- **Cause:** `pac solution init` leaves the `<CanvasApps>` section out of `Customizations.xml`, so `pac solution pack` silently dropped the app.
- **Rule:** add `<CanvasApps><CanvasApp>…</CanvasApp></CanvasApps>` to `Other/Customizations.xml`. After packing, open the zip and confirm the app (type 300), each flow (type 29) and each environment variable (type 380) are inside.
- **Script:** PKG-02.

### PKG-03: Bump the version on every build
- **Rule:** the solution version has four parts and goes up on every build, or an upgrade import does nothing. Ship unmanaged while the app is still changing.
- **Script:** PKG-03 (pass the previous version).

### PKG-04: Build the `.msapp` from a real app's supporting files
- **Seen:** the import succeeded, but the app wouldn't open: `ErrOpeningDocument_UnknownError`, with no detail.
- **Cause:** `Header.json`, `Properties.json`, `References/*` and the manifest were written from scratch.
- **Rule:** start from a Studio-saved `.msapp`, or from `pac canvas unpack` of a real sample. Generate only the screens and formulas. If an app won't open and the error gives no detail, build a small diagnostic solution with several tiny apps that each change one thing, rather than guessing.
- **Script:** PKG-04 checks the structure. MANUAL: confirm where the template came from.

### PKG-05: Round-trip every `.msapp`
- **Rule:** run `pac canvas unpack`, then `pac canvas pack`, and compare. No formula may change. pac strips default values, so compare against the packed result.

### PKG-06: Toolchain
- **Installing pac on Windows:** use the VS Code **Power Platform Tools** extension, the MSI, or `dotnet tool install --global Microsoft.PowerApps.CLI.Tool`.
- **Source format:** the `.fx.yaml` format behind `pac canvas pack` is deprecated (pac prints a warning) but still works. The fallback is to paste `.pa.yaml` into Studio one screen at a time.
- **Dataverse:** solutions, environment variables and connection references need Dataverse in the environment, even when the data is in SharePoint. Say so in the README.

---

## B. Canvas app

### APP-01: Only set properties the control actually has
- **Seen:** 20 import errors, because `AccessibleLabel` was set on classic buttons, which don't have it. A later import failed because of `SearchItems` on classic combo boxes.
- **Rule:** only use properties that exist on the control's template. Prefer a classic **Dropdown** to a Combo box for short lists. If you need a combo box, add it in Studio.
- **AI check:** flag `AccessibleLabel` on any classic button and `SearchItems` on any combo box. If unsure whether a property exists on that control, say so.
- **Script:** APP-01 checks every property against the control template inside the package.

### APP-02: Don't leave template defaults that point at sample data
- **Seen:** errors mentioning `Value1`. The combo box's default search formula uses a sample column.
- **AI check:** flag any formula that refers to `Value1`, `Value2` and so on, or to other sample names.
- **Script:** APP-02.

### APP-03: Every screen needs Width and Height
- **Seen:** every screen was blank. The tree view showed the root container at 0 × 0.
- **Rule:** give every screen these rules:
  ```
  Width       = App.Width
  Height      = App.Height
  Size        = 1 + CountRows(App.SizeBreakpoints) - CountIf(App.SizeBreakpoints, Value >= Self.Width)
  Orientation = If(Self.Width < Self.Height, Layout.Vertical, Layout.Horizontal)
  ```
  and set `App.SizeBreakpoints = [640, 1024, 1366]`.
- **AI check:** every screen has Width and Height.
- **Script:** APP-03.

### APP-04: No EditorState files when packing generated source
- **Seen:** labels, inputs and dropdowns were black.
- **Cause:** with `Src/EditorState/*.editorstate.json` present, pac adds no theme defaults, so the controls have no Fill.
- **Rule:** delete the EditorState files before `pac canvas pack`. Every text input, dropdown, combo box and date picker needs Fill. Every label needs Color.
- **Script:** APP-04.

### APP-05: Galleries need an explicit Layout
- **Seen:** the nav rail and lists ran sideways, because the template default is Horizontal.
- **Rule:** every gallery sets `Layout` (`Layout.Vertical` unless horizontal is intended).
- **AI check:** every gallery has a Layout.
- **Script:** APP-05.

### APP-06: An attachments control outside a form must be made editable
- **Seen:** the file box showed only "No file selected", then "Please fill in: File".
- **Rule:** set `DisplayMode = DisplayMode.Edit`, `IsInDataCard = true` and `Items = []`.
- **AI check:** every attachments control has all three.
- **Script:** APP-06.

### APP-07: Watch `!` precedence
- **Seen:** the manager visibility rules errored. `!Lower(email) = fxMeEmail` negates the text, not the comparison.
- **Rule:** write `!(a = b)` or `Not(a = b)`.
- **AI check:** look for `!` followed by an operand and then `=` or `<>`.
- **Script:** APP-07.

### APP-08: Keep paired controls wired to their own pair
- **Seen:** `chk_cboPN2` used `chk_tglL1Run`. Turning Laser 1 off disabled both part boxes and blocked Submit.
- **AI check:** when controls come in numbered sets (…1 / …2), each one refers only to its own set. When giving copy-and-rename steps for Studio, list every property that names the other set.
- **Script:** APP-08 (WARN).

### APP-09: Keep SharePoint queries delegable
- **Seen:** SharePoint rejected the History screen's query.
- **Rule:** send SharePoint only simple filters on indexed Text, Number, Choice, Date and Yes/No columns, using `=`, `<`, `>`, `StartsWith`, `&&` and `||`.
  - Never apply `Lower`, `Upper`, `Trim`, `Len`, `IsBlank`, `Text`, `Year`, `in` or `Search` to a **column** inside `Filter`/`LookUp` on a SharePoint list.
  - For complex filters, query a capped date range first (under 2,000 rows), then filter in the app.
- **AI check:** review every `Filter`/`LookUp`/`Search` on a SharePoint list, and name each part that can't be delegated.
- **Script:** WARN in `verify_package.py`. MANUAL in the PowerShell version.

### APP-10: Don't name record fields after Power Fx names
- **Seen:** a field called `Type` clashed with a built-in name and had to become `ItemType`.
- **AI check:** flag record fields named `Type`, `Self`, `Parent`, `ThisItem` or `ThisRecord`.

### APP-11: No hard-coded tenant values
- **Rule:** site URLs, list IDs and chat IDs come from environment variables. Environment variables ship with **no value**, so the import wizard asks for them. A placeholder like `contoso` is fine only where an environment variable overrides it.
- **AI check:** flag any real `*.sharepoint.com` URL, GUID or email address in the source.
- **Script:** APP-11.

### APP-12: Bind every SharePoint data source to environment variables
- **Rule:** in the app's `ConnectionReferences` (in `customizations.xml`), each SharePoint data source needs `datasetOverride` (the site variable) and `tableNameOverride` (the list variable). Both variables must be in the solution.
- **Script:** APP-12.

### APP-13: The app's flow reference must point at the flow in the same solution
- **Seen:** after an import, App checker said the flow had no `Run`, with knock-on errors.
- **Rule:** the flow data source's `WorkflowEntityId` equals the solution's workflow ID, and `CdsDependencies` lists it. POST_IMPORT includes the fallback: **Power Automate pane → remove the flow → add it again**.
- **Script:** APP-13.

### APP-14: The app's embedded list definitions must match the schema
- **Seen:** things worked after **Refresh** in Studio, then broke again after the next import.
- **Cause:** every solution import resets the app's embedded list definitions.
- **Rule:** generate the definitions from the same `lists.json` as the setup guide. After every import: **Data → each list → ⋯ → Refresh**.
- **Script:** APP-14 (pass the schema).

### Also: hidden controls with formula errors do nothing
- **Seen:** Submit stuck on "Saving…" with no message. The save logic sat on a hidden button that had an App checker error, and Power Apps doesn't run a formula that has an error.
- **Rule:** put the save logic on the visible button, wrap each step in `IfError`, show which step is running, and always clear the busy state. App checker must show 0 errors before testing.

---

## C. SharePoint lists and libraries

### SP-01: Display name = internal name, created in the right order
- **Seen:** columns had internal names like `field_1` and `field_3`, from lists made by hand or from Excel. The app showed 800–990 errors and the flow couldn't turn on.
- **Rule:** every column's internal name equals its display name: a plain identifier with no spaces (`DocNumber`). Create each column with that exact name first, then never rename it. Never create lists by importing from Excel.
- **AI check:** setup guides tell the user to type the exact name when creating each column.
- **Script:** SP-01 (pass the schema).

### SP-02: Mark each entry as list or library
- **Seen:** document libraries were created as lists. The environment variable couldn't be changed after import, so they had to be recreated.
- **Rule:** `lists.json` says `"kind": "list"` or `"library"`, and the setup guide says **Document library** in bold.
- **Script:** SP-02.

### SP-03: Compare against the real site before blaming the app
- **Seen:** wrong column types (Text instead of Person, Choice instead of Yes/No), Choice columns with no choices, and a duplicate `DocTitle`. Refresh can't fix a type mismatch.
- **Rule:** export the real fields, one command per list (PnP PowerShell):
  ```powershell
  Get-PnPField -List "<List>" | Select InternalName,Title,TypeAsString | Export-Csv "<List>.csv" -NoTypeInformation
  ```
  Then run the checker with the schema and that folder of exports.
- **Prove the app first:** before asking anyone to spend time fixing lists, check the app works on built-in sample data with a demo copy that uses collections instead of SharePoint.
- **Script:** SP-03.

### SP-04: Data added outside the app must still show
- **Seen:** a file uploaded straight into the library didn't appear. The filter required DocType and Status, and both were blank.
- **Rule:** treat blank as the default, show the row with a "details missing" flag, and let Edit fill it in. Sample data includes one row with blank metadata.
- **AI check:** for each gallery filter, ask what happens when the column is blank.

---

## D. Flows

### FLOW-01: Use only connectors and actions the tenant allows
- **Seen:** "Admin data policy 'Advanced Connector Policy' restricts … HttpRequest".
- **Rule:** no *Send an HTTP request to SharePoint*, no premium connectors (HTTP, Dataverse) and no custom connectors. Create lists by hand from a guide, or with PnP PowerShell.
- **Script:** FLOW-01.

### FLOW-02: Flows don't set list columns
- **Seen:** "The API operation does not contain a definition for parameter 'item/DocType/Value'", and the flow wouldn't turn on.
- **Cause:** *Update file properties* checks its column names against the **real** library when the flow is saved.
- **Rule:** the flow only creates or replaces the file and returns the item ID. The app sets the columns with `Patch` right after.
- **Script:** FLOW-02.

### FLOW-03: Connection references must be defined in the solution
- **Rule:** the user picks the connection in the import wizard. If they skip it, the flow stays off.
- **Script:** FLOW-03.

### FLOW-04: No placeholders that silently break
- **Seen:** the Teams chat imported as `REPLACE_CHAT_ID`, and the user re-picked it after every import.
- **Rule:** ask for the real ID once (the action → ⋯ → **Peek code** → `body/recipient`) and build it in. Until then, POST_IMPORT lists the step.
- **Script:** FLOW-04 (WARN).

### FLOW-05: A flow the app waits on must fail fast
- **Seen:** the app stuck on "Saving…" for minutes while a failing Teams post retried.
- **Rule:** in flows called from Power Apps, set **Retry policy = None** and **Timeout = PT1M** on actions that aren't SharePoint.
- **Script:** FLOW-05 (WARN).

### FLOW-06: Respond to the app on failure too
- **Rule:** put the work in a Try scope, and add a *Respond to a PowerApp or flow* step that runs after it fails or times out.

### FLOW-07: The flow may be off after import
- **Seen:** "flows may not have turned on", then "flow is switched off" when uploading.
- **Rule:** POST_IMPORT says to bind the connection reference and then turn the flow on (**Cloud flows → Turn on**). Check again after every upgrade import.

---

## E. Docs and handover

### DOC-01: POST_IMPORT has every step
1. **Solutions → Import solution**, and don't unzip the file.
2. Pick the connections.
3. Fill in the environment variables.
4. Turn the flows on.
5. Open the app and Refresh every data source.
6. Re-add the flow if `Run` is missing.
7. App checker shows 0 errors, then Save and Publish.

Also state the Dataverse prerequisite. **Script:** DOC-01 (pass the docs folder).

### DOC-02: The docs never send the user to *Import canvas app*

### RUN-01: Test with sample data
Test formulas against sample data before delivery, including the edge cases: blank metadata, inactive users, revisions and overdue items.

### RUN-02: A re-import overwrites the app
- Before rebuilding, collect every change made in Studio and put it into the source.
- A re-import also means re-adding the data sources and the flow, and re-picking any placeholders.
- For small fixes, offer paste-in-Studio steps instead of a new zip.

### RUN-03: Honest handover
Every handover says the package passed the checker but **wasn't opened in Power Apps**, lists the post-import steps, and asks for the exact error text if anything fails.

---

## F. Building from a spec in vertical slices

This kit is the **build** stage. The spec or PRD can come from anywhere, for example Matt Pocock's grill-me → write-a-prd → prd-to-plan skills. The assistant builds from it one vertical slice at a time.

### SLICE-01: Start from the spec, and slice it if needed
- **If the spec already has a plan of vertical slices** (for example a `prd-to-plan` output), build them in that order. Don't re-slice it.
- **If it doesn't,** propose the slices first: a numbered list, each with the user-visible behaviour, the lists/columns, screens/controls and flow steps it touches, and its acceptance test. **Wait for approval before building.**
- **If the spec is missing something a slice needs** (column types, list or library, roles, the exact flow trigger), ask. Don't guess.

### SLICE-02: Slice 1 is a tracer bullet through the packaging
- **Slice 1 contains:** the solution, the environment variables, **one** list (from `lists.json`), and **one** screen that reads and writes it. Include the flow too if the app has one.
- **The user imports it and it works** before any other features are built.
- **Why:** this proves every packaging rule (PKG, APP-03/04/12/13, SP, FLOW-01/02/07) on a tiny app.
- **Seen:** JQC/PWI was built in horizontal layers (all lists → environment variables → formulas → flow → 13 screens → docs). The first real import then hit the missing app (PKG-02), the flow column error (FLOW-02), `field_N` columns (SP-01), blank screens (APP-03) and black controls (APP-04), all at once. Stage 2 skipped testing between slices, and its first import failed the same way (APP-01, then PKG-04).

### SLICE-03: Each slice is vertical, not horizontal
- **A slice is one user-visible behaviour, end to end:** the list columns it needs, the screen controls, the formulas, any flow step, and its post-import steps.
- **Wrong:** "all lists", "all screens" or "all formulas".
- **Typical order:** tracer bullet (list + browse + add) → view/edit → status rules → file upload/flow → roles and permissions → reports/matrix → polish.

### SLICE-04: Every slice ends with an import and a test
For each slice, in order:
1. Bump the version.
2. Run the checker and get 0 FAIL.
3. The user imports it and App checker shows 0 errors.
4. The user runs the slice's acceptance test and reports back.

Don't start the next slice until this one passes, and don't batch slices into one import.

### SLICE-05: List changes per slice
SharePoint lists are set up by hand, so every slice gives:
- the exact columns to add, with internal name, type and choices
- the updated `lists.json`

Never rename or retype a column from an earlier slice. Add a new one instead.

### SLICE-06: Keep a slice log
Keep a short plan file (for example `plans/<app>-slices.md`) with each slice's status, version, test result, and any changes the user made in Studio, so they can be copied back into the source before the next build (RUN-02).

---

## `lists.json` format

```json
{
  "Rejections": {
    "kind": "list",
    "columns": { "Title": "Text", "PartNumber": "Text", "Status": "Choice",
                 "QtyRejected": "Number", "ClosedOn": "DateTime",
                 "IsOverdue": "Boolean", "Owner": "User" }
  },
  "RejectionDocuments": {
    "kind": "library",
    "columns": { "Title": "Text", "RejectionID": "Number", "DocType": "Choice" }
  }
}
```

Types use SharePoint `TypeAsString` names: `Text`, `Note`, `Number`, `Currency`, `DateTime`, `Boolean`, `Choice`, `MultiChoice`, `User`, `UserMulti`, `Lookup` and `URL`.
