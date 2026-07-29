# File: Start-DeliveryScannerWebApp.ps1
param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$AppRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerPath = Join-Path $AppRoot "server.py"
$LogDirectory = Join-Path $AppRoot "logs"
$StandardOutputLog = Join-Path $LogDirectory "server-stdout.log"
$StandardErrorLog = Join-Path $LogDirectory "server-stderr.log"
$LauncherLog = Join-Path $LogDirectory "launcher.log"
$PidFile = Join-Path $LogDirectory "delivery-scanner.pid"

# Purpose: Record one launcher milestone in the console and persistent log.
# Effects: Creates the logs directory when needed and appends launcher.log.
# Flow: Prefixes the message with local time, writes the file, then shows it to the operator.
function Write-LauncherLog {
    param([string]$Message)

    if (-not (Test-Path -LiteralPath $LogDirectory)) {
        New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    Add-Content -LiteralPath $LauncherLog -Value $line -Encoding UTF8
    Write-Host $Message
}

# Purpose: Determine whether a local TCP port can be safely bound by the server.
# Effects: Opens and immediately closes a temporary loopback listener.
# Flow: Returns true only when Windows permits the test listener to start.
function Test-PortAvailable {
    param([int]$CandidatePort)

    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new(
            [System.Net.IPAddress]::Parse("127.0.0.1"),
            $CandidatePort
        )
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($listener) {
            $listener.Stop()
        }
    }
}

# Purpose: Identify a healthy Delivery List Scanner already listening on a port.
# Effects: Sends a short local HTTP request to /api/health.
# Flow: Returns the parsed health object only when ok=true and a database mode is present.
function Get-DeliveryScannerHealth {
    param([int]$CandidatePort)

    try {
        $healthUrl = "http://127.0.0.1:$CandidatePort/api/health"
        $response = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
        if ($response.ok -eq $true -and $response.mode) {
            return $response
        }
    } catch {
        return $null
    }

    return $null
}

# Purpose: Open the verified local web address without making browser launch a startup dependency.
# Effects: Starts the default browser or prints the URL when Windows cannot open it.
# Flow: Browser failures are logged but never stop an already healthy server.
function Open-DeliveryScannerBrowser {
    param([string]$Url)

    try {
        Start-Process $Url | Out-Null
        Write-LauncherLog "Opened $Url"
    } catch {
        Write-LauncherLog "The server is running, but Windows could not open the browser automatically: $($_.Exception.Message)"
        Write-Host "Open this address manually: $Url" -ForegroundColor Yellow
    }
}

# Purpose: Select a supported Python 3.10+ runtime for the local SQLite server.
# Effects: Executes lightweight version checks against available Python candidates.
# Flow: Prefers a project virtual environment, then py/python, with the Codex runtime last.
function Resolve-PythonRuntime {
    $candidates = @()
    $virtualEnvironmentPython = Join-Path $AppRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $virtualEnvironmentPython) {
        $candidates += ,@($virtualEnvironmentPython, @())
    }

    if (Get-Command py -ErrorAction SilentlyContinue) {
        $candidates += ,@("py", @("-3"))
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        $candidates += ,@("python", @())
    }

    $bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if (Test-Path -LiteralPath $bundledPython) {
        $candidates += ,@($bundledPython, @())
    }

    foreach ($candidate in $candidates) {
        $command = [string]$candidate[0]
        $prefixArguments = @($candidate[1])
        try {
            $versionText = & $command @prefixArguments -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
            if ($LASTEXITCODE -ne 0 -or -not $versionText) {
                continue
            }

            $version = [Version]($versionText | Select-Object -Last 1)
            if ($version -lt [Version]"3.10.0") {
                Write-LauncherLog "Skipped Python $version from '$command' because Python 3.10 or newer is required."
                continue
            }

            return [PSCustomObject]@{
                Command = $command
                PrefixArguments = $prefixArguments
                Version = $version
            }
        } catch {
            continue
        }
    }

    throw "Python 3.10 or newer was not found. Install current 64-bit Python and make sure the 'py' launcher is available."
}

# Purpose: Load the locally encrypted Microsoft Graph app registration settings.
# Effects: Decrypts the client secret only in memory for the current Windows user
# and exposes it to the child Python process through inherited environment variables.
# Flow: Reads data\secrets\microsoft-graph-email.json when present, validates the
# non-secret fields, decrypts the DPAPI-protected secret, and logs readiness only.
function Import-MicrosoftGraphEmailConfiguration {
    $configPath = Join-Path $AppRoot "data\secrets\microsoft-graph-email.json"
    if (-not (Test-Path -LiteralPath $configPath)) {
        Write-LauncherLog "Microsoft Graph email is not locally configured. Email messages will remain drafts until setup is completed."
        return
    }

    try {
        $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $tenantId = [string]$config.tenantId
        $clientId = [string]$config.clientId
        $sender = [string]$config.sender
        $testRecipient = [string]$config.testRecipient
        $encryptedSecret = [string]$config.encryptedClientSecret
        if (-not $tenantId -or -not $clientId -or -not $sender -or -not $encryptedSecret) {
            throw "The Graph email configuration is incomplete. Run Configure-MicrosoftGraphEmail.bat again."
        }

        $secureSecret = ConvertTo-SecureString $encryptedSecret
        $secretPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureSecret)
        try {
            $plainSecret = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($secretPointer)
        } finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretPointer)
        }
        if (-not $plainSecret) {
            throw "The Graph client secret could not be decrypted for this Windows account."
        }

        $env:DLS_EMAIL_TRANSPORT = "graph"
        $env:DLS_GRAPH_AUTH_MODE = "client-secret"
        $env:DLS_GRAPH_TENANT_ID = $tenantId
        $env:DLS_GRAPH_CLIENT_ID = $clientId
        $env:DLS_GRAPH_CLIENT_SECRET = $plainSecret
        $env:DLS_GRAPH_SENDER = $sender
        $env:DLS_EMAIL_FROM = $sender
        $env:DLS_EMAIL_TEST_RECIPIENT = $testRecipient
        $env:DLS_GRAPH_SAVE_TO_SENT_ITEMS = if ($config.saveToSentItems -eq $false) { "0" } else { "1" }
        Write-LauncherLog "Microsoft Graph email configuration loaded for $sender."
    } catch {
        throw "Microsoft Graph email configuration could not be loaded: $($_.Exception.Message)"
    }
}

# Purpose: Keep startup errors visible and point the operator to durable diagnostics.
# Effects: Reads recent stderr/startup logs and writes a launcher failure milestone.
# Flow: Displays the reason, process exit code when available, traceback tail, and log folder.
function Show-StartupFailure {
    param(
        [string]$Reason,
        [System.Diagnostics.Process]$Process
    )

    Write-LauncherLog $Reason
    Write-Host "" 
    Write-Host "Delivery List Scanner failed to start." -ForegroundColor Red

    if ($Process) {
        try {
            $Process.Refresh()
            Write-Host "Python exit code: $($Process.ExitCode)"
        } catch {
            # The process may not have reached an exit state yet.
        }
    }

    if (Test-Path -LiteralPath $StandardErrorLog) {
        Write-Host "" 
        Write-Host "Latest Python error:" -ForegroundColor Yellow
        Get-Content -LiteralPath $StandardErrorLog -Tail 80
    }

    $startupErrorLog = Join-Path $LogDirectory "startup-error.log"
    if (Test-Path -LiteralPath $startupErrorLog) {
        Write-Host "" 
        Write-Host "Detailed startup traceback:" -ForegroundColor Yellow
        Get-Content -LiteralPath $startupErrorLog -Tail 120
    }

    Write-Host "" 
    Write-Host "Logs are saved in: $LogDirectory"
}

try {
    if (-not (Test-Path -LiteralPath $ServerPath)) {
        throw "server.py was not found beside this launcher. Keep the BAT, PS1, and project files in the same folder."
    }

    if (-not (Test-Path -LiteralPath $LogDirectory)) {
        New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
    }

    Write-LauncherLog "Starting Delivery List Scanner from $AppRoot"

    $existingHealth = $null
    if (-not (Test-PortAvailable -CandidatePort $Port)) {
        $existingHealth = Get-DeliveryScannerHealth -CandidatePort $Port
    }

    if ($existingHealth) {
        $url = "http://127.0.0.1:$Port/"
        Write-LauncherLog "Delivery List Scanner is already running on port $Port using $($existingHealth.mode)."
        Open-DeliveryScannerBrowser -Url $url
        exit 0
    }

    while (-not (Test-PortAvailable -CandidatePort $Port)) {
        Write-LauncherLog "Port $Port is being used by another program. Trying port $($Port + 1)."
        $Port += 1
    }

    $pythonRuntime = Resolve-PythonRuntime
    Write-LauncherLog "Using Python $($pythonRuntime.Version) from '$($pythonRuntime.Command)'."

    $env:PORT = [string]$Port
    $env:DLS_PORT = [string]$Port
    $env:DLS_HOST = "127.0.0.1"
    if (-not $env:DLS_DATABASE_TYPE) {
        $env:DLS_DATABASE_TYPE = "sqlite"
    }
    if (-not $env:DLS_TEMP_DELIVERY_LISTS_PATH) {
        $env:DLS_TEMP_DELIVERY_LISTS_PATH = "I:\BAREFOOT-INSTALL\Glass Production\Brandon\Temp Delivery Lists"
    }
    Import-MicrosoftGraphEmailConfiguration

    $url = "http://127.0.0.1:$Port/"
    $databasePath = Join-Path $AppRoot "data\delivery-scanner-pilot.db"

    Remove-Item -LiteralPath $StandardOutputLog -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $StandardErrorLog -Force -ErrorAction SilentlyContinue

    $serverArguments = @($pythonRuntime.PrefixArguments) + @("-u", "server.py")
    # Run Python inside this existing console host. -NoNewWindow prevents the
    # py/python launcher from creating a second terminal that can later steal focus.
    # Server output remains redirected to durable log files for diagnostics.
    $serverProcess = Start-Process `
        -FilePath $pythonRuntime.Command `
        -ArgumentList $serverArguments `
        -WorkingDirectory $AppRoot `
        -RedirectStandardOutput $StandardOutputLog `
        -RedirectStandardError $StandardErrorLog `
        -NoNewWindow `
        -PassThru

    Set-Content -LiteralPath $PidFile -Value $serverProcess.Id -Encoding ASCII
    Write-LauncherLog "Python process $($serverProcess.Id) started. Waiting for database initialization and web health check."
    Write-Host "SQLite database: $databasePath"

    $health = $null
    $deadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 500
        $serverProcess.Refresh()

        if ($serverProcess.HasExited) {
            Show-StartupFailure -Reason "Python exited before the health check completed." -Process $serverProcess
            exit 1
        }

        $health = Get-DeliveryScannerHealth -CandidatePort $Port
        if ($health) {
            break
        }
    }

    if (-not $health) {
        try {
            if (-not $serverProcess.HasExited) {
                Stop-Process -Id $serverProcess.Id -Force
            }
        } catch {
            # Continue to the diagnostic output even if process cleanup fails.
        }
        Show-StartupFailure -Reason "The server did not become healthy within 90 seconds." -Process $serverProcess
        exit 1
    }

    Write-LauncherLog "Delivery List Scanner is healthy at $url using database mode '$($health.mode)'."
    Open-DeliveryScannerBrowser -Url $url
    Write-Host "Keep this window open while the local web app is running."

    Wait-Process -Id $serverProcess.Id
    $serverProcess.Refresh()
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue

    if ($serverProcess.ExitCode -ne 0) {
        Show-StartupFailure -Reason "The server stopped unexpectedly after startup." -Process $serverProcess
        exit $serverProcess.ExitCode
    }

    Write-LauncherLog "Delivery List Scanner stopped normally."
    exit 0
} catch {
    Show-StartupFailure -Reason $_.Exception.Message -Process $null
    exit 1
}
