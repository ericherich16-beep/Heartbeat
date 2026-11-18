# Phase 4 - Build

**Goal:** everything the user needs to produce, import and test **one** slice. You write the files and steps; the user runs them on their PC. Follow **PowerApps Build Rules** throughout.

## One-time setup (before slice 1)

Check the user has each of these. If not, give them the steps:

1. **pac CLI:** the VS Code **Power Platform Tools** extension, or the Power Platform CLI MSI, or `dotnet tool install --global Microsoft.PowerApps.CLI.Tool`. Check it with `pac --version`.
2. **Project folder** on their PC:
   ```
   <App>\
     spec\                spec, lists.json, slice plan, project state
     template\            a Studio-saved .msapp, unpacked (see step 3)
     src\                 the app source you generate
     solution\            pac solution project
     dist\                built zips
     Verify-PowerAppsPackage.ps1
   ```
3. **A real template (PKG-04):**
   1. In Power Apps, create a blank **Tablet** canvas app in the target environment and save it.
   2. Download it as a `.msapp` from Studio: **Save as → This computer** or **Download a copy** (the label varies by Studio version). Don't use **Export package**, which produces a different zip.
   3. Run `pac canvas unpack --msapp template.msapp --sources template`.
   4. Generate only screens and formulas on top of this. Never write `Header.json`, `Properties.json` or `References` by hand.
   5. Delete `template\Src\EditorState\*` (APP-04).
4. **Solution project:**
   1. Run `pac solution init --publisher-name <name> --publisher-prefix <prefix>`.
   2. Add the `<CanvasApps>` section to `Other\Customizations.xml` (PKG-02).

## Each slice: what you give the user

Give these in this order, with exact file names:

1. **SharePoint changes:** a table of columns to add (internal name, type, required, choices, indexed), and the updated `lists.json`. Remind the user to type the exact internal name when creating each column, and never to create lists from Excel (SP-01).
2. **Source:** the full content of each new or changed source file (`src\Src\<Screen>.fx.yaml`, App formulas). For changes, give the whole file, not fragments. Before showing it, run the AI checks APP-01 to APP-11 and list them as PASS or FIX. Key reminders:
   - Every screen has `Width = App.Width` and `Height = App.Height`, plus `Size` and `Orientation` (APP-03).
   - Every gallery has `Layout` (APP-05).
   - Attachments controls outside a form have `DisplayMode.Edit`, `IsInDataCard = true` and `Items = []` (APP-06).
   - Use `!(a = b)`, never `!a = b` (APP-07).
   - No `AccessibleLabel` on classic buttons. Prefer a Dropdown to a Combo box (APP-01 / APP-02).
   - Save logic sits on the visible button, wrapped in `IfError`, and always clears its busy state.
3. **Flow** (if the slice has one): the flow definition, or click-by-click steps.
   - **Retry policy** None and **Timeout** PT1M on actions that aren't SharePoint (FLOW-05).
   - Respond to the app on failure too (FLOW-06).
   - The flow doesn't set list columns (FLOW-02).
4. **Pack commands:**
   ```powershell
   pac canvas pack --sources src --msapp dist\<App>.msapp
   # copy the .msapp into solution\src\CanvasApps\ and update the version in solution\src\Other\Solution.xml
   pac solution pack --zipfile dist\<App>_<version>_unmanaged.zip --folder solution\src --packagetype Unmanaged
   ```
   Bump the version on every build (PKG-03).
5. **Verify command:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\Verify-PowerAppsPackage.ps1 -Zip .\dist\<zip> -PreviousVersion <last> -Schema .\spec\lists.json
   ```
   Ask the user to paste the report, then fix every FAIL before they import.
6. **Post-import steps for this slice (DOC-01):**
   1. **Solutions → Import solution** (don't unzip).
   2. Pick the connections, and fill in the environment variables on the first import.
   3. Turn the flows on.
   4. Open the app, then **Data → each list → ⋯ → Refresh**.
   5. If `Run` is missing, re-add the flow.
   6. App checker must show 0 errors, then Save and Publish.
7. **The acceptance test** from the slice plan.

## If building a solution zip isn't possible

For example, pac isn't allowed on their PC. Fall back to paste-in-Studio:
- Give each screen as `.pa.yaml` to paste in Studio, plus the formulas per property.
- The user builds the solution in Power Apps. The rules still apply.

## Before re-importing (RUN-02)

Ask whether the user changed anything in Studio since the last zip. If they did, put those changes into the source first, because a re-import overwrites them.

## Finish

Output a PROJECT STATE with Phase: Build, Current slice: n, Version: x. Then move to Phase 5 - Test.
