"""
Azure ML Scoring Script for Sleep Quality Classification
This script is used by Azure ML Online Endpoint to serve predictions.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd

def init():
    """
    Initialize the model and preprocessors.
    Called once when the endpoint container starts.
    """
    global model, imputer, label_encoder
    
    # Azure ML sets AZUREML_MODEL_DIR to the directory containing model files
    model_path = os.path.join(os.getenv('AZUREML_MODEL_DIR', '.'), 'random_forest_sleep_classifier.pkl')
    imputer_path = os.path.join(os.getenv('AZUREML_MODEL_DIR', '.'), 'imputer.pkl')
    encoder_path = os.path.join(os.getenv('AZUREML_MODEL_DIR', '.'), 'label_encoder.pkl')
    
    # Load the trained model
    model = joblib.load(model_path)
    print(f"Model loaded from {model_path}")
    
    # Load the imputer (for handling missing values)
    if os.path.exists(imputer_path):
        imputer = joblib.load(imputer_path)
        print(f"Imputer loaded from {imputer_path}")
    else:
        imputer = None
        print("No imputer found, will use raw features")
    
    # Load the label encoder (for decoding predictions)
    if os.path.exists(encoder_path):
        label_encoder = joblib.load(encoder_path)
        print(f"Label encoder loaded from {encoder_path}")
    else:
        label_encoder = None
        print("No label encoder found, will return raw predictions")

def run(raw_data):
    """
    Make predictions on incoming data.
    Called for each request to the endpoint.
    
    Expected input format:
    {
        "data": [
            {
                "deep_sleep_in_minutes": 90,
                "resting_heart_rate": 65,
                "restlessness": 0.1,
                "DayOfWeek": 2,
                "IsWeekend": 0,
                "WakeupHour": 7,
                "Score_Lag1": 75,
                "DeepSleep_Lag1": 85,
                "RHR_Lag1": 66
            }
        ]
    }
    """
    try:
        # Parse input
        data = json.loads(raw_data)
        
        if isinstance(data, dict) and 'data' in data:
            input_data = data['data']
        elif isinstance(data, list):
            input_data = data
        else:
            input_data = [data]
        
        # Convert to DataFrame
        df = pd.DataFrame(input_data)
        
        # Define expected feature columns (must match training)
        feature_columns = [
            'deep_sleep_in_minutes',
            'resting_heart_rate', 
            'restlessness',
            'DayOfWeek',
            'IsWeekend',
            'WakeupHour',
            'Score_Lag1',
            'DeepSleep_Lag1',
            'RHR_Lag1'
        ]
        
        # Ensure all required columns exist with defaults
        for col in feature_columns:
            if col not in df.columns:
                # Use sensible defaults
                defaults = {
                    'deep_sleep_in_minutes': 90,
                    'resting_heart_rate': 65,
                    'restlessness': 0.1,
                    'DayOfWeek': 3,
                    'IsWeekend': 0,
                    'WakeupHour': 7,
                    'Score_Lag1': 75,
                    'DeepSleep_Lag1': 85,
                    'RHR_Lag1': 65
                }
                df[col] = defaults.get(col, 0)
        
        # Select and order features
        X = df[feature_columns]
        
        # Apply imputer if available
        if imputer is not None:
            X = imputer.transform(X)
        
        # Make predictions
        predictions = model.predict(X)
        
        # Get probabilities if available
        try:
            probabilities = model.predict_proba(X)
            confidence = np.max(probabilities, axis=1)
        except:
            probabilities = None
            confidence = [1.0] * len(predictions)
        
        # Decode labels if encoder exists
        if label_encoder is not None:
            decoded_predictions = label_encoder.inverse_transform(predictions)
        else:
            decoded_predictions = predictions
        
        # Format response
        results = []
        for i, pred in enumerate(decoded_predictions):
            result = {
                'prediction': str(pred),
                'confidence': float(confidence[i])
            }
            
            # Add probabilities per class if available
            if probabilities is not None:
                if label_encoder is not None:
                    class_probs = {
                        str(label): float(prob)
                        for label, prob in zip(label_encoder.classes_, probabilities[i])
                    }
                else:
                    class_probs = {
                        f'class_{j}': float(prob)
                        for j, prob in enumerate(probabilities[i])
                    }
                result['probabilities'] = class_probs
            
            results.append(result)
        
        return json.dumps(results)
    
    except Exception as e:
        error_msg = f"Error during prediction: {str(e)}"
        print(error_msg)
        return json.dumps({"error": error_msg})
