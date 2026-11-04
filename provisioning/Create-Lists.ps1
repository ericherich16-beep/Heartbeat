<#
.SYNOPSIS
    Creates the SharePoint lists and libraries for JQC/PWI Management.

.DESCRIPTION
    Creates (or brings up to date) these lists and libraries on the target site:
      JP_Employees       (list)
      JP_Documents       (document library, major versioning on)
      JP_Assignments     (list)
      JP_SignoffRecords  (document library, major versioning on)
      JP_Settings        (list, single row)

    Schema source: CLAUDE.md Section 6 and SPEC.md Section 3.

    The script is idempotent. Lists, libraries and columns that already exist are
    left in place, and only missing pieces are added. It never deletes anything.

    Nothing site-specific is hard-coded. The site URL and the Entra app client ID
    are passed in as parameters.

.PARAMETER SiteUrl
    Full URL of the target SharePoint site. Use a test site first.

.PARAMETER ClientId
    Client ID of the Entra ID app registration that PnP.PowerShell uses for
    interactive sign-in. Recent PnP.PowerShell versions require one. See
    https://pnp.github.io/powershell/articles/registerapplication.html
    TODO: register an app in your tenant (or reuse your org's PnP app) and pass its ID.

.PARAMETER ConfigurePermissions
    Optional. Breaks permission inheritance on the five JP_ lists and libraries and
    grants the CLAUDE.md Section 9 permissions to three SharePoint groups.
    Missing groups are created. Run it without this switch first if you're not sure.

.PARAMETER ManagersGroup
    Name of the managers group. Placeholder by default. TODO: map to the real group.

.PARAMETER TechniciansGroup
    Name of the technicians group. Placeholder by default. TODO: map to the real group.

.PARAMETER ViewersGroup
    Name of the viewers group. Placeholder by default. TODO: map to the real group.

.EXAMPLE
    ./Create-Lists.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/JQCPWI-Test" -ClientId "00000000-0000-0000-0000-000000000000"

.EXAMPLE
    ./Create-Lists.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/JQCPWI-Test" -ClientId "00000000-0000-0000-0000-000000000000" -ConfigurePermissions

.NOTES
    Requires PowerShell 7.4 or later and the PnP.PowerShell module (2.x or later):
        Install-Module PnP.PowerShell -Scope CurrentUser
    The account you sign in with needs Site Owner (Full Control) on the site.

    In the two document libraries, columns that CLAUDE.md marks as required are
    created as NOT required in SharePoint. The app and the upload flow enforce them
    instead (SPEC.md A-21). If a library column is required in SharePoint, files
    uploaded by the flow before "Update file properties" runs can be left in an
    incomplete state.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://')]
    [string] $SiteUrl,

    [Parameter(Mandatory = $true)]
    [string] $ClientId,

    [switch] $ConfigurePermissions,

    [string] $ManagersGroup    = 'JQCPWI Managers',     # TODO: map to real group at deployment
    [string] $TechniciansGroup = 'JQCPWI Technicians',  # TODO: map to real group at deployment
    [string] $ViewersGroup     = 'JQCPWI Viewers'       # TODO: map to real group at deployment
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Schema definition
#   Name     : internal column name (no spaces, never changes)
#   Display  : friendly display name shown in SharePoint and Power Apps
#   Type     : Text | Note | Choice | Number | Boolean | DateOnly | DateTime | User | UserMulti | Lookup
#   Required : enforced by SharePoint (lists only, see notes above)
#   Indexed  : creates a column index (needed for delegable, large-list filtering)
#   Unique   : enforce unique values (column is indexed as well)
#   Choices  : choice values (Choice only)
#   Default  : default value
#   LookupList / LookupField : Lookup only
# ---------------------------------------------------------------------------

$shiftChoices      = @('1st', '2nd', '3rd', 'Days')
$departmentChoices = @('Production', 'Quality', 'Other')
$docTypeChoices    = @('JQC', 'PWI')

$schema = @(
    @{
        Title       = 'JP_Employees'
        Template    = 'GenericList'
        Description = 'JQC/PWI Management - employees. Never delete; set Active = No.'
        TitleDisplay = 'Employee Name'
        Fields = @(
            @{ Name = 'Email';        Display = 'Email';         Type = 'Text';     Required = $true;  Indexed = $true; Unique = $true }
            @{ Name = 'EmployeeUser'; Display = 'Employee User'; Type = 'User' }
            @{ Name = 'JobTitle';     Display = 'Job Title';     Type = 'Choice';   Required = $true;  Choices = @('Production Technician', 'Quality Technician', 'Supervisor', 'Manager', 'Other') }
            @{ Name = 'Department';   Display = 'Department';    Type = 'Choice';   Indexed = $true;   Choices = $departmentChoices }
            @{ Name = 'Shift';        Display = 'Shift';         Type = 'Choice';   Indexed = $true;   Choices = $shiftChoices }
            @{ Name = 'Supervisor';   Display = 'Supervisor';    Type = 'Lookup';   Indexed = $true;   LookupList = 'JP_Employees'; LookupField = 'Title' }
            @{ Name = 'AppRole';      Display = 'App Role';      Type = 'Choice';   Required = $true;  Choices = @('Manager/Supervisor', 'Technician', 'Viewer'); Default = 'Technician' }
            @{ Name = 'Active';       Display = 'Active';        Type = 'Boolean';  Indexed = $true;   Default = '1' }
        )
    }
    @{
        Title       = 'JP_Documents'
        Template    = 'DocumentLibrary'
        Description = 'JQC/PWI Management - JQC templates and PWIs. One item per document; new revisions replace the file in place.'
        Versioning  = $true
        Fields = @(
            @{ Name = 'DocType';       Display = 'Doc Type';       Type = 'Choice';    Indexed = $true; Choices = $docTypeChoices }
            @{ Name = 'DocNumber';     Display = 'Doc Number';     Type = 'Text';      Indexed = $true; Unique = $true }
            @{ Name = 'DocTitle';      Display = 'Doc Title';      Type = 'Text' }
            @{ Name = 'Revision';      Display = 'Revision';       Type = 'Text' }
            @{ Name = 'RevisionDate';  Display = 'Revision Date';  Type = 'DateOnly' }
            @{ Name = 'RevisionNotes'; Display = 'Revision Notes'; Type = 'Note' }
            @{ Name = 'Area';          Display = 'Area';           Type = 'Choice';    Indexed = $true; Choices = @('Production', 'Quality', 'Metrology', 'Other') }
            @{ Name = 'Status';        Display = 'Status';         Type = 'Choice';    Indexed = $true; Choices = @('Active', 'Obsolete'); Default = 'Active' }
            @{ Name = 'Trainers';      Display = 'Trainers';       Type = 'UserMulti' }
            @{ Name = 'Description';   Display = 'Description';    Type = 'Note' }
        )
    }
    @{
        Title       = 'JP_Assignments'
        Template    = 'GenericList'
        Description = 'JQC/PWI Management - one row per employee per document revision. Never delete; use Removed or Superseded.'
        TitleDisplay = 'Title'
        Fields = @(
            @{ Name = 'Employee';             Display = 'Employee';               Type = 'Lookup';   Required = $true; LookupList = 'JP_Employees'; LookupField = 'Title' }
            @{ Name = 'EmployeeEmail';        Display = 'Employee Email';         Type = 'Text';     Required = $true; Indexed = $true }
            @{ Name = 'DocumentID';           Display = 'Document ID';            Type = 'Number';   Required = $true; Indexed = $true }
            @{ Name = 'DocType';              Display = 'Doc Type';               Type = 'Choice';   Required = $true; Indexed = $true; Choices = $docTypeChoices }
            @{ Name = 'DocNumber';            Display = 'Doc Number';             Type = 'Text';     Required = $true }
            @{ Name = 'DocTitle';             Display = 'Doc Title';              Type = 'Text';     Required = $true }
            @{ Name = 'RevisionAssigned';     Display = 'Revision Assigned';      Type = 'Text';     Required = $true }
            @{ Name = 'AssignmentReason';     Display = 'Assignment Reason';      Type = 'Choice';   Required = $true; Choices = @('New Assignment', 'Revision Change'); Default = 'New Assignment' }
            @{ Name = 'PreviousAssignmentID'; Display = 'Previous Assignment ID'; Type = 'Number' }
            @{ Name = 'IsCurrent';            Display = 'Is Current';             Type = 'Boolean';  Indexed = $true; Default = '1' }
            @{ Name = 'AssignedBy';           Display = 'Assigned By';            Type = 'User';     Required = $true }
            @{ Name = 'AssignedDate';         Display = 'Assigned Date';          Type = 'DateOnly'; Required = $true }
            @{ Name = 'DueDate';              Display = 'Due Date';               Type = 'DateOnly' }
            @{ Name = 'Trainer';              Display = 'Trainer';                Type = 'User' }
            @{ Name = 'Status';               Display = 'Status';                 Type = 'Choice';   Required = $true; Indexed = $true; Choices = @('Assigned', 'In Training', 'Signed Off', 'Superseded', 'Removed'); Default = 'Assigned' }
            @{ Name = 'SignedOffBy';          Display = 'Signed Off By';          Type = 'User' }
            @{ Name = 'SignedOffDate';        Display = 'Signed Off Date';        Type = 'DateTime' }
            @{ Name = 'SignoffFileID';        Display = 'Sign-off File ID';       Type = 'Number' }
            @{ Name = 'Comments';             Display = 'Comments';               Type = 'Note' }
        )
    }
    @{
        Title       = 'JP_SignoffRecords'
        Template    = 'DocumentLibrary'
        Description = 'JQC/PWI Management - signed JQCs and PWI training logs. Never delete.'
        Versioning  = $true
        Fields = @(
            @{ Name = 'AssignmentID';  Display = 'Assignment ID';  Type = 'Number'; Indexed = $true }
            @{ Name = 'DocType';       Display = 'Doc Type';       Type = 'Choice'; Choices = $docTypeChoices }
            @{ Name = 'Revision';      Display = 'Revision';       Type = 'Text' }
            @{ Name = 'EmployeeEmail'; Display = 'Employee Email'; Type = 'Text';   Indexed = $true }
            @{ Name = 'UploadedBy';    Display = 'Uploaded By';    Type = 'User' }
        )
    }
    @{
        Title       = 'JP_Settings'
        Template    = 'GenericList'
        Description = 'JQC/PWI Management - global settings. Keep exactly one row.'
        TitleDisplay = 'Title'
        Fields = @(
            # TODO: confirm defaults (CLAUDE.md Section 19)
            @{ Name = 'MinQualifiedPerTask'; Display = 'Min Qualified Per Task'; Type = 'Number'; Required = $true; Default = '2';  Min = 1 }
            @{ Name = 'ResignDueDays';       Display = 'Re-sign Due Days';       Type = 'Number'; Required = $true; Default = '14'; Min = 1 }
        )
    }
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Step([string] $Message) { Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Info([string] $Message) { Write-Host "    $Message" }

function ConvertTo-XmlText([string] $Value) {
    return [System.Security.SecurityElement]::Escape($Value)
}

function New-FieldXml {
    param([hashtable] $Field, [hashtable] $ListIds)

    # Internal names come from DisplayName when SharePoint creates a field from
    # XML, so the field is created with DisplayName = internal Name. The friendly
    # display name is applied afterwards in Set-FieldDisplayName.
    $name  = $Field.Name
    $req   = if ($Field.ContainsKey('Required') -and $Field.Required) { 'TRUE' } else { 'FALSE' }
    $attrs = "Name=`"$name`" StaticName=`"$name`" DisplayName=`"$name`" Required=`"$req`""
    $inner = ''

    switch ($Field.Type) {
        'Text'      { $xml = "<Field Type=`"Text`" $attrs MaxLength=`"255`" />" }
        'Note'      { $xml = "<Field Type=`"Note`" $attrs NumLines=`"6`" RichText=`"FALSE`" />" }
        'Number'    {
            $min = if ($Field.ContainsKey('Min')) { " Min=`"$($Field.Min)`"" } else { '' }
            $xml = "<Field Type=`"Number`" $attrs Decimals=`"0`"$min />"
        }
        'Boolean'   { $xml = "<Field Type=`"Boolean`" $attrs />" }
        'DateOnly'  { $xml = "<Field Type=`"DateTime`" $attrs Format=`"DateOnly`" />" }
        'DateTime'  { $xml = "<Field Type=`"DateTime`" $attrs Format=`"DateTime`" />" }
        'User'      { $xml = "<Field Type=`"User`" $attrs UserSelectionMode=`"PeopleOnly`" UserSelectionScope=`"0`" ShowField=`"ImnName`" />" }
        'UserMulti' { $xml = "<Field Type=`"UserMulti`" $attrs Mult=`"TRUE`" UserSelectionMode=`"PeopleOnly`" UserSelectionScope=`"0`" ShowField=`"ImnName`" />" }
        'Choice'    {
            $choices = ($Field.Choices | ForEach-Object { "<CHOICE>$(ConvertTo-XmlText $_)</CHOICE>" }) -join ''
            $inner   = "<CHOICES>$choices</CHOICES>"
            $xml     = "<Field Type=`"Choice`" $attrs Format=`"Dropdown`" FillInChoice=`"FALSE`">{INNER}</Field>"
        }
        'Lookup'    {
            $listId = $ListIds[$Field.LookupList]
            if (-not $listId) { throw "Lookup target list '$($Field.LookupList)' not found." }
            $xml = "<Field Type=`"Lookup`" $attrs List=`"{$listId}`" ShowField=`"$($Field.LookupField)`" />"
        }
        default     { throw "Unknown field type '$($Field.Type)' for $name." }
    }

    if ($Field.ContainsKey('Default')) {
        $defaultXml = "<Default>$(ConvertTo-XmlText $Field.Default)</Default>"
        if ($xml -like '*{INNER}*') {
            $inner += $defaultXml
        }
        else {
            $xml = $xml -replace ' />$', ">$defaultXml</Field>"
        }
    }
    return $xml.Replace('{INNER}', $inner)
}

function Get-FieldOrNull([string] $List, [string] $Name) {
    try { return Get-PnPField -List $List -Identity $Name -ErrorAction Stop }
    catch { return $null }
}

function Get-ListOrNull([string] $Name) {
    try { return Get-PnPList -Identity $Name -ErrorAction Stop }
    catch { return $null }
}

function Get-GroupOrNull([string] $Name) {
    try { return Get-PnPGroup -Identity $Name -ErrorAction Stop }
    catch { return $null }
}

# ---------------------------------------------------------------------------
# Connect
# ---------------------------------------------------------------------------

if (-not (Get-Module -ListAvailable -Name PnP.PowerShell)) {
    throw 'PnP.PowerShell is not installed. Run: Install-Module PnP.PowerShell -Scope CurrentUser'
}

Write-Step "Connecting to $SiteUrl"
Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId

# ---------------------------------------------------------------------------
# 1. Create lists and libraries (all first, so lookups can reference them)
# ---------------------------------------------------------------------------

Write-Step 'Creating lists and libraries'
$listIds = @{}
foreach ($def in $schema) {
    $list = Get-ListOrNull $def.Title
    if ($null -eq $list) {
        Write-Info "Creating $($def.Title)"
        $list = New-PnPList -Title $def.Title -Url $def.Title -Template $def.Template -OnQuickLaunch
    }
    else {
        Write-Info "$($def.Title) already exists"
    }
    Set-PnPList -Identity $def.Title -Description $def.Description | Out-Null
    if ($def.ContainsKey('Versioning') -and $def.Versioning) {
        Set-PnPList -Identity $def.Title -EnableVersioning $true -MajorVersions 50 | Out-Null
    }
    $listIds[$def.Title] = (Get-PnPList -Identity $def.Title).Id.Guid
}

# ---------------------------------------------------------------------------
# 2. Columns
# ---------------------------------------------------------------------------

foreach ($def in $schema) {
    Write-Step "Columns on $($def.Title)"

    if ($def.ContainsKey('TitleDisplay')) {
        Set-PnPField -List $def.Title -Identity 'Title' -Values @{ Title = $def.TitleDisplay } | Out-Null
    }

    $isLibrary = $def.Template -eq 'DocumentLibrary'
    $view      = Get-PnPView -List $def.Title -Includes ViewFields | Where-Object { $_.DefaultView } | Select-Object -First 1
    $viewFields = [System.Collections.Generic.List[string]]::new()
    foreach ($f in $view.ViewFields) { $viewFields.Add($f) }

    foreach ($field in $def.Fields) {
        $f = $field.Clone()
        if ($isLibrary) { $f.Required = $false }   # see NOTES: enforced by app + flow

        if ($null -eq (Get-FieldOrNull -List $def.Title -Name $f.Name)) {
            Write-Info "Adding $($f.Name) ($($f.Type))"
            $xml = New-FieldXml -Field $f -ListIds $listIds
            Add-PnPFieldFromXml -List $def.Title -FieldXml $xml | Out-Null
        }
        else {
            Write-Info "$($f.Name) already exists"
        }

        Set-PnPField -List $def.Title -Identity $f.Name -Values @{ Title = $field.Display } | Out-Null

        $wantIndex = ($f.ContainsKey('Indexed') -and $f.Indexed) -or ($f.ContainsKey('Unique') -and $f.Unique)
        if ($wantIndex) {
            Set-PnPField -List $def.Title -Identity $f.Name -Values @{ Indexed = $true } | Out-Null
        }
        if ($f.ContainsKey('Unique') -and $f.Unique) {
            # Must be set after Indexed. Fails if duplicate values already exist.
            Set-PnPField -List $def.Title -Identity $f.Name -Values @{ EnforceUniqueValues = $true } | Out-Null
        }

        if (-not $viewFields.Contains($f.Name)) { $viewFields.Add($f.Name) }
    }

    Set-PnPView -List $def.Title -Identity $view.Id -Fields ($viewFields.ToArray()) | Out-Null
}

# ---------------------------------------------------------------------------
# 3. Settings row (exactly one)
# ---------------------------------------------------------------------------

Write-Step 'Settings row'
$settingsItems = @(Get-PnPListItem -List 'JP_Settings' -PageSize 10)
if ($settingsItems.Count -eq 0) {
    # TODO: confirm defaults (CLAUDE.md Section 19)
    Add-PnPListItem -List 'JP_Settings' -Values @{ Title = 'Settings'; MinQualifiedPerTask = 2; ResignDueDays = 14 } | Out-Null
    Write-Info 'Created settings row (MinQualifiedPerTask = 2, ResignDueDays = 14)'
}
elseif ($settingsItems.Count -gt 1) {
    Write-Warning "JP_Settings has $($settingsItems.Count) rows. The app expects exactly one. Mark the extras clearly or remove them by hand."
}
else {
    Write-Info 'Settings row already exists (left unchanged)'
}

# ---------------------------------------------------------------------------
# 4. Optional permissions (CLAUDE.md Section 9)
# ---------------------------------------------------------------------------

if ($ConfigurePermissions) {
    Write-Step 'Configuring permissions'

    foreach ($g in @($ManagersGroup, $TechniciansGroup, $ViewersGroup)) {
        if ($null -eq (Get-GroupOrNull $g)) {
            Write-Info "Creating group '$g' (add members afterwards)"
            New-PnPGroup -Title $g | Out-Null
        }
    }

    $permissions = @{
        'JP_Employees'      = @{ $ManagersGroup = 'Contribute'; $TechniciansGroup = 'Read';       $ViewersGroup = 'Read' }
        'JP_Documents'      = @{ $ManagersGroup = 'Contribute'; $TechniciansGroup = 'Read';       $ViewersGroup = 'Read' }
        'JP_Settings'       = @{ $ManagersGroup = 'Contribute'; $TechniciansGroup = 'Read';       $ViewersGroup = 'Read' }
        'JP_Assignments'    = @{ $ManagersGroup = 'Contribute'; $TechniciansGroup = 'Contribute'; $ViewersGroup = 'Read' }
        'JP_SignoffRecords' = @{ $ManagersGroup = 'Contribute'; $TechniciansGroup = 'Contribute'; $ViewersGroup = 'Read' }
    }

    foreach ($listName in $permissions.Keys) {
        Write-Info "Breaking inheritance on $listName (existing permissions are copied)"
        Set-PnPList -Identity $listName -BreakRoleInheritance -CopyRoleAssignments | Out-Null
        foreach ($group in $permissions[$listName].Keys) {
            $role = $permissions[$listName][$group]
            # Remove any copied role first so the group ends up with exactly one role.
            foreach ($r in @('Contribute', 'Read', 'Edit')) {
                try { Set-PnPListPermission -Identity $listName -Group $group -RemoveRole $r -ErrorAction Stop | Out-Null } catch { }
            }
            Set-PnPListPermission -Identity $listName -Group $group -AddRole $role | Out-Null
            Write-Info "  $group -> $role"
        }
    }
    Write-Warning 'Technicians have Contribute on JP_Assignments and JP_SignoffRecords, so row-level rules are enforced by the app only. See SPEC.md OQ-03.'
}
else {
    Write-Info 'Skipped permissions (run again with -ConfigurePermissions to apply CLAUDE.md Section 9).'
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Step 'Done'
Write-Host ''
Write-Host 'Use these values for the solution environment variables (see /solution/env-vars.md):'
Write-Host "  jp_SiteUrl          = $SiteUrl"
Write-Host "  jp_ListEmployees    = $($listIds['JP_Employees'])"
Write-Host "  jp_LibDocuments     = $($listIds['JP_Documents'])"
Write-Host "  jp_ListAssignments  = $($listIds['JP_Assignments'])"
Write-Host "  jp_LibSignoffs      = $($listIds['JP_SignoffRecords'])"
Write-Host "  jp_ListSettings     = $($listIds['JP_Settings'])"
Write-Host ''
Write-Host 'These IDs belong to this site only. Do not commit them to the repository.'
