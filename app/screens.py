"""Screen definitions for JQC/PWI Management (build step 5).

Called by app/build_app.py: build(B) returns the list of screen controls, where B is the
build_app module (control classes and shared helpers). Every screen uses the same
responsive shell (B.screen): left nav rail on tablet/desktop, bottom nav bar on phones.

Conventions (CLAUDE.md Sections 7, 11, 14, 15)
- Every write: Patch inside IfError, Notify on success and failure, button disabled while
  gblSaving is true.
- Status is always text + colour from fxStatusStyle.
- Every gallery has an empty-state label.
- Prefixes: scr, con, gal, btn, lbl, txt, drp, cmb, col, loc, gbl.
"""

FLOW = "'JQCPWI-UploadFile'"
ALLOWED_EXT = '["pdf", "docx", "xlsx", "jpg", "jpeg", "png"]'


def build(B):
    C, q, label, vbox, hbox, screen = B.C, B.q, B.label, B.vbox, B.hbox, B.screen
    R = lambda r: {f"Radius{c}": r for c in ("TopLeft", "TopRight", "BottomLeft", "BottomRight")}
    SAVING = "If(gblSaving, DisplayMode.Disabled, DisplayMode.Edit)"
    FW = "If(fxIsPhone, Parent.Width - 32, 200)"      # filter control width

    def is_expr(t):
        return t.startswith(("\"", "If(", "With(", "Switch(", "Concat(", "CountRows(", "=")) or " & " in t

    def T(t):
        """Literal text -> quoted string; formula -> as is (a leading '=' forces formula)."""
        return t[1:] if t.startswith("=") else (t if is_expr(t) else q(t))

    # ------------------------------------------------------------------ control helpers
    def btn(name, text, onselect, style="primary", display=None, visible=None, width=160, height=44):
        fill, color, border = {"primary": ("clrPrimary", "Color.White", "clrPrimary"),
                               "secondary": ("clrPanel", "clrPrimary", "clrPrimary"),
                               "danger": ("clrPanel", "clrRed", "clrRed")}[style]
        p = {"Text": T(text), "OnSelect": onselect,
             "Fill": fill, "Color": color, "BorderColor": border, "BorderThickness": 1,
             "HoverFill": f"ColorFade({fill}, -10%)", "PressedFill": f"ColorFade({fill}, -20%)",
             "HoverColor": color, "PressedColor": color, "DisabledFill": "clrGreyBg", "DisabledColor": "clrGrey",
             "Font": B.FONT, "Size": 14, "FontWeight": "FontWeight.Semibold", "Width": width, "Height": height,
             "FillPortions": 0, **R(6)}
        if display:
            p["DisplayMode"] = display
        if visible:
            p["Visible"] = visible
        return C(name, "button", p)

    def txt(name, default='""', hint="", multiline=False, height=None, display=None, visible=None, width=None):
        p = {"Default": default, "HintText": q(hint), "Font": B.FONT, "Size": 14, "Color": "clrText",
             "BorderColor": "clrBorder", "Height": height or (96 if multiline else 44), "FillPortions": 0,
             "Mode": "TextMode.MultiLine" if multiline else "TextMode.SingleLine",
             "AccessibleLabel": q(hint or name), **R(4)}
        if width:
            p["Width"] = width
        if display:
            p["DisplayMode"] = display
        if visible:
            p["Visible"] = visible
        return C(name, "text", p)

    def drp(name, items, default='""', visible=None, display=None, label_text=None, width=None, value=None):
        p = {"Items": items, "Default": default, "Font": B.FONT, "Size": 14, "Color": "clrText",
             "BorderColor": "clrBorder", "Height": 44, "FillPortions": 0, "ChevronBackground": "clrPrimary",
             "AccessibleLabel": q(label_text or name)}
        if width:
            p["Width"] = width
        if value:
            p["Value"] = q(value)
        if visible:
            p["Visible"] = visible
        if display:
            p["DisplayMode"] = display
        return C(name, "dropdown", p)

    def cmb(name, items, multi=True, default="Blank()", fields='["Title"]', placeholder="Search", visible=None,
            display=None, label_text=None):
        p = {"Items": items, "SelectMultiple": "true" if multi else "false", "DefaultSelectedItems": default,
             "DisplayFields": fields, "SearchFields": fields, "IsSearchable": "true",
             "InputTextPlaceholder": q(placeholder), "Font": B.FONT, "Size": 14, "Color": "clrText",
             "BorderColor": "clrBorder", "Height": 44, "FillPortions": 0, "ChevronBackground": "clrPrimary",
             "AccessibleLabel": q(label_text or placeholder)}
        if visible:
            p["Visible"] = visible
        if display:
            p["DisplayMode"] = display
        return C(name, "combobox", p)

    def datepick(name, default="Blank()", visible=None, width=None):
        p = {"DefaultDate": default, "Format": "DateTimeFormat.ShortDate", "IsEditable": "true", "Font": B.FONT,
             "Size": 14, "Color": "clrText", "BorderColor": "clrBorder", "Height": 44, "FillPortions": 0,
             "IconBackground": "clrPrimary", "AccessibleLabel": q(name)}
        if width:
            p["Width"] = width
        if visible:
            p["Visible"] = visible
        return C(name, "datepicker", p)

    def chk(name, text, visible=None, display=None):
        p = {"Text": q(text), "Default": "false", "Font": B.FONT, "Size": 14, "Color": "clrText",
             "CheckboxBorderColor": "clrPrimary", "CheckmarkFill": "Color.White", "CheckboxBackgroundFill": "clrPanel",
             "Height": 56, "FillPortions": 0}
        if visible:
            p["Visible"] = visible
        if display:
            p["DisplayMode"] = display
        return C(name, "checkbox", p)

    def toggle(name, default, text):
        return C(name, "toggleSwitch", {"Default": default, "TrueText": q("Yes"), "FalseText": q("No"),
                                         "Height": 44, "FillPortions": 0, "TrueFill": "clrPrimary",
                                         "AccessibleLabel": q(text)})

    def attach(name, visible=None):
        p = {"MaxAttachments": 1, "MaxAttachmentSize": 25, "Height": 100, "FillPortions": 0,
             "NoAttachmentsText": q("No file selected"), "AddAttachmentText": q("Choose a file (PDF, DOCX, XLSX, JPG or PNG, max 25 MB)"),
             "BorderColor": "clrBorder", "BorderThickness": 1, "Font": B.FONT, "Size": 14, "Color": "clrText",
             "AccessibleLabel": q("File to upload")}
        if visible:
            p["Visible"] = visible
        return C(name, "attachments", p)

    def caption(name, text, visible=None, required=False):
        p = {"Height": 24, "FillPortions": 0}
        if visible:
            p["Visible"] = visible
        return label(name, q(text + (" *" if required else "")), size=13, color="clrMuted", bold=True, **p)

    def field(name, text, ctrl, required=False, visible=None):
        h = ctrl.props.get("Height", 44)
        p = {"Height": 28 + (h if isinstance(h, int) else 44), "FillPortions": 0, "LayoutGap": 4}
        if visible:
            p["Visible"] = visible
        return vbox(name, [caption("lbl" + name[3:], text, required=required), ctrl], **p)

    def heading(name, text, visible=None):
        p = {"Height": 32, "FillPortions": 0}
        if visible:
            p["Visible"] = visible
        return label(name, T(text), size=16, bold=True, **p)

    def note(name, text, visible=None, color="clrMuted", height=40):
        p = {"Height": height, "FillPortions": 0}
        if visible:
            p["Visible"] = visible
        return label(name, T(text), size=14, color=color, **p)

    def row(name, children, visible=None, height=48, gap=8, wrap=False):
        p = {"Height": height, "FillPortions": 0, "LayoutGap": gap, "LayoutAlignItems": "LayoutAlignItems.Center"}
        if wrap:
            p["LayoutWrap"] = "true"
        if visible:
            p["Visible"] = visible
        return hbox(name, children, **p)

    def card(name, children, visible=None, height=None, fill_portions=0):
        total = sum((c.props.get("Height") if isinstance(c.props.get("Height"), int) else 104) for c in children)
        p = {"Fill": "clrPanel", "BorderColor": "clrBorder", "BorderThickness": 1, "PaddingLeft": 16, "PaddingRight": 16,
             "PaddingTop": 12, "PaddingBottom": 12, "LayoutGap": 8, "FillPortions": fill_portions,
             "Height": height or (total + 8 * (len(children) - 1) + 26), **R(8)}
        if visible:
            p["Visible"] = visible
        return vbox(name, children, **p)

    def chip_props(status_expr, x, y, w=150, h=28):
        return {"Text": status_expr, "X": x, "Y": y, "Width": w, "Height": h, "Size": 12, "Align": "Align.Center",
                "Color": f"LookUp(fxStatusStyle, Status = {status_expr}, Fore)",
                "Fill": f"LookUp(fxStatusStyle, Status = {status_expr}, Back)",
                "FontWeight": "FontWeight.Semibold", "OnSelect": "Select(Parent)", **R(14)}

    def gallery(name, items, children, tsize=72, onselect=None, visible=None, min_h=240, empty=None, wrap=None):
        p = {"Items": items, "TemplateSize": tsize, "TemplatePadding": 0, "ShowScrollbar": "true",
             "BorderThickness": 0, "FillPortions": 1, "LayoutMinHeight": min_h, "Fill": "clrPanel",
             "AccessibleLabel": q(name)}
        if onselect:
            p["OnSelect"] = onselect
        if visible:
            p["Visible"] = visible
        if wrap:
            p["WrapCount"] = wrap
        line = C(name.replace("gal", "rect") + "Line", "rectangle", {
            "X": 0, "Y": "Parent.TemplateHeight - 1", "Width": "Parent.TemplateWidth", "Height": 1, "Fill": "clrBorder"})
        g = C(name, "gallery.galleryVertical", p, children + [line])
        out = [g]
        if empty:
            out.append(note("lbl" + name[3:] + "Empty", empty,
                            visible=f"CountRows({name}.AllItems) = 0" + (f" && ({visible})" if visible else ""),
                            height=40))
        return out

    def glabel(name, text, x, y, w, h=24, size=14, color="clrText", bold=False, **kw):
        return label(name, text, size=size, color=color, bold=bold, X=x, Y=y, Width=w, Height=h,
                     OnSelect="Select(Parent)", Wrap="false", **kw)

    def person(email_expr, name_expr):
        return (f'{{Claims: "i:0#.f|membership|" & Lower({email_expr}), DisplayName: {name_expr}, '
                f'Email: Lower({email_expr}), Department: "", JobTitle: "", Picture: ""}}')

    def save(patch_expr, ok_msg, after="true"):
        """Standard write: IfError + Notify + gblSaving (CLAUDE.md Section 7 rule 11)."""
        return (f"Set(gblSaving, true);\n"
                f"IfError(\n    {patch_expr},\n"
                f"    Notify(\"Couldn't save: \" & FirstError.Message, NotificationType.Error),\n"
                f"    Notify({q(ok_msg)}, NotificationType.Success);\n    {after}\n);\n"
                f"Set(gblSaving, false)")

    def upload(att, target, existing, meta):
        """Call the upload flow (CLAUDE.md Section 11). Result in gblUpload {success, itemid, fileurl, message}."""
        if getattr(B, "DEMO", False):   # demo build: no flow, no SharePoint
            return 'Set(gblUpload, {success: "false", itemid: 0, fileurl: "", message: "Uploads are turned off in demo mode."})'
        return (f"IfError(\n"
                f"    Set(gblUpload, {FLOW}.Run(\n"
                f"        {{name: First({att}.Attachments).Name, contentBytes: First({att}.Attachments).Value}},\n"
                f"        {q(target)},\n        {existing},\n        JSON({meta}, JSONFormat.IgnoreBinaryData)\n    )),\n"
                f"    Set(gblUpload, {{success: \"false\", itemid: 0, fileurl: \"\", message: FirstError.Message}})\n)")

    def file_ok(att):
        return (f"CountRows({att}.Attachments) = 1 && "
                f"Lower(Last(Split(First({att}.Attachments).Name, \".\")).Value) in {ALLOWED_EXT}")

    def file_ext(att):
        return f'Lower(Last(Split(First({att}.Attachments).Name, ".")).Value)'

    screens = []

    # ================================================================== scrHome
    screens.append(B.home_screen())

    # ================================================================== scrEmployees
    emp_items = """SortByColumns(
    Filter(
        JP_Employees,
        tglEmpInactive.Value || Active,
        IsBlank(drpEmpDept.Selected.Value) || drpEmpDept.Selected.Value = "All" || Department.Value = drpEmpDept.Selected.Value,
        IsBlank(drpEmpShift.Selected.Value) || drpEmpShift.Selected.Value = "All" || Shift.Value = drpEmpShift.Selected.Value,
        IsBlank(txtEmpSearch.Text) || StartsWith(Title, txtEmpSearch.Text) || StartsWith(Email, txtEmpSearch.Text)
    ),
    "Title"
)
// Delegation: Active / Department / Shift / StartsWith are delegable for SharePoint; "||" combinations may not be.
// The app's data row limit (2000) applies to employees."""
    emp_row = [
        glabel("lblEmpRowName", 'ThisItem.Title & If(ThisItem.Active, "", "  (Inactive)")', 16, 10,
               "Parent.TemplateWidth - 190", bold=True),
        glabel("lblEmpRowSub", 'ThisItem.JobTitle.Value & " · " & ThisItem.Department.Value & " · " & ThisItem.Shift.Value & "  " & ThisItem.Email',
               16, 38, "Parent.TemplateWidth - 190", size=13, color="clrMuted"),
        glabel("lblEmpRowRole", "ThisItem.AppRole.Value", "Parent.TemplateWidth - 170", 22, 160, size=13,
               color="clrPrimary", Align="Align.Right"),
    ]
    emp_select = "Set(gblSelEmployee, ThisItem); Navigate(scrEmployeeDetail, ScreenTransition.None)"
    emp_form_fields = [
        heading("lblEmpFormTitle", 'If(IsBlank(gblEmpForm), "Add employee", "Edit employee")'),
        field("conEmpName", "Name", txt("txtEmpName", "gblEmpForm.Title", "Full name"), required=True),
        field("conEmpEmail", "Email", txt("txtEmpEmail", "gblEmpForm.Email", "name@company.com"), required=True),
        field("conEmpJob", "Job title", drp("drpEmpJob", "Choices([@JP_Employees].JobTitle)", "gblEmpForm.JobTitle.Value",
                                            label_text="Job title"), required=True),
        field("conEmpDeptF", "Department", drp("drpEmpDeptF", "Choices([@JP_Employees].Department)",
                                               "gblEmpForm.Department.Value", label_text="Department")),
        field("conEmpShiftF", "Shift", drp("drpEmpShiftF", "Choices([@JP_Employees].Shift)", "gblEmpForm.Shift.Value",
                                           label_text="Shift")),
        field("conEmpSup", "Supervisor", cmb("cmbEmpSup", "Filter(fxManagers, ID <> Coalesce(gblEmpForm.ID, 0))", multi=False,
                                             default="Filter(fxManagers, ID = gblEmpForm.Supervisor.Id)",
                                             placeholder="Pick a manager or supervisor", label_text="Supervisor")),
        field("conEmpRole", "App role", drp("drpEmpRole", "Choices([@JP_Employees].AppRole)",
                                            'Coalesce(gblEmpForm.AppRole.Value, "Technician")', label_text="App role"),
              required=True),
        field("conEmpActive", "Active", toggle("tglEmpActive", "Coalesce(gblEmpForm.Active, true)", "Active")),
    ]
    emp_missing = """Concat(
    Filter(
        Table(
            {F: "Name", Ok: !IsBlank(Trim(txtEmpName.Text))},
            {F: "Email", Ok: !IsBlank(Trim(txtEmpEmail.Text))},
            {F: "Job title", Ok: !IsBlank(drpEmpJob.Selected.Value)},
            {F: "App role", Ok: !IsBlank(drpEmpRole.Selected.Value)}
        ),
        !Ok
    ),
    F,
    ", "
)"""
    emp_patch = f"""Patch(
        JP_Employees,
        If(IsBlank(gblEmpForm), Defaults(JP_Employees), LookUp(JP_Employees, ID = gblEmpForm.ID)),
        {{
            Title: Trim(txtEmpName.Text),
            Email: Lower(Trim(txtEmpEmail.Text)),
            JobTitle: {{Value: drpEmpJob.Selected.Value}},
            Department: If(IsBlank(drpEmpDeptF.Selected.Value), Blank(), {{Value: drpEmpDeptF.Selected.Value}}),
            Shift: If(IsBlank(drpEmpShiftF.Selected.Value), Blank(), {{Value: drpEmpShiftF.Selected.Value}}),
            Supervisor: If(IsBlank(cmbEmpSup.Selected), Blank(), {{Id: cmbEmpSup.Selected.ID, Value: cmbEmpSup.Selected.Title}}),
            AppRole: {{Value: drpEmpRole.Selected.Value}},
            Active: tglEmpActive.Value
        }}
    )"""
    emp_save = f"""If(
    !IsBlank({emp_missing}),
    Notify("Please fill in: " & {emp_missing}, NotificationType.Warning),
    // Email must be unique (CLAUDE.md Section 6.1)
    CountRows(Filter(JP_Employees, Email = Lower(Trim(txtEmpEmail.Text)), ID <> Coalesce(gblEmpForm.ID, 0))) > 0,
    Notify("Another employee already uses this email.", NotificationType.Warning),
    {save(emp_patch, "Employee saved.", "Set(gblShowEmpForm, false); Set(gblEmpForm, Blank())")}
)"""
    emp_form = card("conEmpForm", emp_form_fields + [
        row("conEmpFormButtons", [btn("btnEmpSave", "Save", emp_save, display=SAVING),
                                  btn("btnEmpCancel", "Cancel", "Set(gblShowEmpForm, false); Set(gblEmpForm, Blank())",
                                      style="secondary")])], visible="gblShowEmpForm && fxIsManager")
    emp_form.props.update({"Width": "If(fxIsPhone, Parent.Width, 400)", "FillPortions": "If(fxIsPhone, 1, 0)",
                           "LayoutOverflowY": "LayoutOverflow.Scroll", "Height": 760})
    emp_list = vbox("conEmpList", [
        row("conEmpFilters", [
            txt("txtEmpSearch", hint="Search name or email", width=FW),
            drp("drpEmpDept", 'Ungroup(Table({V: ["All"]}, {V: ShowColumns(Choices([@JP_Employees].Department), Value)}), "V")', '"All"',
                label_text="Department filter", width=FW),
            drp("drpEmpShift", 'Ungroup(Table({V: ["All"]}, {V: ShowColumns(Choices([@JP_Employees].Shift), Value)}), "V")', '"All"',
                label_text="Shift filter", width=FW),
            toggle("tglEmpInactive", "false", "Show inactive"),
            label("lblEmpInactive", q("Show inactive"), size=13, color="clrMuted", Width=110, Height=44, FillPortions=0),
            btn("btnEmpAdd", "+ Add employee", "Set(gblEmpForm, Blank()); Set(gblShowEmpForm, true)",
                visible="fxIsManager", width=170),
        ], height="If(fxIsPhone, 160, 56)", wrap=True),
        *gallery("galEmployees", emp_items, emp_row, tsize=72, onselect=emp_select,
                 empty="No employees match these filters."),
    ], FillPortions=1, LayoutGap=8, Visible="!(fxIsPhone && gblShowEmpForm)")
    screens.append(screen("scrEmployees", "Employees", "employees", [
        hbox("conEmpPanes", [emp_list, emp_form], FillPortions=1, LayoutGap=16)]))

    # ================================================================== scrEmployeeDetail
    sel_emp_ok = "!IsBlank(gblSelEmployee) && (fxIsManager || fxIsViewer || Lower(gblSelEmployee.Email) = fxMeEmail)"
    cur_items = """SortByColumns(
    Filter(fxAssignmentDisplayStatus, Employee.Id = gblSelEmployee.ID && DocIsActive),
    "DocNumber"
)"""
    prev_items = """SortByColumns(
    Filter(JP_Assignments, EmployeeEmail = gblSelEmployee.Email, IsCurrent = false),
    "Modified", SortOrder.Descending
)
// Delegable: EmployeeEmail (text, indexed) and IsCurrent (Yes/No, indexed)."""
    cur_row = [
        glabel("lblEdCurDoc", 'ThisItem.DocNumber & " – " & ThisItem.DocTitle', 16, 10, "Parent.TemplateWidth - 200", bold=True),
        glabel("lblEdCurSub", '"Rev " & ThisItem.RevisionAssigned & If(IsBlank(ThisItem.DueDate), "", " · Due " & Text(ThisItem.DueDate, DateTimeFormat.ShortDate)) & If(ThisItem.ShowNewRevisionBadge, " · New Revision", "")',
               16, 38, "Parent.TemplateWidth - 200", size=13, color="clrMuted"),
        C("lblEdCurStatus", "label", chip_props("ThisItem.DisplayStatus", "Parent.TemplateWidth - 170", 22)),
    ]
    prev_row = [
        glabel("lblEdPrevDoc", 'ThisItem.DocNumber & " Rev " & ThisItem.RevisionAssigned & " – " & ThisItem.Status.Value', 16, 10,
               "Parent.TemplateWidth - 150", bold=True),
        glabel("lblEdPrevSub", 'If(IsBlank(ThisItem.SignedOffDate), "Not signed off", "Signed off " & Text(ThisItem.SignedOffDate, DateTimeFormat.ShortDate) & " by " & ThisItem.SignedOffBy.DisplayName)',
               16, 38, "Parent.TemplateWidth - 150", size=13, color="clrMuted"),
        btn("btnEdPrevFile", "Open file", "Launch(LookUp(JP_SignoffRecords, ID = ThisItem.SignoffFileID).'{Link}')",
            style="secondary", width=120, height=40,
            visible="!IsBlank(ThisItem.SignoffFileID) && ThisItem.SignoffFileID > 0 && (fxIsManager || fxIsViewer || Lower(ThisItem.EmployeeEmail) = fxMeEmail)"),
    ]
    prev_row[-1].props.update({"X": "Parent.TemplateWidth - 136", "Y": 16})
    remove_patch = """Patch(
        JP_Assignments,
        LookUp(JP_Assignments, ID = locRemoveRow.ID),
        {Status: {Value: "Removed"}, IsCurrent: false, Comments: "Removed: " & Trim(txtEdRemoveReason.Text)}
    )"""
    remove_save = f"""If(
    IsBlank(Trim(txtEdRemoveReason.Text)),
    Notify("Please enter a reason for removing this assignment.", NotificationType.Warning),
    {save(remove_patch, "Assignment removed.", "Refresh(JP_Assignments); UpdateContext({locRemoveRow: Blank()}); Reset(txtEdRemoveReason)")}
)"""
    screens.append(screen("scrEmployeeDetail", "Employee", "employees", [
        note("lblEdNoAccess", "You can only view your own items.", visible=f"!({sel_emp_ok})", color="clrRed"),
        card("conEdProfile", [
            heading("lblEdName", 'gblSelEmployee.Title & If(gblSelEmployee.Active, "", "  (Inactive)")'),
            note("lblEdInfo", 'gblSelEmployee.JobTitle.Value & " · " & gblSelEmployee.Department.Value & " · Shift " & gblSelEmployee.Shift.Value & " · " & gblSelEmployee.AppRole.Value & Char(10) & gblSelEmployee.Email & If(IsBlank(gblSelEmployee.Supervisor.Value), "", " · Supervisor: " & gblSelEmployee.Supervisor.Value)',
                 color="clrText", height=48),
            row("conEdButtons", [
                btn("btnEdEdit", "Edit", "Set(gblEmpForm, gblSelEmployee); Set(gblShowEmpForm, true); Navigate(scrEmployees, ScreenTransition.None)",
                    style="secondary", width=120),
                btn("btnEdAssign", "Assign", "Set(gblAssignEmpIds, Table({ID: gblSelEmployee.ID})); Set(gblAssignDocIds, Blank()); Navigate(scrAssign, ScreenTransition.None)",
                    width=120, visible="gblSelEmployee.Active"),
            ], visible="fxIsManager"),
        ], visible=sel_emp_ok),
        heading("lblEdCurHead", "Current assignments", visible=sel_emp_ok),
        *gallery("galEdCurrent", cur_items, cur_row + [
            C("btnEdRemove", "button", {**btn("x", "Remove", "UpdateContext({locRemoveRow: ThisItem})", style="danger",
                                               width=90, height=32, visible="fxIsManager").props,
                                        "X": "Parent.TemplateWidth - 270", "Y": 20})], tsize=72, visible=sel_emp_ok, min_h=200,
                 onselect="Set(gblSelAssignment, ThisItem); Navigate(scrAssignmentDetail, ScreenTransition.None)",
                 empty="No current assignments."),
        card("conEdRemove", [
            heading("lblEdRemoveHead", '"Remove " & locRemoveRow.DocNumber & " from " & gblSelEmployee.Title & "?"'),
            field("conEdRemoveReason", "Reason", txt("txtEdRemoveReason", hint="Why is this assignment removed?"), required=True),
            row("conEdRemoveButtons", [btn("btnEdRemoveConfirm", "Remove", remove_save, style="danger", display=SAVING),
                                       btn("btnEdRemoveCancel", "Cancel", "UpdateContext({locRemoveRow: Blank()})", style="secondary")]),
        ], visible="!IsBlank(locRemoveRow) && fxIsManager"),
        heading("lblEdPrevHead", "Previous revisions and history", visible=sel_emp_ok),
        *gallery("galEdPrevious", prev_items, prev_row, tsize=72, visible=sel_emp_ok, min_h=200,
                 empty="No history yet."),
    ]))

    # ================================================================== Libraries (JQC / PWI)
    def library(scr, doc_type, key):
        sfx = doc_type
        items = f"""SortByColumns(
    Filter(
        JP_Documents,
        DocType.Value = "{doc_type}",
        drpLib{sfx}Status.Selected.Value = "All" || Status.Value = drpLib{sfx}Status.Selected.Value,
        drpLib{sfx}Area.Selected.Value = "All" || Area.Value = drpLib{sfx}Area.Selected.Value,
        IsBlank(txtLib{sfx}Search.Text) || StartsWith(DocNumber, txtLib{sfx}Search.Text) || StartsWith(DocTitle, txtLib{sfx}Search.Text)
    ),
    "DocNumber"
)"""
        counts = (f'With({{q: CountRows(Filter(fxAssignmentDisplayStatus, DocumentID = ThisItem.ID && IsQualified)), '
                  f'y: CountRows(Filter(fxAssignmentDisplayStatus, DocumentID = ThisItem.ID && EmpIsActive && StatusText <> "Removed")), '
                  f'n: CountRows(Filter(fxAssignmentDisplayStatus, DocumentID = ThisItem.ID && EmpIsActive && StatusText = "Assigned"))}}, '
                  + ('q & " of " & y & " qualified on current rev · " & n & " Needs Training"' if doc_type == "JQC"
                     else 'q & " of " & y & " signed off on current rev"') + ")")
        r = [
            glabel(f"lblLib{sfx}Num", 'ThisItem.DocNumber & " – " & ThisItem.DocTitle & If(ThisItem.Status.Value = "Obsolete", "  (Obsolete)", "")',
                   16, 8, "Parent.TemplateWidth - 32", bold=True),
            glabel(f"lblLib{sfx}Rev", '"Rev " & ThisItem.Revision & " · " & Text(ThisItem.RevisionDate, DateTimeFormat.ShortDate) & " · " & ThisItem.Area.Value & " · Trainers: " & If(CountRows(ThisItem.Trainers) = 0, "none", Concat(ThisItem.Trainers, DisplayName, ", "))',
                   16, 34, "Parent.TemplateWidth - 32", size=13, color="clrMuted"),
            glabel(f"lblLib{sfx}Counts", counts, 16, 58, "Parent.TemplateWidth - 32", size=13),
            glabel(f"lblLib{sfx}NoTrainer", q("No trainer — can't assign"), 16, 82, 240, size=13, color="clrRed",
                   Visible="CountRows(ThisItem.Trainers) = 0 && fxIsManager"),
        ]
        buttons = [("Open", "Launch(ThisItem.'{Link}')", "true", "secondary")]
        if doc_type == "PWI":
            buttons.append(("Status", "Set(gblSelDoc, ThisItem); Navigate(scrPWIStatus, ScreenTransition.None)",
                            "fxIsManager || fxIsViewer", "secondary"))
        buttons.append(("Edit", f'Set(gblDocForm, ThisItem); Set(gblDocFormType, "{doc_type}"); Set(gblDocMode, "edit"); Navigate(scrDocumentEdit, ScreenTransition.None)',
                        'fxIsManager && ThisItem.Status.Value = "Active"', "secondary"))
        buttons.append(("New revision", f'Set(gblDocForm, ThisItem); Set(gblDocFormType, "{doc_type}"); Set(gblDocMode, "revise"); Navigate(scrDocumentEdit, ScreenTransition.None)',
                        'fxIsManager && ThisItem.Status.Value = "Active"', "secondary"))
        for i, (t, on, vis, style) in enumerate(buttons):
            b = btn(f"btnLib{sfx}{t.replace(' ', '')}", t, on, style=style, width=140 if t == "New revision" else 100, height=40,
                    visible=vis)
            b.props.update({"X": 16 + i * 112, "Y": 108})
            r.append(b)
        title = "JQC Library" if doc_type == "JQC" else "PWI Library"
        return screen(scr, title, key, [
            row(f"conLib{sfx}Filters", [
                txt(f"txtLib{sfx}Search", hint="Search number or title", width=FW),
                drp(f"drpLib{sfx}Area", 'Ungroup(Table({V: ["All"]}, {V: ShowColumns(Choices([@JP_Documents].Area), Value)}), "V")', '"All"',
                    label_text="Area filter", width=FW),
                drp(f"drpLib{sfx}Status", '["Active", "Obsolete", "All"]', '"Active"', label_text="Status filter", width=FW),
                btn(f"btnLib{sfx}Add", f"+ Add {doc_type}",
                    f'Set(gblDocForm, Blank()); Set(gblDocFormType, "{doc_type}"); Set(gblDocMode, "new"); Navigate(scrDocumentEdit, ScreenTransition.None)',
                    visible="fxIsManager", width=140),
            ], height="If(fxIsPhone, 160, 56)", wrap=True),
            *gallery(f"galLib{sfx}", items, r, tsize=160, empty=f"No {doc_type}s match these filters."),
        ])

    screens.append(library("scrJQCLibrary", "JQC", "jqc"))
    screens.append(library("scrPWILibrary", "PWI", "pwi"))

    # ================================================================== scrDocumentEdit
    is_new, is_edit, is_rev = 'gblDocMode = "new"', 'gblDocMode = "edit"', 'gblDocMode = "revise"'
    trainers_json = "ForAll(cmbDocTrainers.SelectedItems As t, {Claims: Lower(t.Email)})"
    trainers_people = f"ForAll(cmbDocTrainers.SelectedItems As t, {person('t.Email', 't.Title')})"
    affected = """Filter(
        fxAssignmentDisplayStatus,
        DocumentID = gblDocForm.ID && EmpIsActive && RevisionAssigned <> Trim(txtDocNewRev.Text)
            && (StatusText = "Assigned" || StatusText = "In Training" || StatusText = "Signed Off")
    )"""
    new_meta = f"""{{
            FileName: Upper(Trim(txtDocNumber.Text)) & "." & {file_ext('attDoc')},
            DocType: gblDocFormType, DocNumber: Upper(Trim(txtDocNumber.Text)), DocTitle: Trim(txtDocTitle.Text),
            Revision: Trim(txtDocRev.Text), RevisionDate: Text(Today(), "yyyy-mm-dd"), RevisionNotes: Trim(txtDocNotes.Text),
            Area: drpDocArea.Selected.Value, Status: "Active", Trainers: {trainers_json}, Description: Trim(txtDocDesc.Text)
        }}"""
    rev_meta = f"""{{
            FileName: gblDocForm.'{{Name}}',
            DocType: gblDocForm.DocType.Value, DocNumber: gblDocForm.DocNumber, DocTitle: gblDocForm.DocTitle,
            Revision: Trim(txtDocNewRev.Text), RevisionDate: Text(Today(), "yyyy-mm-dd"), RevisionNotes: Trim(txtDocRevNotes.Text),
            Area: gblDocForm.Area.Value, Status: "Active",
            Trainers: ForAll(gblDocForm.Trainers As t, {{Claims: Lower(t.Email)}}), Description: gblDocForm.Description
        }}"""
    new_missing = """Concat(Filter(Table(
        {F: "Document number", Ok: !IsBlank(Trim(txtDocNumber.Text))},
        {F: "Title", Ok: !IsBlank(Trim(txtDocTitle.Text))},
        {F: "Revision", Ok: !IsBlank(Trim(txtDocRev.Text))},
        {F: "File (PDF, DOCX, XLSX, JPG or PNG)", Ok: """ + file_ok("attDoc") + """}
    ), !Ok), F, ", ")"""
    new_save = f"""If(
    !IsBlank({new_missing}),
    Notify("Please fill in: " & {new_missing}, NotificationType.Warning),
    CountRows(Filter(JP_Documents, DocNumber = Upper(Trim(txtDocNumber.Text)))) > 0,
    Notify("Document number " & Upper(Trim(txtDocNumber.Text)) & " already exists.", NotificationType.Warning),
    Set(gblSaving, true);
    {upload('attDoc', 'Documents', '0', new_meta)};
    If(
        gblUpload.success = "true",
        // The flow only saves the file; the app sets its columns (SPEC.md A-38).
        IfError(
            Patch(JP_Documents, LookUp(JP_Documents, ID = gblUpload.itemid), {{
                Title: Upper(Trim(txtDocNumber.Text)),
                DocType: {{Value: gblDocFormType}},
                DocNumber: Upper(Trim(txtDocNumber.Text)),
                DocTitle: Trim(txtDocTitle.Text),
                Revision: Trim(txtDocRev.Text),
                RevisionDate: Today(),
                RevisionNotes: Trim(txtDocNotes.Text),
                Area: If(IsBlank(drpDocArea.Selected.Value), Blank(), {{Value: drpDocArea.Selected.Value}}),
                Status: {{Value: "Active"}},
                Trainers: {trainers_people},
                Description: Trim(txtDocDesc.Text)
            }}),
            Notify("The file was uploaded, but its details couldn't be saved: " & FirstError.Message, NotificationType.Error),
            Notify("Document added.", NotificationType.Success); Refresh(JP_Documents); Reset(attDoc);
            Navigate(If(gblDocFormType = "JQC", scrJQCLibrary, scrPWILibrary), ScreenTransition.None)
        ),
        Notify(gblUpload.message, NotificationType.Error)
    );
    Set(gblSaving, false)
)"""
    edit_patch = f"""Patch(
        JP_Documents,
        LookUp(JP_Documents, ID = gblDocForm.ID),
        {{
            DocTitle: Trim(txtDocTitle.Text),
            Area: If(IsBlank(drpDocArea.Selected.Value), Blank(), {{Value: drpDocArea.Selected.Value}}),
            Description: Trim(txtDocDesc.Text),
            Trainers: {trainers_people}
        }}
    )"""
    edit_save = f"""If(
    IsBlank(Trim(txtDocTitle.Text)),
    Notify("Please fill in: Title", NotificationType.Warning),
    {save(edit_patch, "Document saved.", "Refresh(JP_Documents); Back()")}
)"""
    obsolete_patch = """Patch(JP_Documents, LookUp(JP_Documents, ID = gblDocForm.ID), {Status: {Value: "Obsolete"}})"""
    # Revision change: CLAUDE.md Section 7 rules 8 (PWI) and 9 (JQC), SPEC.md BR-31 to BR-38.
    # Re-assign logic (also used by Retry): for every row still current on an older revision,
    # create the new row first (unless one already exists), then close the old row. A failed row
    # is left current on the old revision, so Retry simply runs the same logic again.
    reassign = """ClearCollect(
        colRevResults,
        ForAll(
            Filter(
                JP_Assignments,
                DocumentID = gblRevDoc.ID,
                IsCurrent = true
            ) As r,
            // Delegable: DocumentID (number) and IsCurrent (Yes/No) are indexed. Designed for up to
            // 500 rows per document (Admin-Guide.md); the rest of this logic runs in the app.
            If(
                r.RevisionAssigned <> gblRevDoc.NewRev
                    && (r.Status.Value = "Assigned" || r.Status.Value = "In Training" || r.Status.Value = "Signed Off")
                    && !IsBlank(LookUp(fxEmployeesActive, ID = r.Employee.Id, ID)),
                IfError(
                    If(
                        IsBlank(LookUp(JP_Assignments, DocumentID = gblRevDoc.ID && EmployeeEmail = r.EmployeeEmail && IsCurrent = true && RevisionAssigned = gblRevDoc.NewRev, ID)),
                        Patch(JP_Assignments, Defaults(JP_Assignments), {
                            Title: r.DocNumber & " Rev " & gblRevDoc.NewRev & " – " & r.Employee.Value,
                            Employee: {Id: r.Employee.Id, Value: r.Employee.Value},
                            EmployeeEmail: r.EmployeeEmail,
                            DocumentID: gblRevDoc.ID,
                            DocType: {Value: r.DocType.Value},
                            DocNumber: r.DocNumber,
                            DocTitle: r.DocTitle,
                            RevisionAssigned: gblRevDoc.NewRev,
                            AssignmentReason: {Value: "Revision Change"},
                            PreviousAssignmentID: r.ID,
                            IsCurrent: true,
                            AssignedBy: fxMePerson,
                            AssignedDate: Today(),
                            DueDate: DateAdd(Today(), fxResignDueDays, TimeUnit.Days),
                            Trainer: r.Trainer,
                            Status: {Value: "Assigned"}
                        })
                    );
                    Patch(JP_Assignments, LookUp(JP_Assignments, ID = r.ID), {
                        Status: If(r.Status.Value = "Signed Off", {Value: "Superseded"}, {Value: r.Status.Value}),
                        IsCurrent: false
                    });
                    {Employee: r.Employee.Value, Ok: true},
                    {Employee: r.Employee.Value, Ok: false}
                ),
                Blank()
            )
        )
    );
    RemoveIf(colRevResults, IsBlank(Employee));
    Refresh(JP_Assignments)"""
    rev_missing = """Concat(Filter(Table(
        {F: "New revision (different from the current one)", Ok: !IsBlank(Trim(txtDocNewRev.Text)) && Trim(txtDocNewRev.Text) <> gblDocForm.Revision},
        {F: "Revision notes", Ok: !IsBlank(Trim(txtDocRevNotes.Text))},
        {F: "File (PDF, DOCX, XLSX, JPG or PNG)", Ok: """ + file_ok("attDocRev") + """}
    ), !Ok), F, ", ")"""
    rev_confirm_msg = f"""With(
    {{n: CountRows({affected})}},
    If(
        gblDocForm.DocType.Value = "PWI",
        "This will require " & n & " employees to sign off on Rev " & Trim(txtDocNewRev.Text) & ".",
        "This will put " & n & " employees back to Needs Training on Rev " & Trim(txtDocNewRev.Text) & ". Their current qualification will no longer count."
    )
)"""
    rev_go = f"""Set(gblSaving, true);
Set(gblRevDoc, {{ID: gblDocForm.ID, NewRev: Trim(txtDocNewRev.Text)}});
{upload('attDocRev', 'Documents', 'gblDocForm.ID', rev_meta)};
If(
    gblUpload.success = "true",
    // The flow replaced the file; the app updates the revision columns (SPEC.md A-38).
    IfError(
        Patch(JP_Documents, LookUp(JP_Documents, ID = gblDocForm.ID), {{
            Revision: Trim(txtDocNewRev.Text), RevisionDate: Today(), RevisionNotes: Trim(txtDocRevNotes.Text)
        }}),
        Notify("The new file was uploaded, but the revision details couldn't be saved: " & FirstError.Message, NotificationType.Error)
    );
    Refresh(JP_Documents);
    {reassign};
    UpdateContext({{locRevConfirm: false, locRevDone: true}});
    Notify(CountRows(Filter(colRevResults, Ok)) & " re-assigned, " & CountRows(Filter(colRevResults, !Ok)) & " failed.",
        If(CountRows(Filter(colRevResults, !Ok)) = 0, NotificationType.Success, NotificationType.Warning)),
    Notify(gblUpload.message, NotificationType.Error)
);
Set(gblSaving, false)"""
    rev_retry = f"""Set(gblSaving, true);
{reassign};
Notify(CountRows(Filter(colRevResults, Ok)) & " re-assigned, " & CountRows(Filter(colRevResults, !Ok)) & " failed.",
    If(CountRows(Filter(colRevResults, !Ok)) = 0, NotificationType.Success, NotificationType.Warning));
Set(gblSaving, false)"""
    doc_people = "fxEligibleEmployees"
    screens.append(screen("scrDocumentEdit", "Document", "jqc", [
        heading("lblDocHead", 'Switch(gblDocMode, "new", "Add " & gblDocFormType, "edit", "Edit " & gblDocForm.DocNumber, "revise", "Upload new revision – " & gblDocForm.DocNumber)'),
        note("lblDocNoAccess", "Only managers and supervisors can change documents.", visible="!fxIsManager", color="clrRed"),
        card("conDocMain", [
            field("conDocNumber", "Document number", txt("txtDocNumber", '""', "For example PWI-DEMO-100"),
                  required=True, visible=is_new),
            field("conDocTitle", "Title", txt("txtDocTitle", "gblDocForm.DocTitle", "Document title"), required=True),
            field("conDocArea", "Area", drp("drpDocArea", "Choices([@JP_Documents].Area)", "gblDocForm.Area.Value", label_text="Area")),
            field("conDocTrainers", "Trainers (needed before the document can be assigned)",
                  cmb("cmbDocTrainers", doc_people, default=f"Filter({doc_people}, Lower(Email) in ShowColumns(ForAll(gblDocForm.Trainers As t, {{E: Lower(t.Email)}}), E))",
                      placeholder="Search employees", label_text="Trainers")),
            field("conDocDesc", "Description", txt("txtDocDesc", "gblDocForm.Description", "Description", multiline=True)),
            field("conDocRev", "Revision", txt("txtDocRev", '"A"', "For example A"), required=True, visible=is_new),
            field("conDocNotes", "Revision notes", txt("txtDocNotes", '"Initial release."', "Revision notes", multiline=True),
                  visible=is_new),
            field("conDocFile", "File", attach("attDoc"), required=True, visible=is_new),
            row("conDocButtons", [
                btn("btnDocCreate", "Add document", new_save, display=SAVING, visible=is_new, width=170),
                btn("btnDocSave", "Save", edit_save, display=SAVING, visible=is_edit),
                btn("btnDocObsolete", "Mark obsolete", "UpdateContext({locObsoleteConfirm: true})", style="danger",
                    visible=is_edit),
                btn("btnDocCancel", "Cancel", "Back()", style="secondary"),
            ], wrap=True, height="If(fxIsPhone, 104, 48)"),
        ], visible=f"fxIsManager && ({is_new} || {is_edit})"),
        card("conDocObsolete", [
            note("lblDocObsoleteMsg", '"Mark " & gblDocForm.DocNumber & " as obsolete? It can no longer be assigned or revised and leaves the matrix and cross-training views. Nothing is deleted."',
                 color="clrText", height=48),
            row("conDocObsoleteButtons", [
                btn("btnDocObsoleteYes", "Mark obsolete", save(obsolete_patch, "Document marked obsolete.",
                                                               "Refresh(JP_Documents); UpdateContext({locObsoleteConfirm: false}); Back()"),
                    style="danger", display=SAVING),
                btn("btnDocObsoleteNo", "Cancel", "UpdateContext({locObsoleteConfirm: false})", style="secondary")]),
        ], visible=f"locObsoleteConfirm && {is_edit}"),
        card("conDocRevise", [
            note("lblDocRevCurrent", '"Current revision: " & gblDocForm.Revision & " (" & Text(gblDocForm.RevisionDate, DateTimeFormat.ShortDate) & ")"',
                 color="clrText", height=28),
            field("conDocNewRev", "New revision", txt("txtDocNewRev", hint="For example B"), required=True),
            field("conDocRevNotes", "Revision notes (shown to employees)", txt("txtDocRevNotes", hint="What changed?", multiline=True),
                  required=True),
            field("conDocRevFile", "New file", attach("attDocRev"), required=True),
            row("conDocRevButtons", [
                btn("btnDocRevNext", "Upload New Revision",
                    f'If(!IsBlank({rev_missing}), Notify("Please fill in: " & {rev_missing}, NotificationType.Warning), UpdateContext({{locRevConfirm: true}}))',
                    display=SAVING, width=210),
                btn("btnDocRevCancel", "Cancel", "Back()", style="secondary"),
            ]),
        ], visible=f"fxIsManager && {is_rev} && !locRevDone"),
        card("conDocRevConfirm", [
            note("lblDocRevConfirm", rev_confirm_msg, color="clrText", height=56),
            row("conDocRevConfirmButtons", [
                btn("btnDocRevGo", "Confirm", rev_go, display=SAVING),
                btn("btnDocRevBack", "Go back", "UpdateContext({locRevConfirm: false})", style="secondary")]),
        ], visible=f"locRevConfirm && {is_rev}"),
        card("conDocRevResult", [
            heading("lblDocRevResult", 'CountRows(Filter(colRevResults, Ok)) & " re-assigned, " & CountRows(Filter(colRevResults, !Ok)) & " failed"'),
            note("lblDocRevFailed", '"Failed: " & Concat(Filter(colRevResults, !Ok), Employee, ", ")',
                 visible="CountRows(Filter(colRevResults, !Ok)) > 0", color="clrRed"),
            row("conDocRevResultButtons", [
                btn("btnDocRevRetry", "Retry failures", rev_retry, display=SAVING,
                    visible="CountRows(Filter(colRevResults, !Ok)) > 0", width=170),
                btn("btnDocRevDone", "Done", "UpdateContext({locRevDone: false}); Back()", style="secondary")]),
        ], visible=f"locRevDone && {is_rev}"),
    ]))
    screens[-1].props["OnVisible"] = ('Set(gblNavKey, If(gblDocFormType = "PWI", "pwi", "jqc")); '
                                      'UpdateContext({locRevConfirm: false, locRevDone: false, locObsoleteConfirm: false}); '
                                      'Reset(txtDocNumber); Reset(txtDocTitle); Reset(drpDocArea); Reset(cmbDocTrainers); Reset(txtDocDesc); '
                                      'Reset(txtDocRev); Reset(txtDocNotes); Reset(attDoc); Reset(txtDocNewRev); Reset(txtDocRevNotes); Reset(attDocRev)')

    # ================================================================== scrAssign
    preview = """Clear(colAssignPreview);
ForAll(
    cmbAssignEmp.SelectedItems As e,
    ForAll(
        cmbAssignDoc.SelectedItems As d,
        Collect(colAssignPreview, {
            EmpId: e.ID, EmpName: e.Title, EmpEmail: Lower(e.Email),
            DocId: d.ID, DocNumber: d.DocNumber, DocTitle: d.DocTitle, DocType: d.DocType.Value, Rev: d.Revision,
            Trainer: If(CountRows(cmbAssignDoc.SelectedItems) = 1 && !IsBlank(drpAssignTrainer.Selected), drpAssignTrainer.Selected, First(d.Trainers)),
            // Block duplicates: one current row per employee per document (CLAUDE.md Section 7 rule 3).
            Exists: !IsBlank(LookUp(fxAssignmentsCurrent, DocumentID = d.ID && Lower(EmployeeEmail) = Lower(e.Email), ID))
        })
    )
)"""
    create = """ClearCollect(
        colAssignResults,
        ForAll(
            Filter(colAssignPreview, !Exists) As p,
            IfError(
                Patch(JP_Assignments, Defaults(JP_Assignments), {
                    Title: p.DocNumber & " Rev " & p.Rev & " – " & p.EmpName,
                    Employee: {Id: p.EmpId, Value: p.EmpName},
                    EmployeeEmail: p.EmpEmail,
                    DocumentID: p.DocId,
                    DocType: {Value: p.DocType},
                    DocNumber: p.DocNumber,
                    DocTitle: p.DocTitle,
                    RevisionAssigned: p.Rev,
                    AssignmentReason: {Value: "New Assignment"},
                    IsCurrent: true,
                    AssignedBy: fxMePerson,
                    AssignedDate: Today(),
                    DueDate: dpAssignDue.SelectedDate,
                    Trainer: p.Trainer,
                    Status: {Value: "Assigned"}
                });
                {Ok: true},
                {Ok: false}
            )
        )
    )"""
    create_go = f"""Set(gblSaving, true);
{create};
Refresh(JP_Assignments);
Notify(CountRows(Filter(colAssignResults, Ok)) & " assignments created" & If(CountRows(Filter(colAssignResults, !Ok)) > 0, ", " & CountRows(Filter(colAssignResults, !Ok)) & " failed", "") & ".",
    If(CountRows(Filter(colAssignResults, !Ok)) = 0, NotificationType.Success, NotificationType.Warning));
Clear(colAssignPreview);
Set(gblSaving, false)"""
    prev_row = [
        glabel("lblAsgPrevName", 'ThisItem.EmpName & " – " & ThisItem.DocNumber & " Rev " & ThisItem.Rev', 16, 10,
               "Parent.TemplateWidth - 200", bold=True),
        glabel("lblAsgPrevTrainer", '"Trainer: " & Coalesce(ThisItem.Trainer.DisplayName, "none")', 16, 36,
               "Parent.TemplateWidth - 200", size=13, color="clrMuted"),
        C("lblAsgPrevState", "label", {**chip_props('If(ThisItem.Exists, "Already assigned", "Will be created")',
                                                    "Parent.TemplateWidth - 180", 18, 170),
                                       "Color": "If(ThisItem.Exists, clrGrey, clrGreen)",
                                       "Fill": "If(ThisItem.Exists, clrGreyBg, clrGreenBg)"}),
    ]
    screens.append(screen("scrAssign", "Assign", "assign", [
        note("lblAsgNoAccess", "Only managers and supervisors can assign documents.", visible="!fxIsManager", color="clrRed"),
        card("conAsgPick", [
            field("conAsgEmp", "Employees", cmb("cmbAssignEmp", "fxEligibleEmployees",
                                                default="Filter(fxEligibleEmployees, ID in ShowColumns(gblAssignEmpIds, ID))",
                                                placeholder="Search employees", label_text="Employees"), required=True),
            field("conAsgDoc", "Documents (active, with at least one trainer)",
                  cmb("cmbAssignDoc", "Filter(fxDocsActive, CountRows(Trainers) > 0)",
                      default="Filter(fxDocsActive, CountRows(Trainers) > 0 && ID in ShowColumns(gblAssignDocIds, ID))",
                      fields='["DocNumber", "DocTitle"]', placeholder="Search documents", label_text="Documents"), required=True),
            note("lblAsgNoTrainerDocs", '"Not shown because they have no trainer: " & Concat(Filter(fxDocsActive, CountRows(Trainers) = 0), DocNumber, ", ")',
                 visible="CountRows(Filter(fxDocsActive, CountRows(Trainers) = 0)) > 0", height=40),
            field("conAsgTrainer", "Trainer (when one document is selected; otherwise its first trainer)",
                  drp("drpAssignTrainer", "First(cmbAssignDoc.SelectedItems).Trainers", '""', label_text="Trainer", value="DisplayName"),
                  visible="CountRows(cmbAssignDoc.SelectedItems) = 1"),
            field("conAsgDue", "Due date (optional)", datepick("dpAssignDue")),
            row("conAsgButtons", [btn("btnAssignPreview", "Preview", preview,
                                      display="If(CountRows(cmbAssignEmp.SelectedItems) > 0 && CountRows(cmbAssignDoc.SelectedItems) > 0, DisplayMode.Edit, DisplayMode.Disabled)")]),
        ], visible="fxIsManager"),
        heading("lblAsgSummary", 'CountRows(Filter(colAssignPreview, !Exists)) & " will be created, " & CountRows(Filter(colAssignPreview, Exists)) & " already assigned (skipped)"',
                visible="fxIsManager && CountRows(colAssignPreview) > 0"),
        *gallery("galAssignPreview", "colAssignPreview", prev_row, tsize=64, visible="fxIsManager && CountRows(colAssignPreview) > 0",
                 min_h=160),
        row("conAsgCreate", [btn("btnAssignCreate", "Create assignments", create_go, width=200,
                                 display="If(gblSaving || CountRows(Filter(colAssignPreview, !Exists)) = 0, DisplayMode.Disabled, DisplayMode.Edit)")],
            visible="fxIsManager && CountRows(colAssignPreview) > 0"),
    ]))
    screens[-1].props["OnVisible"] = 'Set(gblNavKey, "assign"); Clear(colAssignPreview); Reset(cmbAssignEmp); Reset(cmbAssignDoc); Reset(dpAssignDue)'

    # ================================================================== scrPWIStatus
    st_items = """SortByColumns(Filter(fxAssignmentDisplayStatus, DocumentID = gblSelDoc.ID && EmpIsActive), "EmployeeEmail")"""
    st_row = [
        glabel("lblPwsName", "ThisItem.Employee.Value", 16, 10, "Parent.TemplateWidth - 330", bold=True),
        glabel("lblPwsRev", '"Rev " & ThisItem.RevisionAssigned & If(IsBlank(ThisItem.DueDate), "", " · Due " & Text(ThisItem.DueDate, DateTimeFormat.ShortDate))',
               16, 36, "Parent.TemplateWidth - 330", size=13, color="clrMuted"),
        C("lblPwsStatus", "label", chip_props("ThisItem.DisplayStatus", "Parent.TemplateWidth - 300", 22)),
        btn("btnPwsRemove", "Remove", "UpdateContext({locPwsRemove: ThisItem})", style="danger", width=110, height=36,
            visible="fxIsManager"),
    ]
    st_row[-1].props.update({"X": "Parent.TemplateWidth - 126", "Y": 18})
    pws_remove_patch = """Patch(JP_Assignments, LookUp(JP_Assignments, ID = locPwsRemove.ID),
        {Status: {Value: "Removed"}, IsCurrent: false, Comments: "Removed: " & Trim(txtPwsReason.Text)})"""
    screens.append(screen("scrPWIStatus", "PWI Status", "pwi", [
        note("lblPwsNoAccess", "This view is for managers and viewers.", visible="fxIsTechnician", color="clrRed"),
        card("conPwsHead", [
            heading("lblPwsDoc", 'gblSelDoc.DocNumber & " – " & gblSelDoc.DocTitle & " (current Rev " & gblSelDoc.Revision & ")"'),
            note("lblPwsCounts", """With({s: Filter(fxAssignmentDisplayStatus, DocumentID = gblSelDoc.ID && EmpIsActive)},
    CountRows(Filter(s, DisplayStatus = "Signed Off")) & " signed off · " & CountRows(Filter(s, DisplayStatus = "Re-Sign Required")) & " re-sign required · " &
    CountRows(Filter(s, DisplayStatus = "Overdue")) & " overdue · " & CountRows(Filter(s, DisplayStatus = "Pending")) & " pending")""",
                 color="clrText", height=28),
            row("conPwsButtons", [btn("btnPwsAssign", "Assign more employees",
                                      "Set(gblAssignDocIds, Table({ID: gblSelDoc.ID})); Set(gblAssignEmpIds, Blank()); Navigate(scrAssign, ScreenTransition.None)",
                                      width=230)], visible="fxIsManager"),
        ], visible="!fxIsTechnician"),
        *gallery("galPwiStatus", st_items, st_row, tsize=72, visible="!fxIsTechnician",
                 empty="Nobody is assigned to this PWI yet."),
        card("conPwsRemove", [
            heading("lblPwsRemoveHead", '"Remove " & locPwsRemove.Employee.Value & " from " & gblSelDoc.DocNumber & "?"'),
            field("conPwsReason", "Reason", txt("txtPwsReason", hint="Why is this assignment removed?"), required=True),
            row("conPwsRemoveButtons", [
                btn("btnPwsRemoveYes", "Remove", f"""If(IsBlank(Trim(txtPwsReason.Text)), Notify("Please enter a reason.", NotificationType.Warning),
{save(pws_remove_patch, "Assignment removed.", "Refresh(JP_Assignments); UpdateContext({locPwsRemove: Blank()}); Reset(txtPwsReason)")})""",
                    style="danger", display=SAVING),
                btn("btnPwsRemoveNo", "Cancel", "UpdateContext({locPwsRemove: Blank()})", style="secondary")]),
        ], visible="!IsBlank(locPwsRemove) && fxIsManager"),
    ]))

    # ================================================================== scrMyTraining
    my_items = """SortByColumns(
    Filter(
        fxMyAssignments,
        Switch(locMyTab, "pending", IsPending, "signed", IsQualified, true)
    ),
    "DueDate"
)"""
    my_row = [
        glabel("lblMyDoc", 'ThisItem.DocNumber & " – " & ThisItem.DocTitle', 16, 8, "Parent.TemplateWidth - 200", bold=True),
        glabel("lblMySub", '"Rev " & ThisItem.RevisionAssigned & If(IsBlank(ThisItem.DueDate), "", " · Due " & Text(ThisItem.DueDate, DateTimeFormat.ShortDate))',
               16, 34, "Parent.TemplateWidth - 200", size=13, color="clrMuted"),
        glabel("lblMyBadge", 'If(ThisItem.DocTypeText = "PWI", "New Revision – Please Re-Sign", "New Revision")', 16, 58, 260,
               size=13, color="clrAmber", bold=True, Visible="ThisItem.ShowNewRevisionBadge"),
        glabel("lblMyNotes", '"What changed: " & LookUp(fxDocsActive, ID = ThisItem.DocumentID, RevisionNotes)', 16, 82,
               "Parent.TemplateWidth - 32", size=13, Visible="ThisItem.ShowNewRevisionBadge"),
        C("lblMyStatus", "label", chip_props('If(fxIsTechnician && ThisItem.DisplayStatus = "In Training", "In Training – Waiting on Supervisor", ThisItem.DisplayStatus)',
                                             "Parent.TemplateWidth - 180", 10, 170)),
    ]
    tab = lambda key, text: btn(f"btnMyTab{key.title()}", text, f'UpdateContext({{locMyTab: "{key}"}})', style="secondary", width=130)
    tabs = [tab("pending", "Pending"), tab("signed", "Signed Off"), tab("all", "All")]
    for t, k in zip(tabs, ("pending", "signed", "all")):
        t.props["Fill"] = f'If(locMyTab = "{k}", clrPrimary, clrPanel)'
        t.props["Color"] = f'If(locMyTab = "{k}", Color.White, clrPrimary)'
        t.props["HoverColor"] = t.props["Color"]
        t.props["PressedColor"] = t.props["Color"]
    screens.append(screen("scrMyTraining", "My Training", "mytraining", [
        note("lblMyViewer", "You have read-only access, so there are no assignments to show.", visible="fxIsViewer"),
        row("conMyTabs", tabs, visible="!fxIsViewer"),
        note("lblMyCounts", 'CountRows(fxMyPending) & " pending · " & fxMyResignCount & " need re-sign · " & CountRows(fxMySignedOff) & " signed off on the current revision"',
             visible="!fxIsViewer", height=28),
        *gallery("galMyTraining", my_items, my_row, tsize=112, visible="!fxIsViewer",
                 onselect="Set(gblSelAssignment, ThisItem); Navigate(scrAssignmentDetail, ScreenTransition.None)",
                 empty="If(locMyTab = \"pending\", \"Nothing pending — you're all caught up.\", \"Nothing to show yet.\")"),
    ]))
    screens[-1].props["OnVisible"] = 'Set(gblNavKey, "mytraining"); If(IsBlank(locMyTab), UpdateContext({locMyTab: "pending"}))'

    # ================================================================== scrAssignmentDetail
    a = "gblSelAssignment"
    doc = f"LookUp(JP_Documents, ID = {a}.DocumentID)"
    is_own = f"Lower({a}.EmployeeEmail) = fxMeEmail"
    can_view = f"!IsBlank({a}) && (fxIsManager || {is_own})"
    rev_ok = f'({a}.RevisionAssigned = {doc}.Revision && {doc}.Status.Value = "Active" && {a}.IsCurrent)'
    pending = f'({a}.Status.Value = "Assigned" || {a}.Status.Value = "In Training")'
    pwi_can = f'{a}.DocType.Value = "PWI" && {pending} && {rev_ok} && ({is_own} || fxIsManager)'
    jqc_mgr = f'{a}.DocType.Value = "JQC" && fxIsManager && !({is_own}) && {rev_ok}'
    file_name = (f'{a}.DocNumber & "_Rev" & {a}.RevisionAssigned & "_" & {a}.Employee.Id & "_" & Text(Now(), "yyyymmdd_hhmmss") '
                 f'& "." & {{EXT}}')
    sign_meta = lambda att: (f'{{FileName: {file_name.replace("{EXT}", file_ext(att))}, AssignmentID: {a}.ID, '
                             f'DocType: {a}.DocType.Value, Revision: {a}.RevisionAssigned, EmployeeEmail: Lower({a}.EmployeeEmail), '
                             f'UploadedBy: fxMeEmail}}')
    refresh_sel = f"Refresh(JP_Assignments); Set({a}, LookUp(fxAssignmentDisplayStatus, ID = {a}.ID))"
    upload_log = f"""If(
    !({file_ok('attSignLog')}),
    Notify("Choose one PDF, DOCX, XLSX, JPG or PNG file (max 25 MB).", NotificationType.Warning),
    Set(gblSaving, true);
    {upload('attSignLog', 'Signoffs', '0', sign_meta('attSignLog'))};
    If(gblUpload.success = "true",
        // The flow only saves the file; the app sets its columns (SPEC.md A-38).
        IfError(
            Patch(JP_SignoffRecords, LookUp(JP_SignoffRecords, ID = gblUpload.itemid), {{
                AssignmentID: {a}.ID, DocType: {{Value: {a}.DocType.Value}}, Revision: {a}.RevisionAssigned,
                EmployeeEmail: Lower({a}.EmployeeEmail), UploadedBy: fxMePerson
            }}),
            Notify("The file was uploaded, but its details couldn't be saved: " & FirstError.Message, NotificationType.Error),
            UpdateContext({{locEvidenceId: gblUpload.itemid, locEvidenceFor: {a}.ID}}); Notify("Training log uploaded.", NotificationType.Success)
        ),
        Notify(gblUpload.message, NotificationType.Error));
    Set(gblSaving, false)
)"""
    signoff_patch = f"""Patch(JP_Assignments, LookUp(JP_Assignments, ID = {a}.ID), {{
        Status: {{Value: "Signed Off"}}, SignedOffBy: fxMePerson, SignedOffDate: Now(), SignoffFileID: locEvidenceId
    }})"""
    # Sign Off is blocked on an outdated revision (CLAUDE.md Section 7 rule 4): checked again at save time.
    pwi_sign = f"""If(
    !{rev_ok},
    Notify("This revision is no longer current. Open your new item from My Training.", NotificationType.Error),
    {save(signoff_patch, "Signed off.", refresh_sel + "; UpdateContext({locEvidenceId: 0})")}
)"""
    upload_jqc = upload_log.replace("attSignLog", "attSignJqc").replace("Training log uploaded.", "Signed JQC uploaded.")
    jqc_sign = f"""If(
    !{rev_ok},
    Notify("This revision is no longer current.", NotificationType.Error),
    !chkJqcVerified.Value,
    Notify("Tick the confirmation first.", NotificationType.Warning),
    {save(signoff_patch, "JQC signed off.", refresh_sel + "; UpdateContext({locEvidenceId: 0}); Reset(chkJqcVerified)")}
)"""
    put_training = f"""Patch(JP_Assignments, LookUp(JP_Assignments, ID = {a}.ID), {{
        Status: {{Value: "In Training"}},
        Trainer: If(IsBlank(drpJqcTrainer.Selected), {a}.Trainer, drpJqcTrainer.Selected)
    }})"""
    evidence_ready = f"locEvidenceId > 0 && locEvidenceFor = {a}.ID"
    screens.append(screen("scrAssignmentDetail", "Assignment", "mytraining", [
        note("lblAdNoAccess", "You can only view your own items.", visible=f"!({can_view})", color="clrRed"),
        card("conAdInfo", [
            heading("lblAdDoc", f'{a}.DocNumber & " – " & {a}.DocTitle'),
            note("lblAdMeta", f'{a}.Employee.Value & " · Rev " & {a}.RevisionAssigned & " (current: " & {doc}.Revision & ")" & If(IsBlank({a}.DueDate), "", " · Due " & Text({a}.DueDate, DateTimeFormat.ShortDate)) & " · Trainer: " & Coalesce({a}.Trainer.DisplayName, "none")',
                 color="clrText", height=48),
            label("lblAdStatus", f'If(fxIsTechnician && {a}.DisplayStatus = "In Training", "In Training – Waiting on Supervisor", {a}.DisplayStatus)',
                  size=14, bold=True, Height=36, FillPortions=0, Align="Align.Center", Width=320,
                  Color=f"LookUp(fxStatusStyle, Status = {a}.DisplayStatus, Fore)",
                  Fill=f"LookUp(fxStatusStyle, Status = {a}.DisplayStatus, Back)", **R(18)),
            note("lblAdBadge", f'If({a}.DocType.Value = "PWI", "New Revision – Please Re-Sign", "New Revision") & Char(10) & "What changed: " & {doc}.RevisionNotes',
                 visible=f"{a}.ShowNewRevisionBadge", color="clrAmber", height=56),
            note("lblAdOutdated", "This revision is no longer current.", visible=f"!{rev_ok} && {pending}", color="clrRed", height=28),
            row("conAdOpen", [btn("btnAdOpen", "Open document", f"Launch({doc}.'{{Link}}')", style="secondary", width=180)]),
        ], visible=can_view),
        # ---- PWI: upload training log, then Sign Off
        card("conAdPwi", [
            heading("lblAdPwiHead", "Sign off this PWI"),
            field("conAdLog", "Training log", attach("attSignLog"), required=True),
            row("conAdPwiButtons", [
                btn("btnAdUploadLog", "Upload Training Log", upload_log, display=SAVING, width=210),
                btn("btnAdSignOff", "Sign Off", pwi_sign, width=140,
                    display=f"If(gblSaving || !({evidence_ready}), DisplayMode.Disabled, DisplayMode.Edit)"),
            ], wrap=True, height="If(fxIsPhone, 104, 48)"),
            note("lblAdLogDone", "Training log uploaded. You can now sign off.", visible=evidence_ready, color="clrGreen", height=28),
        ], visible=f"{can_view} && {pwi_can}"),
        # ---- JQC (technician view)
        note("lblAdJqcTech", f'If({a}.Status.Value = "Assigned", "Needs Training. Your supervisor will put you into training.", "In Training – Waiting on Supervisor. A manager will sign off your JQC.")',
             visible=f'{can_view} && {a}.DocType.Value = "JQC" && {pending} && !({jqc_mgr})', color="clrText", height=48),
        # ---- JQC (manager): Put Into Training
        card("conAdJqcTrain", [
            heading("lblAdJqcTrainHead", "Put Into Training"),
            field("conAdJqcTrainer", "Trainer", drp("drpJqcTrainer", f"{doc}.Trainers", f"{a}.Trainer.DisplayName",
                                                    label_text="Trainer", value="DisplayName")),
            row("conAdJqcTrainButtons", [btn("btnAdPutTraining", "Put Into Training",
                                             save(put_training, "Employee put into training.", refresh_sel),
                                             display=SAVING, width=200)]),
        ], visible=f'{can_view} && {jqc_mgr} && {a}.Status.Value = "Assigned"'),
        # ---- JQC (manager): upload signed JQC and confirm
        card("conAdJqcSign", [
            heading("lblAdJqcSignHead", "Sign off this JQC"),
            field("conAdJqcFile", "Signed JQC", attach("attSignJqc"), required=True),
            row("conAdJqcUploadRow", [btn("btnAdUploadJqc", "Upload Signed JQC", upload_jqc, display=SAVING, width=200)]),
            chk("chkJqcVerified", "I verified this employee is qualified to perform this task."),
            row("conAdJqcSignRow", [btn("btnAdJqcSign", "Confirm qualified", jqc_sign, width=200,
                                        display=f"If(gblSaving || !({evidence_ready}) || !chkJqcVerified.Value, DisplayMode.Disabled, DisplayMode.Edit)")]),
        ], visible=f'{can_view} && {jqc_mgr} && {a}.Status.Value = "In Training"'),
        note("lblAdOwnJqc", "Another manager must sign off your own JQC.",
             visible=f'{can_view} && {a}.DocType.Value = "JQC" && fxIsManager && {is_own} && {pending}', height=28),
        note("lblAdSigned", f'"Signed off by " & {a}.SignedOffBy.DisplayName & " on " & Text({a}.SignedOffDate, DateTimeFormat.ShortDateTime)',
             visible=f'{can_view} && {a}.Status.Value = "Signed Off"', color="clrGreen", height=28),
    ]))
    screens[-1].props["OnVisible"] = ('Set(gblNavKey, "mytraining"); UpdateContext({locEvidenceId: 0, locEvidenceFor: 0}); '
                                      'Reset(attSignLog); Reset(attSignJqc); Reset(chkJqcVerified)')

    # ================================================================== scrSignoffReview
    rv_filter = ('(IsBlank(txtRvEmp.Text) || StartsWith(Employee.Value, txtRvEmp.Text)) && '
                 '(IsBlank(txtRvDoc.Text) || StartsWith(DocNumber, txtRvDoc.Text))')
    rv_items = f"""Switch(
    locRvTab,
    "recent",
        Filter(fxAssignmentDisplayStatus, StatusText = "Signed Off" && !IsBlank(SignedOffDate)
            && SignedOffDate >= Coalesce(dpRvFrom.SelectedDate, DateAdd(Today(), -30, TimeUnit.Days)) && {rv_filter}),
    "jqcneeds", Filter(fxAssignmentDisplayStatus, DocIsActive && EmpIsActive && DocTypeText = "JQC" && StatusText = "Assigned" && {rv_filter}),
    "jqctraining", Filter(fxAssignmentDisplayStatus, DocIsActive && EmpIsActive && DocTypeText = "JQC" && StatusText = "In Training" && {rv_filter}),
    "resign", Filter(fxAssignmentDisplayStatus, DocIsActive && EmpIsActive && DocTypeText = "PWI" && IsPending && IsRevisionChange && {rv_filter}),
    Filter(fxAssignmentDisplayStatus, DocIsActive && EmpIsActive && IsOverdue && {rv_filter})
)"""
    rv_row = [
        glabel("lblRvName", 'ThisItem.Employee.Value & " – " & ThisItem.DocNumber & " Rev " & ThisItem.RevisionAssigned', 16, 10,
               "Parent.TemplateWidth - 200", bold=True),
        glabel("lblRvSub", 'If(locRvTab = "recent", "Signed off " & Text(ThisItem.SignedOffDate, DateTimeFormat.ShortDate) & " by " & ThisItem.SignedOffBy.DisplayName, If(IsBlank(ThisItem.DueDate), "No due date", "Due " & Text(ThisItem.DueDate, DateTimeFormat.ShortDate)))',
               16, 36, "Parent.TemplateWidth - 200", size=13, color="clrMuted"),
        C("lblRvStatus", "label", chip_props("ThisItem.DisplayStatus", "Parent.TemplateWidth - 170", 22)),
    ]
    rv_tabs = []
    for k, t in (("recent", "Recently Signed Off"), ("jqcneeds", "JQCs Needing Training"), ("jqctraining", "JQCs In Training"),
                 ("resign", "PWI Re-Sign Required"), ("overdue", "Overdue")):
        b = btn(f"btnRvTab{k.title()}", t, f'UpdateContext({{locRvTab: "{k}"}})', style="secondary", width=200)
        b.props.update({"Fill": f'If(locRvTab = "{k}", clrPrimary, clrPanel)', "Color": f'If(locRvTab = "{k}", Color.White, clrPrimary)'})
        b.props["HoverColor"] = b.props["PressedColor"] = b.props["Color"]
        rv_tabs.append(b)
    rv_open = ('If(locRvTab = "recent", Launch(LookUp(JP_SignoffRecords, ID = ThisItem.SignoffFileID).\'{Link}\'), '
               'fxIsManager, Set(gblSelAssignment, LookUp(fxAssignmentDisplayStatus, ID = ThisItem.ID)); Navigate(scrAssignmentDetail, ScreenTransition.None))')
    screens.append(screen("scrSignoffReview", "Sign-off Review", "review", [
        note("lblRvNoAccess", "This view is for managers and viewers.", visible="fxIsTechnician", color="clrRed"),
        row("conRvTabs", rv_tabs, visible="!fxIsTechnician", wrap=True, height="If(fxIsPhone, 260, If(fxIsWide, 56, 112))"),
        row("conRvFilters", [txt("txtRvEmp", hint="Employee name", width=FW), txt("txtRvDoc", hint="Document number", width=FW),
                             datepick("dpRvFrom", "DateAdd(Today(), -30, TimeUnit.Days)", visible='locRvTab = "recent"', width=FW)],
            visible="!fxIsTechnician", wrap=True, height="If(fxIsPhone, 160, 56)"),
        note("lblRvHint", 'If(locRvTab = "recent", "Tap a row to open its sign-off file.", If(fxIsManager, "Tap a row to open it (Put Into Training and sign-off are on the assignment).", ""))',
             visible="!fxIsTechnician", height=28),
        *gallery("galSignoffReview", rv_items, rv_row, tsize=72, visible="!fxIsTechnician", onselect=rv_open,
                 empty="Nothing in this list."),
    ]))
    screens[-1].props["OnVisible"] = 'Set(gblNavKey, "review"); If(IsBlank(locRvTab), UpdateContext({locRvTab: "jqcneeds"}))'

    # ================================================================== scrMatrix
    mx_docs = """SortByColumns(
    Filter(
        fxDocsActive,
        drpMxType.Selected.Value = "All" || DocType.Value = drpMxType.Selected.Value,
        drpMxArea.Selected.Value = "All" || Area.Value = drpMxArea.Selected.Value
    ),
    "DocNumber"
)"""
    mx_emps = """SortByColumns(
    Filter(
        fxEligibleEmployees,
        drpMxDept.Selected.Value = "All" || Department.Value = drpMxDept.Selected.Value,
        drpMxShift.Selected.Value = "All" || Shift.Value = drpMxShift.Selected.Value,
        drpMxSup.Selected.Value = "All" || Supervisor.Value = drpMxSup.Selected.Value,
        !tglMxResign.Value || !IsBlank(LookUp(fxAssignmentDisplayStatus, Employee.Id = ID && DisplayStatus = "Re-Sign Required", ID))
    ),
    "Title"
)"""
    cell_status = ('Coalesce(LookUp(colMxStatus, EmpId = {emp} && DocumentID = {doc}, DisplayStatus), "Not Assigned")')
    COLW, NAMEW = 130, 190
    mx_page_docs = f"FirstN(LastN(colMxDocs, CountRows(colMxDocs) - locMxStart), locMxPage)"
    # Inner gallery cells read the outer row's employee ID from lblMxRowId (a control in the outer template).
    st = cell_status.format(emp="Value(lblMxRowId.Text)", doc="ThisItem.ID")
    mx_cell = C("lblMxCell", "label", chip_props(st, 4, 10, COLW - 8, 32))
    mx_cell.props.pop("OnSelect")
    mx_inner = C("galMxCells", "gallery.galleryHorizontal", {
        "Items": mx_page_docs, "TemplateSize": COLW, "TemplatePadding": 0, "ShowScrollbar": "false",
        "BorderThickness": 0, "X": NAMEW, "Y": 0, "Width": "Parent.TemplateWidth - " + str(NAMEW), "Height": 52,
        "AccessibleLabel": q("Status per document")}, [mx_cell])
    mx_rows = C("galMxRows", "gallery.galleryVertical", {
        "Items": "colMxEmps", "TemplateSize": 52, "TemplatePadding": 0, "ShowScrollbar": "true", "BorderThickness": 0,
        "FillPortions": 1, "LayoutMinHeight": 300, "Fill": "clrPanel", "Visible": "!fxIsPhone",
        "AccessibleLabel": q("Training matrix")}, [
        glabel("lblMxRowName", "ThisItem.Title", 12, 0, NAMEW - 16, 52, bold=True, VerticalAlign="VerticalAlign.Middle"),
        label("lblMxRowId", "ThisItem.ID", Visible="false", X=0, Y=0, Width=10, Height=10),
        mx_inner,
        C("rectMxRowLine", "rectangle", {"X": 0, "Y": 51, "Width": "Parent.TemplateWidth", "Height": 1, "Fill": "clrBorder"}),
    ])
    mx_header = C("galMxHeader", "gallery.galleryHorizontal", {
        "Items": mx_page_docs, "TemplateSize": COLW, "TemplatePadding": 0, "ShowScrollbar": "false", "BorderThickness": 0,
        "Height": 56, "FillPortions": 1, "AccessibleLabel": q("Documents")}, [
        label("lblMxHead", 'ThisItem.DocNumber & Char(10) & "Rev " & ThisItem.Revision', size=12, bold=True,
              X=4, Y=4, Width=COLW - 8, Height=48, Align="Align.Center")])
    mx_filter_row = row("conMxFilters", [
        drp("drpMxType", '["All", "JQC", "PWI"]', '"All"', label_text="Type"),
        drp("drpMxArea", 'Ungroup(Table({V: ["All"]}, {V: ShowColumns(Choices([@JP_Documents].Area), Value)}), "V")', '"All"', label_text="Area"),
        drp("drpMxDept", 'Ungroup(Table({V: ["All"]}, {V: ShowColumns(Choices([@JP_Employees].Department), Value)}), "V")', '"All"',
            label_text="Department"),
        drp("drpMxShift", 'Ungroup(Table({V: ["All"]}, {V: ShowColumns(Choices([@JP_Employees].Shift), Value)}), "V")', '"All"', label_text="Shift"),
        drp("drpMxSup", 'Ungroup(Table({V: ["All"]}, {V: ForAll(fxManagers, {Value: Title})}), "V")', '"All"', label_text="Supervisor"),
        toggle("tglMxResign", "false", "Re-Sign Required only"),
        label("lblMxResign", q("Re-Sign Required only"), size=13, color="clrMuted", Width=170, Height=44, FillPortions=0),
    ], wrap=True, height="If(fxIsPhone, 420, If(fxIsWide, 56, 112))")
    for c in mx_filter_row.children:
        if c.kind == "dropdown":
            c.props["Width"] = "If(fxIsPhone, Parent.Width - 32, 160)"   # set after construction: same for all six
    # phone: by employee or by document
    ph_items = """If(
    locMxPhoneMode = "emp",
    AddColumns(colMxDocs As d, Name, d.DocNumber & " – " & d.DocTitle,
        Stat, Coalesce(LookUp(colMxStatus, EmpId = drpMxPhoneEmp.Selected.ID && DocumentID = d.ID, DisplayStatus), "Not Assigned")),
    AddColumns(colMxEmps As e, Name, e.Title,
        Stat, Coalesce(LookUp(colMxStatus, EmpId = e.ID && DocumentID = drpMxPhoneDoc.Selected.ID, DisplayStatus), "Not Assigned"))
)"""
    ph_row = [glabel("lblMxPhName", "ThisItem.Name", 16, 14, "Parent.TemplateWidth - 200", bold=True),
              C("lblMxPhStatus", "label", chip_props("ThisItem.Stat", "Parent.TemplateWidth - 170", 14))]
    mx_on_visible = f"""Set(gblNavKey, "matrix");
If(IsBlank(locMxPhoneMode), UpdateContext({{locMxPhoneMode: "emp"}}));
UpdateContext({{locMxStart: 0}});
// Snapshot of the current statuses (in memory; based on the first 2,000 current rows, see Admin-Guide.md).
ClearCollect(colMxStatus, ShowColumns(AddColumns(Filter(fxAssignmentDisplayStatus, EmpIsActive && DocIsActive), EmpId, Employee.Id), EmpId, DocumentID, DisplayStatus))"""
    mx_recalc = f"ClearCollect(colMxDocs, {mx_docs}); ClearCollect(colMxEmps, {mx_emps}); UpdateContext({{locMxStart: 0}})"
    screens.append(screen("scrMatrix", "Training Matrix", "matrix", [
        mx_filter_row,
        row("conMxPager", [
            btn("btnMxApply", "Apply filters", mx_recalc, width=150),
            btn("btnMxPrev", "◀ Previous", f"UpdateContext({{locMxStart: Max(0, locMxStart - locMxPage)}})", style="secondary",
                width=130, display="If(locMxStart > 0, DisplayMode.Edit, DisplayMode.Disabled)", visible="!fxIsPhone"),
            btn("btnMxNext", "Next ▶", f"UpdateContext({{locMxStart: locMxStart + locMxPage}})", style="secondary", width=120,
                display="If(locMxStart + locMxPage < CountRows(colMxDocs), DisplayMode.Edit, DisplayMode.Disabled)",
                visible="!fxIsPhone"),
            label("lblMxPage", '"Documents " & Min(locMxStart + 1, CountRows(colMxDocs)) & "–" & Min(locMxStart + locMxPage, CountRows(colMxDocs)) & " of " & CountRows(colMxDocs) & " · " & CountRows(colMxEmps) & " employees"',
                  size=13, color="clrMuted", Width=300, Height=44, FillPortions=0),
        ], height="If(fxIsPhone, 104, 56)", wrap=True),
        hbox("conMxHeadRow", [label("lblMxCorner", q("Employee"), size=13, bold=True, color="clrMuted", Width=NAMEW, Height=56,
                                    FillPortions=0, PaddingLeft=12, VerticalAlign="VerticalAlign.Middle"), mx_header],
             Height=56, FillPortions=0, Visible="!fxIsPhone", Fill="clrPanel"),
        mx_rows,
        note("lblMxEmpty", "No employees or documents match these filters.",
             visible="CountRows(colMxEmps) = 0 || CountRows(colMxDocs) = 0", height=28),
        # phone layout
        row("conMxPhoneMode", [
            btn("btnMxByEmp", "By employee", 'UpdateContext({locMxPhoneMode: "emp"})', style="secondary", width=150),
            btn("btnMxByDoc", "By document", 'UpdateContext({locMxPhoneMode: "doc"})', style="secondary", width=150),
        ], visible="fxIsPhone"),
        drp("drpMxPhoneEmp", "colMxEmps", "First(colMxEmps).Title", visible='fxIsPhone && locMxPhoneMode = "emp"', label_text="Employee", value="Title"),
        drp("drpMxPhoneDoc", "colMxDocs", "First(colMxDocs).DocNumber", visible='fxIsPhone && locMxPhoneMode = "doc"', label_text="Document", value="DocNumber"),
        *gallery("galMxPhone", ph_items, ph_row, tsize=56, visible="fxIsPhone", empty="Nothing to show."),
    ]))
    scr = screens[-1]
    scr.props["OnVisible"] = mx_on_visible + ";\n" + mx_recalc
    # page size depends on the available width
    scr.props["OnVisible"] += f";\nUpdateContext({{locMxPage: RoundDown(Max(1, (App.Width - If(fxIsPhone, 0, 220) - 32 - {NAMEW}) / {COLW}), 0)}})"

    # ================================================================== scrCrossTraining
    cov_items = """SortByColumns(
    AddColumns(
        fxTaskCoverage As t,
        Below, t.Qualified < t.Target,
        PendingAfterRevision, CountRows(Filter(fxAssignmentDisplayStatus, DocumentID = t.ID && EmpIsActive && IsRevisionChange && !IsQualified))
    ),
    "Below", SortOrder.Descending, "Qualified", SortOrder.Ascending
)"""
    maxq = "Max(fxMinQualified, Max(fxTaskCoverage, Qualified))"
    cov_row = [
        glabel("lblXtTask", 'ThisItem.DocNumber & " – " & ThisItem.DocTitle', 16, 6, "Parent.TemplateWidth - 32", bold=True),
        C("rectXtBarBg", "rectangle", {"X": 16, "Y": 36, "Width": "Parent.TemplateWidth - 220", "Height": 20, "Fill": "clrGreyBg",
                                       "OnSelect": "Select(Parent)"}),
        C("rectXtBar", "rectangle", {"X": 16, "Y": 36, "Width": f"(Parent.TemplateWidth - 220) * ThisItem.Qualified / {maxq}",
                                     "Height": 20, "Fill": "If(ThisItem.Below, clrRed, clrGreen)", "OnSelect": "Select(Parent)"}),
        C("rectXtTarget", "rectangle", {"X": f"16 + (Parent.TemplateWidth - 220) * ThisItem.Target / {maxq}", "Y": 30, "Width": 2,
                                        "Height": 32, "Fill": "clrText", "OnSelect": "Select(Parent)"}),
        glabel("lblXtCount", 'ThisItem.Qualified & " / " & ThisItem.Target & If(ThisItem.Below, "  Below target", "")',
               "Parent.TemplateWidth - 196", 34, 180, size=13, color="If(ThisItem.Below, clrRed, clrGreen)", bold=True),
        glabel("lblXtPending", 'ThisItem.PendingAfterRevision & " pending after a revision"', 16, 60, "Parent.TemplateWidth - 32",
               size=13, color="clrMuted"),
    ]
    xt_tap = 'If(fxIsManager && ThisItem.Below, Set(gblAssignDocIds, Table({ID: ThisItem.ID})); Set(gblAssignEmpIds, Blank()); Navigate(scrAssign, ScreenTransition.None))'
    spof_items = """AddColumns(
    Filter(fxTaskCoverage, Qualified = 1) As t,
    Person, LookUp(fxAssignmentDisplayStatus, DocumentID = t.ID && IsQualified, Employee.Value)
)"""
    spof_row = [glabel("lblSpofTask", 'ThisItem.DocNumber & " – " & ThisItem.DocTitle', 16, 10, "Parent.TemplateWidth - 32", bold=True),
                glabel("lblSpofWho", '"Only qualified: " & ThisItem.Person', 16, 36, "Parent.TemplateWidth - 32", size=13, color="clrRed")]
    shift_cell = C("lblShiftCell", "label", {
        "Text": 'ThisItem.N', "X": 4, "Y": 6, "Width": 92, "Height": 40, "Align": "Align.Center", "Size": 14,
        "FontWeight": "FontWeight.Semibold", "Color": "If(ThisItem.N = 0, clrRed, clrText)",
        "Fill": "If(ThisItem.N = 0, clrRedBg, clrGreyBg)", **R(6)})
    shift_items = """AddColumns(
    fxShifts As s,
    N, CountRows(Filter(fxAssignmentDisplayStatus, DocumentID = Value(lblShiftDocId.Text) && IsQualified &&
        LookUp(fxEmployeesActive, ID = Employee.Id, Shift.Value) = s.Value))
)"""
    shift_row = [
        glabel("lblShiftTask", "ThisItem.DocNumber", 12, 0, 170, 52, bold=True, VerticalAlign="VerticalAlign.Middle"),
        label("lblShiftDocId", "ThisItem.ID", Visible="false", X=0, Y=0, Width=10, Height=10),
        C("galShiftCells", "gallery.galleryHorizontal", {"Items": shift_items, "TemplateSize": 100, "TemplatePadding": 0,
                                                          "ShowScrollbar": "false", "BorderThickness": 0, "X": 180, "Y": 0,
                                                          "Width": "Parent.TemplateWidth - 180", "Height": 52,
                                                          "AccessibleLabel": q("Qualified per shift")}, [shift_cell]),
    ]
    shift_head = C("galShiftHead", "gallery.galleryHorizontal", {"Items": "fxShifts", "TemplateSize": 100, "TemplatePadding": 0,
                                                                  "ShowScrollbar": "false", "BorderThickness": 0, "Height": 40,
                                                                  "FillPortions": 1, "AccessibleLabel": q("Shifts")},
                   [label("lblShiftHead", "ThisItem.Value", size=13, bold=True, X=4, Y=4, Width=92, Height=32, Align="Align.Center")])
    breadth_items = """SortByColumns(
    AddColumns(fxEligibleEmployees As e, Quals, CountRows(Filter(fxAssignmentDisplayStatus, Employee.Id = e.ID && IsQualified))),
    "Quals", SortOrder.Ascending, "Title", SortOrder.Ascending
)"""
    breadth_row = [glabel("lblBrName", 'ThisItem.Title & " · " & ThisItem.Shift.Value', 16, 14, "Parent.TemplateWidth - 140", bold=True),
                   glabel("lblBrCount", 'ThisItem.Quals & If(ThisItem.Quals = 1, " qualification", " qualifications")',
                          "Parent.TemplateWidth - 180", 14, 164, size=13, Align="Align.Right")]
    xt_tabs = []
    for k, t in (("coverage", "Coverage by task"), ("spof", "Single points of failure"), ("shift", "Coverage by shift"),
                 ("breadth", "Employee breadth")):
        b = btn(f"btnXtTab{k.title()}", t, f'UpdateContext({{locXtTab: "{k}"}})', style="secondary", width=210)
        b.props.update({"Fill": f'If(locXtTab = "{k}", clrPrimary, clrPanel)', "Color": f'If(locXtTab = "{k}", Color.White, clrPrimary)'})
        b.props["HoverColor"] = b.props["PressedColor"] = b.props["Color"]
        xt_tabs.append(b)
    screens.append(screen("scrCrossTraining", "Cross-Training", "cross", [
        row("conXtTabs", xt_tabs, wrap=True, height="If(fxIsPhone, 208, If(fxIsWide, 56, 112))"),
        note("lblXtSummary", 'CountRows(fxCoverageGaps) & " tasks below the target of " & fxMinQualified & " qualified · " & CountRows(Filter(fxTaskCoverage, Qualified = 1)) & " single points of failure"',
             color="clrText", height=28),
        note("lblXtHint", "Tap a red task to assign it.", visible='fxIsManager && locXtTab = "coverage"', height=28),
        *gallery("galXtCoverage", cov_items, cov_row, tsize=88, onselect=xt_tap, visible='locXtTab = "coverage"',
                 empty="No active tasks yet."),
        *gallery("galXtSpof", spof_items, spof_row, tsize=72, visible='locXtTab = "spof"', empty="No single points of failure."),
        hbox("conShiftHeadRow", [label("lblShiftCorner", q("Task"), size=13, bold=True, color="clrMuted", Width=180, Height=40,
                                       FillPortions=0, PaddingLeft=12, VerticalAlign="VerticalAlign.Middle"), shift_head],
             Height=40, FillPortions=0, Visible='locXtTab = "shift"', Fill="clrPanel"),
        *gallery("galXtShift", "fxDocsActive", shift_row, tsize=52, visible='locXtTab = "shift"', empty="No active tasks yet."),
        *gallery("galXtBreadth", breadth_items, breadth_row, tsize=56, visible='locXtTab = "breadth"', empty="No employees yet."),
    ]))
    screens[-1].props["OnVisible"] = 'Set(gblNavKey, "cross"); If(IsBlank(locXtTab), UpdateContext({locXtTab: "coverage"}))'

    # Order screens as listed in ALL_SCREENS
    order = [s[0] for s in B.ALL_SCREENS]
    screens.sort(key=lambda s: order.index(s.name))
    return screens
