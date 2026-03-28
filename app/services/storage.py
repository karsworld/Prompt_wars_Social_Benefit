"""
Google Cloud Storage (GCS) service - archives successful BridgeLink 'benefit' prompts as JSON.
Part of the BridgeLink 'Social Benefit' project to store processed incidents.
"""
from __future__ import annotations
import os
import json
import logging
from datetime import datetime, timezone
from google.cloud import storage

logger = logging.getLogger(__name__)

def archive_incident_json(incident_data: dict, filename_prefix: str = "incident") -> str:
    """
    Archive successful incident prompts as JSON objects to Google Cloud Storage.
    Returns the public path or GCS URI on success.
    """
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        logger.warning("GCS_BUCKET_NAME is not set. Skipping archive.")
        return "Skipped: Bucket not defined"

    try:
        # Create full storage client - will use ambient credentials from Cloud Run
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        # Create a unique filename for each archive
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        blob_name = f"archives/{filename_prefix}_{timestamp}.json"
        blob = bucket.blob(blob_name)

        # Add some metadata and upload
        incident_data["_metadata"] = {
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "status": "success",
            "source": "BridgeLink Archive",
        }
        
        blob.upload_from_string(
            data=json.dumps(incident_data, indent=2),
            content_type="application/json",
        )

        logger.info(f"Successfully archived incident JSON to GCS: gs://{bucket_name}/{blob_name}")
        return f"gs://{bucket_name}/{blob_name}"

    except Exception as e:
        logger.error(f"GCS archival failed: {e}")
        return f"Failed: {e}"
