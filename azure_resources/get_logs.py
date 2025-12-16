from azure.ai.ml import MLClient
from azure.identity import InteractiveBrowserCredential

SUBSCRIPTION_ID = "6a36bb7a-aee5-4e15-a3c7-2e362d2c2387"
RESOURCE_GROUP = "CCFAI"
WORKSPACE_NAME = "CCFAI_ML_DAYMON"
TENANT_ID = "4f3f75e5-d447-48c8-9483-c82b6c655896"

credential = InteractiveBrowserCredential(tenant_id=TENANT_ID)
ml_client = MLClient(
    credential=credential,
    subscription_id=SUBSCRIPTION_ID,
    resource_group_name=RESOURCE_GROUP,
    workspace_name=WORKSPACE_NAME,
)

print("Fetching deployment logs...")
try:
    logs = ml_client.online_deployments.get_logs(
        name="rf-prod",
        endpoint_name="fitbit-sleep-alarm-endpoint",
        lines=200
    )
    print(logs)
except Exception as e:
    print(f"Error: {e}")
