"""
Alarm service for smart wake-up functionality.
Monitors sleep state and triggers alarm when user is in light sleep within wake window.
"""

from datetime import datetime, timedelta
from .config import config_store

alarm_config = {
    'enabled': False,
    'wake_time': None,
    'window_minutes': 30,
    'triggered': False,
    'trigger_reason': None,
    'last_check': None
}

def set_alarm(wake_time_str, window_minutes=30):
    try:
        wake_time = datetime.strptime(wake_time_str, "%H:%M").time()
        alarm_config['wake_time'] = wake_time_str
        alarm_config['window_minutes'] = window_minutes
        alarm_config['enabled'] = True
        alarm_config['triggered'] = False
        alarm_config['trigger_reason'] = None
        return True
    except ValueError:
        return False

def disable_alarm():
    alarm_config['enabled'] = False
    alarm_config['triggered'] = False
    alarm_config['trigger_reason'] = None

def dismiss_alarm():
    alarm_config['triggered'] = False
    alarm_config['trigger_reason'] = None

def snooze_alarm(minutes=9):
    if alarm_config['triggered']:
        alarm_config['triggered'] = False
        alarm_config['trigger_reason'] = None
        
        now = datetime.now()
        new_wake = (now + timedelta(minutes=minutes)).strftime("%H:%M")
        alarm_config['wake_time'] = new_wake
        return new_wake
    return None

def check_alarm_trigger(sleep_quality=None, is_light_sleep=False):
    if not alarm_config['enabled'] or alarm_config['triggered']:
        return None
    
    if not alarm_config['wake_time']:
        return None
    
    now = datetime.now()
    alarm_config['last_check'] = now.isoformat()
    
    try:
        wake_time = datetime.strptime(alarm_config['wake_time'], "%H:%M").time()
        wake_datetime = datetime.combine(now.date(), wake_time)
        
        if wake_datetime < now:
            wake_datetime += timedelta(days=1)
        
        window_start = wake_datetime - timedelta(minutes=alarm_config['window_minutes'])
        
        if now >= wake_datetime:
            alarm_config['triggered'] = True
            alarm_config['trigger_reason'] = 'wake_time_reached'
            return {
                'trigger': True,
                'reason': 'Wake time reached',
                'time': now.strftime("%H:%M:%S")
            }
        
        if window_start <= now < wake_datetime:
            if is_light_sleep or (sleep_quality and sleep_quality.lower() in ['fair', 'poor']):
                alarm_config['triggered'] = True
                alarm_config['trigger_reason'] = 'light_sleep_detected'
                return {
                    'trigger': True,
                    'reason': 'Light sleep detected in wake window',
                    'time': now.strftime("%H:%M:%S"),
                    'sleep_quality': sleep_quality
                }
    except Exception as e:
        print(f"[ALARM] Check error: {e}")
    
    return None

def get_alarm_status():
    now = datetime.now()
    status = {
        **alarm_config,
        'current_time': now.strftime("%H:%M:%S")
    }
    
    if alarm_config['enabled'] and alarm_config['wake_time']:
        try:
            wake_time = datetime.strptime(alarm_config['wake_time'], "%H:%M").time()
            wake_datetime = datetime.combine(now.date(), wake_time)
            
            if wake_datetime < now and not alarm_config['triggered']:
                wake_datetime += timedelta(days=1)
            
            window_start = wake_datetime - timedelta(minutes=alarm_config['window_minutes'])
            
            status['window_start'] = window_start.strftime("%H:%M")
            status['window_end'] = wake_datetime.strftime("%H:%M")
            status['in_window'] = window_start <= now < wake_datetime
            
            if now < wake_datetime:
                time_until = wake_datetime - now
                status['minutes_until_wake'] = int(time_until.total_seconds() / 60)
        except Exception:
            pass
    
    return status
