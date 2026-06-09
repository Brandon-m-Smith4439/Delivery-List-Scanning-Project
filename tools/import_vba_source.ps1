param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,

    [Parameter(Mandatory = $true)]
    [string]$WorkbookName,

    [string]$SourceRoot = "VBA Source",

    [string[]]$Files = @(),

    [string]$FilesCsv = "",

    [string]$OpenPassword = "",

    [string]$WritePassword = "",

    [switch]$CreateBackup = $true,

    [switch]$ValidateInputsOnly,

    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
    param([string]$PathText)

    if ([System.IO.Path]::IsPathRooted($PathText)) {
        return [System.IO.Path]::GetFullPath($PathText)
    }

    return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $PathText))
}

function Get-ComponentNameFromSource {
    param(
        [string]$SourceText,
        [string]$FallbackName
    )

    $match = [regex]::Match($SourceText, '(?m)^Attribute\s+VB_Name\s*=\s*"([^"]+)"\s*$')
    if ($match.Success) {
        return $match.Groups[1].Value
    }

    return $FallbackName
}

function Remove-VbaAttributeLines {
    param([string]$SourceText)

    $text = $SourceText -replace "^\uFEFF", ""
    $text = [regex]::Replace($text, '(?m)^Attribute\s+VB_[^\r\n]*(\r?\n)?', '')
    $text = $text -replace "^\s*(\r?\n)+", ""
    return $text
}

function Get-VbComponent {
    param(
        [object]$Components,
        [string]$Name
    )

    try {
        return $Components.Item($Name)
    } catch {
        return $null
    }
}

function Replace-CodeModuleText {
    param(
        [object]$Component,
        [string]$CodeText
    )

    $module = $Component.CodeModule
    $lineCount = [int]$module.CountOfLines
    if ($lineCount -gt 0) {
        $module.DeleteLines(1, $lineCount)
    }
    if ($CodeText.Trim().Length -gt 0) {
        $module.AddFromString($CodeText)
    }
}

function New-StandardComponent {
    param(
        [object]$Components,
        [string]$ComponentName,
        [string]$Extension
    )

    # VBIDE component types:
    # 1 = standard module, 2 = class module, 3 = MSForm, 100 = document module.
    switch ($Extension.ToLowerInvariant()) {
        ".bas" { $type = 1 }
        ".cls" { $type = 2 }
        default {
            throw "Cannot create missing component '$ComponentName' from '$Extension'. Create forms/document modules in Excel first, then sync their code."
        }
    }

    $component = $Components.Add($type)
    $component.Name = $ComponentName
    return $component
}

$projectRootPath = Resolve-ProjectPath $ProjectRoot
$workbookPath = Join-Path $projectRootPath $WorkbookName
if (-not (Test-Path -LiteralPath $workbookPath)) {
    throw "Workbook not found: $workbookPath"
}

$sourceRootPath = $SourceRoot
if (-not [System.IO.Path]::IsPathRooted($sourceRootPath)) {
    $sourceRootPath = Join-Path $projectRootPath $SourceRoot
}

$sourceFolderName = [System.IO.Path]::GetFileNameWithoutExtension($WorkbookName)
$sourceFolder = Join-Path $sourceRootPath $sourceFolderName
if (-not (Test-Path -LiteralPath $sourceFolder)) {
    throw "Source folder not found: $sourceFolder"
}

if ($FilesCsv.Trim().Length -gt 0) {
    $Files = @($FilesCsv -split '\|' | Where-Object { $_.Trim().Length -gt 0 } | ForEach-Object { $_.Trim() })
}

$sourceFiles = Get-ChildItem -LiteralPath $sourceFolder -File |
    Where-Object { $_.Extension -in ".bas", ".cls", ".frm" } |
    Sort-Object Name

if ($Files.Count -gt 0) {
    $wanted = @{}
    foreach ($fileName in $Files) {
        $wanted[$fileName.ToLowerInvariant()] = $true
        $wanted[[System.IO.Path]::GetFileNameWithoutExtension($fileName).ToLowerInvariant()] = $true
    }

    $sourceFiles = @($sourceFiles | Where-Object {
        $wanted.ContainsKey($_.Name.ToLowerInvariant()) -or
        $wanted.ContainsKey($_.BaseName.ToLowerInvariant())
    })
}

if ($sourceFiles.Count -eq 0) {
    throw "No VBA source files found in $sourceFolder"
}

if ($ValidateInputsOnly) {
    Write-Host ("Validated source folder: {0}" -f $sourceFolder)
    Write-Host ("Selected source files: {0}" -f (($sourceFiles | Select-Object -ExpandProperty Name) -join ", "))
    exit 0
}

# Excel/VBIDE expose late-bound COM objects. PowerShell StrictMode can reject
# their dynamic properties even when Excel exposes them correctly.
Set-StrictMode -Off

$backupPath = $null
if ($CreateBackup -and -not $DryRun) {
    $backupDir = Join-Path $projectRootPath "Backups\VBA Sync Backups"
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupName = "{0}__before_vba_import_{1}{2}" -f [System.IO.Path]::GetFileNameWithoutExtension($WorkbookName), $timestamp, [System.IO.Path]::GetExtension($WorkbookName)
    $backupPath = Join-Path $backupDir $backupName
    Copy-Item -LiteralPath $workbookPath -Destination $backupPath -Force
}

$changes = New-Object System.Collections.Generic.List[object]
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false

try {
    # Disable workbook events only for the open call so Workbook_Open does not
    # start queue processing. Re-enable before touching VBIDE; Excel exposes
    # VBComponents reliably after events are restored.
    $previousEnableEvents = $xl.EnableEvents
    try {
        $xl.EnableEvents = $false
        if (($OpenPassword.Length -gt 0) -or ($WritePassword.Length -gt 0)) {
            $workbook = $xl.Workbooks.Open($workbookPath, 0, $false, 5, $OpenPassword, $WritePassword, $true)
        } else {
            $workbook = $xl.Workbooks.Open($workbookPath)
        }
    } finally {
        $xl.EnableEvents = $previousEnableEvents
    }

    try {
        if ((-not $DryRun) -and $workbook.ReadOnly) {
            throw "Workbook opened read-only. Close any open copies of '$WorkbookName' before importing source."
        }

        if (-not $workbook.HasVBProject) {
            throw "Workbook does not have a VBA project: $WorkbookName"
        }

        $components = $workbook.VBProject.VBComponents
        if ([int]$components.Count -eq 0) {
            throw "Excel returned zero VBA components. Confirm Trust Access is enabled and the VBA project is unlocked."
        }

        foreach ($sourceFile in $sourceFiles) {
            $rawSource = Get-Content -LiteralPath $sourceFile.FullName -Raw
            $componentName = Get-ComponentNameFromSource -SourceText $rawSource -FallbackName $sourceFile.BaseName
            $codeText = Remove-VbaAttributeLines -SourceText $rawSource
            $component = Get-VbComponent -Components $components -Name $componentName
            $action = "Update"

            if ($null -eq $component) {
                $component = New-StandardComponent -Components $components -ComponentName $componentName -Extension $sourceFile.Extension
                $action = "Create"
            }

            $changes.Add([pscustomobject]@{
                Component = $componentName
                File = $sourceFile.Name
                Action = $action
                Lines = ($codeText -split "`r?`n").Count
            })

            if (-not $DryRun) {
                Replace-CodeModuleText -Component $component -CodeText $codeText
            }
        }

        if (-not $DryRun) {
            $workbook.Save()
        }
    } finally {
        if ($null -ne $workbook) {
            try {
                $workbook.Close($false) | Out-Null
            } catch {
                Write-Warning "Excel workbook cleanup reported: $($_.Exception.Message)"
            }
        }
    }
} finally {
    try {
        $xl.Quit() | Out-Null
    } catch {
        Write-Warning "Excel application cleanup reported: $($_.Exception.Message)"
    }
    try {
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
    } catch {
        Write-Warning "Excel COM release reported: $($_.Exception.Message)"
    }
}

$logDir = Join-Path $sourceRootPath "_sync_logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = [pscustomobject]@{
    workbook = $workbookPath
    sourceFolder = $sourceFolder
    dryRun = [bool]$DryRun
    backupPath = $backupPath
    syncedAt = (Get-Date).ToString("s")
    changes = $changes
}
$logPath = Join-Path $logDir ("import_{0}_{1}.json" -f ([System.IO.Path]::GetFileNameWithoutExtension($WorkbookName) -replace '[^\w.-]', '_'), (Get-Date -Format "yyyyMMdd_HHmmss"))
$log | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $logPath -Encoding UTF8

$changes | Format-Table -AutoSize
Write-Host ""
if ($DryRun) {
    Write-Host "Dry run complete. No workbook changes were saved."
} else {
    Write-Host "Import complete."
    if ($backupPath) {
        Write-Host "Backup: $backupPath"
    }
}
Write-Host "Log: $logPath"
