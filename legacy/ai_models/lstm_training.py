import os
import logging
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DATA_PATH = "data/archive (1)"

def load_all_data_from_directory(base_dir):
    """
    Loads all CSV files, infers the sleep stage label from the filename,
    and returns a single combined DataFrame.
    """
    all_dfs = []
    
    label_map = {
        'Awake': 'Awake',
        'DS': 'Deep',
        'LS': 'Light',
        'REM': 'REM', 
        'Awak': 'Awake' 
    }

    for filename in os.listdir(base_dir):
        if filename.endswith(".csv"):
            filepath = os.path.join(base_dir, filename)
            
            inferred_label = 'Unknown'
            for prefix, label in label_map.items():
                if prefix in filename:
                    inferred_label = label
                    break
            
            if inferred_label == 'Unknown':
                logger.warning(f"Skipping file with unknown sleep stage prefix: {filename}")
                continue
            
            # Read CSV without header initially
            df = pd.read_csv(filepath, header=None)
            
            # Check if the first row is actually a header (contains strings instead of numbers)
            # We check the first column of the first row. If it's a string that can't be converted to float, it's likely a header.
            try:
                float(df.iloc[0, 0])
                is_header = False
            except ValueError:
                is_header = True
                
            if is_header:
                # Reload with header=0 to correctly parse columns, then reset index to treat it like others
                df = pd.read_csv(filepath, header=0)
                # If the header was read, the column names are now the keys. 
                # We need to ensure we are working with a uniform structure (numpy array or consistent columns)
                # For simplicity in this mixed dataset, we'll convert to values and lose column names
                # But we must ensure the shape is correct.
            
            # Handle missing label column (11 columns instead of 12)
            if df.shape[1] == 11:
                df['Label'] = inferred_label # Add label column
            elif df.shape[1] >= 12:
                # If 12+ columns, assume the 12th (index 11) is the label.
                # We overwrite it with the inferred label from filename to be safe/consistent, 
                # or we could trust the file. Let's trust the filename as it's more consistent in this dataset.
                df.iloc[:, 11] = inferred_label 
            else:
                logger.warning(f"Skipping file {filename}: Expected at least 11 columns, found {df.shape[1]}")
                continue
            
            # Ensure we only keep the first 12 columns (0-10 features, 11 label) to match dimensions
            df = df.iloc[:, :12]
            
            # Standardize column names for concatenation
            df.columns = [i for i in range(12)]
            
            all_dfs.append(df)
            
    if not all_dfs:
        logger.error(f"No valid CSV files found in {base_dir}. Generating dummy data.")
        return generate_dummy_data(n_samples=5000, for_real_data=True)

    combined_df = pd.concat(all_dfs, ignore_index=True)
    logger.info(f"Successfully loaded {len(all_dfs)} files, resulting in {combined_df.shape[0]} total samples.")
    return combined_df

def load_and_preprocess_data():
    """
    Loads the combined Kaggle dataset, maps it to Fitbit-compatible features,
    and scales the features.
    """
    df = load_all_data_from_directory(BASE_DATA_PATH)
    
    # 1. Extract Features compatible with Fitbit: Heart Rate (Col 10) and Movement (Derived from Accel Col 0, 1, 2)
    hr = df.iloc[:, 10].values
    accel_x = df.iloc[:, 0].values
    accel_y = df.iloc[:, 1].values
    accel_z = df.iloc[:, 2].values
    
    # Calculate Movement Magnitude: sqrt(x^2 + y^2 + z^2) - 1.0 (to account for gravity)
    magnitude = np.sqrt(accel_x**2 + accel_y**2 + accel_z**2)
    # Scale movement to look more like intensity
    movement = np.abs(magnitude - 1.0) * 10
    
    # Combine into features [HR, Movement]
    X_raw = np.column_stack((hr, movement))
    
    # 2. Scale Features
    logger.info("Scaling features using StandardScaler...")
    scaler = StandardScaler()
    X = scaler.fit_transform(X_raw)
    
    # 3. Encode Labels (Column 11)
    y_raw = df.iloc[:, 11].values
    
    # Use only labels found in the dataset
    valid_labels = ["Awake", "Light", "Deep", "REM"]
    le = LabelEncoder()
    le.fit(valid_labels) # Fit only to known sleep stages
    
    # Filter out any 'Unknown' labels if they somehow slipped in
    mask = [label in valid_labels for label in y_raw]
    X = X[mask]
    y_raw = y_raw[mask]
    
    y = le.transform(y_raw)
    
    return X, y, le, scaler # Return the scaler for later use in prediction

def generate_dummy_data(n_samples=1000, for_real_data=False):
    """Generates dummy data if CSV is missing or for fallback."""
    logger.info("Generating dummy data becauese the real model didn't work ...")
    if for_real_data:
        data = {
            0: np.random.randn(n_samples), # Accel X
            1: np.random.randn(n_samples), # Accel Y
            2: np.random.randn(n_samples), # Accel Z
            10: np.random.normal(70, 10, n_samples), # HR
            11: np.random.choice(["Awake", "Light", "Deep", "REM"], n_samples) # Label
        }
        # Add placeholder columns 3-9
        for i in range(3, 10):
            data[i] = np.random.randn(n_samples)
        
        df = pd.DataFrame(data)
        # Ensure column order is correct for slicing (0 to 11)
        df = df[list(range(12))]
        return df
    # Fallback return structure (original)
    return np.random.rand(n_samples, 2), np.random.randint(0, 4, n_samples), LabelEncoder().fit(["Awake", "Light", "Deep", "REM"])

def create_lstm_model(input_shape, n_classes):
    """
    Creates a simple LSTM model for Sleep Stage Classification.
    """
    # Model definition as before...
    model = tf.keras.Sequential([
        # Input layer: (TimeSteps, Features)
        tf.keras.layers.Input(shape=input_shape),
        
        # LSTM Layer
        tf.keras.layers.LSTM(64, return_sequences=False),
        
        # Dense Layers
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(n_classes, activation='softmax')
    ])
    
    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    
    return model

def train_model():
    # 1. Prepare Data
    TIME_STEPS = 10
    FEATURES = 2 # HR, Movement
    
    # Updated call to retrieve the necessary components
    X_raw, y_raw, le, scaler = load_and_preprocess_data()
    
    # Create Sequences
    X_seq, y_seq = [], []
    for i in range(len(X_raw) - TIME_STEPS):
        X_seq.append(X_raw[i:(i + TIME_STEPS)])
        y_seq.append(y_raw[i + TIME_STEPS])
        
    X_seq = np.array(X_seq)
    y_seq = np.array(y_seq)
    
    logger.info(f"Total sequences created: {len(X_seq)}")
    
    # Split: Train (70%), Validation (15%), Test (15%)
    X_train, X_temp, y_train, y_temp = train_test_split(X_seq, y_seq, test_size=0.3, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)
    
    logger.info(f"Data Split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")
    
    # 2. Create Model
    model = create_lstm_model((TIME_STEPS, FEATURES), len(le.classes_))
    
    # 3. Train
    logger.info("Starting LSTM training...")
    history = model.fit(
        X_train, y_train, 
        epochs=10, # Increased epochs
        batch_size=32, 
        validation_data=(X_val, y_val)
    )
    
    # 4. Evaluate on Test Set
    loss, accuracy = model.evaluate(X_test, y_test)
    logger.info(f"Test Set Accuracy: {accuracy:.4f}")
    
    # 5. Save
    os.makedirs('models', exist_ok=True)
    model.save('models/lstm_sleep_model.h5')
    
    # Save Label Encoder classes and the Scaler
    np.save('models/classes.npy', le.classes_)
    import joblib # Requires joblib for saving the scaler
    joblib.dump(scaler, 'models/scaler.pkl')
    
    logger.info("Model saved successfully. Classes and Scaler saved.")

if __name__ == "__main__":
    # Ensure joblib is available for saving the scaler
    try:
        import joblib
    except ImportError:
        print("Please install joblib: pip install joblib")
        exit()
        
    train_model()