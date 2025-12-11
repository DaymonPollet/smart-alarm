# Smart Alarm Setup Script
# ========================
# This script helps you set up the development environment

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Smart Sleep Alarm - Setup Script  " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Python not found. Please install Python 3.8 or higher." -ForegroundColor Red
    exit 1
}

# Check if .env exists
Write-Host ""
Write-Host "Checking configuration..." -ForegroundColor Yellow
if (Test-Path "config\.env") {
    Write-Host "✓ config\.env found" -ForegroundColor Green
} else {
    Write-Host "! config\.env not found. Creating from template..." -ForegroundColor Yellow
    Copy-Item "config\.env.template" -Destination "config\.env"
    Write-Host "✓ Created config\.env - Please edit it with your credentials" -ForegroundColor Green
}

# Create virtual environment
Write-Host ""
Write-Host "Setting up Python virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✓ Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Install cloud dependencies
Write-Host ""
Write-Host "Installing cloud component dependencies..." -ForegroundColor Yellow
pip install -r cloud\requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Cloud dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to install cloud dependencies" -ForegroundColor Red
}

# Install edge dependencies
Write-Host ""
Write-Host "Installing edge component dependencies..." -ForegroundColor Yellow
pip install -r edge\requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Edge dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to install edge dependencies" -ForegroundColor Red
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!                   " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Edit config\.env with your credentials" -ForegroundColor White
Write-Host "2. Set up Fitbit API access at https://dev.fitbit.com/apps" -ForegroundColor White
Write-Host "3. Create Azure IoT Hub and register device" -ForegroundColor White
Write-Host "4. Run: python cloud\fitbit_data_ferry.py" -ForegroundColor White
Write-Host "5. Run: python edge\rpi_smart_alarm.py (on Raspberry Pi)" -ForegroundColor White
Write-Host ""
