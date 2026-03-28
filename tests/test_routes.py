"""Integration tests for BridgeLink routes using FastAPI TestClient and service mocking."""
from __future__ import annotations

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import VerificationCard, LocationModel, ActionPayload

client = TestClient(app)

# --- CONFIG TESTS ---

def test_config_endpoint():
    """Verify /api/config returns the Maps API Key from the environment."""
    with patch("os.getenv", return_value="FAKE_MAPS_KEY"):
        # We need to clear the lru_cache if possible, or just accept the mock
        from app.routes.config import get_config
        get_config.cache_clear()
        
        response = client.get("/api/config")
        assert response.status_code == 200
        assert response.json()["GOOGLE_MAPS_API_KEY"] == "FAKE_MAPS_KEY"


def test_health_check():
    """Verify the health endpoint is operational."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# --- CAPTURE TESTS ---

@patch("app.services.firestore.save_incident")
@patch("app.services.gemini.analyze_text")
def test_capture_text_success(mock_analyze, mock_save):
    """Verify /api/capture correctly calls Gemini and persists to Firestore."""
    # Setup mock return
    mock_analyze.return_value = VerificationCard(
        priority="P1",
        category="Medical",
        location=LocationModel(lat=10.0, lng=20.0, description="Test site"),
        summary="A test incident detected by AI.",
        confidence=0.95,
        action_payload=ActionPayload(
            dispatch_type="ambulance",
            units_needed=2,
            urgency_minutes=10,
            notes="Mocked results"
        )
    )
    mock_save.return_value = "mock_firestore_id"

    # Note: /api/capture uses Form data
    payload = {
        "input_type": "text",
        "text": "There is a medical emergency at the park.",
        "lat": 10.0,
        "lng": 20.0
    }
    
    response = client.post("/api/capture", data=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["priority"] == "P1"
    assert data["category"] == "Medical"
    assert data["location"]["lat"] == 10.0
    assert mock_analyze.called
    assert mock_save.called


# --- HISTORY TESTS ---

@patch("app.services.firestore.get_recent_incidents")
def test_get_history_success(mock_get):
    """Verify history endpoint retrieves items from Firestore."""
    mock_get.return_value = [
        {"priority": "P1", "category": "Medical", "summary": "Incident 1", "confidence": 0.9, "id": "1"},
        {"priority": "P2", "category": "Safety", "summary": "Incident 2", "confidence": 0.8, "id": "2"},
    ]
    
    response = client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["priority"] == "P1"
    assert mock_get.called


# --- CONFIRM TESTS ---

@patch("app.services.storage.archive_incident_json")
def test_confirm_dispatch_success(mock_archive):
    """Verify /api/confirm generates a dispatch ID and archives to GCS."""
    mock_archive.return_value = "gs://mock-bucket/archives/test.json"

    # Minimal VerificationCard structure for the request
    card_data = {
        "priority": "P1",
        "category": "Medical",
        "location": {"lat": 12.34, "lng": 56.78, "description": "123 Main St"},
        "summary": "Verified report.",
        "confidence": 1.0,
        "action_payload": {
            "dispatch_type": "ambulance",
            "units_needed": 1,
            "urgency_minutes": 5,
            "notes": "Fastest response"
        }
    }

    payload = {
        "confirmed_by": "test_agent_007",
        "card": card_data
    }

    response = client.post("/api/confirm", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "BL-" in data["dispatch_id"]
    assert data["status"] == "dispatched"
    assert "Priority 1" in data["message"]
    
    # Ensure archival was called with the dispatch_id included
    assert mock_archive.called
    archived_data = mock_archive.call_args[1]["incident_data"]
    assert archived_data["dispatch_id"] == data["dispatch_id"]
    assert archived_data["confirmed_at"] is not None
