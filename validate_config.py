"""
Configuration Validator for Smart Alarm System
==============================================
This script validates your configuration before running the main components.
"""

import os
import sys
from typing import List, Tuple

# ANSI color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'


def check_env_var(var_name: str, required: bool = True) -> Tuple[bool, str]:
    """
    Check if an environment variable is set.
    
    Args:
        var_name: Name of the environment variable
        required: Whether the variable is required
        
    Returns:
        Tuple of (is_valid, value)
    """
    value = os.getenv(var_name)
    if not value:
        return (not required, "")
    
    # Check if it's still the placeholder value
    if "your_" in value or "_here" in value:
        return (False, value)
    
    return (True, value)


def validate_cloud_config() -> bool:
    """Validate cloud component configuration."""
    print(f"\n{CYAN}{'='*50}")
    print("Validating Cloud Component Configuration")
    print(f"{'='*50}{RESET}\n")
    
    all_valid = True
    
    # Check Fitbit credentials
    print(f"{YELLOW}Fitbit API Credentials:{RESET}")
    
    checks = [
        ("FITBIT_CLIENT_ID", True),
        ("FITBIT_CLIENT_SECRET", True),
        ("FITBIT_ACCESS_TOKEN", True),
        ("FITBIT_REFRESH_TOKEN", True),
    ]
    
    for var_name, required in checks:
        is_valid, value = check_env_var(var_name, required)
        status = f"{GREEN}✓{RESET}" if is_valid else f"{RED}✗{RESET}"
        
        if is_valid:
            masked_value = value[:8] + "..." if len(value) > 8 else value
            print(f"  {status} {var_name}: {masked_value}")
        else:
            print(f"  {status} {var_name}: Not set or placeholder value")
            all_valid = False
    
    # Check Azure IoT Hub
    print(f"\n{YELLOW}Azure IoT Hub Configuration:{RESET}")
    
    checks = [
        ("IOT_HUB_CONNECTION_STRING", True),
        ("TARGET_DEVICE_ID", False),
    ]
    
    for var_name, required in checks:
        is_valid, value = check_env_var(var_name, required)
        status = f"{GREEN}✓{RESET}" if is_valid else f"{RED}✗{RESET}"
        
        if is_valid:
            if "CONNECTION_STRING" in var_name:
                # Extract hostname from connection string
                try:
                    host = [p for p in value.split(';') if 'HostName' in p][0]
                    print(f"  {status} {var_name}: {host}")
                except:
                    print(f"  {status} {var_name}: Set (but may be invalid)")
            else:
                print(f"  {status} {var_name}: {value}")
        else:
            if required:
                print(f"  {status} {var_name}: Not set or placeholder value")
                all_valid = False
            else:
                print(f"  {status} {var_name}: Not set (using default)")
    
    return all_valid


def validate_edge_config() -> bool:
    """Validate edge component configuration."""
    print(f"\n{CYAN}{'='*50}")
    print("Validating Edge Component Configuration")
    print(f"{'='*50}{RESET}\n")
    
    all_valid = True
    
    # Check device connection
    print(f"{YELLOW}Azure IoT Device Configuration:{RESET}")
    
    checks = [
        ("IOT_DEVICE_CONNECTION_STRING", True),
        ("ALARM_TIME", False),
    ]
    
    for var_name, required in checks:
        is_valid, value = check_env_var(var_name, required)
        status = f"{GREEN}✓{RESET}" if is_valid else f"{RED}✗{RESET}"
        
        if is_valid:
            if "CONNECTION_STRING" in var_name:
                try:
                    device_id = [p for p in value.split(';') if 'DeviceId' in p][0]
                    print(f"  {status} {var_name}: {device_id}")
                except:
                    print(f"  {status} {var_name}: Set (but may be invalid)")
            else:
                print(f"  {status} {var_name}: {value}")
        else:
            if required:
                print(f"  {status} {var_name}: Not set or placeholder value")
                all_valid = False
            else:
                print(f"  {status} {var_name}: Not set (using default: 07:00)")
    
    # Check GPIO configuration (optional)
    print(f"\n{YELLOW}GPIO Configuration (Optional):{RESET}")
    
    checks = [
        ("BUZZER_PIN", False),
        ("LED_PIN", False),
    ]
    
    for var_name, required in checks:
        is_valid, value = check_env_var(var_name, required)
        status = f"{GREEN}✓{RESET}" if is_valid else f"{YELLOW}!{RESET}"
        
        if is_valid:
            print(f"  {status} {var_name}: {value}")
        else:
            print(f"  {status} {var_name}: Not set (using default)")
    
    return all_valid


def check_dependencies() -> bool:
    """Check if required Python packages are installed."""
    print(f"\n{CYAN}{'='*50}")
    print("Checking Python Dependencies")
    print(f"{'='*50}{RESET}\n")
    
    required_packages = [
        ("fitbit", "Fitbit API client"),
        ("azure.iot.hub", "Azure IoT Hub Service SDK"),
        ("azure.iot.device", "Azure IoT Device SDK"),
        ("numpy", "NumPy for numerical computations"),
    ]
    
    all_installed = True
    
    for package, description in required_packages:
        try:
            __import__(package.replace('-', '_').split('.')[0])
            print(f"  {GREEN}✓{RESET} {package}: {description}")
        except ImportError:
            print(f"  {RED}✗{RESET} {package}: {description} - NOT INSTALLED")
            all_installed = False
    
    return all_installed


def main():
    """Main validation routine."""
    print(f"\n{CYAN}{'='*60}")
    print("    Smart Sleep Alarm - Configuration Validator")
    print(f"{'='*60}{RESET}")
    
    # Load .env file if it exists
    env_file = os.path.join("config", ".env")
    if os.path.exists(env_file):
        print(f"\n{GREEN}✓{RESET} Found config/.env file")
        print(f"{YELLOW}Loading environment variables...{RESET}")
        
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    else:
        print(f"\n{RED}✗{RESET} config/.env file not found")
        print(f"{YELLOW}Please create it from config/.env.template{RESET}")
        return False
    
    # Run validations
    deps_valid = check_dependencies()
    cloud_valid = validate_cloud_config()
    edge_valid = validate_edge_config()
    
    # Summary
    print(f"\n{CYAN}{'='*60}")
    print("Validation Summary")
    print(f"{'='*60}{RESET}\n")
    
    if deps_valid:
        print(f"{GREEN}✓{RESET} Dependencies: All required packages installed")
    else:
        print(f"{RED}✗{RESET} Dependencies: Some packages missing")
        print(f"  Run: pip install -r cloud/requirements.txt")
        print(f"  Run: pip install -r edge/requirements.txt")
    
    if cloud_valid:
        print(f"{GREEN}✓{RESET} Cloud Config: Ready to run fitbit_data_ferry.py")
    else:
        print(f"{RED}✗{RESET} Cloud Config: Missing required configuration")
    
    if edge_valid:
        print(f"{GREEN}✓{RESET} Edge Config: Ready to run rpi_smart_alarm.py")
    else:
        print(f"{RED}✗{RESET} Edge Config: Missing required configuration")
    
    all_valid = deps_valid and cloud_valid and edge_valid
    
    print()
    if all_valid:
        print(f"{GREEN}{'='*60}")
        print("✓ All checks passed! Your system is ready to run.")
        print(f"{'='*60}{RESET}\n")
        return True
    else:
        print(f"{RED}{'='*60}")
        print("✗ Some checks failed. Please fix the issues above.")
        print(f"{'='*60}{RESET}\n")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
