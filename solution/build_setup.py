"""Build the JQC/PWI *Setup* solution: one flow that creates the SharePoint lists.

Why a separate solution
  The main solution's environment variables point at the JP_ lists, so the lists
  must exist before it is imported. This small solution has no environment
  variables. Import it, run its flow once with your site address, then import the
  main solution.

The flow: "JQCPWI - Setup SharePoint Lists" (instant / manual trigger)
  Input: SharePoint site address (for example https://contoso.sharepoint.com/sites/JQCPWI)
  Uses only the standard SharePoint connector ("Send an HTTP request to SharePoint"),
  and runs as the person who runs it. That person needs Site Owner (Full Control)
  on the site.
    Phase A  create the 5 lists/libraries, turn on versioning, rename Title columns
    Phase B  create every column (lookups use the JP_Employees list ID), then
             add indexes and unique constraints
    Phase C  create the single JP_Settings row if the list is empty
    Phase D  report the list IDs (for the environment variables)
  Every request is logged. Already-existing lists and columns are reported but not
  treated as errors, so it is safe to run again. Nothing is ever deleted.
  At the end the run fails with a clear message if any real error happened. The
  "Summary" action shows every step's result.

Schema source: CLAUDE.md Section 6 / SPEC.md Section 3. It must stay in step with
provisioning/Create-Lists.ps1. check_ps_schema() warns if the column names differ.

Usage
  PAC="python3 /path/to/pac.py" python3 solution/build_setup.py
"""
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import uuid
from xml.sax.saxutils import escape, quoteattr

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PROJECT = os.path.join(HERE, "JQCPWISetup")
SRC = os.path.join(PROJECT, "src")
DIST = os.path.join(HERE, "dist")
MAIN_SOLUTION_XML = os.path.join(HERE, "JQCPWIManagement", "src", "Other", "Solution.xml")

UNIQUE_NAME = "JQCPWISetup"
DISPLAY_NAME = "JQC/PWI Management - Setup"
DESCRIPTION = ("One-time setup for JQC/PWI Management: a flow that creates the JP_ SharePoint "
               "lists and libraries on a site you choose. Import and run this before the main solution.")
VERSION = "1.0.0.0"
FLOW_NAME = "JQCPWI - Setup SharePoint Lists"
NS = uuid.UUID("6f1c7b52-3a8e-4f0e-9a51-0c2d7e4b9a10")      # fixed namespace -> stable IDs across builds
FLOW_ID = str(uuid.uuid5(NS, "flow:setup-sharepoint-lists"))
CONN_REF = "jp_sharepointsetup"
SP_API = "/providers/Microsoft.PowerApps/apis/shared_sharepointonline"

# ---------------------------------------------------------------------------
# Schema (mirror of provisioning/Create-Lists.ps1)
# ---------------------------------------------------------------------------
SHIFT = ["1st", "2nd", "3rd", "Days"]
DEPT = ["Production", "Quality", "Other"]
DOCTYPE = ["JQC", "PWI"]

def F(name, display, ftype, **kw):
    d = {"Name": name, "Display": display, "Type": ftype}
    d.update(kw)
    return d

LISTS = [
    {"Title": "JP_Employees", "Template": 100,
     "Description": "JQC/PWI Management - employees. Never delete; set Active = No.",
     "Fields": [
         F("Email", "Email", "Text", Required=True, Indexed=True, Unique=True),
         F("EmployeeUser", "Employee User", "User"),
         F("JobTitle", "Job Title", "Choice", Required=True,
           Choices=["Production Technician", "Quality Technician", "Supervisor", "Manager", "Other"]),
         F("Department", "Department", "Choice", Indexed=True, Choices=DEPT),
         F("Shift", "Shift", "Choice", Indexed=True, Choices=SHIFT),
         F("Supervisor", "Supervisor", "Lookup", Indexed=True),
         F("AppRole", "App Role", "Choice", Required=True,
           Choices=["Manager/Supervisor", "Technician", "Viewer"], Default="Technician"),
         F("Active", "Active", "Boolean", Indexed=True, Default="1"),
     ]},
    {"Title": "JP_Documents", "Template": 101, "Versioning": True,
     "Description": "JQC/PWI Management - JQC templates and PWIs. One item per document; new revisions replace the file in place.",
     "Fields": [
         F("DocType", "Doc Type", "Choice", Indexed=True, Choices=DOCTYPE),
         F("DocNumber", "Doc Number", "Text", Indexed=True, Unique=True),
         F("DocTitle", "Doc Title", "Text"),
         F("Revision", "Revision", "Text"),
         F("RevisionDate", "Revision Date", "DateOnly"),
         F("RevisionNotes", "Revision Notes", "Note"),
         F("Area", "Area", "Choice", Indexed=True, Choices=["Production", "Quality", "Metrology", "Other"]),
         F("Status", "Status", "Choice", Indexed=True, Choices=["Active", "Obsolete"], Default="Active"),
         F("Trainers", "Trainers", "UserMulti"),
         F("Description", "Description", "Note"),
     ]},
    {"Title": "JP_Assignments", "Template": 100,
     "Description": "JQC/PWI Management - one row per employee per document revision. Never delete; use Removed or Superseded.",
     "Fields": [
         F("Employee", "Employee", "Lookup", Required=True),
         F("EmployeeEmail", "Employee Email", "Text", Required=True, Indexed=True),
         F("DocumentID", "Document ID", "Number", Required=True, Indexed=True),
         F("DocType", "Doc Type", "Choice", Required=True, Indexed=True, Choices=DOCTYPE),
         F("DocNumber", "Doc Number", "Text", Required=True),
         F("DocTitle", "Doc Title", "Text", Required=True),
         F("RevisionAssigned", "Revision Assigned", "Text", Required=True),
         F("AssignmentReason", "Assignment Reason", "Choice", Required=True,
           Choices=["New Assignment", "Revision Change"], Default="New Assignment"),
         F("PreviousAssignmentID", "Previous Assignment ID", "Number"),
         F("IsCurrent", "Is Current", "Boolean", Indexed=True, Default="1"),
         F("AssignedBy", "Assigned By", "User", Required=True),
         F("AssignedDate", "Assigned Date", "DateOnly", Required=True),
         F("DueDate", "Due Date", "DateOnly"),
         F("Trainer", "Trainer", "User"),
         F("Status", "Status", "Choice", Required=True, Indexed=True,
           Choices=["Assigned", "In Training", "Signed Off", "Superseded", "Removed"], Default="Assigned"),
         F("SignedOffBy", "Signed Off By", "User"),
         F("SignedOffDate", "Signed Off Date", "DateTime"),
         F("SignoffFileID", "Sign-off File ID", "Number"),
         F("Comments", "Comments", "Note"),
     ]},
    {"Title": "JP_SignoffRecords", "Template": 101, "Versioning": True,
     "Description": "JQC/PWI Management - signed JQCs and PWI training logs. Never delete.",
     "Fields": [
         F("AssignmentID", "Assignment ID", "Number", Indexed=True),
         F("DocType", "Doc Type", "Choice", Choices=DOCTYPE),
         F("Revision", "Revision", "Text"),
         F("EmployeeEmail", "Employee Email", "Text", Indexed=True),
         F("UploadedBy", "Uploaded By", "User"),
     ]},
    {"Title": "JP_Settings", "Template": 100,
     "Description": "JQC/PWI Management - global settings. Keep exactly one row.",
     "Fields": [
         # TODO: confirm defaults (CLAUDE.md Section 19)
         F("MinQualifiedPerTask", "Min Qualified Per Task", "Number", Required=True, Default="2", Min=1),
         F("ResignDueDays", "Re-sign Due Days", "Number", Required=True, Default="14", Min=1),
     ]},
]
SETTINGS_ROW = {"Title": "Settings", "MinQualifiedPerTask": 2, "ResignDueDays": 14}  # TODO: confirm defaults
EMP_PLACEHOLDER = "__JP_EMPLOYEES_LIST_ID__"

# ---------------------------------------------------------------------------
# SharePoint REST step builders
# ---------------------------------------------------------------------------
VERBOSE = {"Accept": "application/json;odata=verbose", "Content-Type": "application/json;odata=verbose"}
MERGE = dict(VERBOSE, **{"X-HTTP-Method": "MERGE", "IF-MATCH": "*"})


def q(title):
    return "_api/web/lists/getbytitle('" + title + "')"


def step(label, uri, body, headers=None, method="POST"):
    return {"label": label, "method": method, "uri": uri,
            "headers": headers or VERBOSE, "body": json.dumps(body, ensure_ascii=False)}


def field_xml(lst, f):
    is_library = lst["Template"] == 101
    req = "TRUE" if (f.get("Required") and not is_library) else "FALSE"   # SPEC.md A-21
    a = (f'Name="{f["Name"]}" StaticName="{f["Name"]}" DisplayName="{f["Name"]}" '   # display = internal (A-27)
         f'Required="{req}"')
    t = f["Type"]
    inner = ""
    if t == "Text":
        x = f'<Field Type="Text" {a} MaxLength="255"'
    elif t == "Note":
        x = f'<Field Type="Note" {a} NumLines="6" RichText="FALSE"'
    elif t == "Number":
        x = f'<Field Type="Number" {a} Decimals="0"' + (f' Min="{f["Min"]}"' if "Min" in f else "")
    elif t == "Boolean":
        x = f'<Field Type="Boolean" {a}'
    elif t == "DateOnly":
        x = f'<Field Type="DateTime" {a} Format="DateOnly"'
    elif t == "DateTime":
        x = f'<Field Type="DateTime" {a} Format="DateTime"'
    elif t == "User":
        x = f'<Field Type="User" {a} UserSelectionMode="PeopleOnly" UserSelectionScope="0" ShowField="ImnName"'
    elif t == "UserMulti":
        x = f'<Field Type="UserMulti" {a} Mult="TRUE" UserSelectionMode="PeopleOnly" UserSelectionScope="0" ShowField="ImnName"'
    elif t == "Choice":
        x = f'<Field Type="Choice" {a} Format="Dropdown" FillInChoice="FALSE"'
        inner = "<CHOICES>" + "".join(f"<CHOICE>{escape(c)}</CHOICE>" for c in f["Choices"]) + "</CHOICES>"
    elif t == "Lookup":
        x = f'<Field Type="Lookup" {a} List="{{{EMP_PLACEHOLDER}}}" ShowField="Title"'
    else:
        raise ValueError(t)
    if "Default" in f:
        inner += f"<Default>{escape(f['Default'])}</Default>"
    return x + (f">{inner}</Field>" if inner else " />")


def phase_a():
    steps = []
    for lst in LISTS:
        steps.append(step(f"Create {lst['Title']}", "_api/web/lists",
                          {"__metadata": {"type": "SP.List"}, "Title": lst["Title"],
                           "BaseTemplate": lst["Template"], "Description": lst["Description"],
                           "AllowContentTypes": True, "ContentTypesEnabled": False}))
        if lst.get("Versioning"):
            steps.append(step(f"Versioning on {lst['Title']}", q(lst["Title"]),
                              {"__metadata": {"type": "SP.List"}, "EnableVersioning": True,
                               "MajorVersionLimit": 50}, MERGE))
    return steps


def phase_b():
    create, index, unique = [], [], []
    for lst in LISTS:
        for f in lst["Fields"]:
            create.append(step(f"Column {lst['Title']}.{f['Name']}", q(lst["Title"]) + "/fields/createfieldasxml",
                               {"parameters": {"__metadata": {"type": "SP.XmlSchemaFieldCreationInformation"},
                                               "SchemaXml": field_xml(lst, f),
                                               "Options": 24}}))   # 8 = use Name as internal name, 16 = add to default view
            fu = q(lst["Title"]) + f"/fields/getbyinternalnameortitle('{f['Name']}')"
            if f.get("Indexed") or f.get("Unique"):
                index.append(step(f"Index {lst['Title']}.{f['Name']}", fu,
                                  {"__metadata": {"type": "SP.Field"}, "Indexed": True}, MERGE))
            if f.get("Unique"):
                unique.append(step(f"Unique {lst['Title']}.{f['Name']}", fu,
                                   {"__metadata": {"type": "SP.Field"}, "EnforceUniqueValues": True}, MERGE))
    return create + index + unique   # unique must come after index


# ---------------------------------------------------------------------------
# Flow definition
# ---------------------------------------------------------------------------
def meta(name):
    return {"operationMetadataId": str(uuid.uuid5(NS, "op:" + name))}


def http(name, method, uri, headers, body=None, run_after=None):
    params = {"dataset": "@{trim(triggerBody()['text'])}", "parameters/method": method,
              "parameters/uri": uri, "parameters/headers": headers}
    if body is not None:
        params["parameters/body"] = body
    return {"type": "OpenApiConnection", "runAfter": run_after or {}, "metadata": meta(name),
            "inputs": {"host": {"apiId": SP_API, "operationId": "HttpRequest",
                                "connectionName": "shared_sharepointonline"},
                       "parameters": params}}


def log_entry(send_action, label_expr):
    return {"step": label_expr,
            "status": f"@outputs('{send_action}')?['statusCode']",
            "error": f"@coalesce(body('{send_action}')?['error']?['message']?['value'], body('{send_action}')?['odata.error']?['message']?['value'], '')"}


def loop(name, items_action, send_name, body_expr, run_after):
    return {
        "type": "Foreach", "foreach": f"@outputs('{items_action}')", "runAfter": run_after,
        "runtimeConfiguration": {"concurrency": {"repetitions": 1}},   # one request at a time, in order
        "metadata": meta(name),
        "actions": {
            send_name: http(send_name, "@item()?['method']", "@item()?['uri']", "@item()?['headers']", body_expr),
            "Log_" + send_name: {
                "type": "AppendToArrayVariable", "runAfter": {send_name: ["Succeeded", "Failed"]},
                "metadata": meta("Log_" + send_name),
                "inputs": {"name": "Log", "value": log_entry(send_name, "@item()?['label']")}},
        }}


def any_status(prev):
    return {prev: ["Succeeded", "Failed", "Skipped", "TimedOut"]}


def flow_definition():
    acts = {}
    acts["Check_site_address"] = {
        "type": "If", "runAfter": {}, "metadata": meta("Check_site_address"),
        "expression": {"and": [{"not": {"startsWith": ["@toLower(trim(triggerBody()['text']))", "https://"]}}]},
        "actions": {"Stop_bad_address": {"type": "Terminate", "runAfter": {}, "metadata": meta("Stop_bad_address"),
                                         "inputs": {"runStatus": "Failed", "runError": {
                                             "code": "BadSiteAddress",
                                             "message": "Enter the full site address, starting with https:// (for example https://contoso.sharepoint.com/sites/JQCPWI)."}}}},
        "else": {"actions": {}}}
    acts["Initialize_Log"] = {"type": "InitializeVariable", "runAfter": {"Check_site_address": ["Succeeded"]},
                              "metadata": meta("Initialize_Log"),
                              "inputs": {"variables": [{"name": "Log", "type": "array", "value": []}]}}
    acts["Phase_A_steps"] = {"type": "Compose", "runAfter": {"Initialize_Log": ["Succeeded"]},
                             "metadata": meta("Phase_A_steps"), "inputs": phase_a()}
    acts["Phase_A_create_lists"] = loop("Phase_A_create_lists", "Phase_A_steps", "Send_A",
                                        "@item()?['body']", {"Phase_A_steps": ["Succeeded"]})
    acts["Get_Employees_list_ID"] = http("Get_Employees_list_ID", "GET", q("JP_Employees") + "?$select=Id",
                                         VERBOSE, None, any_status("Phase_A_create_lists"))
    acts["Employees_list_ID"] = {"type": "Compose", "runAfter": {"Get_Employees_list_ID": ["Succeeded"]},
                                 "metadata": meta("Employees_list_ID"),
                                 "inputs": "@body('Get_Employees_list_ID')?['d']?['Id']"}
    acts["Phase_B_steps"] = {"type": "Compose", "runAfter": {"Employees_list_ID": ["Succeeded"]},
                             "metadata": meta("Phase_B_steps"), "inputs": phase_b()}
    acts["Phase_B_create_columns"] = loop(
        "Phase_B_create_columns", "Phase_B_steps", "Send_B",
        f"@replace(item()?['body'], '{EMP_PLACEHOLDER}', string(outputs('Employees_list_ID')))",
        {"Phase_B_steps": ["Succeeded"]})
    # Phase C: settings row
    acts["Get_settings_rows"] = http("Get_settings_rows", "GET",
                                     q("JP_Settings") + "/items?$select=Id&$top=5", VERBOSE, None,
                                     any_status("Phase_B_create_columns"))
    acts["Settings_list_empty"] = {
        "type": "If", "runAfter": {"Get_settings_rows": ["Succeeded"]}, "metadata": meta("Settings_list_empty"),
        "expression": {"and": [{"equals": ["@length(body('Get_settings_rows')?['d']?['results'])", 0]}]},
        "actions": {
            "Get_settings_item_type": http("Get_settings_item_type", "GET",
                                           q("JP_Settings") + "?$select=ListItemEntityTypeFullName", VERBOSE),
            "Create_settings_row": http(
                "Create_settings_row", "POST", q("JP_Settings") + "/items", VERBOSE,
                "@{concat('{\"__metadata\":{\"type\":\"', body('Get_settings_item_type')?['d']?['ListItemEntityTypeFullName'], '\"},"
                + json.dumps(SETTINGS_ROW)[1:].replace("'", "''") + "')}",
                {"Get_settings_item_type": ["Succeeded"]}),
            "Log_settings_row": {"type": "AppendToArrayVariable",
                                 "runAfter": {"Create_settings_row": ["Succeeded", "Failed", "Skipped"]},
                                 "metadata": meta("Log_settings_row"),
                                 "inputs": {"name": "Log", "value": log_entry("Create_settings_row", "Create settings row")}},
        },
        "else": {"actions": {
            "Log_settings_exists": {"type": "AppendToArrayVariable", "runAfter": {}, "metadata": meta("Log_settings_exists"),
                                    "inputs": {"name": "Log", "value": {"step": "Settings row already exists (left unchanged)",
                                                                        "status": 200, "error": ""}}}}}}
    # Phase D: list IDs for the environment variables
    acts["Get_list_IDs"] = http("Get_list_IDs", "GET",
                                "_api/web/lists?$select=Title,Id&$filter=startswith(Title,'JP_')", VERBOSE, None,
                                any_status("Settings_list_empty"))
    acts["List_IDs"] = {"type": "Select", "runAfter": {"Get_list_IDs": ["Succeeded", "Failed"]},
                        "metadata": meta("List_IDs"),
                        "inputs": {"from": "@coalesce(body('Get_list_IDs')?['d']?['results'], json('[]'))",
                                   "select": {"List": "@item()?['Title']", "Id": "@item()?['Id']"}}}
    acts["Real_errors"] = {"type": "Query", "runAfter": {"List_IDs": ["Succeeded", "Failed", "Skipped"]},
                           "metadata": meta("Real_errors"),
                           "inputs": {"from": "@variables('Log')",
                                      "where": "@and(greaterOrEquals(int(coalesce(item()?['status'], 0)), 300), "
                                               "not(contains(toLower(string(item()?['error'])), 'already exists')), "
                                               "not(contains(toLower(string(item()?['error'])), 'duplicate')))"}}
    acts["Summary"] = {"type": "Compose", "runAfter": {"Real_errors": ["Succeeded"]}, "metadata": meta("Summary"),
                       "inputs": {"site": "@triggerBody()['text']",
                                  "realErrors": "@length(body('Real_errors'))",
                                  "errors": "@body('Real_errors')",
                                  "listIds": "@body('List_IDs')",
                                  "allSteps": "@variables('Log')"}}
    acts["Any_errors"] = {
        "type": "If", "runAfter": {"Summary": ["Succeeded"]}, "metadata": meta("Any_errors"),
        "expression": {"and": [{"greater": ["@length(body('Real_errors'))", 0]}]},
        "actions": {"Fail_with_errors": {"type": "Terminate", "runAfter": {}, "metadata": meta("Fail_with_errors"),
                                         "inputs": {"runStatus": "Failed", "runError": {
                                             "code": "SetupErrors",
                                             "message": "@{length(body('Real_errors'))} setup step(s) failed. Open the 'Summary' action in this run to see which ones and why."}}}},
        "else": {"actions": {}}}

    return {
        "properties": {
            "connectionReferences": {
                "shared_sharepointonline": {"runtimeSource": "invoker",
                                            "connection": {"connectionReferenceLogicalName": CONN_REF},
                                            "api": {"name": "shared_sharepointonline"}}},
            "definition": {
                "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
                "contentVersion": "1.0.0.0",
                "parameters": {"$connections": {"defaultValue": {}, "type": "Object"},
                               "$authentication": {"defaultValue": {}, "type": "SecureObject"}},
                "triggers": {"manual": {
                    "type": "Request", "kind": "Button", "metadata": meta("manual"),
                    "inputs": {"schema": {"type": "object", "required": ["text"], "properties": {
                        "text": {"title": "SharePoint site address", "type": "string",
                                 "x-ms-dynamically-added": True, "x-ms-content-hint": "TEXT",
                                 "description": "Full site address, e.g. https://contoso.sharepoint.com/sites/JQCPWI"}}}}}},
                "actions": acts,
                "outputs": {}},
            "templateName": ""},
        "schemaVersion": "1.0.0.0"}


# ---------------------------------------------------------------------------
# Solution files
# ---------------------------------------------------------------------------
def write_flow():
    wf = os.path.join(SRC, "Workflows")
    if os.path.isdir(wf):
        shutil.rmtree(wf)
    os.makedirs(wf)
    base = "JQCPWI-SetupSharePointLists-" + FLOW_ID.upper()
    with open(os.path.join(wf, base + ".json"), "w", encoding="utf-8") as f:
        json.dump(flow_definition(), f, indent=2, ensure_ascii=False)
    data = f"""<?xml version="1.0" encoding="utf-8"?>
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
    <Description languagecode="1033" description={quoteattr("Creates the JP_ SharePoint lists and libraries for JQC/PWI Management on the site you enter. Safe to run again.")} />
  </Descriptions>
</Workflow>
"""
    with open(os.path.join(wf, base + ".json.data.xml"), "w", encoding="utf-8") as f:
        f.write(data)


def write_customizations():
    path = os.path.join(SRC, "Other", "Customizations.xml")
    xml = open(path, encoding="utf-8-sig").read()
    xml = re.sub(r"\s*<connectionreferences>.*?</connectionreferences>", "", xml, flags=re.S)
    block = f"""  <connectionreferences>
    <connectionreference connectionreferencelogicalname="{CONN_REF}">
      <connectionreferencedisplayname>JQC/PWI Setup - SharePoint</connectionreferencedisplayname>
      <connectorid>{SP_API}</connectorid>
      <iscustomizable>1</iscustomizable>
      <statecode>0</statecode>
      <statuscode>1</statuscode>
    </connectionreference>
  </connectionreferences>
"""
    xml = xml.replace("  <Languages>", block + "  <Languages>", 1)
    open(path, "w", encoding="utf-8").write(xml)


def write_solution_xml():
    path = os.path.join(SRC, "Other", "Solution.xml")
    xml = open(path, encoding="utf-8-sig").read()
    # Same publisher as the main solution, including the option value prefix.
    main = open(MAIN_SOLUTION_XML, encoding="utf-8-sig").read()
    main_prefix = re.search(r"<CustomizationOptionValuePrefix>(\d+)<", main).group(1)
    xml = re.sub(r"<CustomizationOptionValuePrefix>\d+<", f"<CustomizationOptionValuePrefix>{main_prefix}<", xml)
    head, sep, pub = xml.partition("<Publisher>")
    head = re.sub(r'<LocalizedName description="[^"]*" languagecode="1033" />',
                  f"<LocalizedName description={quoteattr(DISPLAY_NAME)} languagecode=\"1033\" />", head, count=1)
    head = re.sub(r"<Descriptions\s*/>|<Descriptions>.*?</Descriptions>",
                  f"<Descriptions>\n      <Description description={quoteattr(DESCRIPTION)} languagecode=\"1033\" />\n    </Descriptions>",
                  head, count=1, flags=re.S)
    head = re.sub(r"<Version>[^<]*</Version>", f"<Version>{VERSION}</Version>", head, count=1)
    main_pub_name = re.search(r"<Publisher>.*?<LocalizedName description=\"([^\"]*)\"", main, re.S).group(1)
    pub = re.sub(r'<LocalizedName description="[^"]*" languagecode="1033" />',
                 f'<LocalizedName description="{main_pub_name}" languagecode="1033" />', pub, count=1)
    xml = head + sep + pub
    xml = re.sub(r"<RootComponents\s*/>|<RootComponents>.*?</RootComponents>",
                 f'<RootComponents>\n      <RootComponent type="29" id="{{{FLOW_ID}}}" behavior="0" />\n    </RootComponents>',
                 xml, count=1, flags=re.S)
    open(path, "w", encoding="utf-8").write(xml)


def check_ps_schema():
    """Warn if Create-Lists.ps1 and this file disagree on list/column names."""
    ps = open(os.path.join(REPO, "provisioning", "Create-Lists.ps1"), encoding="utf-8").read()
    ps_names = set(re.findall(r"@\{ Name = '(\w+)';", ps))
    py_names = {f["Name"] for l in LISTS for f in l["Fields"]}
    if ps_names != py_names:
        print("WARNING: column names differ from Create-Lists.ps1:",
              "only in PS:", sorted(ps_names - py_names), "only here:", sorted(py_names - ps_names))
    else:
        print(f"Schema matches Create-Lists.ps1 ({len(py_names)} distinct column names)")


def pack():
    pac = shlex.split(os.environ.get("PAC", "pac"))
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, f"{UNIQUE_NAME}_{VERSION.replace('.', '_')}_unmanaged.zip")
    if os.path.exists(out):
        os.remove(out)
    res = subprocess.run(pac + ["solution", "pack", "--zipfile", out, "--folder", SRC, "--packagetype", "Unmanaged"],
                         capture_output=True, text=True)
    print("\n".join(l for l in res.stdout.splitlines() if l.strip() and not l.startswith("Processing Component")))
    if res.returncode != 0 or not os.path.exists(out):
        sys.stderr.write(res.stderr)
        sys.exit("pac solution pack failed")
    print("Built:", os.path.relpath(out, REPO))


if __name__ == "__main__":
    check_ps_schema()
    write_flow()
    write_customizations()
    write_solution_xml()
    if "--no-pack" not in sys.argv:
        pack()
