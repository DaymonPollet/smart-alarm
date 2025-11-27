"""
Fitbit Data Ferry - Azure Function Simulator
============================================
This module simulates an Azure Function that pulls sleep data from the Fitbit Web API
and sends it to Azure IoT Hub for processing by the Raspberry Pi smart alarm.

It acts as a cloud-to-cloud bridge between Fitbit's servers and Azure IoT Hub.
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Fitbit API client
import fitbit

# Azure IoT Hub Service SDK (for sending messages to devices)
from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.models import CloudToDeviceMethod, Message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FitbitDataFerry:
    """
    Manages the data pipeline from Fitbit API to Azure IoT Hub.
    
    This class handles:
    - Authentication with Fitbit API
    - Fetching minute-level HRV and movement data
    - Formatting data for IoT Hub transmission
    - Sending telemetry to the Raspberry Pi device
    """
    
    def __init__(
        self,
        fitbit_client_id: str,
        fitbit_client_secret: str,
        fitbit_access_token: str,
        fitbit_refresh_token: str,
        iot_hub_connection_string: str,
        target_device_id: str
    ):
        """
        Initialize the Fitbit Data Ferry.
        
        Args:
            fitbit_client_id: Fitbit API client ID
            fitbit_client_secret: Fitbit API client secret
            fitbit_access_token: OAuth2 access token for Fitbit
            fitbit_refresh_token: OAuth2 refresh token for Fitbit
            iot_hub_connection_string: Azure IoT Hub service connection string
            target_device_id: The device ID of the Raspberry Pi in IoT Hub
        """
        self.target_device_id = target_device_id
        
        # Initialize Fitbit client
        logger.info("Initializing Fitbit client...")
        self.fitbit_client = fitbit.Fitbit(
            fitbit_client_id,
            fitbit_client_secret,
            access_token=fitbit_access_token,
            refresh_token=fitbit_refresh_token,
            system=fitbit.Fitbit.METRIC  # Use metric system
        )
        
        # Initialize IoT Hub Registry Manager
        logger.info(f"Connecting to IoT Hub for device: {target_device_id}")
        self.registry_manager = IoTHubRegistryManager(iot_hub_connection_string)
        
        logger.info("FitbitDataFerry initialized successfully")
    
    def fetch_sleep_data(self, date: Optional[str] = None) -> Dict:
        """
        Fetch sleep data from Fitbit API for a specific date.
        
        Args:
            date: Date string in 'YYYY-MM-DD' format. Defaults to today.
            
        Returns:
            Dictionary containing sleep data
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Fetching sleep data for date: {date}")
        
        try:
            sleep_data = self.fitbit_client.sleep(date=date)
            logger.info(f"Retrieved {len(sleep_data.get('sleep', []))} sleep sessions")
            return sleep_data
        except Exception as e:
            logger.error(f"Error fetching sleep data: {e}")
            raise
    
    def fetch_heart_rate_intraday(
        self,
        date: Optional[str] = None,
        detail_level: str = '1min'
    ) -> Dict:
        """
        Fetch intraday heart rate data from Fitbit API.
        
        Args:
            date: Date string in 'YYYY-MM-DD' format. Defaults to today.
            detail_level: Data granularity ('1min', '5min', '15min')
            
        Returns:
            Dictionary containing heart rate intraday data
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Fetching heart rate intraday data for {date} at {detail_level} intervals")
        
        try:
            hr_data = self.fitbit_client.intraday_time_series(
                'activities/heart',
                base_date=date,
                detail_level=detail_level
            )
            logger.info(f"Retrieved {len(hr_data.get('activities-heart-intraday', {}).get('dataset', []))} heart rate data points")
            return hr_data
        except Exception as e:
            logger.error(f"Error fetching heart rate data: {e}")
            raise
    
    def fetch_hrv_data(self, date: Optional[str] = None) -> Dict:
        """
        Fetch Heart Rate Variability (HRV) data from Fitbit API.
        
        Args:
            date: Date string in 'YYYY-MM-DD' format. Defaults to today.
            
        Returns:
            Dictionary containing HRV data
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Fetching HRV data for date: {date}")
        
        try:
            hrv_data = self.fitbit_client.time_series(
                'hrv',
                base_date=date,
                end_date=date
            )
            logger.info(f"Retrieved HRV data")
            return hrv_data
        except Exception as e:
            logger.error(f"Error fetching HRV data: {e}")
            raise
    
    def process_sleep_stages(self, sleep_data: Dict) -> List[Dict]:
        """
        Process sleep data to extract sleep stages with timestamps.
        
        Args:
            sleep_data: Raw sleep data from Fitbit API
            
        Returns:
            List of sleep stage data points with movement information
        """
        processed_data = []
        
        for sleep_session in sleep_data.get('sleep', []):
            if not sleep_session.get('isMainSleep', False):
                continue  # Only process main sleep session
            
            # Extract sleep levels (stages)
            levels_data = sleep_session.get('levels', {}).get('data', [])
            
            for level in levels_data:
                data_point = {
                    'timestamp': level.get('dateTime'),
                    'sleep_stage': level.get('level'),  # wake, light, deep, rem
                    'duration_seconds': level.get('seconds', 0)
                }
                processed_data.append(data_point)
        
        logger.info(f"Processed {len(processed_data)} sleep stage data points")
        return processed_data
    
    def combine_data_for_alarm(
        self,
        sleep_stages: List[Dict],
        hr_data: Dict,
        hrv_data: Dict
    ) -> Dict:
        """
        Combine sleep, heart rate, and HRV data into a unified format for the alarm.
        
        Args:
            sleep_stages: Processed sleep stage data
            hr_data: Heart rate intraday data
            hrv_data: HRV data
            
        Returns:
            Combined data payload ready for transmission
        """
        # Extract heart rate dataset
        hr_dataset = hr_data.get('activities-heart-intraday', {}).get('dataset', [])
        
        # Extract HRV values
        hrv_values = hrv_data.get('hrv', [])
        
        # Create the combined payload
        payload = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'data_type': 'sleep_metrics',
            'sleep_stages': sleep_stages,
            'heart_rate': hr_dataset,
            'hrv': hrv_values,
            'device_id': self.target_device_id
        }
        
        logger.info(f"Combined data payload created with {len(sleep_stages)} sleep stages, "
                   f"{len(hr_dataset)} HR points, and {len(hrv_values)} HRV values")
        
        return payload
    
    def send_to_iot_hub(self, payload: Dict) -> bool:
        """
        Send the combined data payload to the Raspberry Pi via IoT Hub.
        
        Args:
            payload: The data to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert payload to JSON string
            message_body = json.dumps(payload)
            
            logger.info(f"Sending {len(message_body)} bytes to device {self.target_device_id}")
            
            # Send cloud-to-device message
            self.registry_manager.send_c2d_message(
                self.target_device_id,
                message_body,
                properties={'content-type': 'application/json'}
            )
            
            logger.info("Message sent successfully to IoT Hub")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to IoT Hub: {e}")
            return False
    
    def run_data_ferry(self, date: Optional[str] = None) -> bool:
        """
        Execute the complete data ferry pipeline.
        
        This is the main method that:
        1. Fetches all required data from Fitbit
        2. Processes and combines the data
        3. Sends it to the IoT Hub
        
        Args:
            date: Date to fetch data for (defaults to today)
            
        Returns:
            True if the complete pipeline succeeds
        """
        try:
            logger.info("=" * 60)
            logger.info("Starting Fitbit Data Ferry Pipeline")
            logger.info("=" * 60)
            
            # Step 1: Fetch data from Fitbit
            logger.info("Step 1: Fetching data from Fitbit API...")
            sleep_data = self.fetch_sleep_data(date)
            hr_data = self.fetch_heart_rate_intraday(date, detail_level='1min')
            hrv_data = self.fetch_hrv_data(date)
            
            # Step 2: Process sleep stages
            logger.info("Step 2: Processing sleep stage data...")
            sleep_stages = self.process_sleep_stages(sleep_data)
            
            if not sleep_stages:
                logger.warning("No sleep data found for the specified date")
                return False
            
            # Step 3: Combine all data
            logger.info("Step 3: Combining data into unified payload...")
            combined_payload = self.combine_data_for_alarm(
                sleep_stages,
                hr_data,
                hrv_data
            )
            
            # Step 4: Send to IoT Hub
            logger.info("Step 4: Sending data to IoT Hub...")
            success = self.send_to_iot_hub(combined_payload)
            
            if success:
                logger.info("=" * 60)
                logger.info("Data Ferry Pipeline Completed Successfully!")
                logger.info("=" * 60)
            else:
                logger.error("Data Ferry Pipeline Failed at transmission step")
            
            return success
            
        except Exception as e:
            logger.error(f"Data Ferry Pipeline Failed: {e}")
            return False


def main():
    """
    Main entry point for the Fitbit Data Ferry.
    Loads configuration from environment variables and runs the ferry.
    """
    # Load configuration from environment variables
    fitbit_client_id = os.getenv('FITBIT_CLIENT_ID')
    fitbit_client_secret = os.getenv('FITBIT_CLIENT_SECRET')
    fitbit_access_token = os.getenv('FITBIT_ACCESS_TOKEN')
    fitbit_refresh_token = os.getenv('FITBIT_REFRESH_TOKEN')
    iot_hub_connection_string = os.getenv('IOT_HUB_CONNECTION_STRING')
    target_device_id = os.getenv('TARGET_DEVICE_ID', 'raspberrypi-alarm')
    
    # Validate required environment variables
    required_vars = {
        'FITBIT_CLIENT_ID': fitbit_client_id,
        'FITBIT_CLIENT_SECRET': fitbit_client_secret,
        'FITBIT_ACCESS_TOKEN': fitbit_access_token,
        'FITBIT_REFRESH_TOKEN': fitbit_refresh_token,
        'IOT_HUB_CONNECTION_STRING': iot_hub_connection_string
    }
    
    missing_vars = [k for k, v in required_vars.items() if not v]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set all required environment variables before running.")
        return
    
    # Initialize and run the ferry
    ferry = FitbitDataFerry(
        fitbit_client_id=fitbit_client_id,
        fitbit_client_secret=fitbit_client_secret,
        fitbit_access_token=fitbit_access_token,
        fitbit_refresh_token=fitbit_refresh_token,
        iot_hub_connection_string=iot_hub_connection_string,
        target_device_id=target_device_id
    )
    
    # Run the data ferry for today's data
    success = ferry.run_data_ferry()
    
    if not success:
        exit(1)


if __name__ == '__main__':
    main()
