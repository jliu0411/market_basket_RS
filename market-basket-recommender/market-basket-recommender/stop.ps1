$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $root '.running-processes.json'
if (-not (Test-Path $pidFile)) {
    Write-Host 'No saved running session found.' -ForegroundColor Yellow
    exit 0
}
$processIds = Get-Content $pidFile -Raw | ConvertFrom-Json
foreach ($idToStop in @($processIds.backend_pid, $processIds.frontend_pid)) {
    if ($idToStop) {
        # Windows taskkill /T cleans up child processes (e.g. npm/node).
        & taskkill.exe /PID $idToStop /T /F 2>$null | Out-Null
    }
}
Remove-Item $pidFile -Force
Write-Host 'Stopped the saved backend and frontend process trees.' -ForegroundColor Green
