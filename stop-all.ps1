# smart alarm -> most gracefull way i managed to stop the program

Write-Host "Stopping Smart Alarm services..." -ForegroundColor Yellow
Write-Host ""

# stop background processes first (otherwise some stuff will respawn)
$jobs = Get-Job | Where-Object { $_.State -eq "Running" }
if ($jobs) {
    Write-Host "Stopping background jobs..." -ForegroundColor Yellow
    $jobs | Stop-Job
    $jobs | Remove-Job -Force
    Write-Host "Background jobs stopped" -ForegroundColor Green
}

# stop python backend (this is model service and api)
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "Stopping Python services..." -ForegroundColor Yellow
    $pythonProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "Python services stopped" -ForegroundColor Green
}

# stop node.js frontend
$nodeProcesses = Get-Process node -ErrorAction SilentlyContinue
if ($nodeProcesses) {
    Write-Host "Stopping Node.js processes..." -ForegroundColor Yellow
    $nodeProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "Node.js processes stopped" -ForegroundColor Green
}

Write-Host ""
Write-Host "All services stopped" -ForegroundColor Green
