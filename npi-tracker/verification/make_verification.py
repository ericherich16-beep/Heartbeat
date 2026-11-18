from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.utils import get_column_letter
import sys
OUT=sys.argv[1]
F="Arial"
H=Font(name=F,bold=True,color="FFFFFF",size=10); HF=PatternFill("solid",fgColor="0A5CB2")
B=Font(name=F,size=10); BB=Font(name=F,size=10,bold=True); T=Font(name=F,size=14,bold=True)
IN=PatternFill("solid",fgColor="FFF2CC")  # user-fill cells
SEC=PatternFill("solid",fgColor="E4EAF2")
thin=Side(style="thin",color="C9D2DE"); BD=Border(left=thin,right=thin,top=thin,bottom=thin)
WR=Alignment(wrap_text=True,vertical="top")
wb=Workbook()

# ---------------- test data
R=[]  # (id, release, req, area, check, pre, steps, expected)
def t(rel, req, area, check, pre, steps, exp): R.append([rel,req,area,check,pre,steps,exp])
# 0 smoke per release
for rel in ["1.2.0.3","1.3.0.0","1.4.0.0","1.5.0.0","1.6.0.0"]:
    t(rel,"Import","Import & open",f"Solution {rel} imports and the app opens",
      "Previous release working; export taken as backup; SharePoint steps for this release done (Setup sheet)",
      "1. Solutions > Import > choose the zip > Update (keep customizations unless told otherwise).\n2. Allow SharePoint connection if asked.\n3. Solutions > NPI Tracker app > Play.",
      "Import completes with no error. App opens to the Overview without a blank screen or error banner.")
    t(rel,"Import","Import & open",f"No app checker errors in {rel}","App opens","Edit the app in Studio > App checker (stethoscope icon) > Formulas.",
      "Zero formula errors. Record any control + message in Notes.")
# 1.2.0.3
A="1.2.0.3"
t(A,"R14","Roles","Role badge recognises the QE","Signed in as the project's QE (U-number sign-in, mail address on QE column)",
  "Open the project. Look at the badge in the blue header.","Badge reads 'You: QE' (green).")
t(A,"R14","Roles","QM recognised","Signed in as the person in NPI Role Defaults with Role = QM, who is not the project QE",
  "Open any project.","Badge reads 'You: QM'.")
t(A,"R14","Roles","Team member gets no QE controls","Signed in as someone who is neither QE nor QM",
  "Open a project, select a row.","Badge 'You: Team member'. No Reassign / Change date / Mark N/A buttons. Done rows show 'Only the project QE (...) or the QM can review' with your email.")
t(A,"R7","Progress","Gate % shown as whole numbers","Project with 3 Gate 1 rows, 1 Reviewed",
  "Look at Gate 1 in the gate strip and on the Overview row.","Shows 33% (not 0.33% or 0%).")
t(A,"R12","Status","Submit for review moves to Done","QE; row in Draft with a linked file (1.6+) or any file state (1.2-1.5)",
  "Select row > Submit for review.","Pill shows 'Ready for review'; list status updates; success message.")
t(A,"R12","Status","Save draft with a note","Row Not started",
  "Type a note > Save draft.","Status Draft. Activity shows 'Not started -> Draft' with the note as 'Note:'.")
t(A,"R12","Status","Send back returns to Draft","QE; row Done, not Independent Review",
  "Select row > Send back (add a note).","Status Draft; Activity entry 'Done -> Draft' with note.")
t(A,"R14","Review","Self-review allowed on a normal row","QE is the assignee/submitter of a row with IndependentReview = No; row Done",
  "Select row.","Primary button reads 'Mark reviewed' and works; ReviewedBy = you, ReviewedDate set.")
t(A,"R14","Review","Independent Review blocks the submitter","QE submitted (Draft -> Done) a row with IndependentReview = Yes",
  "Select row.","Button reads 'Waiting for review' (disabled). Hint: 'Independent review: you can't review an item you are assigned to, uploaded or submitted...'")
t(A,"R14","Review","Independent Review blocks the assignee","Row IndependentReview = Yes, Assignee = you, submitted by someone else",
  "Select row.","'Waiting for review' disabled.")
t(A,"R14","Review","Independent Review allows another QE/QM","Row IndependentReview = Yes; reviewer is QM, not assignee/uploader/submitter",
  "Sign in as QM, select row > Mark reviewed.","Status Reviewed; ReviewedBy = QM.")
t(A,"R12","Status","Reopen a Reviewed row","QE; row Reviewed","Select row > Reopen.","Status Done (Ready for review).")
t(A,"R9","Panel edits","Reassign from the panel","QE; any unlocked row",
  "Reassign > type 2+ letters > pick a person > Save assignee.","Assigned to shows the new person; Assignee column updated; Activity 'Reassign' 'old -> new'.")
t(A,"R9","Panel edits","Change due date with shortcut","QE",
  "Change date > +2 weeks > check the 'New due date' line > Save due date.","Due shows date 14 days out; DueDate column updated; Activity 'Due date' entry.")
t(A,"R9","Panel edits","Invalid due date is refused","QE","Change date > type 'abc'.","Red 'That isn't a date' text; Save disabled.")
t(A,"R13","N/A","Mark N/A needs a reason and an 'If required' row","QE; ReqLevel = If required, status Not started or Draft",
  "Mark N/A > leave reason empty, then type a reason > Set N/A.","Set N/A disabled until reason typed. Status N/A; NAReason saved; Activity 'N/A' with reason. Link absent on Required rows.")
t(A,"R13","N/A","Restore an N/A row","QE; row N/A","Select row > Restore.","Status Not started; NAReason cleared.")
t(A,"R8","Details","View details grid is readable","Any row","Select row > View details.","Two-column grid of labelled fields (Status ... Requirement ID). Close returns to the panel. Open file button only when a file is linked.")
t(A,"R8","Details","Activity list shows the row's history","Row with several actions","Select row > Activity.","Entries newest first with date, person, action, detail and note. No 'Detail isn't recognized' error.")
t(A,"R8","Documents","Document filters","Project with mixed statuses",
  "Click All / Open / Needed for current gate; click Gate 2 in the strip.","All = every row of the selected gate; Open = unfinished rows across all gates (with 'Gate N ·'); Needed = unfinished rows of the selected gate; remaining count matches.")
# 1.3
A="1.3.0.0"
t(A,"R5","Overview","Project table columns","Several open projects",
  "Open the app.","Columns: Project, Customer, Part/Rev, QE, Progress (Gate N · % and '% overall'), Next due, Overdue, (Open Qs from 1.4).")
t(A,"R7","Overview","Overall % is correct","Project with 16 rows, 4 Reviewed, 2 N/A","Check the '% overall' line.","Shows 38% ((4+2)/16).")
t(A,"R5","Overview","Overdue count and next due","Project with one open row due yesterday and one due next week",
  "Check the row.","Overdue = 1 in red; Next due = yesterday's date (earliest open due date).")
t(A,"R6","Filters","My tasks lists only your open rows",
  "Rows assigned to you in 2 open projects; app freshly opened (no project visited yet)","Click My tasks.",
  "Only your unfinished rows in open projects, soonest due first. List is populated straight after opening the app.")
t(A,"R6","Filters","Overdue lists past-due rows for everyone","Overdue rows assigned to different people","Click Overdue.","Only open rows with due date before today, any assignee; dates in red with 'Overdue'.")
t(A,"R6","Filters","Task opens the project on that row","My tasks has a Gate 2 row","Click the task.","Project opens with that row selected, Gate 2 shown, filter 'All'.")
t(A,"R6","Filters","Search works in every view","","Type part of a project ID in Open, then in My tasks.","Lists filter to matches in both views.")
t(A,"R6","Filters","Closed and All filters","At least one closed project","Click Closed, then All.","Closed shows only closed projects (progress 'Closed'); All shows both.")
# 1.4
A="1.4.0.0"
t(A,"R15","Open questions","Add a question","List NPI Open Questions created; ActionType choices added",
  "Project > Open questions > New question > text, Gate 1, owner, due date > Add question.","Question appears (Gate 1, owner, due, Open). Button shows 'Open questions (1)' in red. Item exists in SharePoint with ProjectID, Gate, Owner, QStatus Open.")
t(A,"R15","Open questions","Gate strip and overview counts","One open Gate 1 question","Look at gate strip; go back to Overview.","Gate 1 shows '· 1 open question'; Overview Open Qs = 1 in red.")
t(A,"R15","Open questions","Move gate needs a reason","Open question at Gate 1",
  "Select it > choose Gate 2 > leave reason empty, then add reason > Move question.","Move disabled until a reason is typed and a different gate chosen. Gate becomes 2; GateMoveReason 'Gate 1 -> 2: <reason>'; Activity 'Question moved'.")
t(A,"R15","Open questions","Close with resolution","Open question","Type resolution > Close question.","Status Closed; Resolution saved; counts drop; Activity 'Question closed'.")
t(A,"R15","Open questions","Reopen","Closed question","All filter > select > Reopen question.","Status Open again; counts go back up.")
t(A,"R15","Open questions","Missing ActionType choice is not fatal","(Optional) temporarily without the question choices","Add a question.","Question still saves; yellow warning about the Activity Log entry.")
# 1.5
A="1.5.0.0"
t(A,"R16","Sign-off","Blocked message lists the reasons","Gate 1 with unfinished rows and one open question",
  "Look under Sign Gate 1.","Button disabled; text 'Gate 1 blocked: N requirements are not Reviewed or N/A; 1 open question at this gate or earlier.'")
t(A,"R16","Sign-off","Open question at an earlier gate blocks later gate","Gates 1 signed, Gate 2 rows done, open question tagged Gate 1","Look at Sign Gate 2.","Blocked with the open-question reason.")
t(A,"R16","Sign-off","Sign Gate 1 (two-step)","All Gate 1 rows Reviewed/N/A, no open Gate 1 questions, QE signed in",
  "Sign Gate 1 > read the confirm text > Confirm.","Gate1SignedBy = you, Gate1SignedDate = now, CurrentGate = 2. Strip shows 'Signed <date> · <name>'. Activity 'Gate signed'. Current gate moves to 2.")
t(A,"R16","Sign-off","Cancel the confirm","Gate ready","Sign Gate N > Cancel.","Nothing is written; button back to 'Sign Gate N'.")
t(A,"R18","Sign-off","Gates in order","Gate 1 not signed but Gate 2 rows all done","Look at the button.","Button only ever offers the lowest unsigned gate (Gate 1).")
t(A,"R16","Sign-off","Non-QE cannot sign","Team member; gate otherwise ready","Look at Sign Gate.","Disabled; text 'ready. Only the project QE or the QM can sign it.'")
t(A,"R16","Sign-off","QM can sign as backup","QM who is not the project QE; gate ready","Sign the gate.","Succeeds; SignedBy = QM.")
t(A,"R16","Lock","Signed gate rows are locked","Gate 1 signed","Select a Gate 1 row.","Submit/Save draft/Reopen disabled; Reassign, Change date, Mark N/A hidden; hint 'Gate 1 is signed, so this item is locked.'")
t(A,"R16","Sign-off","Gate document required","Gate 4 rows done except the IsGateDoc row has no file",
  "Look at Sign Gate 4.","Blocked: 'the signed gate document is not uploaded'.")
t(A,"R19","Sign-off","Gate 4 closes the project","Gate 4 ready (file on the gate document row)","Sign Gate 4 > Confirm.",
  "ProjectStatus Closed, CloseDate today, RetentionUntil = today + 30 years. Hint shows closed and retention dates. Overview shows the project under Closed.")
t(A,"R19","Sign-off","Missing 'Gate signed' choice is not fatal","(Optional) before renaming Choice 8","Sign a test gate.","Gate still signed; yellow warning about the Activity Log entry.")
# upload test
A="Upload test"
t(A,"R10","Upload test","Test app opens (file picker type confirmed)","EricP_NPIUploadTest imported; NPIUploadFile turned on","Open NPI Upload Test.","App opens and shows the 'Choose a PDF' picker. (Confirmed in tenant 2026-11-18 via 1.6.0.0.)")
t(A,"R10","Upload test","Flow run from the test app","Test app opens","Paste a ProjectFolderUrl, choose a small PDF, Run upload.","success: true, a fileurl, stamped true/false. File present in the folder. A run appears in NPIUploadFile run history.")
# 1.6
A="1.6.0.0"
t(A,"R10","Upload","Flow is bound to the app","1.6.0.0 imported; flow on","Studio > Power Automate pane: NPIUploadFile listed without warning. (If not: remove and re-add.)","Flow listed; Upload produces a run in run history.")
t(A,"R10","Upload","Upload a PDF to a row","Row Not started, no file","Choose a PDF > Upload.",
  "Success message. 'Current file: <name>' link opens the PDF. Row: FileLink, FileName, FileItemId, UploadedBy = you, UploadedDate set. Status Draft. Activity 'Upload'.")
t(A,"R10","Upload","Library columns stamped with the real uploader","NPIProjectFiles columns added","Open the uploaded file's properties in the library.",
  "ProjectID, RequirementID, Gate, FormNumber, FormSection, UploadedBy = you (not the flow owner), UploadedDate filled.")
t(A,"R10","Upload","Only PDFs accepted","","Choose a .docx.","Red 'Only PDF files can be uploaded.'; Upload disabled.")
t(A,"R11","Replace","Replace saves a new version","Row has a linked file; library versioning on","Choose another PDF > Replace.",
  "Same file name kept; library Version history shows a new version; Activity 'Replace'.")
t(A,"U4","Replace","New file on a Reviewed row resets to Done","Row Reviewed with a file","Replace the file.","Status Done (Ready for review); Activity detail '; Reviewed -> Done'.")
t(A,"Naming","Upload","Duplicate name gets the requirement ID prefix","Row A already has 'report.pdf'","Upload 'report.pdf' on row B.","Row B file saved as '<RowB ID>_report.pdf'; row A's file untouched.")
t(A,"U5","Remove","Remove needs a reason and moves to _Removed","Row with a file, status Done","Remove file > reason > Remove file.",
  "File now in <project folder>/_Removed; row file fields cleared; status Draft; Activity 'Remove' with reason.")
t(A,"U4","Lock","Upload closed after gate signed","Gate signed","Select a row of that gate.","Picker and Upload/Replace disabled; Remove link hidden; label says upload is closed / signed record.")
t(A,"R12","Status","Submit needs a linked PDF","Row Draft, no file","Look at Submit for review.","Disabled; hint 'PDF required before submitting.' After upload: enabled, hint changes.")
t(A,"R10","Upload","Failure shows the real error","(Optional) turn the flow off","Try Upload.","Red message 'The NPIUploadFile flow call failed: <real error>' (source build after 2026-11-18).")
# end-to-end
A="End-to-end"
t(A,"R1","Create","Create a New Part project","","New Project > fill fields > Create.","NPI-#### created with 16 rows, folder and templates; appears at top of Overview at 0%.")
t(A,"R2","Create","Duplicate Part + Rev rejected","Existing project for part/rev","Create the same part and revision.","Error message names the existing project; nothing created.")
t(A,"R4","Create","Revision links to previous","","Create a Revision with PreviousProjectId.","New project linked to the previous one.")
t(A,"R3","Create","Default assignees by role","Role on all Gate Requirements rows; Role Defaults filled","Create a project; check rows.","Every row has an Assignee matching its Role default.")
t(A,"R21","Config","Config change applies to new projects only","Edit one Gate Requirements row (with ChangeReason/ApprovedBy)","Create a new project; check an old one.","New project reflects the change; old project's rows unchanged.")
t(A,"R20","Config","Config edits are controlled","Increment 6 settings applied","As a non-QM try to edit Gate Requirements; as QM edit without ChangeReason.","Non-QM cannot edit; QM edit blocked until ChangeReason and ApprovedBy filled; version history records the change.")
t(A,"All","Full run","Gate 1 to Gate 4 on a test project","1.6.0.0 working","Upload, submit, review (second person for Independent Review rows), add/close a question, sign each gate.",
  "All four gates signed; project Closed with retention; Activity Log shows every step; signed gate rows locked.")

# ---------------- Instructions
ws=wb.active; ws.title="Instructions"
ws["A1"]="NPI Tracker: verification workbook"; ws["A1"].font=T
lines=[
("Purpose","Check every feature built in releases 1.2.0.3 to 1.6.0.0 in the tenant, record the result, and see coverage of spec requirements R1 to R22."),
("Order","1. Do the SharePoint steps on the Setup sheet for the release.  2. Import the release.  3. Run its rows on Test Cases (filter column B).  4. Record results.  5. Summary and Spec Coverage update themselves."),
("Cells you fill in","Yellow cells only: Setup > Done / Notes; Test Cases > Result, Tested by, Date, Notes / evidence, Defect ref; Risks > Outcome / Notes. Everything else is reference text or formulas."),
("Result values","Pass = success condition met exactly.  Fail = not met (describe what happened in Notes).  Blocked = could not run (missing setup, earlier failure).  N/A = not applicable to this tenant.  Blank = not run yet."),
("Evidence","For Fail, note the control name and exact message, or the first red action in the flow run history. Screenshots: put the file name in Notes."),
("Rule","Open the app after every import before testing features. A release that will not open: stop, go back to the previous release, record the first error."),
("Source","Test steps and success conditions come from the release notes in npi-tracker/history/<version>/NOTES.md and spec v3; Spec IDs from NPI_Tracker_Progress_vs_Spec_Summary.md."),
]
r=3
for k,v in lines:
    ws.cell(r,1,k).font=BB; c=ws.cell(r,2,v); c.font=B; c.alignment=WR; r+=1
r+=1; ws.cell(r,1,"Example of a completed Test Cases row (format only, not a real result)").font=BB; r+=1
hdr=["Result","Tested by","Date","Notes / evidence","Defect ref"]
ex=["Fail","E. Hernandez","11/18/2026","Upload: 'flow could not be reached', no run. Re-added flow in Studio, then Pass.","D-01"]
for i,(h,v) in enumerate(zip(hdr,ex)):
    a=ws.cell(r,2+i,h); a.font=H; a.fill=HF; b=ws.cell(r+1,2+i,v); b.font=B; b.fill=IN; b.border=BD; b.alignment=WR
ws.column_dimensions["A"].width=22; ws.column_dimensions["B"].width=110
for col in "CDEF": ws.column_dimensions[col].width=22

# ---------------- Setup
ss=wb.create_sheet("Setup")
sh=["ID","Before release","Where","Item","How to check","Success condition","Done (Y/N)","Notes"]
setup=[
("1.4.0.0","SharePoint site","Create list 'NPI Open Questions'","Site contents","List exists with that exact name."),
("1.4.0.0","NPI Open Questions","Columns ProjectID (text, required), Gate (number 1-4, required), Owner (person), DueDate (date), QStatus (choice Open/Closed, default Open), Resolution (multi-line plain), GateMoveReason (multi-line plain)","List settings > click each column > URL ends Field=<name>","Every internal name matches exactly (case and no spaces)."),
("1.4.0.0","NPI Activity Log","ActionType choices Question added, Question closed, Question moved","List settings > ActionType","All three choices present."),
("1.5.0.0","NPI Projects","Gate1-4SignedBy (person), Gate1-4SignedDate (date and time), CloseDate (date), RetentionUntil (date)","List settings > Field= in URL","All 10 internal names match."),
("1.5.0.0","NPI Activity Log","Rename choice 'Choice 8' to 'Gate signed'","List settings > ActionType","'Gate signed' present; 'Choice 8' gone."),
("1.6.0.0","NPIProjectFiles","Columns ProjectID, RequirementID, FormNumber, FormSection (text), Gate (number), UploadedBy (person), UploadedDate (date and time)","Library settings > Field= in URL","All 7 internal names match."),
("1.6.0.0","NPIProjectFiles","Versioning on (major versions)","Library settings > Versioning settings","'Create major versions' selected."),
("1.6.0.0","Power Automate","NPIUploadFile turned on and bound to the app","Solutions > Cloud flows; Studio > Power Automate pane","Flow status On; listed in the app without warning."),
("Any","Gate Requirements","Role set on all 16 rows; ReqLevel 'Choice 3' removed; ApprovedBy filled; DefaultAssignee required","List view","No blanks; no 'Choice 3'."),
("Any","NPI Projects","PartRevKey indexed and unique","List settings > column","'Enforce unique values' Yes."),
("After 1.6.0.0","Environment","Delete test solutions A-D, NPI Upload Test and TEST-* projects/rows/folders","Solutions; lists; library","None remain."),
]
for i,h in enumerate(sh):
    c=ss.cell(1,i+1,h); c.font=H; c.fill=HF; c.alignment=WR; c.border=BD
for n,(rel,where,item,how,ok) in enumerate(setup, start=2):
    vals=[f"S-{n-1:02d}",rel,where,item,how,ok,None,None]
    for i,v in enumerate(vals):
        c=ss.cell(n,i+1,v); c.font=B; c.alignment=WR; c.border=BD
        if i>=6: c.fill=IN
dv=DataValidation(type="list",formula1='"Y,N"',allow_blank=True); ss.add_data_validation(dv); dv.add(f"G2:G{len(setup)+1}")
for col,w in zip("ABCDEFGH",[7,13,18,55,32,38,10,30]): ss.column_dimensions[col].width=w
ss.freeze_panes="A2"; ss.auto_filter.ref=f"A1:H{len(setup)+1}"

# ---------------- Test cases
tc=wb.create_sheet("Test Cases")
th=["ID","Release","Spec / decision","Area","What to check","Preconditions","How to check (steps)","Success condition","Result","Tested by","Date","Notes / evidence","Defect ref"]
for i,h in enumerate(th):
    c=tc.cell(1,i+1,h); c.font=H; c.fill=HF; c.alignment=WR; c.border=BD
prefix={"1.2.0.3":"A","1.3.0.0":"B","1.4.0.0":"C","1.5.0.0":"D","Upload test":"U","1.6.0.0":"E","End-to-end":"Z"}
cnt={}
rows=[]
order=list(prefix)
R.sort(key=lambda x: order.index(x[0]))
for rel,req,area,check,pre,steps,exp in R:
    cnt[rel]=cnt.get(rel,0)+1
    rows.append([f"{prefix[rel]}-{cnt[rel]:02d}",rel,req,area,check,pre,steps,exp])
last=len(rows)+1
for n,row in enumerate(rows, start=2):
    for i,v in enumerate(row+[None]*5):
        c=tc.cell(n,i+1,v); c.font=B; c.alignment=WR; c.border=BD
        if i>=8: c.fill=IN
    tc.cell(n,11).number_format="mm/dd/yyyy"
dv2=DataValidation(type="list",formula1='"Pass,Fail,Blocked,N/A"',allow_blank=True,showErrorMessage=True,errorTitle="Result",error="Choose Pass, Fail, Blocked or N/A")
tc.add_data_validation(dv2); dv2.add(f"I2:I{last}")
dv3=DataValidation(type="date",operator="greaterThan",formula1="45000",allow_blank=True); tc.add_data_validation(dv3); dv3.add(f"K2:K{last}")
for val,col in [("Pass","C6EFCE"),("Fail","FFC7CE"),("Blocked","FFEB9C"),("N/A","D9D9D9")]:
    tc.conditional_formatting.add(f"I2:I{last}",CellIsRule(operator="equal",formula=[f'"{val}"'],fill=PatternFill("solid",fgColor=col)))
for col,w in zip("ABCDEFGHIJKLM",[7,11,11,14,34,32,46,50,10,14,11,32,10]): tc.column_dimensions[col].width=w
tc.freeze_panes="E2"; tc.auto_filter.ref=f"A1:M{last}"

# ---------------- Summary
sm=wb.create_sheet("Summary")
sm["A1"]="Verification summary"; sm["A1"].font=T
sm["A2"]="All figures are formulas over the Test Cases sheet."; sm["A2"].font=Font(name=F,size=9,italic=True)
hd=["Release","Tests","Pass","Fail","Blocked","N/A","Not run","% passed (of tests run)","Release status"]
for i,h in enumerate(hd):
    c=sm.cell(4,i+1,h); c.font=H; c.fill=HF; c.alignment=WR; c.border=BD
TCR=f"'Test Cases'!$B$2:$B${last}"; TCI=f"'Test Cases'!$I$2:$I${last}"
for n,rel in enumerate(order, start=5):
    sm.cell(n,1,rel)
    sm.cell(n,2,f'=COUNTIF({TCR},A{n})')
    for j,v in enumerate(["Pass","Fail","Blocked","N/A"]):
        sm.cell(n,3+j,f'=COUNTIFS({TCR},$A{n},{TCI},"{v}")')
    sm.cell(n,7,f'=B{n}-SUM(C{n}:F{n})')
    sm.cell(n,8,f'=IF(C{n}+D{n}=0,"-",C{n}/(C{n}+D{n}))'); sm.cell(n,8).number_format="0%"
    sm.cell(n,9,f'=IF(B{n}=0,"-",IF(D{n}>0,"Has failures",IF(G{n}=B{n},"Not started",IF(G{n}+E{n}>0,"In progress","Verified"))))')
tot=5+len(order)
sm.cell(tot,1,"Total").font=BB
for col in range(2,8):
    L=get_column_letter(col); sm.cell(tot,col,f"=SUM({L}5:{L}{tot-1})").font=BB
sm.cell(tot,8,f'=IF(C{tot}+D{tot}=0,"-",C{tot}/(C{tot}+D{tot}))'); sm.cell(tot,8).number_format="0%"; sm.cell(tot,8).font=BB
for rr in range(5,tot+1):
    for cc in range(1,10):
        c=sm.cell(rr,cc); c.border=BD
        if c.font!=BB: c.font=B if rr<tot else BB
sm.conditional_formatting.add(f"I5:I{tot-1}",CellIsRule(operator="equal",formula=['"Verified"'],fill=PatternFill("solid",fgColor="C6EFCE")))
sm.conditional_formatting.add(f"I5:I{tot-1}",CellIsRule(operator="equal",formula=['"Has failures"'],fill=PatternFill("solid",fgColor="FFC7CE")))
sm.cell(tot+2,1,"Setup items done").font=BB
sm.cell(tot+2,2,f"=COUNTIF(Setup!$G$2:$G${len(setup)+1},\"Y\")&\" of \"&COUNTA(Setup!$A$2:$A${len(setup)+1})").font=B
for col,w in zip("ABCDEFGHI",[16,8,8,8,9,8,9,14,16]): sm.column_dimensions[col].width=w

# ---------------- Spec coverage
sc=wb.create_sheet("Spec Coverage")
spec=[("R1","One action creates project, ID, folder, templates, requirement rows"),("R2","Duplicate Part + Rev rejected"),("R3","Default assignee by Role"),
("R4","Revision links to previous revision"),("R5","Projects list: gate bar, % done, open OFQ, overdue, QE, next due"),("R6","Filters All / My Tasks / Overdue / Closed and search"),
("R7","% done = (Reviewed + N/A) / total"),("R8","Project Detail with gate bar and gate cards"),("R9","QE reassigns rows and sets due dates"),
("R10","Upload from the row, stamped and linked, real uploader recorded"),("R11","Re-upload saves a new version, history kept"),("R12","Status flow with rework"),
("R13","N/A only on 'If required' rows, with reason"),("R14","Independent Review rows cannot be self-reviewed"),("R15","F-Q-08 items with gate, moves logged"),
("R16","Gate sign-off rules and blocked messages"),("R18","Gates signed in order"),("R19","Gate 4 closes project and sets retention"),
("R20","Config change control"),("R21","Config changes apply to new projects only"),("R22","Library permissions and versioning (decision N1: not built)"),
("U4","New file on Reviewed resets to Done; upload closed after sign-off"),("U5","Self-service file fixes, logged; Remove to _Removed"),("Naming","Duplicate names get the requirement ID prefix")]
hd=["Spec ID","Requirement","Tests","Pass","Fail","Blocked / not run","Coverage status"]
for i,h in enumerate(hd):
    c=sc.cell(1,i+1,h); c.font=H; c.fill=HF; c.alignment=WR; c.border=BD
TCS=f"'Test Cases'!$C$2:$C${last}"
for n,(sid,txt) in enumerate(spec, start=2):
    sc.cell(n,1,sid); sc.cell(n,2,txt)
    sc.cell(n,3,f'=COUNTIF({TCS},A{n})')
    sc.cell(n,4,f'=COUNTIFS({TCS},A{n},{TCI},"Pass")')
    sc.cell(n,5,f'=COUNTIFS({TCS},A{n},{TCI},"Fail")')
    sc.cell(n,6,f'=C{n}-D{n}-E{n}-COUNTIFS({TCS},A{n},{TCI},"N/A")')
    sc.cell(n,7,f'=IF(C{n}=0,"No test (see notes)",IF(E{n}>0,"Failing",IF(F{n}>0,"Not yet verified","Verified")))')
    for cc in range(1,8):
        c=sc.cell(n,cc); c.font=B; c.border=BD; c.alignment=WR
sc.cell(len(spec)+3,1,"Note: R17 (blocked-message wording) is covered by the R16 tests. R22 has no test by decision N1; the versioning part is Setup item S-07.").font=Font(name=F,size=9,italic=True)
sc.conditional_formatting.add(f"G2:G{len(spec)+1}",CellIsRule(operator="equal",formula=['"Verified"'],fill=PatternFill("solid",fgColor="C6EFCE")))
sc.conditional_formatting.add(f"G2:G{len(spec)+1}",CellIsRule(operator="equal",formula=['"Failing"'],fill=PatternFill("solid",fgColor="FFC7CE")))
for col,w in zip("ABCDEFG",[9,60,8,8,8,12,20]): sc.column_dimensions[col].width=w
sc.freeze_panes="A2"

# ---------------- Risks
rk=wb.create_sheet("Risks")
rh=["ID","Item not verified at build time","Why it matters","How to check","Success condition","Status at build","Outcome / notes"]
risks=[
("Attachments@2.3.0 control type in YAML","Wrong type stops the app opening","Open 1.6.0.0","App opens with the PDF picker","Confirmed in tenant 2026-11-18"),
("App-to-flow binding for NPIUploadFile","App cannot call the flow; no runs","Upload once; check run history","A run appears. If not, remove and re-add the flow in Studio","Failed first try 2026-11-18; fix: re-add"),
("JSON(file, IncludeBinaryData) for PDFs","Empty or corrupt file in SharePoint","Upload a PDF and open it from the link","PDF opens and matches the original","Not yet tested"),
("UpdateFile keeps version history","Replace could overwrite without history","Replace a file; open Version history","Previous version listed","Not yet tested"),
("MoveFileAsync with nameConflictBehavior 2","Remove may fail if the name already exists in _Removed","Remove two files with the same name over time","Both end in _Removed (second renamed)","Not yet tested"),
("Library column stamping","Uploader not recorded in the library","Check properties of an uploaded file","All 7 columns filled; app says saved (not 'could not be stamped')","Not yet tested"),
("Studio formula type checks","A formula error shows in Studio","App checker after each import","No errors (record any)","Activity 'Detail' error found 2026-11-18; hand fix given"),
("Large files","Slow or time out (sent as text)","Upload a 10-20 MB PDF","Completes in under 2 minutes","Not yet tested"),
]
for i,h in enumerate(rh):
    c=rk.cell(1,i+1,h); c.font=H; c.fill=HF; c.alignment=WR; c.border=BD
for n,(a,b,cc,d,e) in enumerate(risks, start=2):
    for i,v in enumerate([f"K-{n-1:02d}",a,b,cc,d,e,None]):
        c=rk.cell(n,i+1,v); c.font=B; c.alignment=WR; c.border=BD
        if i==6: c.fill=IN
for col,w in zip("ABCDEFG",[7,36,32,34,36,28,30]): rk.column_dimensions[col].width=w
rk.freeze_panes="A2"

wb._sheets=[wb[n] for n in ["Instructions","Summary","Setup","Test Cases","Spec Coverage","Risks"]]
wb.save(OUT)
print(len(rows),"tests;", len(setup),"setup;", len(spec),"spec rows")
