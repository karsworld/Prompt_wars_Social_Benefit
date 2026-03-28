"""
Pytest suite for BridgeLink parsing logic and input sanitization.
Run with:  pytest tests/ -v
"""
import json
import pytest

from app.models.schemas import ActionPayload, LocationModel, VerificationCard
from app.services.gemini import _parse_response
from app.services.sanitizer import (
    MAX_TEXT_LENGTH,
    sanitize_text,
    validate_audio,
    validate_image,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_payload(**overrides) -> dict:
    base = {
        "priority": "P1",
        "category": "Medical",
        "location": {"lat": 37.7749, "lng": -122.4194, "description": "Market St, San Francisco"},
        "summary": "Person collapsed and unresponsive on the street.",
        "confidence": 0.95,
        "action_payload": {
            "dispatch_type": "ambulance",
            "units_needed": 2,
            "urgency_minutes": 5,
            "notes": "Possible cardiac arrest — AED on scene.",
        },
    }
    base.update(overrides)
    return base


# ─── _parse_response tests ────────────────────────────────────────────────────

class TestParseResponse:

    def test_valid_p1_medical(self):
        card = _parse_response(json.dumps(_make_payload()))
        assert card.priority == "P1"
        assert card.category == "Medical"
        assert card.location.lat == pytest.approx(37.7749)
        assert card.location.lng == pytest.approx(-122.4194)
        assert "collapsed" in card.summary.lower()
        assert card.confidence == pytest.approx(0.95)
        assert card.action_payload.dispatch_type == "ambulance"
        assert card.action_payload.units_needed == 2
        assert card.action_payload.urgency_minutes == 5

    def test_valid_p4_other(self):
        card = _parse_response(json.dumps(_make_payload(
            priority="P4",
            category="Other",
            action_payload={"dispatch_type": "other", "units_needed": 1,
                            "urgency_minutes": 1440, "notes": ""},
        )))
        assert card.priority == "P4"
        assert card.category == "Other"

    def test_null_coordinates_allowed(self):
        payload = _make_payload()
        payload["location"] = {"lat": None, "lng": None, "description": "Somewhere in the city"}
        card = _parse_response(json.dumps(payload))
        assert card.location.lat is None
        assert card.location.lng is None
        assert card.location.description == "Somewhere in the city"

    def test_malformed_json_raises_value_error(self):
        with pytest.raises(ValueError, match="invalid JSON"):
            _parse_response("{not: valid json}")

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            _parse_response("")

    def test_strips_markdown_code_fences(self):
        raw = f"```json\n{json.dumps(_make_payload())}\n```"
        card = _parse_response(raw)
        assert card.priority == "P1"

    def test_strips_plain_code_fences(self):
        raw = f"```\n{json.dumps(_make_payload())}\n```"
        card = _parse_response(raw)
        assert card.priority == "P1"

    def test_infrastructure_category(self):
        card = _parse_response(json.dumps(_make_payload(
            priority="P3",
            category="Infrastructure",
            action_payload={"dispatch_type": "utilities", "units_needed": 1,
                            "urgency_minutes": 240, "notes": "Gas leak reported"},
        )))
        assert card.category == "Infrastructure"
        assert card.action_payload.dispatch_type == "utilities"


# ─── sanitize_text tests ──────────────────────────────────────────────────────

class TestSanitizeText:

    def test_strips_script_tags(self):
        dirty = '<script>alert("xss")</script>Help!'
        clean = sanitize_text(dirty)
        assert "<script>" not in clean
        assert "Help!" in clean

    def test_strips_html_tags(self):
        dirty = "<b>Bold</b> and <i>italic</i>"
        clean = sanitize_text(dirty)
        assert "<b>" not in clean
        assert "Bold" in clean
        assert "italic" in clean

    def test_strips_event_handlers(self):
        dirty = 'Click me <a onclick="evil()">here</a>'
        clean = sanitize_text(dirty)
        assert "onclick" not in clean

    def test_truncates_to_max_length(self):
        long_text = "a" * (MAX_TEXT_LENGTH + 500)
        clean = sanitize_text(long_text)
        assert len(clean) <= MAX_TEXT_LENGTH

    def test_normal_text_unchanged(self):
        normal = "There is a gas leak at 5th and Main. Smell is strong."
        assert sanitize_text(normal) == normal

    def test_empty_string(self):
        assert sanitize_text("") == ""


# ─── validate_image tests ─────────────────────────────────────────────────────

class TestValidateImage:

    def test_rejects_unsupported_mime(self):
        with pytest.raises(ValueError, match="Invalid image type"):
            validate_image(b"data", "application/pdf")

    def test_rejects_oversized_image(self):
        oversized = b"x" * (6 * 1024 * 1024)  # 6 MB
        with pytest.raises(ValueError, match="too large"):
            validate_image(oversized, "image/jpeg")

    def test_rejects_corrupted_data(self):
        with pytest.raises(ValueError):
            validate_image(b"not-an-image", "image/png")


# ─── validate_audio tests ─────────────────────────────────────────────────────

class TestValidateAudio:

    def test_rejects_oversized_audio(self):
        oversized = b"x" * (11 * 1024 * 1024)  # 11 MB
        with pytest.raises(ValueError, match="too large"):
            validate_audio(oversized)

    def test_rejects_empty_audio(self):
        with pytest.raises(ValueError, match="empty"):
            validate_audio(b"")

    def test_accepts_valid_audio(self):
        data = b"x" * 1000
        assert validate_audio(data) == data


# ─── Schema validation tests ──────────────────────────────────────────────────

class TestSchemas:

    def test_confidence_clamp_fails_below_zero(self):
        with pytest.raises(Exception):
            VerificationCard(
                priority="P1", category="Medical",
                location=LocationModel(description="test"),
                summary="test",
                confidence=-0.1,
                action_payload=ActionPayload(),
            )

    def test_confidence_clamp_fails_above_one(self):
        with pytest.raises(Exception):
            VerificationCard(
                priority="P1", category="Medical",
                location=LocationModel(description="test"),
                summary="test",
                confidence=1.5,
                action_payload=ActionPayload(),
            )

    def test_invalid_priority_fails(self):
        with pytest.raises(Exception):
            VerificationCard(
                priority="P9", category="Medical",
                location=LocationModel(description="test"),
                summary="test",
                confidence=0.5,
                action_payload=ActionPayload(),
            )
