---
name: powerapps-package-builder
description: Build, check and hand over Power Apps canvas apps packaged as importable solution zips (pac canvas pack / pac solution pack) on SharePoint lists, with Power Automate flows. Use when generating .msapp or .pa.yaml/.fx.yaml source, a solution zip, SharePoint list setup, or flows for an app, and when diagnosing an import error, an App checker error, a blank or black app, or a flow that won't turn on. Builds from an existing spec or PRD in tracer-bullet vertical slices (slicing it first if needed), with the rules from earlier failed imports and a verifier script to run before every slice is delivered.
---

# Power Apps package builder

Every rule here comes from a real failure: an import error, a flow that wouldn't turn on, a blank or black app, or a control that didn't work. The full rules, with symptoms and causes, are in `references/build-rules.md`. Read it before generating anything, and when diagnosing an error.

## Workflow

This skill is the **build** stage. The spec or PRD usually comes from elsewhere (for example grill-me → write-a-prd → prd-to-plan). Build it in vertical slices. Full rules are in section F of `references/build-rules.md`.

1. **Read the spec and get the slices.**
   - **If it already has vertical slices** (for example a `prd-to-plan` file in `plans/`), use them in order.
   - **If not,** propose numbered slices. For each: the user-visible behaviour, the lists/columns, screens/controls and flow steps it touches, and its acceptance test. **Stop and wait for approval.**
   - **If anything is missing** that a slice needs, ask instead of guessing.
2. **Slice 1 is a tracer bullet:** solution + environment variables + one list + one screen that reads and writes it (+ the flow if the app has one). It must be imported and working before any feature work.
3. **For each slice:**
   1. **Update `lists.json`** (format in `assets/lists.example.json`):
      - mark every list or library with `kind` `list` or `library`
      - every column's internal name equals its display name, a plain identifier with no spaces
      - give every column's SharePoint `TypeAsString`
      - add new columns only; never rename or retype earlier ones
   2. **Generate the source** from a real Studio-saved `.msapp` template (PKG-04). Never write `Header.json`, `Properties.json` or `References/*` by hand.
   3. **Pack:** `pac canvas pack`, then add the app to the solution, then `pac solution pack`. Add `<CanvasApps>` to `Customizations.xml` yourself (PKG-02), and bump the version (PKG-03).
   4. **Verify** (below) until there are 0 FAIL.
   5. **Hand over** using the template at the end, including the exact SharePoint columns to add for this slice.
   6. **Wait** for the user's import, App checker result and acceptance test before starting the next slice. Never batch slices.
4. **Keep a slice log** (for example `plans/<app>-slices.md`): status, version, test result, and any changes the user made in Studio, so they can be copied back into the source before the next build.

## Verify before every delivery

If you can run Python:
```bash
python3 scripts/verify_package.py <solution.zip> \
  --previous-version <last version the user imported> \
  --schema lists.json --docs <docs folder> --src <unpacked canvas src> --pac "pac"
# add --tenant-fields <folder of per-list CSV exports> once the user has sent them
```

If the user is running it on Windows instead, it's `scripts/Verify-PowerAppsPackage.ps1 -Zip <zip> [-PreviousVersion] [-Schema] [-TenantFields] [-Docs]`. That script has the same check IDs but hasn't been run on Windows yet. If its output looks wrong, fall back to the Python script.

How to read the report:
- **FAIL:** don't deliver. Fix it and run the check again.
- **WARN:** fix it, or explain to the user why it's fine.
- **MANUAL:** confirm it yourself and say which ones you confirmed in the handover.

You can't open Power Apps, so never claim a package works in Studio.

## Rules to apply while generating (summary; details and causes in `references/build-rules.md`)

- **Import route:** solution zip, imported at **Solutions → Import solution**, not unzipped. Never send the user to *Import canvas app*.
- **Control properties:** only set properties the control template has. No `AccessibleLabel` on classic buttons. Prefer a Dropdown to a Combo box. No template defaults pointing at `Value1`.
- **Screens:** every screen has Width `App.Width`, Height `App.Height`, plus Size and Orientation, and `App.SizeBreakpoints` is set.
- **Theme:** no EditorState files when packing. Inputs need Fill and labels need Color.
- **Galleries:** every gallery has an explicit `Layout`.
- **Attachments:** an attachments control outside a form needs `DisplayMode.Edit`, `IsInDataCard = true` and `Items = []`.
- **`!` precedence:** write `!(a = b)`, never `!a = b`.
- **Paired controls:** numbered sets (…1 / …2) refer only to their own set.
- **Delegation:** SharePoint filters can be delegated. No functions applied to columns inside `Filter`/`LookUp`.
- **Environment variables:** every site and list is bound to environment variables that ship with no value. No hard-coded tenant URLs.
- **Flow link:** the app's flow source matches the solution's workflow ID and is listed in `CdsDependencies`.
- **Flow actions:** no `HttpRequest`, premium or custom connectors. Flows never set list columns (`item/...`); the app sets them with `Patch`.
- **Flow behaviour:** no `REPLACE_…` placeholders. Actions the app waits on that aren't SharePoint get retry None and a timeout. Always respond to the app, including on failure.
- **Save buttons:** save logic sits on a visible button, wrapped in `IfError`, and always clears its busy state.
- **Blank data:** rows with blank metadata (files added straight in SharePoint) still show.

## Diagnosing

Match the user's exact message against the **Seen:** lines in `references/build-rules.md`:

| User sees | Rule |
|---|---|
| "manifest file could not be found" | PKG-01 |
| "Cannot add a Root Component … type 300" | PKG-02 |
| `ErrOpeningDocument_UnknownError` | PKG-04 |
| Blank screens | APP-03 |
| Black controls | APP-04 |
| Lists running sideways | APP-05 |
| "No file selected" | APP-06 |
| `Value1` errors | APP-02 |
| Flow has no `Run` | APP-13 |
| `item/…` parameter error | FLOW-02 |
| "Advanced Connector Policy … HttpRequest" | FLOW-01 |
| Stuck on "Saving…" | FLOW-05, and the hidden-button note in section B |
| Hundreds of errors after import | SP-01 / SP-03 / APP-14 |

If nothing matches and the error has no detail, build a small diagnostic solution with several tiny apps that each change one thing, rather than guessing. Ask for App checker errors as control + property + message.

Before asking the user to rebuild SharePoint lists, prove the app itself works with a demo build that uses collections filled from sample data instead of SharePoint (SP-03).

## Handover template

> **Built:** slice <n> of <total>, `<Name>_<version>_unmanaged.zip`.
> **SharePoint changes for this slice:** <columns to add: internal name, type, choices>.
> **Acceptance test:** <steps and expected result>.
> **Checks:** passed `verify_package.py` with 0 FAIL. WARN items: … MANUAL items confirmed: …
> **Not tested:** not opened in Power Apps.
> **After import:**
> 1. Pick the connections.
> 2. Fill in the environment variables.
> 3. Turn the flows on.
> 4. Refresh every data source in Studio.
> 5. Re-add the flow if `Run` is missing.
> 6. App checker shows 0 errors, then Save and Publish.
>
> **Re-import warning:** a re-import overwrites any changes made in Studio, so send me those first.
> **If something fails:** send the exact message (control + property + message).
