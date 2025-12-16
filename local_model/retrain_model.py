"""
Retrain the model with current sklearn version to fix compatibility issues.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
import joblib
import os

# this is the proprocessed data from our preprocessed ipynb file
# even tho we already had a model, this code could later be used in a pipelining feature and makes it easy to retrain again (may our data be adjusted / expended)
data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sleep_quality_preprocessed.csv')

print(f"Loading data from: {data_path}")

if not os.path.exists(data_path):
    print("ERROR: Preprocessed data not found!")
    print("Looking for alternative data...")
    # Try to use archive data
    exit(1)

df = pd.read_csv(data_path)
print(f"Data shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")

# features and target (as used in preprocessing.ipynb)
feature_columns = [
    'revitalization_score',
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

target_column = 'overall_score'

# check if columns exist
missing = [c for c in feature_columns if c not in df.columns]
if missing:
    print(f"Missing columns: {missing}")
    print(f"Available: {df.columns.tolist()}")
    exit(1)

X = df[feature_columns]
y = df[target_column]

print(f"\nFeatures shape: {X.shape}")
print(f"Target shape: {y.shape}")

# create and fit imputer
print("\nCreating imputer...")
imputer = SimpleImputer(strategy='median')
X_imputed = imputer.fit_transform(X)

# train model
print("Training Random Forest Regressor...")
X_train, X_test, y_train, y_test = train_test_split(X_imputed, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train, y_train)

# store feature names -> (this was commented later) -> this come in usefull in debugging
model.feature_names_in_ = np.array(feature_columns)

train_score = model.score(X_train, y_train)
test_score = model.score(X_test, y_test)
print(f"\nTraining R²: {train_score:.4f}")
print(f"Testing R²: {test_score:.4f}")
model_path = os.path.join(os.path.dirname(__file__), 'random_forest_regression_model.pkl')
imputer_path = os.path.join(os.path.dirname(__file__), 'imputer_reg.pkl')

print(f"\nSaving model to: {model_path}")
joblib.dump(model, model_path)

print(f"Saving imputer to: {imputer_path}")
joblib.dump(imputer, imputer_path)

print("\nDone! Models retrained with current sklearn version.")
