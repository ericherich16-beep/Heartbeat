#!/usr/bin/env python3
"""
verify_package.py - pre-delivery checks for a Power Apps solution zip.

Every check ID matches a numbered lesson in LESSONS.md (same folder). Each check
comes from a real failure in an earlier build: an import error, a flow that
wouldn't turn on, a blank or black app, or a control that didn't work.

Usage
    python3 verify_package.py <solution.zip> [options]

Options
    --schema FILE         lists.json describing every SharePoint list/library (see LESSONS.md, SP-01).
                          Checks the app's embedded table definitions against it.
    --tenant-fields DIR   Folder of <ListName>.csv exports from the user's real site
                          (Get-PnPField ... | Export-Csv). Compared against --schema.
    --docs DIR            Folder holding README / POST_IMPORT docs to check for the required steps.
    --src DIR             Unpacked canvas source folder the .msapp was packed from (checks EditorState).
    --previous-version V  Last version delivered to the user. The new version must be higher.
    --pac CMD             How to run pac (e.g. "pac" or "python3 /path/pac.py"). Enables the round-trip check.
    --blocked-ops LIST    Comma-separated operationIds blocked by the tenant's DLP policy (default: HttpRequest).
    --allow-flow-item-params  Allow SharePoint column parameters (item/...) in flows. Only use this once
                          the real list's internal names have been confirmed (FLOW-02).
    --json                Print results as JSON.

Exit code: 1 if any check FAILs, else 0. WARN means look at it; MANUAL means a person or the agent
has to confirm it outside this script (the list is printed at the end).
"""
import argparse, csv, io, json, os, re, shlex, subprocess, sys, tempfile, zipfile
import xml.etree.ElementTree as ET

RESULTS = []


def add(cid, status, msg):
    RESULTS.append({"id": cid, "status": status, "msg": msg})


# Properties Studio accepts on every control even though the template XML doesn't list them
# (auto-layout child properties, z-order, corner radius on label/rectangle). Calibrated against
# an app that imported and opened in Studio.
IMPLICIT_PROPS = {"ZIndex", "X", "Y", "Width", "Height", "Visible", "FillPortions", "AlignInContainer",
                  "LayoutMinWidth", "LayoutMinHeight", "LayoutMaxWidth", "LayoutMaxHeight",
                  "RadiusTopLeft", "RadiusTopRight", "RadiusBottomLeft", "RadiusBottomRight"}
# Properties that broke a real import or app: (template, property) -> reason.
DENYLIST = {("button", "AccessibleLabel"): "classic buttons don't support AccessibleLabel (20 import errors, Stage 2)",
            }
# Properties that are legal but dangerous when generated: (template, property) -> advice (WARN).
CAUTION = {("combobox", "SearchItems"): "the .pa.yaml loader rejected SearchItems (Stage 2 import failed) and its template "
                                        "default points at sample column Value1; prefer a dropdown, or set it explicitly and test in Studio"}
BUILTIN_TEMPLATES = {"screen", "appinfo", "galleryTemplate", "hostControl"}
NONDELEGABLE_FN = ["Len", "Left", "Right", "Mid", "Lower", "Upper", "Trim", "Text", "Value", "Year", "Month", "Day",
                   "Weekday", "Hour", "DateDiff", "DateValue", "Concatenate", "Substitute", "IsBlank", "IsEmpty", "Find"]
DOC_STEPS = {
    "import route": r"Import solution",
    "don't unzip": r"(?i)(don.?t|do not) unzip",
    "bind connection references": r"(?i)connection",
    "set environment variables": r"(?i)environment variable",
    "turn the flow on": r"(?i)turn on",
    "refresh / re-add data sources after import": r"(?i)refresh",
    "re-add the flow in the app if Run is missing": r"(?i)(re-?add|add flow|remove.{0,40}add)",
    "App checker before publish": r"(?i)app checker",
    "Dataverse prerequisite": r"(?i)dataverse",
}


def strip_strings(s):
    return re.sub(r'"(?:[^"]|"")*"', '""', s)


def balanced(s, i):
    """s[i] == '(' ; return the text up to the matching ')'."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            depth += 1
        elif s[j] == ")":
            depth -= 1
            if depth == 0:
                return s[i + 1:j]
    return s[i + 1:]


def norm(name):
    return name.replace("\\", "/")


# ---------------------------------------------------------------- solution level
def check_solution(z):
    names = {norm(n) for n in z.namelist()}
    root = {n for n in names if "/" not in n}
    need = {"solution.xml", "customizations.xml", "[Content_Types].xml"}
    if need <= root:
        add("PKG-01", "PASS", "solution zip layout: solution.xml, customizations.xml and [Content_Types].xml at the root")
    else:
        msapps = [n for n in names if n.endswith(".msapp")]
        hint = " It looks like a zipped .msapp, which 'Import canvas app' rejects with 'manifest file could not be found'." if msapps else ""
        add("PKG-01", "FAIL", f"missing at zip root: {sorted(need - root)}.{hint}")
        return None
    if any(n.endswith(".zip") for n in names):
        add("PKG-01", "FAIL", "zip contains another zip; give the user the solution zip itself")

    sol = ET.fromstring(z.read("solution.xml"))
    cust_raw = z.read("customizations.xml").decode("utf-8-sig")
    cust = ET.fromstring(cust_raw)
    ver = (sol.findtext(".//Version") or "").strip()
    managed = (sol.findtext(".//Managed") or "").strip()
    rcs = [(rc.get("type"), rc.get("schemaName") or rc.get("id")) for rc in sol.iter("RootComponent")]

    # PKG-02 every root component is really in the package
    apps = {ca.findtext("Name"): ca for ca in cust.iter("CanvasApp")}
    wfs = {(w.get("WorkflowId") or "").strip("{}").lower(): w for w in cust.iter("Workflow")}
    bad = []
    for t, key in rcs:
        if t == "300":
            ca = apps.get(key)
            if ca is None:
                bad.append(f"canvas app {key} is a root component but customizations.xml has no <CanvasApp> for it "
                           "(import error 'Cannot add a Root Component ... of type 300')")
            elif norm(ca.findtext("DocumentUri") or "").lstrip("/") not in names:
                bad.append(f"canvas app {key}: DocumentUri file missing from zip")
        elif t == "29":
            w = wfs.get((key or "").strip("{}").lower())
            if w is None:
                bad.append(f"workflow {key} missing from customizations.xml")
            elif norm(w.findtext("JsonFileName") or "").lstrip("/") not in names:
                bad.append(f"workflow {key}: JSON file missing from zip")
        elif t == "380":
            if not any(n.lower().startswith(f"environmentvariabledefinitions/{key.lower()}/") for n in names):
                bad.append(f"environment variable {key}: definition missing from zip")
    for name in apps:
        if ("300", name) not in rcs:
            bad.append(f"canvas app {name} is in customizations.xml but not a root component")
    if bad:
        for b in bad:
            add("PKG-02", "FAIL", b)
    else:
        add("PKG-02", "PASS", f"all {len(rcs)} root components are present in the zip")

    # PKG-03 version
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", ver):
        add("PKG-03", "FAIL", f"solution version '{ver}' is not 4-part")
    elif ARGS.previous_version:
        a = tuple(map(int, ver.split(".")))
        b = tuple(map(int, ARGS.previous_version.split(".")))
        add("PKG-03", "PASS" if a > b else "FAIL",
            f"version {ver} vs previously delivered {ARGS.previous_version}" + ("" if a > b else ": bump it, or the upgrade import does nothing"))
    else:
        add("PKG-03", "WARN", f"version {ver}; pass --previous-version to confirm it was bumped")
    if managed not in ("0", "2", ""):
        add("PKG-03", "WARN", f"<Managed>{managed}</Managed>: deliver unmanaged while the app is still changing")

    # env vars
    envvars = {}
    for n in names:
        m = re.match(r"environmentvariabledefinitions/([^/]+)/environmentvariabledefinition\.xml$", n, re.I)
        if m:
            ev = ET.fromstring(z.read(next(x for x in z.namelist() if norm(x) == n)))
            envvars[m.group(1)] = {"type": ev.findtext("type"), "key": ev.findtext("parameterkey"),
                                   "parent": ev.findtext("parentdefinitionid/schemaname"),
                                   "default": ev.findtext("defaultvalue")}
    for k, v in envvars.items():
        if v["default"] and re.search(r"sharepoint\.com", v["default"]) and "contoso" not in v["default"]:
            add("APP-11", "FAIL", f"environment variable {k} ships a real default value; leave it empty for the import wizard")

    connrefs = {c.get("connectionreferencelogicalname"): c.findtext("connectorid") for c in cust.iter("connectionreference")}
    return {"names": names, "cust": cust, "cust_raw": cust_raw, "apps": apps, "wfs": wfs, "envvars": envvars,
            "connrefs": connrefs, "version": ver}


# ---------------------------------------------------------------- flows
def walk_actions(acts, path=""):
    for k, a in (acts or {}).items():
        yield k, a
        yield from walk_actions(a.get("actions"), k)
        if isinstance(a.get("else"), dict):
            yield from walk_actions(a["else"].get("actions"), k)
        for c in (a.get("cases") or {}).values():
            yield from walk_actions(c.get("actions"), k)
        if isinstance(a.get("default"), dict):
            yield from walk_actions(a["default"].get("actions"), k)


def check_flows(z, ctx):
    blocked = {b.strip() for b in ARGS.blocked_ops.split(",") if b.strip()}
    for wid, w in ctx["wfs"].items():
        fn = norm(w.findtext("JsonFileName") or "").lstrip("/")
        member = next((x for x in z.namelist() if norm(x) == fn), None)
        if not member:
            continue
        raw = z.read(member).decode("utf-8-sig")
        flow = json.loads(raw)
        name = w.get("Name")
        props = flow.get("properties", {})
        d = props.get("definition", {})
        trig = list((d.get("triggers") or {}).values())
        is_app_flow = any(t.get("kind") == "PowerAppV2" or t.get("kind") == "PowerApp" for t in trig)
        problems = {"FLOW-01": [], "FLOW-02": [], "FLOW-05": []}
        responses = []
        for k, a in walk_actions(d.get("actions")):
            inp = a.get("inputs") if isinstance(a.get("inputs"), dict) else {}
            host = inp.get("host", {}) if isinstance(inp.get("host"), dict) else {}
            op = host.get("operationId", "")
            api = (host.get("apiId") or host.get("connectionName") or host.get("connection", {}).get("name", "")
                   if isinstance(host.get("connection", {}), dict) else "")
            api = str(host.get("apiId") or host.get("connectionName") or api)
            if op in blocked:
                problems["FLOW-01"].append(f"{k}: operation {op} is blocked by the tenant data policy")
            if a.get("type") in ("Http", "HttpWebhook"):
                problems["FLOW-01"].append(f"{k}: HTTP action is a premium connector")
            if "commondataservice" in api.lower():
                problems["FLOW-01"].append(f"{k}: Dataverse connector is premium")
            params = inp.get("parameters", {}) if isinstance(inp.get("parameters"), dict) else {}
            item_params = [p for p in params if p.startswith("item/")]
            if item_params and not ARGS.allow_flow_item_params:
                problems["FLOW-02"].append(f"{k} ({op}): sets list columns {item_params[:4]}... Power Automate checks these "
                                           "against the real list when the flow is turned on")
            if a.get("type") == "Response":
                responses.append((k, a))
            if is_app_flow and a.get("type") == "OpenApiConnection" and "sharepoint" not in api.lower():
                if "retryPolicy" not in inp or "timeout" not in json.dumps(a.get("limit", {})):
                    problems["FLOW-05"].append(f"{k} ({api.split('/')[-1] or op}): no retryPolicy none / timeout; "
                                               "a failing call keeps the app on 'Saving...' for minutes")
        for cid, lst in problems.items():
            if lst:
                for p in lst:
                    add(cid, "FAIL" if cid != "FLOW-05" else "WARN", f"flow '{name}': {p}")
            else:
                add(cid, "PASS", f"flow '{name}'")
        # FLOW-03 connection references exist in the solution
        miss = []
        for key, cr in (props.get("connectionReferences") or {}).items():
            ln = (cr.get("connection") or {}).get("connectionReferenceLogicalName")
            if not ln or ln not in ctx["connrefs"]:
                miss.append(f"{key} -> {ln}")
        add("FLOW-03", "FAIL" if miss else "PASS",
            f"flow '{name}': " + (f"connection references not defined in the solution: {miss}" if miss
                                  else "every connection reference is defined in the solution"))
        # FLOW-04 placeholders
        ph = sorted(set(re.findall(r"REPLACE_[A-Z_]+|TODO[:\s][^\"]{0,30}|<your[^>\"]*>", raw)))
        add("FLOW-04", "WARN" if ph else "PASS",
            f"flow '{name}': " + (f"placeholders the user must replace after import: {ph}. Say so in POST_IMPORT, "
                                  "or ask for the real value so it survives re-imports" if ph else "no placeholders"))
        # FLOW-06 respond on failure
        if is_app_flow:
            allacts = dict(walk_actions(d.get("actions")))
            def on_fail_path(k, seen=()):
                ra = (allacts.get(k) or {}).get("runAfter") or {}
                if any(st in ("Failed", "TimedOut") for v in ra.values() for st in v):
                    return True
                return any(on_fail_path(x, seen + (k,)) for x in ra if x not in seen)
            fail_resp = [k for k, a in responses if on_fail_path(k)]
            add("FLOW-06", "PASS" if fail_resp else "WARN",
                f"flow '{name}': " + ("responds to the app on failure too" if fail_resp else
                                      "no Respond-to-Power-Apps step that runs after a failure; the app can hang"))
        # state
        if (w.findtext("StateCode") or "") != "1":
            add("FLOW-07", "WARN", f"flow '{name}' ships turned off: POST_IMPORT must say to turn it on")
        else:
            add("FLOW-07", "MANUAL", f"flow '{name}' ships on, but Power Platform leaves it off if a connection "
                                     "wasn't bound at import. POST_IMPORT must say to check it is on")


# ---------------------------------------------------------------- canvas app
def load_msapp(z, ctx, appname):
    ca = ctx["apps"][appname]
    uri = norm(ca.findtext("DocumentUri") or "").lstrip("/")
    member = next((x for x in z.namelist() if norm(x) == uri), None)
    data = z.read(member)
    mz = zipfile.ZipFile(io.BytesIO(data))
    files = {norm(n): n for n in mz.namelist()}
    return ca, mz, files, data


def iter_controls(node, parents=()):
    yield node, parents
    for ch in node.get("Children", []):
        yield from iter_controls(ch, parents + (node,))


def check_app(z, ctx, appname):
    try:
        ca, mz, files, data = load_msapp(z, ctx, appname)
    except Exception as e:
        add("PKG-04", "FAIL", f"{appname}: .msapp can't be opened as a zip ({e})")
        return
    tag = f"[{appname}] "
    need = ["Header.json", "Properties.json"]
    missing = [n for n in need if n not in files]
    ctrl_files = [n for n in files if n.startswith("Controls/") and n.endswith(".json")]
    yaml_files = [n for n in files if n.startswith("Src/") and n.endswith((".pa.yaml", ".fx.yaml"))]
    if missing or not (ctrl_files or yaml_files):
        add("PKG-04", "FAIL", tag + f".msapp is missing {missing or 'Controls/*.json and Src/*.yaml'}")
        return
    for n in need + ["References/Templates.json", "References/DataSources.json"]:
        if n in files:
            try:
                json.loads(mz.read(files[n]).decode("utf-8-sig"))
            except Exception as e:
                add("PKG-04", "FAIL", tag + f"{n} is not valid JSON ({e})")
    hdr = json.loads(mz.read(files["Header.json"]).decode("utf-8-sig"))
    add("PKG-04", "PASS", tag + f".msapp structure OK (DocVersion {hdr.get('DocVersion')}, "
                               f"{len(ctrl_files)} control files, {len(yaml_files)} yaml files)")
    add("PKG-04", "MANUAL", tag + "Header/Properties/References came from a Studio-saved or pac-unpacked real app "
                                  "(not written by hand): hand-made ones gave ErrOpeningDocument_UnknownError")
    if not ctrl_files:
        add("APP-00", "WARN", tag + "no Controls/*.json (load-from-YAML package): structural APP checks skipped; "
                                    "run pac canvas unpack and re-run on that output")
        return

    templates = {}
    if "References/Templates.json" in files:
        t = json.loads(mz.read(files["References/Templates.json"]).decode("utf-8-sig"))
        for u in t.get("UsedTemplates", []):
            templates[u["Name"]] = set(re.findall(r'name="([A-Za-z0-9]+)"', u.get("Template", "")))
    ds = json.loads(mz.read(files["References/DataSources.json"]).decode("utf-8-sig")).get("DataSources", []) \
        if "References/DataSources.json" in files else []
    sp_sources = [d for d in ds if d.get("Type") == "ConnectedDataSourceInfo" and "sharepoint" in d.get("ApiId", "")]
    flow_sources = [d for d in ds if "logicflows" in d.get("ApiId", "")]

    controls = []
    for f in ctrl_files:
        top = json.loads(mz.read(files[f]).decode("utf-8-sig"))["TopParent"]
        controls.extend(iter_controls(top))
    names = {c["Name"] for c, _ in controls}
    rules = lambda c: {r["Property"]: r.get("InvariantScript", "") for r in c.get("Rules", [])}

    issues = {k: [] for k in ["APP-01", "APP-01w", "APP-02", "APP-03", "APP-04", "APP-05", "APP-06", "APP-07", "APP-08",
                              "APP-09", "APP-10", "APP-11"]}
    sp_names = [d["Name"] for d in sp_sources]
    sp_cols = {}
    for d in sp_sources:
        meta = list((d.get("DataEntityMetadataJson") or {}).values())
        meta = json.loads(meta[0]) if meta and isinstance(meta[0], str) else (meta[0] if meta else {})
        sp_cols[d["Name"]] = [c for c in meta.get("schema", {}).get("items", {}).get("properties", {})
                              if re.fullmatch(r"[A-Za-z_]\w*", c)]
    for c, parents in controls:
        tn = c["Template"]["Name"]
        r = rules(c)
        nm = c["Name"]
        # APP-01 properties exist on the control template
        for p in r:
            if (tn, p) in DENYLIST:
                issues["APP-01"].append(f"{nm}.{p}: {DENYLIST[(tn, p)]}")
            elif (tn, p) in CAUTION:
                issues["APP-01w"].append(f"{nm}.{p}: {CAUTION[(tn, p)]}")
            elif tn in templates and p not in templates[tn] and p not in IMPLICIT_PROPS and not p.startswith("#"):
                issues["APP-01"].append(f"{nm}.{p}: not a property of template '{tn}'")
        # APP-03 screen size
        if tn == "screen":
            for p in ("Width", "Height"):
                if not r.get(p, "").strip():
                    issues["APP-03"].append(f"{nm}: no {p} rule (Studio sizes it 0x0, every container collapses, screen looks blank)")
        # APP-04 theme defaults (black controls)
        if tn in ("text", "dropdown", "combobox", "datepicker") and "Fill" not in r:
            issues["APP-04"].append(f"{nm} ({tn}): no Fill rule; Studio draws it black")
        if tn == "label" and "Color" not in r:
            issues["APP-04"].append(f"{nm} (label): no Color rule")
        # APP-05 gallery layout
        if tn == "gallery" and "Layout" not in r:
            issues["APP-05"].append(f"{nm}: no Layout rule; template default is Horizontal (lists render sideways)")
        # APP-06 attachments outside a form
        if tn == "attachments" and not any(p["Template"]["Name"] in ("form", "typedDataCard", "dataCard") for p in parents):
            bad = []
            if "DisplayMode.Edit" not in r.get("DisplayMode", ""):
                bad.append("DisplayMode=DisplayMode.Edit")
            if r.get("IsInDataCard", "").strip().lower() != "true":
                bad.append("IsInDataCard=true")
            if "Items" not in r:
                bad.append("Items")
            if bad:
                issues["APP-06"].append(f"{nm}: outside a form and missing {bad}; it renders read-only ('No file selected', no Choose a file)")
        for p, f in r.items():
            s = strip_strings(f)
            # APP-02 sample-column references
            for m in re.finditer(r"(?<![\w.'])Value\d+\b", s):
                issues["APP-02"].append(f"{nm}.{p}: refers to sample column '{m.group(0)}'")
            # APP-07 precedence of !
            for m in re.finditer(r"(?<![!<>=\w])!\s*(?!\()([A-Za-z_'][\w.']*(?:\([^()]*\))?)\s*(=|<>)(?!=)", s):
                issues["APP-07"].append(f"{nm}.{p}: '!{m.group(1)} {m.group(2)} ...' negates before comparing; write !( ... ) or Not( ... )")
            # APP-08 paired controls cross-wired (e.g. cboPN2 using tglL1Run)
            own_digits = set(re.findall(r"\d+", nm))
            if own_digits and not nm.endswith("template1"):
                for ref in set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", s)) & names:
                    if ref == nm:
                        continue
                    for m in re.finditer(r"\d+", ref):
                        if m.group(0) in own_digits:
                            continue
                        for d in own_digits:
                            alt = ref[:m.start()] + d + ref[m.end():]
                            if alt in names and alt != ref:
                                issues["APP-08"].append(f"{nm}.{p} uses {ref}, but {alt} exists (copy-paste from the other set?)")
            # APP-09 delegation
            for spn in sp_names:
                if re.search(r"\bSearch\(\s*'?" + re.escape(spn) + r"'?\s*,", s):
                    issues["APP-09"].append(f"{nm}.{p}: Search({spn}, ...) is not delegable to SharePoint")
                cols = "|".join(map(re.escape, sp_cols.get(spn, []))) or "^$"
                for m in re.finditer(r"\b(Filter|LookUp|CountIf)\(\s*('?)" + re.escape(spn) + r"\2\s*,", s):
                    body = balanced(s, m.end() - len(m.group(0)) + m.group(0).index("("))
                    found = sorted(set(re.findall(r"\b(" + "|".join(NONDELEGABLE_FN) + r")\(\s*(?:ThisRecord\.)?(?:" + cols + r")\b", body)))
                    found += [f"'in' on {c}" for c in set(re.findall(r"\bin\s+(?:ThisRecord\.)?(" + cols + r")\b(?!\s*\.)", body))]
                    if found:
                        issues["APP-09"].append(f"{nm}.{p}: {m.group(1)}({spn}, ...) applies {found} to a column; SharePoint "
                                                "may reject the query or only the first 500-2000 rows are searched")
            # APP-10 reserved names as record fields
            for m in re.finditer(r"[{,]\s*(Type|Self|Parent|ThisItem|ThisRecord)\s*:", s):
                if p in ("Formulas", "OnStart", "Items"):
                    issues["APP-10"].append(f"{nm}.{p}: record field '{m.group(1)}' clashes with a Power Fx name")
            # APP-11 hard-coded tenant values
            for m in re.finditer(r"https?://[\w.-]+\.sharepoint\.com[^\"\s]*", f):
                if "contoso" not in m.group(0):
                    issues["APP-11"].append(f"{nm}.{p}: hard-coded site '{m.group(0)}'")
    for cid, lst in issues.items():
        status = "WARN" if cid in ("APP-01w", "APP-08", "APP-09", "APP-10") else "FAIL"
        if cid == "APP-01w":
            cid = "APP-01"
            if not lst:
                continue
        if lst:
            for i in sorted(set(lst))[:25]:
                add(cid, status, tag + i)
            if len(set(lst)) > 25:
                add(cid, status, tag + f"... and {len(set(lst)) - 25} more")
        else:
            add(cid, "PASS", tag + f"{len(controls)} controls checked")

    # APP-12 data sources bound to environment variables
    m = re.search(r"\{.*\}", ca.findtext("ConnectionReferences") or "", re.S)
    cr = json.loads(m.group(0)) if m else {}
    bound, unbound = set(), []
    for v in cr.values():
        for dsurl, dset in (v.get("dataSets") or {}).items():
            site_ev = (dset.get("datasetOverride") or {}).get("environmentVariableName")
            for dname, dd in (dset.get("dataSources") or {}).items():
                tbl_ev = (dd.get("tableNameOverride") or {}).get("environmentVariableName")
                if site_ev and tbl_ev and site_ev in ctx["envvars"] and tbl_ev in ctx["envvars"]:
                    bound.add(dname)
    for d in sp_sources:
        if d["Name"] not in bound:
            unbound.append(d["Name"])
    if unbound:
        add("APP-12", "FAIL", tag + f"SharePoint sources not bound to environment variables in the solution: {unbound} "
                                    "(they'd point at the build's placeholder site)")
    else:
        add("APP-12", "PASS", tag + f"{len(sp_sources)} SharePoint sources bound to environment variables")

    # APP-13 flow data sources point at a flow in this solution
    cds = ca.findtext("CdsDependencies") or ""
    for d in flow_sources:
        wid = (d.get("WorkflowEntityId") or d.get("FlowNameId") or "").lower()
        ok = wid in ctx["wfs"] and wid in cds.lower()
        add("APP-13", "PASS" if ok else "FAIL",
            tag + f"flow source '{d['Name']}' -> workflow {wid}: " +
            ("in solution and in CdsDependencies" if ok else "not in this solution / CdsDependencies; 'Run' won't resolve after import"))
    if flow_sources:
        add("APP-13", "MANUAL", tag + "after import, if App checker says the flow has no Run: Power Automate pane -> remove and re-add the flow")

    # APP-14 embedded list definitions vs schema
    if ARGS.schema:
        schema = json.load(open(ARGS.schema))
        for d in sp_sources:
            lst = schema.get(d["Name"])
            if not lst:
                add("APP-14", "FAIL", tag + f"data source {d['Name']} not in schema file")
                continue
            meta = list((d.get("DataEntityMetadataJson") or {}).values())
            meta = json.loads(meta[0]) if meta and isinstance(meta[0], str) else (meta[0] if meta else {})
            props = meta.get("schema", {}).get("items", {}).get("properties", {})
            n_before = sum(r["status"] == "FAIL" for r in RESULTS)
            for col, typ in lst["columns"].items():
                pv = props.get(col)
                if pv is None:
                    add("APP-14", "FAIL", tag + f"{d['Name']}.{col}: in schema but not in the app's embedded definition")
                    continue
                got = classify(pv)
                if typ not in got:
                    add("APP-14", "FAIL", tag + f"{d['Name']}.{col}: app expects {got}, schema says {typ}")
            if sum(r["status"] == "FAIL" for r in RESULTS) == n_before:
                add("APP-14", "PASS", tag + f"{d['Name']}: embedded definition matches schema ({len(lst['columns'])} columns)")

    # PKG-05 round trip with pac
    if ARGS.pac:
        roundtrip(data, tag, controls)
    else:
        add("PKG-05", "MANUAL", tag + "round trip not run (pass --pac): pac canvas unpack -> pack -> compare every rule")


def classify(pv):
    t, f = pv.get("type"), pv.get("format")
    if t == "boolean":
        return {"Boolean"}
    if t in ("number", "integer"):
        return {"Number", "Currency", "Counter", "Integer"}
    if t == "string":
        return {"DateTime"} if f in ("date", "date-time") else {"Text", "Note", "URL"}
    sub = pv.get("properties") or pv.get("items", {}).get("properties") or {}
    multi = t == "array"
    if "Claims" in sub:
        return {"UserMulti"} if multi else {"User"}
    return {"MultiChoice", "LookupMulti"} if multi else {"Choice", "Lookup"}


def roundtrip(data, tag, controls):
    cmd = shlex.split(ARGS.pac)
    with tempfile.TemporaryDirectory() as td:
        a = os.path.join(td, "a.msapp")
        open(a, "wb").write(data)
        r1 = subprocess.run(cmd + ["canvas", "unpack", "--msapp", a, "--sources", os.path.join(td, "src")],
                            capture_output=True, text=True)
        if r1.returncode:
            add("PKG-05", "FAIL", tag + f"pac canvas unpack failed: {(r1.stdout + r1.stderr)[-400:]}")
            return
        b = os.path.join(td, "b.msapp")
        r2 = subprocess.run(cmd + ["canvas", "pack", "--sources", os.path.join(td, "src"), "--msapp", b],
                            capture_output=True, text=True)
        if r2.returncode:
            add("PKG-05", "FAIL", tag + f"pac canvas pack failed: {(r2.stdout + r2.stderr)[-400:]}")
            return
        mz = zipfile.ZipFile(b)
        after = set()
        for n in mz.namelist():
            if norm(n).startswith("Controls/"):
                for c, _ in iter_controls(json.loads(mz.read(n).decode("utf-8-sig"))["TopParent"]):
                    for rr in c.get("Rules", []):
                        after.add((c["Name"], rr["Property"], rr.get("InvariantScript", "").strip()))
        before = {(c["Name"], rr["Property"], rr.get("InvariantScript", "").strip()) for c, _ in controls for rr in c.get("Rules", [])}
        lost = before - after
        add("PKG-05", "FAIL" if lost else "PASS",
            tag + (f"{len(lost)} rules changed in the round trip, e.g. {sorted(lost)[:3]}" if lost
                   else f"round trip kept all {len(before)} rules"))


# ---------------------------------------------------------------- source, schema, docs
def check_src():
    if not ARGS.src:
        return
    es = [os.path.join(dp, f) for dp, _, fs in os.walk(ARGS.src) for f in fs if f.endswith(".editorstate.json")]
    add("APP-04", "FAIL" if es else "PASS",
        f"source folder: {len(es)} EditorState files" + (": delete them before pac canvas pack, or pac adds no theme defaults (black controls)" if es else ""))


def check_schema():
    if not ARGS.schema:
        add("SP-01", "MANUAL", "no --schema: write lists.json (every list/library, kind, internal column names and types) "
                               "and keep display name = internal name")
        return
    schema = json.load(open(ARGS.schema))
    bad = [f"{l}.{c}" for l, v in schema.items() for c in v["columns"] if re.match(r"field_\d+$", c) or " " in c]
    add("SP-01", "FAIL" if bad else "PASS",
        "schema internal names " + (f"not safe: {bad}" if bad else "are plain identifiers (no field_N, no spaces)"))
    kinds = {l: v.get("kind") for l, v in schema.items()}
    nokind = [l for l, k in kinds.items() if k not in ("list", "library")]
    add("SP-02", "FAIL" if nokind else "PASS",
        "every entry says list or library" + (f"; missing for {nokind}" if nokind else ""))
    if not ARGS.tenant_fields:
        add("SP-03", "MANUAL", "real site not compared: have the user export fields per list "
                               "(Get-PnPField -List <name> | Select InternalName,Title,TypeAsString | Export-Csv <name>.csv) "
                               "and re-run with --tenant-fields")
        return
    for lst, v in schema.items():
        n_before = sum(r["status"] == "FAIL" for r in RESULTS)
        p = os.path.join(ARGS.tenant_fields, f"{lst}.csv")
        if not os.path.exists(p):
            add("SP-03", "FAIL", f"{lst}: no export at {p} (list not created yet?)")
            continue
        rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
        real = {r["InternalName"]: r for r in rows}
        is_lib = "FileLeafRef" in real
        if (v.get("kind") == "library") != is_lib:
            add("SP-02", "FAIL", f"{lst}: schema says {v.get('kind')} but the site has a {'library' if is_lib else 'list'}; "
                                 "recreate it (the environment variable can't be switched after import)")
        for col, typ in v["columns"].items():
            r = real.get(col)
            if not r:
                alt = [x["InternalName"] for x in rows if x.get("Title") == col]
                add("SP-03", "FAIL", f"{lst}.{col}: missing on site" + (f" (display name exists with internal name {alt}: "
                                     "column was created with another name or by Excel import)" if alt else ""))
            elif r.get("TypeAsString") != typ:
                add("SP-03", "FAIL", f"{lst}.{col}: site type {r.get('TypeAsString')}, needs {typ}")
            elif r.get("Title") != col:
                add("SP-03", "WARN", f"{lst}.{col}: display name '{r.get('Title')}' differs; formulas use display names after Refresh")
        dup = [r["Title"] for r in rows if [x["Title"] for x in rows].count(r["Title"]) > 1 and r["Title"] in v["columns"]]
        if dup:
            add("SP-03", "FAIL", f"{lst}: duplicate display names {sorted(set(dup))}")
        if sum(r["status"] == "FAIL" for r in RESULTS) == n_before:
            add("SP-03", "PASS", f"{lst}: matches the real site ({len(v['columns'])} columns)")


def check_docs():
    if not ARGS.docs:
        add("DOC-01", "MANUAL", "no --docs: POST_IMPORT / README steps not checked")
        return
    text = ""
    for dp, _, fs in os.walk(ARGS.docs):
        for f in fs:
            if f.lower().endswith((".md", ".txt")):
                text += open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read() + "\n"
    for step, pat in DOC_STEPS.items():
        ok = re.search(pat, text)
        add("DOC-01", "PASS" if ok else "FAIL", f"docs cover: {step}" + ("" if ok else " (missing)"))
    if re.search(r"(?i)import canvas app", text) and not re.search(r"(?i)(don.?t|not|never)[^.\n]{0,60}import canvas app", text):
        add("DOC-02", "FAIL", "docs point to 'Import canvas app'; it only takes exported packages with manifest.json")
    else:
        add("DOC-02", "PASS", "docs don't send the user to 'Import canvas app'")


MANUAL_ALWAYS = [
    ("RUN-01", "Offline formula tests ran against seed data (pac power-fx run), including a row with blank Choice/metadata "
               "columns (a file uploaded straight to SharePoint must still show)"),
    ("RUN-02", "A no-SharePoint demo build of the same app (collections from seed data) opened and rendered in Studio, or "
               "the mockups were compared against the user's screenshot"),
    ("RUN-03", "Every change the user made in Studio since the last zip has been copied back into the source "
               "(a re-import overwrites the app)"),
    ("RUN-04", "Delivery message says what was NOT tested in Power Apps, and lists the post-import steps"),
]


def main():
    global ARGS
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip")
    ap.add_argument("--schema"); ap.add_argument("--tenant-fields"); ap.add_argument("--docs"); ap.add_argument("--src")
    ap.add_argument("--previous-version"); ap.add_argument("--pac")
    ap.add_argument("--blocked-ops", default="HttpRequest")
    ap.add_argument("--allow-flow-item-params", action="store_true")
    ap.add_argument("--json", action="store_true")
    ARGS = ap.parse_args()

    try:
        z = zipfile.ZipFile(ARGS.zip)
    except Exception as e:
        add("PKG-01", "FAIL", f"not a zip: {e}")
        z = None
    if z:
        ctx = check_solution(z)
        if ctx:
            check_flows(z, ctx)
            for app in ctx["apps"]:
                check_app(z, ctx, app)
    check_src(); check_schema(); check_docs()
    for cid, msg in MANUAL_ALWAYS:
        add(cid, "MANUAL", msg)

    if ARGS.json:
        print(json.dumps(RESULTS, indent=2))
    else:
        order = {"FAIL": 0, "WARN": 1, "MANUAL": 2, "PASS": 3}
        for r in sorted(RESULTS, key=lambda r: (order[r["status"]], r["id"])):
            print(f"{r['status']:<6} {r['id']:<7} {r['msg']}")
        c = {s: sum(r["status"] == s for r in RESULTS) for s in order}
        print(f"\n{c['FAIL']} FAIL, {c['WARN']} WARN, {c['MANUAL']} MANUAL, {c['PASS']} PASS")
    sys.exit(1 if any(r["status"] == "FAIL" for r in RESULTS) else 0)


if __name__ == "__main__":
    main()
