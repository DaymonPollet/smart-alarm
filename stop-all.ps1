# Smart Alarm - Stop All Services

Write-Host "Stopping Smart Alarm services..." -ForegroundColor Yellow
Write-Host ""

# Stop all background jobs first
$jobs = Get-Job | Where-Object { $_.State -eq "Running" }
if ($jobs) {
    Write-Host "Stopping background jobs..." -ForegroundColor Yellow
    $jobs | Stop-Job
    $jobs | Remove-Job -Force
    Write-Host "Background jobs stopped" -ForegroundColor Green
}

# Stop Python processes (model service and backend API)
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "Stopping Python services..." -ForegroundColor Yellow
    $pythonProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "Python services stopped" -ForegroundColor Green
}

# Stop Node.js processes (frontend)
$nodeProcesses = Get-Process node -ErrorAction SilentlyContinue
if ($nodeProcesses) {
    Write-Host "Stopping Node.js processes..." -ForegroundColor Yellow
    $nodeProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "Node.js processes stopped" -ForegroundColor Green
}

Write-Host ""
Write-Host "All services stopped" -ForegroundColor Green
