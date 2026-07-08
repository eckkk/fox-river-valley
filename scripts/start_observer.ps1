param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:FRV_HOME = $ProjectRoot
$Url = "http://127.0.0.1:$Port/observer.html"

function Test-Python {
    param([string]$PythonPath)
    if (-not $PythonPath) {
        return $false
    }
    if ($PythonPath -match "\\WindowsApps\\python(\.exe)?$") {
        return $false
    }
    try {
        & $PythonPath -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" *> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Find-Python {
    $candidates = @(
        (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
        (Join-Path $ProjectRoot ".venv\Scripts\python.exe")
    )
    $pathPython = (Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($pathPython) {
        $candidates += $pathPython.Source
    }
    foreach ($candidate in $candidates) {
        if (Test-Python $candidate) {
            return $candidate
        }
    }
    return $null
}

function Wait-ObserverReady {
    param(
        [int]$Port,
        [int]$Attempts = 30
    )
    for ($i = 0; $i -lt $Attempts; $i++) {
        $result = Test-NetConnection -ComputerName "127.0.0.1" -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
        if ($result) {
            return $true
        }
        Start-Sleep -Milliseconds 250
    }
    return $false
}

Set-Location $ProjectRoot
Write-Host "Fox River Valley runtime root: $env:FRV_HOME"
Write-Host "Observer URL: $Url"

$Python = Find-Python
if (-not $Python) {
    Write-Host ""
    Write-Host "Python 3.11+ not found."
    Write-Host "WindowsApps python launcher was ignored because it does not start this game server reliably."
    Write-Host "Install Python 3.11+, or run from Codex where the bundled runtime is available."
    exit 1
}

Write-Host "Using Python: $Python"
try {
    $server = Start-Process -FilePath $Python -ArgumentList @("scripts\run_observer_server.py", "--port", "$Port") -WorkingDirectory $ProjectRoot -NoNewWindow -PassThru
}
catch {
    Write-Host ""
    Write-Host "Observer server failed: $($_.Exception.Message)"
    exit 1
}

if (Wait-ObserverReady -Port $Port) {
    Write-Host "Observer server is ready."
    Start-Process $Url
}
else {
    Write-Host ""
    Write-Host "Observer server did not become ready on port $Port."
    Write-Host "If the browser shows ERR_CONNECTION_REFUSED, keep this window open and check the server output above."
}

Wait-Process -Id $server.Id
