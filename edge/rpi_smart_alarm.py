"""
Raspberry Pi Smart Alarm - Edge AI Device
=========================================
This module runs on the Raspberry Pi 5 and handles:
- Receiving sleep data from Azure IoT Hub
- Running AI model to determine optimal wake-up time
- Managing the physical alarm system

It uses the IoTHubDeviceClient to connect to Azure IoT Hub as a device.
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading

# Azure IoT Device SDK
from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse

# NumPy for numerical computations
import numpy as np

# For GPIO control (alarm buzzer/LED)
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO not available - running in simulation mode")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SleepStagePredictor:
    """
    AI Model for predicting optimal wake-up time based on sleep data.
    
    This is a simplified model that analyzes:
    - Sleep stages (light, deep, REM, wake)
    - Heart rate patterns
    - HRV (Heart Rate Variability)
    - Movement patterns
    """
    
    def __init__(self):
        """Initialize the sleep stage predictor model."""
        logger.info("Initializing Sleep Stage Predictor AI model")
        
        # Model parameters (these would be trained in a real implementation)
        self.light_sleep_weight = 1.0
        self.hrv_weight = 0.5
        self.movement_weight = 0.3
        
    def analyze_sleep_data(self, sleep_data: Dict) -> Dict:
        """
        Analyze incoming sleep data to identify patterns.
        
        Args:
            sleep_data: Combined sleep metrics from Fitbit
            
        Returns:
            Analysis results with wake-up recommendations
        """
        logger.info("Analyzing sleep data for optimal wake-up prediction...")
        
        sleep_stages = sleep_data.get('sleep_stages', [])
        heart_rate = sleep_data.get('heart_rate', [])
        hrv = sleep_data.get('hrv', [])
        
        if not sleep_stages:
            logger.warning("No sleep stage data available")
            return {'status': 'insufficient_data'}
        
        # Find light sleep periods
        light_sleep_periods = self._find_light_sleep_periods(sleep_stages)
        
        # Calculate sleep quality score
        sleep_quality = self._calculate_sleep_quality(sleep_stages, heart_rate, hrv)
        
        # Predict optimal wake-up times
        optimal_times = self._predict_optimal_wake_times(
            light_sleep_periods,
            sleep_stages,
            heart_rate
        )
        
        analysis = {
            'status': 'success',
            'light_sleep_periods': light_sleep_periods,
            'sleep_quality_score': sleep_quality,
            'optimal_wake_times': optimal_times,
            'total_sleep_minutes': sum(s.get('duration_seconds', 0) for s in sleep_stages) / 60,
            'current_stage': sleep_stages[-1].get('sleep_stage') if sleep_stages else 'unknown'
        }
        
        logger.info(f"Analysis complete. Sleep quality: {sleep_quality:.2f}, "
                   f"Found {len(optimal_times)} optimal wake-up windows")
        
        return analysis
    
    def _find_light_sleep_periods(self, sleep_stages: List[Dict]) -> List[Dict]:
        """
        Identify periods of light sleep that are good for waking up.
        
        Args:
            sleep_stages: List of sleep stage data points
            
        Returns:
            List of light sleep periods with timestamps
        """
        light_sleep_periods = []
        
        for stage in sleep_stages:
            if stage.get('sleep_stage') == 'light':
                light_sleep_periods.append({
                    'timestamp': stage.get('timestamp'),
                    'duration_seconds': stage.get('duration_seconds', 0)
                })
        
        return light_sleep_periods
    
    def _calculate_sleep_quality(
        self,
        sleep_stages: List[Dict],
        heart_rate: List[Dict],
        hrv: List[Dict]
    ) -> float:
        """
        Calculate overall sleep quality score (0-100).
        
        Args:
            sleep_stages: Sleep stage data
            heart_rate: Heart rate data
            hrv: HRV data
            
        Returns:
            Sleep quality score between 0 and 100
        """
        score = 50.0  # Base score
        
        # Factor 1: Deep sleep percentage (higher is better)
        total_duration = sum(s.get('duration_seconds', 0) for s in sleep_stages)
        if total_duration > 0:
            deep_duration = sum(
                s.get('duration_seconds', 0) 
                for s in sleep_stages 
                if s.get('sleep_stage') == 'deep'
            )
            deep_percentage = (deep_duration / total_duration) * 100
            score += min(deep_percentage * 0.5, 20)  # Max 20 points
        
        # Factor 2: Sleep continuity (fewer wake periods is better)
        wake_count = sum(1 for s in sleep_stages if s.get('sleep_stage') == 'wake')
        score -= min(wake_count * 2, 15)  # Max -15 points
        
        # Factor 3: HRV (higher variability during sleep is generally better)
        if hrv:
            avg_hrv = np.mean([h.get('value', {}).get('rmssd', 0) for h in hrv])
            if avg_hrv > 40:  # Good HRV
                score += 15
            elif avg_hrv > 20:  # Moderate HRV
                score += 5
        
        # Ensure score is between 0 and 100
        return max(0, min(100, score))
    
    def _predict_optimal_wake_times(
        self,
        light_sleep_periods: List[Dict],
        sleep_stages: List[Dict],
        heart_rate: List[Dict]
    ) -> List[Dict]:
        """
        Predict the best times to wake up during the alarm window.
        
        Args:
            light_sleep_periods: Identified light sleep periods
            sleep_stages: All sleep stage data
            heart_rate: Heart rate data
            
        Returns:
            List of optimal wake-up times with confidence scores
        """
        optimal_times = []
        
        # Look for light sleep periods that last at least 5 minutes
        for period in light_sleep_periods:
            if period.get('duration_seconds', 0) >= 300:  # 5 minutes
                # Calculate confidence based on duration and stability
                duration_score = min(period.get('duration_seconds', 0) / 600, 1.0)  # Max at 10 min
                
                optimal_times.append({
                    'timestamp': period.get('timestamp'),
                    'confidence': duration_score * 100,
                    'reason': 'Extended light sleep period'
                })
        
        # Sort by confidence
        optimal_times.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Return top 5 candidates
        return optimal_times[:5]


class SmartAlarmController:
    """
    Controls the physical alarm hardware on the Raspberry Pi.
    
    Manages:
    - Buzzer/speaker
    - LED indicators
    - Snooze functionality
    """
    
    def __init__(self, buzzer_pin: int = 18, led_pin: int = 23):
        """
        Initialize the alarm controller.
        
        Args:
            buzzer_pin: GPIO pin for buzzer (BCM numbering)
            led_pin: GPIO pin for LED indicator (BCM numbering)
        """
        self.buzzer_pin = buzzer_pin
        self.led_pin = led_pin
        self.alarm_active = False
        self.snooze_count = 0
        self.max_snoozes = 3
        
        if GPIO_AVAILABLE:
            logger.info(f"Initializing GPIO: Buzzer on pin {buzzer_pin}, LED on pin {led_pin}")
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.buzzer_pin, GPIO.OUT)
            GPIO.setup(self.led_pin, GPIO.OUT)
            GPIO.output(self.buzzer_pin, GPIO.LOW)
            GPIO.output(self.led_pin, GPIO.LOW)
        else:
            logger.info("Running in simulation mode (no GPIO)")
    
    def trigger_alarm(self):
        """Activate the alarm (buzzer and LED)."""
        logger.info("🔔 ALARM TRIGGERED!")
        self.alarm_active = True
        
        if GPIO_AVAILABLE:
            GPIO.output(self.buzzer_pin, GPIO.HIGH)
            GPIO.output(self.led_pin, GPIO.HIGH)
        else:
            logger.info("🔊 [SIMULATION] Buzzer would be sounding...")
            logger.info("💡 [SIMULATION] LED would be lit...")
    
    def stop_alarm(self):
        """Deactivate the alarm."""
        logger.info("Alarm stopped")
        self.alarm_active = False
        
        if GPIO_AVAILABLE:
            GPIO.output(self.buzzer_pin, GPIO.LOW)
            GPIO.output(self.led_pin, GPIO.LOW)
        else:
            logger.info("🔇 [SIMULATION] Buzzer stopped")
            logger.info("💡 [SIMULATION] LED turned off")
    
    def snooze(self, duration_minutes: int = 5) -> bool:
        """
        Snooze the alarm for a specified duration.
        
        Args:
            duration_minutes: How long to snooze (default 5 minutes)
            
        Returns:
            True if snooze allowed, False if max snoozes reached
        """
        if self.snooze_count >= self.max_snoozes:
            logger.warning(f"Maximum snoozes ({self.max_snoozes}) reached!")
            return False
        
        self.snooze_count += 1
        self.stop_alarm()
        logger.info(f"⏰ Snoozed for {duration_minutes} minutes (Snooze {self.snooze_count}/{self.max_snoozes})")
        
        # Schedule alarm to trigger again
        threading.Timer(duration_minutes * 60, self.trigger_alarm).start()
        return True
    
    def cleanup(self):
        """Clean up GPIO resources."""
        if GPIO_AVAILABLE:
            logger.info("Cleaning up GPIO")
            GPIO.cleanup()


class RaspberryPiSmartAlarm:
    """
    Main smart alarm system that integrates IoT Hub communication,
    AI analysis, and alarm control.
    """
    
    def __init__(self, connection_string: str, alarm_time: str = "07:00"):
        """
        Initialize the smart alarm system.
        
        Args:
            connection_string: Azure IoT Hub device connection string
            alarm_time: Target wake-up time in HH:MM format (24-hour)
        """
        self.connection_string = connection_string
        self.alarm_time = alarm_time
        self.alarm_window_minutes = 30  # Wake up within 30 min before target time
        
        # Initialize components
        self.ai_model = SleepStagePredictor()
        self.alarm_controller = SmartAlarmController()
        self.device_client = None
        
        # Data storage
        self.latest_sleep_data = None
        self.latest_analysis = None
        self.optimal_wake_time = None
        
        logger.info(f"Smart Alarm initialized with target time: {alarm_time}")
    
    def connect_to_iot_hub(self):
        """Establish connection to Azure IoT Hub."""
        logger.info("Connecting to Azure IoT Hub...")
        
        try:
            # Create device client
            self.device_client = IoTHubDeviceClient.create_from_connection_string(
                self.connection_string
            )
            
            # Set up message handler for cloud-to-device messages
            self.device_client.on_message_received = self.message_handler
            
            # Set up method handler for direct methods
            self.device_client.on_method_request_received = self.method_handler
            
            # Connect to IoT Hub
            self.device_client.connect()
            
            logger.info("✓ Successfully connected to IoT Hub")
            
            # Send initial telemetry
            self.send_telemetry({
                'status': 'online',
                'alarm_time': self.alarm_time,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
            
        except Exception as e:
            logger.error(f"Failed to connect to IoT Hub: {e}")
            raise
    
    def message_handler(self, message):
        """
        Handle incoming cloud-to-device messages containing sleep data.
        
        Args:
            message: Message object from IoT Hub
        """
        logger.info("📨 Received message from IoT Hub")
        
        try:
            # Parse message data
            data = json.loads(message.data.decode('utf-8'))
            
            logger.info(f"Message type: {data.get('data_type')}")
            
            if data.get('data_type') == 'sleep_metrics':
                self.latest_sleep_data = data
                
                # Run AI analysis
                self.latest_analysis = self.ai_model.analyze_sleep_data(data)
                
                # Determine if we should trigger the alarm
                self.evaluate_wake_up_decision()
            
            # Send acknowledgment back to IoT Hub
            self.send_telemetry({
                'message_received': True,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def method_handler(self, method_request):
        """
        Handle direct method calls from IoT Hub.
        
        Supported methods:
        - set_alarm: Update alarm time
        - snooze: Snooze the alarm
        - stop_alarm: Stop the alarm
        - get_status: Get current system status
        
        Args:
            method_request: Method request object
        """
        logger.info(f"Direct method called: {method_request.name}")
        
        try:
            if method_request.name == "set_alarm":
                payload = json.loads(method_request.payload)
                new_time = payload.get('alarm_time', self.alarm_time)
                self.alarm_time = new_time
                
                response_payload = {
                    'status': 'success',
                    'message': f'Alarm time updated to {new_time}'
                }
                response_status = 200
                
            elif method_request.name == "snooze":
                success = self.alarm_controller.snooze()
                response_payload = {
                    'status': 'success' if success else 'failed',
                    'message': 'Alarm snoozed' if success else 'Max snoozes reached'
                }
                response_status = 200
                
            elif method_request.name == "stop_alarm":
                self.alarm_controller.stop_alarm()
                response_payload = {
                    'status': 'success',
                    'message': 'Alarm stopped'
                }
                response_status = 200
                
            elif method_request.name == "get_status":
                response_payload = {
                    'status': 'success',
                    'alarm_time': self.alarm_time,
                    'alarm_active': self.alarm_controller.alarm_active,
                    'latest_analysis': self.latest_analysis,
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
                response_status = 200
                
            else:
                response_payload = {
                    'status': 'error',
                    'message': f'Unknown method: {method_request.name}'
                }
                response_status = 404
            
            # Send method response
            method_response = MethodResponse.create_from_method_request(
                method_request,
                response_status,
                response_payload
            )
            self.device_client.send_method_response(method_response)
            
        except Exception as e:
            logger.error(f"Error handling method: {e}")
            error_response = MethodResponse.create_from_method_request(
                method_request,
                500,
                {'status': 'error', 'message': str(e)}
            )
            self.device_client.send_method_response(error_response)
    
    def send_telemetry(self, data: Dict):
        """
        Send telemetry data to IoT Hub.
        
        Args:
            data: Telemetry data to send
        """
        try:
            message = Message(json.dumps(data))
            message.content_type = "application/json"
            message.content_encoding = "utf-8"
            
            self.device_client.send_message(message)
            logger.debug("Telemetry sent to IoT Hub")
            
        except Exception as e:
            logger.error(f"Error sending telemetry: {e}")
    
    def evaluate_wake_up_decision(self):
        """
        Evaluate whether to trigger the alarm based on:
        - Current time vs target alarm time
        - Current sleep stage (prefer light sleep)
        - AI model predictions
        """
        if not self.latest_analysis:
            logger.warning("No analysis available for wake-up decision")
            return
        
        current_time = datetime.now()
        target_time = datetime.strptime(self.alarm_time, "%H:%M").replace(
            year=current_time.year,
            month=current_time.month,
            day=current_time.day
        )
        
        # Calculate alarm window (30 minutes before target)
        window_start = target_time - timedelta(minutes=self.alarm_window_minutes)
        
        logger.info(f"Current time: {current_time.strftime('%H:%M')}")
        logger.info(f"Alarm window: {window_start.strftime('%H:%M')} - {target_time.strftime('%H:%M')}")
        logger.info(f"Current sleep stage: {self.latest_analysis.get('current_stage')}")
        
        # Check if we're in the alarm window
        if window_start <= current_time <= target_time:
            # Check if in light sleep (optimal for waking)
            if self.latest_analysis.get('current_stage') == 'light':
                logger.info("✓ Optimal wake-up condition met: Light sleep within alarm window")
                self.trigger_optimal_alarm()
            else:
                logger.info(f"In alarm window but not in light sleep (currently: {self.latest_analysis.get('current_stage')})")
                # Wait for light sleep, but trigger at target time regardless
                
        elif current_time > target_time:
            # Past target time - trigger immediately
            logger.info("⚠ Past target alarm time - triggering alarm")
            self.trigger_optimal_alarm()
    
    def trigger_optimal_alarm(self):
        """Trigger the alarm and send notification to IoT Hub."""
        self.alarm_controller.trigger_alarm()
        
        # Send telemetry about alarm trigger
        self.send_telemetry({
            'event': 'alarm_triggered',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'sleep_quality': self.latest_analysis.get('sleep_quality_score'),
            'sleep_stage': self.latest_analysis.get('current_stage')
        })
    
    def run(self):
        """
        Main run loop for the smart alarm system.
        Keeps the device connected and responsive.
        """
        try:
            self.connect_to_iot_hub()
            
            logger.info("Smart Alarm is running. Press Ctrl+C to exit.")
            
            # Keep the program running
            while True:
                # Periodic status check
                time.sleep(60)  # Check every minute
                
                # Send heartbeat telemetry
                self.send_telemetry({
                    'heartbeat': True,
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'alarm_active': self.alarm_controller.alarm_active
                })
                
        except KeyboardInterrupt:
            logger.info("Shutting down Smart Alarm...")
            
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources before exit."""
        logger.info("Cleaning up resources...")
        
        if self.alarm_controller:
            self.alarm_controller.stop_alarm()
            self.alarm_controller.cleanup()
        
        if self.device_client:
            self.device_client.disconnect()
        
        logger.info("Cleanup complete")


def main():
    """
    Main entry point for the Raspberry Pi Smart Alarm.
    Loads configuration from environment variables and starts the system.
    """
    # Load configuration from environment variables
    connection_string = os.getenv('IOT_DEVICE_CONNECTION_STRING')
    alarm_time = os.getenv('ALARM_TIME', '07:00')
    
    if not connection_string:
        logger.error("IOT_DEVICE_CONNECTION_STRING environment variable not set")
        logger.error("Please set this to your device's connection string from Azure IoT Hub")
        return
    
    # Create and run the smart alarm
    alarm = RaspberryPiSmartAlarm(
        connection_string=connection_string,
        alarm_time=alarm_time
    )
    
    alarm.run()


if __name__ == '__main__':
    main()
