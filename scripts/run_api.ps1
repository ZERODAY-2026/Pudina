$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location (Join-Path $repoRoot "backend")

# Direct alternative from the backend directory:
# uvicorn src.api:app --reload --port 8000
python -m uvicorn src.api:app --reload --port 8000
