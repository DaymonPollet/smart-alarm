# Smart Alarm - Full Application Startup Script
# This script starts all components: Backend API (with integrated model) and Frontend
# Note: Model is now integrated directly into local-api, no separate model service needed

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Smart Alarm - Starting Application   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "[ERROR] .env file not found. Please create it first." -ForegroundColor Red
    exit 1
}

# Check if Python is available
Write-Host "[1/5] Checking Python installation..." -ForegroundColor Yellow
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python is not installed or not in PATH" -ForegroundColor Red
    exit 1
}
Write-Host "      Python found" -ForegroundColor Green

# Check if Node.js is available
Write-Host ""
Write-Host "[2/5] Checking Node.js installation..." -ForegroundColor Yellow
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Node.js is not installed or not in PATH" -ForegroundColor Red
    Write-Host "      Please install Node.js from: https://nodejs.org/" -ForegroundColor Yellow
    exit 1
}
Write-Host "      Node.js found: $(node --version)" -ForegroundColor Green

# Activate virtual environment
Write-Host ""
Write-Host "[3/5] Activating Python virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & .venv\Scripts\Activate.ps1
    Write-Host "      Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Virtual environment not found. Run: python -m venv .venv" -ForegroundColor Red
    exit 1
}

# Check if node_modules exists
Write-Host ""
Write-Host "[4/5] Checking frontend dependencies..." -ForegroundColor Yellow
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "      Installing frontend dependencies (this may take a minute)..." -ForegroundColor Yellow
    Push-Location frontend
    npm install
    Pop-Location
    Write-Host "      Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "      Dependencies already installed" -ForegroundColor Green
}

# Get Python executable path from venv
$pythonExe = Join-Path $PWD ".venv\Scripts\python.exe"

# Start Backend API (with integrated model) in background
Write-Host ""
Write-Host "[5/5] Starting services in background..." -ForegroundColor Yellow
Write-Host "      Starting Backend API (with integrated ML model)..." -ForegroundColor Cyan

$backendJob = Start-Job -ScriptBlock {
    $python = $using:pythonExe
    Set-Location $using:PWD
    Set-Location backend\local-api
    & $python app.py
}

Start-Sleep -Seconds 3

# Start Frontend in background (without activating Python venv)
Write-Host "      Starting Frontend..." -ForegroundColor Cyan

$frontendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    Set-Location frontend
    $env:BROWSER = "none"
    npm start
}

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Verifying services..." -ForegroundColor Yellow

# Wait a bit for services to start
Start-Sleep -Seconds 3

# Check job status
$allRunning = $true
if ($backendJob.State -ne "Running") {
    Write-Host "      [WARNING] Backend API may have failed to start" -ForegroundColor Yellow
    $allRunning = $false
}
if ($frontendJob.State -ne "Running") {
    Write-Host "      [WARNING] Frontend may have failed to start" -ForegroundColor Yellow
    $allRunning = $false
}

if ($allRunning) {
    Write-Host "      All services are running" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Application Started                  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services:" -ForegroundColor White
Write-Host "  - Backend API:   http://localhost:8080 (with integrated ML model)" -ForegroundColor White
Write-Host "  - Frontend:      http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "Job IDs (for monitoring):" -ForegroundColor White
Write-Host "  - Backend API:   $($backendJob.Id)" -ForegroundColor Gray
Write-Host "  - Frontend:      $($frontendJob.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "Commands:" -ForegroundColor White
Write-Host "  - Open frontend:    start http://localhost:3000" -ForegroundColor Gray
Write-Host "  - View logs:        Get-Job | Receive-Job -Keep" -ForegroundColor Gray
Write-Host "  - Stop services:    .\stop-all.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "Opening frontend in browser..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
Start-Process "http://localhost:3000"
