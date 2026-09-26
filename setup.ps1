# One-time setup for Truescope.
# Safe to run again after updating: it never overwrites your settings (backend\.env).
# Usage (PowerShell, in the project folder):  .\setup.ps1

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$venv = Join-Path $backend 'venv'
$venvPython = Join-Path (Join-Path $venv 'Scripts') 'python.exe'

function Fail($message) {
    Write-Host ''
    Write-Host $message -ForegroundColor Red
    exit 1
}

function Step($message) {
    Write-Host ''
    Write-Host "==> $message" -ForegroundColor Cyan
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Fail 'Python was not found. Install Python 3.11 or newer from python.org (tick "Add python.exe to PATH"), then open a new PowerShell window and run .\setup.ps1 again.'
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Fail 'Node.js was not found. Install Node.js 22 LTS from nodejs.org, then open a new PowerShell window and run .\setup.ps1 again.'
}

Step 'Python environment'
if (-not (Test-Path $venvPython)) {
    & python -m venv $venv
    if ($LASTEXITCODE -ne 0) { Fail 'Could not create the Python environment (backend\venv).' }
    Write-Host 'Created backend\venv'
} else {
    Write-Host 'backend\venv already exists'
}

Step 'Python packages (the first time this includes PyTorch and can take several minutes)'
& $venvPython -m pip install -r (Join-Path $backend 'requirements-dev.txt')
if ($LASTEXITCODE -ne 0) { Fail 'Installing Python packages failed. Check your internet connection and run .\setup.ps1 again.' }

Step 'Settings'
$envFile = Join-Path $backend '.env'
if (Test-Path $envFile) {
    Write-Host 'Kept your existing settings in backend\.env'
} else {
    Copy-Item (Join-Path $backend '.env.example') $envFile
    Write-Host 'Created backend\.env. To turn on AI, open it with "notepad backend\.env" and add your Gemini key.'
}

Step 'Web page (npm install and build)'
Push-Location $frontend
try {
    & npm install
    if ($LASTEXITCODE -ne 0) { Fail 'npm install failed. Check your internet connection and run .\setup.ps1 again.' }
    & npm run build
    if ($LASTEXITCODE -ne 0) { Fail 'Building the web page failed. See the messages above.' }
} finally {
    Pop-Location
}

Write-Host ''
Write-Host 'Setup complete. Start Truescope with:  .\start.ps1' -ForegroundColor Green
