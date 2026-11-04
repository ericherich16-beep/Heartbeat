<#
.SYNOPSIS
    Imports the fictional seed data in /seed into a TEST site for JQC/PWI Management.

.DESCRIPTION
    Run this after Create-Lists.ps1, against a test site only. The script:
      1. Validates the seed CSVs (references, one current row per employee and document).
         It writes nothing if they fail.
      2. Updates the JP_Settings row from settings.csv.
      3. Creates employees, then sets their Supervisor lookups.
      4. Uploads a placeholder PDF for each document. Where a document has a
         PreviousRevision, that revision is uploaded first and the current one is
         uploaded over it, so the earlier file is kept in version history.
      5. Creates assignments in CSV order, linking PreviousAssignmentID.
      6. Uploads a placeholder sign-off PDF for every signed row and sets SignoffFileID.

    All files are generated placeholders marked "FICTIONAL SEED FILE".
    Expected results are in /seed/expected-results.md.

    People columns (AssignedBy, Trainer, SignedOffBy, Trainers, UploadedBy) need
    real accounts in your tenant. The seed uses fictional @contoso.com addresses:
      - Pass -UserMapPath to map each seed email to a real TEST account. The mapped
        email is also written to JP_Employees.Email, so testers get the right role.
      - Any person who can't be resolved is replaced by the signed-in account in
        required people columns (with a warning), and left blank in optional ones.

.PARAMETER SiteUrl
    Full URL of the TEST SharePoint site.

.PARAMETER ClientId
    Client ID of the Entra ID app registration used by PnP.PowerShell.
    TODO: use your tenant's PnP app registration.

.PARAMETER SeedPath
    Folder that holds the seed CSVs. Defaults to ../seed next to this script.

.PARAMETER UserMapPath
    Optional CSV with the columns SeedEmail and TenantEmail. Copy
    seed/user-map.example.csv to seed/user-map.csv (git-ignored) and fill it in.

.EXAMPLE
    ./Import-SeedData.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/JQCPWI-Test" -ClientId "00000000-0000-0000-0000-000000000000" -UserMapPath ../seed/user-map.csv

.NOTES
    Requires PowerShell 7.4 or later and PnP.PowerShell 2.x or later.
    The script stops if any seed employee email already exists in JP_Employees,
    so it can't import the same data twice.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://')]
    [string] $SiteUrl,

    [Parameter(Mandatory = $true)]
    [string] $ClientId,

    [string] $SeedPath = (Join-Path $PSScriptRoot '..' 'seed'),

    [string] $UserMapPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step([string] $Message) { Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Info([string] $Message) { Write-Host "    $Message" }

function Test-Blank([object] $Value) { return [string]::IsNullOrWhiteSpace([string] $Value) }

function Get-DateFromOffset([string] $DaysAgo) {
    if (Test-Blank $DaysAgo) { return $null }
    return (Get-Date).Date.AddDays(-[int] $DaysAgo)
}

# ---------------------------------------------------------------------------
# Placeholder PDF (valid single-page PDF with correct xref offsets)
# ---------------------------------------------------------------------------

function New-PlaceholderPdf([string[]] $Lines) {
    $safe = foreach ($line in $Lines) {
        $ascii = $line -replace '[^\x20-\x7E]', '-'
        '(' + ($ascii -replace '([\\()])', '\$1') + ') Tj T*'
    }
    $content = "BT /F1 14 Tf 72 720 Td 20 TL`n" + ($safe -join "`n") + "`nET"

    $objects = @(
        '<< /Type /Catalog /Pages 2 0 R >>'
        '<< /Type /Pages /Kids [3 0 R] /Count 1 >>'
        '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>'
        "<< /Length $($content.Length) >>`nstream`n$content`nendstream"
        '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'
    )

    $sb = [System.Text.StringBuilder]::new()
    [void] $sb.Append("%PDF-1.4`n")
    $offsets = @()
    for ($i = 0; $i -lt $objects.Count; $i++) {
        $offsets += $sb.Length
        [void] $sb.Append("$($i + 1) 0 obj`n$($objects[$i])`nendobj`n")
    }
    $xrefStart = $sb.Length
    [void] $sb.Append("xref`n0 $($objects.Count + 1)`n0000000000 65535 f `n")
    foreach ($o in $offsets) { [void] $sb.Append(("{0:D10} 00000 n `n" -f $o)) }
    [void] $sb.Append("trailer`n<< /Size $($objects.Count + 1) /Root 1 0 R >>`nstartxref`n$xrefStart`n%%EOF`n")

    return [System.Text.Encoding]::ASCII.GetBytes($sb.ToString())
}

function Add-PlaceholderFile {
    param([string] $Library, [string] $FileName, [string[]] $Lines, [hashtable] $Values)
    $bytes  = New-PlaceholderPdf -Lines $Lines
    $stream = [System.IO.MemoryStream]::new($bytes)
    try {
        # Add-PnPFile replaces an existing file with the same name. With
        # versioning on, the earlier file is kept as a previous version.
        Add-PnPFile -Folder $Library -FileName $FileName -Stream $stream -Values $Values | Out-Null
    }
    finally {
        $stream.Dispose()
    }
    return (Get-PnPFile -Url "$Library/$FileName" -AsListItem).Id
}

# ---------------------------------------------------------------------------
# Load and validate seed data (nothing is written if this fails)
# ---------------------------------------------------------------------------

Write-Step "Loading seed data from $SeedPath"
$employees   = @(Import-Csv (Join-Path $SeedPath 'employees.csv'))
$documents   = @(Import-Csv (Join-Path $SeedPath 'documents.csv'))
$assignments = @(Import-Csv (Join-Path $SeedPath 'assignments.csv'))
$settings    = @(Import-Csv (Join-Path $SeedPath 'settings.csv'))

$userMap = @{}
if (-not (Test-Blank $UserMapPath)) {
    foreach ($row in Import-Csv $UserMapPath) {
        if ((Test-Blank $row.TenantEmail) -or $row.TenantEmail -like 'TODO*') { continue }
        $userMap[$row.SeedEmail.Trim().ToLowerInvariant()] = $row.TenantEmail.Trim().ToLowerInvariant()
    }
    Write-Info "User map loaded: $($userMap.Count) mapped account(s)"
    $dupes = @($userMap.Values | Group-Object | Where-Object { $_.Count -gt 1 })
    if ($dupes.Count -gt 0) {
        throw "User map assigns the same tenant account to more than one seed email ($($dupes[0].Name)). JP_Employees.Email must be unique, so map each seed email to a different account, or leave it unmapped."
    }
}

function Get-MappedEmail([string] $SeedEmail) {
    $key = $SeedEmail.Trim().ToLowerInvariant()
    if ($userMap.ContainsKey($key)) { return $userMap[$key] }
    return $key
}

$errors   = [System.Collections.Generic.List[string]]::new()
$empByKey = @{}; foreach ($e in $employees) { $empByKey[$e.Email.ToLowerInvariant()] = $e }
$docByNum = @{}; foreach ($d in $documents) { $docByNum[$d.DocNumber] = $d }

foreach ($e in $employees) {
    if (-not (Test-Blank $e.SupervisorEmail) -and -not $empByKey.ContainsKey($e.SupervisorEmail.ToLowerInvariant())) {
        $errors.Add("Employee $($e.Email): unknown supervisor $($e.SupervisorEmail)")
    }
}
$seenKeys = @{}; $currentPairs = @{}
foreach ($a in $assignments) {
    if (-not $empByKey.ContainsKey($a.EmployeeEmail.ToLowerInvariant())) { $errors.Add("$($a.Key): unknown employee $($a.EmployeeEmail)") }
    if (-not $docByNum.ContainsKey($a.DocNumber)) { $errors.Add("$($a.Key): unknown document $($a.DocNumber)"); continue }
    $d = $docByNum[$a.DocNumber]
    if ($a.RevisionAssigned -ne $d.Revision -and $a.RevisionAssigned -ne $d.PreviousRevision) {
        $errors.Add("$($a.Key): revision $($a.RevisionAssigned) doesn't exist for $($a.DocNumber)")
    }
    if (-not (Test-Blank $a.PreviousKey) -and -not $seenKeys.ContainsKey($a.PreviousKey)) {
        $errors.Add("$($a.Key): PreviousKey $($a.PreviousKey) must appear earlier in the file")
    }
    if ([bool]::Parse($a.IsCurrent)) {
        $pair = "$($a.EmployeeEmail.ToLowerInvariant())|$($a.DocNumber)"
        if ($currentPairs.ContainsKey($pair)) { $errors.Add("$($a.Key): second current row for $pair") }
        $currentPairs[$pair] = $true
    }
    $seenKeys[$a.Key] = $true
}
if ($errors.Count -gt 0) {
    $errors | ForEach-Object { Write-Host "    ERROR: $_" -ForegroundColor Red }
    throw 'Seed data failed validation. Nothing was written.'
}
Write-Info "Validated $($employees.Count) employees, $($documents.Count) documents, $($assignments.Count) assignments"

# ---------------------------------------------------------------------------
# Connect and guard against a second import
# ---------------------------------------------------------------------------

Write-Step "Connecting to $SiteUrl"
Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId

$web = Get-PnPWeb -Includes CurrentUser
$fallbackUser = if (-not (Test-Blank $web.CurrentUser.Email)) { $web.CurrentUser.Email } else { $web.CurrentUser.LoginName }

$existingEmails = @(Get-PnPListItem -List 'JP_Employees' -PageSize 500 | ForEach-Object { ([string] $_.FieldValues['Email']).ToLowerInvariant() })
$clash = @($employees | Where-Object { $existingEmails -contains (Get-MappedEmail $_.Email) })
if ($clash.Count -gt 0) {
    throw "JP_Employees already contains seed employees (for example $(Get-MappedEmail $clash[0].Email)). Use a fresh test site."
}

# ---------------------------------------------------------------------------
# People resolution
# ---------------------------------------------------------------------------

$personCache = @{}
$script:fallbackCount = 0

function Resolve-Person {
    param([string] $SeedEmail, [switch] $NoFallback)
    if (Test-Blank $SeedEmail) { return $null }
    $email = Get-MappedEmail $SeedEmail
    if (-not $personCache.ContainsKey($email)) {
        try {
            New-PnPUser -LoginName $email -ErrorAction Stop | Out-Null
            $personCache[$email] = $email
        }
        catch {
            Write-Warning "Can't resolve '$email' in this tenant. Add it to the user map to fix this."
            $personCache[$email] = $null
        }
    }
    $resolved = $personCache[$email]
    if ($null -eq $resolved -and -not $NoFallback) {
        $script:fallbackCount++
        return $fallbackUser
    }
    return $resolved
}

# ---------------------------------------------------------------------------
# 1. Settings
# ---------------------------------------------------------------------------

Write-Step 'Settings'
$settingsItem = Get-PnPListItem -List 'JP_Settings' -PageSize 10 | Select-Object -First 1
$settingsValues = @{
    MinQualifiedPerTask = [int] $settings[0].MinQualifiedPerTask
    ResignDueDays       = [int] $settings[0].ResignDueDays
}
if ($null -eq $settingsItem) {
    $settingsValues['Title'] = 'Settings'
    Add-PnPListItem -List 'JP_Settings' -Values $settingsValues | Out-Null
}
else {
    Set-PnPListItem -List 'JP_Settings' -Identity $settingsItem.Id -Values $settingsValues | Out-Null
}
Write-Info "MinQualifiedPerTask = $($settingsValues.MinQualifiedPerTask), ResignDueDays = $($settingsValues.ResignDueDays)"

# ---------------------------------------------------------------------------
# 2. Employees
# ---------------------------------------------------------------------------

Write-Step 'Employees'
$empIds    = @{}   # seed email (lower) -> list item ID
$empTitles = @{}
foreach ($e in $employees) {
    $values = @{
        Title      = $e.Title
        Email      = Get-MappedEmail $e.Email
        JobTitle   = $e.JobTitle
        Department = $e.Department
        Shift      = $e.Shift
        AppRole    = $e.AppRole
        Active     = [bool]::Parse($e.Active)
    }
    $user = Resolve-Person -SeedEmail $e.Email -NoFallback
    if ($null -ne $user) { $values['EmployeeUser'] = $user }

    $item = Add-PnPListItem -List 'JP_Employees' -Values $values
    $key  = $e.Email.ToLowerInvariant()
    $empIds[$key]    = $item.Id
    $empTitles[$key] = $e.Title
    Write-Info "$($e.Title) -> ID $($item.Id)"
}
foreach ($e in $employees | Where-Object { -not (Test-Blank $_.SupervisorEmail) }) {
    Set-PnPListItem -List 'JP_Employees' -Identity $empIds[$e.Email.ToLowerInvariant()] `
        -Values @{ Supervisor = $empIds[$e.SupervisorEmail.ToLowerInvariant()] } | Out-Null
}
Write-Info 'Supervisors linked'

# ---------------------------------------------------------------------------
# 3. Documents
# ---------------------------------------------------------------------------

Write-Step 'Documents'
$docIds = @{}
foreach ($d in $documents) {
    $trainers = @()
    if (-not (Test-Blank $d.TrainerEmails)) {
        $trainers = @($d.TrainerEmails -split ';' | ForEach-Object { Resolve-Person -SeedEmail $_ -NoFallback } | Where-Object { $_ })
        if ($trainers.Count -eq 0) {
            # Keep the document assignable for testing, as the seed intends.
            $trainers = @($fallbackUser); $script:fallbackCount++
        }
    }

    $fileName = "$($d.DocNumber).pdf"
    $kind     = if ($d.DocType -eq 'JQC') { 'JQC template' } else { 'Process work instruction' }

    $revisions = @()
    if (-not (Test-Blank $d.PreviousRevision)) {
        $revisions += @{ Rev = $d.PreviousRevision; DaysAgo = $d.PreviousRevisionDaysAgo; Notes = $d.PreviousRevisionNotes }
    }
    $revisions += @{ Rev = $d.Revision; DaysAgo = $d.RevisionDaysAgo; Notes = $d.RevisionNotes }

    foreach ($r in $revisions) {
        $values = @{
            DocType       = $d.DocType
            DocNumber     = $d.DocNumber
            DocTitle      = $d.DocTitle
            Revision      = $r.Rev
            RevisionDate  = Get-DateFromOffset $r.DaysAgo
            RevisionNotes = $r.Notes
            Area          = $d.Area
            Status        = $d.Status
            Description   = $d.Description
        }
        if ($trainers.Count -gt 0) { $values['Trainers'] = $trainers }

        $lines = @(
            'FICTIONAL SEED FILE - NOT A REAL DOCUMENT'
            'JQC/PWI Management test data'
            ''
            "$kind $($d.DocNumber)  Rev $($r.Rev)"
            $d.DocTitle
            ''
            "Revision notes: $($r.Notes)"
        )
        $id = Add-PlaceholderFile -Library 'JP_Documents' -FileName $fileName -Lines $lines -Values $values
    }
    $docIds[$d.DocNumber] = $id
    Write-Info "$($d.DocNumber) Rev $($d.Revision) -> ID $id"
}

# ---------------------------------------------------------------------------
# 4. Assignments and sign-off files
# ---------------------------------------------------------------------------

Write-Step 'Assignments'
$dash      = [char] 0x2013
$asgIds    = @{}
$fileCount = 0
foreach ($a in $assignments) {
    $empKey = $a.EmployeeEmail.ToLowerInvariant()
    $d      = $docByNum[$a.DocNumber]

    $values = @{
        Title            = "$($a.DocNumber) Rev $($a.RevisionAssigned) $dash $($empTitles[$empKey])"
        Employee         = $empIds[$empKey]
        EmployeeEmail    = Get-MappedEmail $a.EmployeeEmail
        DocumentID       = $docIds[$a.DocNumber]
        DocType          = $d.DocType
        DocNumber        = $a.DocNumber
        DocTitle         = $d.DocTitle
        RevisionAssigned = $a.RevisionAssigned
        AssignmentReason = $a.AssignmentReason
        IsCurrent        = [bool]::Parse($a.IsCurrent)
        Status           = $a.Status
        AssignedBy       = Resolve-Person -SeedEmail $a.AssignedByEmail
        AssignedDate     = Get-DateFromOffset $a.AssignedDaysAgo
    }
    if (-not (Test-Blank $a.DueInDays))   { $values['DueDate'] = (Get-Date).Date.AddDays([int] $a.DueInDays) }
    if (-not (Test-Blank $a.PreviousKey)) { $values['PreviousAssignmentID'] = $asgIds[$a.PreviousKey] }
    if (-not (Test-Blank $a.Comments))    { $values['Comments'] = $a.Comments }
    $trainer = Resolve-Person -SeedEmail $a.TrainerEmail -NoFallback
    if ($null -ne $trainer) { $values['Trainer'] = $trainer }

    $signedOn = $null
    if (-not (Test-Blank $a.SignedOffByEmail)) {
        $signedOn = (Get-DateFromOffset $a.SignedOffDaysAgo).AddHours(10)
        $values['SignedOffBy']   = Resolve-Person -SeedEmail $a.SignedOffByEmail
        $values['SignedOffDate'] = $signedOn
    }

    $item = Add-PnPListItem -List 'JP_Assignments' -Values $values
    $asgIds[$a.Key] = $item.Id

    if ($null -ne $signedOn) {
        $empId    = $empIds[$empKey]
        $fileName = "$($a.DocNumber)_Rev$($a.RevisionAssigned)_$($empId)_$($signedOn.ToString('yyyyMMdd')).pdf"
        $kind     = if ($d.DocType -eq 'JQC') { 'Signed JQC' } else { 'PWI training log' }
        $lines = @(
            'FICTIONAL SEED FILE - NOT A REAL RECORD'
            'JQC/PWI Management test data'
            ''
            "$kind  $($a.DocNumber)  Rev $($a.RevisionAssigned)"
            $d.DocTitle
            "Employee: $($empTitles[$empKey])"
            "Signed off: $($signedOn.ToString('yyyy-MM-dd'))"
        )
        $fileValues = @{
            AssignmentID  = $item.Id
            DocType       = $d.DocType
            Revision      = $a.RevisionAssigned
            EmployeeEmail = Get-MappedEmail $a.EmployeeEmail
            UploadedBy    = Resolve-Person -SeedEmail $a.SignedOffByEmail
        }
        $fileId = Add-PlaceholderFile -Library 'JP_SignoffRecords' -FileName $fileName -Lines $lines -Values $fileValues
        Set-PnPListItem -List 'JP_Assignments' -Identity $item.Id -Values @{ SignoffFileID = $fileId } | Out-Null
        $fileCount++
    }
    Write-Info "$($a.Key) $($values.Title) [$($a.Status)] -> ID $($item.Id)"
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Step 'Done'
Write-Info "Employees:        $($empIds.Count)"
Write-Info "Documents:        $($docIds.Count)"
Write-Info "Assignments:      $($asgIds.Count)"
Write-Info "Sign-off files:   $fileCount"
if ($script:fallbackCount -gt 0) {
    Write-Warning "$($script:fallbackCount) people value(s) were replaced by the signed-in account ($fallbackUser) because they couldn't be resolved. Use -UserMapPath for realistic tests."
}
Write-Host ''
Write-Host 'Check the app against /seed/expected-results.md.'
