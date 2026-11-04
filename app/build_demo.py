"""Build the DEMO version of JQC/PWI Management: same screens and formulas, no SharePoint.

Purpose: prove the app itself works in Power Apps Studio before anyone spends time on
SharePoint lists. If the demo opens without formula errors, any remaining errors in the
real app come from the lists, not from the app.

What changes compared with the real app
- The five SharePoint lists become in-memory collections (colEmployees, colDocuments,
  colAssignments, colSignoffRecords, colSettings), filled from the fictional seed CSVs in
  App.OnStart, with exactly the column shapes the real lists have.
- Choices([@JP_x].Column) becomes a fixed table of the schema's choice values.
- A "Sign in as" dropdown on Home lets you try every role (fxMeEmail uses it).
- Uploads are turned off (the flow isn't included). Everything else, including assigning,
  editing, removing, Put Into Training and revisions without files, works on the demo data.
- New rows get an ID (collections don't number rows themselves).

Output
  solution/dist/JQCPWIDemo_<version>_unmanaged.zip  (its own solution; doesn't touch the real one)

Usage
  PAC="python3 /path/to/pac.py" python3 app/build_demo.py
"""
import csv
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SEED = os.path.join(REPO, "seed")
DEMO_PROJECT = os.path.join(REPO, "solution", "JQCPWIDemo")
DIST = os.path.join(REPO, "solution", "dist")
VERSION = "1.0.4.0"

sys.path.insert(0, HERE)
import build_app as B      # noqa: E402
import screens as S        # noqa: E402

B.DEMO = True
B.BUILD = os.path.join(HERE, "build_demo")
B.SRC = os.path.join(B.BUILD, "src")
B.MSAPP = os.path.join(B.BUILD, "JQCPWIManagement_Demo.msapp")
B.APP_SCHEMA_NAME = "jp_jqcpwidemo_4c2d1"
B.APP_DISPLAY_NAME = "JQC/PWI Management (Demo)"
B.APP_DESCRIPTION = "Demo of JQC/PWI Management with built-in fictional data. No SharePoint, no uploads."

RENAME = {"JP_Employees": "colEmployees", "JP_Documents": "colDocuments", "JP_Assignments": "colAssignments",
          "JP_SignoffRecords": "colSignoffRecords", "JP_Settings": "colSettings"}
SCHEMA = B.load_schema()


def fx_str(s):
    return '"' + str(s).replace('"', '""') + '"'


def demo_fx(text):
    """Turn a formula written for SharePoint into the demo (collections) version."""
    def choices(m):
        lst, col = m.group(1), m.group(2)
        f = next(x for x in SCHEMA["JP_" + lst]["Fields"] if x["Name"] == col)
        return "Table(" + ", ".join("{Value: " + fx_str(c) + "}" for c in f["Choices"]) + ")"
    text = re.sub(r"Choices\(\[@JP_(\w+)\]\.(\w+)\)", choices, text)
    for a, b in RENAME.items():
        text = re.sub(r"\b" + a + r"\b", b, text)
    text = re.sub(r"Patch\((col\w+), Defaults\(\1\), \{", r"Patch(\1, Defaults(\1), {ID: Max(\1, ID) + 1, ", text)
    text = re.sub(r"Refresh\(col\w+\)", "true", text)
    text = text.replace("fxMeEmail = Lower(User().Email);", "fxMeEmail = Lower(Coalesce(gblDemoUser, User().Email));")
    return text


def transform(ctrl):
    for k, v in list(ctrl.props.items()):
        if isinstance(v, str):
            ctrl.props[k] = demo_fx(v)
    for ch in ctrl.children:
        transform(ch)


# ---------------------------------------------------------------- seed data -> OnStart
def person(email, name):
    if not email:
        return "Blank()"
    return (f'{{Claims: {fx_str("i:0#.f|membership|" + email)}, DisplayName: {fx_str(name)}, Email: {fx_str(email)}, '
            f'Department: "", JobTitle: "", Picture: ""}}')


def days(n, now=False):
    if n == "" or n is None:
        return "Blank()"
    fn = "Now()" if now else "Today()"
    return f"DateAdd({fn}, {-int(n)}, TimeUnit.Days)"


def seed_onstart():
    rows = lambda f: list(csv.DictReader(open(os.path.join(SEED, f), encoding="utf-8")))
    emps, docs, asg = rows("employees.csv"), rows("documents.csv"), rows("assignments.csv")
    emp_id = {e["Email"]: i + 1 for i, e in enumerate(emps)}
    emp_name = {e["Email"]: e["Title"] for e in emps}
    doc_id = {d["DocNumber"]: i + 1 for i, d in enumerate(docs)}
    doc_by = {d["DocNumber"]: d for d in docs}
    blank_people = f"Filter(Table({person('x@contoso.com', 'x')}), false)"
    out = []

    recs = []
    for e in emps:
        sup = e["SupervisorEmail"]
        recs.append("{" + ", ".join([
            f"ID: {emp_id[e['Email']]}", f"Title: {fx_str(e['Title'])}", f"Email: {fx_str(e['Email'])}",
            f"EmployeeUser: {person(e['Email'], e['Title'])}",
            f"JobTitle: {{Value: {fx_str(e['JobTitle'])}}}", f"Department: {{Value: {fx_str(e['Department'])}}}",
            f"Shift: {{Value: {fx_str(e['Shift'])}}}", f"AppRole: {{Value: {fx_str(e['AppRole'])}}}",
            f"Active: {'true' if e['Active'] == 'TRUE' else 'false'}",
            (f"Supervisor: {{Id: {emp_id[sup]}, Value: {fx_str(emp_name[sup])}}}" if sup else "Supervisor: Blank()"),
        ]) + "}")
    out.append("ClearCollect(colEmployees, " + ", ".join(recs) + ")")

    recs = []
    for d in docs:
        trainers = [t for t in d["TrainerEmails"].split(";") if t]
        tr = ("Table(" + ", ".join(person(t, emp_name[t]) for t in trainers) + ")") if trainers else blank_people
        name = d["DocNumber"] + ".pdf"
        recs.append("{" + ", ".join([
            f"ID: {doc_id[d['DocNumber']]}", f"Title: {fx_str(d['DocNumber'])}", f"'{{Name}}': {fx_str(name)}",
            f"'{{Link}}': {fx_str('https://contoso.sharepoint.com/sites/JQCPWI-Demo/JP_Documents/' + name)}",
            f"DocType: {{Value: {fx_str(d['DocType'])}}}", f"DocNumber: {fx_str(d['DocNumber'])}",
            f"DocTitle: {fx_str(d['DocTitle'])}", f"Revision: {fx_str(d['Revision'])}",
            f"RevisionDate: {days(d['RevisionDaysAgo'])}", f"RevisionNotes: {fx_str(d['RevisionNotes'])}",
            f"Area: {{Value: {fx_str(d['Area'])}}}", f"Status: {{Value: {fx_str(d['Status'])}}}",
            f"Trainers: {tr}", f"Description: {fx_str(d['Description'])}",
        ]) + "}")
    out.append("ClearCollect(colDocuments, " + ", ".join(recs) + ")")

    # sign-off records first (assignments point to them)
    sign_id, srecs = {}, []
    for a in asg:
        if a["SignedOffByEmail"]:
            n = len(srecs) + 1
            sign_id[a["Key"]] = n
            dt = doc_by[a["DocNumber"]]["DocType"]
            srecs.append("{" + ", ".join([
                f"ID: {n}", f"Title: {fx_str(a['Key'])}", f"AssignmentID: {asg.index(a) + 1}",
                f"DocType: {{Value: {fx_str(dt)}}}", f"Revision: {fx_str(a['RevisionAssigned'])}",
                f"EmployeeEmail: {fx_str(a['EmployeeEmail'])}",
                f"UploadedBy: {person(a['SignedOffByEmail'], emp_name[a['SignedOffByEmail']])}",
                f"'{{Link}}': {fx_str('https://contoso.sharepoint.com/sites/JQCPWI-Demo/JP_SignoffRecords/' + a['Key'] + '.pdf')}",
            ]) + "}")
    out.append("ClearCollect(colSignoffRecords, " + ", ".join(srecs) + ")")

    key_id = {a["Key"]: i + 1 for i, a in enumerate(asg)}
    recs = []
    for i, a in enumerate(asg, 1):
        d = doc_by[a["DocNumber"]]
        e = a["EmployeeEmail"]
        recs.append("{" + ", ".join([
            f"ID: {i}", f"Title: {fx_str(a['DocNumber'] + ' Rev ' + a['RevisionAssigned'] + ' - ' + emp_name[e])}",
            f"Employee: {{Id: {emp_id[e]}, Value: {fx_str(emp_name[e])}}}", f"EmployeeEmail: {fx_str(e)}",
            f"DocumentID: {doc_id[a['DocNumber']]}", f"DocType: {{Value: {fx_str(d['DocType'])}}}",
            f"DocNumber: {fx_str(a['DocNumber'])}", f"DocTitle: {fx_str(d['DocTitle'])}",
            f"RevisionAssigned: {fx_str(a['RevisionAssigned'])}",
            f"AssignmentReason: {{Value: {fx_str(a['AssignmentReason'])}}}",
            f"PreviousAssignmentID: {key_id[a['PreviousKey']] if a['PreviousKey'] else 'Blank()'}",
            f"IsCurrent: {'true' if a['IsCurrent'] == 'TRUE' else 'false'}",
            f"AssignedBy: {person(a['AssignedByEmail'], emp_name[a['AssignedByEmail']])}",
            f"AssignedDate: {days(a['AssignedDaysAgo'])}",
            f"DueDate: {('DateAdd(Today(), ' + str(int(a['DueInDays'])) + ', TimeUnit.Days)') if a['DueInDays'] else 'Blank()'}",
            f"Trainer: {person(a['TrainerEmail'], emp_name.get(a['TrainerEmail'], ''))}",
            f"Status: {{Value: {fx_str(a['Status'])}}}",
            f"SignedOffBy: {person(a['SignedOffByEmail'], emp_name.get(a['SignedOffByEmail'], ''))}",
            f"SignedOffDate: {days(a['SignedOffDaysAgo'], now=True)}",
            f"SignoffFileID: {sign_id.get(a['Key'], 'Blank()')}",
            f"Comments: {fx_str(a['Comments'])}", f"Modified: {days(a['AssignedDaysAgo'], now=True)}",
        ]) + "}")
    out.append("ClearCollect(colAssignments, " + ", ".join(recs) + ")")
    out.append('ClearCollect(colSettings, {ID: 1, Title: "Settings", MinQualifiedPerTask: 2, ResignDueDays: 14})')
    out.append('Set(gblDemoUser, "manager1@contoso.com")')
    return out


# ---------------------------------------------------------------- build hooks
orig_build = S.build


def demo_build(mod):
    screens = orig_build(mod)
    for scr in screens:
        transform(scr)
    home = next(s for s in screens if s.name == "scrHome")
    body = home.children[0].children[1].children[1]          # conRoot -> conMain -> conBody
    picker = B.C("drpDemoUser", "dropdown", {
        "Items": "colEmployees", "Value": '"Email"', "Default": "gblDemoUser", "OnChange": "Set(gblDemoUser, Self.Selected.Email)",
        "Font": B.FONT, "Size": 14, "Color": "clrText", "BorderColor": "clrBorder", "Height": 44, "Width": 300,
        "FillPortions": 0, "AccessibleLabel": B.q("Sign in as")})
    body.children.insert(0, B.hbox("conDemoBar", [
        B.label("lblDemo", B.q("DEMO MODE (fictional data, uploads off). Sign in as:"), size=14, bold=True,
                color="clrAmber", Height=44, Width=420, FillPortions=0, VerticalAlign="VerticalAlign.Middle"),
        picker], Height=56, FillPortions=0, LayoutGap=12, LayoutAlignItems="LayoutAlignItems.Center",
        Fill="clrAmberBg", PaddingLeft=12, LayoutWrap="true"))
    return screens


S.build = demo_build
orig_formulas = B.formulas_text
B.formulas_text = lambda: demo_fx(orig_formulas())
SEED_LINES = seed_onstart()
B.APP_ONSTART = B.APP_ONSTART + ";\n// Demo data (fictional seed)\n" + ";\n".join(SEED_LINES)


def no_data_sources(schema):
    os.makedirs(os.path.join(B.SRC, "Connections"))
    json.dump({}, open(os.path.join(B.SRC, "Connections", "Connections.json"), "w"))
    return {}


B.write_data_sources = no_data_sources


def pac():
    return shlex.split(os.environ.get("PAC", "pac"))


def check_formulas_offline():
    """Run the demo seed + every named formula with pac power-fx: catches type/shape errors."""
    # The runner can't create collections with ClearCollect; load the same data with Set(name, Table(...)).
    lines = [re.sub(r"^ClearCollect\((\w+), (.*)\)$", r"Set(\1, Table(\2))", l, flags=re.S) for l in SEED_LINES]
    text = re.sub(r"//[^\n]*", "", B.formulas_text())
    for m in re.finditer(r"(?ms)^([A-Za-z_]\w*)\s*=\s*(.*?);\s*(?=^[A-Za-z_]\w*\s*=|\Z)", text):
        expr = m.group(2).replace("User().Email", '"x@contoso.com"').replace("User().FullName", '"Demo"')
        expr = expr.replace("App.Width", "1366")
        expr = re.sub(r"Icon\.([A-Za-z]+)", r'"\1"', expr)
        lines.append(f"Set({m.group(1)}, {re.sub(r'\s*\n\s*', ' ', expr)})")
    with tempfile.NamedTemporaryFile("w", suffix=".fx", delete=False, encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
        path = fh.name
    res = subprocess.run(pac() + ["power-fx", "run", "--file", path], capture_output=True)
    os.unlink(path)
    out = (res.stdout + res.stderr).replace(b"\x00", b"").decode("utf-8", "replace")
    errs = [l.strip() for l in out.splitlines() if "Error" in l]
    if errs:
        print("Offline formula check FAILED:")
        for e in errs[:20]:
            print("   ", e)
        sys.exit(1)
    print(f"Offline formula check: demo data + {len(lines) - len(SEED_LINES)} named formulas, no errors")


def write_demo_solution():
    if not os.path.isdir(DEMO_PROJECT):
        res = subprocess.run(pac() + ["solution", "init", "--publisher-name", "JQCPWIManagement", "--publisher-prefix", "jp",
                                      "--outputDirectory", DEMO_PROJECT], capture_output=True, text=True)
        if res.returncode != 0:
            sys.exit(res.stdout + res.stderr)
    src = os.path.join(DEMO_PROJECT, "src")
    # canvas app files (no connection references, no environment variables)
    canvas = os.path.join(src, "CanvasApps")
    if os.path.isdir(canvas):
        shutil.rmtree(canvas)
    B.SOLUTION_CANVAS = canvas
    B.write_solution_app({"dataSources": [], "datasets": {B.PLACEHOLDER_SITE: {"dataSources": {}}}})
    meta_path = os.path.join(canvas, f"{B.APP_SCHEMA_NAME}.meta.xml")
    meta = open(meta_path, encoding="utf-8").read()
    meta = re.sub(r"<ConnectionReferences>.*?</ConnectionReferences>", "<ConnectionReferences>{}</ConnectionReferences>", meta, flags=re.S)
    meta = re.sub(r"<CdsDependencies>.*?</CdsDependencies>",
                  '<CdsDependencies>{"cdsdependencies":[]}</CdsDependencies>', meta, flags=re.S)
    open(meta_path, "w", encoding="utf-8").write(meta)
    # Customizations.xml needs <CanvasApps /> or the packer drops the app
    cpath = os.path.join(src, "Other", "Customizations.xml")
    cx = open(cpath, encoding="utf-8-sig").read()
    if "<CanvasApps" not in cx:
        cx = cx.replace("  <EntityDataProviders />", "  <EntityDataProviders />\n  <CanvasApps />", 1)
        open(cpath, "w", encoding="utf-8").write(cx)
    # Solution.xml: names, same publisher as the main solution, root component
    spath = os.path.join(src, "Other", "Solution.xml")
    sx = open(spath, encoding="utf-8-sig").read()
    main = open(os.path.join(REPO, "solution", "JQCPWIManagement", "src", "Other", "Solution.xml"), encoding="utf-8-sig").read()
    prefix = re.search(r"<CustomizationOptionValuePrefix>(\d+)<", main).group(1)
    sx = re.sub(r"<CustomizationOptionValuePrefix>\d+<", f"<CustomizationOptionValuePrefix>{prefix}<", sx)
    sx = sx.replace("<UniqueName>JQCPWIDemo</UniqueName>", "<UniqueName>JQCPWIDemo</UniqueName>", 1)
    head, sep, pub = sx.partition("<Publisher>")
    head = re.sub(r'<LocalizedName description="[^"]*" languagecode="1033" />',
                  '<LocalizedName description="JQC/PWI Management - Demo" languagecode="1033" />', head, count=1)
    head = re.sub(r"<Version>[^<]*</Version>", f"<Version>{VERSION}</Version>", head, count=1)
    pub = re.sub(r'<LocalizedName description="[^"]*" languagecode="1033" />',
                 '<LocalizedName description="JQC/PWI Management" languagecode="1033" />', pub, count=1)
    sx = head + sep + pub
    sx = re.sub(r"<RootComponents\s*/>|<RootComponents>.*?</RootComponents>",
                f'<RootComponents>\n      <RootComponent type="300" schemaName="{B.APP_SCHEMA_NAME}" behavior="0" />\n    </RootComponents>',
                sx, count=1, flags=re.S)
    open(spath, "w", encoding="utf-8").write(sx)
    # pack + verify
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, f"JQCPWIDemo_{VERSION.replace('.', '_')}_unmanaged.zip")
    if os.path.exists(out):
        os.remove(out)
    res = subprocess.run(pac() + ["solution", "pack", "--zipfile", out, "--folder", src, "--packagetype", "Unmanaged"],
                         capture_output=True, text=True)
    if res.returncode != 0 or not os.path.exists(out):
        sys.exit(res.stdout[-3000:] + res.stderr[-3000:])
    spec = importlib.util.spec_from_file_location("solution_build", os.path.join(REPO, "solution", "build.py"))
    sb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sb)
    sb.verify(out)
    print("Built:", os.path.relpath(out, REPO))


def main():
    check_formulas_offline()
    screens, _ = B.write_sources(SCHEMA)
    print(f"Demo sources written: {len(screens)} screens, no data sources")
    B.run(["canvas", "pack", "--sources", B.SRC, "--msapp", B.MSAPP])
    print("Packed:", os.path.relpath(B.MSAPP, REPO))
    B.round_trip_check(screens)
    write_demo_solution()


if __name__ == "__main__":
    main()
