"""Render reference mockups of every JQC/PWI Management screen (HTML -> PNG).

These are drawings of the intended design, not Power Apps screenshots: same layout as
app/screens.py (nav rail / bottom bar, header, body), same theme colours as the named
formulas, same labels, and the fictional seed data with the statuses from
seed/expected-results.md (computed here with the app's rules).

Output: docs/mockups/*.png  (desktop 1366x768, plus phone 390x844 for a few screens)
Usage:  python3 tools/render_mockups.py      (needs Playwright + Chromium)
"""
import csv
import datetime
import html
import os

import json
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "docs", "mockups")
TODAY = datetime.date.today()
E = html.escape

C = dict(primary="#1F5FAD", bg="#F4F6F9", panel="#FFFFFF", border="#DDE2E8", text="#1F2937", muted="#5B6472",
         nav="#13325B", navact="#2C5C99", green="#1E7B34", greenbg="#E7F4EA", amber="#8A5100", amberbg="#FFF4E0",
         red="#B42318", redbg="#FDECEA", grey="#5F6773", greybg="#F1F2F4")
STYLE = {"Signed Off": ("green", "greenbg"), "Overdue": ("red", "redbg"), "Re-Sign Required": ("amber", "amberbg"),
         "Needs Training": ("amber", "amberbg"), "In Training": ("amber", "amberbg"), "Pending": ("amber", "amberbg"),
         "Not Assigned": ("grey", "greybg"), "In Training – Waiting on Supervisor": ("amber", "amberbg"),
         "Will be created": ("green", "greenbg"), "Already assigned": ("grey", "greybg")}

# ------------------------------------------------------------------ seed data + app rules
rows = lambda f: list(csv.DictReader(open(os.path.join(REPO, "seed", f), encoding="utf-8")))
EMPS, DOCS, ASG = rows("employees.csv"), rows("documents.csv"), rows("assignments.csv")
EMP = {e["Email"]: e for e in EMPS}
DOC = {d["DocNumber"]: d for d in DOCS}
ACTIVE_DOCS = [d for d in DOCS if d["Status"] == "Active"]
ELIGIBLE = [e for e in EMPS if e["Active"] == "TRUE" and e["AppRole"] != "Viewer"]
CUR = {(a["EmployeeEmail"], a["DocNumber"]): a for a in ASG if a["IsCurrent"] == "TRUE"}


def due(a):
    return TODAY + datetime.timedelta(days=int(a["DueInDays"])) if a["DueInDays"] else None


def status(email, docnum):
    a, d = CUR.get((email, docnum)), DOC[docnum]
    if not a or a["Status"] == "Removed":
        return "Not Assigned"
    if a["Status"] == "Signed Off" and a["RevisionAssigned"] == d["Revision"] and EMP[email]["Active"] == "TRUE":
        return "Signed Off"
    pend = a["Status"] in ("Assigned", "In Training")
    if pend and due(a) and due(a) < TODAY:
        return "Overdue"
    if d["DocType"] == "PWI" and pend and a["AssignmentReason"] == "Revision Change":
        return "Re-Sign Required"
    if d["DocType"] == "JQC" and a["Status"] == "Assigned":
        return "Needs Training"
    if d["DocType"] == "JQC" and a["Status"] == "In Training":
        return "In Training"
    return "Pending" if pend else "Not Assigned"


def qualified(docnum):
    return [e for e in ELIGIBLE if status(e["Email"], docnum) == "Signed Off"]


def fmt(d):
    return d.strftime("%m/%d/%Y") if d else ""


# ------------------------------------------------------------------ HTML building blocks
CSS = f"""
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: 'Segoe UI', 'Noto Sans', Arial, sans-serif; font-size: 14px; color: {C['text']}; background: {C['bg']}; }}
.app {{ display: flex; height: 100vh; }}
.rail {{ width: 220px; background: {C['nav']}; color: #fff; display: flex; flex-direction: column; flex: none; }}
.rail .t {{ height: 64px; display: flex; align-items: center; padding: 0 16px; font-weight: 600; font-size: 16px; }}
.rail .i {{ height: 48px; display: flex; align-items: center; padding: 0 16px; gap: 14px; }}
.rail .i.a {{ background: {C['navact']}; font-weight: 600; }}
.rail .ic {{ width: 22px; text-align: center; opacity: .9; }}
.rail .who {{ margin-top: auto; padding: 12px 16px 16px; font-size: 12px; line-height: 1.5; opacity: .9; }}
.main {{ flex: 1; display: flex; flex-direction: column; min-width: 0; }}
.hdr {{ height: 64px; background: {C['panel']}; border-bottom: 1px solid {C['border']}; display: flex; align-items: center; padding: 0 16px; font-size: 20px; font-weight: 600; flex: none; justify-content: space-between; }}
.hdr small {{ font-size: 12px; font-weight: 400; color: {C['muted']}; }}
.body {{ flex: 1; overflow: hidden; padding: 16px; display: flex; flex-direction: column; gap: 12px; }}
.card {{ background: {C['panel']}; border: 1px solid {C['border']}; border-radius: 8px; padding: 12px 16px; }}
.row {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
.btn {{ height: 44px; padding: 0 18px; border-radius: 6px; border: 1px solid {C['primary']}; background: {C['primary']}; color: #fff; font-weight: 600; display: inline-flex; align-items: center; }}
.btn.s {{ background: #fff; color: {C['primary']}; }}
.btn.d {{ background: #fff; color: {C['red']}; border-color: {C['red']}; }}
.btn.sm {{ height: 34px; padding: 0 12px; font-size: 13px; }}
.btn.dis {{ background: {C['greybg']}; color: {C['grey']}; border-color: {C['border']}; }}
.inp {{ height: 44px; border: 1px solid {C['border']}; border-radius: 4px; background: #fff; display: inline-flex; align-items: center; padding: 0 10px; color: {C['muted']}; min-width: 200px; justify-content: space-between; }}
.inp b {{ color: {C['text']}; font-weight: 400; }}
.chev {{ background: {C['primary']}; color: #fff; width: 30px; height: 42px; margin-right: -10px; display: flex; align-items: center; justify-content: center; border-radius: 0 4px 4px 0; }}
.cap {{ font-size: 13px; color: {C['muted']}; font-weight: 600; margin-bottom: 4px; }}
.list {{ background: {C['panel']}; border: 1px solid {C['border']}; border-radius: 8px; overflow: hidden; }}
.li {{ display: flex; align-items: center; padding: 10px 16px; border-bottom: 1px solid {C['border']}; gap: 12px; }}
.li:last-child {{ border-bottom: 0; }}
.li .m {{ flex: 1; min-width: 0; }}
.li .t1 {{ font-weight: 600; }}
.li .t2 {{ font-size: 13px; color: {C['muted']}; margin-top: 3px; }}
.chip {{ border-radius: 14px; padding: 5px 12px; font-size: 12px; font-weight: 600; white-space: nowrap; text-align: center; min-width: 130px; }}
.h {{ font-size: 16px; font-weight: 600; }}
.muted {{ color: {C['muted']}; }}
.tabs .btn {{ min-width: 120px; justify-content: center; }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 12px; }}
.tile {{ background: #fff; border: 1px solid {C['border']}; border-radius: 8px; padding: 14px 18px 14px 24px; position: relative; height: 138px; }}
.tile:before {{ content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 6px; border-radius: 8px 0 0 8px; background: var(--c); }}
.tile .n {{ font-size: 34px; font-weight: 700; color: var(--c); margin: 4px 0; }}
table.mx {{ border-collapse: collapse; background: #fff; width: 100%; }}
table.mx th, table.mx td {{ border-bottom: 1px solid {C['border']}; padding: 6px 4px; text-align: center; }}
table.mx th {{ font-size: 12px; background: #fff; }}
table.mx td.n, table.mx th.n {{ text-align: left; padding-left: 12px; font-weight: 600; width: 190px; }}
.bar {{ height: 20px; background: {C['greybg']}; position: relative; flex: 1; border-radius: 3px; }}
.bar i {{ position: absolute; left: 0; top: 0; bottom: 0; border-radius: 3px; }}
.bar u {{ position: absolute; top: -6px; bottom: -6px; width: 2px; background: {C['text']}; }}
.att {{ border: 1px dashed {C['border']}; border-radius: 4px; background: #fff; padding: 14px; color: {C['muted']}; }}
.bottom {{ height: 64px; background: {C['nav']}; display: flex; color: #fff; flex: none; }}
.bottom div {{ flex: 1; text-align: center; font-size: 10px; padding-top: 8px; }}
.bottom div.a {{ background: {C['navact']}; }}
.bottom .ic {{ font-size: 18px; display: block; margin-bottom: 4px; }}
.demo-note {{ position: fixed; right: 8px; bottom: 6px; font-size: 10px; color: #9aa3ae; }}
"""

NAV = [("home", "Home", "⌂", "MTV"), ("mytraining", "My Training", "🔖", "MT"), ("jqc", "JQCs", "✔", "MTV"),
       ("pwi", "PWIs", "📄", "MTV"), ("matrix", "Matrix", "▦", "MTV"), ("cross", "Cross-Training", "◎", "MTV"),
       ("review", "Sign-off Review", "✓", "MV"), ("employees", "Employees", "👤", "MTV"), ("assign", "Assign", "➕", "M")]
ROLE_CODE = {"Manager/Supervisor": "M", "Technician": "T", "Viewer": "V"}


def chip(s):
    f, b = STYLE.get(s, ("grey", "greybg"))
    return f'<span class="chip" style="color:{C[f]};background:{C[b]}">{E(s)}</span>'


def inp(text, value=None, chev=False, w=200):
    v = f"<b>{E(value)}</b>" if value else E(text)
    return f'<span class="inp" style="min-width:{w}px">{v}{"<span class=chev>⌄</span>" if chev else ""}</span>'


def page(title, active, body, user="manager1@contoso.com", phone=False):
    u = EMP[user]
    role = ROLE_CODE[u["AppRole"]]
    items = [n for n in NAV if role in n[3]]
    if phone:
        bottom = "".join(f'<div class="{"a" if k == active else ""}"><span class="ic">{ic}</span>{E(l)}</div>'
                         for k, l, ic, _ in items[:6])
        return (f"<html><head><meta charset=utf-8><style>{CSS}</style></head><body><div class=app><div class=main>"
                f"<div class=hdr>{E(title)}<small>{E(u['Title'])} · {E(u['AppRole'])}</small></div>"
                f"<div class=body>{body}</div><div class=bottom>{bottom}</div></div></div></body></html>")
    rail = "".join(f'<div class="i {"a" if k == active else ""}"><span class=ic>{ic}</span>{E(l)}</div>' for k, l, ic, _ in items)
    return (f"<html><head><meta charset=utf-8><style>{CSS}</style></head><body><div class=app>"
            f"<div class=rail><div class=t>JQC/PWI Management</div>{rail}<div class=who>{E(u['Title'])}<br>{E(u['AppRole'])}</div></div>"
            f"<div class=main><div class=hdr>{E(title)}</div><div class=body>{body}</div></div></div>"
            f"<div class=demo-note>Mockup with fictional data</div></body></html>")


def li(t1, t2="", right=""):
    return f'<div class=li><div class=m><div class=t1>{t1}</div><div class=t2>{t2}</div></div>{right}</div>'


# ------------------------------------------------------------------ screens
def my_items(email):
    return [(dn, status(email, dn), CUR[(email, dn)]) for (e, dn) in CUR if e == email and DOC[dn]["Status"] == "Active"]


def home(user="manager1@contoso.com", phone=False):
    u = EMP[user]
    items = my_items(user)
    pend = [x for x in items if x[2]["Status"] in ("Assigned", "In Training")]
    resign = [x for x in pend if DOC[x[0]]["DocType"] == "PWI" and x[2]["AssignmentReason"] == "Revision Change"]
    signed = [x for x in items if x[1] == "Signed Off"]
    team = [e["Email"] for e in ELIGIBLE if e["SupervisorEmail"] == user]
    team_p = [(e, dn) for (e, dn), a in CUR.items() if e in team and DOC[dn]["Status"] == "Active" and a["Status"] in ("Assigned", "In Training")]
    team_jqc = [(e, dn) for e, dn in team_p if DOC[dn]["DocType"] == "JQC" and CUR[(e, dn)]["Status"] == "Assigned"]
    gaps = [d for d in ACTIVE_DOCS if len(qualified(d["DocNumber"])) < 2]
    tiles = [("My Pending", len(pend), f"{len(resign)} need re-sign (new PWI revision)", "amber"),
             ("My Signed Off", len(signed), "on the current revision", "green")]
    if u["AppRole"] == "Manager/Supervisor":
        tiles.append(("Team Pending", len(team_p), f"{len(team_jqc)} JQCs need training", "amber"))
    tiles.append(("Coverage Gaps", len(gaps), "tasks below target of 2 qualified", "red"))
    t = "".join(f'<div class=tile style="--c:{C[c]}"><div class="muted" style="font-weight:600">{E(a)}</div>'
                f'<div class=n>{n}</div><div>{E(s)}</div></div>' for a, n, s, c in tiles)
    return page("Home", "home", f'<div class=h style="font-size:18px">Welcome, {E(u["Title"])}</div><div class=tiles>{t}</div>', user, phone)


def employees():
    rows = "".join(li(E(e["Title"]) + ("" if e["Active"] == "TRUE" else "  <span class=muted>(Inactive)</span>"),
                      f'{E(e["JobTitle"])} · {E(e["Department"])} · {E(e["Shift"])}  {E(e["Email"])}',
                      f'<span style="color:{C["primary"]};font-size:13px;width:150px;text-align:right">{E(e["AppRole"])}</span>')
                   for e in sorted([e for e in EMPS if e["Active"] == "TRUE"], key=lambda x: x["Title"]))
    form = (f'<div class=card style="width:400px;flex:none"><div class=h>Add employee</div>'
            + "".join(f'<div style="margin-top:8px"><div class=cap>{c}</div>{inp("", v, ch, 360)}</div>' for c, v, ch in [
                ("Name *", "Tech G", False), ("Email *", "techg@contoso.com", False), ("Job title *", "Production Technician", True),
                ("Department", "Production", True), ("Shift", "2nd", True), ("Supervisor", "Manager One", True),
                ("App role *", "Technician", True)])
            + '<div class=row style="margin-top:12px"><span class=btn>Save</span><span class="btn s">Cancel</span></div></div>')
    filt = (f'<div class=row>{inp("Search name or email")}{inp("", "All", True)}{inp("", "All", True)}'
            f'<span class=muted>◯ Show inactive</span><span class=btn>+ Add employee</span></div>')
    return page("Employees", "employees", f'<div class=row style="align-items:flex-start;flex-wrap:nowrap;gap:16px">'
                f'<div style="flex:1;display:flex;flex-direction:column;gap:8px">{filt}<div class=list>{rows}</div></div>{form}</div>')


def employee_detail(email="techb@contoso.com"):
    e = EMP[email]
    cur = "".join(li(f'{dn} – {E(DOC[dn]["DocTitle"])}',
                     f'Rev {a["RevisionAssigned"]}' + (f' · Due {fmt(due(a))}' if due(a) else "")
                     + (" · New Revision" if a["AssignmentReason"] == "Revision Change" and s != "Signed Off" else ""),
                     '<span class="btn d sm">Remove</span>' + chip(s)) for dn, s, a in my_items(email))
    prev = "".join(li(f'{a["DocNumber"]} Rev {a["RevisionAssigned"]} – {a["Status"]}',
                      f'Signed off {fmt(TODAY - datetime.timedelta(days=int(a["SignedOffDaysAgo"])))} by {EMP[a["SignedOffByEmail"]]["Title"]}'
                      if a["SignedOffByEmail"] else "Not signed off", '<span class="btn s sm">Open file</span>')
                   for a in ASG if a["EmployeeEmail"] == email and a["IsCurrent"] == "FALSE")
    prof = (f'<div class=card><div class=h>{E(e["Title"])}</div><div style="margin:6px 0 10px">{E(e["JobTitle"])} · {E(e["Department"])} · '
            f'Shift {E(e["Shift"])} · {E(e["AppRole"])}<br>{E(e["Email"])} · Supervisor: {E(EMP[e["SupervisorEmail"]]["Title"])}</div>'
            f'<div class=row><span class="btn s">Edit</span><span class=btn>Assign</span></div></div>')
    return page("Employee", "employees", f'{prof}<div class=h>Current assignments</div><div class=list>{cur}</div>'
                f'<div class=h>Previous revisions and history</div><div class=list>{prev}</div>')


def library(doc_type):
    rows = ""
    for d in [x for x in ACTIVE_DOCS if x["DocType"] == doc_type]:
        dn = d["DocNumber"]
        assigned = [e for e in ELIGIBLE if (e["Email"], dn) in CUR and CUR[(e["Email"], dn)]["Status"] != "Removed"]
        q = len(qualified(dn))
        nt = len([e for e in assigned if CUR[(e["Email"], dn)]["Status"] == "Assigned"])
        tr = ", ".join(EMP[t]["Title"] for t in d["TrainerEmails"].split(";") if t) or "none"
        counts = (f"{q} of {len(assigned)} qualified on current rev · {nt} Needs Training" if doc_type == "JQC"
                  else f"{q} of {len(assigned)} signed off on current rev")
        rd = fmt(TODAY - datetime.timedelta(days=int(d["RevisionDaysAgo"])))
        warn = f'<div style="color:{C["red"]};font-size:13px;margin-top:4px">No trainer — can\'t assign</div>' if tr == "none" else ""
        btns = '<span class="btn s sm">Open</span>' + ('<span class="btn s sm">Status</span>' if doc_type == "PWI" else "") \
               + '<span class="btn s sm">Edit</span><span class="btn s sm">New revision</span>'
        rows += (f'<div class=li style="display:block"><div class=t1>{dn} – {E(d["DocTitle"])}</div>'
                 f'<div class=t2>Rev {d["Revision"]} · {rd} · {E(d["Area"])} · Trainers: {E(tr)}</div>'
                 f'<div style="margin-top:4px">{counts}</div>{warn}<div class=row style="margin-top:8px">{btns}</div></div>')
    filt = (f'<div class=row>{inp("Search number or title")}{inp("", "All", True)}{inp("", "Active", True)}'
            f'<span class=btn>+ Add {doc_type}</span></div>')
    return page(f"{doc_type} Library", doc_type.lower(), f'{filt}<div class=list>{rows}</div>')


def document_edit():
    n = len([e for e in ELIGIBLE if (e["Email"], "PWI-DEMO-002") in CUR
             and CUR[(e["Email"], "PWI-DEMO-002")]["Status"] in ("Assigned", "In Training", "Signed Off")])
    form = (f'<div class=card><div class=muted style="color:{C["text"]}">Current revision: A (08/06/2026)</div>'
            f'<div style="margin-top:8px"><div class=cap>New revision *</div>{inp("", "B", False, 300)}</div>'
            f'<div style="margin-top:8px"><div class=cap>Revision notes (shown to employees) *</div>'
            f'<div class=inp style="height:80px;width:100%;align-items:flex-start;padding-top:8px"><b>Fictional change: printer calibration step added.</b></div></div>'
            f'<div style="margin-top:8px"><div class=cap>New file *</div><div class=att>📎 PWI-DEMO-002_RevB.pdf</div></div>'
            f'<div class=row style="margin-top:12px"><span class=btn>Upload New Revision</span><span class="btn s">Cancel</span></div></div>')
    confirm = (f'<div class=card style="border-color:{C["amber"]};background:{C["amberbg"]}">'
               f'<div style="font-size:15px">This will require {n} employees to sign off on Rev B.</div>'
               f'<div class=row style="margin-top:10px"><span class=btn>Confirm</span><span class="btn s">Go back</span></div></div>')
    return page("Document", "pwi", f'<div class=h>Upload new revision – PWI-DEMO-002</div>{form}{confirm}')


def assign():
    emps = ["Tech D", "Tech E"]
    pick = (f'<div class=card><div class=cap>Employees *</div><div class=inp style="width:100%"><b>Tech D ✕ &nbsp; Tech E ✕</b><span class=chev>⌄</span></div>'
            f'<div class=cap style="margin-top:8px">Documents (active, with at least one trainer) *</div>'
            f'<div class=inp style="width:100%"><b>PWI-DEMO-001 Demo Widget Torque Check ✕</b><span class=chev>⌄</span></div>'
            f'<div class=muted style="margin-top:6px">Not shown because they have no trainer: JQC-DEMO-102</div>'
            f'<div class=row style="margin-top:8px"><div><div class=cap>Trainer</div>{inp("", "Tech A", True, 260)}</div>'
            f'<div><div class=cap>Due date (optional)</div>{inp("", fmt(TODAY + datetime.timedelta(days=14)) + "  📅", False, 220)}</div></div>'
            f'<div class=row style="margin-top:10px"><span class=btn>Preview</span></div></div>')
    prev = "".join(li(f'{n} – PWI-DEMO-001 Rev B', 'Trainer: Tech A',
                      chip("Already assigned" if n == "Tech E" else "Will be created")) for n in emps)
    return page("Assign", "assign", f'{pick}<div class=h>1 will be created, 1 already assigned (skipped)</div>'
                f'<div class=list>{prev}</div><div class=row><span class=btn>Create assignments</span></div>')


def pwi_status(dn="PWI-DEMO-001"):
    d = DOC[dn]
    people = [(e, status(e["Email"], dn), CUR[(e["Email"], dn)]) for e in ELIGIBLE if (e["Email"], dn) in CUR]
    cnt = lambda s: len([p for p in people if p[1] == s])
    head = (f'<div class=card><div class=h>{dn} – {E(d["DocTitle"])} (current Rev {d["Revision"]})</div>'
            f'<div style="margin:6px 0 10px">{cnt("Signed Off")} signed off · {cnt("Re-Sign Required")} re-sign required · '
            f'{cnt("Overdue")} overdue · {cnt("Pending")} pending</div><span class=btn>Assign more employees</span></div>')
    rows = "".join(li(E(e["Title"]), f'Rev {a["RevisionAssigned"]}' + (f' · Due {fmt(due(a))}' if due(a) else ""),
                      chip(s) + '<span class="btn d sm">Remove</span>') for e, s, a in people)
    return page("PWI Status", "pwi", f'{head}<div class=list>{rows}</div>')


def my_training(user="techb@contoso.com", phone=False):
    items = [x for x in my_items(user) if x[2]["Status"] in ("Assigned", "In Training")]
    tabs = ('<div class="row tabs"><span class=btn>Pending</span><span class="btn s">Signed Off</span><span class="btn s">All</span></div>')
    cnt = f'<div class=muted>{len(items)} pending · 1 need re-sign · 1 signed off on the current revision</div>'
    rows = ""
    for dn, s, a in items:
        badge = ""
        if a["AssignmentReason"] == "Revision Change":
            b = "New Revision – Please Re-Sign" if DOC[dn]["DocType"] == "PWI" else "New Revision"
            badge = (f'<div style="color:{C["amber"]};font-weight:600;font-size:13px;margin-top:4px">{b}</div>'
                     f'<div style="font-size:13px">What changed: {E(DOC[dn]["RevisionNotes"])}</div>')
        shown = "In Training – Waiting on Supervisor" if s == "In Training" else s
        rows += (f'<div class=li style="align-items:flex-start"><div class=m><div class=t1>{dn} – {E(DOC[dn]["DocTitle"])}</div>'
                 f'<div class=t2>Rev {a["RevisionAssigned"]}' + (f' · Due {fmt(due(a))}' if due(a) else "") + f'</div>{badge}</div>{chip(shown)}</div>')
    return page("My Training", "mytraining", f'{tabs}{cnt}<div class=list>{rows}</div>', user, phone)


def assignment_detail(user="techb@contoso.com"):
    a = CUR[(user, "PWI-DEMO-001")]
    d = DOC["PWI-DEMO-001"]
    info = (f'<div class=card><div class=h>PWI-DEMO-001 – {E(d["DocTitle"])}</div>'
            f'<div style="margin:6px 0">{E(EMP[user]["Title"])} · Rev {a["RevisionAssigned"]} (current: {d["Revision"]}) · Due {fmt(due(a))} · Trainer: Tech A</div>'
            f'<div style="margin:8px 0">{chip("Re-Sign Required")}</div>'
            f'<div style="color:{C["amber"]}">New Revision – Please Re-Sign<br>What changed: {E(d["RevisionNotes"])}</div>'
            f'<div class=row style="margin-top:10px"><span class="btn s">Open document</span></div></div>')
    sign = (f'<div class=card><div class=h>Sign off this PWI</div><div class=cap style="margin-top:8px">Training log *</div>'
            f'<div class=att>📎 Choose a file (PDF, DOCX, XLSX, JPG or PNG, max 25 MB)</div>'
            f'<div class=row style="margin-top:10px"><span class=btn>Upload Training Log</span><span class="btn dis">Sign Off</span></div>'
            f'<div class=muted style="margin-top:6px">Sign Off turns on after the training log is uploaded.</div></div>')
    return page("Assignment", "mytraining", info + sign, user)


def signoff_review():
    tabs = ('<div class="row tabs"><span class="btn s">Recently Signed Off</span><span class=btn>JQCs Needing Training</span>'
            '<span class="btn s">JQCs In Training</span><span class="btn s">PWI Re-Sign Required</span><span class="btn s">Overdue</span></div>')
    filt = f'<div class=row>{inp("Employee name")}{inp("Document number")}</div>'
    rows = ""
    for (e, dn), a in CUR.items():
        if DOC[dn]["DocType"] == "JQC" and DOC[dn]["Status"] == "Active" and a["Status"] == "Assigned" and EMP[e]["Active"] == "TRUE":
            s = status(e, dn)
            rows += li(f'{E(EMP[e]["Title"])} – {dn} Rev {a["RevisionAssigned"]}', f'Due {fmt(due(a))}' if due(a) else "No due date", chip(s))
    return page("Sign-off Review", "review", f'{tabs}{filt}<div class=muted>Tap a row to open it (Put Into Training and sign-off are on the assignment).</div><div class=list>{rows}</div>')


def matrix(phone=False):
    if phone:
        rows = "".join(li(f'{d["DocNumber"]} – {E(d["DocTitle"])}', "", chip(status("techc@contoso.com", d["DocNumber"]))) for d in ACTIVE_DOCS)
        body = (f'<div class=row><span class=btn>By employee</span><span class="btn s">By document</span></div>'
                f'{inp("", "Tech C", True, 340)}<div class=list>{rows}</div>')
        return page("Training Matrix", "matrix", body, phone=True)
    filt = (f'<div class=row>{inp("", "Type: All", True, 150)}{inp("", "Area: All", True, 150)}{inp("", "Department: All", True, 160)}'
            f'{inp("", "Shift: All", True, 140)}{inp("", "Supervisor: All", True, 160)}<span class=muted>◯ Re-Sign Required only</span></div>')
    pager = '<div class=row><span class=btn>Apply filters</span><span class="btn s dis">◀ Previous</span><span class="btn s">Next ▶</span><span class=muted>Documents 1–6 of 6 · 7 employees</span></div>'
    th = "".join(f'<th>{d["DocNumber"]}<br><span class=muted>Rev {d["Revision"]}</span></th>' for d in ACTIVE_DOCS)
    trs = "".join(f'<tr><td class=n>{E(e["Title"])}</td>' + "".join(f'<td>{chip(status(e["Email"], d["DocNumber"]))}</td>' for d in ACTIVE_DOCS) + "</tr>"
                  for e in sorted(ELIGIBLE, key=lambda x: x["Title"]))
    return page("Training Matrix", "matrix", f'{filt}{pager}<div class=list><table class=mx><tr><th class=n class=muted>Employee</th>{th}</tr>{trs}</table></div>')


def cross_training():
    tabs = ('<div class="row tabs"><span class=btn>Coverage by task</span><span class="btn s">Single points of failure</span>'
            '<span class="btn s">Coverage by shift</span><span class="btn s">Employee breadth</span></div>')
    cov = []
    for d in ACTIVE_DOCS:
        q = len(qualified(d["DocNumber"]))
        pend = len([e for e in ELIGIBLE if (e["Email"], d["DocNumber"]) in CUR and CUR[(e["Email"], d["DocNumber"])]["AssignmentReason"] == "Revision Change"
                    and status(e["Email"], d["DocNumber"]) != "Signed Off"])
        cov.append((q < 2, q, d, pend))
    cov.sort(key=lambda x: (not x[0], x[1]))
    mx = max(2, max(c[1] for c in cov))
    rows = "".join(
        f'<div class=li style="display:block"><div class=t1>{d["DocNumber"]} – {E(d["DocTitle"])}</div>'
        f'<div class=row style="flex-wrap:nowrap;margin-top:6px"><div class=bar><i style="width:{q / mx * 100}%;background:{C["red"] if below else C["green"]}"></i>'
        f'<u style="left:{2 / mx * 100}%"></u></div><span style="width:170px;text-align:right;font-weight:600;color:{C["red"] if below else C["green"]}">'
        f'{q} / 2{"  Below target" if below else ""}</span></div><div class=t2>{pend} pending after a revision</div></div>'
        for below, q, d, pend in cov)
    summ = '<div>3 tasks below the target of 2 qualified · 2 single points of failure</div><div class=muted>Tap a red task to assign it.</div>'
    return page("Cross-Training", "cross", f'{tabs}{summ}<div class=list>{rows}</div>')


SCREENS = [
    ("01_scrHome", lambda: home()), ("02_scrMyTraining", lambda: my_training()),
    ("03_scrAssignmentDetail", lambda: assignment_detail()), ("04_scrJQCLibrary", lambda: library("JQC")),
    ("05_scrPWILibrary", lambda: library("PWI")), ("06_scrDocumentEdit", document_edit),
    ("07_scrPWIStatus", lambda: pwi_status()), ("08_scrEmployees", employees),
    ("09_scrEmployeeDetail", lambda: employee_detail()), ("10_scrAssign", assign), ("11_scrMatrix", lambda: matrix()),
    ("12_scrCrossTraining", cross_training), ("13_scrSignoffReview", signoff_review),
]
PHONE = [("phone_scrHome", lambda: home("techb@contoso.com", phone=True)),
         ("phone_scrMyTraining", lambda: my_training(phone=True)), ("phone_scrMatrix", lambda: matrix(phone=True))]


NODE_SHOT = r"""
const { chromium } = require('playwright');
const jobs = JSON.parse(process.argv[2]);
(async () => {
  const b = await chromium.launch();
  for (const j of jobs) {
    const p = await b.newPage({ viewport: { width: j.w, height: j.h }, deviceScaleFactor: 2 });
    await p.goto('file://' + j.html);
    await p.screenshot({ path: j.png });
    await p.close();
    console.log('wrote', j.png.split('/').pop());
  }
  await b.close();
})();
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(REPO, "docs", "mockups", ".html")
    os.makedirs(tmp, exist_ok=True)
    jobs = []
    for (w, h), items in (((1366, 768), SCREENS), ((390, 844), PHONE)):
        for name, fn in items:
            path = os.path.join(tmp, name + ".html")
            open(path, "w", encoding="utf-8").write(fn())
            jobs.append({"w": w, "h": h, "html": path, "png": os.path.join(OUT, name + ".png")})
    js = os.path.join(tmp, "shot.js")
    open(js, "w").write(NODE_SHOT)
    subprocess.run(["node", js, json.dumps(jobs)], check=True)


if __name__ == "__main__":
    main()
