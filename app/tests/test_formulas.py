"""Test the app's named formulas against the seed data, offline, with `pac power-fx run`.

How it works
  - Loads the fictional seed CSVs (seed/*.csv) and turns them into Power Fx tables that
    look like the SharePoint data sources (Choice -> {Value}, Lookup -> {Id, Value}, ...).
  - Takes the named formulas from app/build_app.py (the exact text compiled into the app)
    and evaluates them in order with Set(), after replacing the few canvas-only
    functions (User(), App.Width, Icon.*) with test values.
  - Signs in as each seed user and checks the home tiles, the matrix cells and the
    cross-training numbers against seed/expected-results.md.

Usage
  PAC="python3 /path/to/pac.py" python3 app/tests/test_formulas.py
Exit code 0 = all checks passed.
"""
import csv
import datetime
import importlib.util
import os
import re
import shlex
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SEED = os.path.join(REPO, "seed")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


app = load(os.path.join(REPO, "app", "build_app.py"), "build_app")
TODAY = datetime.date.today()


def fx_str(s):
    return '"' + str(s).replace('"', '""') + '"'


def fx_date(d):
    return f"Date({d.year},{d.month},{d.day})" if d else "Blank()"


def rows(name):
    return list(csv.DictReader(open(os.path.join(SEED, name), encoding="utf-8")))


def build_tables():
    emps, docs, asg = rows("employees.csv"), rows("documents.csv"), rows("assignments.csv")
    emp_id = {e["Email"]: i + 1 for i, e in enumerate(emps)}
    emp_title = {e["Email"]: e["Title"] for e in emps}
    doc_id = {d["DocNumber"]: i + 1 for i, d in enumerate(docs)}
    out = []
    recs = []
    for e in emps:
        sup = e["SupervisorEmail"]
        recs.append("{" + ", ".join([
            f"ID: {emp_id[e['Email']]}", f"Title: {fx_str(e['Title'])}", f"Email: {fx_str(e['Email'])}",
            f"JobTitle: {{Value: {fx_str(e['JobTitle'])}}}", f"Department: {{Value: {fx_str(e['Department'])}}}",
            f"Shift: {{Value: {fx_str(e['Shift'])}}}", f"AppRole: {{Value: {fx_str(e['AppRole'])}}}",
            f"Active: {'true' if e['Active'] == 'TRUE' else 'false'}",
            f"Supervisor: {{Id: {emp_id[sup] if sup else 0}, Value: {fx_str(emp_title.get(sup, ''))}}}",
        ]) + "}")
    out.append("Set(JP_Employees, Table(" + ", ".join(recs) + "))")
    recs = []
    for d in docs:
        recs.append("{" + ", ".join([
            f"ID: {doc_id[d['DocNumber']]}", f"Title: {fx_str(d['DocNumber'])}", f"DocNumber: {fx_str(d['DocNumber'])}",
            f"DocTitle: {fx_str(d['DocTitle'])}", f"DocType: {{Value: {fx_str(d['DocType'])}}}",
            f"Revision: {fx_str(d['Revision'])}", f"Status: {{Value: {fx_str(d['Status'])}}}",
            f"Area: {{Value: {fx_str(d['Area'])}}}",
        ]) + "}")
    out.append("Set(JP_Documents, Table(" + ", ".join(recs) + "))")
    recs = []
    for i, a in enumerate(asg, 1):
        due = TODAY + datetime.timedelta(days=int(a["DueInDays"])) if a["DueInDays"] else None
        dtype = next(d["DocType"] for d in docs if d["DocNumber"] == a["DocNumber"])
        recs.append("{" + ", ".join([
            f"ID: {i}", f"Title: {fx_str(a['Key'])}",
            f"Employee: {{Id: {emp_id[a['EmployeeEmail']]}, Value: {fx_str(emp_title[a['EmployeeEmail']])}}}",
            f"EmployeeEmail: {fx_str(a['EmployeeEmail'])}", f"DocumentID: {doc_id[a['DocNumber']]}",
            f"DocType: {{Value: {fx_str(dtype)}}}", f"DocNumber: {fx_str(a['DocNumber'])}",
            f"RevisionAssigned: {fx_str(a['RevisionAssigned'])}",
            f"AssignmentReason: {{Value: {fx_str(a['AssignmentReason'])}}}",
            f"IsCurrent: {'true' if a['IsCurrent'] == 'TRUE' else 'false'}",
            f"Status: {{Value: {fx_str(a['Status'])}}}", f"DueDate: {fx_date(due)}",
        ]) + "}")
    out.append("Set(JP_Assignments, Table(" + ", ".join(recs) + "))")
    out.append("Set(JP_Settings, Table({ID: 1, Title: \"Settings\", MinQualifiedPerTask: 2, ResignDueDays: 14}))")
    return out, emps, docs, emp_id, doc_id


def named_formulas():
    """Split App.Formulas into (name, expression) in order."""
    text = app.formulas_text()
    text = re.sub(r"//[^\n]*", "", text)
    parts = []
    for m in re.finditer(r"(?ms)^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?);\s*(?=^[A-Za-z_][A-Za-z0-9_]*\s*=|\Z)", text):
        parts.append((m.group(1), m.group(2).strip()))
    return parts


def to_test_expr(expr, me_email):
    expr = expr.replace("User().Email", fx_str(me_email))
    expr = expr.replace("User().FullName", fx_str("Test User"))
    expr = expr.replace("App.Width", "1366")
    expr = re.sub(r"Icon\.([A-Za-z]+)", r'"\1"', expr)          # canvas-only enum
    return re.sub(r"\s*\n\s*", " ", expr)                         # the runner reads one statement per line


def pac_run(lines):
    with tempfile.NamedTemporaryFile("w", suffix=".fx", delete=False, encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
        path = f.name
    pac = shlex.split(os.environ.get("PAC", "pac"))
    res = subprocess.run(pac + ["power-fx", "run", "--file", path, "--echo"], capture_output=True)
    os.unlink(path)
    out = (res.stdout + res.stderr).replace(b"\x00", b"").decode("utf-8", "replace")
    return out


def main():
    tables, emps, docs, emp_id, doc_id = build_tables()
    formulas = named_formulas()
    print(f"{len(formulas)} named formulas, {len(emps)} employees, {len(docs)} documents")

    expected_home = {   # seed/expected-results.md section 4
        "manager1@contoso.com": (2, 1, 0, 6, 3), "supervisor2@contoso.com": (1, 0, 0, 2, 0),
        "techa@contoso.com": (1, 0, 1, 0, 0), "techb@contoso.com": (2, 1, 1, 0, 0),
        "techc@contoso.com": (2, 1, 2, 0, 0), "techd@contoso.com": (0, 0, 3, 0, 0),
        "teche@contoso.com": (2, 0, 2, 0, 0), "viewer1@contoso.com": (0, 0, 0, 0, 0),
    }
    expected_matrix = {   # section 1 (employee, doc) -> status; omitted = Not Assigned
        ("manager1@contoso.com", "PWI-DEMO-001"): "Re-Sign Required", ("manager1@contoso.com", "JQC-DEMO-101"): "In Training",
        ("supervisor2@contoso.com", "JQC-DEMO-100"): "Needs Training",
        ("techa@contoso.com", "PWI-DEMO-001"): "Signed Off", ("techa@contoso.com", "JQC-DEMO-100"): "Needs Training",
        ("techb@contoso.com", "PWI-DEMO-001"): "Re-Sign Required", ("techb@contoso.com", "PWI-DEMO-002"): "Signed Off",
        ("techb@contoso.com", "JQC-DEMO-100"): "In Training",
        ("techc@contoso.com", "PWI-DEMO-001"): "Re-Sign Required", ("techc@contoso.com", "PWI-DEMO-002"): "Signed Off",
        ("techc@contoso.com", "JQC-DEMO-100"): "Signed Off", ("techc@contoso.com", "JQC-DEMO-101"): "Overdue",
        ("techd@contoso.com", "PWI-DEMO-002"): "Signed Off", ("techd@contoso.com", "PWI-DEMO-003"): "Signed Off",
        ("techd@contoso.com", "JQC-DEMO-101"): "Signed Off",
        ("teche@contoso.com", "PWI-DEMO-001"): "Pending", ("teche@contoso.com", "PWI-DEMO-002"): "Overdue",
        ("teche@contoso.com", "PWI-DEMO-003"): "Signed Off", ("teche@contoso.com", "JQC-DEMO-101"): "Signed Off",
    }
    expected_coverage = {"PWI-DEMO-001": 1, "PWI-DEMO-002": 3, "PWI-DEMO-003": 2,
                         "JQC-DEMO-100": 1, "JQC-DEMO-101": 2, "JQC-DEMO-102": 0}

    failures = 0
    for me, exp in expected_home.items():
        lines = list(tables)
        for name, expr in formulas:
            lines.append(f"Set({name}, {to_test_expr(expr, me)})")
        marker = "##"
        # Home screen tile table (screen formula, not a named formula): must evaluate without errors.
        lines.append("Set(testTiles, " + to_test_expr(app.HOME_TILES, me) + ")")
        lines.append(f'"{marker}TILES|" & CountRows(testTiles)')
        lines.append(f'"{marker}HOME|" & CountRows(fxMyPending) & "|" & fxMyResignCount & "|" & CountRows(fxMySignedOff)'
                     f' & "|" & CountRows(fxTeamPending) & "|" & CountRows(fxTeamJqcNeedsTraining) & "|" & fxRole'
                     f' & "|" & CountRows(fxCoverageGaps) & "|" & CountRows(fxNavItems)')
        if me == "manager1@contoso.com":
            active_rows = [e for e in emps if e["Active"] == "TRUE" and e["AppRole"] != "Viewer"]
            active_docs = [d for d in docs if d["Status"] == "Active"]
            for e in active_rows:
                for d in active_docs:
                    lines.append(f'"{marker}CELL|{e["Email"]}|{d["DocNumber"]}|" & Coalesce(LookUp(fxAssignmentDisplayStatus, '
                                 f'Employee.Id = {emp_id[e["Email"]]} && DocumentID = {doc_id[d["DocNumber"]]} && EmpIsActive, '
                                 f'DisplayStatus), "Not Assigned")')
            for d in active_docs:
                lines.append(f'"{marker}COV|{d["DocNumber"]}|" & LookUp(fxTaskCoverage, ID = {doc_id[d["DocNumber"]]}, Qualified)')
        out = pac_run(lines)
        errors = [l for l in out.splitlines() if re.search(r"\bError\b", l)]
        if errors:
            print(f"Power Fx errors (signed in as {me}):")
            for l in errors[:15]:
                print("   ", l.strip())
            return 1
        vals = {}
        for l in out.splitlines():
            if l.startswith(">>"):
                continue   # echoed input line
            m = re.search(r'"?##(\w+)\|([^"]*)"?', l)
            if m:
                vals.setdefault(m.group(1), []).append(m.group(2).split("|"))
        home = vals.get("HOME", [[]])[0]
        got = tuple(int(x) for x in home[:5]) if len(home) >= 5 else None
        role = home[5] if len(home) > 5 else "?"
        if got != exp:
            print(f"FAIL home tiles {me} ({role}): got {got}, expected {exp}"); failures += 1
        else:
            print(f"ok   home tiles {me:26} {role:19} pending/resign/signed/team/teamJQC = {got}, gaps = {home[6]}, nav items = {home[7]}")
        if home and home[6] != "3":
            print(f"FAIL coverage gaps: got {home[6]}, expected 3"); failures += 1
        for email, doc, status in vals.get("CELL", []):
            want = expected_matrix.get((email, doc), "Not Assigned")
            if status != want:
                print(f"FAIL matrix {email} {doc}: got {status}, expected {want}"); failures += 1
        tiles_n = vals.get("TILES", [["?"]])[0][0]
        want_tiles = {"Manager/Supervisor": "4", "Technician": "3", "Viewer": "1"}.get(role)
        if tiles_n != want_tiles:
            print(f"FAIL home tile count {me}: got {tiles_n}, expected {want_tiles}"); failures += 1
        if vals.get("CELL"):
            print(f"ok   matrix: {len(vals['CELL'])} cells checked")
        for doc, n in vals.get("COV", []):
            if int(n) != expected_coverage[doc]:
                print(f"FAIL coverage {doc}: got {n}, expected {expected_coverage[doc]}"); failures += 1
        if vals.get("COV"):
            print(f"ok   coverage: {len(vals['COV'])} tasks checked")
    print("ALL PASSED" if failures == 0 else f"{failures} FAILURE(S)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
