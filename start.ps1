# Starts Truescope at http://localhost:8000.
# Usage (PowerShell, in the project folder):  .\start.ps1
# Keep this window open while you use the app. Press Ctrl+C here to stop it.
# Options:  -Port 8001   use another port     -NoBrowser   don't open the browser

param(
    [int]$Port = 8000,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$venvPython = Join-Path (Join-Path (Join-Path $backend 'venv') 'Scripts') 'python.exe'
$url = "http://localhost:$Port"

function Fail($message) {
    Write-Host ''
    Write-Host $message -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $venvPython)) {
    Fail 'The app is not set up yet. Run .\setup.ps1 first.'
}

# 1. Make sure nothing else (usually an older copy of this app) is using the port.
$listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Port)
try {
    $listener.Start()
    $listener.Stop()
} catch {
    Fail "Port $Port is already in use, probably by the app running in another window. Close that window (or press Ctrl+C in it) and run .\start.ps1 again. Or open $url if it is already running."
}

# 2. Build the web page if it is missing or older than its source files.
$index = Join-Path (Join-Path $frontend 'dist') 'index.html'
$needBuild = -not (Test-Path $index)
if (-not $needBuild) {
    $builtAt = (Get-Item $index).LastWriteTime
    $sources = @(Get-ChildItem -Path (Join-Path $frontend 'src') -Recurse -File)
    $sources += Get-Item (Join-Path $frontend 'index.html'), (Join-Path $frontend 'package.json'), (Join-Path $frontend 'vite.config.js')
    $newest = $sources | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($newest.LastWriteTime -gt $builtAt) { $needBuild = $true }
}
if ($needBuild) {
    Write-Host 'Building the web page (only needed after an update)...' -ForegroundColor Cyan
    Push-Location $frontend
    try {
        if (-not (Test-Path 'node_modules')) {
            & npm install
            if ($LASTEXITCODE -ne 0) { Fail 'npm install failed. Run .\setup.ps1, then try again.' }
        }
        & npm run build
        if ($LASTEXITCODE -ne 0) { Fail 'Building the web page failed. See the messages above.' }
    } finally {
        Pop-Location
    }
}

# 3. Open the browser once the server answers (in the background).
if (-not $NoBrowser) {
    Start-Job -ArgumentList $url -ScriptBlock {
        param($u)
        for ($i = 0; $i -lt 90; $i++) {
            try {
                Invoke-WebRequest -Uri "$u/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
                Start-Process $u
                return
            } catch {
                Start-Sleep -Seconds 1
            }
        }
    } | Out-Null
}

# 4. Run the server in this window.
Write-Host ''
Write-Host "Starting Truescope at $url  (press Ctrl+C to stop)" -ForegroundColor Green
Write-Host ''
Push-Location $backend
try {
    & $venvPython -m uvicorn main:app --host 127.0.0.1 --port $Port
} finally {
    Pop-Location
}
