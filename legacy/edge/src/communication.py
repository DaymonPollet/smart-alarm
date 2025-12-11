import json
import logging
import threading
from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse

logger = logging.getLogger(__name__)

class IoTHubClient:
    """
    Wrapper for Azure IoT Hub Device Client.
    Handles connection, telemetry sending, and receiving messages/twins.
    """
    
    def __init__(self, connection_string, message_callback=None, twin_callback=None):
        self.client = IoTHubDeviceClient.create_from_connection_string(connection_string)
        self.message_callback = message_callback
        self.twin_callback = twin_callback
        self.connected = False

    def connect(self):
        try:
            self.client.connect()
            self.connected = True
            logger.info("Connected to Azure IoT Hub")
            
            # Set up callbacks
            if self.message_callback:
                self.client.on_message_received = self.message_callback
            
            if self.twin_callback:
                self.client.on_twin_desired_properties_patch_received = self.twin_callback
                
        except Exception as e:
            logger.error(f"Failed to connect to IoT Hub: {e}")
            self.connected = False

    def send_telemetry(self, data):
        if not self.connected:
            logger.warning("Cannot send telemetry - not connected")
            return

        try:
            msg = Message(json.dumps(data))
            msg.content_encoding = "utf-8"
            msg.content_type = "application/json"
            self.client.send_message(msg)
            logger.info("Telemetry sent to IoT Hub")
        except Exception as e:
            logger.error(f"Error sending telemetry: {e}")

    def get_twin(self):
        if not self.connected:
            return None
        try:
            return self.client.get_twin()
        except Exception as e:
            logger.error(f"Error getting twin: {e}")
            return None

    def update_reported_properties(self, patch):
        if not self.connected:
            return
        try:
            self.client.patch_twin_reported_properties(patch)
            logger.info(f"Reported properties updated: {patch}")
        except Exception as e:
            logger.error(f"Error updating reported properties: {e}")

    def shutdown(self):
        if self.connected:
            self.client.shutdown()
            self.connected = False
            logger.info("Disconnected from IoT Hub")
