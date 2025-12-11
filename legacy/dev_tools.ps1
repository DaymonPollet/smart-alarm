# Development Scripts
# ===================
# Helpful scripts for development and testing

Write-Host "Smart Alarm - Developer Tools" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Write-Host ""

# Load environment variables
function Load-Env {
    Write-Host "Loading environment variables from config\.env..." -ForegroundColor Yellow
    if (Test-Path "config\.env") {
        Get-Content "config\.env" | ForEach-Object {
            if ($_ -match '^([^#][^=]+)=(.*)$') {
                $name = $matches[1].Trim()
                $value = $matches[2].Trim()
                [System.Environment]::SetEnvironmentVariable($name, $value, 'Process')
                Write-Host "  ✓ Loaded: $name" -ForegroundColor Green
            }
        }
    } else {
        Write-Host "  ✗ config\.env not found" -ForegroundColor Red
    }
}

# Test Fitbit API connection
function Test-FitbitAPI {
    Write-Host ""
    Write-Host "Testing Fitbit API Connection..." -ForegroundColor Yellow
    Load-Env
    python -c @"
from fitbit import Fitbit
import os
client_id = os.getenv('FITBIT_CLIENT_ID')
client_secret = os.getenv('FITBIT_CLIENT_SECRET')
access_token = os.getenv('FITBIT_ACCESS_TOKEN')
refresh_token = os.getenv('FITBIT_REFRESH_TOKEN')

if not all([client_id, client_secret, access_token, refresh_token]):
    print('❌ Missing Fitbit credentials')
    exit(1)

try:
    client = Fitbit(client_id, client_secret, access_token=access_token, refresh_token=refresh_token)
    profile = client.user_profile_get()
    print(f'✅ Connected to Fitbit as: {profile[\"user\"][\"displayName\"]}')
    exit(0)
except Exception as e:
    print(f'❌ Fitbit API Error: {e}')
    exit(1)
"@
}

# Test Azure IoT Hub connection (cloud side)
function Test-IoTHubCloud {
    Write-Host ""
    Write-Host "Testing Azure IoT Hub (Cloud Connection)..." -ForegroundColor Yellow
    Load-Env
    python -c @"
from azure.iot.hub import IoTHubRegistryManager
import os

conn_str = os.getenv('IOT_HUB_CONNECTION_STRING')
device_id = os.getenv('TARGET_DEVICE_ID', 'raspberrypi-alarm')

if not conn_str:
    print('❌ IOT_HUB_CONNECTION_STRING not set')
    exit(1)

try:
    registry_manager = IoTHubRegistryManager(conn_str)
    device = registry_manager.get_device(device_id)
    print(f'✅ Connected to IoT Hub')
    print(f'   Device ID: {device.device_id}')
    print(f'   Status: {device.status}')
    exit(0)
except Exception as e:
    print(f'❌ IoT Hub Error: {e}')
    exit(1)
"@
}

# Test Azure IoT Hub connection (device side)
function Test-IoTHubDevice {
    Write-Host ""
    Write-Host "Testing Azure IoT Hub (Device Connection)..." -ForegroundColor Yellow
    Load-Env
    python -c @"
from azure.iot.device import IoTHubDeviceClient
import os

conn_str = os.getenv('IOT_DEVICE_CONNECTION_STRING')

if not conn_str:
    print('❌ IOT_DEVICE_CONNECTION_STRING not set')
    exit(1)

try:
    client = IoTHubDeviceClient.create_from_connection_string(conn_str)
    client.connect()
    print('✅ Device connected to IoT Hub')
    client.disconnect()
    exit(0)
except Exception as e:
    print(f'❌ Device Connection Error: {e}')
    exit(1)
"@
}

# Send test message to device
function Send-TestMessage {
    Write-Host ""
    Write-Host "Sending test sleep data to device..." -ForegroundColor Yellow
    Load-Env
    
    $testMessage = @{
        timestamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        data_type = 'sleep_metrics'
        sleep_stages = @(
            @{timestamp = '2025-11-27T06:00:00'; sleep_stage = 'deep'; duration_seconds = 1800}
            @{timestamp = '2025-11-27T06:30:00'; sleep_stage = 'light'; duration_seconds = 900}
            @{timestamp = '2025-11-27T06:45:00'; sleep_stage = 'light'; duration_seconds = 600}
        )
        heart_rate = @(
            @{time = '06:00:00'; value = 58}
            @{time = '06:30:00'; value = 62}
        )
        hrv = @(
            @{dateTime = '2025-11-27'; value = @{rmssd = 45}}
        )
        device_id = $env:TARGET_DEVICE_ID
    }
    
    $json = $testMessage | ConvertTo-Json -Depth 10
    
    python -c @"
from azure.iot.hub import IoTHubRegistryManager
import os
import json

conn_str = os.getenv('IOT_HUB_CONNECTION_STRING')
device_id = os.getenv('TARGET_DEVICE_ID', 'raspberrypi-alarm')

registry_manager = IoTHubRegistryManager(conn_str)
registry_manager.send_c2d_message(device_id, '$($json -replace "'", "\'")')
print('✅ Test message sent to device')
"@
}

# Run cloud component
function Run-Cloud {
    Write-Host ""
    Write-Host "Starting Cloud Component (Data Ferry)..." -ForegroundColor Yellow
    Load-Env
    python cloud\fitbit_data_ferry.py
}

# Run edge component
function Run-Edge {
    Write-Host ""
    Write-Host "Starting Edge Component (Smart Alarm)..." -ForegroundColor Yellow
    Load-Env
    python edge\rpi_smart_alarm.py
}

# Monitor IoT Hub messages
function Monitor-IoTHub {
    Write-Host ""
    Write-Host "Monitoring IoT Hub messages..." -ForegroundColor Yellow
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
    Load-Env
    
    $hubName = ($env:IOT_HUB_CONNECTION_STRING -split ';')[0] -replace 'HostName=', '' -replace '\.azure-devices\.net', ''
    
    az iot hub monitor-events --hub-name $hubName --output table
}

# Show menu
function Show-Menu {
    Write-Host ""
    Write-Host "Available Commands:" -ForegroundColor Cyan
    Write-Host "==================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1. Load-Env              - Load environment variables" -ForegroundColor White
    Write-Host "  2. Test-FitbitAPI        - Test Fitbit API connection" -ForegroundColor White
    Write-Host "  3. Test-IoTHubCloud      - Test IoT Hub (cloud side)" -ForegroundColor White
    Write-Host "  4. Test-IoTHubDevice     - Test IoT Hub (device side)" -ForegroundColor White
    Write-Host "  5. Send-TestMessage      - Send test data to device" -ForegroundColor White
    Write-Host "  6. Run-Cloud             - Start cloud component" -ForegroundColor White
    Write-Host "  7. Run-Edge              - Start edge component" -ForegroundColor White
    Write-Host "  8. Monitor-IoTHub        - Monitor IoT Hub messages" -ForegroundColor White
    Write-Host ""
    Write-Host "Usage: .\dev_tools.ps1; <Command>" -ForegroundColor Yellow
    Write-Host "Example: .\dev_tools.ps1; Test-FitbitAPI" -ForegroundColor Yellow
    Write-Host ""
}

# Run all tests
function Test-All {
    Write-Host ""
    Write-Host "Running All Tests..." -ForegroundColor Cyan
    Write-Host "==================" -ForegroundColor Cyan
    
    $results = @{
        Fitbit = $false
        CloudIoT = $false
        DeviceIoT = $false
    }
    
    # Test Fitbit
    try {
        Test-FitbitAPI
        if ($LASTEXITCODE -eq 0) { $results.Fitbit = $true }
    } catch {
        Write-Host "Fitbit test failed" -ForegroundColor Red
    }
    
    # Test IoT Hub Cloud
    try {
        Test-IoTHubCloud
        if ($LASTEXITCODE -eq 0) { $results.CloudIoT = $true }
    } catch {
        Write-Host "IoT Hub Cloud test failed" -ForegroundColor Red
    }
    
    # Test IoT Hub Device
    try {
        Test-IoTHubDevice
        if ($LASTEXITCODE -eq 0) { $results.DeviceIoT = $true }
    } catch {
        Write-Host "IoT Hub Device test failed" -ForegroundColor Red
    }
    
    # Summary
    Write-Host ""
    Write-Host "Test Summary:" -ForegroundColor Cyan
    Write-Host "=============" -ForegroundColor Cyan
    foreach ($test in $results.GetEnumerator()) {
        $status = if ($test.Value) { "✅ PASS" } else { "❌ FAIL" }
        $color = if ($test.Value) { "Green" } else { "Red" }
        Write-Host "  $($test.Key): $status" -ForegroundColor $color
    }
    
    $allPassed = ($results.Values | Where-Object { $_ -eq $false }).Count -eq 0
    
    if ($allPassed) {
        Write-Host ""
        Write-Host "🎉 All tests passed! System is ready." -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "⚠ Some tests failed. Check configuration." -ForegroundColor Yellow
    }
}

# Export functions
Export-ModuleMember -Function Load-Env, Test-FitbitAPI, Test-IoTHubCloud, Test-IoTHubDevice, Send-TestMessage, Run-Cloud, Run-Edge, Monitor-IoTHub, Test-All, Show-Menu

# Show menu if run directly
Show-Menu
