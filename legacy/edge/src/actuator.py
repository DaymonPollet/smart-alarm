import logging
import threading
import time

logger = logging.getLogger(__name__)
# stil WIP - SAFE MODE: No GPIO imports or usage cuz am scared of buring the pi to crisp
class SmartAlarmController:
    """
    Controls the physical alarm hardware on the Raspberry Pi.
    SAFE MODE: No GPIO pins are used. Simulation only.
    """
    
    def __init__(self):
        self.alarm_active = False
        self.snooze_count = 0
        self.max_snoozes = 3
        logger.info("SmartAlarmController initialized in SIMULATION MODE (Safe for hardware)")
    
    def trigger_alarm(self):
        """Activate the alarm (Simulation)."""
        logger.info(" [ACTUATOR] ALARM TRIGGERED! (Buzzer Sounding, LED Flashing)")
        self.alarm_active = True
        
    def stop_alarm(self):
        """Deactivate the alarm."""
        logger.info(" [ACTUATOR] Alarm stopped")
        self.alarm_active = False
    
    def snooze(self, duration_minutes: int = 5) -> bool:
        """
        Snooze the alarm for a specified duration.
        """
        if self.snooze_count >= self.max_snoozes:
            logger.warning(f"Maximum snoozes ({self.max_snoozes}) reached!")
            return False
        
        self.snooze_count += 1
        self.stop_alarm()
        logger.info(f" [ACTUATOR] Snoozed for {duration_minutes} minutes (Snooze {self.snooze_count}/{self.max_snoozes})")
        
        threading.Timer(duration_minutes * 60, self.trigger_alarm).start()
        return True
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up Actuator resources")
