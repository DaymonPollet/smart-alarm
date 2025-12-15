import psycopg2
import os
from datetime import datetime

class StorageService:
    def __init__(self):
        self.host = os.getenv('QUESTDB_HOST', 'localhost')
        self.port = os.getenv('QUESTDB_PORT', '8812')
        self.user = os.getenv('QUEST_DB_USER', 'admin')
        self.password = os.getenv('QUEST_DB_PASSWORD', 'Admin.1234')
        self.database = 'qdb'
        self.conn = None
        self._connect()
        
    def _connect(self):
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            self._create_table()
        except Exception as e:
            print(f"Database connection failed: {e}")
    
    def _create_table(self):
        if not self.conn:
            return
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sleep_data (
                    timestamp TIMESTAMP,
                    mean_hr DOUBLE,
                    std_hr DOUBLE,
                    min_hr DOUBLE,
                    max_hr DOUBLE,
                    hrv_rmssd DOUBLE,
                    prediction VARCHAR
                ) timestamp(timestamp) PARTITION BY DAY;
            """)
            self.conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Table creation error: {e}")
    
    def save(self, features, prediction):
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO sleep_data (timestamp, mean_hr, std_hr, min_hr, max_hr, hrv_rmssd, prediction)
                VALUES (NOW(), %s, %s, %s, %s, %s, %s)
            """, (
                features.get('mean_hr'),
                features.get('std_hr'),
                features.get('min_hr'),
                features.get('max_hr'),
                features.get('hrv_rmssd'),
                prediction
            ))
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"Save error: {e}")
            return False
    
    def get_recent(self, limit=100):
        if not self.conn:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT timestamp, mean_hr, std_hr, min_hr, max_hr, hrv_rmssd, prediction
                FROM sleep_data
                ORDER BY timestamp DESC
                LIMIT %s
            """, (limit,))
            results = cursor.fetchall()
            cursor.close()
            
            return [
                {
                    'timestamp': row[0].isoformat() if row[0] else None,
                    'mean_hr': row[1],
                    'std_hr': row[2],
                    'min_hr': row[3],
                    'max_hr': row[4],
                    'hrv_rmssd': row[5],
                    'prediction': row[6]
                }
                for row in results
            ]
        except Exception as e:
            print(f"Query error: {e}")
            return []
