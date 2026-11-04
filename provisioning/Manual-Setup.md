# Create the SharePoint lists by hand (about 30–40 minutes)

Use this guide when you can't run `Create-Lists.ps1`, or when the setup flow is blocked. Some organisations' data policies block the "Send an HTTP request to SharePoint" action that the flow uses.

You need **Site Owner** (Full Control) on the site. Everything is done in the browser.

## Rules that matter
- **Type each column name exactly as shown**: no spaces, same capitals. The app refers to columns by these names.
- **Never rename a column after creating it.** If you mistype one, delete it straight away and create it again. That's fine during setup, before any data exists.
- **Required:** open **More options** in the column panel and switch on **Require that this column contains information**. In the two **libraries**, leave every column **not required**, even when the app treats it as required (SPEC.md A-21).
- **Unique:** **More options** → **Enforce unique values** = Yes. SharePoint indexes the column automatically.
- **Choice values:** enter one per line, spelled exactly as shown. Under **More options**, set **Can add values manually** to **No**.

## How to…
- **Create a list:** site home → **+ New** → **List** → **Blank list** → name → **Create**.
- **Create a library:** site home → **+ New** → **Document library** → name → **Create**.
- **Add a column:** in the list or library, select **+ Add column** at the right end of the column headers → pick the type → **Next**.
  - If you don't see a type such as **Lookup**, choose **See all column types**.
- **Add an index:** ⚙ (top right) → **List settings** (or **Library settings**) → **Indexed columns** → **Create a new index** → pick the column → **Create**.
- **Turn on versioning (libraries):** ⚙ → **Library settings** → **Versioning settings** → **Create major versions** → **OK**.

Tick off each line as you go.

---

## 1. List `JP_Employees`

Keep the built-in **Title** column (it holds the employee's name). Don't rename it.

| ✓ | Column name | Type | Settings |
|---|---|---|---|
| ☐ | `Email` | Single line of text | Required. **Enforce unique values: Yes** |
| ☐ | `EmployeeUser` | Person | Allow multiple selections: No |
| ☐ | `JobTitle` | Choice | Required. Choices: `Production Technician`, `Quality Technician`, `Supervisor`, `Manager`, `Other`. Default: none |
| ☐ | `Department` | Choice | Choices: `Production`, `Quality`, `Other`. Default: none |
| ☐ | `Shift` | Choice | Choices: `1st`, `2nd`, `3rd`, `Days`. Default: none |
| ☐ | `AppRole` | Choice | Required. Choices: `Manager/Supervisor`, `Technician`, `Viewer`. Default: `Technician` |
| ☐ | `Active` | Yes/No | Default: **Yes** |
| ☐ | `Supervisor` | Lookup | Source list: **JP_Employees**, column: **Title**. Allow multiple: No |

**Indexes** (List settings → Indexed columns), one at a time:
☐ `Department` ☐ `Shift` ☐ `Supervisor` ☐ `Active`

`Email` is already indexed through Enforce unique values.

---

## 2. Library `JP_Documents`

**Versioning:** ☐ Library settings → Versioning settings → **Create major versions**.

None of these columns are required (see Rules).

| ✓ | Column name | Type | Settings |
|---|---|---|---|
| ☐ | `DocType` | Choice | Choices: `JQC`, `PWI`. Default: none |
| ☐ | `DocNumber` | Single line of text | **Enforce unique values: Yes** |
| ☐ | `DocTitle` | Single line of text | |
| ☐ | `Revision` | Single line of text | |
| ☐ | `RevisionDate` | Date and time | Include time: **No** |
| ☐ | `RevisionNotes` | Multiple lines of text | Plain text (rich text off) |
| ☐ | `Area` | Choice | Choices: `Production`, `Quality`, `Metrology`, `Other`. Default: none |
| ☐ | `Status` | Choice | Choices: `Active`, `Obsolete`. Default: `Active` |
| ☐ | `Trainers` | Person | **Allow multiple selections: Yes** |
| ☐ | `Description` | Multiple lines of text | Plain text |

**Indexes:** ☐ `DocType` ☐ `Area` ☐ `Status`

`DocNumber` is already indexed through Enforce unique values.

> If SharePoint says a name like `Status` or `Description` already exists in the library, tell me the exact message before carrying on.

---

## 3. List `JP_Assignments`

Keep **Title** as it is (the app fills it in).

| ✓ | Column name | Type | Settings |
|---|---|---|---|
| ☐ | `Employee` | Lookup | Required. Source list: **JP_Employees**, column: **Title** |
| ☐ | `EmployeeEmail` | Single line of text | Required |
| ☐ | `DocumentID` | Number | Required. Decimal places: 0 |
| ☐ | `DocType` | Choice | Required. Choices: `JQC`, `PWI`. Default: none |
| ☐ | `DocNumber` | Single line of text | Required |
| ☐ | `DocTitle` | Single line of text | Required |
| ☐ | `RevisionAssigned` | Single line of text | Required |
| ☐ | `AssignmentReason` | Choice | Required. Choices: `New Assignment`, `Revision Change`. Default: `New Assignment` |
| ☐ | `PreviousAssignmentID` | Number | Decimal places: 0 |
| ☐ | `IsCurrent` | Yes/No | Default: **Yes** |
| ☐ | `AssignedBy` | Person | Required |
| ☐ | `AssignedDate` | Date and time | Required. Include time: **No** |
| ☐ | `DueDate` | Date and time | Include time: **No** |
| ☐ | `Trainer` | Person | |
| ☐ | `Status` | Choice | Required. Choices: `Assigned`, `In Training`, `Signed Off`, `Superseded`, `Removed`. Default: `Assigned` |
| ☐ | `SignedOffBy` | Person | |
| ☐ | `SignedOffDate` | Date and time | Include time: **Yes** |
| ☐ | `SignoffFileID` | Number | Decimal places: 0 |
| ☐ | `Comments` | Multiple lines of text | Plain text |

**Indexes:** ☐ `EmployeeEmail` ☐ `DocumentID` ☐ `DocType` ☐ `IsCurrent` ☐ `Status`

---

## 4. Library `JP_SignoffRecords`

**Versioning:** ☐ Library settings → Versioning settings → **Create major versions**.

| ✓ | Column name | Type | Settings |
|---|---|---|---|
| ☐ | `AssignmentID` | Number | Decimal places: 0 |
| ☐ | `DocType` | Choice | Choices: `JQC`, `PWI`. Default: none |
| ☐ | `Revision` | Single line of text | |
| ☐ | `EmployeeEmail` | Single line of text | |
| ☐ | `UploadedBy` | Person | |

**Indexes:** ☐ `AssignmentID` ☐ `EmployeeEmail`

---

## 5. List `JP_Settings`

| ✓ | Column name | Type | Settings |
|---|---|---|---|
| ☐ | `MinQualifiedPerTask` | Number | Required. Decimal places: 0. Minimum: 1. Default: 2 |
| ☐ | `ResignDueDays` | Number | Required. Decimal places: 0. Minimum: 1. Default: 14 |

☐ **Add the one settings row:** **+ New** → Title `Settings`, MinQualifiedPerTask `2`, ResignDueDays `14` → **Save**.
`TODO:` confirm 2 and 14 (CLAUDE.md Section 19).

---

## 6. Check your work (2 minutes)

- ☐ Five items on the site: `JP_Employees`, `JP_Documents`, `JP_Assignments`, `JP_SignoffRecords`, `JP_Settings`.
- ☐ Check that each internal name has no spaces or stray characters. Open ⚙ → List settings → click a column → look at the end of the browser address bar: `Field=JobTitle`, not `Field=Job_x0020_Title` or `Field=JobTitle0`.
- ☐ `JP_Settings` has exactly one row.

Then import the main solution. In the wizard, pick this site and the five lists for the environment variables (see `solution/env-vars.md`).

## Optional: permissions (CLAUDE.md Section 9)
This can wait until after testing.
- ⚙ → **Site permissions** → **Advanced permissions settings** → create three groups (placeholders: JQCPWI Managers, JQCPWI Technicians, JQCPWI Viewers).
- In each list's settings → **Permissions for this list** → **Stop inheriting permissions** → set:
  - Managers: Contribute on all five.
  - Technicians: Read on JP_Employees, JP_Documents and JP_Settings. Contribute on JP_Assignments and JP_SignoffRecords.
  - Viewers: Read on all five.
