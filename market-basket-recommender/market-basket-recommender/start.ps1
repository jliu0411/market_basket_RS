$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$venvPython = Join-Path $backend '.venv\Scripts\python.exe'
$pidFile = Join-Path $root '.running-processes.json'

function Fail($message) {
    Write-Host "ERROR: $message" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Market Basket Recommender: One-Run Setup ===`n" -ForegroundColor Cyan
if (Test-Path $pidFile) {
    Write-Host 'A previous session file exists. Run stop.bat before starting again.' -ForegroundColor Yellow
    exit 1
}

$python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    try {
        $python = (& py -3 -c 'import sys; print(sys.executable)' 2>$null | Select-Object -First 1)
        if ($LASTEXITCODE -ne 0) { $python = $null }
    } catch { $python = $null }
}
if (-not $python -and (Get-Command python -ErrorAction SilentlyContinue)) {
    $python = (Get-Command python).Source
}
if (-not $python) { Fail 'Install Python 3 from python.org and reopen this folder.' }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    Fail 'Install Node.js LTS (includes npm) from nodejs.org and reopen this folder.'
}

try {
    if (-not (Test-Path $venvPython)) {
        Write-Host '[1/4] Creating Python virtual environment...'
        & $python -m venv (Join-Path $backend '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Python virtual environment creation failed.' }
    }
    Write-Host '[2/4] Checking/installing Python packages...'
    & $venvPython -m pip install -r (Join-Path $backend 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }

    if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
        Write-Host '[3/4] Installing frontend packages (first launch can take a few minutes)...'
        Push-Location $frontend
        try {
            & npm.cmd install
            if ($LASTEXITCODE -ne 0) { throw 'npm install failed.' }
        } finally { Pop-Location }
    } else {
        Write-Host '[3/4] Frontend packages already installed.'
    }

    Write-Host '[4/4] Starting backend and frontend in separate windows...'
    $api = Start-Process -FilePath $venvPython -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $backend -PassThru
    try {
        $ui = Start-Process -FilePath 'cmd.exe' -ArgumentList '/k','npm run dev -- --host 127.0.0.1 --port 5173 --strictPort' -WorkingDirectory $frontend -PassThru
    } catch {
        Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue
        throw
    }
    @{backend_pid=$api.Id; frontend_pid=$ui.Id} | ConvertTo-Json | Set-Content -Path $pidFile -Encoding UTF8
    $ready = $false
    for ($i=0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $result = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 2
            if ($result.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
    }
    if (-not $ready) { Write-Host 'Backend has not responded yet. Check the server windows.' -ForegroundColor Yellow }
    Write-Host "`nFrontend: http://localhost:5173" -ForegroundColor Green
    Write-Host 'API docs: http://127.0.0.1:8000/docs' -ForegroundColor Green
    Write-Host 'To stop both servers: double-click stop.bat' -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    Start-Process 'http://localhost:5173'
} catch {
    Fail $_.Exception.Message
}
