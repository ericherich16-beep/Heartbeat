"""Generate the JQC/PWI Management canvas app and add it to the solution.

Pipeline (CLAUDE.md Section 4, decision D-02)
  1. Write Power Apps source files (.fx.yaml, data sources, manifest) into
     app/build/src, using control templates from app/template/ (taken from
     Microsoft and PnP public samples).
  2. `pac canvas pack` -> app/build/JQCPWIManagement.msapp
  3. Round-trip check: `pac canvas unpack` the .msapp and compare every control
     property with the sources, so nothing is silently dropped.
  4. Copy the .msapp into the solution project
     (solution/JQCPWIManagement/src/CanvasApps/) with a .meta.xml whose SharePoint
     connection references are bound to the environment variables
     (datasetOverride / tableNameOverride). No site URL or list ID is stored:
     the placeholders below are fictional and are replaced by the variables.
  5. Write app/App.fx.md (named formulas, role logic, status logic, theme,
     navigation) from the same formula text, so the doc never drifts.

Then run `python3 solution/build.py` to pack the solution zip.

Usage
  PAC="python3 /path/to/pac.py" python3 app/build_app.py
"""
import datetime
import importlib.util
import json
import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
import uuid
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TEMPLATE = os.path.join(HERE, "template")
BUILD = os.path.join(HERE, "build")
SRC = os.path.join(BUILD, "src")
MSAPP = os.path.join(BUILD, "JQCPWIManagement.msapp")
SOLUTION_CANVAS = os.path.join(REPO, "solution", "JQCPWIManagement", "src", "CanvasApps")

APP_SCHEMA_NAME = "jp_jqcpwimanagement_7b3e1"
APP_DISPLAY_NAME = "JQC/PWI Management"
APP_DESCRIPTION = ("Job qualification checklists (JQC) and process work instructions (PWI): "
                   "assignments, sign-offs, re-signs after revisions, training matrix and cross-training.")
NS = uuid.UUID("2d0e4c8a-91f5-4b7e-8a3c-5f1d2e6b7a90")      # fixed namespace: stable IDs across builds
SP_API = "/providers/microsoft.powerapps/apis/shared_sharepointonline"
# Fictional placeholders. At runtime the environment variables replace them (see .meta.xml).
PLACEHOLDER_SITE = "https://contoso.sharepoint.com/sites/JQCPWI"
SP_CONNECTION_ID = str(uuid.uuid5(NS, "connection:sharepoint"))
FLOW_CONNECTION_ID = str(uuid.uuid5(NS, "connection:logicflows"))
FLOW_DS_NAME = "JQCPWI-UploadFile"          # name Studio gives "JQCPWI - Upload File" when the flow is added
FLOW_WORKFLOW_ID = str(uuid.UUID("f64e5b50-4ba1-5706-a620-0ec628dbede8"))   # flows/build_flow.py FLOW_ID
LOGICFLOWS_API = "/providers/microsoft.powerapps/apis/shared_logicflows"

ENV_SITE = "jp_SiteUrl"
DATA_SOURCES = [   # (data source name in the app = list title, environment variable)
    ("JP_Employees", "jp_ListEmployees"),
    ("JP_Documents", "jp_LibDocuments"),
    ("JP_Assignments", "jp_ListAssignments"),
    ("JP_SignoffRecords", "jp_LibSignoffs"),
    ("JP_Settings", "jp_ListSettings"),
]


def load_schema():
    """The list schema lives in solution/build_setup.py (single Python source)."""
    spec = importlib.util.spec_from_file_location("build_setup", os.path.join(REPO, "solution", "build_setup.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {l["Title"]: l for l in mod.LISTS}


def gid(*parts):
    return str(uuid.uuid5(NS, ":".join(parts)))


# =============================================================================
# 1. Power Fx: named formulas (App.Formulas) — also rendered into App.fx.md
# =============================================================================
FORMULA_SECTIONS = [
    ("Identity and role (CLAUDE.md Section 5, SPEC.md BR-01)", """
// Signed-in user, matched on JP_Employees.Email (indexed text column: delegable).
fxMeEmail = Lower(User().Email);
fxMe = LookUp(JP_Employees, Email = fxMeEmail);
fxMeActive = !IsBlank(fxMe) && fxMe.Active;
// No match, or inactive employee -> Viewer.
fxRole = If(fxMeActive, fxMe.AppRole.Value, "Viewer");
fxIsManager = fxRole = "Manager/Supervisor";
fxIsTechnician = fxRole = "Technician";
fxIsViewer = Not(fxIsManager || fxIsTechnician);
fxIsRegistered = fxMeActive;
// Person value for AssignedBy / SignedOffBy (SharePoint Person column format).
fxMePerson = {
    Claims: "i:0#.f|membership|" & fxMeEmail,
    DisplayName: Coalesce(fxMe.Title, User().FullName),
    Email: fxMeEmail,
    Department: "",
    JobTitle: "",
    Picture: ""
};
"""),
    ("Settings (JP_Settings, single row)", """
fxSettings = First(JP_Settings);
// TODO: confirm defaults 2 and 14 (CLAUDE.md Section 19).
fxMinQualified = Coalesce(fxSettings.MinQualifiedPerTask, 2);
fxResignDueDays = Coalesce(fxSettings.ResignDueDays, 14);
"""),
    ("Layout breakpoints (responsive, CLAUDE.md Section 3)", """
fxIsPhone = App.Width < 640;
fxIsWide = App.Width >= 1024;
"""),
    ("Theme (CLAUDE.md Section 14: colors only here, never on controls)", """
clrPrimary = ColorValue("#1F5FAD");
clrPrimaryDark = ColorValue("#174A87");
clrBg = ColorValue("#F4F6F9");
clrPanel = Color.White;
clrBorder = ColorValue("#DDE2E8");
clrText = ColorValue("#1F2937");
clrMuted = ColorValue("#5B6472");
clrNavBg = ColorValue("#13325B");
clrNavActive = ColorValue("#2C5C99");
clrNavText = Color.White;
// Status colors: text colors meet 4.5:1 on their background.
clrGreen = ColorValue("#1E7B34");
clrGreenBg = ColorValue("#E7F4EA");
clrAmber = ColorValue("#8A5100");
clrAmberBg = ColorValue("#FFF4E0");
clrRed = ColorValue("#B42318");
clrRedBg = ColorValue("#FDECEA");
clrGrey = ColorValue("#5F6773");
clrGreyBg = ColorValue("#F1F2F4");
"""),
    ("Core data (delegation notes)", """
// Delegable filters on indexed Choice / Yes-No columns.
fxDocsActive = Filter(JP_Documents, Status.Value = "Active");
fxEmployeesActive = Filter(JP_Employees, Active = true);
// People who can be assigned documents or be trainers (Viewers can't, SPEC.md A-08).
fxEligibleEmployees = Filter(fxEmployeesActive, AppRole.Value <> "Viewer");
fxManagers = Filter(fxEmployeesActive, AppRole.Value = "Manager/Supervisor");
// Shifts that have at least one eligible employee (cross-training "coverage by shift").
fxShifts = Filter(Distinct(fxEligibleEmployees, Shift.Value), !IsBlank(Value));
// Current assignment rows only (IsCurrent is indexed). Everything built on top of this
// (AddColumns, LookUp into collections) is NOT delegable, so it works on the first
// 2,000 current rows (app setting "Data row limit" = 2000). Documented in Admin-Guide.md.
fxAssignmentsCurrent = Filter(JP_Assignments, IsCurrent = true);
"""),
    ("fxAssignmentDisplayStatus (CLAUDE.md Section 8, SPEC.md BR-40/BR-41)", """
// One row per current assignment, with the display status and helper flags.
// Precedence: Signed Off -> Overdue -> Re-Sign Required -> Needs Training -> In Training -> Pending.
fxAssignmentDisplayStatus =
    With(
        {docs: fxDocsActive, emps: fxEmployeesActive},
        AddColumns(
            AddColumns(
                AddColumns(
                    AddColumns(
                        fxAssignmentsCurrent As a,
                        CurrentRevision, LookUp(docs, ID = a.DocumentID, Revision),
                        DocIsActive, !IsBlank(LookUp(docs, ID = a.DocumentID, ID)),
                        EmpIsActive, !IsBlank(LookUp(emps, ID = a.Employee.Id, ID)),
                        StatusText, a.Status.Value,
                        DocTypeText, a.DocType.Value,
                        IsRevisionChange, a.AssignmentReason.Value = "Revision Change"
                    ) As b,
                    // Qualified = signed off on the CURRENT revision, active employee and document (BR-40).
                    IsQualified, b.StatusText = "Signed Off" && b.RevisionAssigned = b.CurrentRevision && b.EmpIsActive && b.DocIsActive,
                    IsPending, b.StatusText = "Assigned" || b.StatusText = "In Training",
                    IsOutdatedSignOff, b.StatusText = "Signed Off" && b.RevisionAssigned <> b.CurrentRevision
                ) As c,
                IsOverdue, c.IsPending && !IsBlank(c.DueDate) && c.DueDate < Today()
            ) As d,
            DisplayStatus,
                If(
                    d.IsQualified, "Signed Off",
                    d.IsOverdue, "Overdue",
                    d.DocTypeText = "PWI" && ((d.IsPending && d.IsRevisionChange) || d.IsOutdatedSignOff), "Re-Sign Required",
                    d.DocTypeText = "JQC" && (d.StatusText = "Assigned" || d.IsOutdatedSignOff), "Needs Training",
                    d.DocTypeText = "JQC" && d.StatusText = "In Training", "In Training",
                    d.IsPending, "Pending",
                    "Not Assigned"
                ),
            ShowNewRevisionBadge, d.IsRevisionChange && !d.IsQualified
        )
    );
"""),
    ("Status colors and labels", """
// Use: fxStatusStyle lookup by DisplayStatus. Status is always text + color (Section 14).
fxStatusStyle = Table(
    {Status: "Signed Off", Fore: clrGreen, Back: clrGreenBg},
    {Status: "Overdue", Fore: clrRed, Back: clrRedBg},
    {Status: "Re-Sign Required", Fore: clrAmber, Back: clrAmberBg},
    {Status: "Needs Training", Fore: clrAmber, Back: clrAmberBg},
    {Status: "In Training", Fore: clrAmber, Back: clrAmberBg},
    {Status: "Pending", Fore: clrAmber, Back: clrAmberBg},
    {Status: "Not Assigned", Fore: clrGrey, Back: clrGreyBg}
);
"""),
    ("Personal and team views (scrHome tiles, scrMyTraining)", """
fxMyAssignments = Filter(fxAssignmentDisplayStatus, Lower(EmployeeEmail) = fxMeEmail && DocIsActive);
fxMyPending = Filter(fxMyAssignments, IsPending);
// PWI re-signs only; JQC revision rows show as Needs Training (D-01).
fxMyResignCount = CountRows(Filter(fxMyPending, DocTypeText = "PWI" && IsRevisionChange));
fxMySignedOff = Filter(fxMyAssignments, IsQualified);
fxMyTeam = If(fxIsManager, Filter(fxEmployeesActive, Supervisor.Id = fxMe.ID), Filter(fxEmployeesActive, false));
fxTeamPending = Filter(fxAssignmentDisplayStatus, DocIsActive && IsPending && Employee.Id in ShowColumns(fxMyTeam, ID));
fxTeamJqcNeedsTraining = Filter(fxTeamPending, DocTypeText = "JQC" && StatusText = "Assigned");
"""),
    ("Cross-training coverage (SPEC.md BR-43 to BR-49)", """
fxTaskCoverage =
    AddColumns(
        fxDocsActive As t,
        Qualified, CountRows(Filter(fxAssignmentDisplayStatus, DocumentID = t.ID && IsQualified)),
        Target, fxMinQualified
    );
fxCoverageGaps = Filter(fxTaskCoverage, Qualified < Target);
"""),
    ("Navigation (CLAUDE.md Section 12: only what the role allows)", """
// Roles: M = Manager/Supervisor, T = Technician, V = Viewer.
fxNavItems = Filter(
    Table(
        {Key: "home", Label: "Home", Icon: Icon.Home, Roles: "MTV"},
        {Key: "mytraining", Label: "My Training", Icon: Icon.Bookmark, Roles: "MT"},
        {Key: "jqc", Label: "JQCs", Icon: Icon.CheckBadge, Roles: "MTV"},
        {Key: "pwi", Label: "PWIs", Icon: Icon.Note, Roles: "MTV"},
        {Key: "matrix", Label: "Matrix", Icon: Icon.ListWatchlistRemind, Roles: "MTV"},
        {Key: "cross", Label: "Cross-Training", Icon: Icon.View, Roles: "MTV"},
        {Key: "review", Label: "Sign-off Review", Icon: Icon.Check, Roles: "MV"},
        {Key: "employees", Label: "Employees", Icon: Icon.Person, Roles: "MTV"},
        {Key: "assign", Label: "Assign", Icon: Icon.AddUser, Roles: "M"}
    ),
    (fxIsManager && "M" in Roles) || (fxIsTechnician && "T" in Roles) || (fxIsViewer && "V" in Roles)
);
"""),
]


def formulas_text():
    out = []
    for title, body in FORMULA_SECTIONS:
        out.append("// ===== " + title + " =====")
        out.append(body.strip("\n"))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


APP_ONSTART = """// Named formulas (App.Formulas) hold all logic; OnStart only sets UI state.
Set(gblSaving, false);
Set(gblNavKey, "home")"""

NAV_SCREENS = {   # nav key -> screen name
    "home": "scrHome", "mytraining": "scrMyTraining", "jqc": "scrJQCLibrary", "pwi": "scrPWILibrary",
    "matrix": "scrMatrix", "cross": "scrCrossTraining", "review": "scrSignoffReview",
    "employees": "scrEmployees", "assign": "scrAssign",
}
ALL_SCREENS = [   # (screen, title, nav key it highlights, purpose)
    ("scrHome", "Home", "home", "Tiles: my pending, my signed off, team pending, coverage gaps."),
    ("scrMyTraining", "My Training", "mytraining", "Your current assignments: Pending, Signed Off, All."),
    ("scrAssignmentDetail", "Assignment", "mytraining", "Open the document, upload evidence, sign off or put into training."),
    ("scrJQCLibrary", "JQC Library", "jqc", "Job qualification checklists, trainers and coverage."),
    ("scrPWILibrary", "PWI Library", "pwi", "Process work instructions and current-revision sign-off counts."),
    ("scrDocumentEdit", "Document", "jqc", "Add or edit a document, designate trainers, upload a new revision."),
    ("scrPWIStatus", "PWI Status", "pwi", "Everyone assigned to one PWI and the revision they are on."),
    ("scrEmployees", "Employees", "employees", "Employee list; managers add and edit."),
    ("scrEmployeeDetail", "Employee", "employees", "One employee's assignments and previous revisions."),
    ("scrAssign", "Assign", "assign", "Assign documents to employees."),
    ("scrMatrix", "Training Matrix", "matrix", "Who is qualified on what (current revision only)."),
    ("scrCrossTraining", "Cross-Training", "cross", "Coverage by task and shift, single points of failure."),
    ("scrSignoffReview", "Sign-off Review", "review", "Recent sign-offs, JQCs needing training, re-signs, overdue."),
]


def nav_onselect():
    cases = ", ".join(f'"{k}", Navigate({s}, ScreenTransition.None)' for k, s in NAV_SCREENS.items())
    return f"Switch(ThisItem.Key, {cases})"


# =============================================================================
# 2. Controls (.fx.yaml emitter, as in the earlier working project)
# =============================================================================
class C:
    def __init__(self, name, kind, props=None, children=None):
        self.name, self.kind, self.props, self.children = name, kind, dict(props or {}), list(children or [])


def emit(ctrl, indent=0):
    pad = " " * indent
    out = [f"{pad}{ctrl.name} As {ctrl.kind}:"]
    for k in sorted(ctrl.props):
        v = str(ctrl.props[k]).strip("\n")
        if "\n" in v or any(ch in v for ch in ':#"\'{}[]&|>%@`'):
            out.append(f"{pad}    {k}: |-")
            lines = v.split("\n")
            out.append(f"{pad}        ={lines[0]}")
            out += [f"{pad}        {l}" for l in lines[1:]]
        else:
            out.append(f"{pad}    {k}: ={v}")
    for i, ch in enumerate(ctrl.children, 1):
        ch.props.setdefault("ZIndex", i)
        out.append("")
        out += emit(ch, indent + 4)
    return out


def q(s):
    return '"' + s.replace('"', '""') + '"'


FONT = "Font.'Segoe UI'"


def label(name, text, size=14, color="clrText", bold=False, **kw):
    p = {"Text": text, "Size": size, "Color": color, "Font": FONT, "Wrap": "true",
         "PaddingLeft": 0, "PaddingRight": 0, "PaddingTop": 0, "PaddingBottom": 0}
    if bold:
        p["FontWeight"] = "FontWeight.Semibold"
    p.update(kw)
    return C(name, "label", p)


def vbox(name, children, **kw):
    p = {"LayoutMode": "LayoutMode.Auto", "LayoutDirection": "LayoutDirection.Vertical",
         "LayoutAlignItems": "LayoutAlignItems.Stretch", "LayoutGap": 0, "DropShadow": "DropShadow.None",
         "DisplayMode": "DisplayMode.Edit", "BorderThickness": 0}
    p.update(kw)
    return C(name, "groupContainer.verticalAutoLayoutContainer", p, children)


def hbox(name, children, **kw):
    p = {"LayoutMode": "LayoutMode.Auto", "LayoutDirection": "LayoutDirection.Horizontal",
         "LayoutAlignItems": "LayoutAlignItems.Stretch", "LayoutGap": 0, "DropShadow": "DropShadow.None",
         "DisplayMode": "DisplayMode.Edit", "BorderThickness": 0}
    p.update(kw)
    return C(name, "groupContainer.horizontalAutoLayoutContainer", p, children)


def nav_rail(sfx, active_key):
    """Left nav rail (tablet/desktop)."""
    item_label = label(f"lblNavRail{sfx}", "ThisItem.Label", size=14, color="clrNavText",
                       X=52, Y=0, Width="Parent.TemplateWidth - 60", Height="Parent.TemplateHeight",
                       VerticalAlign="VerticalAlign.Middle", OnSelect="Select(Parent)",
                       FontWeight=f'If(ThisItem.Key = "{active_key}", FontWeight.Semibold, FontWeight.Normal)')
    item_icon = C(f"icoNavRail{sfx}", "icon.Home", {
        "Icon": "ThisItem.Icon", "Color": "clrNavText", "X": 16, "Y": "(Parent.TemplateHeight - 24) / 2",
        "Width": 24, "Height": 24, "OnSelect": "Select(Parent)", "AccessibleLabel": "ThisItem.Label"})
    gal = C(f"galNavRail{sfx}", "gallery.galleryVertical", {
        "Items": "fxNavItems", "TemplateSize": 48, "TemplatePadding": 0, "ShowScrollbar": "false",
        "BorderThickness": 0, "OnSelect": nav_onselect(), "FillPortions": 1,
        "TemplateFill": f'If(ThisItem.Key = "{active_key}", clrNavActive, Color.Transparent)',
        "AccessibleLabel": q("Main navigation")}, [item_icon, item_label])
    title = label(f"lblAppTitleRail{sfx}", q("JQC/PWI Management"), size=16, color="clrNavText", bold=True,
                  Height=64, PaddingLeft=16, PaddingRight=12, VerticalAlign="VerticalAlign.Middle",
                  FillPortions=0)
    who = label(f"lblWhoRail{sfx}", 'If(fxIsRegistered, fxMe.Title & Char(10) & fxRole, "Read-only access")',
                size=12, color="clrNavText", Height=56, PaddingLeft=16, PaddingRight=12, FillPortions=0)
    return vbox(f"conNavRail{sfx}", [title, gal, who], Fill="clrNavBg", Width=220, FillPortions=0,
                Visible="!fxIsPhone", LayoutMinWidth=220)


def nav_bottom(sfx, active_key):
    """Bottom nav bar (phone)."""
    icon = C(f"icoNavBottom{sfx}", "icon.Home", {
        "Icon": "ThisItem.Icon", "Color": "clrNavText", "X": "(Parent.TemplateWidth - 24) / 2", "Y": 8,
        "Width": 24, "Height": 24, "OnSelect": "Select(Parent)", "AccessibleLabel": "ThisItem.Label"})
    lbl = label(f"lblNavBottom{sfx}", "ThisItem.Label", size=10, color="clrNavText", X=0, Y=34,
                Width="Parent.TemplateWidth", Height=24, Align="Align.Center", Wrap="false",
                OnSelect="Select(Parent)")
    gal = C(f"galNavBottom{sfx}", "gallery.galleryHorizontal", {
        "Items": "fxNavItems", "TemplateSize": "Max(72, Self.Width / Max(1, CountRows(fxNavItems)))",
        "TemplatePadding": 0, "ShowScrollbar": "false", "BorderThickness": 0, "OnSelect": nav_onselect(),
        "Fill": "clrNavBg", "Height": 64, "FillPortions": 0, "Visible": "fxIsPhone",
        "TemplateFill": f'If(ThisItem.Key = "{active_key}", clrNavActive, Color.Transparent)',
        "AccessibleLabel": q("Main navigation")}, [icon, lbl])
    return gal


def header(sfx, title):
    return hbox(f"conHeader{sfx}", [
        label(f"lblTitle{sfx}", q(title), size=20, bold=True, FillPortions=1, VerticalAlign="VerticalAlign.Middle"),
        label(f"lblWho{sfx}", 'If(fxIsRegistered, fxMe.Title & " · " & fxRole, "Read-only access")',
              size=12, color="clrMuted", FillPortions=0, Width=220, Align="Align.Right",
              VerticalAlign="VerticalAlign.Middle", Visible="fxIsPhone"),
    ], Height=64, FillPortions=0, Fill="clrPanel", PaddingLeft=16, PaddingRight=16,
        LayoutAlignItems="LayoutAlignItems.Center", BorderColor="clrBorder")


def screen(name, title, active_key, body_children):
    sfx = name[3:]
    body = vbox(f"conBody{sfx}", body_children, FillPortions=1, PaddingLeft=16, PaddingRight=16,
                PaddingTop=16, PaddingBottom=16, LayoutGap=16, Fill="clrBg",
                LayoutOverflowY="LayoutOverflow.Scroll")
    main = vbox(f"conMain{sfx}", [header(sfx, title), body, nav_bottom(sfx, active_key)], FillPortions=1)
    root = hbox(f"conRoot{sfx}", [nav_rail(sfx, active_key), main],
                X=0, Y=0, Width="Parent.Width", Height="Parent.Height", Fill="clrBg")
    return C(name, "screen", {"Fill": "clrBg", "LoadingSpinnerColor": "clrPrimary",
                              "OnVisible": f'Set(gblNavKey, "{active_key}")'}, [root])


HOME_TILES = """Filter(
    Table(
        {Key: "mypending", Title: "My Pending", Count: CountRows(fxMyPending),
         Sub: fxMyResignCount & " need re-sign (new PWI revision)", Fore: clrAmber, Back: clrAmberBg,
         Show: fxIsManager || fxIsTechnician},
        {Key: "mysigned", Title: "My Signed Off", Count: CountRows(fxMySignedOff),
         Sub: "on the current revision", Fore: clrGreen, Back: clrGreenBg,
         Show: fxIsManager || fxIsTechnician},
        {Key: "team", Title: "Team Pending", Count: CountRows(fxTeamPending),
         Sub: CountRows(fxTeamJqcNeedsTraining) & " JQCs need training", Fore: clrAmber, Back: clrAmberBg,
         Show: fxIsManager},
        {Key: "gaps", Title: "Coverage Gaps", Count: CountRows(fxCoverageGaps),
         Sub: "tasks below target of " & fxMinQualified & " qualified", Fore: clrRed, Back: clrRedBg,
         Show: true}
    ),
    Show
)"""


def home_screen():
    tiles = HOME_TILES
    on_tile = """Switch(
    ThisItem.Key,
    "mypending", Navigate(scrMyTraining, ScreenTransition.None),
    "mysigned", Navigate(scrMyTraining, ScreenTransition.None),
    "team", Navigate(scrSignoffReview, ScreenTransition.None),
    "gaps", Navigate(scrCrossTraining, ScreenTransition.None)
)"""
    tile_children = [
        C("rectTileBg", "rectangle", {"X": 6, "Y": 6, "Width": "Parent.TemplateWidth - 12",
                                     "Height": "Parent.TemplateHeight - 12", "Fill": "clrPanel",
                                     "BorderColor": "clrBorder", "BorderThickness": 1,
                                     "OnSelect": "Select(Parent)",
                                     **{f"Radius{c}": 8 for c in ("TopLeft", "TopRight", "BottomLeft", "BottomRight")}}),
        C("rectTileAccent", "rectangle", {"X": 6, "Y": 6, "Width": 6, "Height": "Parent.TemplateHeight - 12",
                                         "Fill": "ThisItem.Fore", "OnSelect": "Select(Parent)"}),
        label("lblTileTitle", "ThisItem.Title", size=14, color="clrMuted", bold=True, X=24, Y=18,
              Width="Parent.TemplateWidth - 40", Height=24, OnSelect="Select(Parent)"),
        label("lblTileCount", "ThisItem.Count", size=32, color="ThisItem.Fore", bold=True, X=24, Y=46,
              Width="Parent.TemplateWidth - 40", Height=48, OnSelect="Select(Parent)"),
        label("lblTileSub", "ThisItem.Sub", size=13, color="clrText", X=24, Y=98,
              Width="Parent.TemplateWidth - 40", Height=40, OnSelect="Select(Parent)"),
    ]
    gal = C("galHomeTiles", "gallery.galleryVertical", {
        "Items": tiles, "WrapCount": "If(fxIsPhone, 1, Max(1, RoundDown(Self.Width / 280, 0)))",
        "TemplateSize": 150, "TemplatePadding": 0, "ShowScrollbar": "false", "BorderThickness": 0,
        "OnSelect": on_tile, "FillPortions": 1, "LayoutMinHeight": 320,
        "AccessibleLabel": q("Summary tiles")}, tile_children)
    welcome = label("lblWelcome", 'If(fxIsRegistered, "Welcome, " & fxMe.Title, "Welcome")',
                    size=18, bold=True, Height=32, FillPortions=0)
    viewer_note = label("lblViewerNote",
                        q("You have read-only access. Ask a manager to add you as an employee to receive assignments."),
                        size=13, color="clrMuted", Height=40, FillPortions=0, Visible="!fxIsRegistered")
    return screen("scrHome", "Home", "home", [welcome, viewer_note, gal])


def placeholder_screen(name, title, key, purpose):
    sfx = name[3:]
    return screen(name, title, key, [
        label(f"lblPurpose{sfx}", q(purpose), size=14, Height=48, FillPortions=0),
        label(f"lblTodo{sfx}", q("This screen is built in build step 5. Navigation and data are already connected."),
              size=13, color="clrMuted", Height=40, FillPortions=0),
    ])


# Auto-layout child properties are "dynamic properties": pac keeps them only when the
# screen's EditorState file declares them (learned from Microsoft/PnP samples).
DYNAMIC_PROPS = ["FillPortions", "AlignInContainer", "LayoutMinWidth", "LayoutMinHeight",
                 "LayoutMaxWidth", "LayoutMaxHeight"]
AUTO_KINDS = ("groupContainer.verticalAutoLayoutContainer", "groupContainer.horizontalAutoLayoutContainer")


def editor_state(top):
    states = {}

    def prop_entry(p):
        cat = "Behavior" if p.startswith("On") else ("Data" if p in ("Text", "Items", "Default") else "Design")
        return {"Category": cat, "PropertyName": p, "RuleProviderType": "Unknown"}

    def walk(ctrl, parent_auto, index):
        dyn = [p for p in ctrl.props if parent_auto and p in DYNAMIC_PROPS]
        normal = [p for p in sorted(ctrl.props) if p not in dyn]
        states[ctrl.name] = {
            "AllowAccessToGlobals": True,
            "ControlPropertyState": normal + dyn,
            "DynamicProperties": [{"ControlPropertyState": p,
                                   "Property": {"Category": "Design", "PropertyName": p, "RuleProviderType": "Unknown"},
                                   "PropertyName": p} for p in dyn] if dyn else None,
            "HasDynamicProperties": bool(dyn),
            "IsAutoGenerated": False, "IsComponentDefinition": False, "IsDataControl": False,
            "IsFromScreenLayout": False, "IsGroupControl": False, "IsLocked": False, "LayoutName": "",
            "MetaDataIDKey": "", "Name": ctrl.name, "ParentIndex": index, "PersistMetaDataIDKey": False,
            "Properties": [prop_entry(p) for p in normal], "StyleName": "", "Type": "ControlInfo"}
        if not dyn:
            states[ctrl.name].pop("DynamicProperties")
        for i, ch in enumerate(ctrl.children):
            walk(ch, ctrl.kind in AUTO_KINDS, i)

    walk(top, False, 0)
    return {"ControlStates": states, "TopParentName": top.name}


# =============================================================================
# 3. SharePoint data sources (table definitions synthesized from the schema)
# =============================================================================
def sp_column(lst, f, table_id):
    """Return {property name: definition} for one SharePoint column (connector format)."""
    n, t = f["Name"], f["Type"]
    rw = "read-write"
    dv = lambda path, title: {"operationId": "GetEntityValues",
                              "parameters": {"dataset": {"parameter": "dataset"}, "table": {"parameter": "table"},
                                             "id": gid("field", lst["Title"], n)},
                              "value-path": path, "value-title": title, "value-collection": "value"}
    odt = {"title": "@odata.type", "x-ms-visibility": "internal", "type": "string", "x-ms-permission": rw}
    cmp_ops = ["eq", "gt", "ge", "lt", "le", "ne"]
    if t == "Text":
        return {n: {"title": n, "type": "string", "x-ms-permission": rw, "x-ms-sort": "asc,desc",
                    "x-ms-capabilities": {"filterFunctions": ["eq", "startswith"]}, "maxLength": 255}}
    if t == "Note":
        return {n: {"title": n, "type": "string", "x-ms-permission": rw, "x-ms-sort": "none"}}
    if t == "Number":
        return {n: {"title": n, "type": "number", "format": "double", "x-ms-permission": rw, "x-ms-sort": "asc,desc",
                    "x-ms-capabilities": {"filterFunctions": cmp_ops},
                    "maximum": 1.7976931348623157e+308, "minimum": -1.7976931348623157e+308}}
    if t == "Boolean":
        return {n: {"title": n, "type": "boolean", "x-ms-permission": rw, "x-ms-sort": "asc,desc",
                    "x-ms-capabilities": {"filterFunctions": ["eq"]}, "default": f.get("Default") == "1"}}
    if t in ("DateOnly", "DateTime"):
        return {n: {"title": n, "type": "string", "format": "date" if t == "DateOnly" else "date-time",
                    "x-ms-permission": rw, "x-ms-sort": "asc,desc", "x-ms-capabilities": {"filterFunctions": cmp_ops}}}
    if t == "Choice":
        return {
            f"{n}#Id": {"title": f"{n} Id", "type": "integer", "format": "int64", "x-ms-permission": "read-only",
                        "x-ms-visibility": "internal"},
            n: {"title": n, "type": "object", "x-ms-permission": rw, "x-ms-sort": "asc,desc",
                "x-ms-capabilities": {"x-ms-sp": {"IsChoice": True}, "filterFunctions": ["eq"]},
                "properties": {"@odata.type": odt, "Value": {"title": "Value", "type": "string", "x-ms-dynamic-values": dv("Value", "Value")},
                               "Id": {"title": "Id", "type": "integer", "format": "int64", "x-ms-visibility": "internal",
                                      "x-ms-permission": "read-only"}},
                "x-ms-displayFormat": {"titleProperty": "Value"}}}
    if t == "Lookup":
        return {
            f"{n}#Id": {"title": f"{n} Id", "type": "integer", "format": "int64", "x-ms-permission": "read-only",
                        "x-ms-visibility": "internal"},
            n: {"title": n, "type": "object", "x-ms-permission": rw, "x-ms-sort": "asc,desc",
                "x-ms-capabilities": {"filterFunctions": ["eq"]},
                "properties": {"@odata.type": odt, "Id": {"title": "Id", "type": "integer", "format": "int64",
                                                          "x-ms-dynamic-values": dv("Id", "Value")},
                               "Value": {"title": "Value", "type": "string", "x-ms-permission": "read-only",
                                         "x-ms-capabilities": {"x-ms-sp": {"OdataQueryName": f"{n}/Title"}, "filterFunctions": ["eq"]}}},
                "x-ms-displayFormat": {"titleProperty": "Value"}}}
    if t in ("User", "UserMulti"):
        person = {"title": n, "type": "object", "x-ms-permission": rw, "x-ms-sort": "asc,desc",
                  "x-ms-capabilities": {"filterFunctions": ["eq"]},
                  "properties": {
                      "@odata.type": odt,
                      "Claims": {"title": "Claims", "type": "string", "x-ms-permission": rw, "x-ms-dynamic-values": dv("Claims", "DisplayName")},
                      "DisplayName": {"title": "DisplayName", "type": "string", "x-ms-permission": "read-only"},
                      "Email": {"title": "Email", "type": "string", "x-ms-permission": "read-only"},
                      "Picture": {"title": "Picture", "type": "string", "format": "uri", "x-ms-media-kind": "image",
                                  "x-ms-permission": "read-only"},
                      "Department": {"title": "Department", "type": "string", "x-ms-permission": "read-only"},
                      "JobTitle": {"title": "JobTitle", "type": "string", "x-ms-permission": "read-only"}},
                  "x-ms-displayFormat": {"titleProperty": "DisplayName"}}
        claims = {"title": f"{n} Claims", "type": "string", "x-ms-permission": rw, "x-ms-visibility": "internal"}
        if t == "User":
            return {f"{n}#Claims": claims, n: person}
        # Multi-person: no public sample available; built from the single-person shape.
        # If Studio shows a schema warning, refresh the data source once (Admin-Guide.md).
        item = dict(person); item.pop("title"); item.pop("x-ms-sort"); item.pop("x-ms-capabilities")
        return {f"{n}#Claims": {"title": f"{n} Claims", "type": "array", "items": {"type": "string"},
                                "x-ms-permission": rw, "x-ms-visibility": "internal"},
                n: {"title": n, "type": "array", "x-ms-permission": rw, "x-ms-sort": "none",
                    "x-ms-capabilities": {"x-ms-sp": {"IsMultiSelect": True}}, "items": item}}
    raise ValueError(t)


def table_definition(lst, base):
    table_id = gid("table", lst["Title"])
    meta = json.loads(json.dumps(base["metadata"]).replace("__TABLE_ID__", table_id)
                      .replace("__SITE_URL__", PLACEHOLDER_SITE).replace("__SITE_PATH__", "/sites/JQCPWI"))
    meta["name"], meta["title"] = table_id, lst["Title"]
    items = meta["schema"]["items"]
    props = items["properties"]
    is_library = lst["Template"] == 101
    custom, rels, refs, unsortable = {}, {}, {}, []
    for f in lst["Fields"]:
        cols = sp_column(lst, f, table_id)
        custom.update(cols)
        if f["Type"] in ("Choice", "Lookup"):
            rels[f["Name"]] = {"targetEntity": f["Name"], "referentialConstraints": {f"{f['Name']}#Id": {"referencedProperty": "Id"}}}
        if f["Type"] in ("Choice", "Lookup", "User", "UserMulti"):
            refs[f["Name"]] = {"lookupEndpoint": {"path": f"/tables/{table_id}/entities/{f['Name']}",
                                                  "capabilities": {"searchable": True, "requiresSearch": False}}}
        if f["Type"] in ("Note", "UserMulti"):
            unsortable.append(f["Name"])
    # Order: ID, Title, custom columns, then the system columns from the base.
    ordered = {"ID": props["ID"], "Title": props["Title"]}
    ordered.update(custom)
    for k, v in props.items():
        if k in ordered:
            continue
        if is_library and k in ("{Attachments}", "{Attachments}@odata.type", "{HasAttachments}"):
            continue
        ordered[k] = v
    items["properties"] = ordered
    items["required"] = [] if is_library else ["Title"] + [f["Name"] for f in lst["Fields"] if f.get("Required")]
    items.setdefault("x-ms-relationships", {}).update(rels)
    meta.setdefault("referencedEntities", {}).update(refs)
    caps = meta["x-ms-capabilities"]
    caps["sortRestrictions"]["unsortableProperties"] = unsortable + [p for p in caps["sortRestrictions"]["unsortableProperties"] if p in ordered]
    caps["filterRestrictions"]["nonFilterableProperties"] = unsortable + [p for p in caps["filterRestrictions"]["nonFilterableProperties"] if p in ordered]
    names = ["Title"] + [f["Name"] for f in lst["Fields"]]
    items["x-ms-displayFormat"] = {"propertiesDisplayOrder": names, "propertiesCompactDisplayOrder": names,
                                   "propertiesTabularDisplayOrder": names}
    name_map = {k: v for k, v in base["nameMapping"].items() if k in ordered}
    for k, v in custom.items():
        name_map[k] = v.get("title", k)
    return table_id, meta, name_map


def write_data_sources(schema):
    base = json.load(open(os.path.join(TEMPLATE, "sp_list_base.json")))
    os.makedirs(os.path.join(SRC, "DataSources"))
    os.makedirs(os.path.join(SRC, "pkgs", "TableDefinitions"))
    datasets = {}
    for name, env in DATA_SOURCES:
        table_id, meta, name_map = table_definition(schema[name], base)
        ds = [{"ApiId": SP_API, "CdpRevision": {"BaseUrl": "/", "LastChangedTimeString": "2026-11-04T00:00:00.0000000Z",
                                                "RevisionNumber": 1},
               "ConnectedDataSourceInfoNameMapping": name_map, "DatasetName": PLACEHOLDER_SITE, "EncodeDataset": True,
               "IsSampleData": False, "IsWritable": True, "Name": name, "Type": "ConnectedDataSourceInfo"}]
        json.dump(ds, open(os.path.join(SRC, "DataSources", name + ".json"), "w"), indent=2)
        json.dump({"DataEntityMetadataJson": {table_id: json.dumps(meta, separators=(",", ":"))},
                   "EntityName": name, "TableName": table_id},
                  open(os.path.join(SRC, "pkgs", "TableDefinitions", name + ".json"), "w"), indent=2)
        datasets[name] = {"tableName": table_id, "tableNameOverride": {"environmentVariableName": env}}
    connection = {
        "appActions": ["providers/PowerPlatform.Governance/Operations/Read"],
        "connectionRef": {"apiTier": "Standard", "displayName": "SharePoint", "id": SP_API,
                          "parameterHints": {}, "parameterHintsV2": {}},
        "datasets": {PLACEHOLDER_SITE: {"datasetOverride": {"environmentVariableName": ENV_SITE},
                                        "dataSources": datasets}},
        "dataSources": [n for n, _ in DATA_SOURCES], "dependencies": {}, "dependents": [], "id": SP_CONNECTION_ID}
    # ---- the upload flow as a data source (pattern from Microsoft/PnP sample apps)
    json.dump([{"ApiId": LOGICFLOWS_API, "FlowNameId": FLOW_WORKFLOW_ID, "Name": FLOW_DS_NAME,
                "ServiceKind": "ConnectedWadl", "Type": "ServiceInfo", "WorkflowEntityId": FLOW_WORKFLOW_ID}],
              open(os.path.join(SRC, "DataSources", FLOW_DS_NAME + ".json"), "w"), indent=2)
    os.makedirs(os.path.join(SRC, "pkgs", "Wadl"))
    open(os.path.join(SRC, "pkgs", "Wadl", FLOW_DS_NAME + ".xml"), "w", encoding="utf-8").write(flow_wadl())
    flow_conn = {
        "appActions": ["Run"],
        "connectionRef": {"apiTier": "Standard", "displayName": "Logic flows", "id": LOGICFLOWS_API,
                          "parameterHints": {SP_CONNECTION_ID: {"value": "shared_sharepointonline"},
                                             "workflowEntityId": {"value": FLOW_WORKFLOW_ID},
                                             "workflowName": {"value": FLOW_WORKFLOW_ID}},
                          "parameterHintsV2": {"shared_sharepointonline": {"value": SP_CONNECTION_ID},
                                               "workflowEntityId": {"value": FLOW_WORKFLOW_ID},
                                               "workflowName": {"value": FLOW_WORKFLOW_ID}}},
        "datasets": {}, "dataSources": [FLOW_DS_NAME],
        "dependencies": {"shared_sharepointonline": SP_CONNECTION_ID}, "dependents": [], "id": FLOW_CONNECTION_ID}
    connection["dependents"] = [FLOW_CONNECTION_ID]
    os.makedirs(os.path.join(SRC, "Connections"))
    json.dump({SP_CONNECTION_ID: connection, FLOW_CONNECTION_ID: flow_conn},
              open(os.path.join(SRC, "Connections", "Connections.json"), "w"), indent=2)
    return connection


def flow_wadl():
    """API description of the upload flow's Power Apps (V2) trigger: Run(file, text, number, text_1)."""
    base = "https://europe-002.azure-apim.net/apim/logicflows"
    return f"""<application xmlns:xml="http://www.w3.org/XML/1998/namespace" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:service="{base}" xmlns:siena="http://schemas.microsoft.com/MicrosoftProjectSiena/WADL/2014/11" siena:serviceId="{FLOW_DS_NAME}" xmlns="http://wadl.dev.java.net/2009/02">
  <doc title="JQCPWI - Upload File" />
  <grammars>
    <jsonTypes targetNamespace="{base}" xmlns="http://schemas.microsoft.com/MicrosoftProjectSiena/WADL/2014/11">
      <string name="ManualTriggerInput_file_def_name_def" />
      <base64Binary name="ManualTriggerInput_file_def_contentBytes_def" />
      <object name="ManualTriggerInput_file_def">
        <property name="name" type="string" />
        <property name="contentBytes" typeRef="ManualTriggerInput_file_def_contentBytes_def" />
      </object>
      <string name="ManualTriggerInput_text_def" />
      <number name="ManualTriggerInput_number_def" />
      <string name="ManualTriggerInput_text_1_def" />
      <object name="ManualTriggerInput">
        <property name="file" typeRef="ManualTriggerInput_file_def" />
        <property name="text" type="string" />
        <property name="number" type="number" />
        <property name="text_1" type="string" />
      </object>
      <string name="ResponseActionOutput_success_def" />
      <number name="ResponseActionOutput_itemid_def" />
      <string name="ResponseActionOutput_fileurl_def" />
      <string name="ResponseActionOutput_message_def" />
      <object name="ResponseActionOutput">
        <property name="success" type="string" />
        <property name="itemid" type="number" />
        <property name="fileurl" type="string" />
        <property name="message" type="string" />
      </object>
      <object name="Run_responses_default_def" />
    </jsonTypes>
  </grammars>
  <resources siena:authenticationProviderHref="#PowerAppAuth" base="{base}">
    <resource path="/{{connectionId}}/triggers/manual/run">
      <param style="template" name="connectionId" type="xs:string" required="true" />
      <method siena:requiresAuthentication="true" name="POST" id="Run">
        <doc title="Runs a logic flow trigger." />
        <request>
          <param style="query" name="api-version" type="xs:string" required="true" fixed="2015-02-01-preview">
            <doc title="The api version" />
          </param>
          <representation mediaType="application/json">
            <param style="plain" name="file" path="/file" type="service:ManualTriggerInput_file_def" required="true">
              <doc title="File" />
            </param>
            <param style="plain" name="text" path="/text" type="xs:string" required="true">
              <doc title="TargetLibrary" />
            </param>
            <param style="plain" name="number" path="/number" type="xs:double" required="true">
              <doc title="ExistingItemID" />
            </param>
            <param style="plain" name="text_1" path="/text_1" type="xs:string" required="true">
              <doc title="MetadataJson" />
            </param>
          </representation>
        </request>
        <response>
          <representation mediaType="application/json" element="service:ResponseActionOutput" />
        </response>
      </method>
    </resource>
  </resources>
  <authenticationProviders xmlns="http://schemas.microsoft.com/MicrosoftProjectSiena/WADL/2014/11">
    <connectionProvider id="PowerAppAuth" siena:connectionProviderId="logicflows" />
  </authenticationProviders>
  <template xmlns="http://schemas.microsoft.com/MicrosoftProjectSiena/WADL/2014/11">
    <variable name="connectionId">
      <modifyParams style="template" name="connectionId" attribute="fixed" />
    </variable>
  </template>
</application>
"""


# =============================================================================
# 4. Assemble sources, pack, round-trip check
# =============================================================================
NEEDED_TEMPLATES = ["appinfo", "screen", "label", "button", "icon", "rectangle", "groupContainer",
                    "gallery", "galleryTemplate", "text", "dropdown", "combobox", "datepicker",
                    "checkbox", "toggleSwitch", "attachments", "form", "typedDataCard", "htmlViewer", "image"]


def write_sources(schema):
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(os.path.join(SRC, "Src"))
    os.makedirs(os.path.join(SRC, "pkgs"))

    app = C("App", "appinfo", {"BackEnabled": "false", "Formulas": formulas_text().rstrip("\n"),
                               "OnStart": APP_ONSTART, "Theme": "PowerAppsTheme"})
    sys.path.insert(0, HERE)
    import screens as screen_defs
    screens = screen_defs.build(sys.modules[__name__])
    os.makedirs(os.path.join(SRC, "Src", "EditorState"))
    for ctrl in [app] + screens:
        with open(os.path.join(SRC, "Src", ctrl.name + ".fx.yaml"), "w", encoding="utf-8") as f:
            f.write("\n".join(emit(ctrl)) + "\n")
        json.dump(editor_state(ctrl), open(os.path.join(SRC, "Src", "EditorState", ctrl.name + ".editorstate.json"), "w"),
                  indent=2)

    shutil.copy(os.path.join(TEMPLATE, "Themes.json"), os.path.join(SRC, "Src", "Themes.json"))
    tmpl = json.load(open(os.path.join(TEMPLATE, "ControlTemplates.json")))
    json.dump({k: v for k, v in tmpl.items() if k in NEEDED_TEMPLATES},
              open(os.path.join(SRC, "ControlTemplates.json"), "w"), indent=2)
    for f in os.listdir(os.path.join(TEMPLATE, "pkgs")):
        shutil.copy(os.path.join(TEMPLATE, "pkgs", f), os.path.join(SRC, "pkgs", f))

    connection = write_data_sources(schema)

    man = json.load(open(os.path.join(TEMPLATE, "CanvasManifest.base.json")))
    man["PublishInfo"].update({"AppName": APP_DISPLAY_NAME, "BackgroundColor": "RGBA(19,50,91,1)",
                               "IconColor": "RGBA(255,255,255,1)", "IconName": "Edit", "LogoFileName": ""})
    man["ScreenOrder"] = [s.name for s in screens]
    p = man["Properties"]
    p.update({"AppDescription": APP_DESCRIPTION, "Name": APP_DISPLAY_NAME, "Author": "",
              "Id": gid("app"), "FileID": gid("file"),
              "DocumentLayoutScaleToFit": False, "DocumentLayoutMaintainAspectRatio": False,
              "DocumentLayoutLockOrientation": False, "DocumentLayoutWidth": 1366, "DocumentLayoutHeight": 768,
              "DocumentAppType": "DesktopOrTablet", "DefaultConnectedDataSourceMaxGetRowsCount": 2000})
    p["AppPreviewFlagsMap"]["errorhandling"] = True
    json.dump(man, open(os.path.join(SRC, "CanvasManifest.json"), "w"), indent=2)
    with open(os.path.join(SRC, "ComponentReferences.json"), "w") as f:
        f.write("[]")
    return screens, connection


def pac():
    return shlex.split(os.environ.get("PAC", "pac"))


def run(args):
    res = subprocess.run(pac() + args, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stdout.write(res.stdout[-4000:])
        sys.stderr.write(res.stderr[-4000:])
        sys.exit("pac " + " ".join(args[:2]) + " failed")
    return res.stdout


def parse_props(path):
    """Read control -> {property: value} from an .fx.yaml file (enough for a comparison)."""
    props, stack, cur_key, block = {}, [], None, None
    for raw in open(path, encoding="utf-8").read().split("\n"):
        if block is not None:
            if raw.startswith(" " * block[0]) or raw.strip() == "":
                block[1].append(raw.strip())
                continue
            props[cur_key] = "\n".join(block[1]).strip()
            block = None
        m = re.match(r"^(\s*)(\S.*?) As ([^:]+):\s*$", raw)
        if m:
            depth = len(m.group(1))
            stack = [s for s in stack if s[0] < depth] + [(depth, m.group(2))]
            continue
        m = re.match(r"^(\s*)([A-Za-z]+): (.*)$", raw)
        if m and stack:
            key = stack[-1][1] + "." + m.group(2)
            val = m.group(3)
            if val in ("|-", "|", "|+"):
                cur_key, block = key, (len(m.group(1)) + 4, [])
            else:
                props[key] = val.strip()
    if block is not None:
        props[cur_key] = "\n".join(block[1]).strip()
    return props


def norm(v):
    return re.sub(r"\s+", "", v.lstrip("=").replace("=", "", 1) if v.startswith("=") else v)


def msapp_rules():
    """control name -> {property: script} as stored in the packed .msapp (what Studio loads)."""
    import zipfile
    rules = {}
    with zipfile.ZipFile(MSAPP) as z:
        for n in z.namelist():
            if not n.replace("\\", "/").startswith("Controls/"):
                continue
            def walk(c):
                r = {x["Property"]: x["InvariantScript"] for x in c.get("Rules", [])}
                for dp in c.get("DynamicProperties") or []:
                    if dp.get("Rule"):
                        r[dp["PropertyName"]] = dp["Rule"]["InvariantScript"]
                rules[c["Name"]] = r
                for ch in c.get("Children", []):
                    walk(ch)
            walk(json.loads(z.read(n))["TopParent"])
    return rules


def round_trip_check(screens):
    """1) pac can unpack what it packed; 2) every property we wrote is in the .msapp with the same formula."""
    rt = os.path.join(BUILD, "roundtrip")
    run(["canvas", "unpack", "--msapp", MSAPP, "--sources", rt])
    rules = msapp_rules()
    problems, checked = 0, 0
    def walk(ctrl):
        nonlocal problems, checked
        got = rules.get(ctrl.name)
        if got is None:
            print("  control missing from .msapp:", ctrl.name); problems += 1; return
        if ctrl.kind.startswith("gallery."):
            # Studio stores a gallery's OnSelect / TemplateFill on its template child.
            got = dict(got, **rules.get(ctrl.name + "template1", {}))
        for k, v in ctrl.props.items():
            checked += 1
            want = re.sub(r"\s+", "", str(v))
            if k not in got:
                print("  property missing from .msapp:", ctrl.name + "." + k); problems += 1
            elif re.sub(r"\s+", "", got[k]) != want:
                print("  property changed in .msapp:", ctrl.name + "." + k, "->", got[k][:80]); problems += 1
        for ch in ctrl.children:
            walk(ch)
    for ctrl in screens:
        walk(ctrl)
    app_rules = rules.get("App", {})
    for k in ("Formulas", "OnStart"):
        if re.sub(r"\s+", "", app_rules.get(k, "")) == "":
            print("  App." + k, "missing"); problems += 1
    lsdir = lambda d: sorted(os.listdir(d)) if os.path.isdir(d) else []
    ds_a = lsdir(os.path.join(SRC, "DataSources"))
    ds_b = lsdir(os.path.join(rt, "DataSources"))
    if ds_a != ds_b:
        print("  data sources differ:", ds_a, ds_b); problems += 1
    print(f"Round-trip check: {checked} properties on {len(screens)} screens + App, "
          f"{len(ds_a)} data sources, {problems} problem(s)")
    if problems:
        sys.exit("round-trip check failed")


# =============================================================================
# 5. Solution: .meta.xml, background image, msapp
# =============================================================================
def png(width, height, rgb):
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def write_solution_app(connection):
    if os.path.isdir(SOLUTION_CANVAS):
        shutil.rmtree(SOLUTION_CANVAS)
    os.makedirs(SOLUTION_CANVAS)
    shutil.copy(MSAPP, os.path.join(SOLUTION_CANVAS, f"{APP_SCHEMA_NAME}_DocumentUri.msapp"))
    open(os.path.join(SOLUTION_CANVAS, f"{APP_SCHEMA_NAME}_BackgroundImageUri"), "wb").write(png(64, 64, (19, 50, 91)))
    conn_refs = {SP_CONNECTION_ID: {
        "id": SP_API, "displayName": "SharePoint", "dataSources": connection["dataSources"],
        "dependencies": [], "dependents": [FLOW_CONNECTION_ID], "parameterHints": {}, "parameterHintsV2": {},
        "isOnPremiseConnection": False, "bypassConsent": False,
        "dataSets": {PLACEHOLDER_SITE: {
            "datasetOverride": {"environmentVariableName": ENV_SITE},
            "dataSources": connection["datasets"][PLACEHOLDER_SITE]["dataSources"]}},
        "apiTier": "Standard", "actions": ["providers/PowerPlatform.Governance/Operations/Read"]},
        FLOW_CONNECTION_ID: {
            "id": LOGICFLOWS_API, "displayName": "Logic flows", "dataSources": [FLOW_DS_NAME],
            "dependencies": [SP_CONNECTION_ID], "dependents": [],
            "parameterHints": {"workflowName": {"value": FLOW_WORKFLOW_ID}, "workflowEntityId": {"value": FLOW_WORKFLOW_ID},
                               SP_CONNECTION_ID: {"value": "shared_sharepointonline"}},
            "parameterHintsV2": {"workflowName": {"value": FLOW_WORKFLOW_ID}, "workflowEntityId": {"value": FLOW_WORKFLOW_ID},
                                 "shared_sharepointonline": {"value": SP_CONNECTION_ID}},
            "isOnPremiseConnection": False, "dataSets": {}, "apiTier": "Standard", "actions": ["Run"]}}
    cds = {"cdsdependencies": [{"logicalname": v, "componenttype": 380,
                                "componenttypeplatformname": "EnvironmentVariableDefinition"}
                               for v in [ENV_SITE] + [e for _, e in DATA_SOURCES]]
           + [{"dependencyid": FLOW_WORKFLOW_ID, "componenttype": 29, "componenttypeplatformname": "Workflow"}]}
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tags = {"primaryDeviceWidth": "1366", "primaryDeviceHeight": "768", "supportsPortrait": "true",
            "supportsLandscape": "true", "primaryFormFactor": "Tablet", "showStatusBar": "false",
            "publisherVersion": "3.26094.9", "minimumRequiredApiVersion": "2.2.0", "hasComponent": "false",
            "hasUnlockedComponent": "false", "isUnifiedRootApp": "false"}
    meta = f"""<?xml version="1.0" encoding="utf-8"?>
<CanvasApp xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Name>{APP_SCHEMA_NAME}</Name>
  <AppVersion>{now}</AppVersion>
  <Status>Ready</Status>
  <CreatedByClientVersion>3.26094.9.0</CreatedByClientVersion>
  <MinClientVersion>3.26094.9.0</MinClientVersion>
  <Tags>{esc(json.dumps(tags, separators=(",", ":")))}</Tags>
  <IsCdsUpgraded>0</IsCdsUpgraded>
  <GalleryItemId xsi:nil="true"></GalleryItemId>
  <BackgroundColor>RGBA(19,50,91,1)</BackgroundColor>
  <DisplayName>{esc(APP_DISPLAY_NAME)}</DisplayName>
  <Description>{esc(APP_DESCRIPTION)}</Description>
  <CommitMessage xsi:nil="true"></CommitMessage>
  <Publisher xsi:nil="true"></Publisher>
  <AuthorizationReferences>[]</AuthorizationReferences>
  <ConnectionReferences>{esc(json.dumps(conn_refs, separators=(",", ":")))}</ConnectionReferences>
  <DatabaseReferences>{{}}</DatabaseReferences>
  <AppComponents>[]</AppComponents>
  <AppComponentDependencies>[]</AppComponentDependencies>
  <CanConsumeAppPass>1</CanConsumeAppPass>
  <CanvasAppType>0</CanvasAppType>
  <BypassConsent>0</BypassConsent>
  <AdminControlBypassConsent>0</AdminControlBypassConsent>
  <EmbeddedApp xsi:nil="true"></EmbeddedApp>
  <IntroducedVersion>1.0</IntroducedVersion>
  <CdsDependencies>{esc(json.dumps(cds, separators=(",", ":")))}</CdsDependencies>
  <IsCustomizable>1</IsCustomizable>
  <BackgroundImageUri>/CanvasApps/{APP_SCHEMA_NAME}_BackgroundImageUri</BackgroundImageUri>
  <DocumentUri>/CanvasApps/{APP_SCHEMA_NAME}_DocumentUri.msapp</DocumentUri>
</CanvasApp>
"""
    open(os.path.join(SOLUTION_CANVAS, f"{APP_SCHEMA_NAME}.meta.xml"), "w", encoding="utf-8").write(meta)


# =============================================================================
# 6. App.fx.md
# =============================================================================
def write_doc(screens):
    md = ["# App.fx.md — named formulas, role logic, status logic, theme, navigation", "",
          "> **Generated by `app/build_app.py`. Don't edit by hand.** The same text is compiled into the app's",
          "> **App → Formulas** property, so this file always matches the app.", "",
          "## How the app is organised", "",
          "- **All logic is in named formulas** (`App.Formulas`). Named formulas recalculate automatically and are only",
          "  evaluated when used, so screens stay simple and the rules live in one place.",
          "- **OnStart** sets UI state only:", "", "```powerfx", APP_ONSTART, "```", "",
          "- **Data sources:** the five SharePoint lists, bound to the environment variables:", "",
          "| Data source in the app | Environment variable |", "|---|---|"]
    md += [f"| `{n}` | `{e}` (site: `{ENV_SITE}`) |" for n, e in DATA_SOURCES]
    md += ["",
           "- **Delegation:**",
           "  - Filters use indexed columns only: `Email`, `Status`, `Active`, `IsCurrent`, `DocType`, `EmployeeEmail` and `DocumentID`.",
           "  - The status logic (`AddColumns`, `LookUp` into the active-documents table) is **not delegable**. It works on the",
           "    first **2,000 current assignment rows**; the app's data row limit is set to 2000.",
           "  - Past that size, see Admin-Guide.md.", "",
           "- **Layout:** every screen is the same responsive shell. A horizontal container holds a",
           "  **left nav rail** (hidden on phones) and the main column (header, scrolling body, and a **bottom nav bar** on phones only).",
           "  Breakpoint: `fxIsPhone = App.Width < 640`. Scale-to-fit and lock-aspect-ratio are off.", "",
           "## Named formulas", ""]
    for title, body in FORMULA_SECTIONS:
        md += [f"### {title}", "", "```powerfx", body.strip("\n"), "```", ""]
    md += ["## Navigation", "",
           "- `fxNavItems` lists only the items the role may use.",
           "- The rail and the bottom bar both run:", "", "```powerfx", nav_onselect(), "```", "",
           "## Screens in this build", "", "| Screen | Purpose |", "|---|---|"]
    md += [f"| `{s}` | {p} |" for s, _, _, p in ALL_SCREENS]
    md += ["", "Screen layouts and actions are defined in `app/screens.py`.",
           "`app/tests/lint_formulas.py` syntax-checks every formula, and `app/tests/test_formulas.py` runs the named formulas against the seed data.", ""]
    open(os.path.join(HERE, "App.fx.md"), "w", encoding="utf-8").write("\n".join(md))


def main():
    schema = load_schema()
    screens, connection = write_sources(schema)
    print(f"Sources written: {len(screens)} screens, {len(DATA_SOURCES)} SharePoint data sources")
    run(["canvas", "pack", "--sources", SRC, "--msapp", MSAPP])
    print("Packed:", os.path.relpath(MSAPP, REPO), f"({os.path.getsize(MSAPP):,} bytes)")
    round_trip_check(screens)
    write_solution_app(connection)
    write_doc(screens)
    print("Added to solution:", os.path.relpath(SOLUTION_CANVAS, REPO))
    print("Wrote app/App.fx.md. Next: python3 solution/build.py")


if __name__ == "__main__":
    main()
