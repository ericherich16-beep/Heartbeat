# Power Apps packaging: lessons and pre-delivery checks

This document collects the problems from three earlier builds: **Quality Rejection** (Part Rejection Tracker), **Stage 2** (Laser Shift Checklist) and **JQC/PWI Management**. For each problem it gives the cause, the rule that prevents it, and the check an agent runs before handing over a package.

Each check ID matches a check in `verify_package.py`. Checks marked **MANUAL** can't be decided from the zip, so the agent confirms them and says so in the delivery message.

## How an agent runs it

```bash
python3 powerapps-packaging/verify_package.py solution/dist/<Name>_<ver>_unmanaged.zip \
    --previous-version <last version the user imported> \
    --schema lists.json \
    --docs docs/ \
    --src app/build/src \
    --pac "pac"                      # or the Linux shim: "python3 /path/pac.py"
# optional, once the user has sent their field exports:
#   --tenant-fields exports/
```

**Don't deliver while anything FAILs.** Read every WARN, and either fix it or explain it to the user. List the MANUAL items in the handover and say which ones you confirmed.

The script was tested on every old JQC/PWI build. Each build fails exactly where it failed for the user. 1.0.6 and 1.0.7 pass everything except APP-02: four combo boxes still default to a sample column (`Value1`), and that issue is in every build so far.

| Build | What the user saw | Script result |
|---|---|---|
| 1.0.0 | Import failed: "Cannot add a Root Component … type 300" | PKG-02 FAIL, FLOW-02 FAIL |
| 1.0.1 | Flow wouldn't turn on (`item/DocType/Value`); screens blank | FLOW-02, APP-03/04/05/06/07 FAIL |
| 1.0.2–1.0.3 | Blank screens, black controls, sideways galleries | APP-03/04/05 FAIL |
| 1.0.4 | Black controls, sideways galleries | APP-04/05 FAIL |
| 1.0.5 | File picker showed only "No file selected" | APP-06 FAIL |
| Setup 1.0.0 | Flow blocked by "Advanced Connector Policy" | FLOW-01 FAIL |
| 1.0.6–1.0.7 | (not reported yet) | APP-02 FAIL on 4 combo boxes |

---

## A. Package and import route

**PKG-01: Deliver a solution zip, and send the user to the right import button.**
- *What happened (Quality Rejection):* the user zipped the `.msapp` and used **Apps → Import canvas app**. It failed with "manifest file could not be found". That button only takes packages exported from another environment, which contain `manifest.json`. Studio also no longer has a File menu with Open.
- *Rule:* deliver a solution zip built with `pac solution pack`. The user imports it at **Solutions → Import solution** and **doesn't unzip it**. A bare `.msapp` opens only from **Apps → Import app → From file (.msapp)**, never from *Import canvas app*.
- *Check:* `solution.xml`, `customizations.xml` and `[Content_Types].xml` are at the zip root, with no nested zip. DOC-02 fails if the docs point the user to *Import canvas app*.

**PKG-02: Every root component must really be in the zip.**
- *What happened (JQC 1.0.0):* "Cannot add a Root Component jp_… of type 300". `pac solution init` leaves `<CanvasApps />` out of `Customizations.xml`, so `pac solution pack` silently dropped the app.
- *Rule:* add the `<CanvasApps>` section yourself. After packing, open the zip and confirm that every `RootComponent` is there: the app (300), each flow (29) and each environment variable (380).
- *Check:* each type 300 has a `<CanvasApp>` and its `.msapp` file. Each type 29 has a `<Workflow>` and its JSON file. Each type 380 has its definition folder. The reverse also holds: every app in the zip is a root component.

**PKG-03: Bump the version on every build.**
- *Why:* an upgrade import of the same version doesn't replace anything. A version per zip also lets the user say which build they tested.
- *Check:* the version has four parts and is higher than `--previous-version`. Ship unmanaged while the app is still changing.

**PKG-04: Build the `.msapp` from a real app's supporting files.**
- *What happened (Stage 2 1.0.0.2):* the import succeeded, but the app wouldn't open in Studio: `ErrOpeningDocument_UnknownError`, with no detail. The cause was the supporting files written from scratch (Header, Properties, References, manifest). A diagnostic solution with four test apps proved this: the same screens on a **Studio-saved base file** opened.
- *Rule:* never write `Header.json`, `Properties.json` or `References/*` by hand. Start from a Studio-saved `.msapp`, or from `pac canvas unpack` of a real sample, and generate only the screens and formulas. If an app won't open and the error gives no detail, ship a small diagnostic solution with one variable per test app rather than guessing.
- *Check:* the `.msapp` opens as a zip and its JSON parses. **MANUAL:** confirm where the template came from.

**PKG-05: Round-trip every `.msapp`.**
- *Rule:* run `pac canvas unpack` and then `pac canvas pack`, and compare every rule. pac strips defaults, so compare against the **packed** rules, not your generator's input.
- *Check:* with `--pac`, unpack and repack must succeed, and no control/property/formula may change.

**PKG-06: Toolchain (no automated check).**
- `pac` runs on Linux without .NET: get the `pac` NuGet package and the .NET runtime from nuget.org, and start it through a small `hostfxr` shim (`tools/setup-pac-linux.sh` in the JQC repo).
- The `.fx.yaml` format behind `pac canvas pack` is deprecated (pac prints a warning) but still works in 2.14. The fallback is per-screen `.pa.yaml` pasted into Studio.
- Solutions, environment variables and connection references need **Dataverse in the environment**, even when the app's data lives in SharePoint. Say so in the README (DOC-01).

## B. Canvas app

**APP-01: Only set properties the control actually has.**
- *What happened (Stage 2 1.0.0.1):* 20 import errors. `AccessibleLabel` was set on classic **buttons**, which don't support it.
- *What happened (Stage 2 1.0.0.5/6):* a `SearchItems` property on classic **combo boxes**. Studio shows it, but the YAML loader rejected it and the import failed.
- *Rule:* check each property against the control's template XML (`References/Templates.json`). Prefer a classic **dropdown** to a combo box for short lists. If you need a combo box, add it in Studio, or set `SearchItems` explicitly and test it.
- *Check:* FAIL for properties that aren't on the template, apart from known implicit layout properties. FAIL on the denylist (`button.AccessibleLabel`). WARN on `combobox.SearchItems`.

**APP-02: Don't leave template defaults that point at sample data.**
- *What happened (Stage 2):* the combo box's default `SearchItems` refers to the template's sample column `Value1`, which produced `Value1` errors.
- *Check:* FAIL on any formula that refers to `Value1`, `Value2` and so on.
- **The current JQC/PWI build (1.0.7.0) still has this in 4 combo boxes:** `cmbAssignDoc`, `cmbAssignEmp`, `cmbDocTrainers` and `cmbEmpSup`.

**APP-03: Every screen needs Width and Height.**
- *What happened (JQC 1.0.1–1.0.3):* every screen was blank. With no size rules, Studio sized the screens 0×0, so the root containers (`Parent.Width`) collapsed. The user's tree view showed `conRootHome 0 x 0`.
- *Rule:* give each screen `Width = App.Width`, `Height = App.Height`, `Size = 1 + CountRows(App.SizeBreakpoints) - CountIf(App.SizeBreakpoints, Value >= Self.Width)` and `Orientation = If(Self.Width < Self.Height, Layout.Vertical, Layout.Horizontal)`, and set `App.SizeBreakpoints` (for example `[640, 1024, 1366]`).
- *Check:* every screen has non-empty Width and Height rules.

**APP-04: No EditorState files when packing generated source.**
- *What happened (JQC 1.0.2–1.0.4):* labels, inputs and dropdowns showed black and harsh. With EditorState files present, pac adds **no theme defaults**, so the controls have no Fill. Without them, pac adds the defaults and still keeps the auto-layout properties.
- *Check:* with `--src`, there are no `*.editorstate.json` files. In the `.msapp`, every text input, dropdown, combo box and date picker has a Fill rule, and every label has a Color rule.

**APP-05: Galleries need an explicit Layout.**
- *What happened (JQC 1.0.2–1.0.4):* the nav rail and lists ran sideways, because the template default is Horizontal.
- *Check:* every gallery has a `Layout` rule.

**APP-06: An attachments control outside a form must be made editable.**
- *What happened (JQC 1.0.5):* Add document showed only "No file selected", then "Please fill in: File". An attachments control outside a form is read-only.
- *Rule:* set `DisplayMode = DisplayMode.Edit`, `IsInDataCard = true` and `Items = []`.
- *Check:* every attachments control that isn't inside a form/data card has all three.

**APP-07: Watch `!` precedence.**
- *What happened (JQC):* `!Lower(email) = fxMeEmail` negates the text before the comparison, so the manager visibility rules errored.
- *Rule:* write `!(a = b)` or `Not(a = b)`.
- *Check:* regex for `!operand =` / `!operand <>`.

**APP-08: Keep paired controls wired to their own pair.**
- *What happened (Stage 2, after a manual change in Studio):* `chk_cboPN2` used `chk_tglL1Run`. Turning Laser 1 off disabled both part boxes and blocked Submit.
- *Check (WARN):* a control whose name has a number N that refers to a sibling numbered M ≠ N, when an N version of that sibling exists. Give the same check to the user when they copy controls by hand.

**APP-09: Keep SharePoint queries delegable.**
- *What happened (Stage 2):* SharePoint rejected the History query. The fix was one plain date-range filter sent to SharePoint, capped below the 2,000-row limit, with the other filters applied in the app afterwards.
- *Rule:* filter SharePoint on indexed Text, Number, Choice, Date and Yes/No columns, using `=`, `<`, `>`, `StartsWith` and `&&`/`||`. Never apply `Lower`, `Trim`, `Len`, `IsBlank`, `Text`, `in` or `Search` to a column inside `Filter`/`LookUp` on a SharePoint list.
- *Check (WARN):* those functions applied directly to a column of the list being filtered, plus `Search(<SP list>)`.

**APP-10: Don't name record fields after Power Fx names.**
- *What happened (Stage 2):* a checklist-item field called `Type` clashed with a built-in function and had to become `ItemType`.
- *Check (WARN):* record fields named `Type`, `Self`, `Parent`, `ThisItem` or `ThisRecord` in `Formulas`, `OnStart` or `Items`.

**APP-11: No hard-coded tenant values.**
- *Rule:* site URLs, list GUIDs and chat IDs go through environment variables. Placeholders (`contoso`) are fine only where an environment variable overrides them. Environment variables ship with **no value**, so the import wizard asks for them.
- *Check:* no non-contoso `*.sharepoint.com` URL appears in a formula or environment variable default.

**APP-12: Bind every SharePoint data source to environment variables.**
- *Rule:* in the app's `ConnectionReferences`, each data source needs `datasetOverride` (the site variable) and `tableNameOverride` (the list variable), and both variables must be in the solution.
- *Check:* every SharePoint source in `DataSources.json` is bound, and both variables exist.

**APP-13: The app's flow reference must point at the flow in the same solution.**
- *What happened (Stage 2, and JQC A-33):* after an import, App checker said the flow had no `Run`, along with knock-on errors. The link from the app to the flow was dropped.
- *Rule:* the flow data source's `WorkflowEntityId` must equal the solution's workflow ID, and that workflow must be in `CdsDependencies`. POST_IMPORT must include the fallback: **Power Automate pane → remove the flow → add it again**.
- *Check:* both IDs match. **MANUAL:** the fallback step is in the docs.

**APP-14: The app's embedded list definitions must match the schema.**
- *What happened (JQC):* every solution import resets the app's embedded table definitions to what was generated. After a Studio *Refresh* fixed things, the next import broke them again.
- *Rule:* generate the definitions from the same `lists.json` that drives the setup guide. After each import, the user runs **Data → each list → ⋯ → Refresh**.
- *Check:* with `--schema`, every column exists in the embedded definition with a compatible type.

## C. SharePoint lists and libraries

**SP-01: Display name = internal name, created in the right order.**
- *What happened (JQC):* the user created the lists by hand or from Excel, and got internal names like `field_1` and `field_3`. The app and flow asked SharePoint for columns that didn't exist (990+, then 800+ errors), and the flow couldn't turn on.
- *Rule:* in `lists.json`, internal name = display name, a plain identifier (`DocNumber`, not "Doc Number"). The manual guide says to create each column **with that exact name first**, never by importing from Excel, and rename nothing afterwards.
- *Check:* the schema has no `field_N` and no spaces.

**SP-02: Mark each entry as list or library.**
- *What happened (JQC):* `JP_Documents` and `JP_SignoffRecords` were created as **lists**, not document libraries. The environment variable type can't be changed after import, so the user had to recreate them.
- *Rule:* every entry in `lists.json` has `"kind": "list" | "library"`, and the setup guide says **Document library** in bold.
- *Check:* `kind` is set on every entry. With `--tenant-fields`, a library has `FileLeafRef` and a list doesn't.

**SP-03: Compare against the real site before blaming the app.**
- *What happened (JQC):* columns had the wrong type: Text instead of Person, Choice instead of Yes/No, Choice columns with no choices, and a duplicate `DocTitle` (`docTitle0`). Refresh can't fix a type mismatch.
- *Rule:* ask the user for a field export, then compare. One command per list:
  `Get-PnPField -List "<List>" | Select InternalName,Title,TypeAsString | Export-Csv "<List>.csv"`.
  Before asking the user to spend time fixing lists, prove the app itself works with a no-SharePoint **demo build** (RUN-02).
- *Check:* with `--tenant-fields`, flag missing columns (and display names that map to a different internal name), wrong `TypeAsString` values and duplicate display names.

**SP-04: Data added outside the app must still show.**
- *What happened (JQC 1.0.7):* a JQC uploaded straight into the library didn't appear. The filters required `DocType = JQC` and `Status = Active`, and both were empty.
- *Rule:* treat a blank as the default, show such rows with a "details missing" flag, and let Edit fill them in. Seed data includes one row with blank metadata.
- *Check:* **MANUAL** (RUN-01).

## D. Flows

**FLOW-01: Use only connectors and actions the tenant allows.**
- *What happened (JQC setup flow):* "Admin data policy 'Advanced Connector Policy' restricts … `HttpRequest`". *Send an HTTP request to SharePoint* is blocked, so a flow that creates lists can't run there.
- *Rule:* no `HttpRequest`, no premium connectors (HTTP, Dataverse) and no custom connectors. Lists are created by hand or with PnP.
- *Check:* FAIL on blocked operationIds (`--blocked-ops`, default `HttpRequest`), on HTTP actions and on the Dataverse connector.

**FLOW-02: Flows don't set list columns.**
- *What happened (JQC 1.0.0/1.0.1):* "The API operation does not contain a definition for parameter 'item/DocType/Value'", and the flow wouldn't turn on. *Update file properties* checks its column parameters against the **real** library when the flow is saved, and the user's columns had `field_N` names.
- *Rule:* the flow only creates or replaces the file and returns the item ID. The app sets the columns with `Patch`, because Power Apps uses display names after a Refresh.
- *Check:* FAIL on any `item/...` parameter, unless `--allow-flow-item-params` (only once the real internal names are confirmed).

**FLOW-03: Connection references must be defined in the solution.**
- *Rule:* each `connectionReferenceLogicalName` the flow uses has a `<connectionreference>` in `customizations.xml`. The user binds it in the import wizard. If they skip it, the flow stays off.
- *Check:* every logical name resolves.

**FLOW-04: No placeholders that silently break.**
- *What happened (Stage 2):* the Teams chat imported as `REPLACE_CHAT_ID`. The user had to re-pick it in both post actions after **every** import.
- *Rule:* ask the user for the real ID once (**⋯ → Peek code** on the action, `body/recipient`) and build it in. Until then, POST_IMPORT lists the step.
- *Check (WARN):* `REPLACE_…`, `TODO` or `<your…>` in a flow definition.

**FLOW-05: A flow the app waits on must fail fast.**
- *What happened (Stage 2):* Submit stuck on "Saving…" with every button greyed out. A failing Teams post retried for minutes while the app waited.
- *Rule:* in Power Apps–triggered flows, set `retryPolicy: none` and a short timeout on non-SharePoint actions. In the app, wrap each step in `IfError`, show which step is running, and always clear the busy state.
- *Check (WARN):* non-SharePoint `OpenApiConnection` actions without `retryPolicy` and a `limit.timeout`.

**FLOW-06: Respond to the app on failure too.**
- *Rule:* put the work in a Try scope, and add a *Respond to Power Apps* step that runs after it fails or times out.
- *Check (WARN):* follows the `runAfter` chain to find a Response step on a failure path.

**FLOW-07: The flow may be off after import.**
- *What happened (JQC):* "flows may not have turned on". Later the upload failed with "flow is switched off". Power Platform leaves a flow off when its connection wasn't picked at import, and an upgrade import can turn it off again.
- *Rule:* POST_IMPORT says: bind the connection reference, then **Cloud flows → Turn on**, and check again after every upgrade.
- *Check:* WARN if the flow ships off. **MANUAL** otherwise.

**Also from Stage 2: hidden controls with formula errors do nothing.** Power Apps won't run a formula that has an App checker error, so a hidden "do submit" button just sat on "Saving…" with no message. Put save logic on the visible button. The user's App checker must show 0 errors before testing.

## E. Docs and the handover

**DOC-01: POST_IMPORT has every step.**
- *Required steps:* Solutions → Import solution, don't unzip, bind connection references, fill in environment variables, turn the flow on, refresh the data sources, re-add the flow if `Run` is missing, App checker shows 0 errors, then Save and Publish. Also the Dataverse prerequisite.
- *Check:* with `--docs`, keyword checks for each step.

**DOC-02: The docs never send the user to *Import canvas app*.** See PKG-01.

**RUN-01: Offline formula tests.** Use `pac power-fx run` on the named formulas against fictional seed data, including the edge cases: blank metadata, inactive users, revisions, overdue items. pac's offline mode limits: no `ClearCollect` (use `Set(x, Table(...))`), one statement per line, `!(a||b)` fails (use `Not`).

**RUN-02: A demo build proves the app separately from the lists.** Build the same app on collections filled from seed data, with no SharePoint. In JQC, the demo rendered correctly while the real app was empty, which proved the remaining faults were in the list setup.

**RUN-03: Studio edits get lost on re-import.** Before rebuilding, ask the user for any changes they made in Studio and put them into the source. A re-import also means re-adding data sources and the flow and re-picking any placeholders. For small fixes, offer paste-in-Studio instructions as well as a new zip.

**RUN-04: Say honestly what was tested.** Every handover says the package passed `verify_package.py` but **hasn't been opened in Power Apps**, lists the post-import steps, and asks for exact error text (control + property + message) if something fails.

---

## lists.json format (for `--schema`)

See `lists.example.json`. Types use SharePoint `TypeAsString` names: `Text`, `Note`, `Number`, `Currency`, `DateTime`, `Boolean`, `Choice`, `MultiChoice`, `User`, `UserMulti`, `Lookup` and `URL`.
