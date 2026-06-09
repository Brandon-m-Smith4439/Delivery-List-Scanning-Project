Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$ErrorActionPreference = "Stop"

$script:ProjectRoot = Split-Path -Parent $PSScriptRoot
$script:SourceRoot = Join-Path $script:ProjectRoot "VBA Source"
$script:DefaultFiles = @(
    "ThisWorkbook.cls",
    "modMasterQueueProcessor.bas",
    "modSnapshotPublisher.bas",
    "ScannerValidation.bas"
)

function Add-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "HH:mm:ss"
    $txtLog.AppendText("[$timestamp] $Message`r`n")
}

function Quote-ProcessArgument {
    param([string]$Value)
    if ($null -eq $Value) { return '""' }
    return '"' + ($Value -replace '"', '\"') + '"'
}

function Join-FileListArgument {
    param([string[]]$Names)
    return ($Names | ForEach-Object { $_.Trim() } | Where-Object { $_.Length -gt 0 }) -join "|"
}

function Get-SelectedWorkbookName {
    if ($cmbWorkbook.SelectedItem) {
        return [string]$cmbWorkbook.SelectedItem
    }
    return [string]$cmbWorkbook.Text
}

function Get-SourceFolder {
    $workbookName = Get-SelectedWorkbookName
    if ([string]::IsNullOrWhiteSpace($workbookName)) { return $null }
    $folderName = [System.IO.Path]::GetFileNameWithoutExtension($workbookName)
    return Join-Path $script:SourceRoot $folderName
}

function Refresh-WorkbookList {
    $cmbWorkbook.Items.Clear()
    if (-not (Test-Path -LiteralPath $txtProjectRoot.Text)) {
        Add-Log "Project root does not exist."
        return
    }

    $script:ProjectRoot = [System.IO.Path]::GetFullPath($txtProjectRoot.Text)
    $script:SourceRoot = Join-Path $script:ProjectRoot "VBA Source"
    $workbooks = Get-ChildItem -LiteralPath $script:ProjectRoot -Filter "*.xlsm" -File |
        Sort-Object LastWriteTime -Descending

    foreach ($workbook in $workbooks) {
        [void]$cmbWorkbook.Items.Add($workbook.Name)
    }

    $preferred = $workbooks | Where-Object { $_.Name -like "*version 3*.xlsm" } | Select-Object -First 1
    if ($preferred) {
        $cmbWorkbook.SelectedItem = $preferred.Name
    } elseif ($cmbWorkbook.Items.Count -gt 0) {
        $cmbWorkbook.SelectedIndex = 0
    }

    Refresh-FileList
}

function Refresh-FileList {
    $checkedFiles.Items.Clear()
    $sourceFolder = Get-SourceFolder
    $lblSourceValue.Text = if ($sourceFolder) { $sourceFolder } else { "" }

    if (-not $sourceFolder -or -not (Test-Path -LiteralPath $sourceFolder)) {
        Add-Log "Source folder not found for selected workbook."
        return
    }

    $files = Get-ChildItem -LiteralPath $sourceFolder -File |
        Where-Object { $_.Extension -in ".bas", ".cls", ".frm" } |
        Sort-Object Name

    foreach ($file in $files) {
        $checked = $script:DefaultFiles -contains $file.Name
        [void]$checkedFiles.Items.Add($file.Name, $checked)
    }
    Add-Log "Loaded $($files.Count) source files from $([System.IO.Path]::GetFileName($sourceFolder))."
}

function Select-PatchedDefaults {
    for ($i = 0; $i -lt $checkedFiles.Items.Count; $i++) {
        $name = [string]$checkedFiles.Items[$i]
        $checkedFiles.SetItemChecked($i, ($script:DefaultFiles -contains $name))
    }
    Add-Log "Selected the patched queue/snapshot/bad-scan modules."
}

function Get-CheckedFileNames {
    $names = New-Object System.Collections.Generic.List[string]
    foreach ($item in $checkedFiles.CheckedItems) {
        [void]$names.Add([string]$item)
    }
    return @($names)
}

function Invoke-VbaImport {
    param([switch]$DryRun)

    $importScript = Join-Path $PSScriptRoot "import_vba_source.ps1"
    if (-not (Test-Path -LiteralPath $importScript)) {
        Add-Log "Import script not found: $importScript"
        return
    }

    $workbookName = Get-SelectedWorkbookName
    if ([string]::IsNullOrWhiteSpace($workbookName)) {
        Add-Log "Select a workbook first."
        return
    }

    $selectedFiles = Get-CheckedFileNames
    if ($selectedFiles.Count -eq 0) {
        Add-Log "Select at least one source file."
        return
    }

    $lockPath = Join-Path $script:ProjectRoot ("~$" + $workbookName)
    if (Test-Path -LiteralPath $lockPath) {
        Add-Log "Workbook lock file exists. Close Excel before importing: $lockPath"
        return
    }

    $btnDryRun.Enabled = $false
    $btnImport.Enabled = $false
    $modeText = if ($DryRun) { "dry run" } else { "import" }
    Add-Log "Starting $modeText for $workbookName..."

    $engine = (Get-Process -Id $PID).Path
    if ([string]::IsNullOrWhiteSpace($engine)) { $engine = "powershell.exe" }

    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", (Quote-ProcessArgument $importScript),
        "-ProjectRoot", (Quote-ProcessArgument $script:ProjectRoot),
        "-WorkbookName", (Quote-ProcessArgument $workbookName),
        "-FilesCsv", (Quote-ProcessArgument (Join-FileListArgument $selectedFiles))
    )
    if ($DryRun) { $args += "-DryRun" }

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $engine
    $psi.Arguments = ($args -join " ")
    $psi.WorkingDirectory = $script:ProjectRoot
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    [void]$process.Start()

    $timeoutMs = 8 * 60 * 1000
    if (-not $process.WaitForExit($timeoutMs)) {
        try { $process.Kill() } catch {}
        Add-Log "Import timed out after 8 minutes. Excel/VBIDE did not respond cleanly."
    } else {
        $stdout = $process.StandardOutput.ReadToEnd()
        $stderr = $process.StandardError.ReadToEnd()
        if ($stdout.Trim().Length -gt 0) { Add-Log $stdout.Trim() }
        if ($stderr.Trim().Length -gt 0) { Add-Log $stderr.Trim() }
        Add-Log "$modeText finished with exit code $($process.ExitCode)."
    }

    $btnDryRun.Enabled = $true
    $btnImport.Enabled = $true
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "Delivery List VBA Import"
$form.Size = New-Object System.Drawing.Size(940, 690)
$form.StartPosition = "CenterScreen"
$form.MinimumSize = New-Object System.Drawing.Size(840, 600)

$font = New-Object System.Drawing.Font("Segoe UI", 9)
$form.Font = $font

$lblRoot = New-Object System.Windows.Forms.Label
$lblRoot.Text = "Project root"
$lblRoot.Location = New-Object System.Drawing.Point(16, 18)
$lblRoot.Size = New-Object System.Drawing.Size(120, 24)
$form.Controls.Add($lblRoot)

$txtProjectRoot = New-Object System.Windows.Forms.TextBox
$txtProjectRoot.Location = New-Object System.Drawing.Point(140, 16)
$txtProjectRoot.Size = New-Object System.Drawing.Size(640, 24)
$txtProjectRoot.Text = $script:ProjectRoot
$form.Controls.Add($txtProjectRoot)

$btnRefresh = New-Object System.Windows.Forms.Button
$btnRefresh.Text = "Refresh"
$btnRefresh.Location = New-Object System.Drawing.Point(792, 14)
$btnRefresh.Size = New-Object System.Drawing.Size(110, 28)
$btnRefresh.Add_Click({ Refresh-WorkbookList })
$form.Controls.Add($btnRefresh)

$lblWorkbook = New-Object System.Windows.Forms.Label
$lblWorkbook.Text = "Workbook"
$lblWorkbook.Location = New-Object System.Drawing.Point(16, 58)
$lblWorkbook.Size = New-Object System.Drawing.Size(120, 24)
$form.Controls.Add($lblWorkbook)

$cmbWorkbook = New-Object System.Windows.Forms.ComboBox
$cmbWorkbook.Location = New-Object System.Drawing.Point(140, 56)
$cmbWorkbook.Size = New-Object System.Drawing.Size(360, 24)
$cmbWorkbook.DropDownStyle = "DropDown"
$cmbWorkbook.Add_SelectedIndexChanged({ Refresh-FileList })
$form.Controls.Add($cmbWorkbook)

$btnDefaults = New-Object System.Windows.Forms.Button
$btnDefaults.Text = "Patched defaults"
$btnDefaults.Location = New-Object System.Drawing.Point(516, 54)
$btnDefaults.Size = New-Object System.Drawing.Size(130, 28)
$btnDefaults.Add_Click({ Select-PatchedDefaults })
$form.Controls.Add($btnDefaults)

$btnDryRun = New-Object System.Windows.Forms.Button
$btnDryRun.Text = "Dry run"
$btnDryRun.Location = New-Object System.Drawing.Point(660, 54)
$btnDryRun.Size = New-Object System.Drawing.Size(110, 28)
$btnDryRun.Add_Click({ Invoke-VbaImport -DryRun })
$form.Controls.Add($btnDryRun)

$btnImport = New-Object System.Windows.Forms.Button
$btnImport.Text = "Import selected"
$btnImport.Location = New-Object System.Drawing.Point(784, 54)
$btnImport.Size = New-Object System.Drawing.Size(118, 28)
$btnImport.Add_Click({
    $answer = [System.Windows.Forms.MessageBox]::Show(
        "Import selected VBA files into the workbook? A backup is created first.",
        "Confirm import",
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Question
    )
    if ($answer -eq [System.Windows.Forms.DialogResult]::Yes) {
        Invoke-VbaImport
    }
})
$form.Controls.Add($btnImport)

$lblSource = New-Object System.Windows.Forms.Label
$lblSource.Text = "Source folder"
$lblSource.Location = New-Object System.Drawing.Point(16, 96)
$lblSource.Size = New-Object System.Drawing.Size(120, 24)
$form.Controls.Add($lblSource)

$lblSourceValue = New-Object System.Windows.Forms.Label
$lblSourceValue.Location = New-Object System.Drawing.Point(140, 96)
$lblSourceValue.Size = New-Object System.Drawing.Size(760, 42)
$lblSourceValue.AutoEllipsis = $true
$form.Controls.Add($lblSourceValue)

$checkedFiles = New-Object System.Windows.Forms.CheckedListBox
$checkedFiles.Location = New-Object System.Drawing.Point(20, 146)
$checkedFiles.Size = New-Object System.Drawing.Size(380, 470)
$checkedFiles.CheckOnClick = $true
$form.Controls.Add($checkedFiles)

$txtLog = New-Object System.Windows.Forms.TextBox
$txtLog.Location = New-Object System.Drawing.Point(420, 146)
$txtLog.Size = New-Object System.Drawing.Size(482, 470)
$txtLog.Multiline = $true
$txtLog.ScrollBars = "Vertical"
$txtLog.ReadOnly = $true
$form.Controls.Add($txtLog)

$lblHint = New-Object System.Windows.Forms.Label
$lblHint.Text = "Close Excel before importing. Use Dry run first. Default selection contains the queue, snapshot, workbook-open, and bad-scan fixes."
$lblHint.Location = New-Object System.Drawing.Point(20, 622)
$lblHint.Size = New-Object System.Drawing.Size(800, 22)
$form.Controls.Add($lblHint)

Refresh-WorkbookList
[void]$form.ShowDialog()
