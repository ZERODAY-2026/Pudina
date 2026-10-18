$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $repoRoot "backend"
$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonPath)) {
    $pythonPath = (Get-Command python -ErrorAction Stop).Source
}
$npmPath = (Get-Command npm.cmd -ErrorAction Stop).Source

function Assert-PortAvailable([int]$Port) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    try {
        $listener.Start()
    }
    catch [System.Net.Sockets.SocketException] {
        throw "Port $Port is already in use. Stop its current service before starting DataMind."
    }
    finally {
        $listener.Stop()
    }
}

function Wait-ForListener([int]$Port, [string]$ServiceName) {
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $client = [System.Net.Sockets.TcpClient]::new()
        try {
            $connection = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
            if ($connection.AsyncWaitHandle.WaitOne(500) -and $client.Connected) {
                return
            }
        }
        catch [System.Net.Sockets.SocketException] {
        }
        finally {
            $client.Close()
        }
        Start-Sleep -Seconds 1
    }
    throw "$ServiceName did not become available on port $Port."
}

Assert-PortAvailable 8000
Assert-PortAvailable 5173

$api = $null
$vite = $null
try {
    $api = Start-Process `
        -FilePath $pythonPath `
        -ArgumentList @("-m", "uvicorn", "src.api:app", "--reload", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $backendRoot `
        -PassThru

    $vite = Start-Process `
        -FilePath $npmPath `
        -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort") `
        -WorkingDirectory (Join-Path $repoRoot "frontend") `
        -PassThru

    Wait-ForListener 8000 "FastAPI"
    Wait-ForListener 5173 "Vite"
    Write-Host "FastAPI is available at http://localhost:8000 (PID $($api.Id))."
    Write-Host "Vite is available at http://localhost:5173 (PID $($vite.Id))."
    Write-Host "Each server runs in its own console window; stop it with Ctrl+C."
}
catch {
    if ($null -ne $api -and -not $api.HasExited) {
        Stop-Process -Id $api.Id
    }
    if ($null -ne $vite -and -not $vite.HasExited) {
        Stop-Process -Id $vite.Id
    }
    throw
}
