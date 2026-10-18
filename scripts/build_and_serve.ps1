$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $repoRoot "backend"
$frontendRoot = Join-Path $repoRoot "frontend"
$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonPath)) {
    $pythonPath = (Get-Command python -ErrorAction Stop).Source
}
$npmPath = (Get-Command npm.cmd -ErrorAction Stop).Source

Push-Location $frontendRoot
try {
    & $npmPath run build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend build failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

Write-Host "Serving the frontend and API at http://localhost:8000."
Push-Location $backendRoot
try {
    & $pythonPath -m uvicorn src.api:app --host 127.0.0.1 --port 8000
    if ($LASTEXITCODE -ne 0) {
        throw "FastAPI exited with code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
