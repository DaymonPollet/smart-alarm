from flask import Flask, request, jsonify
import joblib
import numpy as np
import os

app = Flask(__name__)

MODEL_PATH = "model.joblib"
model = None

def load_model():
    global model
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print("Model loaded successfully.")
    else:
        print("Model file not found. Please train the model first.")

@app.route('/predict', methods=['POST'])
def predict():
    if not model:
        return jsonify({"error": "Model not loaded"}), 500
    
    try:
        data = request.get_json()
        # Expecting a list of features or a dictionary
        # Features: mean_hr, std_hr, min_hr, max_hr, mean_activity, std_activity
        
        features = []
        if isinstance(data, dict):
            features = [
                data.get("mean_hr", 0),
                data.get("std_hr", 0),
                data.get("min_hr", 0),
                data.get("max_hr", 0),
                data.get("mean_activity", 0),
                data.get("std_activity", 0)
            ]
        elif isinstance(data, list):
            features = data
        
        # Reshape for prediction
        features_array = np.array(features).reshape(1, -1)
        
        prediction = model.predict(features_array)[0]
        
        return jsonify({"prediction": prediction})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "model_loaded": model is not None})

if __name__ == '__main__':
    load_model()
    app.run(host='0.0.0.0', port=5000)
