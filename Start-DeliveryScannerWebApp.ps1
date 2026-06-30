param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$AppRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Test-PortAvailable {
    param([int]$CandidatePort)

    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), $CandidatePort)
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

function Test-ExistingDeliveryScanner {
    param([int]$CandidatePort)

    try {
        $healthUrl = "http://127.0.0.1:$CandidatePort/api/health"
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 1
        return ($response.StatusCode -eq 200 -and ($response.Content -like '*database*' -and $response.Content -like '*delivery-scanner*'))
    } catch {
        return $false
    }
}

if (-not (Test-PortAvailable -CandidatePort $Port) -and (Test-ExistingDeliveryScanner -CandidatePort $Port)) {
    $url = "http://127.0.0.1:$Port/"
    Write-Host "Delivery List Scanner is already running at $url"
    Start-Process $url
    return
}

while (-not (Test-PortAvailable -CandidatePort $Port)) {
    $Port += 1
}

$bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$pythonCommand = $null
$pythonArgs = @()

if (Test-Path -LiteralPath $bundledPython) {
    $pythonCommand = $bundledPython
    $pythonArgs = @("server.py")
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCommand = "py"
    $pythonArgs = @("-3", "server.py")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCommand = "python"
    $pythonArgs = @("server.py")
} else {
    throw "Python was not found. Install Python 3 or run this from Codex where the bundled Python runtime is available."
}

$env:PORT = [string]$Port
$env:DLS_PORT = [string]$Port
$env:DLS_HOST = "127.0.0.1"
$env:DLS_TEMP_DELIVERY_LISTS_PATH = "I:\BAREFOOT-INSTALL\Glass Production\Brandon\Temp Delivery Lists"

$url = "http://127.0.0.1:$Port/"

Set-Location -LiteralPath $AppRoot
Write-Host "Delivery List Scanner starting at $url"
Write-Host "SQLite database: $AppRoot\data\delivery-scanner-pilot.db"
Start-Process $url
& $pythonCommand @pythonArgs
