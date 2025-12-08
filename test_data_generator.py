"""
Test Data Generator for Smart Alarm System
==========================================
Generates realistic mock sleep data for testing without Fitbit API
"""
# this is purely for testing purposes as I may lack enough real data to train the model well
import json
from datetime import datetime, timedelta
import random


def generate_heart_rate_data(start_time, duration_hours=8):
    """
    Generate realistic heart rate data during sleep.
    
    Args:
        start_time: Start time as datetime
        duration_hours: Duration of sleep in hours
        
    Returns:
        List of heart rate data points (minute-level)
    """
    hr_data = []
    base_hr = 58  # Typical resting heart rate
    
    for minute in range(duration_hours * 60):
        current_time = start_time + timedelta(minutes=minute)
        
        # Add some variation
        # Deep sleep: lower HR (55-60)
        # Light sleep: moderate HR (58-65)
        # REM sleep: higher HR (60-70)
        hour = minute // 60
        
        if hour < 2:  # First 2 hours - typically deep sleep
            hr = base_hr + random.randint(-3, 2)
        elif hour < 6:  # Middle hours - mixed stages
            hr = base_hr + random.randint(0, 7)
        else:  # Last 2 hours - lighter sleep, approaching wake
            hr = base_hr + random.randint(2, 12)
        
        hr_data.append({
            'time': current_time.strftime('%H:%M:%S'),
            'value': hr
        })
    
    return hr_data


def generate_sleep_stages(start_time, duration_hours=8):
    """
    Generate realistic sleep stage progression.
    
    Typical sleep architecture:
    - First cycle: Deep sleep dominant
    - Middle cycles: Mix of deep, light, REM
    - Final cycles: More light sleep and REM
    
    Args:
        start_time: Start time as datetime
        duration_hours: Duration of sleep in hours
        
    Returns:
        List of sleep stage data points
    """
    stages = []
    current_time = start_time
    
    # Define a typical sleep cycle pattern (90 minutes)
    cycle_patterns = [
        # Cycle 1 (0-90 min): Heavy deep sleep
        [
            ('light', 10),
            ('deep', 60),
            ('light', 15),
            ('rem', 5)
        ],
        # Cycle 2 (90-180 min): Moderate deep sleep
        [
            ('light', 15),
            ('deep', 40),
            ('light', 20),
            ('rem', 15)
        ],
        # Cycle 3 (180-270 min): Less deep, more REM
        [
            ('light', 20),
            ('deep', 20),
            ('light', 25),
            ('rem', 25)
        ],
        # Cycle 4 (270-360 min): Light and REM dominant
        [
            ('light', 30),
            ('deep', 10),
            ('light', 20),
            ('rem', 30)
        ],
        # Cycle 5 (360-450 min): Preparing to wake
        [
            ('light', 35),
            ('rem', 25),
            ('light', 20),
            ('wake', 10)
        ]
    ]
    
    num_cycles = min(duration_hours // 1.5, len(cycle_patterns))
    
    for cycle_idx in range(int(num_cycles)):
        pattern = cycle_patterns[min(cycle_idx, len(cycle_patterns) - 1)]
        
        for stage_name, duration_min in pattern:
            stages.append({
                'timestamp': current_time.isoformat(),
                'sleep_stage': stage_name,
                'duration_seconds': duration_min * 60
            })
            current_time += timedelta(minutes=duration_min)
    
    # Fill remaining time with light sleep
    if current_time < start_time + timedelta(hours=duration_hours):
        remaining_minutes = int((start_time + timedelta(hours=duration_hours) - current_time).total_seconds() / 60)
        stages.append({
            'timestamp': current_time.isoformat(),
            'sleep_stage': 'light',
            'duration_seconds': remaining_minutes * 60
        })
    
    return stages


def generate_hrv_data(date, quality='good'):
    """
    Generate HRV (Heart Rate Variability) data.
    
    Args:
        date: Date string in YYYY-MM-DD format
        quality: Sleep quality level ('excellent', 'good', 'fair', 'poor')
        
    Returns:
        List of HRV data points
    """
    hrv_values = {
        'excellent': random.randint(60, 80),
        'good': random.randint(40, 60),
        'fair': random.randint(25, 40),
        'poor': random.randint(10, 25)
    }
    
    rmssd = hrv_values.get(quality, 45)
    
    return [{
        'dateTime': date,
        'value': {
            'rmssd': rmssd,
            'coverage': 0.95,
            'hf': rmssd * 1.5,
            'lf': rmssd * 0.8
        }
    }]


def generate_complete_sleep_data(
    sleep_date=None,
    sleep_start_hour=23,
    duration_hours=8,
    quality='good'
):
    """
    Generate complete sleep data payload for testing.
    
    Args:
        sleep_date: Date of sleep (defaults to yesterday)
        sleep_start_hour: Hour when sleep started (24-hour format)
        duration_hours: Total sleep duration in hours
        quality: Sleep quality ('excellent', 'good', 'fair', 'poor')
        
    Returns:
        Complete sleep data payload ready to send to device
    """
    if sleep_date is None:
        sleep_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Calculate sleep start time
    sleep_start = datetime.strptime(
        f"{sleep_date} {sleep_start_hour:02d}:00:00",
        '%Y-%m-%d %H:%M:%S'
    )
    
    # Generate all components
    sleep_stages = generate_sleep_stages(sleep_start, duration_hours)
    heart_rate = generate_heart_rate_data(sleep_start, duration_hours)
    hrv = generate_hrv_data(sleep_date, quality)
    
    # Create complete payload
    payload = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'data_type': 'sleep_metrics',
        'sleep_stages': sleep_stages,
        'heart_rate': heart_rate,
        'hrv': hrv,
        'device_id': 'raspberrypi-alarm',
        'test_data': True,
        'quality_level': quality
    }
    
    return payload


def save_test_data(filename='test_sleep_data.json'):
    """Generate and save test data to a file."""
    print(f"Generating test sleep data...")
    
    scenarios = [
        ('excellent', 'Excellent sleep - long deep sleep periods'),
        ('good', 'Good sleep - normal sleep architecture'),
        ('fair', 'Fair sleep - some disruptions'),
        ('poor', 'Poor sleep - frequent wake periods')
    ]
    
    test_cases = {}
    
    for quality, description in scenarios:
        print(f"  Generating {quality} sleep data...")
        data = generate_complete_sleep_data(quality=quality)
        test_cases[quality] = {
            'description': description,
            'data': data
        }
    
    with open(filename, 'w') as f:
        json.dump(test_cases, f, indent=2)
    
    print(f"\n✓ Test data saved to {filename}")
    print(f"\nGenerated {len(scenarios)} test scenarios:")
    for quality, description in scenarios:
        sleep_stages = test_cases[quality]['data']['sleep_stages']
        hr_points = len(test_cases[quality]['data']['heart_rate'])
        print(f"  • {quality.capitalize()}: {len(sleep_stages)} sleep stages, {hr_points} HR points")


def print_sample_data():
    """Print a sample payload to console."""
    print("\n" + "="*60)
    print("Sample Sleep Data Payload")
    print("="*60 + "\n")
    
    data = generate_complete_sleep_data(quality='good')
    
    print("Sleep Stages Summary:")
    stage_counts = {}
    for stage in data['sleep_stages']:
        stage_name = stage['sleep_stage']
        stage_counts[stage_name] = stage_counts.get(stage_name, 0) + 1
    
    for stage, count in stage_counts.items():
        print(f"  {stage.capitalize()}: {count} periods")
    
    print(f"\nHeart Rate Data Points: {len(data['heart_rate'])}")
    print(f"HRV Values: {len(data['hrv'])}")
    
    print("\nFirst few sleep stages:")
    for i, stage in enumerate(data['sleep_stages'][:5]):
        print(f"  {i+1}. {stage['sleep_stage'].ljust(6)} - {stage['duration_seconds']//60} min at {stage['timestamp']}")
    
    print("\nJSON Payload (first 500 chars):")
    json_str = json.dumps(data, indent=2)
    print(json_str[:500] + "...")
    print(f"\nTotal payload size: {len(json_str)} bytes")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'generate':
        # Generate and save test data files
        save_test_data()
    else:
        # Print sample to console
        print_sample_data()
        print("\n" + "="*60)
        print("To generate test data files, run:")
        print("  python test_data_generator.py generate")
        print("="*60)
