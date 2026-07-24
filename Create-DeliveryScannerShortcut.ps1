[CmdletBinding()]
param(
    [string]$ShortcutName = "Glass Delivery Scanner"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-ScannerProjectRoot {
    $resolved = (Resolve-Path -LiteralPath $PSScriptRoot).Path
    if (-not (Test-Path -LiteralPath $resolved -PathType Container)) {
        throw "Scanner project folder was not found: $resolved"
    }
    return $resolved
}

function Get-DesktopFolder {
    param([Parameter(Mandatory = $true)]$Shell)

    $desktopPath = [string]$Shell.SpecialFolders.Item("Desktop")
    if ([string]::IsNullOrWhiteSpace($desktopPath)) {
        $desktopPath = [Environment]::GetFolderPath([Environment+SpecialFolder]::DesktopDirectory)
    }
    if ([string]::IsNullOrWhiteSpace($desktopPath) -and -not [string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
        $desktopPath = Join-Path $env:USERPROFILE "Desktop"
    }
    if ([string]::IsNullOrWhiteSpace($desktopPath)) {
        throw "Windows could not resolve the current user's Desktop folder."
    }
    if (-not (Test-Path -LiteralPath $desktopPath -PathType Container)) {
        [void](New-Item -ItemType Directory -Path $desktopPath -Force)
    }
    return (Resolve-Path -LiteralPath $desktopPath).Path
}

function Get-ShortcutIcon {
    param([Parameter(Mandatory = $true)][string]$ProjectRoot)

    $candidates = @(
        (Join-Path $ProjectRoot "assets\delivery-list-scanner-icon.ico"),
        (Join-Path $ProjectRoot "delivery-list-scanner-icon.ico")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }
    return ""
}

try {
    $projectRoot = Get-ScannerProjectRoot
    $launcherPath = Join-Path $projectRoot "Start-DeliveryScannerWebApp.bat"
    if (-not (Test-Path -LiteralPath $launcherPath -PathType Leaf)) {
        throw "The maintained scanner launcher was not found: $launcherPath"
    }

    $commandProcessor = [string]$env:ComSpec
    if ([string]::IsNullOrWhiteSpace($commandProcessor)) {
        $commandProcessor = Join-Path $env:SystemRoot "System32\cmd.exe"
    }
    if (-not (Test-Path -LiteralPath $commandProcessor -PathType Leaf)) {
        throw "Windows command processor was not found: $commandProcessor"
    }

    $shell = New-Object -ComObject WScript.Shell
    $desktopPath = Get-DesktopFolder -Shell $shell
    $shortcutPath = Join-Path $desktopPath ($ShortcutName + ".lnk")
    $shortcutArguments = '/d /c ""{0}""' -f $launcherPath

    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $commandProcessor
    $shortcut.Arguments = $shortcutArguments
    $shortcut.WorkingDirectory = $projectRoot
    $shortcut.WindowStyle = 1
    $shortcut.Description = "Start the Glass Delivery Scanner web app"

    $iconPath = Get-ShortcutIcon -ProjectRoot $projectRoot
    if ($iconPath) {
        $shortcut.IconLocation = "$iconPath,0"
    }
    else {
        $shortcut.IconLocation = "$commandProcessor,0"
    }

    $shortcut.Save()

    if (-not (Test-Path -LiteralPath $shortcutPath -PathType Leaf)) {
        throw "Windows did not create the shortcut at $shortcutPath"
    }

    $verified = $shell.CreateShortcut($shortcutPath)
    if (-not [string]::Equals(
        [IO.Path]::GetFullPath([string]$verified.TargetPath),
        [IO.Path]::GetFullPath($commandProcessor),
        [StringComparison]::OrdinalIgnoreCase
    )) {
        throw "The created shortcut points to an unexpected program."
    }
    if ([string]$verified.Arguments -ne $shortcutArguments) {
        throw "The created shortcut does not contain the expected scanner launcher command."
    }
    if (-not [string]::Equals(
        [IO.Path]::GetFullPath([string]$verified.WorkingDirectory),
        [IO.Path]::GetFullPath($projectRoot),
        [StringComparison]::OrdinalIgnoreCase
    )) {
        throw "The created shortcut has an unexpected working directory."
    }

    Write-Host "" 
    Write-Host "Desktop shortcut created successfully." -ForegroundColor Green
    Write-Host "Shortcut: $shortcutPath"
    Write-Host "Launcher: $launcherPath"
    exit 0
}
catch {
    Write-Host "" 
    Write-Host ("DESKTOP SHORTCUT FAILED: {0}" -f $_.Exception.Message) -ForegroundColor Red
    exit 1
}
