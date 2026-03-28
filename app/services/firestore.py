"""Firestore service — manages persistence for analyzed results in Native Mode."""
from __future__ import annotations

import datetime
import os
import sys
from typing import Any

from google.cloud import firestore
from app.models.schemas import VerificationCard

# ---------------------------------------------------------------------------
# Client Initialization
# ---------------------------------------------------------------------------
def _get_db() -> firestore.AsyncClient:
    """Initialize local or production Firestore client."""
    # Cloud Run automatically has GOOGLE_CLOUD_PROJECT set.
    # For local testing, ensure GOOGLE_APPLICATION_CREDENTIALS points to your key.
    return firestore.AsyncClient()


async def save_incident(card: VerificationCard) -> str:
    """Save an analyzed incident report to Firestore 'incidents' collection."""
    db = _get_db()
    
    incident_ref = db.collection("incidents").document()
    
    # Extract fields as requested by PromptWars 2026 specs
    data = {
        "priority": card.priority,
        "category": card.category,
        "summary": card.summary,
        "confidence": card.confidence,
        "location": {
            "lat": card.location.lat,
            "lng": card.location.lng,
            "description": card.location.description
        },
        "action_payload": {
            "dispatch_type": card.action_payload.dispatch_type,
            "units_needed": card.action_payload.units_needed,
            "urgency_minutes": card.action_payload.urgency_minutes,
            "notes": card.action_payload.notes
        },
        "timestamp": firestore.SERVER_TIMESTAMP,
        "created_at": datetime.datetime.now(datetime.timezone.utc)
    }
    
    try:
        await incident_ref.set(data)
        print(f"INFO: Saved incident to Firestore: {incident_ref.id}", file=sys.stderr)
        return incident_ref.id
    except Exception as e:
        print(f"ERROR: Firestore save failed: {e}", file=sys.stderr)
        return ""


async def get_recent_incidents(limit: int = 3) -> list[dict[str, Any]]:
    """Fetch the last N incidents ordered by timestamp."""
    db = _get_db()
    try:
        docs_stream = db.collection("incidents")\
            .order_by("created_at", direction=firestore.Query.DESCENDING)\
            .limit(limit)\
            .stream()
            
        results = []
        async for doc in docs_stream:
            d = doc.to_dict()
            # Convert timestamp to ISO string for JSON serialization
            if "created_at" in d and hasattr(d["created_at"], "isoformat"):
                d["created_at"] = d["created_at"].isoformat()
            elif "timestamp" in d and hasattr(d["timestamp"], "isoformat"):
                # Handle SERVER_TIMESTAMP after it's been committed
                d["timestamp"] = d["timestamp"].isoformat()
            
            d["id"] = doc.id
            results.append(d)
        return results
    except Exception as e:
        print(f"ERROR: Firestore fetch failed: {e}", file=sys.stderr)
        return []
