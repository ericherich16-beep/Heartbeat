<#
.SYNOPSIS
  Pre-delivery checks for a Power Apps solution zip. Windows PowerShell 5.1 or PowerShell 7.

.DESCRIPTION
  Runs the automatable checks from PowerApps-Build-Rules.txt (same check IDs) and writes
  a report you paste or upload into Copilot Chat. Nothing is changed and nothing is sent anywhere.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\Verify-PowerAppsPackage.ps1 -Zip .\MyApp_1_0_3_0_unmanaged.zip

.EXAMPLE
  .\Verify-PowerAppsPackage.ps1 -Zip .\MyApp.zip -PreviousVersion 1.0.2.0 -Schema .\lists.json -TenantFields .\exports -Docs .\docs

  -Schema        lists.json: every list/library, "kind" (list|library), columns with SharePoint TypeAsString.
  -TenantFields  folder of <ListName>.csv files from the real site:
                 Get-PnPField -List "<ListName>" | Select InternalName,Title,TypeAsString | Export-Csv "<ListName>.csv" -NoTypeInformation
  -Docs          folder with README / POST_IMPORT files (.md or .txt).
  -Report        where to write the report (default: <zip name>.verify.txt next to the zip).
#>
param(
    [Parameter(Mandatory = $true)][string]$Zip,
    [string]$PreviousVersion,
    [string]$Schema,
    [string]$TenantFields,
    [string]$Docs,
    [string]$BlockedOps = "HttpRequest",
    [switch]$AllowFlowItemParams,
    [string]$Report
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$script:Results = New-Object System.Collections.ArrayList
function Add-Result([string]$Id, [string]$Status, [string]$Msg) {
    [void]$script:Results.Add([pscustomobject]@{ Id = $Id; Status = $Status; Msg = $Msg })
}

# ---------- JSON that works the same in 5.1 and 7 (dictionaries, safe for big files) ----------
if ($PSVersionTable.PSVersion.Major -lt 6) { Add-Type -AssemblyName System.Web.Extensions }
function ConvertFrom-JsonText([string]$Text) {
    if ($PSVersionTable.PSVersion.Major -ge 6) {
        return ($Text | ConvertFrom-Json -AsHashtable -Depth 200)
    }
    $ser = New-Object System.Web.Script.Serialization.JavaScriptSerializer
    $ser.MaxJsonLength = [int]::MaxValue
    $ser.RecursionLimit = 1000
    return $ser.DeserializeObject($Text)
}
function G($Obj, [string]$Key) {
    if ($null -eq $Obj) { return $null }
    if ($Obj -is [System.Collections.IDictionary]) {
        if ($Obj.Contains($Key)) { return $Obj[$Key] }
        return $null
    }
    return $null
}
function Keys($Obj) {
    if ($Obj -is [System.Collections.IDictionary]) { return @($Obj.Keys) }
    return @()
}

# ---------- zip helpers ----------
function Norm([string]$n) { return ($n -replace '\\', '/').TrimStart('/') }
function Get-EntryMap($Archive) {
    $map = @{}
    foreach ($e in $Archive.Entries) { $map[(Norm $e.FullName)] = $e }
    return $map
}
function Read-EntryText($Entry) {
    $s = $Entry.Open()
    try {
        $r = New-Object System.IO.StreamReader($s, [System.Text.Encoding]::UTF8, $true)
        return $r.ReadToEnd()
    } finally { $s.Dispose() }
}
function Read-EntryBytes($Entry) {
    $s = $Entry.Open()
    try {
        $ms = New-Object System.IO.MemoryStream
        $s.CopyTo($ms)
        $ms.Position = 0
        return ,$ms
    } finally { $s.Dispose() }
}
function Strip-Strings([string]$s) { return [regex]::Replace($s, '"(?:[^"]|"")*"', '""') }

# Properties Studio accepts though the template XML doesn't list them (calibrated on an app that opened).
$ImplicitProps = @("ZIndex", "X", "Y", "Width", "Height", "Visible", "FillPortions", "AlignInContainer",
    "LayoutMinWidth", "LayoutMinHeight", "LayoutMaxWidth", "LayoutMaxHeight",
    "RadiusTopLeft", "RadiusTopRight", "RadiusBottomLeft", "RadiusBottomRight")
$Deny = @{ "button|AccessibleLabel" = "classic buttons don't support AccessibleLabel (20 import errors in Stage 2)" }
$Caution = @{ "combobox|SearchItems" = "SearchItems was rejected by the YAML loader (Stage 2) and its default points at sample column Value1; prefer a dropdown or set it explicitly and test in Studio" }

# =====================================================================================
if (-not (Test-Path $Zip)) { Write-Error "Zip not found: $Zip" }
$ZipPath = (Resolve-Path $Zip).Path
if (-not $Report) { $Report = [System.IO.Path]::ChangeExtension($ZipPath, ".verify.txt") }

$za = $null
try { $za = [System.IO.Compression.ZipFile]::OpenRead($ZipPath) }
catch { Add-Result "PKG-01" "FAIL" "not a zip file: $($_.Exception.Message)" }

$ctx = $null
if ($za) {
    $map = Get-EntryMap $za
    # ---------------- PKG-01 ----------------
    $need = @("solution.xml", "customizations.xml", "[Content_Types].xml")
    $missing = @($need | Where-Object { -not $map.ContainsKey($_) })
    if ($missing.Count -eq 0) {
        Add-Result "PKG-01" "PASS" "solution zip layout: solution.xml, customizations.xml and [Content_Types].xml at the root"
        $nested = @($map.Keys | Where-Object { $_ -like "*.zip" })
        if ($nested.Count) { Add-Result "PKG-01" "FAIL" "zip contains another zip ($($nested -join ', ')); give the user the solution zip itself" }
        $ok = $true
    } else {
        $hint = ""
        if (@($map.Keys | Where-Object { $_ -like "*.msapp" }).Count) { $hint = " It looks like a zipped .msapp: 'Import canvas app' rejects that with 'manifest file could not be found'." }
        Add-Result "PKG-01" "FAIL" ("missing at zip root: " + ($missing -join ", ") + "." + $hint)
        $ok = $false
    }

    if ($ok) {
        [xml]$sol = Read-EntryText $map["solution.xml"]
        [xml]$cust = Read-EntryText $map["customizations.xml"]
        $ver = "$($sol.SelectSingleNode('//Version').InnerText)".Trim()
        $rcs = @($sol.SelectNodes('//RootComponent'))
        $apps = @{}
        foreach ($ca in $cust.SelectNodes('//CanvasApps/CanvasApp')) { $apps[$ca.SelectSingleNode('Name').InnerText] = $ca }
        $wfs = @{}
        foreach ($w in $cust.SelectNodes('//Workflows/Workflow')) { $wfs[$w.GetAttribute('WorkflowId').Trim('{', '}').ToLower()] = $w }
        $connrefs = @{}
        foreach ($c in $cust.SelectNodes('//connectionreferences/connectionreference')) { $connrefs[$c.GetAttribute('connectionreferencelogicalname')] = $c }

        # ---------------- PKG-02 ----------------
        $bad = @()
        $rcKeys = @()
        foreach ($rc in $rcs) {
            $t = $rc.GetAttribute('type')
            $key = $rc.GetAttribute('schemaName'); if (-not $key) { $key = $rc.GetAttribute('id') }
            $rcKeys += "$t|$key"
            if ($t -eq "300") {
                if (-not $apps.ContainsKey($key)) {
                    $bad += "canvas app $key is a root component but customizations.xml has no <CanvasApp> for it (import error 'Cannot add a Root Component ... of type 300')"
                } else {
                    $uri = Norm $apps[$key].SelectSingleNode('DocumentUri').InnerText
                    if (-not $map.ContainsKey($uri)) { $bad += "canvas app ${key}: DocumentUri file $uri missing from zip" }
                }
            } elseif ($t -eq "29") {
                $wid = $key.Trim('{', '}').ToLower()
                if (-not $wfs.ContainsKey($wid)) { $bad += "workflow $key missing from customizations.xml" }
                else {
                    $jf = Norm $wfs[$wid].SelectSingleNode('JsonFileName').InnerText
                    if (-not $map.ContainsKey($jf)) { $bad += "workflow ${key}: JSON file $jf missing from zip" }
                }
            } elseif ($t -eq "380") {
                $prefix = "environmentvariabledefinitions/$($key.ToLower())/"
                if (-not @($map.Keys | Where-Object { $_.ToLower().StartsWith($prefix) }).Count) { $bad += "environment variable ${key}: definition missing from zip" }
            }
        }
        foreach ($n in $apps.Keys) { if ($rcKeys -notcontains "300|$n") { $bad += "canvas app $n is in customizations.xml but is not a root component" } }
        if ($bad.Count) { foreach ($b in $bad) { Add-Result "PKG-02" "FAIL" $b } }
        else { Add-Result "PKG-02" "PASS" "all $($rcs.Count) root components are present in the zip" }

        # ---------------- PKG-03 ----------------
        if ($ver -notmatch '^\d+\.\d+\.\d+\.\d+$') { Add-Result "PKG-03" "FAIL" "solution version '$ver' is not 4-part" }
        elseif ($PreviousVersion) {
            if ([version]$ver -gt [version]$PreviousVersion) { Add-Result "PKG-03" "PASS" "version $ver is higher than $PreviousVersion" }
            else { Add-Result "PKG-03" "FAIL" "version $ver is not higher than ${PreviousVersion}: bump it, or the upgrade import does nothing" }
        } else { Add-Result "PKG-03" "WARN" "version $ver; pass -PreviousVersion to confirm it was bumped" }

        # environment variables
        $envvars = @{}
        foreach ($k in $map.Keys) {
            $m = [regex]::Match($k, '^environmentvariabledefinitions/([^/]+)/environmentvariabledefinition\.xml$', 'IgnoreCase')
            if ($m.Success) {
                [xml]$ev = Read-EntryText $map[$k]
                $envvars[$m.Groups[1].Value] = $ev
                $dv = $ev.SelectSingleNode('//defaultvalue')
                if ($dv -and $dv.InnerText -match 'sharepoint\.com' -and $dv.InnerText -notmatch 'contoso') {
                    Add-Result "APP-11" "FAIL" "environment variable $($m.Groups[1].Value) ships a real default value; leave it empty so the import wizard asks"
                }
            }
        }

        # ---------------- FLOWS ----------------
        $blocked = @($BlockedOps -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
        foreach ($wid in $wfs.Keys) {
            $w = $wfs[$wid]
            $name = $w.GetAttribute('Name')
            $jf = Norm $w.SelectSingleNode('JsonFileName').InnerText
            if (-not $map.ContainsKey($jf)) { continue }
            $raw = Read-EntryText $map[$jf]
            $flow = ConvertFrom-JsonText $raw
            $props = G $flow 'properties'
            $def = G $props 'definition'
            $isAppFlow = $false
            $trigs = G $def 'triggers'
            foreach ($tk in (Keys $trigs)) { $kind = G $trigs[$tk] 'kind'; if ($kind -eq 'PowerAppV2' -or $kind -eq 'PowerApp') { $isAppFlow = $true } }

            # collect all actions (nested scopes, conditions, switches)
            $all = New-Object System.Collections.ArrayList
            $queue = New-Object System.Collections.Queue
            $queue.Enqueue((G $def 'actions'))
            while ($queue.Count) {
                $acts = $queue.Dequeue()
                foreach ($ak in (Keys $acts)) {
                    $a = $acts[$ak]
                    [void]$all.Add(@($ak, $a))
                    if (G $a 'actions') { $queue.Enqueue((G $a 'actions')) }
                    $elseB = G $a 'else'; if ($elseB -and (G $elseB 'actions')) { $queue.Enqueue((G $elseB 'actions')) }
                    $dflt = G $a 'default'; if ($dflt -and (G $dflt 'actions')) { $queue.Enqueue((G $dflt 'actions')) }
                    $cases = G $a 'cases'; foreach ($ck in (Keys $cases)) { $ca2 = G $cases[$ck] 'actions'; if ($ca2) { $queue.Enqueue($ca2) } }
                }
            }
            $f1 = @(); $f2 = @(); $f5 = @()
            foreach ($pair in $all) {
                $ak = $pair[0]; $a = $pair[1]
                $inp = G $a 'inputs'
                $host1 = G $inp 'host'
                $op = "$(G $host1 'operationId')"
                $api = "$(G $host1 'apiId')$(G $host1 'connectionName')"
                if ($blocked -contains $op) { $f1 += "${ak}: operation $op is blocked by the tenant data policy" }
                $type = "$(G $a 'type')"
                if ($type -eq 'Http' -or $type -eq 'HttpWebhook') { $f1 += "${ak}: HTTP action is a premium connector" }
                if ($api -match 'commondataservice') { $f1 += "${ak}: Dataverse connector is premium" }
                $params = G $inp 'parameters'
                $itemParams = @((Keys $params) | Where-Object { $_ -like 'item/*' })
                if ($itemParams.Count -and -not $AllowFlowItemParams) {
                    $f2 += "$ak ($op): sets list columns ($(($itemParams | Select-Object -First 4) -join ', ')...). Power Automate checks these against the real list when the flow is turned on"
                }
                if ($isAppFlow -and $type -eq 'OpenApiConnection' -and $api -notmatch 'sharepoint') {
                    $hasRetry = $null -ne (G $inp 'retryPolicy')
                    $hasTimeout = $null -ne (G (G $a 'limit') 'timeout')
                    if (-not ($hasRetry -and $hasTimeout)) { $f5 += "$ak ($api): no retryPolicy none / timeout; a failing call keeps the app on 'Saving...' for minutes" }
                }
            }
            if ($f1.Count) { foreach ($x in $f1) { Add-Result "FLOW-01" "FAIL" "flow '$name': $x" } } else { Add-Result "FLOW-01" "PASS" "flow '$name': no blocked or premium actions" }
            if ($f2.Count) { foreach ($x in $f2) { Add-Result "FLOW-02" "FAIL" "flow '$name': $x" } } else { Add-Result "FLOW-02" "PASS" "flow '$name': doesn't set list columns" }
            if ($f5.Count) { foreach ($x in $f5) { Add-Result "FLOW-05" "WARN" "flow '$name': $x" } } else { Add-Result "FLOW-05" "PASS" "flow '$name'" }

            $miss = @()
            $crs = G $props 'connectionReferences'
            foreach ($ck in (Keys $crs)) {
                $ln = G (G $crs[$ck] 'connection') 'connectionReferenceLogicalName'
                if (-not $ln -or -not $connrefs.ContainsKey($ln)) { $miss += "$ck -> $ln" }
            }
            if ($miss.Count) { Add-Result "FLOW-03" "FAIL" "flow '$name': connection references not defined in the solution: $($miss -join '; ')" }
            else { Add-Result "FLOW-03" "PASS" "flow '$name': every connection reference is defined in the solution" }

            $ph = @([regex]::Matches($raw, 'REPLACE_[A-Z_]+|TODO[:\s][^"]{0,30}|<your[^>"]*>') | ForEach-Object { $_.Value } | Sort-Object -Unique)
            if ($ph.Count) { Add-Result "FLOW-04" "WARN" "flow '$name': placeholders the user must replace after import: $($ph -join ', '). Say so in POST_IMPORT, or ask for the real value" }
            else { Add-Result "FLOW-04" "PASS" "flow '$name': no placeholders" }

            if ($w.SelectSingleNode('StateCode') -and $w.SelectSingleNode('StateCode').InnerText -ne '1') { Add-Result "FLOW-07" "WARN" "flow '$name' ships turned off: POST_IMPORT must say to turn it on" }
            else { Add-Result "FLOW-07" "MANUAL" "flow '$name' ships on, but stays off if its connection wasn't picked at import: POST_IMPORT must say to check" }
        }

        # ---------------- CANVAS APPS ----------------
        foreach ($appName in $apps.Keys) {
            $ca = $apps[$appName]
            $tag = "[$appName] "
            $uri = Norm $ca.SelectSingleNode('DocumentUri').InnerText
            if (-not $map.ContainsKey($uri)) { continue }
            $ms = Read-EntryBytes $map[$uri]
            try { $mz = New-Object System.IO.Compression.ZipArchive($ms, [System.IO.Compression.ZipArchiveMode]::Read) }
            catch { Add-Result "PKG-04" "FAIL" ($tag + ".msapp can't be opened as a zip"); continue }
            $mmap = Get-EntryMap $mz
            $ctrlFiles = @($mmap.Keys | Where-Object { $_ -like 'Controls/*.json' })
            $yamlFiles = @($mmap.Keys | Where-Object { $_ -like 'Src/*.yaml' })
            $missingM = @(@("Header.json", "Properties.json") | Where-Object { -not $mmap.ContainsKey($_) })
            if ($missingM.Count -or -not ($ctrlFiles.Count -or $yamlFiles.Count)) {
                Add-Result "PKG-04" "FAIL" ($tag + ".msapp is missing Header.json/Properties.json or has no controls"); continue
            }
            $hdr = ConvertFrom-JsonText (Read-EntryText $mmap["Header.json"])
            Add-Result "PKG-04" "PASS" ($tag + ".msapp structure OK (DocVersion $(G $hdr 'DocVersion'), $($ctrlFiles.Count) control files)")
            Add-Result "PKG-04" "MANUAL" ($tag + "Header/Properties/References came from a Studio-saved or pac-unpacked real app, not written by hand (ErrOpeningDocument_UnknownError)")
            if (-not $ctrlFiles.Count) {
                Add-Result "APP-00" "WARN" ($tag + "load-from-YAML package: structural checks skipped; run pac canvas unpack and paste the screens into Copilot"); continue
            }

            $templates = @{}
            if ($mmap.ContainsKey("References/Templates.json")) {
                $tj = ConvertFrom-JsonText (Read-EntryText $mmap["References/Templates.json"])
                foreach ($u in @(G $tj 'UsedTemplates')) {
                    $set = @{}
                    foreach ($mm in [regex]::Matches("$(G $u 'Template')", 'name="([A-Za-z0-9]+)"')) { $set[$mm.Groups[1].Value] = $true }
                    $templates["$(G $u 'Name')"] = $set
                }
            }
            $dsList = @()
            if ($mmap.ContainsKey("References/DataSources.json")) { $dsList = @(G (ConvertFrom-JsonText (Read-EntryText $mmap["References/DataSources.json"])) 'DataSources') }
            $spSources = @($dsList | Where-Object { (G $_ 'Type') -eq 'ConnectedDataSourceInfo' -and "$(G $_ 'ApiId')" -match 'sharepoint' })
            $flowSources = @($dsList | Where-Object { "$(G $_ 'ApiId')" -match 'logicflows' })

            # flatten controls with their parents' template names
            $controls = New-Object System.Collections.ArrayList
            foreach ($cf in $ctrlFiles) {
                $top = G (ConvertFrom-JsonText (Read-EntryText $mmap[$cf])) 'TopParent'
                $stack = New-Object System.Collections.Stack
                $stack.Push(@($top, @()))
                while ($stack.Count) {
                    $item = $stack.Pop()
                    $node = $item[0]; $parents = $item[1]
                    [void]$controls.Add(@($node, $parents))
                    $tn = "$(G (G $node 'Template') 'Name')"
                    foreach ($ch in @(G $node 'Children')) { if ($ch) { $stack.Push(@($ch, @($parents + $tn))) } }
                }
            }
            $names = @{}
            foreach ($c in $controls) { $names["$(G $c[0] 'Name')"] = $true }

            $iss = @{ "APP-01" = @(); "APP-01w" = @(); "APP-02" = @(); "APP-03" = @(); "APP-04" = @(); "APP-05" = @(); "APP-06" = @(); "APP-07" = @(); "APP-08" = @(); "APP-11" = @() }
            foreach ($c in $controls) {
                $node = $c[0]; $parents = $c[1]
                $nm = "$(G $node 'Name')"
                $tn = "$(G (G $node 'Template') 'Name')"
                $rules = @{}
                foreach ($r in @(G $node 'Rules')) { if ($r) { $rules["$(G $r 'Property')"] = "$(G $r 'InvariantScript')" } }

                foreach ($p in $rules.Keys) {
                    $k = "$tn|$p"
                    if ($Deny.ContainsKey($k)) { $iss["APP-01"] += "$nm.${p}: $($Deny[$k])" }
                    elseif ($Caution.ContainsKey($k)) { $iss["APP-01w"] += "$nm.${p}: $($Caution[$k])" }
                    elseif ($templates.ContainsKey($tn) -and -not $templates[$tn].ContainsKey($p) -and $ImplicitProps -notcontains $p -and -not $p.StartsWith('#')) {
                        $iss["APP-01"] += "$nm.${p}: not a property of template '$tn'"
                    }
                }
                if ($tn -eq 'screen') {
                    foreach ($p in @('Width', 'Height')) {
                        if (-not $rules.ContainsKey($p) -or -not $rules[$p].Trim()) { $iss["APP-03"] += "${nm}: no $p rule (Studio sizes it 0x0 and the screen looks blank)" }
                    }
                }
                if (@('text', 'dropdown', 'combobox', 'datepicker') -contains $tn -and -not $rules.ContainsKey('Fill')) { $iss["APP-04"] += "$nm (${tn}): no Fill rule; Studio draws it black" }
                if ($tn -eq 'label' -and -not $rules.ContainsKey('Color')) { $iss["APP-04"] += "$nm (label): no Color rule" }
                if ($tn -eq 'gallery' -and -not $rules.ContainsKey('Layout')) { $iss["APP-05"] += "${nm}: no Layout rule; the default is Horizontal (lists render sideways)" }
                if ($tn -eq 'attachments') {
                    $inForm = @($parents | Where-Object { @('form', 'typedDataCard', 'dataCard') -contains $_ }).Count -gt 0
                    if (-not $inForm) {
                        $b = @()
                        if ("$($rules['DisplayMode'])" -notmatch 'DisplayMode\.Edit') { $b += "DisplayMode=DisplayMode.Edit" }
                        if ("$($rules['IsInDataCard'])".Trim().ToLower() -ne 'true') { $b += "IsInDataCard=true" }
                        if (-not $rules.ContainsKey('Items')) { $b += "Items" }
                        if ($b.Count) { $iss["APP-06"] += "${nm}: outside a form and missing $($b -join ', '); it shows only 'No file selected'" }
                    }
                }
                $ownDigits = @([regex]::Matches($nm, '\d+') | ForEach-Object { $_.Value })
                foreach ($p in $rules.Keys) {
                    $f = $rules[$p]
                    $s = Strip-Strings $f
                    foreach ($mm in [regex]::Matches($s, "(?<![\w.'])Value\d+\b")) { $iss["APP-02"] += "$nm.${p}: refers to sample column '$($mm.Value)'" }
                    foreach ($mm in [regex]::Matches($s, "(?<![!<>=\w])!\s*(?!\()([A-Za-z_'][\w.']*(?:\([^()]*\))?)\s*(=|<>)(?!=)")) {
                        $iss["APP-07"] += "$nm.${p}: '!$($mm.Groups[1].Value) $($mm.Groups[2].Value) ...' negates before comparing; write !( ... ) or Not( ... )"
                    }
                    foreach ($mm in [regex]::Matches($f, 'https?://[\w.-]+\.sharepoint\.com[^"\s]*')) {
                        if ($mm.Value -notmatch 'contoso') { $iss["APP-11"] += "$nm.${p}: hard-coded site '$($mm.Value)'" }
                    }
                    if ($ownDigits.Count -and -not $nm.EndsWith('template1')) {
                        $refs = @([regex]::Matches($s, '[A-Za-z_][A-Za-z0-9_]*') | ForEach-Object { $_.Value } | Sort-Object -Unique | Where-Object { $names.ContainsKey($_) -and $_ -ne $nm })
                        foreach ($ref in $refs) {
                            foreach ($dm in [regex]::Matches($ref, '\d+')) {
                                if ($ownDigits -contains $dm.Value) { continue }
                                foreach ($d in $ownDigits) {
                                    $alt = $ref.Substring(0, $dm.Index) + $d + $ref.Substring($dm.Index + $dm.Length)
                                    if ($alt -ne $ref -and $names.ContainsKey($alt)) { $iss["APP-08"] += "$nm.$p uses $ref, but $alt exists (copied from the other set?)" }
                                }
                            }
                        }
                    }
                }
            }
            foreach ($cid in @("APP-01", "APP-01w", "APP-02", "APP-03", "APP-04", "APP-05", "APP-06", "APP-07", "APP-08", "APP-11")) {
                $list = @($iss[$cid] | Sort-Object -Unique)
                $id = $cid -replace 'w$', ''
                $status = "FAIL"; if ($cid -eq "APP-01w" -or $cid -eq "APP-08") { $status = "WARN" }
                if ($list.Count) {
                    foreach ($x in ($list | Select-Object -First 25)) { Add-Result $id $status ($tag + $x) }
                    if ($list.Count -gt 25) { Add-Result $id $status ($tag + "... and $($list.Count - 25) more") }
                } elseif ($cid -ne "APP-01w") { Add-Result $id "PASS" ($tag + "$($controls.Count) controls checked") }
            }

            # APP-12 data sources bound to environment variables
            $crText = "$($ca.SelectSingleNode('ConnectionReferences').InnerText)"
            $bound = @{}
            if ($crText.Trim()) {
                $cr = ConvertFrom-JsonText $crText
                foreach ($ck in (Keys $cr)) {
                    $sets = G $cr[$ck] 'dataSets'
                    foreach ($sk in (Keys $sets)) {
                        $siteEv = G (G $sets[$sk] 'datasetOverride') 'environmentVariableName'
                        $dss = G $sets[$sk] 'dataSources'
                        foreach ($dk in (Keys $dss)) {
                            $tblEv = G (G $dss[$dk] 'tableNameOverride') 'environmentVariableName'
                            if ($siteEv -and $tblEv -and $envvars.ContainsKey($siteEv) -and $envvars.ContainsKey($tblEv)) { $bound[$dk] = $true }
                        }
                    }
                }
            }
            $unbound = @($spSources | ForEach-Object { "$(G $_ 'Name')" } | Where-Object { -not $bound.ContainsKey($_) })
            if ($unbound.Count) { Add-Result "APP-12" "FAIL" ($tag + "SharePoint sources not bound to environment variables: $($unbound -join ', ')") }
            else { Add-Result "APP-12" "PASS" ($tag + "$($spSources.Count) SharePoint sources bound to environment variables") }

            # APP-13 flow source points at a flow in this solution
            $cds = "$($ca.SelectSingleNode('CdsDependencies').InnerText)".ToLower()
            foreach ($fs in $flowSources) {
                $fid = "$(G $fs 'WorkflowEntityId')"; if (-not $fid) { $fid = "$(G $fs 'FlowNameId')" }
                $fid = $fid.ToLower()
                if ($wfs.ContainsKey($fid) -and $cds.Contains($fid)) { Add-Result "APP-13" "PASS" ($tag + "flow source '$(G $fs 'Name')' points at workflow $fid in this solution") }
                else { Add-Result "APP-13" "FAIL" ($tag + "flow source '$(G $fs 'Name')' -> $fid is not in this solution / CdsDependencies; 'Run' won't resolve after import") }
            }
            if ($flowSources.Count) { Add-Result "APP-13" "MANUAL" ($tag + "POST_IMPORT includes: if App checker says the flow has no Run, remove and re-add it in the Power Automate pane") }

            # APP-14 embedded list definitions vs schema
            if ($Schema) {
                $sch = ConvertFrom-JsonText (Get-Content $Schema -Raw)
                foreach ($d in $spSources) {
                    $dn = "$(G $d 'Name')"
                    $lst = G $sch $dn
                    if (-not $lst) { Add-Result "APP-14" "FAIL" ($tag + "data source $dn is not in the schema file"); continue }
                    $meta = G $d 'DataEntityMetadataJson'
                    $mv = $null; foreach ($mk in (Keys $meta)) { $mv = $meta[$mk]; break }
                    if ($mv -is [string]) { $mv = ConvertFrom-JsonText $mv }
                    $props2 = G (G (G $mv 'schema') 'items') 'properties'
                    $before = @($script:Results | Where-Object { $_.Status -eq 'FAIL' }).Count
                    $cols = G $lst 'columns'
                    foreach ($col in (Keys $cols)) {
                        $pv = G $props2 $col
                        if (-not $pv) { Add-Result "APP-14" "FAIL" ($tag + "$dn.${col}: in schema but not in the app's embedded definition"); continue }
                        $t = "$(G $pv 'type')"; $fmt = "$(G $pv 'format')"
                        $sub = G $pv 'properties'; if (-not $sub) { $sub = G (G $pv 'items') 'properties' }
                        $got = switch ($t) {
                            'boolean' { @('Boolean') }
                            'number' { @('Number', 'Currency', 'Integer', 'Counter') }
                            'integer' { @('Number', 'Currency', 'Integer', 'Counter') }
                            'string' { if ($fmt -eq 'date' -or $fmt -eq 'date-time') { @('DateTime') } else { @('Text', 'Note', 'URL') } }
                            default {
                                if ((Keys $sub) -contains 'Claims') { if ($t -eq 'array') { @('UserMulti') } else { @('User') } }
                                elseif ($t -eq 'array') { @('MultiChoice', 'LookupMulti') } else { @('Choice', 'Lookup') }
                            }
                        }
                        if ($got -notcontains $cols[$col]) { Add-Result "APP-14" "FAIL" ($tag + "$dn.${col}: app expects $($got -join '/'), schema says $($cols[$col])") }
                    }
                    if (@($script:Results | Where-Object { $_.Status -eq 'FAIL' }).Count -eq $before) { Add-Result "APP-14" "PASS" ($tag + "${dn}: embedded definition matches the schema") }
                }
            }
            Add-Result "PKG-05" "MANUAL" ($tag + "round trip: pac canvas unpack, then pac canvas pack, then confirm no formula changed")
            $mz.Dispose()
        }
        $ctx = $true
    }
    $za.Dispose()
}

# ---------------- SharePoint schema / real site ----------------
if ($Schema) {
    $sch = ConvertFrom-JsonText (Get-Content $Schema -Raw)
    $badNames = @(); $noKind = @()
    foreach ($l in (Keys $sch)) {
        $kind = G $sch[$l] 'kind'
        if ($kind -ne 'list' -and $kind -ne 'library') { $noKind += $l }
        foreach ($c in (Keys (G $sch[$l] 'columns'))) { if ($c -match '^field_\d+$' -or $c -match '\s') { $badNames += "$l.$c" } }
    }
    if ($badNames.Count) { Add-Result "SP-01" "FAIL" "schema internal names not safe: $($badNames -join ', ')" } else { Add-Result "SP-01" "PASS" "schema internal names are plain identifiers" }
    if ($noKind.Count) { Add-Result "SP-02" "FAIL" "no kind (list/library) for: $($noKind -join ', ')" } else { Add-Result "SP-02" "PASS" "every entry says list or library" }

    if ($TenantFields) {
        foreach ($l in (Keys $sch)) {
            $before = @($script:Results | Where-Object { $_.Status -eq 'FAIL' }).Count
            $p = Join-Path $TenantFields "$l.csv"
            if (-not (Test-Path $p)) { Add-Result "SP-03" "FAIL" "${l}: no export at $p (list not created yet?)"; continue }
            $rows = @(Import-Csv $p)
            $real = @{}; foreach ($r in $rows) { $real[$r.InternalName] = $r }
            $isLib = $real.ContainsKey('FileLeafRef')
            $kind = G $sch[$l] 'kind'
            if (($kind -eq 'library') -ne $isLib) {
                $site = 'list'; if ($isLib) { $site = 'library' }
                Add-Result "SP-02" "FAIL" "${l}: schema says $kind but the site has a $site; recreate it (the environment variable can't be changed after import)"
            }
            $cols = G $sch[$l] 'columns'
            foreach ($col in (Keys $cols)) {
                $want = $cols[$col]
                if (-not $real.ContainsKey($col)) {
                    $alt = @($rows | Where-Object { $_.Title -eq $col } | ForEach-Object { $_.InternalName })
                    $extra = ""; if ($alt.Count) { $extra = " (a column titled $col exists with internal name $($alt -join ', '): it was created under another name or by Excel import)" }
                    Add-Result "SP-03" "FAIL" "$l.${col}: missing on the site$extra"
                } elseif ($real[$col].TypeAsString -ne $want) {
                    Add-Result "SP-03" "FAIL" "$l.${col}: site type $($real[$col].TypeAsString), needs $want"
                } elseif ($real[$col].Title -ne $col) {
                    Add-Result "SP-03" "WARN" "$l.${col}: display name '$($real[$col].Title)' differs; formulas use display names after Refresh"
                }
            }
            $dups = @($rows | Group-Object Title | Where-Object { $_.Count -gt 1 -and (Keys $cols) -contains $_.Name } | ForEach-Object { $_.Name })
            if ($dups.Count) { Add-Result "SP-03" "FAIL" "${l}: duplicate display names $($dups -join ', ')" }
            if (@($script:Results | Where-Object { $_.Status -eq 'FAIL' }).Count -eq $before) { Add-Result "SP-03" "PASS" "${l}: matches the real site" }
        }
    } else {
        Add-Result "SP-03" "MANUAL" "real site not compared: export each list's fields and re-run with -TenantFields"
    }
} else {
    Add-Result "SP-01" "MANUAL" "no -Schema: write lists.json (every list/library, kind, internal names = display names, types)"
}

# ---------------- docs ----------------
if ($Docs) {
    $text = (Get-ChildItem $Docs -Recurse -Include *.md, *.txt | ForEach-Object { Get-Content $_.FullName -Raw }) -join "`n"
    $steps = [ordered]@{
        "import route (Solutions > Import solution)" = 'Import solution'
        "don't unzip"                               = "(?i)(don.?t|do not) unzip"
        "bind connection references"                = '(?i)connection'
        "fill in environment variables"             = '(?i)environment variable'
        "turn the flow on"                          = '(?i)turn on'
        "refresh data sources after import"         = '(?i)refresh'
        "re-add the flow if Run is missing"         = '(?i)(re-?add|add flow|remove.{0,40}add)'
        "App checker before publish"                = '(?i)app checker'
        "Dataverse prerequisite"                    = '(?i)dataverse'
    }
    foreach ($k in $steps.Keys) {
        if ($text -match $steps[$k]) { Add-Result "DOC-01" "PASS" "docs cover: $k" } else { Add-Result "DOC-01" "FAIL" "docs cover: $k (missing)" }
    }
    if ($text -match '(?i)import canvas app' -and $text -notmatch "(?i)(don.?t|not|never)[^.\n]{0,60}import canvas app") {
        Add-Result "DOC-02" "FAIL" "docs point to 'Import canvas app'; it only takes exported packages with manifest.json"
    } else { Add-Result "DOC-02" "PASS" "docs don't send the user to 'Import canvas app'" }
} else {
    Add-Result "DOC-01" "MANUAL" "no -Docs: POST_IMPORT steps not checked"
}

Add-Result "RUN-01" "MANUAL" "formulas tested against sample data, including a row with blank metadata (files added straight in SharePoint must still show)"
Add-Result "RUN-02" "MANUAL" "every change made in Studio since the last zip was copied back into the source (a re-import overwrites the app)"
Add-Result "RUN-03" "MANUAL" "SharePoint queries are delegable (APP-09): ask Copilot to review each Filter/LookUp on a SharePoint list"

# ---------------- report ----------------
$order = @{ FAIL = 0; WARN = 1; MANUAL = 2; PASS = 3 }
$lines = @("Power Apps package check: $(Split-Path $ZipPath -Leaf)", "Run: $(Get-Date -Format 'yyyy-MM-dd HH:mm')", "")
foreach ($r in ($script:Results | Sort-Object @{ Expression = { $order[$_.Status] } }, Id)) { $lines += ("{0,-6} {1,-7} {2}" -f $r.Status, $r.Id, $r.Msg) }
$cnt = @{}; foreach ($s in $order.Keys) { $cnt[$s] = @($script:Results | Where-Object { $_.Status -eq $s }).Count }
$lines += ""
$lines += "$($cnt.FAIL) FAIL, $($cnt.WARN) WARN, $($cnt.MANUAL) MANUAL, $($cnt.PASS) PASS"
$lines | Set-Content -Path $Report -Encoding UTF8
$lines | ForEach-Object {
    if ($_ -like 'FAIL*') { Write-Host $_ -ForegroundColor Red }
    elseif ($_ -like 'WARN*') { Write-Host $_ -ForegroundColor Yellow }
    else { Write-Host $_ }
}
Write-Host "`nReport saved to $Report (upload or paste it into Copilot Chat)." -ForegroundColor Cyan
if ($cnt.FAIL -gt 0) { exit 1 } else { exit 0 }
