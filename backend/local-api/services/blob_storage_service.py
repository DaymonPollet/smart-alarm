"""
Azure Blob Storage Service
Stores sleep predictions and data in Azure Blob Storage for persistence and analytics.
"""
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def _get_env(key, default=''):
    val = os.getenv(key, default)
    if val and val.startswith('"') and val.endswith('"'):
        val = val[1:-1]
    if val and val.startswith("'") and val.endswith("'"):
        val = val[1:-1]
    return val

AZURE_STORAGE_CONNECTION_STRING = _get_env('AZURE_STORAGE_CONNECTION_STRING', '')
AZURE_STORAGE_CONTAINER = _get_env('AZURE_STORAGE_CONTAINER', 'smart-alarm-data')

blob_service_client = None
container_client = None
_initialized = False

def init_blob_storage():
    """Initialize Azure Blob Storage connection."""
    global blob_service_client, container_client, _initialized
    
    if _initialized:
        return container_client is not None
    
    _initialized = True
    
    if not AZURE_STORAGE_CONNECTION_STRING:
        print("[BLOB] Azure Storage connection string not configured")
        return False
    
    print(f"[BLOB] Connection string length: {len(AZURE_STORAGE_CONNECTION_STRING)}")
    
    try:
        from azure.storage.blob import BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER)
        
        try:
            container_client.create_container()
            print(f"[BLOB] Created container: {AZURE_STORAGE_CONTAINER}")
        except Exception as e:
            if "ContainerAlreadyExists" in str(e):
                print(f"[BLOB] Using existing container: {AZURE_STORAGE_CONTAINER}")
            else:
                print(f"[BLOB] Container error: {e}")
                raise
        
        print("[BLOB] Azure Blob Storage initialized successfully")
        return True
    except ImportError:
        print("[BLOB] azure-storage-blob not installed")
        return False
    except Exception as e:
        print(f"[BLOB] Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return False


def store_prediction(prediction_data: dict) -> bool:
    """
    Store a prediction record in Azure Blob Storage.
    """
    global container_client
    
    if not container_client:
        print("[BLOB] Container client not initialized, attempting init...")
        init_blob_storage()
        if not container_client:
            print("[BLOB] Failed to initialize, cannot store prediction")
            return False
    
    try:
        timestamp = prediction_data.get('timestamp', datetime.now().isoformat())
        date_prefix = timestamp[:10].replace('-', '/')  
        safe_timestamp = timestamp.replace(':', '-').replace('+', '_')
        blob_name = f"predictions/{date_prefix}/{safe_timestamp}.json"
        
        blob_client = container_client.get_blob_client(blob_name)
        data_to_store = json.dumps(prediction_data, indent=2, default=str)
        blob_client.upload_blob(data_to_store, overwrite=True)
        print(f"[BLOB] Stored prediction: {blob_name} ({len(data_to_store)} bytes)")
        return True
    except Exception as e:
        print(f"[BLOB] Failed to store prediction: {e}")
        import traceback
        traceback.print_exc()
        return False


def store_sleep_data(date: str, sleep_data: dict) -> bool:
    """
    Store raw sleep data in Azure Blob Storage.
    
    Args:
        date: Date string (YYYY-MM-DD)
        sleep_data: Dict containing Fitbit sleep data
    
    Returns:
        True if stored successfully, False otherwise
    """
    if not container_client:
        return False
    
    try:
        date_prefix = date.replace('-', '/')
        blob_name = f"sleep_data/{date_prefix}/raw.json"
        
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(
            json.dumps(sleep_data, indent=2),
            overwrite=True
        )
        print(f"[BLOB] Stored sleep data: {blob_name}")
        return True
    except Exception as e:
        print(f"[BLOB] Failed to store sleep data: {e}")
        return False


def store_daily_summary(date: str, summary: dict) -> bool:
    """
    Store daily summary (predictions + raw data) for analytics.
    
    Args:
        date: Date string (YYYY-MM-DD)
        summary: Dict containing the full daily summary
    
    Returns:
        True if stored successfully, False otherwise
    """
    if not container_client:
        return False
    
    try:
        date_prefix = date.replace('-', '/')
        blob_name = f"summaries/{date_prefix}/daily_summary.json"
        
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(
            json.dumps(summary, indent=2),
            overwrite=True
        )
        print(f"[BLOB] Stored daily summary: {blob_name}")
        return True
    except Exception as e:
        print(f"[BLOB] Failed to store daily summary: {e}")
        return False


def list_predictions(date_prefix: str = None) -> list:
    """
    List stored predictions, optionally filtered by date.
    
    Args:
        date_prefix: Optional date prefix (YYYY/MM/DD or YYYY/MM or YYYY)
    
    Returns:
        List of blob names
    """
    if not container_client:
        return []
    
    try:
        prefix = f"predictions/{date_prefix}" if date_prefix else "predictions/"
        blobs = container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blobs]
    except Exception as e:
        print(f"[BLOB] Failed to list predictions: {e}")
        return []


def get_storage_status() -> dict:
    """Get current blob storage status."""
    return {
        "configured": bool(AZURE_STORAGE_CONNECTION_STRING),
        "connected": container_client is not None,
        "container": AZURE_STORAGE_CONTAINER if container_client else None
    }
