import sqlite3
import json
from .config import DB_PATH

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sleep_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            session_start TEXT,
            session_end TEXT,
            duration_hours REAL,
            efficiency INTEGER,
            minutes_asleep INTEGER,
            minutes_awake INTEGER,
            deep_sleep_minutes REAL,
            resting_heart_rate REAL,
            restlessness REAL,
            local_quality TEXT,
            local_score REAL,
            cloud_quality TEXT,
            cloud_confidence REAL,
            cloud_probabilities TEXT,
            synced_to_cloud INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_sync (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER,
            payload TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (prediction_id) REFERENCES sleep_predictions(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("[DB] Database initialized")

def save_prediction_to_db(prediction_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO sleep_predictions 
        (timestamp, session_start, session_end, duration_hours, efficiency,
         minutes_asleep, minutes_awake, deep_sleep_minutes, resting_heart_rate,
         restlessness, local_quality, local_score, cloud_quality, 
         cloud_confidence, cloud_probabilities, synced_to_cloud)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        prediction_data.get('timestamp'),
        prediction_data.get('start_time'),
        prediction_data.get('timestamp'),
        prediction_data.get('duration_hours'),
        prediction_data.get('efficiency'),
        prediction_data.get('minutes_asleep'),
        prediction_data.get('minutes_awake'),
        prediction_data.get('deep_sleep_minutes'),
        prediction_data.get('resting_heart_rate'),
        prediction_data.get('restlessness'),
        prediction_data.get('local_quality'),
        prediction_data.get('local_score'),
        prediction_data.get('cloud_quality'),
        prediction_data.get('cloud_confidence'),
        json.dumps(prediction_data.get('cloud_probabilities', {})),
        1 if prediction_data.get('cloud_quality') else 0
    ))
    
    prediction_id = cursor.lastrowid
    
    if not prediction_data.get('cloud_quality'):
        cursor.execute('''
            INSERT INTO pending_sync (prediction_id, payload)
            VALUES (?, ?)
        ''', (prediction_id, json.dumps(prediction_data)))
    
    conn.commit()
    conn.close()
    return prediction_id

def get_pending_sync_items():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, prediction_id, payload FROM pending_sync')
    items = cursor.fetchall()
    conn.close()
    return items

def mark_synced(prediction_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE sleep_predictions SET synced_to_cloud = 1 WHERE id = ?', (prediction_id,))
    cursor.execute('DELETE FROM pending_sync WHERE prediction_id = ?', (prediction_id,))
    conn.commit()
    conn.close()
