# 1.6.0.0: Increment 2b, upload / replace / remove (R10, R11, U4, U5)
**Status:** Built, not opened. Includes 1.5.0.0, so do the 1.4.0.0 and 1.5.0.0 SharePoint steps first.
**Risk:** this is the first package with **two pieces never opened in the tenant**: the `Attachments@2.3.0` file picker in YAML, and a **new flow** (`NPIUploadFile`). **Import `history/uploadtest/EricP_NPIUploadTest_1_0_0_0.zip` first** (see below). If 1.6.0.0 won't open, go back to 1.5.0.0, which has neither piece.

## SharePoint prerequisites
1. **NPIProjectFiles library:** add these columns with these exact internal names. They stamp each file. If they're missing, the file still saves and the app warns "could not be stamped".

   | Column | Type |
   |---|---|
   | ProjectID | Single line of text |
   | RequirementID | Single line of text |
   | Gate | Number |
   | FormNumber | Single line of text |
   | FormSection | Single line of text |
   | UploadedBy | Person |
   | UploadedDate | Date and time |
2. **Confirm versioning is on** in NPIProjectFiles (Library settings → Versioning: major versions, no limit if possible). Replace depends on it to keep history (R11, decision 21).
3. Nothing else. The `_Removed` folder is created automatically in each project folder the first time a file is removed.

## Order to test (do this first)
1. Import **`EricP_NPIUploadTest_1_0_0_0.zip`** as a new solution. When asked, pick your SharePoint connection for "NPI SharePoint Connection Reference".
2. **Turn on the NPIUploadFile flow:** Solutions → NPI Upload Test → Cloud flows → NPIUploadFile → Turn on.
3. Open **NPI Upload Test**.
   - **If it won't open:** the file-picker type is wrong. In any app, insert an Edit form on a list that has attachments, select its Attachments control, right-click → **View code**, and send me the `Control:` line. Stay on 1.5.0.0.
   - **If it opens:** paste a test project's folder URL (the ProjectFolderUrl column in NPI Projects), choose a small PDF, and select **Run upload**.
     - `success: true` with a fileurl: everything works. Go to step 4.
     - "Flow call failed" or a flow error: open NPIUploadFile run history and read the first red action. If the app says the flow isn't found, in Studio go to **Power Automate (left bar) → remove NPIUploadFile → Add flow → NPIUploadFile**, then save and publish.
4. Import **1.6.0.0** as an Update into NPI Tracker. Open it and check NPIUploadFile is on. If Studio shows the flow as broken, remove and re-add it in the app as in step 3.

## Changes
- **PDF area in the panel:** pick a PDF, then **Upload**. The NPIUploadFile flow:
  - saves it in the project folder
  - stamps the library columns, including the real uploader by email
  - returns the link, which the app saves on the row (FileLink, FileName, FileItemId, UploadedBy = you, UploadedDate)
- **Replace** (when a file is already linked) uploads the new content as a **new version of the same file**. The name is kept and history is preserved.
- **Remove file** (red link): you must give a reason. The file moves to `<project folder>/_Removed` and the row's link is cleared. Done or Reviewed goes back to Draft.
- **Duplicate names:** if another row in the project already uses the same name, or a file with that name is already in the folder, the name gets the requirement ID in front (decision on naming). No forced naming otherwise.
- **U4:** a new file on a **Reviewed** row sets it back to **Done** (it needs review again). A new file on **Not started** sets it to **Draft**.
- **Upload is closed once the gate is signed:** the picker and buttons are disabled, and the label says so.
- **Submit for review now needs a linked PDF** (`varPdfRequired = true`).
- Every upload, replace and remove writes an Activity Log entry (Upload / Replace / Remove, with the file name and reason).
- PDF only: other file types are refused with a message.

## Known limits
- Very large files (tens of MB) go through Power Apps as text and can be slow or time out. Normal signed PDFs are fine.
- Everyone can upload, replace and remove for now (decision). Every action is logged.
