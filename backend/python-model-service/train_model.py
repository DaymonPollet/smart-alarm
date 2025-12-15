import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import glob

DATA_DIR = "../../data/archive (1)"
MODEL_PATH = "model.joblib"

def extract_features(file_path):
    try:
        df = pd.read_csv(file_path, header=None)
        
        if df.shape[1] < 11:
            return None
            
        hr_data = df[10]
        
        rr_intervals = 60000 / hr_data
        diff_rr = np.diff(rr_intervals)
        hrv_rmssd = np.sqrt(np.mean(diff_rr**2)) if len(diff_rr) > 0 else 0
        
        mean_hr = hr_data.mean()
        std_hr = hr_data.std()
        min_hr = hr_data.min()
        max_hr = hr_data.max()
        
        # Simulate Fitbit "Activity" (Steps/Intensity) from raw accelerometer
        # Fitbit gives 1-min resolution activity. We approximate this by averaging magnitude.
        mean_activity = acc_mag.mean()
        std_activity = acc_mag.std() 
        
        return {
            "mean_hr": mean_hr,
            "std_hr": std_hr,
            "sdnn": sdnn,
            "rmssd": rmssd,
            "min_hr": min_hr,
            "max_hr": max_hr,
            "mean_activity": mean_activity,
            "std_activity": std_activity
        }
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def get_label_from_filename(filename):
    filename = os.path.basename(filename)
    if "Awake" in filename or "Awak" in filename:
        return "WAKE"
    elif "DS" in filename:
        return "DEEP"
    elif "LS" in filename:
        return "LIGHT"
    elif "REM" in filename:
        return "REM"
    else:
        return None

def main():
    print("Loading data...")
    files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    
    data = []
    labels = []
    
    for f in files:
        features = extract_features(f)
        label = get_label_from_filename(f)
        
        if features and label:
            features_list = [
                features["mean_hr"],
                features["std_hr"],
                features["min_hr"],
                features["max_hr"],
                features["hrv_rmssd"]
            ]
            data.append(features_list)
            labels.append(label)
            
    if not data:
        print("No data found or processed.")
        return

    X = np.array(data)
    y = np.array(labels)
    
    print(f"Processed {len(X)} samples.")
    print(f"Labels distribution: {pd.Series(y).value_counts()}")
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Random Forest Classifier...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    
    print("Evaluating model...")
    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred))
    
    print(f"Saving model to {MODEL_PATH}...")
    joblib.dump(clf, MODEL_PATH)
    print("Done.")

if __name__ == "__main__":
    main()
