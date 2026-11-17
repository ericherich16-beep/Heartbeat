# Using the Power Apps build rules in Copilot Chat

Everything here works in the normal Microsoft 365 Copilot Chat window. You don't need an agent, Copilot Studio or any other model.

**You need:**
- `PowerApps-Build-Rules.md`, the rules and checks
- `Verify-PowerAppsPackage.ps1`, which runs the checks on your PC (Copilot Chat can't run code)
- this guide

## 1. Start every chat the same way

1. Start a new chat and attach `PowerApps-Build-Rules.md`.
   - If Copilot won't take `.md` files, rename it to `.txt`, or open it in Word and save it as `.docx`.
2. Paste the starter prompt below and send it. Copilot replies **Ready**.

Copilot forgets between chats, so repeat this every time.

### Starter prompt

```text
You are helping me build a Power Apps canvas app and package it as an importable solution (.zip) for SharePoint data. I've attached PowerApps-Build-Rules.md. It lists problems from my earlier builds, each with a rule and a check ID (PKG, APP, SP, FLOW, DOC, RUN).

How to work with me:
1. Follow every rule in the file. If something I ask for breaks a rule, say which rule and suggest the safe option.
2. When you write app source (.pa.yaml / .fx.yaml), formulas, flow JSON or setup steps, run the "AI check" items from the file on your own output before you give it to me. List each check ID you ran with PASS or FIX.
3. You can't run code. When a check needs a file or a command, tell me exactly what to run or paste. Usually that's Verify-PowerAppsPackage.ps1 on my PC, or pac canvas unpack.
4. When I paste a Verify-PowerAppsPackage report, go through every FAIL and WARN. For each one, explain what it means, then give the exact fix and where to make it (source file, Studio property, SharePoint list or flow).
5. Never say a package is ready while the report has a FAIL. Tell me plainly what hasn't been tested in Power Apps.
6. Keep answers short and in steps. Use exact control names, property names and menu paths.

Reply "Ready". Then ask me for the app spec, or for the report or error I'm working on.
```

## 2. Run the checker on each solution zip

1. Put `Verify-PowerAppsPackage.ps1` in the same folder as the zip.
2. In File Explorer, click that folder's address bar, type `powershell`, and press Enter.
3. Run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\Verify-PowerAppsPackage.ps1 -Zip .\<YourSolution>.zip
   ```
4. Attach or paste the `<name>.verify.txt` report into the chat, using prompt 3 below.

Optional extras:

| Option | Checks |
|---|---|
| `-PreviousVersion 1.0.2.0` | The version was bumped |
| `-Schema .\lists.json` | The app's list definitions match your design |
| `-TenantFields .\exports` | Your real lists match (one CSV per list, see prompt 5) |
| `-Docs .\docs` | README / POST_IMPORT cover every step |

The script only reads the zip. It changes nothing and sends nothing anywhere. If Windows blocks it, right-click the `.ps1` → **Properties** → tick **Unblock**.

**Self-test first.** Run it once on `JQCPWIManagement_1_0_7_0_unmanaged.zip`. You should see 4 **FAIL APP-02** lines, one for each of `cmbAssignDoc`, `cmbAssignEmp`, `cmbDocTrainers` and `cmbEmpSup` ("refers to sample column 'Value1'"), plus PASS for PKG-01, PKG-02, FLOW-01 to FLOW-03 and APP-03 to APP-07. If you get a PowerShell error instead, send it to Claude to fix. The script couldn't be run on Windows when it was written.

## 3. Prompts to copy

**1. Check a spec before building**
```text
Here is my app spec. Before we build, check it against SP-01 and SP-02 (every list and column has an internal name with no spaces, a SharePoint type, and says list or library), FLOW-01 (no blocked or premium actions), FLOW-02 (flows don't set list columns) and APP-09 (filters can be delegated). Then write lists.json for it.
<paste spec>
```

**2. Check generated source or formulas**
```text
Run the AI checks APP-01, 02, 03, 05, 06, 07, 08, 09, 10 and 11 on this source. List every problem with the control name, the property and the fixed text. If there are none, say PASS for each ID.
<paste one screen's .pa.yaml / .fx.yaml, or the formulas>
```
To get source from a built app, run `pac canvas unpack --msapp <app>.msapp --sources src` and paste one file from `src\Src` at a time.

**3. Read the checker report**
```text
Here is the Verify-PowerAppsPackage report. For each FAIL, then each WARN: say what it means in one line, then give the exact fix and where to make it. Tell me whether I need a new zip or can fix it in Studio. Then list the MANUAL items I still have to confirm.
<paste or attach the .verify.txt>
```

**4. An import error or App checker error**
```text
Importing / opening the app gave this. Find the rule ID that matches, the cause, and the fix. If no rule matches, tell me the smallest test that would narrow it down.
<exact message; for App checker: control name + property + message>
```

**5. Compare my SharePoint lists to the spec**
```text
Here is lists.json and the field export for list <name>. Check SP-01, SP-02 and SP-03: missing columns, wrong types, field_N internal names, duplicate display names, and whether it is a list or a library (a library has FileLeafRef). Give me the fix steps in SharePoint.
<paste lists.json>
<paste the CSV>
```
Export the CSV with PnP PowerShell: `Get-PnPField -List "<name>" | Select InternalName,Title,TypeAsString | Export-Csv "<name>.csv" -NoTypeInformation`. Without PnP, list each column's name and type from **List settings** instead.

**6. Write the post-import steps**
```text
Write POST_IMPORT.md for this solution, covering every DOC-01 step, in order, with exact menu paths:
<app name, flows, connection references, environment variables, lists>
```

**7. Before a re-import**
```text
I'm about to import a new version. Remind me of RUN-02: what Studio changes will be overwritten, and what I have to redo after the import. Can this fix be done in Studio instead?
<describe the change>
```

## 4. Optional: make it a Copilot agent

You don't need this. An agent only saves you attaching the file and pasting the starter prompt each time.

- **With a Microsoft 365 Copilot license:** Agent Builder agents are included at no extra cost.
- **With only the free Copilot Chat:** an agent that reads files from your organisation (SharePoint/OneDrive) is billed per message. Stay with the chat method in that case.

Microsoft changes this often, so check with IT.

**Steps:**
1. **Copilot Chat → Agents → Create agent → Configure.**
2. **Name:** *Power Apps Package Builder*.
3. **Instructions:** paste the starter prompt above, with steps 1–6 only.
4. **Knowledge:** upload `PowerApps-Build-Rules.md`.
