import random
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EnvironmentSensor:
    """
    Simulates an environment sensor connected to the Raspberry Pi.
    Captures Temperature, Humidity, and Noise Level.
    """
    
    def __init__(self):
        logger.info("Initializing Environment Sensor")
        
    def read_sensor_data(self):
        """
        Simulate reading data from physical sensors.
        
        Returns:
            Dictionary containing sensor readings.
        """
        # Simulate temperature between 18 and 25 degrees Celsius
        temperature = round(random.uniform(18.0, 25.0), 1)
        
        # Simulate humidity between 30% and 60%
        humidity = round(random.uniform(30.0, 60.0), 1)
        
        # Simulate noise level in dB (30-50 for quiet room)
        noise_level = round(random.uniform(30.0, 50.0), 1)
        
        data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'temperature': temperature,
            'humidity': humidity,
            'noise_level': noise_level
        }
        
        logger.debug(f"Sensor reading: {data}")
        return data
