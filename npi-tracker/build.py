#!/usr/bin/env python3
"""Build an NPI Tracker importable solution for one release.

Usage: python3 -I build.py releases/<version>.yaml

Rules (learned from 1.1.0.0-1.1.0.3):
  * Start from the latest tenant export (release 'base'). The tenant is the source of truth.
  * The msapp loads from YAML (packed.json LoadFromYaml=true). Only Src/*.pa.yaml, data source
    metadata and version/description metadata change. Controls/*.json are placeholders.
  * Only control types proven to open in the tenant, plus any listed under 'extra_controls'
    for a release that is explicitly marked as carrying an unproven control.
  * No Office 365 Users. New SharePoint lists/columns come from schema.yaml ('since' = release).
  * Keep msapp entry names (literal backslashes) and order. Existing flow JSON copied byte-for-byte.
  * Every formula: YAML-safe, balanced, known data sources, known columns for Patch/varRow/varProject.
"""
import datetime
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"

# ---------------------------------------------------------------- placeholders
def _is_me(p):
    return (f'(Lower(Coalesce({p}.Email, "")) = varMe || '
            f'EndsWith(Lower(Coalesce({p}.Claims, "")), "|" & varMe))')


# Independent Review: the assignee, the uploader and the person who last submitted it (Activity Log
# "x -> Done", excluding a QE reopen "Reviewed -> Done") cannot review it.
CANREVIEW = (
    "If(!varRow.IndependentReview, Set(varCanReview, varIsQEorQM), "
    "With({sub: First(SortByColumns(Filter(Filter('NPI Activity Log', ProjectID = varProject.Title && "
    "RequirementID = varRow.Title), EndsWith(Detail, \"-> Done\") && !StartsWith(Detail, \"Reviewed\")), "
    "\"PerformedDate\", SortOrder.Descending)).PerformedBy}, "
    "Set(varCanReview, varIsQEorQM && !(" + _is_me("varRow.Assignee") + " || " + _is_me("varRow.UploadedBy")
    + " || " + _is_me("sub") + "))))"
)
PRIMARY_TARGET = (
    'Switch(varRow.Status.Value, "Done", If(varCanReview, "Reviewed", ""), '
    '"Reviewed", If(varIsQEorQM, "Done", ""), '
    '"N/A", If(varIsQEorQM, "Not started", ""), "Done")'
)
SAVE = """=With(
    {oldS: varRow.Status.Value, newS: __TARGET__, rowId: varRow.ID, rowTitle: varRow.Title, n: Trim(txtNote.Text)},
    If(
        !IsBlank(newS),
        Set(varSaving, true);
        IfError(
            If(
                newS <> oldS,
                If(
                    newS = "Reviewed",
                    Patch('Project Requirements', LookUp('Project Requirements', ID = rowId), {Status: {Value: newS}, ReviewedBy: varMeUser, ReviewedDate: Now()}),
                    oldS = "N/A",
                    Patch('Project Requirements', LookUp('Project Requirements', ID = rowId), {Status: {Value: newS}, NAReason: Blank()}),
                    Patch('Project Requirements', LookUp('Project Requirements', ID = rowId), {Status: {Value: newS}})
                )
            );
            Patch(
                'NPI Activity Log',
                Defaults('NPI Activity Log'),
                {
                    Title: rowTitle & ": " & If(newS <> oldS, oldS & " -> " & newS, "note"),
                    ProjectID: varProject.Title,
                    RequirementID: rowTitle,
                    ActionType: {Value: "Status change"},
                    Detail: If(newS <> oldS, oldS & " -> " & newS, "Note added, status stays " & oldS),
                    Reason: n,
                    PerformedBy: varMeUser,
                    PerformedDate: Now()
                }
            );
            Reset(txtNote);
            Refresh('Project Requirements');
            ClearCollect(colReqs, Filter('Project Requirements', ProjectID = varProject.Title));
            Set(varRow, LookUp(colReqs, ID = rowId));
            __SET_CANREVIEW__;
            Set(varSaving, false);
            Notify(If(newS <> oldS, rowTitle & " is now " & newS, "Note saved"), NotificationType.Success),
            Set(varSaving, false);
            Notify("Update failed: " & FirstError.Message, NotificationType.Error)
        )
    )
)"""


def indent_block(text, line):
    pad = line[: len(line) - len(line.lstrip())]
    return "\n".join(pad + l for l in text.split("\n"))


def yaml_safe(text):
    """Turn one-line formulas that YAML would misread (': ', ' #', trailing ':') into |- blocks."""
    out = []
    for l in text.split("\n"):
        m = re.match(r"^(\s*)(\w+): (=.*)$", l)
        if m and (": " in m.group(3) or " #" in m.group(3) or m.group(3).rstrip().endswith(":")):
            out.append(f"{m.group(1)}{m.group(2)}: |-")
            out.append(f"{m.group(1)}  {m.group(3)}")
        else:
            out.append(l)
    return "\n".join(out)


def render_template(path):
    t = Path(path).read_text()
    out = []
    for line in t.split("\n"):
        if line.strip() == "__SAVE_PRIMARY__":
            out.append(indent_block(SAVE.replace("__TARGET__", PRIMARY_TARGET), line))
        elif line.strip() == "__SAVE_SECONDARY__":
            out.append(indent_block(SAVE.replace("__TARGET__", '"Draft"'), line))
        else:
            out.append(line)
    t = "\n".join(out)
    t = t.replace("__PRIMARY_TARGET__", PRIMARY_TARGET).replace("__SET_CANREVIEW__", CANREVIEW)
    assert "__" not in t.replace("'@odata.type'", ""), f"unreplaced placeholder in {path}"
    return t


# ---------------------------------------------------------------- validation
LABEL_PROPS = set("""Align AutoHeight Border BorderColor BorderStyle BorderThickness Color DisabledBorderColor
DisabledColor DisabledFill DisplayMode Fill FocusedBorderColor FocusedBorderThickness Font FontWeight Height
HoverBorderColor HoverColor HoverFill Italic LineHeight OnSelect Overflow PaddingBottom PaddingLeft PaddingRight
PaddingTop PressedBorderColor PressedColor PressedFill Size Strikethrough Text Tooltip Underline VerticalAlign
Visible Width Wrap X Y""".split())
RECT_PROPS = set("""BorderColor BorderStyle BorderThickness DisabledFill DisplayMode Fill FocusedBorderColor
FocusedBorderThickness Height HoverFill OnSelect PressedFill Tooltip Visible Width X Y""".split())
GALLERY_PROPS = set("""BorderColor BorderStyle BorderThickness DelayItemLoading DisplayMode Fill Height Items
Layout LoadingSpinner OnSelect ShowNavigation ShowScrollbar TemplateFill TemplatePadding TemplateSize Visible Width
WrapCount X Y""".split())
# Button / text input: properties already used in 1.1.0.3 plus standard classic colour states.
BUTTON_PROPS = set("""Align BorderColor BorderThickness Color DisabledBorderColor DisabledColor DisabledFill
DisplayMode Fill FontWeight Height HoverFill OnSelect PressedFill RadiusBottomLeft RadiusBottomRight RadiusTopLeft
RadiusTopRight Size Text Visible Width X Y""".split())
TEXT_PROPS = set("BorderColor Default Height HintText Mode Size Visible Width X Y".split())
ALLOWED = {
    "Label@2.5.1": LABEL_PROPS,
    "Rectangle@2.3.0": RECT_PROPS,
    "Gallery@2.15.0": GALLERY_PROPS,
    "Classic/Button@2.2.0": BUTTON_PROPS,
    "Classic/TextInput@2.3.2": TEXT_PROPS,
}
SCREEN_PROPS = {"Fill", "OnVisible"}
DATA_SOURCES = set()      # filled from the release schema
COLUMNS = {}              # list name -> set of column names
FLOWS = set()
RECORD_VARS = {"varRow": "Project Requirements", "varProject": "NPI Projects", "varQ": "NPI Open Questions"}


def check_formula(where, f):
    errs = []
    if not isinstance(f, str) or not f.startswith("="):
        return [f"{where}: value must be a string starting with '=' ({f!r})"]
    body = f[1:]
    # strip string literals ("" escapes) then check balance
    stripped = re.sub(r'"(?:[^"]|"")*"', '""', body)
    if stripped.count('"') % 2:
        errs.append(f"{where}: unbalanced double quotes")
    stripped2 = re.sub(r"'[^']*'", "''", stripped)
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in stripped2:
        if ch in "([{":
            stack.append(ch)
        elif ch in ")]}":
            if not stack or stack.pop() != pairs[ch]:
                errs.append(f"{where}: unbalanced {ch}")
                break
    if stack:
        errs.append(f"{where}: unclosed {''.join(stack)}")
    for q in re.findall(r"'[^']*'", stripped):
        if q not in DATA_SOURCES and q != "'@odata.type'" and q.strip("'") not in FLOWS:
            errs.append(f"{where}: unknown quoted name {q}")
    return errs


def walk(children, screen, names, errs, controls):
    for item in children:
        (name, spec), = item.items()
        if name in names:
            errs.append(f"duplicate control name {name}")
        names.add(name)
        ctype = spec.get("Control")
        if ctype not in ALLOWED:
            errs.append(f"{name}: control type {ctype} not proven in the tenant")
            continue
        if ctype == "Gallery@2.15.0" and spec.get("Variant") not in ("Vertical", "Horizontal"):
            errs.append(f"{name}: gallery variant missing")
        extra = set(spec) - {"Control", "Variant", "Properties", "Children"}
        if extra:
            errs.append(f"{name}: unexpected keys {extra}")
        for prop, val in (spec.get("Properties") or {}).items():
            if prop not in ALLOWED[ctype]:
                errs.append(f"{name}: property {prop} not allowed for {ctype}")
            errs += check_formula(f"{screen}.{name}.{prop}", val)
        controls[name] = (screen, ctype, spec)
        if spec.get("Children"):
            if ctype != "Gallery@2.15.0":
                errs.append(f"{name}: only galleries may have children")
            walk(spec["Children"], screen, names, errs, controls)


def validate(app_yaml, screens):
    errs = []
    app = yaml.safe_load(app_yaml)
    for prop, val in app["App"]["Properties"].items():
        errs += check_formula(f"App.{prop}", val)
    names, controls = set(), {}
    for fname, text in screens.items():
        doc = yaml.safe_load(text)
        (sname, sspec), = doc["Screens"].items()
        names.add(sname)
        for prop, val in sspec["Properties"].items():
            if prop not in SCREEN_PROPS:
                errs.append(f"{sname}: screen property {prop} not allowed")
            errs += check_formula(f"{sname}.{prop}", val)
        walk(sspec["Children"], sname, names, errs, controls)
    # every Reset(x)/Select(x)/x.Text/x.AllItems refers to a control on the same screen
    for name, (screen, ctype, spec) in controls.items():
        for prop, val in (spec.get("Properties") or {}).items():
            refs = set(re.findall(r"(?:Reset|Select)\((\w+)\)", val))
            refs |= set(re.findall(r"\b(\w+)\.(?:Text|AllItems)\b", val))
            for r in refs:
                if r in ("Parent", "ThisItem", "Self"):
                    continue
                if r not in controls:
                    errs.append(f"{name}.{prop}: reference to unknown control {r}")
                elif controls[r][0] != screen:
                    errs.append(f"{name}.{prop}: cross-screen reference to {r}")
    # every variable that is read is Set somewhere (catches silently failed edits)
    texts = [v for v in app["App"]["Properties"].values()]
    for _, (screen, ctype, spec) in controls.items():
        texts += list((spec.get("Properties") or {}).values())
    for text in screens.values():
        (_, sspec), = yaml.safe_load(text)["Screens"].items()
        texts += list(sspec["Properties"].values())
    blob = "\n".join(t for t in texts if isinstance(t, str))
    set_vars = set(re.findall(r"\bSet\(\s*(var\w+)", blob))
    for v in sorted(set(re.findall(r"\b(var\w+)\b", blob)) - set_vars):
        errs.append(f"variable {v} is read but never Set")
    # column checks
    for name, (screen, ctype, spec) in controls.items():
        for prop, val in (spec.get("Properties") or {}).items():
            errs += check_columns(f"{name}.{prop}", val)
    for fname, text in screens.items():
        doc = yaml.safe_load(text)
        (sname, sspec), = doc["Screens"].items()
        for prop, val in sspec["Properties"].items():
            errs += check_columns(f"{sname}.{prop}", val)
    return errs, len(controls)


def _args(body, start):
    """Split the call starting at body[start] == '(' into top-level args; return (args, end)."""
    depth, cur, args, i, instr = 0, "", [], start, False
    while i < len(body):
        ch = body[i]
        if ch == '"':
            instr = not instr
        if not instr:
            if ch in "([{":
                depth += 1
                if depth == 1:
                    i += 1
                    continue
            elif ch in ")]}":
                depth -= 1
                if depth == 0:
                    args.append(cur)
                    return args, i
            elif ch == "," and depth == 1:
                args.append(cur)
                cur = ""
                i += 1
                continue
        cur += ch
        i += 1
    return args, i


def _top_keys(rec):
    rec = rec.strip()
    if not rec.startswith("{"):
        return []
    keys, depth, instr, token = [], 0, False, ""
    for ch in rec:
        if ch == '"':
            instr = not instr
        if instr:
            continue
        if ch in "([{":
            depth += 1
            token = ""
            continue
        if ch in ")]}":
            depth -= 1
            continue
        if depth == 1:
            if ch == ":":
                t = token.strip().strip("'")
                if re.fullmatch(r"[\w@.]+", t):
                    keys.append(t)
                token = ""
            elif ch == ",":
                token = ""
            else:
                token += ch
    return keys


def check_columns(where, f):
    errs = []
    body = f[1:] if isinstance(f, str) else ""
    for m in re.finditer(r"\bPatch\(\s*'([^']+)'", body):
        lst = m.group(1)
        args, _ = _args(body, m.start() + len("Patch"))
        if lst not in COLUMNS:
            errs.append(f"{where}: Patch to unknown list {lst}")
            continue
        for a in args[2:]:
            for k in _top_keys(a):
                if k not in COLUMNS[lst]:
                    errs.append(f"{where}: Patch('{lst}') sets unknown column {k}")
    for var, lst in RECORD_VARS.items():
        if lst not in COLUMNS:
            if re.search(rf"\b{var}\.", body):
                errs.append(f"{where}: {var} used but list {lst} not in this release")
            continue
        for col in re.findall(rf"\b{var}\.(\w+)", body):
            if col not in COLUMNS[lst]:
                errs.append(f"{where}: {var}.{col} is not a column of {lst}")
    return errs




# ---------------------------------------------------------------- schema -> data sources
def vkey(v):
    return tuple(int(x) for x in v.split("."))


def release_schema(schema, version):
    """Lists/columns/choices present at this release."""
    out = {}
    for lname, l in schema["lists"].items():
        if "since" in l and vkey(l["since"]) > vkey(version):
            continue
        cols = {}
        for cname, c in l["columns"].items():
            if "since" in c and vkey(c["since"]) > vkey(version):
                continue
            c = dict(c)
            if c["type"] == "choice" and "choices_since" in c:
                c["choices"] = [x for x in c["choices"]
                                if vkey(c["choices_since"].get(x, "0.0.0.0")) <= vkey(version)]
            cols[cname] = c
        out[lname] = {"new": "since" in l, "columns": cols}
    return out


PERSON_PROPS = {
    "@odata.type": {"type": "string"}, "Claims": {"type": "string"}, "DisplayName": {"type": "string"},
    "Email": {"type": "string", "format": "email"}, "Picture": {"type": "string"},
    "Department": {"type": "string"}, "JobTitle": {"type": "string"},
}


def col_schema(name, c):
    t = c["type"]
    base = {"title": name, "x-ms-permission": "read-write"}
    if t == "id":
        return {**base, "type": "integer", "format": "int64"}
    if t == "text":
        return {**base, "type": "string"}
    if t == "number":
        return {**base, "type": "number"}
    if t == "boolean":
        return {**base, "type": "boolean"}
    if t == "datetime":
        return {**base, "type": "string", "format": "date-time"}
    if t == "person":
        return {**base, "type": "object", "properties": json.loads(json.dumps(PERSON_PROPS))}
    if t == "choice":
        return {**base, "type": "object", "properties": {"Value": {"type": "string", "enum": list(c["choices"])}}}
    raise ValueError(t)


def apply_schema(datasources, rs, site):
    """Add new columns/choices to existing SharePoint data sources and add new lists."""
    by_name = {d["Name"]: d for d in datasources["DataSources"]}
    template = by_name["NPI Role Defaults"]
    for lname, l in rs.items():
        if lname in by_name:
            ds = by_name[lname]
        else:
            ds = json.loads(json.dumps(template))
            ds["Name"] = ds["TableName"] = lname
            m = json.loads(ds["DataEntityMetadataJson"]["NPI Role Defaults"])
            m["name"] = m["title"] = lname
            m["schema"]["items"]["properties"] = {}
            ds["DataEntityMetadataJson"] = {lname: json.dumps(m)}
            ds["ConnectedDataSourceInfoNameMapping"] = {}
            datasources["DataSources"].append(ds)
        m = json.loads(ds["DataEntityMetadataJson"][lname])
        props = m["schema"]["items"]["properties"]
        for cname, c in l["columns"].items():
            if cname not in props:
                props[cname] = col_schema(cname, c)
            elif c["type"] == "choice":
                enum = props[cname]["properties"]["Value"]["enum"]
                enum += [x for x in c["choices"] if x not in enum]
            ds["ConnectedDataSourceInfoNameMapping"][cname] = cname
        ds["DataEntityMetadataJson"] = {lname: json.dumps(m)}
        ds["DatasetName"] = site
    return [n for n in rs]


# ---------------------------------------------------------------- flows
def flow_wadl(name, inputs, outputs, base_wadl):
    """WADL for a Power Apps (V1 'manual') trigger with text inputs, modelled on the working NPICreateProject."""
    apim = re.search(r'base="([^"]+)"', base_wadl).group(1)
    keys = ["text"] + [f"text_{i}" for i in range(1, len(inputs))]
    tdefs = "\n".join(f'      <string name="ManualTriggerInput_{k}_def" />' for k in keys)
    tprops = "\n".join(f'        <property name="{k}" type="string" />' for k in keys)
    otype = {"boolean": "boolean", "number": "number", "string": "string"}
    odefs = "\n".join(f'      <{otype[t]} name="ResponseActionOutput_{o}_def" />' for o, t in outputs.items())
    oprops = "\n".join(f'        <property name="{o}" type="{otype[t]}" />' for o, t in outputs.items())
    params = "\n".join(
        f'            <param style="plain" name="{k}" path="/{k}" type="xs:string" required="true">'
        f'<doc title="{inp}" /></param>' for k, inp in zip(keys, inputs))
    return f'''<application xmlns:xml="http://www.w3.org/XML/1998/namespace" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:service="{apim}" xmlns:siena="http://schemas.microsoft.com/MicrosoftProjectSiena/WADL/2014/11" siena:serviceId="{name}" xmlns="http://wadl.dev.java.net/2009/02">
  <doc title="{name}" />
  <grammars>
    <jsonTypes targetNamespace="{apim}" xmlns="http://schemas.microsoft.com/MicrosoftProjectSiena/WADL/2014/11">
{tdefs}
      <object name="ManualTriggerInput">
{tprops}
      </object>
{odefs}
      <object name="ResponseActionOutput">
{oprops}
      </object>
      <object name="Run_responses_default_def" />
    </jsonTypes>
  </grammars>
  <resources siena:authenticationProviderHref="#PowerAppAuth" base="{apim}">
    <resource path="/{{connectionId}}/triggers/manual/run">
      <param style="template" name="connectionId" type="xs:string" required="true" />
      <method siena:requiresAuthentication="true" name="POST" id="Run">
        <doc title="Runs a logic flow trigger." />
        <request>
          <param style="query" name="api-version" type="xs:string" required="true" fixed="2015-02-01-preview"><doc title="The api version" /></param>
          <representation mediaType="application/json">
{params}
          </representation>
        </request>
        <response><representation mediaType="application/json" element="service:ResponseActionOutput" /></response>
      </method>
    </resource>
  </resources>
  <authenticationProviders xmlns="http://schemas.microsoft.com/MicrosoftProjectSiena/WADL/2014/11">
    <connectionProvider id="PowerAppAuth" siena:connectionProviderId="logicflows" />
  </authenticationProviders>
  <template xmlns="http://schemas.microsoft.com/MicrosoftProjectSiena/WADL/2014/11">
    <variable name="connectionId"><modifyParams style="template" name="connectionId" attribute="fixed" /></variable>
  </template>
</application>'''


WORKFLOW_XML = '''    <Workflow WorkflowId="{{{guid}}}" Name="{name}">
      <JsonFileName>/Workflows/{name}-{GUID}.json</JsonFileName>
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
      <IntroducedVersion>{version}</IntroducedVersion>
      <IsCustomizable>1</IsCustomizable>
      <IsCustomProcessingStepAllowedForOtherPublishers>1</IsCustomProcessingStepAllowedForOtherPublishers>
      <ModernFlowType>0</ModernFlowType>
      <PrimaryEntity>none</PrimaryEntity>
      <LocalizedNames>
        <LocalizedName languagecode="1033" description="{name}" />
      </LocalizedNames>
    </Workflow>
'''


# ---------------------------------------------------------------- packaging
def count_types(screens):
    counts = {"screen": len(screens)}
    for text in screens.values():
        doc = yaml.safe_load(text)
        (_, s), = doc["Screens"].items()

        def w(ch):
            for item in ch:
                (_, spec), = item.items()
                k = spec["Control"].split("/")[-1].split("@")[0]
                k = k[0].lower() + k[1:]
                counts[k] = counts.get(k, 0) + 1
                w(spec.get("Children") or [])
        w(s["Children"])
    return counts


def main(release_path):
    rel = yaml.safe_load(Path(release_path).read_text())
    version, title, summary = rel["version"], rel["title"], rel["summary"].strip()
    base_zip = HERE / rel["base"]
    out_dir = HERE / "history" / version
    out_dir.mkdir(parents=True, exist_ok=True)

    schema = yaml.safe_load((HERE / "schema.yaml").read_text())
    rs = release_schema(schema, version)
    COLUMNS.clear()
    COLUMNS.update({l: set(v["columns"]) for l, v in rs.items()})
    DATA_SOURCES.clear()
    DATA_SOURCES.update(f"'{l}'" for l in rs)
    flows = [yaml.safe_load((HERE / "flows" / f / "flow.yaml").read_text()) for f in rel.get("flows", [])]
    FLOWS.clear()
    FLOWS.update(f["name"] for f in flows)
    for c in rel.get("extra_controls", []):
        ALLOWED[c["type"]] = set(c["props"])

    screens = {}
    for name in ("scrProjects", "scrProjectDetail"):
        t = SRC / f"{name}.template.yaml"
        screens[f"Src\\{name}.pa.yaml"] = render_template(t) if t.exists() else (SRC / f"{name}.pa.yaml").read_text()
    screens = {k: yaml_safe(v) for k, v in screens.items()}
    app_yaml = yaml_safe((SRC / "App.pa.yaml").read_text())
    errs, count = validate(app_yaml, screens)
    if errs:
        print("VALIDATION FAILED")
        print("\n".join(errs))
        sys.exit(1)
    print(f"{version}: validation passed, {count} controls, lists: {', '.join(rs)}; flows: {[f['name'] for f in flows]}")
    gen = out_dir / "src"
    gen.mkdir(exist_ok=True)
    (gen / "App.pa.yaml").write_text(app_yaml)
    for n, t in screens.items():
        (gen / n.split("\\")[1]).write_text(t)

    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    stamp_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp_us = now.strftime("%m/%d/%Y %H:%M:%S")
    import io
    base = zipfile.ZipFile(base_zip)
    msapp_name = next(n for n in base.namelist() if n.endswith("_DocumentUri.msapp"))
    old_msapp = zipfile.ZipFile(io.BytesIO(base.read(msapp_name)))
    sp_lists = list(rs)

    ds_json = json.loads(old_msapp.read("References\\DataSources.json"))
    apply_schema(ds_json, rs, schema["site"])
    base_wadl = next(d for d in ds_json["DataSources"] if d["Name"] == "NPICreateProject")["WadlMetadata"]["WadlXml"]
    for f in flows:
        if any(d["Name"] == f["name"] for d in ds_json["DataSources"]):
            continue
        ds_json["DataSources"].append({
            "ApiId": "/providers/microsoft.powerapps/apis/shared_logicflows",
            "FlowNameId": f["guid"], "Name": f["name"], "ServiceKind": "ConnectedWadl", "Type": "ServiceInfo",
            "WadlMetadata": {"WadlXml": flow_wadl(f["name"], f["inputs"], f["outputs"], base_wadl)},
            "WorkflowEntityId": f["guid"],
        })

    entries = []
    for info in old_msapp.infolist():
        n, data = info.filename, old_msapp.read(info.filename)
        if n == "Src\\App.pa.yaml":
            data = app_yaml.encode()
        elif n in screens:
            data = screens[n].encode()
        elif n == "References\\DataSources.json":
            data = json.dumps(ds_json, indent=2).encode()
        elif n == "Header.json":
            h = json.loads(data)
            h["LastSavedDateTimeUTC"] = stamp_us
            data = json.dumps(h, indent=2).encode()
        elif n == "packed.json":
            p = json.loads(data)
            p["LastPackedDateTimeUtc"] = stamp_iso
            p["PackingClient"]["Version"] = version
            data = json.dumps(p, indent=2).encode()
        elif n == "Properties.json":
            p = json.loads(data)
            p["AppDescription"] = f"NPI Tracker {version}: {title}."
            p["DefaultConnectedDataSourceMaxGetRowsCount"] = 2000
            p["ControlCount"] = count_types(screens)
            lcr = json.loads(p["LocalConnectionReferences"])
            for k, v in lcr.items():
                if "sharepointonline" in v["connectionRef"]["id"]:
                    v["dataSources"] = sp_lists
                    v["datasets"][schema["site"]]["dataSources"] = {l: {"tableName": l} for l in sp_lists}
            p["LocalConnectionReferences"] = json.dumps(lcr)
            data = json.dumps(p, indent=2).encode()
        entries.append((n, data))
    mbuf = io.BytesIO()
    with zipfile.ZipFile(mbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in entries:
            zi = zipfile.ZipInfo(n, date_time=now.timetuple()[:6])
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)

    sol_path = out_dir / f"EricP_NPITrackerIncrement1_{version.replace('.', '_')}.zip"
    desc = f"NPI Tracker {version}: {title}"
    with zipfile.ZipFile(sol_path, "w", zipfile.ZIP_DEFLATED) as z:
        def put(n, data, stamp=True, orig=None):
            zi = zipfile.ZipInfo(n, date_time=now.timetuple()[:6] if stamp else orig.date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)
        for info in base.infolist():
            n, data = info.filename, base.read(info.filename)
            if n == msapp_name:
                put(n, mbuf.getvalue())
            elif n == "solution.xml":
                s = data.decode("utf-8")
                s = re.sub(r"<Version>[^<]*</Version>", f"<Version>{version}</Version>", s)
                s = re.sub(r'(<LocalizedNames>\s*<LocalizedName description=")[^"]*(" languagecode="1033" />)',
                           lambda m: m.group(1) + desc + m.group(2), s, count=1)
                s = re.sub(r'(<Descriptions>\s*<Description description=")[^"]*(")',
                           lambda m: m.group(1) + desc + m.group(2), s, count=1)
                for f in flows:
                    if f["guid"].lower() not in s.lower():
                        s = s.replace("<RootComponents>", f'<RootComponents>\n      <RootComponent type="29" id="{{{f["guid"]}}}" behavior="0" />', 1)
                put(n, s.encode("utf-8"))
            elif n == "customizations.xml":
                s = data.decode("utf-8")
                s = re.sub(r"<AppVersion>[^<]*</AppVersion>", f"<AppVersion>{stamp_iso}</AppVersion>", s)
                s = re.sub(r"(<CanvasApp>.*?<Description>)[^<]*(</Description>)",
                           lambda m: m.group(1) + desc + m.group(2), s, count=1, flags=re.S)
                # ConnectionReferences JSON on the canvas app
                m = re.search(r"<ConnectionReferences>(.*?)</ConnectionReferences>", s, re.S)
                cr = json.loads(m.group(1))
                for k, v in cr.items():
                    if v["id"].endswith("shared_sharepointonline"):
                        v["dataSources"] = sp_lists
                        v["dataSets"][schema["site"]]["dataSources"] = {l: {"tableName": l} for l in sp_lists}
                cdeps = json.loads(re.search(r"<CdsDependencies>(.*?)</CdsDependencies>", s, re.S).group(1))
                for f in flows:
                    if not any(f["name"] in v.get("dataSources", []) for v in cr.values()):
                        cr[f["cr_key"]] = {
                            "id": "/providers/microsoft.powerapps/apis/shared_logicflows",
                            "displayName": "Logic flows",
                            "iconUri": "https://static.powerapps.com/resource/ppcr/releases/v1.0.1827/1.0.1827.4908/logicflows/icon.png",
                            "dataSources": [f["name"]], "dependencies": [], "dependents": [],
                            "parameterHints": {"workflowName": {"value": f["guid"]}, "workflowEntityId": {"value": f["guid"]}},
                            "parameterHintsV2": {"workflowName": {"value": f["guid"]}, "workflowEntityId": {"value": f["guid"]}},
                            "isOnPremiseConnection": False, "bypassConsent": False, "dataSets": {},
                            "apiTier": "Standard", "actions": ["Run"]}
                    if not any(d["dependencyid"] == f["guid"] for d in cdeps["cdsdependencies"]):
                        cdeps["cdsdependencies"].append({"componenttype": 29, "dependencyid": f["guid"],
                                                         "componenttypeplatformname": "Workflow"})
                    if f["guid"].lower() not in s.lower():
                        wx = WORKFLOW_XML.format(guid=f["guid"], GUID=f["guid"].upper(), name=f["name"], version=version)
                        s = s.replace("</Workflows>", wx + "  </Workflows>", 1)
                s = s.replace(m.group(1), json.dumps(cr, separators=(",", ":")).replace("&", "&amp;"))
                s = re.sub(r"<CdsDependencies>.*?</CdsDependencies>",
                           lambda _: "<CdsDependencies>" + json.dumps(cdeps, separators=(",", ":")) + "</CdsDependencies>", s, flags=re.S)
                put(n, s.encode("utf-8"))
            else:
                put(n, data, stamp=False, orig=info)
        for f in flows:
            fn = f"Workflows/{f['name']}-{f['guid'].upper()}.json"
            if fn not in base.namelist():
                put(fn, (HERE / "flows" / f["dir"] / "flow.json").read_bytes())
    # sanity: re-open everything
    chk = zipfile.ZipFile(sol_path)
    assert chk.testzip() is None
    zipfile.ZipFile(io.BytesIO(chk.read(msapp_name))).testzip()
    import xml.dom.minidom
    for n in ("solution.xml", "customizations.xml", "[Content_Types].xml"):
        xml.dom.minidom.parseString(chk.read(n))
    for n in chk.namelist():
        if n.endswith(".json"):
            json.loads(chk.read(n).decode("utf-8-sig"))
    print(f"wrote {sol_path.relative_to(HERE)}")


if __name__ == "__main__":
    main(sys.argv[1])
