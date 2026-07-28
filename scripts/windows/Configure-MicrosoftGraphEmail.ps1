param()

$ErrorActionPreference = "Stop"
$AppRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$SecretsDirectory = Join-Path $AppRoot "data\secrets"
$ConfigPath = Join-Path $SecretsDirectory "microsoft-graph-email.json"

function Read-RequiredValue {
    param(
        [string]$Prompt,
        [string]$DefaultValue = ""
    )

    $displayPrompt = if ($DefaultValue) { "$Prompt [$DefaultValue]" } else { $Prompt }
    while ($true) {
        $value = Read-Host $displayPrompt
        if (-not $value -and $DefaultValue) {
            return $DefaultValue
        }
        if ($value) {
            return $value.Trim()
        }
        Write-Host "A value is required." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Microsoft Graph Email Setup" -ForegroundColor Cyan
Write-Host "This stores the client secret encrypted for the current Windows account."
Write-Host "The secret is never written to the project in plain text."
Write-Host ""

$tenantId = Read-RequiredValue -Prompt "Microsoft Entra tenant ID"
$clientId = Read-RequiredValue -Prompt "App registration client ID"
$sender = Read-RequiredValue -Prompt "Sender mailbox" -DefaultValue "BarefootNC.Glass@bldr.com"
$testRecipient = Read-RequiredValue -Prompt "Default test recipient" -DefaultValue "brandon.m.smith@bldr.com"
$clientSecret = Read-Host "App registration client secret" -AsSecureString
if (-not $clientSecret -or $clientSecret.Length -eq 0) {
    throw "A client secret is required."
}

if (-not (Test-Path -LiteralPath $SecretsDirectory)) {
    New-Item -ItemType Directory -Path $SecretsDirectory -Force | Out-Null
}

$encryptedSecret = ConvertFrom-SecureString $clientSecret
$config = [ordered]@{
    version = 1
    authMode = "client-secret"
    tenantId = $tenantId
    clientId = $clientId
    sender = $sender
    testRecipient = $testRecipient
    saveToSentItems = $true
    encryptedClientSecret = $encryptedSecret
    configuredAt = (Get-Date).ToString("o")
}
$config | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8

Write-Host ""
Write-Host "Microsoft Graph email configuration saved." -ForegroundColor Green
Write-Host "Sender: $sender"
Write-Host "Test recipient: $testRecipient"
Write-Host "Configuration: $ConfigPath"
Write-Host ""
Write-Host "Start the Delivery List Scanner, then open Admin > Customer Emails and send the test email."
Write-Host "The test will not work until a Microsoft 365 administrator grants the app permission to send as the sender mailbox."
