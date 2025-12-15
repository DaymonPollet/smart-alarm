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
    """
    Extract HR-based features from CSV files.
    Only using features that can be derived from Fitbit API:
    - Heart Rate (1-second resolution)
    - Activity proxy (from accelerometer magnitude)
    
    Dropping raw accelerometer/gyroscope features since Fitbit API doesn't provide them.
    """
    try:
        df = pd.read_csv(file_path, header=None)
        
        # Check if HR column exists (column 10)
        if df.shape[1] < 11:
            print(f"Skipping {file_path}: insufficient columns ({df.shape[1]})")
            return None
            
        # Heart rate is in column 10
        hr_data = df[10]
        
        # Calculate HRV metrics from HR
        # Convert BPM to RR intervals (in milliseconds)
        rr_intervals = 60000.0 / hr_data
        diff_rr = np.diff(rr_intervals)
        hrv_rmssd = np.sqrt(np.mean(diff_rr**2)) if len(diff_rr) > 0 else 0
        hrv_sdnn = np.std(rr_intervals) if len(rr_intervals) > 1 else 0
        
        # Basic HR statistics
        mean_hr = hr_data.mean()
        std_hr = hr_data.std()
        min_hr = hr_data.min()
        max_hr = hr_data.max()
        
        if df.shape[1] >= 3:
            acc_x = df[0]
            acc_y = df[1]
            acc_z = df[2]
            acc_mag = np.sqrt(acc_x**2 + acc_y**2 + acc_z**2)
            mean_activity = acc_mag.mean()
            std_activity = acc_mag.std()
        else:
            mean_activity = 0
            std_activity = 0
        
        return {
            "mean_hr": mean_hr,
            "std_hr": std_hr,
            "min_hr": min_hr,
            "max_hr": max_hr,
            "hrv_rmssd": hrv_rmssd,
            "hrv_sdnn": hrv_sdnn,
            "mean_activity": mean_activity,
            "std_activity": std_activity
        }
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def get_label_from_filename(filename):
    """
    Extract sleep stage label from filename.
    Maps to Fitbit's sleep stage labels.
    """
    filename = os.path.basename(filename)
    if "Awake" in filename or "Awak" in filename:
        return "wake"
    elif "DS" in filename:
        return "deep"
    elif "LS" in filename:
        return "light"
    elif "REM" in filename:
        return "rem"
    else:
        return None

def main():
    print("=" * 60)
    print("Smart Alarm - Sleep Stage Classification Model Training")
    print("=" * 60)
    print("\nLoading data from:", DATA_DIR)
    files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    print(f"Found {len(files)} CSV files")
    
    data = []
    labels = []
    
    for i, f in enumerate(files):
        if (i + 1) % 10 == 0:
            print(f"Processing file {i+1}/{len(files)}...")
        
        features = extract_features(f)
        label = get_label_from_filename(f)
        
        if features and label:
            features_list = [
                features["mean_hr"],
                features["std_hr"],
                features["min_hr"],
                features["max_hr"],
                features["hrv_rmssd"],
                features["hrv_sdnn"],
                features["mean_activity"],
                features["std_activity"]
            ]
            data.append(features_list)
            labels.append(label)
            
    if not data:
        print("ERROR: No data found or processed.")
        return

    X = np.array(data)
    y = np.array(labels)
    
    print("\n" + "=" * 60)
    print(f"Successfully processed {len(X)} samples")
    print(f"Feature shape: {X.shape}")
    print("\nClass distribution:")
    print(pd.Series(y).value_counts())
    print("=" * 60)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\nTraining set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    
    print("\nTraining Random Forest Classifier...")
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=10,
        random_state=42,
        n_jobs=-1
    )
    clf.fit(X_train, y_train)
    
    print("\nEvaluating model on test set...")
    y_pred = clf.predict(X_test)
    print("\n" + classification_report(y_test, y_pred))
    
    feature_names = [
        "mean_hr", "std_hr", "min_hr", "max_hr",
        "hrv_rmssd", "hrv_sdnn", "mean_activity", "std_activity"
    ]
    print("\nFeature Importance:")
    for name, importance in zip(feature_names, clf.feature_importances_):
        print(f"  {name:15s}: {importance:.4f}")
    
    print(f"\nSaving model to {MODEL_PATH}...")
    joblib.dump(clf, MODEL_PATH)
    print("\n✓ Model training completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
