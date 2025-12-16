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
    
    model_dir = os.getenv('AZUREML_MODEL_DIR', '.')
    
    possible_paths = [
        model_dir,
        os.path.join(model_dir, 'deployment_assets'),
    ]
    
    model_path = None
    for base in possible_paths:
        test_path = os.path.join(base, 'random_forest_sleep_classifier.pkl')
        if os.path.exists(test_path):
            model_path = test_path
            break
    
    if model_path is None:
        raise FileNotFoundError(f"Model not found. Searched in: {possible_paths}")
    
    base_dir = os.path.dirname(model_path)
    imputer_path = os.path.join(base_dir, 'imputer.pkl')
    encoder_path = os.path.join(base_dir, 'label_encoder.pkl')
    
    model = joblib.load(model_path)
    print(f"Model loaded from {model_path}")
    
    if os.path.exists(imputer_path):
        imputer = joblib.load(imputer_path)
        print(f"Imputer loaded from {imputer_path}")
    else:
        imputer = None
        print("No imputer found, will use raw features")
    
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
                "TotalSteps": 8000,
                "TotalMinutesAsleep": 420,
                "TotalTimeInBed": 480,
                "MinutesAwake_Intraday": 30,
                "MinutesRestless_Intraday": 15,
                "Calories": 2200,
                "VeryActiveMinutes": 45,
                "SedentaryMinutes": 600,
                "DayOfWeek": 2,
                "IsWeekend": 0,
                "TotalSteps_Lag1": 7500,
                "TotalMinutesAsleep_Lag1": 400,
                "Calories_Lag1": 2100,
                "VeryActiveMinutes_Lag1": 30
            }
        ]
    }
    """
    try:
        data = json.loads(raw_data)
        
        if isinstance(data, dict) and 'data' in data:
            input_data = data['data']
        elif isinstance(data, list):
            input_data = data
        else:
            input_data = [data]
        
        df = pd.DataFrame(input_data)
        
        feature_columns = [
            'TotalSteps',
            'TotalMinutesAsleep',
            'TotalTimeInBed',
            'MinutesAwake_Intraday',
            'MinutesRestless_Intraday',
            'Calories',
            'VeryActiveMinutes',
            'SedentaryMinutes',
            'DayOfWeek',
            'IsWeekend',
            'TotalSteps_Lag1',
            'TotalMinutesAsleep_Lag1',
            'Calories_Lag1',
            'VeryActiveMinutes_Lag1'
        ]
        
        for col in feature_columns:
            if col not in df.columns:
                defaults = {
                    'TotalSteps': 5000,
                    'TotalMinutesAsleep': 400,
                    'TotalTimeInBed': 450,
                    'MinutesAwake_Intraday': 30,
                    'MinutesRestless_Intraday': 10,
                    'Calories': 2000,
                    'VeryActiveMinutes': 30,
                    'SedentaryMinutes': 600,
                    'DayOfWeek': 3,
                    'IsWeekend': 0,
                    'TotalSteps_Lag1': 5000,
                    'TotalMinutesAsleep_Lag1': 400,
                    'Calories_Lag1': 2000,
                    'VeryActiveMinutes_Lag1': 30
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
