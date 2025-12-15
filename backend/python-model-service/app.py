from flask import Flask, request, jsonify
import joblib
import numpy as np
import os

app = Flask(__name__)

# Use the new local model (regression model for sleep quality score)
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'local_model')
MODEL_PATH = os.path.join(MODEL_DIR, 'random_forest_regression_model.pkl')
IMPUTER_PATH = os.path.join(MODEL_DIR, 'imputer_reg.pkl')

# Fallback to old model if new one doesn't exist
OLD_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model.joblib')

model = None
imputer = None
is_regression_model = False

def load_model():
    global model, imputer, is_regression_model
    
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        is_regression_model = True
        print(f"New regression model loaded from {MODEL_PATH}")
        
        if os.path.exists(IMPUTER_PATH):
            imputer = joblib.load(IMPUTER_PATH)
            print(f"Imputer loaded from {IMPUTER_PATH}")
    elif os.path.exists(OLD_MODEL_PATH):
        model = joblib.load(OLD_MODEL_PATH)
        is_regression_model = False
        print(f"Old classification model loaded from {OLD_MODEL_PATH}")
    else:
        print("No model file found. Please train a model first.")

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "Model Service Running", 
        "model_loaded": model is not None,
        "model_type": "regression" if is_regression_model else "classification"
    })

@app.route('/predict', methods=['POST'])
def predict():
    if not model:
        return jsonify({"error": "Model not loaded"}), 500
    
    try:
        data = request.get_json()
        
        if is_regression_model:
            # model expecting these features, we have default fallback values for now
            # DayOfWeek, IsWeekend, WakeupHour, Score_Lag1, DeepSleep_Lag1, RHR_Lag1, 
            # deep_sleep_in_minutes, resting_heart_rate, restlessness
            features = [
                data.get("day_of_week", 0),
                data.get("is_weekend", 0),
                data.get("wakeup_hour", 8),
                data.get("score_lag1", 75),  # Previous day's score
                data.get("deep_sleep_lag1", 90),  # Previous day's deep sleep
                data.get("rhr_lag1", 65),  # Previous day's resting HR
                data.get("deep_sleep_in_minutes", 90),
                data.get("resting_heart_rate", 65),
                data.get("restlessness", 0.1)
            ]
            
            features_array = np.array(features).reshape(1, -1)
            
            if imputer:
                features_array = imputer.transform(features_array)
            
            predicted_score = model.predict(features_array)[0]
            
            if predicted_score >= 85:
                quality = "excellent"
            elif predicted_score >= 70:
                quality = "good"
            elif predicted_score >= 55:
                quality = "fair"
            else:
                quality = "poor"
            
            return jsonify({
                "prediction": quality,
                "overall_score": float(predicted_score),
                "confidence": min(predicted_score / 100, 1.0),
                "probabilities": {
                    "excellent": 1.0 if quality == "excellent" else 0.0,
                    "good": 1.0 if quality == "good" else 0.0,
                    "fair": 1.0 if quality == "fair" else 0.0,
                    "poor": 1.0 if quality == "poor" else 0.0
                }
            })
        else:
            features = [
                data.get("mean_hr", 0),
                data.get("std_hr", 0),
                data.get("min_hr", 0),
                data.get("max_hr", 0),
                data.get("hrv_rmssd", 0),
                data.get("hrv_sdnn", 0),
                data.get("mean_activity", 0),
                data.get("std_activity", 0)
            ]
            
            features_array = np.array(features).reshape(1, -1)
            
            prediction = model.predict(features_array)[0]
            probabilities = model.predict_proba(features_array)[0]
            
            class_probs = {
                label: float(prob) 
                for label, prob in zip(model.classes_, probabilities)
            }
            
            return jsonify({
                "prediction": prediction,
                "probabilities": class_probs,
                "confidence": float(max(probabilities))
            })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy", 
        "model_loaded": model is not None,
        "model_type": "regression" if is_regression_model else "classification"
    })

if __name__ == '__main__':
    load_model()
    app.run(host='0.0.0.0', port=5000)
