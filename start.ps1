# Smart Alarm - Main Launcher
# ============================
# Interactive launcher for the Smart Alarm System

param(
    [Parameter(Position=0)]
    [ValidateSet('setup', 'validate', 'test', 'cloud', 'edge', 'dev', 'help')]
    [string]$Command = 'help'
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Header($text) {
    Write-Host ""
    Write-Host "=" * 70 -ForegroundColor Cyan
    Write-Host " $text" -ForegroundColor Cyan
    Write-Host "=" * 70 -ForegroundColor Cyan
    Write-Host ""
}

function Write-Success($text) {
    Write-Host "✓ $text" -ForegroundColor Green
}

function Write-Error($text) {
    Write-Host "✗ $text" -ForegroundColor Red
}

function Write-Info($text) {
    Write-Host "ℹ $text" -ForegroundColor Yellow
}

function Show-MainMenu {
    Write-Header "Smart Sleep Alarm System - Main Menu"
    
    Write-Host "Available Commands:" -ForegroundColor White
    Write-Host ""
    Write-Host "  setup      " -NoNewline -ForegroundColor Yellow
    Write-Host "- Run initial setup (install dependencies, create config)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  validate   " -NoNewline -ForegroundColor Yellow
    Write-Host "- Validate configuration and test connections" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  test       " -NoNewline -ForegroundColor Yellow
    Write-Host "- Run all system tests" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  cloud      " -NoNewline -ForegroundColor Yellow
    Write-Host "- Start the cloud data ferry component" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  edge       " -NoNewline -ForegroundColor Yellow
    Write-Host "- Start the edge alarm component (simulation mode)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  dev        " -NoNewline -ForegroundColor Yellow
    Write-Host "- Open developer tools menu" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  help       " -NoNewline -ForegroundColor Yellow
    Write-Host "- Show this help message" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Usage: " -NoNewline -ForegroundColor White
    Write-Host ".\start.ps1 <command>" -ForegroundColor Yellow
    Write-Host "Example: " -NoNewline -ForegroundColor White
    Write-Host ".\start.ps1 setup" -ForegroundColor Yellow
    Write-Host ""
}

# Setup command
function Invoke-Setup {
    Write-Header "Running Setup"
    
    Write-Info "This will install dependencies and create configuration files."
    Write-Host ""
    
    if (Test-Path ".\setup.ps1") {
        & ".\setup.ps1"
    } else {
        Write-Error "setup.ps1 not found!"
        exit 1
    }
    
    Write-Host ""
    Write-Success "Setup complete!"
    Write-Info "Next step: Edit config\.env with your credentials"
    Write-Info "Then run: .\start.ps1 validate"
}

# Validate command
function Invoke-Validate {
    Write-Header "Validating Configuration"
    
    if (-not (Test-Path "config\.env")) {
        Write-Error "config\.env not found!"
        Write-Info "Run: .\start.ps1 setup"
        exit 1
    }
    
    # Activate virtual environment if it exists
    if (Test-Path "venv\Scripts\Activate.ps1") {
        Write-Info "Activating virtual environment..."
        & "venv\Scripts\Activate.ps1"
    }
    
    python validate_config.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Success "All validations passed!"
        Write-Info "You can now run the components:"
        Write-Info "  Cloud: .\start.ps1 cloud"
        Write-Info "  Edge:  .\start.ps1 edge"
    } else {
        Write-Host ""
        Write-Error "Some validations failed. Please fix the issues above."
    }
}

# Test command
function Invoke-Test {
    Write-Header "Running All Tests"
    
    # Load dev tools and run tests
    if (Test-Path ".\dev_tools.ps1") {
        . ".\dev_tools.ps1"
        Test-All
    } else {
        Write-Error "dev_tools.ps1 not found!"
        exit 1
    }
}

# Cloud command
function Invoke-Cloud {
    Write-Header "Starting Cloud Component (Data Ferry)"
    
    if (-not (Test-Path "config\.env")) {
        Write-Error "config\.env not found! Run: .\start.ps1 setup"
        exit 1
    }
    
    # Activate virtual environment
    if (Test-Path "venv\Scripts\Activate.ps1") {
        & "venv\Scripts\Activate.ps1"
    }
    
    # Load environment variables
    Write-Info "Loading environment variables..."
    Get-Content "config\.env" | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($name, $value, 'Process')
        }
    }
    
    Write-Info "Starting Fitbit Data Ferry..."
    Write-Host ""
    
    python cloud\fitbit_data_ferry.py
}

# Edge command
function Invoke-Edge {
    Write-Header "Starting Edge Component (Smart Alarm)"
    
    if (-not (Test-Path "config\.env")) {
        Write-Error "config\.env not found! Run: .\start.ps1 setup"
        exit 1
    }
    
    # Activate virtual environment
    if (Test-Path "venv\Scripts\Activate.ps1") {
        & "venv\Scripts\Activate.ps1"
    }
    
    # Load environment variables
    Write-Info "Loading environment variables..."
    Get-Content "config\.env" | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($name, $value, 'Process')
        }
    }
    
    Write-Info "Starting Raspberry Pi Smart Alarm (Simulation Mode)..."
    Write-Host ""
    
    python edge\rpi_smart_alarm.py
}

# Dev command
function Invoke-Dev {
    Write-Header "Developer Tools"
    
    if (Test-Path ".\dev_tools.ps1") {
        . ".\dev_tools.ps1"
        Show-Menu
        
        Write-Host ""
        Write-Info "Dev tools loaded! Available functions:"
        Write-Host "  • Load-Env"
        Write-Host "  • Test-FitbitAPI"
        Write-Host "  • Test-IoTHubCloud"
        Write-Host "  • Test-IoTHubDevice"
        Write-Host "  • Send-TestMessage"
        Write-Host "  • Run-Cloud"
        Write-Host "  • Run-Edge"
        Write-Host "  • Monitor-IoTHub"
        Write-Host "  • Test-All"
        Write-Host ""
        Write-Info "Run any function directly, e.g.: Test-FitbitAPI"
    } else {
        Write-Error "dev_tools.ps1 not found!"
    }
}

# Help command
function Show-Help {
    Show-MainMenu
    
    Write-Host "Quick Start Guide:" -ForegroundColor White
    Write-Host ""
    Write-Host "  1. Run setup to install dependencies:" -ForegroundColor Gray
    Write-Host "     .\start.ps1 setup" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  2. Edit config\.env with your credentials:" -ForegroundColor Gray
    Write-Host "     notepad config\.env" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  3. Validate your configuration:" -ForegroundColor Gray
    Write-Host "     .\start.ps1 validate" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  4. Test the cloud component:" -ForegroundColor Gray
    Write-Host "     .\start.ps1 cloud" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  5. Test the edge component:" -ForegroundColor Gray
    Write-Host "     .\start.ps1 edge" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "For detailed documentation, see:" -ForegroundColor White
    Write-Host "  • README.md       - Complete documentation" -ForegroundColor Gray
    Write-Host "  • QUICKSTART.md   - Fast setup guide" -ForegroundColor Gray
    Write-Host "  • ARCHITECTURE.md - Technical details" -ForegroundColor Gray
    Write-Host ""
}

# Main execution
try {
    switch ($Command) {
        'setup' { Invoke-Setup }
        'validate' { Invoke-Validate }
        'test' { Invoke-Test }
        'cloud' { Invoke-Cloud }
        'edge' { Invoke-Edge }
        'dev' { Invoke-Dev }
        'help' { Show-Help }
        default { Show-Help }
    }
} catch {
    Write-Host ""
    Write-Error "An error occurred: $_"
    Write-Host ""
    exit 1
}
