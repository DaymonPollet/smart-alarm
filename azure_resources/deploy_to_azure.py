"""
Azure ML Deployment Script for Sleep Quality Classification Model
Run this script to deploy the trained model to Azure ML Online Endpoint.
"""

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential
from azure.ai.ml.entities import Environment, Model, ManagedOnlineEndpoint, ManagedOnlineDeployment
import os
import shutil

# --- USER CONFIGURATION ---
SUBSCRIPTION_ID = "6a36bb7a-aee5-4e15-a3c7-2e362d2c2387"
RESOURCE_GROUP = "CCFAI"
WORKSPACE_NAME = "CCFAI_ML_DAYMON"

# --- DEPLOYMENT ARTIFACTS CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOY_FOLDER = os.path.join(SCRIPT_DIR, "deployment_assets")
ENVIRONMENT_NAME = "sleep-classifier-deployment-env"
MODEL_REGISTER_NAME = "fitbit-rf-sleep-classifier"
ENDPOINT_NAME = "fitbit-sleep-alarm-endpoint"
DEPLOYMENT_NAME = "rf-prod"

def setup_deployment_folder():
    """Create deployment folder with all required files"""
    print("Setting up deployment folder...")
    os.makedirs(DEPLOY_FOLDER, exist_ok=True)
    
    # Files to copy from azure_resources
    files_to_copy = [
        'random_forest_sleep_classifier.pkl',
        'imputer.pkl',
        'label_encoder.pkl',
        'score.py'
    ]
    
    for file_name in files_to_copy:
        src = os.path.join(SCRIPT_DIR, file_name)
        dst = os.path.join(DEPLOY_FOLDER, file_name)
        if os.path.exists(src):
            shutil.copy(src, dst)
            print(f"  Copied: {file_name}")
        else:
            print(f"  Warning: {file_name} not found")
    
    # Create conda environment file
    conda_yaml_content = """name: sleep-classifier-env
channels:
  - conda-forge
dependencies:
  - python=3.10
  - pip
  - pip:
    - numpy
    - pandas
    - scikit-learn
    - joblib
    - azureml-defaults
"""
    conda_path = os.path.join(DEPLOY_FOLDER, "conda.yaml")
    with open(conda_path, "w") as f:
        f.write(conda_yaml_content)
    print(f"  Created: conda.yaml")
    
    print(f"Deployment files ready in '{DEPLOY_FOLDER}'")
    return True

def connect_to_azure():
    """Connect to Azure ML Workspace"""
    print("\nConnecting to Azure ML Workspace...")
    try:
        credential = DefaultAzureCredential()
        ml_client = MLClient(
            credential=credential,
            subscription_id=SUBSCRIPTION_ID,
            resource_group_name=RESOURCE_GROUP,
            workspace_name=WORKSPACE_NAME,
        )
        print(f"Connected to: {WORKSPACE_NAME}")
        return ml_client
    except Exception as e:
        print(f"Error connecting to Azure: {e}")
        return None

def create_environment(ml_client):
    """Create/update the deployment environment"""
    print("\nCreating environment...")
    my_env = Environment(
        name=ENVIRONMENT_NAME,
        description="Custom environment for Fitbit sleep classification",
        conda_file=os.path.join(DEPLOY_FOLDER, "conda.yaml"),
        image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04:latest"
    )
    ml_client.environments.create_or_update(my_env)
    print(f"Environment '{ENVIRONMENT_NAME}' created/updated")
    return my_env

def register_model(ml_client):
    """Register the model artifacts"""
    print("\nRegistering model...")
    model = ml_client.models.create_or_update(
        Model(
            name=MODEL_REGISTER_NAME,
            path=DEPLOY_FOLDER,
            type="custom_model",
            description="Random Forest Classifier predicting sleep quality (Poor/Fair/Good)."
        )
    )
    print(f"Model registered: {model.name} (Version: {model.version})")
    return model

def create_endpoint(ml_client):
    """Create the online endpoint"""
    print("\nCreating online endpoint...")
    endpoint = ManagedOnlineEndpoint(
        name=ENDPOINT_NAME,
        description="Endpoint for Smart Alarm Sleep Quality Prediction",
        auth_mode="key",
        tags={"project": "smart-alarm", "model_type": "RFClassifier"}
    )
    ml_client.begin_create_or_update(endpoint).wait()
    print(f"Endpoint '{ENDPOINT_NAME}' created")
    return endpoint

def create_deployment(ml_client, model, my_env):
    """Create the deployment"""
    print("\nCreating deployment (this may take several minutes)...")
    deployment = ManagedOnlineDeployment(
        name=DEPLOYMENT_NAME,
        endpoint_name=ENDPOINT_NAME,
        model=model,
        environment=my_env,
        code_path=DEPLOY_FOLDER,
        instance_type="Standard_DS2_v2",
        instance_count=1,
        scoring_script="score.py",
    )
    
    ml_client.online_deployments.begin_create_or_update(deployment).wait()
    print(f"Deployment '{DEPLOYMENT_NAME}' created")
    
    # Set 100% traffic
    endpoint = ml_client.online_endpoints.get(name=ENDPOINT_NAME)
    endpoint.traffic = {DEPLOYMENT_NAME: 100}
    ml_client.online_endpoints.begin_create_or_update(endpoint).wait()
    print("Traffic set to 100%")
    
    return deployment

def main():
    print("=" * 60)
    print("Azure ML Deployment - Sleep Quality Classification")
    print("=" * 60)
    
    # Setup
    if not setup_deployment_folder():
        return
    
    # Connect
    ml_client = connect_to_azure()
    if not ml_client:
        return
    
    # Deploy
    my_env = create_environment(ml_client)
    model = register_model(ml_client)
    create_endpoint(ml_client)
    create_deployment(ml_client, model, my_env)
    
    # Get final endpoint info
    final_endpoint = ml_client.online_endpoints.get(name=ENDPOINT_NAME)
    
    print("\n" + "=" * 60)
    print("DEPLOYMENT SUCCESSFUL")
    print("=" * 60)
    print(f"Endpoint Name: {final_endpoint.name}")
    print(f"Scoring URI: {final_endpoint.scoring_uri}")
    print(f"Status: {final_endpoint.provisioning_state}")
    print("=" * 60)
    
    # Save endpoint info to file
    endpoint_info = {
        "endpoint_name": final_endpoint.name,
        "scoring_uri": final_endpoint.scoring_uri,
        "status": final_endpoint.provisioning_state
    }
    import json
    with open(os.path.join(SCRIPT_DIR, "endpoint_info.json"), "w") as f:
        json.dump(endpoint_info, f, indent=2)
    print(f"\nEndpoint info saved to: endpoint_info.json")

if __name__ == "__main__":
    main()
