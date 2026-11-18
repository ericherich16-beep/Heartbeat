#!/usr/bin/env python3
"""Build the NPI Tracker importable solution from the working 1.1.0.3 package.

Usage: python3 -I build.py <base-solution.zip> <output-dir>

Rules this build follows (from the 1.1.0.0-1.1.0.3 failures):
  * Start from the last package that imported and opened in the tenant.
  * Change only Src/*.pa.yaml plus version/description metadata.
    The msapp loads from YAML (packed.json LoadFromYaml=true); Controls/*.json are placeholders.
  * No new connectors or data sources. Same four SharePoint lists and the NPICreateProject flow.
  * Only control types/versions that already opened in 1.1.0.3, and only known properties.
  * Keep the msapp entry names (literal backslashes) and entry order exactly as they were.
  * The NPICreateProject flow JSON is copied byte-for-byte.
"""
import datetime
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

import yaml

VERSION = "1.2.0.1"
LABEL = "NPI Tracker 1.2.0.1 - Overview and Project details redesign"
HERE = Path(__file__).resolve().parent
SRC = HERE / "src"

# ---------------------------------------------------------------- placeholders
CANREVIEW = (
    "Set(varCanReview, varIsQEorQM && !(varRow.IndependentReview && "
    "(Lower(Coalesce(varRow.Assignee.Email, \"\")) = varMe || "
    "EndsWith(Lower(Coalesce(varRow.Assignee.Claims, \"\")), \"|\" & varMe) || "
    "Lower(Coalesce(varRow.UploadedBy.Email, \"\")) = varMe || "
    "EndsWith(Lower(Coalesce(varRow.UploadedBy.Claims, \"\")), \"|\" & varMe))))"
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


def render_detail():
    t = (SRC / "scrProjectDetail.template.yaml").read_text()
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
    assert "__" not in t.replace("'@odata.type'", ""), "unreplaced placeholder"
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
DATA_SOURCES = {"'NPI Projects'", "'Project Requirements'", "'NPI Activity Log'", "'NPI Role Defaults'"}


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
        if q not in DATA_SOURCES and q != "'@odata.type'":
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
            errs.append(f"{name}: control type {ctype} not proven in 1.1.0.3")
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
    return errs, len(controls)


# ---------------------------------------------------------------- packaging
def main(base_zip, out_dir):
    out_dir = Path(out_dir)
    work = out_dir / "work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    screens = {
        "Src\\scrProjects.pa.yaml": (SRC / "scrProjects.pa.yaml").read_text(),
        "Src\\scrProjectDetail.pa.yaml": render_detail(),
    }
    app_yaml = (SRC / "App.pa.yaml").read_text()
    errs, count = validate(app_yaml, screens)
    if errs:
        print("VALIDATION FAILED")
        print("\n".join(errs))
        sys.exit(1)
    print(f"validation passed: {count} controls")
    (SRC / "generated").mkdir(exist_ok=True)
    (SRC / "generated" / "scrProjectDetail.pa.yaml").write_text(screens["Src\\scrProjectDetail.pa.yaml"])

    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    stamp_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp_us = now.strftime("%m/%d/%Y %H:%M:%S")

    base = zipfile.ZipFile(base_zip)
    msapp_name = "CanvasApps/ericp_npitracker_i1_DocumentUri.msapp"
    old_msapp = zipfile.ZipFile(__import__("io").BytesIO(base.read(msapp_name)))

    new_entries = {}
    for info in old_msapp.infolist():
        data = old_msapp.read(info.filename)
        n = info.filename
        if n == "Src\\App.pa.yaml":
            data = app_yaml.encode("utf-8")
        elif n in screens:
            data = screens[n].encode("utf-8")
        elif n == "Header.json":
            h = json.loads(data)
            h["LastSavedDateTimeUTC"] = stamp_us
            data = json.dumps(h, indent=2).encode("utf-8")
        elif n == "packed.json":
            p = json.loads(data)
            p["LastPackedDateTimeUtc"] = stamp_iso
            p["PackingClient"]["Version"] = VERSION
            data = json.dumps(p, indent=2).encode("utf-8")
        elif n == "Properties.json":
            p = json.loads(data)
            p["AppDescription"] = (
                "NPI Tracker 1.2.0.1: overview with highlights and gate progress; project details with gate strip, "
                "document list, action panel, details and activity views. Built on 1.1.0.3."
            )
            p["DefaultConnectedDataSourceMaxGetRowsCount"] = 2000
            p["ControlCount"] = count_types(screens)
            data = json.dumps(p, indent=2).encode("utf-8")
        new_entries[n] = (info, data)

    msapp_path = work / "app.msapp"
    with zipfile.ZipFile(msapp_path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, (info, data) in new_entries.items():
            zi = zipfile.ZipInfo(n, date_time=now.timetuple()[:6])
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)

    sol_name = f"EricP_NPITrackerIncrement1_{VERSION.replace('.', '_')}.zip"
    sol_path = out_dir / sol_name
    with zipfile.ZipFile(sol_path, "w", zipfile.ZIP_DEFLATED) as z:
        for info in base.infolist():
            n = info.filename
            data = base.read(n)
            if n == msapp_name:
                data = msapp_path.read_bytes()
            elif n == "solution.xml":
                s = data.decode("utf-8")
                s = re.sub(r"<Version>[^<]*</Version>", f"<Version>{VERSION}</Version>", s)
                s = s.replace('description="NPI Tracker Increment 2a"', f'description="{LABEL}"')
                s = re.sub(
                    r'<Description description="[^"]*" languagecode="1033" />',
                    '<Description description="NPI Tracker 1.2.0.1: Overview and Project details redesign built on '
                    'the working 1.1.0.3 package. NPICreateProject is unchanged from the working 1.0.0.8 export." '
                    'languagecode="1033" />',
                    s,
                    count=1,
                )
                data = s.encode("utf-8")
            elif n == "customizations.xml":
                s = data.decode("utf-8")
                s = re.sub(r"<AppVersion>[^<]*</AppVersion>", f"<AppVersion>{stamp_iso}</AppVersion>", s)
                s = re.sub(
                    r"<Description>NPI Tracker[^<]*</Description>",
                    "<Description>NPI Tracker 1.2.0.1: Overview and Project details redesign.</Description>",
                    s,
                )
                data = s.encode("utf-8")
            zi = zipfile.ZipInfo(n, date_time=now.timetuple()[:6] if n in (msapp_name, "solution.xml", "customizations.xml") else info.date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)
    shutil.rmtree(work)
    print(f"wrote {sol_path}")


def count_types(screens):
    counts = {"screen": len(screens)}
    key = {"Label@2.5.1": "label", "Classic/Button@2.2.0": "button", "Classic/TextInput@2.3.2": "textInput",
           "Gallery@2.15.0": "gallery", "Rectangle@2.3.0": "rectangle"}
    def w(ch):
        for item in ch:
            (_, spec), = item.items()
            k = key[spec["Control"]]
            counts[k] = counts.get(k, 0) + 1
            w(spec.get("Children") or [])
    for text in screens.values():
        doc = yaml.safe_load(text)
        (_, s), = doc["Screens"].items()
        w(s["Children"])
    return counts


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
