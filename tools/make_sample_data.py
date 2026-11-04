"""Build manual-load sample data from the fictional seed: an Excel workbook + placeholder files.

Output (seed/sample-data/):
  JQCPWI_SampleData.xlsx   one sheet per list/library, headers = SharePoint display names,
                           values ready to paste into SharePoint "Edit in grid view"
  files/JP_Documents/*.pdf       placeholder documents to upload to the JP_Documents library
  files/JP_SignoffRecords/*.pdf  placeholder evidence to upload to JP_SignoffRecords

Everything is fictional. The People sheet lets the user map each fictional person to a real
test account *in their own copy* (Person columns only accept real users); that copy must not be
committed.

Usage: python3 tools/make_sample_data.py
"""
import csv
import datetime
import os
import shutil

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(REPO, "seed")
OUT = os.path.join(SEED, "sample-data")
FONT = "Arial"
HEAD = PatternFill("solid", fgColor="13325B")
INPUT = PatternFill("solid", fgColor="FFFF00")
BASE_DATE = datetime.date.today()

rows = lambda f: list(csv.DictReader(open(os.path.join(SEED, f), encoding="utf-8")))
EMPS, DOCS, ASG = rows("employees.csv"), rows("documents.csv"), rows("assignments.csv")
EMP = {e["Email"]: e for e in EMPS}
DOC = {d["DocNumber"]: d for d in DOCS}


# ------------------------------------------------------------------ placeholder PDF
def pdf(lines):
    safe = []
    for line in lines:
        a = "".join(ch if 32 <= ord(ch) < 127 else "-" for ch in line)
        a = a.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        safe.append(f"({a}) Tj T*")
    content = "BT /F1 14 Tf 72 720 Td 20 TL\n" + "\n".join(safe) + "\nET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            f"<< /Length {len(content)} >>\nstream\n{content}\nendstream", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = "%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n"
    x = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offs)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n"
    return out.encode("ascii")


# ------------------------------------------------------------------ workbook helpers
def sheet(wb, title, headers, widths=None):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=i)
        c.font = Font(name=FONT, bold=True, color="FFFFFF")
        c.fill = HEAD
        c.alignment = Alignment(vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = (widths or {}).get(h, max(14, len(h) + 4))
    ws.freeze_panes = "A2"
    return ws


def style_rows(ws, date_cols=(), datetime_cols=(), input_cols=()):
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = Font(name=FONT)
            col = ws.cell(row=1, column=c.column).value
            if col in date_cols:
                c.number_format = "mm/dd/yyyy"
            if col in datetime_cols:
                c.number_format = "mm/dd/yyyy hh:mm"
            if col in input_cols:
                c.fill = INPUT


def col(ws, name):
    for c in ws[1]:
        if c.value == name:
            return get_column_letter(c.column)
    raise KeyError(name)


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "files", "JP_Documents"))
    os.makedirs(os.path.join(OUT, "files", "JP_SignoffRecords"))
    wb = Workbook()
    rm = wb.active
    rm.title = "Read Me"

    # ---------------- People (inputs)
    pp = sheet(wb, "People", ["Fictional person", "Seed email", "Your test account email (optional)", "Email to use"],
               {"Fictional person": 20, "Seed email": 28, "Your test account email (optional)": 36, "Email to use": 34})
    for i, e in enumerate(EMPS, 2):
        pp.append([e["Title"], e["Email"], None, f'=IF(C{i}="",B{i},LOWER(C{i}))'])
    style_rows(pp, input_cols=("Your test account email (optional)",))
    pp["C1"].comment = Comment("Yellow = fill in. Map each fictional person to a different real test account in your "
                               "tenant (Person columns only accept real users). Map Manager One to YOUR account so the "
                               "app recognises you as a manager. Leave blank to keep the fictional email.", "Sample data")
    np = len(EMPS) + 1

    def person(seed_email_expr):
        """Formula: seed email -> mapped email (People sheet)."""
        return f"IFERROR(INDEX(People!$D$2:$D${np},MATCH({seed_email_expr},People!$B$2:$B${np},0)),\"\")"

    # ---------------- JP_Employees
    em = sheet(wb, "JP_Employees", ["Title", "Email", "EmployeeUser", "JobTitle", "Department", "Shift", "Supervisor",
                                    "AppRole", "Active"], {"Email": 30, "EmployeeUser": 30, "JobTitle": 22, "AppRole": 20})
    for e in EMPS:
        r = em.max_row + 1
        sup = EMP[e["SupervisorEmail"]]["Title"] if e["SupervisorEmail"] else None
        em.append([e["Title"], f'={person(repr(e["Email"]).replace(chr(39), chr(34)))}', f"=B{r}", e["JobTitle"],
                   e["Department"], e["Shift"], sup, e["AppRole"], "Yes" if e["Active"] == "TRUE" else "No"])
    style_rows(em)

    # ---------------- JP_Documents (library)
    dc = sheet(wb, "JP_Documents", ["SharePoint ID", "File to upload", "Title", "DocType", "DocNumber", "DocTitle", "Revision",
                                    "RevisionDate", "RevisionNotes", "Area", "Status", "Trainers", "Description"],
               {"File to upload": 22, "DocTitle": 28, "RevisionNotes": 50, "Trainers": 46, "Description": 60})
    for i, d in enumerate(DOCS, 1):
        name = d["DocNumber"] + ".pdf"
        trainers = [t for t in d["TrainerEmails"].split(";") if t]
        tr = "&\"; \"&".join(f"{person(chr(34) + t + chr(34))}" for t in trainers)
        dc.append([i, name, d["DocNumber"], d["DocType"], d["DocNumber"], d["DocTitle"], d["Revision"],
                   f"='Read Me'!$B$4-{int(d['RevisionDaysAgo'])}", d["RevisionNotes"], d["Area"], d["Status"],
                   (f"={tr}" if trainers else None), d["Description"]])
        open(os.path.join(OUT, "files", "JP_Documents", name), "wb").write(pdf([
            "FICTIONAL SAMPLE FILE - NOT A REAL DOCUMENT", "JQC/PWI Management sample data", "",
            f"{'JQC template' if d['DocType'] == 'JQC' else 'Process work instruction'} {d['DocNumber']}  Rev {d['Revision']}",
            d["DocTitle"], "", "Revision notes: " + d["RevisionNotes"]]))
    style_rows(dc, date_cols=("RevisionDate",), input_cols=("SharePoint ID",))
    dc["A1"].comment = Comment("Yellow = check. The item ID SharePoint gives each file after upload (List settings or the "
                               "ID column). 1-7 assumes a brand-new library with files uploaded in this order.", "Sample data")
    nd = len(DOCS) + 1

    # ---------------- JP_Assignments
    heads = ["SharePoint ID", "Title", "Employee", "EmployeeEmail", "DocumentID", "DocType", "DocNumber", "DocTitle",
             "RevisionAssigned", "AssignmentReason", "PreviousAssignmentID", "IsCurrent", "AssignedBy", "AssignedDate",
             "DueDate", "Trainer", "Status", "SignedOffBy", "SignedOffDate", "SignoffFileID", "Comments"]
    asg = sheet(wb, "JP_Assignments", heads, {"Title": 34, "EmployeeEmail": 28, "DocTitle": 26, "AssignedBy": 28,
                                             "Trainer": 28, "SignedOffBy": 28, "Comments": 50, "AssignmentReason": 18})
    key_row = {a["Key"]: i + 2 for i, a in enumerate(ASG)}
    sign_row = {}
    srecs = [a for a in ASG if a["SignedOffByEmail"]]
    for j, a in enumerate(srecs):
        sign_row[a["Key"]] = j + 2
    for i, a in enumerate(ASG, 1):
        r = i + 1
        d = DOC[a["DocNumber"]]
        e = EMP[a["EmployeeEmail"]]
        q = lambda s: '"' + s + '"'
        asg.append([
            i,
            f'{a["DocNumber"]} Rev {a["RevisionAssigned"]} – {e["Title"]}',
            e["Title"],
            f"={person(q(a['EmployeeEmail']))}",
            f'=INDEX(JP_Documents!$A$2:$A${nd},MATCH(G{r},JP_Documents!$E$2:$E${nd},0))',
            d["DocType"], a["DocNumber"], d["DocTitle"], a["RevisionAssigned"], a["AssignmentReason"],
            (f"=A{key_row[a['PreviousKey']]}" if a["PreviousKey"] else None),
            "Yes" if a["IsCurrent"] == "TRUE" else "No",
            f"={person(q(a['AssignedByEmail']))}",
            f"='Read Me'!$B$4-{int(a['AssignedDaysAgo'])}",
            (f"='Read Me'!$B$4+{int(a['DueInDays'])}" if a["DueInDays"] else None),
            (f"={person(q(a['TrainerEmail']))}" if a["TrainerEmail"] else None),
            a["Status"],
            (f"={person(q(a['SignedOffByEmail']))}" if a["SignedOffByEmail"] else None),
            (f"='Read Me'!$B$4-{int(a['SignedOffDaysAgo'])}+TIME(10,0,0)" if a["SignedOffByEmail"] else None),
            (f"=JP_SignoffRecords!A{sign_row[a['Key']]}" if a["Key"] in sign_row else None),
            a["Comments"] or None])
    style_rows(asg, date_cols=("AssignedDate", "DueDate"), datetime_cols=("SignedOffDate",), input_cols=("SharePoint ID",))
    asg["A1"].comment = Comment("Yellow = check. The ID SharePoint gives each row. 1-29 assumes a brand-new list with rows "
                                "pasted in this order. PreviousAssignmentID and the sign-off sheet use these IDs.", "Sample data")

    # ---------------- JP_SignoffRecords (library)
    so = sheet(wb, "JP_SignoffRecords", ["SharePoint ID", "File to upload", "Title", "AssignmentID", "DocType", "Revision",
                                         "EmployeeEmail", "UploadedBy"],
               {"File to upload": 44, "Title": 40, "EmployeeEmail": 28, "UploadedBy": 28})
    for j, a in enumerate(srecs, 1):
        d = DOC[a["DocNumber"]]
        e_idx = EMPS.index(EMP[a["EmployeeEmail"]]) + 1
        when = BASE_DATE - datetime.timedelta(days=int(a["SignedOffDaysAgo"]))
        name = f"{a['DocNumber']}_Rev{a['RevisionAssigned']}_{e_idx}_{when:%Y%m%d}_100000.pdf"
        q = lambda s: '"' + s + '"'
        so.append([j, name, name[:-4], f"=JP_Assignments!A{key_row[a['Key']]}", d["DocType"], a["RevisionAssigned"],
                   f"={person(q(a['EmployeeEmail']))}", f"={person(q(a['SignedOffByEmail']))}"])
        open(os.path.join(OUT, "files", "JP_SignoffRecords", name), "wb").write(pdf([
            "FICTIONAL SAMPLE FILE - NOT A REAL RECORD", "JQC/PWI Management sample data", "",
            f"{'Signed JQC' if d['DocType'] == 'JQC' else 'PWI training log'}  {a['DocNumber']}  Rev {a['RevisionAssigned']}",
            d["DocTitle"], f"Employee: {EMP[a['EmployeeEmail']]['Title']}", f"Signed off: {when:%Y-%m-%d}"]))
    style_rows(so, input_cols=("SharePoint ID",))
    so["A1"].comment = Comment("Yellow = check. The item ID SharePoint gives each file after upload. 1-18 assumes a "
                               "brand-new library with files uploaded in this order.", "Sample data")

    # ---------------- JP_Settings
    st = sheet(wb, "JP_Settings", ["Title", "MinQualifiedPerTask", "ResignDueDays"])
    st.append(["Settings", 2, 14])
    style_rows(st)

    # ---------------- Read Me
    rm.column_dimensions["A"].width = 30
    rm.column_dimensions["B"].width = 100
    lines = [
        ("JQC/PWI Management – sample data", None),
        ("All names, emails and documents are FICTIONAL.", None),
        ("", None),
        ("Base date (yellow, edit if you like)", BASE_DATE),
        ("", None),
        ("Legend", "Yellow cells are the only cells to edit. Everything else is calculated: copy and paste the values."),
        ("1. People", "Optional: put a real test account next to each fictional person (Manager One = your own account). "
                      "Person columns only accept real users. Don't share your filled-in copy."),
        ("2. JP_Settings", "Check the single row exists: Settings, 2, 14."),
        ("3. JP_Employees", "List → Edit in grid view → paste columns Title to Active (one column at a time is safest). "
                            "Supervisor is a lookup: paste the name, e.g. Manager One."),
        ("4. JP_Documents", "Upload the files from files/JP_Documents in this order, then Edit in grid view and paste "
                            "the columns from Title onward. Note each file's ID and correct the yellow SharePoint ID column if needed."),
        ("5. JP_Assignments", "Edit in grid view → paste Title to Comments, in row order. Then check the yellow SharePoint ID "
                              "column matches the IDs SharePoint gave (PreviousAssignmentID and sign-off links use them)."),
        ("6. JP_SignoffRecords", "Upload the files from files/JP_SignoffRecords in this order, then paste Title onward in grid view."),
        ("7. JP_Assignments again", "If any sign-off file got a different ID, re-paste the SignoffFileID column."),
        ("Expected results", "seed/expected-results.md lists what every screen should show with this data."),
        ("Tip", "Person columns (EmployeeUser, Trainers, AssignedBy, Trainer, SignedOffBy, UploadedBy) resolve only real "
                "accounts. If you skip the People mapping, leave those columns empty; the app still works for testing "
                "statuses, the matrix and cross-training."),
    ]
    for a, b in lines:
        rm.append([a, b])
    for row in rm.iter_rows():
        for c in row:
            c.font = Font(name=FONT, bold=(c.column == 1))
            c.alignment = Alignment(wrap_text=True, vertical="top")
    rm["A1"].font = Font(name=FONT, bold=True, size=14)
    rm["B4"].fill = INPUT
    rm["B4"].number_format = "mm/dd/yyyy"
    path = os.path.join(OUT, "JQCPWI_SampleData.xlsx")
    wb.save(path)
    print("wrote", path)


if __name__ == "__main__":
    main()
