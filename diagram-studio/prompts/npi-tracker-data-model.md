# NPI Tracker data model: prompts for Diagram Studio

Paste these into Diagram Studio's command bar one at a time, in order, with the speed set to **Smart**.
Wait for each to finish before sending the next. Each one builds on the page the previous one made.

Source: `ericherich16-beep/powerapps-factory`, `projects/npi-tracker/` (`schema.yaml`, the two flows in
`flows/`, and the solution export in `base/`), plus the NPI notes on Heartbeat branch `ccr-5cf98041-quun6m`
(`npi-tracker/SETUP_CHECKLIST.md`, `INCREMENT6_CONFIG_CONTROL.md`).

## Prompt 1: page and core tables

```text
Add a new page called "NPI Tracker data model". Build the SharePoint data model for my NPI Tracker Power Apps solution: each SharePoint list or library is one table. Use the column internal names exactly as written, use the SharePoint column type as the field type, and put choice values in the field's examples. Mark ID as the primary key on every table.
Table NPI Projects (blue), description "One row per NPI project: a part number and revision going through gates 1 to 4." Fields: ID id; Title text, required, unique, description "Project ID in the form NPI-0001, set by the create flow"; PartNumber text, required; Revision text, required; PartRevKey text, unique, description "PARTNUMBER|REVISION upper-cased, blocks duplicate projects"; Customer text; ProjectType choice, examples "New Part, Revision"; QE person, description "Quality engineer who owns the project"; CurrentGate number, default 1, examples "1-4"; ProjectFolderUrl text, description "Project folder in NPIProjectFiles"; PreviousProject lookup, description "Earlier project for a revision (lookup to NPI Projects), written only by the create flow"; ProjectStatus choice, default Open, examples "Open, Closed"; Gate1SignedBy, Gate2SignedBy, Gate3SignedBy, Gate4SignedBy person; Gate1SignedDate, Gate2SignedDate, Gate3SignedDate, Gate4SignedDate datetime; CloseDate datetime; RetentionUntil datetime; Created datetime; Modified datetime.
Table Project Requirements (blue), description "One row per required document or sign-off on a project, copied from Gate Requirements when the project is created." Fields: ID id; Title text, unique, description "Requirement key, e.g. NPI-0001-G1-001"; ProjectID text, required, foreign key; Gate number, examples "1-4"; SortOrder number; Form text; Section text; RequirementType choice, examples "Draft uploaded, Section complete, Signed (entire doc), Sent to customer, Customer signed, If required (N/A + reason)"; Role choice, examples "QE, QM, Tech, Quality, Metrology, PM"; ReqLevel choice, examples "Required, If required"; IndependentReview boolean, description "Reviewer must not be the uploader"; IsGateDoc boolean; Assignee person; DueDate datetime; Status choice, default "Not started", examples "Not started, Draft, Done, Reviewed, N/A"; NAReason text; ReviewedBy person; ReviewedDate datetime; UploadedBy person; UploadedDate datetime; FileLink text; FileItemId number; FileName text.
```

## Prompt 2: configuration, questions, audit and libraries

```text
On this page add six more tables, using the same conventions (ID id primary key, internal names, SharePoint types, choices in examples).
Gate Requirements (amber), description "Configuration: master list of requirements per gate, copied into Project Requirements for each new project. Edited only by the QM; changes apply to new projects only." Fields: ID id; Title text; Gate number; SortOrder number; Form text; Section text; RequirementType choice, Role choice and ReqLevel choice with the same values as Project Requirements; IndependentReview boolean; IsGateDoc boolean; Active boolean, default yes, description "Retire a row by setting No instead of deleting it"; ChangeReason text, required; ApprovedBy person, required.
NPI Role Defaults (amber), description "Configuration: default assignee for each role." Fields: ID id; Title text; Role choice, unique, examples "QE, QM, Tech, Quality, Metrology, PM"; DefaultAssignee person, required.
NPI Open Questions (purple), description "Open questions and actions raised on a project at a gate." Fields: ID id; Title text, required, description "The question or action"; ProjectID text, required, foreign key; Gate number, required, examples "1-4"; Owner person; DueDate datetime; QStatus choice, default Open, examples "Open, Closed"; Resolution text; GateMoveReason text, description "Last reason the question's gate was changed"; Created datetime.
NPI Activity Log (grey), description "Audit trail: one row per action taken in the app or flows." Fields: ID id; Title text; ProjectID text, foreign key; RequirementID text, foreign key; ActionType choice, examples "Upload, Replace, Remove, Status change, N/A, Reassign, Due date, Gate signed, Question added, Question closed, Question moved"; Detail text; Reason text; FileName text; PerformedBy person; PerformedDate datetime.
NPIProjectFiles (green), description "Document library: one folder per project. Only the NPIUploadFile flow writes to it." Fields: ID id; FileLeafRef text, description "File name"; ProjectID text, foreign key; RequirementID text, foreign key; Gate number; FormNumber text; FormSection text; UploadedBy person; UploadedDate datetime.
NPIFormTemplates (green), description "Document library of blank form templates that the create flow copies into each new project folder." Fields: ID id; FileLeafRef text, description "Template file name".
```

## Prompt 3: relationships, notes and layout

```text
Connect the tables on this page. These links are text keys, not lookup columns. Many-to-one, start 0N and end 11: Project Requirements.ProjectID to NPI Projects.Title; NPI Open Questions.ProjectID to NPI Projects.Title; NPI Activity Log.ProjectID to NPI Projects.Title; NPIProjectFiles.ProjectID to NPI Projects.Title. Zero-or-more to zero-or-one, start 0N and end 01: NPI Activity Log.RequirementID to Project Requirements.Title; NPIProjectFiles.RequirementID to Project Requirements.Title. Then two dashed lines with no crow's feet (start none, end arrow): from Gate Requirements to Project Requirements labelled "copied at project creation", and from NPI Role Defaults.Role to Project Requirements.Role labelled "default Assignee by Role".
Set the page notes to: "SharePoint site MTCExpansionPlanning. Power Apps canvas app with screens scrProjects (project list) and scrProjectDetail (gates, requirements, questions), plus two Power Automate flows: NPICreateProject creates the NPI Projects row and its NPI-0001 ID, blocks duplicate part/revision pairs, creates the project folder in NPIProjectFiles, copies NPIFormTemplates into it, and copies active Gate Requirements rows into Project Requirements with assignees from NPI Role Defaults; NPIUploadFile uploads, replaces or removes a requirement's file in the project folder, stamps its metadata and returns the file link. Lists link by text keys (ProjectID = NPI Projects.Title, RequirementID = Project Requirements.Title) rather than lookup columns, except PreviousProject. Field names are SharePoint internal names. Gates are signed in order 1 to 4; signing Gate 4 closes the project and sets RetentionUntil."
Finally tidy the layout: NPI Projects in the middle, Project Requirements, NPI Open Questions and NPI Activity Log around it, Gate Requirements and NPI Role Defaults on the left, NPIProjectFiles and NPIFormTemplates on the right.
```

## Inferred, check before relying on it

- `RequirementID` (Activity Log, NPIProjectFiles) is assumed to hold the requirement's Title key
  (`NPI-0001-G1-001`), not its numeric ID. The sources don't say which.
- Gate Requirements columns come from what NPICreateProject reads plus the config-control notes
  (Active, ChangeReason, ApprovedBy). The list isn't in `schema.yaml`.
- NPIFormTemplates and the `FileLeafRef` name column are standard SharePoint library columns, assumed.
- `PreviousProject` is a lookup back to NPI Projects. It is described rather than drawn, because the editor
  can't draw a line from a table to itself.
