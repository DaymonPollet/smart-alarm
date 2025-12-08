import logging
import numpy as np
import os

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

logger = logging.getLogger(__name__)

class SleepStagePredictor:
    """
    Edge AI Model: LSTM (Long Short-Term Memory).
    Predicts sleep stages based on sequence of Heart Rate and Movement data.
    """
    
    def __init__(self):
        logger.info("Initializing Edge AI Model (LSTM)")
        self.model = None
        self.classes = ["Awake", "Light", "Deep", "REM"] 
        self.sequence_buffer = []
        self.TIME_STEPS = 10 # Must match training (yet to verify)
        
        if TF_AVAILABLE and os.path.exists('models/lstm_sleep_model.h5'):
            try:
                self.model = tf.keras.models.load_model('models/lstm_sleep_model.h5')
                self.classes = np.load('models/classes.npy', allow_pickle=True)
                logger.info("LSTM Model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
        else:
            logger.warning("TensorFlow not available or model not found. Running in SIMULATION mode.")

    def analyze_sleep_data(self, sleep_data: dict) -> dict:
        """
        Analyze incoming sleep data.
        
        Args:
            sleep_data: Contains 'heart_rate' (list) and 'movement' (list) or pre-processed stages.
        """
        # Extract latest data point (Simulated extraction from payload)
        # In a real stream, we'd get 1 minute of data at a time which is what we are going to try and do with my request to fitbit api
        # Here we assume the cloud sends us a chunk or we look at the last point but I don't know tho.
        
        # both defaults (will refine later)
        current_hr = 70 
        current_movement = 0
        
        # get value from payload
        if 'heart_rate' in sleep_data and sleep_data['heart_rate']:
            last_point = sleep_data['heart_rate'][-1] # handle both dict and int formats
            if isinstance(last_point, dict):
                current_hr = last_point.get('value', 70)
            else:
                current_hr = last_point
            
        self.sequence_buffer.append([current_hr, current_movement]) # update buffer
        
        # keep buffer size
        if len(self.sequence_buffer) > self.TIME_STEPS:
            self.sequence_buffer.pop(0)
            
        # make the prediction
        predicted_stage = "Unknown"
        confidence = 0.0
        
        if self.model and len(self.sequence_buffer) == self.TIME_STEPS:
            # Prepare input needed for lstm model: (1, TIME_STEPS, FEATURES)
            input_data = np.array([self.sequence_buffer])
            prediction = self.model.predict(input_data, verbose=0)
            class_idx = np.argmax(prediction)
            predicted_stage = self.classes[class_idx]
            confidence = float(np.max(prediction))
        else:
            # SIMULATION mode: simple rules based on HR and Movement
            logger.debug("Running in SIMULATION mode for sleep stage prediction")

            if current_movement > 5:
                predicted_stage = "Awake"
            elif current_hr < 60:
                predicted_stage = "Deep"
            else:
                predicted_stage = "Light"
                
        logger.info(f"LSTM Prediction: {predicted_stage} (HR: {current_hr})")
        
        # decide -> make em if ...
        should_wake = predicted_stage in ["Light", "Awake"]
        
        return {
            'status': 'success',
            'current_stage': predicted_stage,
            'should_wake_now': should_wake,
            'confidence': confidence
        }
