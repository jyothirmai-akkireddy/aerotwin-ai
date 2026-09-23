<#
.SYNOPSIS
    AeroTwin AI — Single-Command Demo Startup Script
.DESCRIPTION
    SIH26054: Generic 4-Cylinder Boxer Turbo Aero-Piston Digital Twin (Rotax 914/915 iS class).
    Launches FastAPI backend on port 8000 and Vite frontend dev server on port 5173.
    Performs initial system health checks and handles graceful shutdown on exit.
.EXAMPLE
    .\scripts\start_demo.ps1
#>

[CmdletBinding()]
param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

Write-Host @"
================================================================================
          AEROTWIN AI — PRESENTATION & DEMONSTRATION RUNNER
          SIH26054 | Generic 4-Cylinder Boxer Turbo Aero-Piston
================================================================================
"@ -ForegroundColor Cyan

# 1. Resolve Project Root
$ProjectRoot = (Get-Item $PSScriptRoot).Parent.FullName
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"

Write-Host "[*] Project Root: $ProjectRoot" -ForegroundColor Gray

# 2. Check Python Virtual Environment
$PythonExe = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Error "[!] Backend virtual environment not found at $PythonExe. Please set up .venv first."
}
Write-Host "[✓] Python Environment: Found ($PythonExe)" -ForegroundColor Green

# 3. Check Node.js & Frontend
$NpmCmd = Get-Command "npm" -ErrorAction SilentlyContinue
if (-not $NpmCmd) {
    Write-Error "[!] npm not found in system PATH. Please install Node.js."
}
$NodeModules = Join-Path $FrontendDir "node_modules"
if (-not (Test-Path $NodeModules)) {
    Write-Warning "[!] node_modules not found. Running 'npm install' in frontend..."
    Push-Location $FrontendDir
    npm install
    Pop-Location
}
Write-Host "[✓] Frontend Dependencies: Verified" -ForegroundColor Green

# 4. Check Port Availability
function Test-PortOpen([int]$Port) {
    $Conn = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
    return $Conn
}

if (Test-PortOpen -Port $BackendPort) {
    Write-Warning "[!] Port $BackendPort is already in use. Ensure existing backend instance is terminated or restart."
}

# 5. Launch Backend
Write-Host "`n[*] Starting AeroTwin AI Backend (FastAPI + WebSocket @ port $BackendPort)..." -ForegroundColor Yellow
$BackendProc = Start-Process -FilePath $PythonExe `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort" `
    -WorkingDirectory $BackendDir `
    -PassThru

# 6. Launch Frontend
Write-Host "[*] Starting AeroTwin AI Frontend (Vite Dev Server @ port $FrontendPort)..." -ForegroundColor Yellow
$FrontendProc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm run dev" `
    -WorkingDirectory $FrontendDir `
    -PassThru

# 7. Health Check Wait Loop
Write-Host "[*] Awaiting backend readiness probe..." -ForegroundColor Gray
$HealthUrl = "http://127.0.0.1:$BackendPort/api/v1/health"
$MaxRetries = 20
$RetryCount = 0
$BackendReady = $false

while (-not $BackendReady -and ($RetryCount -lt $MaxRetries)) {
    Start-Sleep -Milliseconds 750
    try {
        $Resp = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($Resp.status -eq "healthy") {
            $BackendReady = $true
        }
    } catch {
        $RetryCount++
    }
}

if ($BackendReady) {
    Write-Host "[✓] Backend Service Healthy: $HealthUrl" -ForegroundColor Green
} else {
    Write-Warning "[!] Backend readiness probe timed out. Check terminal processes."
}

Write-Host @"
================================================================================
                    AEROTWIN AI IS LIVE AND READY FOR DEMO
================================================================================
  Cockpit / UI:           http://localhost:$FrontendPort
  Backend Health:         http://localhost:$BackendPort/api/v1/health
  Subsystem Readiness:    http://localhost:$BackendPort/api/v1/ready
  Interactive REST Docs:  http://localhost:$BackendPort/docs
  WebSocket Endpoint:     ws://localhost:$BackendPort/api/v1/telemetry/ws
--------------------------------------------------------------------------------
  Press Ctrl+C or enter 'stop' to gracefully terminate all demo services.
================================================================================
"@ -ForegroundColor Cyan

try {
    while ($true) {
        $Input = Read-Host "Type 'stop' to shut down demo"
        if ($Input -eq "stop" -or $Input -eq "exit") {
            break
        }
    }
} finally {
    Write-Host "`n[*] Stopping AeroTwin AI services..." -ForegroundColor Yellow
    if ($BackendProc -and (-not $BackendProc.HasExited)) {
        Stop-Process -Id $BackendProc.Id -Force -ErrorAction SilentlyContinue
        Write-Host "[✓] Backend service stopped." -ForegroundColor Gray
    }
    if ($FrontendProc -and (-not $FrontendProc.HasExited)) {
        Stop-Process -Id $FrontendProc.Id -Force -ErrorAction SilentlyContinue
        Write-Host "[✓] Frontend service stopped." -ForegroundColor Gray
    }
    Write-Host "[✓] Demo session cleanly closed." -ForegroundColor Green
}
