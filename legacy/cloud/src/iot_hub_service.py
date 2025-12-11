import logging
import json
from azure.iot.hub import IoTHubRegistryManager

logger = logging.getLogger(__name__)

class IoTHubService:
    def __init__(self, connection_string):
        self.registry_manager = IoTHubRegistryManager(connection_string)

    def send_c2d_message(self, device_id, payload):
        try:
            message_body = json.dumps(payload)
            logger.info(f"Sending {len(message_body)} bytes to device {device_id}")
            
            self.registry_manager.send_c2d_message(
                device_id,
                message_body,
                properties={'content-type': 'application/json'}
            )
            logger.info("Message sent successfully to IoT Hub")
            return True
        except Exception as e:
            logger.error(f"Error sending message to IoT Hub: {e}")
            return False
