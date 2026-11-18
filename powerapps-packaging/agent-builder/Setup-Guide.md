# Power Apps Builder agent: setup guide (Microsoft 365 Copilot Agent Builder)

This agent takes you from a rough idea to a tested Power Apps app:

**Grill → Spec → Slice → Build → Test**, repeating Build and Test for each slice until the app is complete.

- **Instructions** hold the phase map and the rules for moving between phases.
- **Knowledge** holds one document per phase, which works like a skill, plus the build rules and a project-state template.

## What's in this kit

| File | Where it goes |
|---|---|
| `Instructions.txt` | Paste into the agent's **Instructions** box |
| `knowledge/Phase 1 - Grill.docx` | Knowledge |
| `knowledge/Phase 2 - Spec.docx` | Knowledge |
| `knowledge/Phase 3 - Slice.docx` | Knowledge |
| `knowledge/Phase 4 - Build.docx` | Knowledge |
| `knowledge/Phase 5 - Test.docx` | Knowledge |
| `knowledge/PowerApps Build Rules.docx` | Knowledge |
| `knowledge/Project State Template.docx` | Knowledge |
| `Verify-PowerAppsPackage.ps1` | Your PC (the agent can't run code) |
| `.md` copies of everything | Your own reference or editing; upload the `.docx` versions to the agent |

## Before you start: check the cost

- **You have a Microsoft 365 Copilot license** (the paid add-on): Agent Builder agents are included at no extra cost.
- **You only have the free Copilot Chat:** an agent that uses uploaded or SharePoint knowledge is billed per message, via Copilot Studio pay-as-you-go. Ask IT before building it. If it's metered, use the **Notebook** method at the end instead.

Microsoft changes this often, so confirm with IT. If **Create agent** isn't available, your admin has turned it off.

## Step 1: Store the files

You have two options for knowledge:

| | Upload files into the agent | Point at a OneDrive/SharePoint folder |
|---|---|---|
| Updates | Static: to change a file, delete and re-upload it | Live: edit the Word doc and the agent sees the change |
| Sharing with coworkers | They get the agent with the files built in | They also need access to the folder |
| Cost on free Copilot Chat | Metered | Metered |

**Recommended:** upload the files. It's simplest and the agent always has exactly these versions. When I send updated documents, delete the old file in the agent and upload the new one.

Also make a OneDrive folder called `Power Apps Projects`, with one subfolder per app. Keep each app's spec, `lists.json`, slice plan and project state there, and attach them to chats as needed. Don't upload them as agent knowledge, or every app would mix together.

## Step 2: Create the agent

1. Open Microsoft 365 Copilot (m365copilot.com, or the Copilot app in Teams/Windows).
2. In the left pane, click **Agents → Create agent** (it may say **New agent**).
3. Click the **Configure** tab. The Describe tab writes instructions for you, so skip it.
4. **Name:** `Power Apps Builder`.
5. **Description:** `Takes a Power Apps idea through grilling, spec, vertical slices, build and testing, using my build rules.`
6. **Instructions:** paste the whole of `Instructions.txt`. It's about 3,900 characters, under the commonly cited 8,000 limit.
7. **Knowledge:** click **Upload** (or the paperclip) and add all 7 `.docx` files from the `knowledge` folder.
   - Turn off web search, if offered, so the agent only uses your documents. Microsoft's general Power Apps advice sometimes contradicts the rules, for example "Import canvas app".
8. **Capabilities:** leave Code interpreter and image generation off for now (see the optional section below).
9. **Conversation starters:** add these:

   | Title | Message |
   |---|---|
   | New idea | `I have a new app idea. Start Phase 1 - Grill.` |
   | I have a spec | `I have a spec written elsewhere (attached). Check it against Phase 2, ask only about gaps, then slice it.` |
   | Continue my app | `Here is my PROJECT STATE (attached). Continue from the next step.` |
   | Verify report | `Here is my Verify-PowerAppsPackage report (attached). Go through every FAIL and WARN.` |
   | Import / App checker error | `I got this error: <paste exact message>. Which rule is it and how do I fix it?` |

10. Click **Create**. Keep it private (only you), or share it with specific people if coworkers will use it.

## Step 3: Test the agent

Before relying on it, run these four checks:

1. **"Which documents do you have?"** It should list the seven documents.
2. **"I have a new app idea: tracking forklift inspections."** It should say `[Phase 1 - Grill …]` and ask **one** question with a recommended answer.
3. **"Skip to building the whole app now."** It should refuse to skip the gates, and offer to grill or take a spec.
4. **Attach a real Verify report** (or paste a few lines, for example `FAIL APP-06 attDoc: outside a form…`). It should explain the failure and give the exact fix.

If it misses documents or ignores phases, check that all files uploaded fully (wait until indexing finishes), then retry. Retrieval can be patchy, so the Instructions tell it to name the document for each phase.

## How you use it

1. **Idea:** start with **New idea**, then answer the grill questions. Save the summary.
2. **Spec:** approve the spec, then save the spec and `lists.json` to your app's OneDrive folder.
3. **Slices:** approve the slice plan and save it.
4. **For each slice:**
   1. Create the SharePoint columns.
   2. Save the source files.
   3. Run `pac canvas pack` and `pac solution pack`.
   4. Run `Verify-PowerAppsPackage.ps1` and attach the report.
   5. Import, then run App checker and the acceptance test.
   6. Paste back any errors or results.
5. **End of every chat:** save the PROJECT STATE block. Start the next chat with **Continue my app**, and attach it with the spec and slice plan.
6. **Done:** after the last slice the agent runs the completion checklist and writes a release note.

**One chat per slice keeps answers sharp.** Long chats make Copilot lose detail, which is why the PROJECT STATE exists.

## Optional: try Code interpreter for the checker

Agent Builder has a **Code interpreter** capability that runs Python inside Copilot. It might be able to run the Python checker on a zip you attach, which would save running PowerShell. This is untested:

1. In the agent's **Configure → Capabilities**, turn on **Code interpreter**.
2. Add `verify_package.py` to knowledge. If `.py` files are refused, rename it `verify_package.txt`.
3. In a chat, attach your solution zip and ask: *"Use Code interpreter to run verify_package.py on the attached zip and show the full output."*

If it refuses or can't read the zip, keep using the PowerShell script.

## No Agent Builder, or it's metered? Use a Notebook

1. In Copilot, go to **Notebooks → New notebook** and name it `Power Apps Builder`.
2. Add the 7 `.docx` files as **references**.
3. Paste `Instructions.txt` into the notebook's instructions setting, if your version has one. If not, paste it as the first message of each chat in the notebook.
4. Use the same conversation-starter messages as prompts.

It's the same process, without creating an agent.
