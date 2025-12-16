from azure.ai.ml import MLClient
from azure.identity import InteractiveBrowserCredential
from azure.ai.ml.entities import Environment, Model, ManagedOnlineEndpoint, ManagedOnlineDeployment
import os
import shutil

SUBSCRIPTION_ID = "6a36bb7a-aee5-4e15-a3c7-2e362d2c2387"
RESOURCE_GROUP = "CCFAI"
WORKSPACE_NAME = "CCFAI_ML_DAYMON"
TENANT_ID = "4f3f75e5-d447-48c8-9483-c82b6c655896"

DEPLOY_FOLDER = "deployment_assets"
ENVIRONMENT_NAME = "sleep-classifier-deployment-env"
MODEL_REGISTER_NAME = "fitbit-rf-sleep-classifier"
ENDPOINT_NAME = "fitbit-sleep-alarm-endpoint" 
DEPLOYMENT_NAME = "rf-prod"

os.makedirs(DEPLOY_FOLDER, exist_ok=True)

files_to_deploy = [
    'random_forest_sleep_classifier.pkl', 
    'imputer.pkl', 
    'label_encoder.pkl', 
    'score.py',
]

for file_name in files_to_deploy:
    if os.path.exists(file_name):
        shutil.copy(file_name, os.path.join(DEPLOY_FOLDER, file_name))
    else:
        print(f"Warning: Required file not found: {file_name}")
        
conda_yaml_content = """
name: sleep-classifier-env
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
with open(os.path.join(DEPLOY_FOLDER, "conda.yaml"), "w") as f:
    f.write(conda_yaml_content)
print(f"Deployment files collected in '{DEPLOY_FOLDER}'.")

print("\nConnecting to Azure...")
credential = InteractiveBrowserCredential(tenant_id=TENANT_ID)
ml_client = MLClient(
    credential=credential,
    subscription_id=SUBSCRIPTION_ID,
    resource_group_name=RESOURCE_GROUP,
    workspace_name=WORKSPACE_NAME,
)
print(f"Connected to: {WORKSPACE_NAME}")

print("\nDeleting old deployment...")
try:
    ml_client.online_deployments.begin_delete(
        name=DEPLOYMENT_NAME,
        endpoint_name=ENDPOINT_NAME
    ).wait()
    print("Old deployment deleted")
except Exception as e:
    print(f"Deployment deletion: {e}")

my_env = Environment(
    name=ENVIRONMENT_NAME,
    description="Custom environment for Fitbit sleep classification",
    conda_file=os.path.join(DEPLOY_FOLDER, "conda.yaml"),
    image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04:latest"
)
ml_client.environments.create_or_update(my_env)
print(f"Environment '{ENVIRONMENT_NAME}' updated.")

print("\nRegistering new model version...")
model = ml_client.models.create_or_update(
    Model(
        name=MODEL_REGISTER_NAME,
        path=DEPLOY_FOLDER,
        type="custom_model",
        description="Random Forest Classifier predicting sleep quality (Poor/Fair/Good)."
    )
)
print(f"Model registered: {model.name} (Version: {model.version})")

print("\nCreating deployment (this takes 5-10 minutes)...")
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

endpoint = ml_client.online_endpoints.get(name=ENDPOINT_NAME)
endpoint.traffic = {DEPLOYMENT_NAME: 100}
ml_client.online_endpoints.begin_create_or_update(endpoint).wait()

final_endpoint = ml_client.online_endpoints.get(name=ENDPOINT_NAME)
print("\n" + "="*50)
print("DEPLOYMENT SUCCESSFUL")
print(f"Endpoint Name: {final_endpoint.name}")
print(f"Scoring URI: {final_endpoint.scoring_uri}")
print(f"Status: {final_endpoint.provisioning_state}")
print("="*50)

keys = ml_client.online_endpoints.get_keys(name=ENDPOINT_NAME)
print(f"\nPrimary Key: {keys.primary_key}")
print(f"\nAdd these to your .env file:")
print(f"AZURE_ENDPOINT_URL={final_endpoint.scoring_uri}")
print(f"AZURE_ENDPOINT_KEY={keys.primary_key}")
