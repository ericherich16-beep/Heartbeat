#!/usr/bin/env python3
"""Build EricP_NPIUploadTest: a one-screen canvas app plus the NPIUploadFile flow.

Purpose: prove the two unproven pieces of 1.6.0.0 (the Attachments@2.3.0 control in YAML and the
NPIUploadFile flow called with JSON(..., IncludeBinaryData)) before importing 1.6.0.0.
Usage: python3 -I build_uploadtest.py
"""
import datetime
import io
import json
import re
import sys
import uuid
import zipfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402

VERSION = "1.0.0.0"
APP = "ericp_npiuploadtest"
BASE = HERE / "base" / "tenant_export_1_2_0_1.zip"
OUT = HERE / "history" / "uploadtest"

APP_YAML = """App:
  Properties:
    OnStart: |-
      =Set(varRes, {success: false, message: "Not run yet.", fileurl: "", filename: "", itemid: 0, stamped: false})
    StartScreen: =scrTest
"""
SCREEN = """Screens:
  scrTest:
    Properties:
      Fill: =RGBA(244, 247, 251, 1)
    Children:
      - lblTestTitle:
          Control: Label@2.5.1
          Properties:
            FontWeight: =FontWeight.Bold
            Height: =40
            Size: =20
            Text: ="NPI upload test"
            Width: =600
            X: =24
            Y: =16
      - lblTestHelp:
          Control: Label@2.5.1
          Properties:
            Height: =60
            Size: =12
            Text: |-
              ="1. Paste a test project's ProjectFolderUrl from NPI Projects. 2. Choose a small PDF. 3. Select Run upload. The file should appear in that folder as TEST-REQ_<name> or <name>."
            Width: =900
            X: =24
            Y: =60
      - txtFolderUrl:
          Control: Classic/TextInput@2.3.2
          Properties:
            Default: =""
            Height: =40
            HintText: ="Project folder URL"
            Width: =900
            X: =24
            Y: =130
      - attTest:
          Control: Attachments@2.3.0
          Properties:
            AddAttachmentText: ="Choose a PDF"
            Height: =60
            MaxAttachments: =1
            NoAttachmentsText: ="No file chosen"
            Width: =500
            X: =24
            Y: =186
      - btnRunUpload:
          Control: Classic/Button@2.2.0
          Properties:
            DisplayMode: =If(CountRows(attTest.Attachments) = 1 && !IsBlank(Trim(txtFolderUrl.Text)), DisplayMode.Edit, DisplayMode.Disabled)
            Height: =40
            OnSelect: |-
              =Set(
                  varRes,
                  IfError(
                      NPIUploadFile.Run(
                          "upload",
                          Trim(txtFolderUrl.Text),
                          First(attTest.Attachments).Name,
                          JSON(First(attTest.Attachments).Value, JSONFormat.IncludeBinaryData),
                          "TEST",
                          "TEST-REQ",
                          "1",
                          "TEST",
                          "",
                          Lower(User().Email),
                          ""
                      ),
                      {success: false, message: "Flow call failed: " & FirstError.Message, fileurl: "", filename: "", itemid: 0, stamped: false}
                  )
              )
            Text: ="Run upload"
            Width: =160
            X: =24
            Y: =262
      - lblTestResult:
          Control: Label@2.5.1
          Properties:
            Height: =160
            Size: =12
            Text: |-
              ="success: " & varRes.success & Char(10) & "message: " & varRes.message & Char(10) &
              "filename: " & varRes.filename & Char(10) & "itemid: " & varRes.itemid & Char(10) &
              "stamped: " & varRes.stamped & Char(10) & "fileurl: " & varRes.fileurl
            VerticalAlign: =VerticalAlign.Top
            Width: =900
            X: =24
            Y: =320
      - lblOpenResult:
          Control: Label@2.5.1
          Properties:
            Color: =RGBA(10, 92, 178, 1)
            Height: =30
            OnSelect: =Launch(varRes.fileurl)
            Size: =12
            Text: ="Open uploaded file"
            Underline: =true
            Visible: =!IsBlank(varRes.fileurl)
            Width: =300
            X: =24
            Y: =486
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    flow = yaml.safe_load((HERE / "flows" / "NPIUploadFile" / "flow.yaml").read_text())
    build.FLOWS.add(flow["name"])
    build.ALLOWED["Attachments@2.3.0"] = {"AddAttachmentText", "Height", "MaxAttachments", "NoAttachmentsText",
                                          "Width", "X", "Y"}
    errs, n = build.validate(APP_YAML, {"Src\\scrTest.pa.yaml": SCREEN})
    if errs:
        sys.exit("\n".join(errs))
    print(f"upload test: validation passed, {n} controls")

    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    base = zipfile.ZipFile(BASE)
    msapp_name = next(x for x in base.namelist() if x.endswith("_DocumentUri.msapp"))
    old = zipfile.ZipFile(io.BytesIO(base.read(msapp_name)))
    ds = json.loads(old.read("References\\DataSources.json"))
    base_wadl = next(d for d in ds["DataSources"] if d["Name"] == "NPICreateProject")["WadlMetadata"]["WadlXml"]
    new_ds = {"DataSources": [{
        "ApiId": "/providers/microsoft.powerapps/apis/shared_logicflows", "FlowNameId": flow["guid"],
        "Name": flow["name"], "ServiceKind": "ConnectedWadl", "Type": "ServiceInfo",
        "WadlMetadata": {"WadlXml": build.flow_wadl(flow["name"], flow["inputs"], flow["outputs"], base_wadl)},
        "WorkflowEntityId": flow["guid"]}]}

    mbuf = io.BytesIO()
    with zipfile.ZipFile(mbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for info in old.infolist():
            n, data = info.filename, old.read(info.filename)
            if n in ("Src\\scrProjects.pa.yaml", "Src\\scrProjectDetail.pa.yaml"):
                continue
            if n == "Src\\App.pa.yaml":
                data = APP_YAML.encode()
            elif n == "Src\\_EditorState.pa.yaml":
                data = b"EditorState:\n  ScreensOrder:\n    - scrTest\n"
            elif n == "References\\DataSources.json":
                data = json.dumps(new_ds, indent=2).encode()
            elif n == "Properties.json":
                p = json.loads(data)
                p["Name"] = "NPI Upload Test"
                p["Id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, "npi-upload-test-app"))
                p["FileID"] = str(uuid.uuid5(uuid.NAMESPACE_URL, "npi-upload-test-file"))
                p["AppDescription"] = "Test app for the NPIUploadFile flow and attachments control."
                p["LocalConnectionReferences"] = "{}"
                p["ControlCount"] = build.count_types({"x": SCREEN})
                data = json.dumps(p, indent=2).encode()
            elif n == "packed.json":
                p = json.loads(data)
                p["LastPackedDateTimeUtc"] = iso
                p["PackingClient"]["Version"] = "uploadtest-" + VERSION
                data = json.dumps(p, indent=2).encode()
            elif n == "Resources\\PublishInfo.json":
                p = json.loads(data)
                p["AppName"] = "NPI Upload Test"
                data = json.dumps(p, indent=2).encode()
            z.writestr(zipfile.ZipInfo(n, date_time=now.timetuple()[:6]), data, zipfile.ZIP_DEFLATED)
            if n == "Src\\App.pa.yaml":
                z.writestr(zipfile.ZipInfo("Src\\scrTest.pa.yaml", date_time=now.timetuple()[:6]), SCREEN.encode(),
                           zipfile.ZIP_DEFLATED)

    cust = base.read("customizations.xml").decode("utf-8")
    canvas = re.search(r"<CanvasApp>.*?</CanvasApp>", cust, re.S).group(0)
    canvas = canvas.replace("ericp_npitracker_i1", APP)
    canvas = re.sub(r"<DisplayName>[^<]*</DisplayName>", "<DisplayName>NPI Upload Test</DisplayName>", canvas)
    canvas = re.sub(r"<Description>[^<]*</Description>", "<Description>Test for NPIUploadFile</Description>", canvas)
    canvas = re.sub(r"<AppVersion>[^<]*</AppVersion>", f"<AppVersion>{iso}</AppVersion>", canvas)
    cr = {flow["cr_key"]: {
        "id": "/providers/microsoft.powerapps/apis/shared_logicflows", "displayName": "Logic flows",
        "iconUri": "https://static.powerapps.com/resource/ppcr/releases/v1.0.1827/1.0.1827.4908/logicflows/icon.png",
        "dataSources": [flow["name"]], "dependencies": [], "dependents": [],
        "parameterHints": {"workflowName": {"value": flow["guid"]}, "workflowEntityId": {"value": flow["guid"]}},
        "parameterHintsV2": {"workflowName": {"value": flow["guid"]}, "workflowEntityId": {"value": flow["guid"]}},
        "isOnPremiseConnection": False, "bypassConsent": False, "dataSets": {}, "apiTier": "Standard",
        "actions": ["Run"]}}
    canvas = re.sub(r"<ConnectionReferences>.*?</ConnectionReferences>",
                    lambda _: "<ConnectionReferences>" + json.dumps(cr, separators=(",", ":")) + "</ConnectionReferences>",
                    canvas, flags=re.S)
    canvas = re.sub(r"<CdsDependencies>.*?</CdsDependencies>", lambda _: "<CdsDependencies>" + json.dumps(
        {"cdsdependencies": [{"componenttype": 29, "dependencyid": flow["guid"],
                              "componenttypeplatformname": "Workflow"}]}, separators=(",", ":")) + "</CdsDependencies>",
                    canvas, flags=re.S)
    wf = build.WORKFLOW_XML.format(guid=flow["guid"], GUID=flow["guid"].upper(), name=flow["name"], version=VERSION)
    spref = re.search(r'<connectionreference connectionreferencelogicalname="ericp_sharedsharepointonline_npi">.*?</connectionreference>',
                      cust, re.S).group(0)
    head = cust[:cust.index("<Entities")]
    new_cust = (head + "<Entities />\n  <Roles />\n  <Workflows>\n" + wf + "  </Workflows>\n  <FieldSecurityProfiles />\n"
                "  <Templates />\n  <EntityMaps />\n  <EntityRelationships />\n  <OrganizationSettings />\n  <optionsets />\n"
                "  <CustomControls />\n  <EntityDataProviders />\n  <CanvasApps>\n    " + canvas + "\n  </CanvasApps>\n"
                "  <connectionreferences>\n    " + spref + "\n  </connectionreferences>\n  <Languages>\n"
                "    <Language>1033</Language>\n  </Languages>\n</ImportExportXml>")
    sol = base.read("solution.xml").decode("utf-8")
    sol = re.sub(r"<UniqueName>EricP_NPITrackerIncrement1</UniqueName>", "<UniqueName>EricP_NPIUploadTest</UniqueName>", sol)
    sol = re.sub(r"<Version>[^<]*</Version>", f"<Version>{VERSION}</Version>", sol)
    sol = re.sub(r'(<LocalizedNames>\s*<LocalizedName description=")[^"]*(")', r"\1NPI Upload Test\2", sol, count=1)
    sol = re.sub(r'(<Descriptions>\s*<Description description=")[^"]*(")', r"\1Test for the NPIUploadFile flow and attachments control\2", sol, count=1)
    sol = re.sub(r"<RootComponents>.*?</RootComponents>", f'<RootComponents>\n      <RootComponent type="29" id="{{{flow["guid"]}}}" behavior="0" />\n      <RootComponent type="300" schemaName="{APP}" behavior="0" />\n    </RootComponents>', sol, flags=re.S)

    path = OUT / f"EricP_NPIUploadTest_{VERSION.replace('.', '_')}.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        def put(n, d):
            z.writestr(zipfile.ZipInfo(n, date_time=now.timetuple()[:6]), d, zipfile.ZIP_DEFLATED)
        put("solution.xml", sol.encode())
        put("customizations.xml", new_cust.encode())
        put("[Content_Types].xml", base.read("[Content_Types].xml"))
        put(f"CanvasApps/{APP}_BackgroundImageUri.png", base.read("CanvasApps/ericp_npitracker_i1_BackgroundImageUri.png"))
        put(f"CanvasApps/{APP}_DocumentUri.msapp", mbuf.getvalue())
        put(f"Workflows/{flow['name']}-{flow['guid'].upper()}.json", (HERE / "flows" / "NPIUploadFile" / "flow.json").read_bytes())
    import xml.dom.minidom
    chk = zipfile.ZipFile(path)
    for n in ("solution.xml", "customizations.xml"):
        xml.dom.minidom.parseString(chk.read(n))
    print(f"wrote {path.relative_to(HERE)}")


if __name__ == "__main__":
    main()
