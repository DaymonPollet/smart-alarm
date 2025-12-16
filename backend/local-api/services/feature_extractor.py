from datetime import datetime
from .config import lag_features
from .fitbit_service import fetch_heart_rate_for_date, fetch_activity_for_date

cloud_lag_features = {
    'TotalSteps_Lag1': None,
    'TotalMinutesAsleep_Lag1': None,
    'Calories_Lag1': None,
    'VeryActiveMinutes_Lag1': None
}

def extract_features_for_local_model(session, hr_data=None, previous_session=None):
    """
    Extract features for the LOCAL regression model.
    
    Handles two Fitbit sleep types:
    - "stages": Has detailed sleep stages (deep, light, rem, wake)
    - "classic": Only has basic data (asleep, awake, restless) - estimates deep sleep
    
    Features: revitalization_score, deep_sleep_in_minutes, resting_heart_rate,
              restlessness, DayOfWeek, IsWeekend, WakeupHour, Score_Lag1,
              DeepSleep_Lag1, RHR_Lag1
    """
    global lag_features
    now = datetime.now()
    
    features = {
        'revitalization_score': 70.0,
        'deep_sleep_in_minutes': 0.0,
        'resting_heart_rate': 0.0,
        'restlessness': 0.0,
        'DayOfWeek': now.weekday(),
        'IsWeekend': 1 if now.weekday() >= 5 else 0,
        'WakeupHour': now.hour,
        'Score_Lag1': lag_features.get('Score_Lag1') or 75.0,
        'DeepSleep_Lag1': lag_features.get('DeepSleep_Lag1') or 90.0,
        'RHR_Lag1': lag_features.get('RHR_Lag1') or 65.0
    }
    
    if session:
        end_time = session.get('endTime', '')
        sleep_date = session.get('dateOfSleep', '')
        sleep_type = session.get('type', 'classic')
        
        if end_time:
            try:
                wake_dt = datetime.fromisoformat(end_time.replace('Z', '').split('+')[0])
                features['WakeupHour'] = wake_dt.hour
                features['DayOfWeek'] = wake_dt.weekday()
                features['IsWeekend'] = 1 if wake_dt.weekday() >= 5 else 0
            except:
                pass
        
        levels = session.get('levels', {})
        summary = levels.get('summary', {})
        
        if sleep_type == 'stages':
            deep = summary.get('deep', {})
            if deep.get('minutes') is not None:
                features['deep_sleep_in_minutes'] = float(deep['minutes'])
            
            wake = summary.get('wake', {})
            wake_minutes = wake.get('minutes', 0)
        else:
            minutes_asleep = session.get('minutesAsleep', 0)
            if minutes_asleep > 0:
                features['deep_sleep_in_minutes'] = float(minutes_asleep) * 0.20
            
            restless_data = summary.get('restless', {})
            awake_data = summary.get('awake', {})
            wake_minutes = restless_data.get('minutes', 0) + awake_data.get('minutes', 0)
        
        total_minutes = session.get('minutesAsleep', 0)
        if total_minutes > 0:
            features['restlessness'] = float(wake_minutes / (total_minutes + wake_minutes))
        
        efficiency = session.get('efficiency', 0)
        if efficiency > 0:
            features['revitalization_score'] = float(efficiency)
        
        if sleep_date and (not hr_data or not _has_resting_hr(hr_data)):
            hr_data_for_date = fetch_heart_rate_for_date(sleep_date)
            if hr_data_for_date:
                hr_data = hr_data_for_date
    
    if hr_data and 'activities-heart' in hr_data:
        for day_data in hr_data.get('activities-heart', []):
            resting_hr = day_data.get('value', {}).get('restingHeartRate')
            if resting_hr:
                features['resting_heart_rate'] = float(resting_hr)
                break
    
    if previous_session:
        prev_levels = previous_session.get('levels', {})
        prev_summary = prev_levels.get('summary', {})
        prev_type = previous_session.get('type', 'classic')
        
        if prev_type == 'stages':
            prev_deep = prev_summary.get('deep', {})
            if prev_deep.get('minutes') is not None:
                features['DeepSleep_Lag1'] = float(prev_deep['minutes'])
        else:
            prev_minutes = previous_session.get('minutesAsleep', 0)
            if prev_minutes > 0:
                features['DeepSleep_Lag1'] = float(prev_minutes) * 0.20
        
        prev_efficiency = previous_session.get('efficiency', 0)
        if prev_efficiency > 0:
            features['Score_Lag1'] = float(prev_efficiency)
    
    return features

def _has_resting_hr(hr_data):
    if not hr_data or 'activities-heart' not in hr_data:
        return False
    for day_data in hr_data.get('activities-heart', []):
        if day_data.get('value', {}).get('restingHeartRate'):
            return True
    return False

def update_lag_features(score, deep_sleep, rhr):
    global lag_features
    if score is not None:
        lag_features['Score_Lag1'] = score
    if deep_sleep is not None:
        lag_features['DeepSleep_Lag1'] = deep_sleep
    if rhr is not None and rhr > 0:
        lag_features['RHR_Lag1'] = rhr

def update_cloud_lag_features(steps, minutes_asleep, calories, very_active):
    global cloud_lag_features
    if steps is not None:
        cloud_lag_features['TotalSteps_Lag1'] = steps
    if minutes_asleep is not None:
        cloud_lag_features['TotalMinutesAsleep_Lag1'] = minutes_asleep
    if calories is not None:
        cloud_lag_features['Calories_Lag1'] = calories
    if very_active is not None:
        cloud_lag_features['VeryActiveMinutes_Lag1'] = very_active

def extract_features_for_cloud_model(session, activity_data=None, previous_session=None, previous_activity=None):
    """
    Extract features for the CLOUD classifier model.
    
    Cloud model features (14 total):
    - TotalSteps: Daily step count from activity API
    - TotalMinutesAsleep: Minutes asleep from sleep session
    - TotalTimeInBed: Time in bed from sleep session
    - MinutesAwake_Intraday: Minutes awake during sleep
    - MinutesRestless_Intraday: Minutes restless during sleep
    - Calories: Daily calories burned from activity API
    - VeryActiveMinutes: Very active minutes from activity API
    - SedentaryMinutes: Sedentary minutes from activity API
    - DayOfWeek: 0-6 (Monday-Sunday)
    - IsWeekend: 1 if Saturday/Sunday, 0 otherwise
    - TotalSteps_Lag1: Previous day's steps
    - TotalMinutesAsleep_Lag1: Previous day's sleep minutes
    - Calories_Lag1: Previous day's calories
    - VeryActiveMinutes_Lag1: Previous day's very active minutes
    """
    global cloud_lag_features
    now = datetime.now()
    
    features = {
        'TotalSteps': 0,
        'TotalMinutesAsleep': 0,
        'TotalTimeInBed': 0,
        'MinutesAwake_Intraday': 0,
        'MinutesRestless_Intraday': 0,
        'Calories': 0,
        'VeryActiveMinutes': 0,
        'SedentaryMinutes': 0,
        'DayOfWeek': now.weekday(),
        'IsWeekend': 1 if now.weekday() >= 5 else 0,
        'TotalSteps_Lag1': cloud_lag_features.get('TotalSteps_Lag1') or 5000,
        'TotalMinutesAsleep_Lag1': cloud_lag_features.get('TotalMinutesAsleep_Lag1') or 400,
        'Calories_Lag1': cloud_lag_features.get('Calories_Lag1') or 2000,
        'VeryActiveMinutes_Lag1': cloud_lag_features.get('VeryActiveMinutes_Lag1') or 30
    }
    
    if session:
        sleep_date = session.get('dateOfSleep', '')
        
        if sleep_date:
            try:
                sleep_dt = datetime.strptime(sleep_date, '%Y-%m-%d')
                features['DayOfWeek'] = sleep_dt.weekday()
                features['IsWeekend'] = 1 if sleep_dt.weekday() >= 5 else 0
            except:
                pass
        
        features['TotalMinutesAsleep'] = session.get('minutesAsleep', 0)
        features['TotalTimeInBed'] = session.get('timeInBed', 0)
        features['MinutesAwake_Intraday'] = session.get('minutesAwake', 0)
        
        levels = session.get('levels', {})
        summary = levels.get('summary', {})
        sleep_type = session.get('type', 'classic')
        
        if sleep_type == 'classic':
            restless = summary.get('restless', {})
            features['MinutesRestless_Intraday'] = restless.get('minutes', 0)
        else:
            features['MinutesRestless_Intraday'] = 0
        
        if not activity_data and sleep_date:
            activity_data = fetch_activity_for_date(sleep_date)
    
    if activity_data:
        activity_summary = activity_data.get('summary', {})
        features['TotalSteps'] = activity_summary.get('steps', 0)
        features['Calories'] = activity_summary.get('caloriesOut', 0)
        features['VeryActiveMinutes'] = activity_summary.get('veryActiveMinutes', 0)
        features['SedentaryMinutes'] = activity_summary.get('sedentaryMinutes', 0)
    
    if previous_session:
        features['TotalMinutesAsleep_Lag1'] = previous_session.get('minutesAsleep', 0)
    
    if previous_activity:
        prev_summary = previous_activity.get('summary', {})
        features['TotalSteps_Lag1'] = prev_summary.get('steps', 0)
        features['Calories_Lag1'] = prev_summary.get('caloriesOut', 0)
        features['VeryActiveMinutes_Lag1'] = prev_summary.get('veryActiveMinutes', 0)
    
    return features

def get_sleep_type_info(session):
    """Get information about sleep session type for debugging"""
    if not session:
        return {"type": "unknown", "has_stages": False}
    
    sleep_type = session.get('type', 'classic')
    levels = session.get('levels', {})
    summary = levels.get('summary', {})
    
    return {
        "type": sleep_type,
        "has_stages": sleep_type == 'stages',
        "has_deep": 'deep' in summary,
        "has_rem": 'rem' in summary,
        "has_light": 'light' in summary,
        "summary_keys": list(summary.keys())
    }
