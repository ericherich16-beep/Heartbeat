"""Generate the "JQCPWI - Upload File" flow (CLAUDE.md Section 11) into the main solution.

Writes:
  solution/JQCPWIManagement/src/Workflows/JQCPWI-UploadFile-<GUID>.json (+ .data.xml)
  the SharePoint connection reference in solution/JQCPWIManagement/src/Other/Customizations.xml
Then run `python3 solution/build.py` to pack the solution.

Only standard SharePoint actions are used: Create file, Update file, Get file properties,
Update file properties. Never "Send an HTTP request to SharePoint" (SPEC.md A-28).
Site and libraries come from the environment variables jp_SiteUrl, jp_LibDocuments, jp_LibSignoffs.
The build spec with every expression is flows/JQCPWI-UploadFile.md (generated from this file).

Usage
  python3 flows/build_flow.py
"""
import json
import os
import re
import shutil
import uuid
from xml.sax.saxutils import quoteattr

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(REPO, "solution", "JQCPWIManagement", "src")
NS = uuid.UUID("9b8f0d2e-4c61-4a7d-b2e3-7f05c1a9d6e4")
FLOW_NAME = "JQCPWI - Upload File"
FLOW_ID = str(uuid.uuid5(NS, "flow:upload-file"))
CONN_REF = "jp_sharepoint"
SP_API = "/providers/Microsoft.PowerApps/apis/shared_sharepointonline"

# Flow parameters bound to the solution's environment variables (no default values stored).
P_SITE = "JQC/PWI - SharePoint site (jp_SiteUrl)"
P_DOCS = "JQC/PWI - JP_Documents library (jp_LibDocuments)"
P_SIGN = "JQC/PWI - JP_SignoffRecords library (jp_LibSignoffs)"
ENV_PARAMS = [(P_SITE, "jp_SiteUrl"), (P_DOCS, "jp_LibDocuments"), (P_SIGN, "jp_LibSignoffs")]

# Library URL folders. These are the library names from the schema (CLAUDE.md Section 6), identical
# on every site; Create file needs a folder path, not a list ID (SPEC.md A-31).
FOLDER_DOCS = "/JP_Documents"
FOLDER_SIGN = "/JP_SignoffRecords"
ALLOWED_EXT = ["pdf", "docx", "xlsx", "jpg", "jpeg", "png"]
MAX_BYTES = 26214400   # 25 MB (CLAUDE.md Section 7 rule 6)

SITE = f"@parameters('{P_SITE}')"
META = "outputs('Metadata')"
FILE = "triggerBody()?['file']"


def meta(name):
    return {"operationMetadataId": str(uuid.uuid5(NS, "op:" + name))}


def sp(name, op, params, run_after=None):
    return {"type": "OpenApiConnection", "runAfter": run_after or {}, "metadata": meta(name),
            "inputs": {"host": {"apiId": SP_API, "operationId": op, "connectionName": "shared_sharepointonline"},
                       "parameters": params}}


def compose(name, value, run_after=None):
    return {"type": "Compose", "runAfter": run_after or {}, "metadata": meta(name), "inputs": value}


def respond(name, success, item_id, url, message, run_after):
    return {"type": "Response", "kind": "PowerApp", "runAfter": run_after, "metadata": meta(name),
            "inputs": {"statusCode": 200,
                       "body": {"success": success, "itemid": item_id, "fileurl": url, "message": message},
                       "schema": {"type": "object", "properties": {
                           "success": {"title": "success", "x-ms-dynamically-added": True, "type": "string"},
                           "itemid": {"title": "itemid", "x-ms-dynamically-added": True, "type": "number"},
                           "fileurl": {"title": "fileurl", "x-ms-dynamically-added": True, "type": "string"},
                           "message": {"title": "message", "x-ms-dynamically-added": True, "type": "string"}}}}}


def definition():
    acts = {}
    acts["Metadata"] = compose(
        "Metadata", "@json(if(empty(triggerBody()?['text_1']), '{}', triggerBody()?['text_1']))")
    acts["Extension"] = compose(
        "Extension", f"@toLower(last(split({FILE}?['name'], '.')))", {"Metadata": ["Succeeded"]})
    acts["Initialize_ItemId"] = {"type": "InitializeVariable", "runAfter": {"Extension": ["Succeeded"]},
                                 "metadata": meta("Initialize_ItemId"),
                                 "inputs": {"variables": [{"name": "ItemId", "type": "integer", "value": 0}]}}
    # ---- validation (the app checks too; this is the back-stop) ----
    valid = {"and": [
        {"or": [{"equals": ["@triggerBody()?['text']", "Documents"]},
                {"equals": ["@triggerBody()?['text']", "Signoffs"]}]},
        {"contains": [f"@createArray({', '.join(repr(e) for e in ALLOWED_EXT)})", "@outputs('Extension')"]},
        {"lessOrEquals": [f"@div(mul(length(string({FILE}?['contentBytes'])), 3), 4)", MAX_BYTES]},
    ]}
    acts["Is_valid"] = {
        "type": "If", "runAfter": {"Initialize_ItemId": ["Succeeded"]}, "metadata": meta("Is_valid"),
        "expression": valid,
        "actions": {},
        "else": {"actions": {
            "Respond_invalid": respond("Respond_invalid", "false", 0, "",
                                       "File rejected: use PDF, DOCX, XLSX, JPG or PNG, up to 25 MB.", {}),
            "Stop_invalid": {"type": "Terminate", "runAfter": {"Respond_invalid": ["Succeeded"]},
                             "metadata": meta("Stop_invalid"), "inputs": {"runStatus": "Cancelled"}}}}}

    is_docs = "@equals(triggerBody()?['text'], 'Documents')"
    library = f"@if(equals(triggerBody()?['text'], 'Documents'), parameters('{P_DOCS}'), parameters('{P_SIGN}'))"
    folder = f"@if(equals(triggerBody()?['text'], 'Documents'), '{FOLDER_DOCS}', '{FOLDER_SIGN}')"
    file_name = f"@{{coalesce({META}?['FileName'], {FILE}?['name'])}}"
    content = f"@base64ToBinary({FILE}?['contentBytes'])"

    t = {}
    t["Library_ID"] = compose("Library_ID", library)
    t["New_or_replace"] = {
        "type": "If", "runAfter": {"Library_ID": ["Succeeded"]}, "metadata": meta("New_or_replace"),
        "expression": {"and": [{"greater": ["@triggerBody()?['number']", 0]}]},
        # Existing item: replace the content in place (same item ID, old file kept in version history).
        "actions": {
            "Get_existing_file": sp("Get_existing_file", "GetFileItem",
                                    {"dataset": SITE, "table": "@outputs('Library_ID')", "id": "@triggerBody()?['number']"}),
            "Update_file": sp("Update_file", "UpdateFile",
                              {"dataset": SITE, "id": "@body('Get_existing_file')?['{Identifier}']", "body": content},
                              {"Get_existing_file": ["Succeeded"]}),
            "Set_ItemId_existing": {"type": "SetVariable", "runAfter": {"Update_file": ["Succeeded"]},
                                    "metadata": meta("Set_ItemId_existing"),
                                    "inputs": {"name": "ItemId", "value": "@int(triggerBody()?['number'])"}}},
        "else": {"actions": {
            "Create_file": sp("Create_file", "CreateFile",
                              {"dataset": SITE, "folderPath": folder, "name": file_name, "body": content}),
            "Set_ItemId_new": {"type": "SetVariable",
                               "runAfter": {"Create_file": ["Succeeded"]},
                               "metadata": meta("Set_ItemId_new"),
                               "inputs": {"name": "ItemId",
                                          "value": "@int(body('Create_file')?['ItemId'])"}}}}}
    # Column values are NOT set here: "Update file properties" names each column, and Power Automate
    # validates those names against the real library when the flow is saved, so any naming
    # difference stops the flow from turning on. The app sets the columns with Patch after the
    # upload instead (SPEC.md A-38). MetadataJson is only used for the file name.
    t["Get_file_link"] = sp("Get_file_link", "GetFileItem",
                            {"dataset": SITE, "table": "@outputs('Library_ID')", "id": "@variables('ItemId')"},
                            {"New_or_replace": ["Succeeded"]})
    t["Respond_success"] = respond("Respond_success", "true", "@variables('ItemId')",
                                   "@{body('Get_file_link')?['{Link}']}", "Uploaded.", {"Get_file_link": ["Succeeded"]})
    acts["Try"] = {"type": "Scope", "runAfter": {"Is_valid": ["Succeeded"]}, "metadata": meta("Try"), "actions": t}
    acts["Failed_steps"] = {"type": "Query", "runAfter": {"Try": ["Failed", "TimedOut"]}, "metadata": meta("Failed_steps"),
                            "inputs": {"from": "@result('Try')", "where": "@equals(item()?['status'], 'Failed')"}}
    acts["Respond_failure"] = respond(
        "Respond_failure", "false", "@variables('ItemId')", "",
        "@{concat('Upload failed: ', coalesce(first(body('Failed_steps'))?['error']?['message'], 'see the flow run history.'))}",
        {"Failed_steps": ["Succeeded"]})
    return acts


def flow_json():
    params = {"$connections": {"defaultValue": {}, "type": "Object"},
              "$authentication": {"defaultValue": {}, "type": "SecureObject"}}
    for title, schema in ENV_PARAMS:
        params[title] = {"defaultValue": "", "type": "String", "metadata": {"schemaName": schema}}
    trigger = {"manual": {
        "type": "Request", "kind": "PowerAppV2", "metadata": meta("manual"),
        "inputs": {"schema": {
            "type": "object",
            "properties": {
                "file": {"title": "File", "type": "object", "x-ms-dynamically-added": True, "x-ms-content-hint": "FILE",
                         "description": "The file to upload (Attachments control: First(att.Attachments)).",
                         "properties": {"name": {"type": "string"}, "contentBytes": {"type": "string", "format": "byte"}}},
                "text": {"title": "TargetLibrary", "type": "string", "x-ms-dynamically-added": True,
                         "x-ms-content-hint": "TEXT", "description": "Documents or Signoffs"},
                "number": {"title": "ExistingItemID", "type": "number", "x-ms-dynamically-added": True,
                           "x-ms-content-hint": "NUMBER",
                           "description": "0 = create a new file. Otherwise the item ID whose content is replaced (new revision)."},
                "text_1": {"title": "MetadataJson", "type": "string", "x-ms-dynamically-added": True,
                           "x-ms-content-hint": "TEXT", "description": "JSON with the file name and column values."}},
            "required": ["file", "text", "number", "text_1"]}}}}
    # Connection runs as the app user ("invoker"): SharePoint permissions apply and Created By is the user.
    conn = {"shared_sharepointonline": {"runtimeSource": "invoker",
                                        "connection": {"connectionReferenceLogicalName": CONN_REF},
                                        "api": {"name": "shared_sharepointonline"}}}
    return {"properties": {"connectionReferences": conn, "definition": {
        "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
        "contentVersion": "1.0.0.0", "parameters": params, "triggers": trigger, "actions": definition(), "outputs": {}},
        "templateName": ""}, "schemaVersion": "1.0.0.0"}


def write():
    wf = os.path.join(SRC, "Workflows")
    if os.path.isdir(wf):
        shutil.rmtree(wf)
    os.makedirs(wf)
    base = "JQCPWI-UploadFile-" + FLOW_ID.upper()
    json.dump(flow_json(), open(os.path.join(wf, base + ".json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(os.path.join(wf, base + ".json.data.xml"), "w", encoding="utf-8").write(f"""<?xml version="1.0" encoding="utf-8"?>
<Workflow WorkflowId="{{{FLOW_ID}}}" Name={quoteattr(FLOW_NAME)} xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <JsonFileName>/Workflows/{base}.json</JsonFileName>
  <Type>1</Type>
  <Subprocess>0</Subprocess>
  <Category>5</Category>
  <Mode>0</Mode>
  <Scope>4</Scope>
  <OnDemand>0</OnDemand>
  <TriggerOnCreate>0</TriggerOnCreate>
  <TriggerOnDelete>0</TriggerOnDelete>
  <AsyncAutodelete>0</AsyncAutodelete>
  <SyncWorkflowLogOnFailure>0</SyncWorkflowLogOnFailure>
  <StateCode>1</StateCode>
  <StatusCode>2</StatusCode>
  <RunAs>1</RunAs>
  <IsTransacted>1</IsTransacted>
  <IntroducedVersion>1.0</IntroducedVersion>
  <IsCustomizable>1</IsCustomizable>
  <IsCustomProcessingStepAllowedForOtherPublishers>1</IsCustomProcessingStepAllowedForOtherPublishers>
  <PrimaryEntity>none</PrimaryEntity>
  <LocalizedNames>
    <LocalizedName languagecode="1033" description={quoteattr(FLOW_NAME)} />
  </LocalizedNames>
  <Descriptions>
    <Description languagecode="1033" description={quoteattr("Uploads JQC/PWI documents and sign-off evidence from the app to SharePoint (new file or new revision in place) and sets the file's columns.")} />
  </Descriptions>
</Workflow>
""")
    cpath = os.path.join(SRC, "Other", "Customizations.xml")
    xml = open(cpath, encoding="utf-8-sig").read()
    xml = re.sub(r"\s*<connectionreferences>.*?</connectionreferences>", "", xml, flags=re.S)
    xml = xml.replace("  <Languages>", f"""  <connectionreferences>
    <connectionreference connectionreferencelogicalname="{CONN_REF}">
      <connectionreferencedisplayname>JQC/PWI - SharePoint</connectionreferencedisplayname>
      <connectorid>{SP_API}</connectorid>
      <iscustomizable>1</iscustomizable>
      <statecode>0</statecode>
      <statuscode>1</statuscode>
    </connectionreference>
  </connectionreferences>
  <Languages>""", 1)
    open(cpath, "w", encoding="utf-8").write(xml)
    print("Wrote flow", FLOW_NAME, FLOW_ID, "and connection reference", CONN_REF)


def write_doc():
    d = flow_json()["properties"]["definition"]
    md = [f"# {FLOW_NAME} — build spec", "",
          "> **Generated by `flows/build_flow.py`. Don't edit by hand.** The flow is already included in the solution",
          "> (`solution/JQCPWIManagement/src/Workflows/`). This file documents every step and expression, so the flow can",
          "> be reviewed or rebuilt by hand if needed.", "",
          "## Purpose", "",
          "Canvas apps can't write files to a document library, so the app calls this instant flow (CLAUDE.md Section 11).",
          "- A **new file** (JQC template, PWI, signed JQC or training log): **Create file**.",
          "- A **new revision**: **Update file** replaces the content of the existing item in place, so the item ID stays the",
          "  same and library versioning keeps the old revision.",
          "- The flow does **not** set the file's columns. The app does that with `Patch` once the upload returns the item ID",
          "  (SPEC.md A-38). That keeps the flow independent of the libraries' column names.",
          "- It responds with `success`, `itemid`, `fileurl` and `message`.", "",
          "Only standard SharePoint actions are used. **\"Send an HTTP request to SharePoint\" is never used**: it's blocked",
          "by the tenant's data policy (SPEC.md A-28).", "",
          "## Connection and environment variables", "",
          f"- **Connection reference:** `{CONN_REF}` (SharePoint). It runs as the **app user**, so SharePoint permissions apply",
          "  and *Created By* is the person who uploaded.",
          "- **Flow parameters** bound to the solution's environment variables. No default values are stored:", "",
          "| Parameter | Environment variable | Used for |", "|---|---|---|",
          f"| `{P_SITE}` | `jp_SiteUrl` | Site address in every action |",
          f"| `{P_DOCS}` | `jp_LibDocuments` | Library ID for JQC templates and PWIs |",
          f"| `{P_SIGN}` | `jp_LibSignoffs` | Library ID for sign-off evidence |", "",
          f"**Create file** needs a folder path, not an ID. The paths are the fixed library names from the schema:",
          f"`{FOLDER_DOCS}` and `{FOLDER_SIGN}` (SPEC.md A-31).", "",
          "## Trigger: Power Apps (V2)", "",
          "| Input | Key | Type | Value |", "|---|---|---|---|",
          "| File | `file` | File | `{name, contentBytes}` from an Attachments control |",
          "| TargetLibrary | `text` | Text | `Documents` or `Signoffs` |",
          "| ExistingItemID | `number` | Number | `0` = new file. Otherwise the JP_Documents item ID whose content is replaced (new revision) |",
          "| MetadataJson | `text_1` | Text | JSON with the file name and column values (below) |", "",
          "`ExistingItemID` is required, with `0` meaning \"new file\". This avoids optional-parameter syntax in the app.", "",
          "### MetadataJson", "",
          "Only `FileName` is used by the flow. The other fields are optional context and are ignored.", "",
          "**Documents** (JQC templates and PWIs):", "",
          "```json",
          '{ "FileName": "PWI-DEMO-001.pdf", "DocType": "PWI", "DocNumber": "PWI-DEMO-001", "DocTitle": "Demo Widget Torque Check",',
          '  "Revision": "B", "RevisionDate": "2026-11-04", "RevisionNotes": "What changed", "Area": "Production",',
          '  "Status": "Active", "Trainers": [{"Claims": "techa@contoso.com"}], "Description": "" }',
          "```", "",
          "**Signoffs** (signed JQCs and PWI training logs). The file name follows CLAUDE.md Section 6.4, with the time added so it's unique:", "",
          "```json",
          '{ "FileName": "PWI-DEMO-001_RevB_3_20261104_141502.pdf", "AssignmentID": 42, "DocType": "PWI",',
          '  "Revision": "B", "EmployeeEmail": "techa@contoso.com", "UploadedBy": "techa@contoso.com" }',
          "```", "",
          "### Calling it from the app (used in build step 5)", "",
          "```powerfx",
          "// att = the Attachments control; varMeta = a record with the fields above",
          "Set(gblUpload, 'JQCPWI-UploadFile'.Run(",
          "    {name: First(att.Attachments).Name, contentBytes: First(att.Attachments).Value},",
          '    "Signoffs",',
          "    0,",
          "    JSON(varMeta)",
          "));",
          'If(gblUpload.success = "true", /* Patch the assignment with SignoffFileID = gblUpload.itemid */ true,',
          "   Notify(gblUpload.message, NotificationType.Error))",
          "```", "",
          "## Validation (back-stop for the app's own checks)", "",
          f"- TargetLibrary is `Documents` or `Signoffs`.",
          f"- The extension is one of {', '.join(ALLOWED_EXT)}.",
          f"- The size is at most {MAX_BYTES:,} bytes (25 MB), estimated from the base64 length.",
          "- Otherwise the flow responds `success = \"false\"` with a plain-language message and stops.", "",
          "## Steps", ""]

    def dump(acts, depth):
        for n, a in acts.items():
            pad = "  " * depth
            op = a.get("inputs", {}).get("host", {}).get("operationId", "") if isinstance(a.get("inputs"), dict) else ""
            after = ", ".join(f"{k} ({'/'.join(v)})" for k, v in a.get("runAfter", {}).items()) or "start"
            md.append(f"{pad}- **{n}** — {a['type']}{' `' + op + '`' if op else ''} — runs after: {after}")
            if a["type"] in ("OpenApiConnection", "Compose", "SetVariable", "Query", "InitializeVariable"):
                body = a["inputs"]["parameters"] if a["type"] == "OpenApiConnection" else a["inputs"]
                md.append(f"{pad}  ```json")
                md.extend(pad + "  " + l for l in json.dumps(body, indent=2).split("\n"))
                md.append(f"{pad}  ```")
            if a["type"] == "If":
                md.append(f"{pad}  Condition: `{json.dumps(a['expression'])}`")
                md.append(f"{pad}  - *If yes:*")
                dump(a["actions"], depth + 2)
                md.append(f"{pad}  - *If no:*")
                dump(a["else"]["actions"], depth + 2)
            if a["type"] == "Scope":
                dump(a["actions"], depth + 1)
            if a["type"] == "Response":
                md.append(f"{pad}  Body: `{json.dumps(a['inputs']['body'])}`")
    dump(d["actions"], 0)
    open(os.path.join(HERE, "JQCPWI-UploadFile.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("Wrote flows/JQCPWI-UploadFile.md")


if __name__ == "__main__":
    write()
    write_doc()
