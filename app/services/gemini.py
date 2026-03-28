"""Gemini 1.5 Flash integration — multimodal incident analysis."""
from __future__ import annotations

import json
import os
import re
from typing import Optional

import google.generativeai as genai

from app.models.schemas import ActionPayload, LocationModel, VerificationCard

# ---------------------------------------------------------------------------
# System prompt: instructs Gemini to return ONLY structured JSON
# Low temperature (0.2) keeps output deterministic and token-efficient
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """
You are an emergency triage AI for the BridgeLink crisis response system.
Analyze the provided input (text, image, or audio) and extract structured incident data.

RESPOND ONLY with a single valid JSON object — no markdown, no explanation, no code fences.

JSON schema:
{
  "priority": "P1" | "P2" | "P3" | "P4",
  "category": "Medical" | "Infrastructure" | "Safety" | "Other",
  "location": {
    "lat": <float or null>,
    "lng": <float or null>,
    "description": "<location description string>"
  },
  "summary": "<one sentence describing the incident>",
  "confidence": <float 0.0–1.0>,
  "action_payload": {
    "dispatch_type": "ambulance" | "fire" | "police" | "utilities" | "other",
    "units_needed": <integer>,
    "urgency_minutes": <integer>,
    "notes": "<brief notes for first responders>"
  }
}

Priority definitions:
  P1 — Life-threatening (act within minutes)
  P2 — Serious (act within 1 hour)
  P3 — Non-urgent (act within 24 hours)
  P4 — Informational / low priority
""".strip()


def _build_model() -> genai.GenerativeModel:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=512,
        ),
        system_instruction=_SYSTEM_PROMPT,
    )


def _parse_response(raw: str) -> VerificationCard:
    """Parse raw Gemini text into a VerificationCard. Raises ValueError on failure."""
    # Strip markdown code fences if Gemini wraps the JSON anyway
    cleaned = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE).strip().rstrip("`").strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini returned invalid JSON: {exc}\nRaw output: {raw[:300]}") from exc

    loc_raw = data.get("location", {}) or {}
    action_raw = data.get("action_payload", {}) or {}

    return VerificationCard(
        priority=data["priority"],
        category=data["category"],
        location=LocationModel(
            lat=loc_raw.get("lat"),
            lng=loc_raw.get("lng"),
            description=loc_raw.get("description", "Unknown location"),
        ),
        summary=data.get("summary", "No summary provided."),
        confidence=float(data.get("confidence", 0.5)),
        action_payload=ActionPayload(
            dispatch_type=action_raw.get("dispatch_type", "other"),
            units_needed=int(action_raw.get("units_needed", 1)),
            urgency_minutes=int(action_raw.get("urgency_minutes", 60)),
            notes=action_raw.get("notes", ""),
        ),
    )


async def analyze_text(text: str, geo_hint: Optional[str] = None) -> VerificationCard:
    model = _build_model()
    prompt = f"Incident report:\n{text}"
    if geo_hint:
        prompt += f"\n\nUser's GPS coordinates: {geo_hint}"
    response = model.generate_content(prompt)
    return _parse_response(response.text)


async def analyze_image(
    image_bytes: bytes,
    mime_type: str,
    geo_hint: Optional[str] = None,
) -> VerificationCard:
    model = _build_model()
    parts: list = [{"mime_type": mime_type, "data": image_bytes}]
    context = "Analyze this emergency scene image."
    if geo_hint:
        context += f" User GPS: {geo_hint}."
    parts.append(context)
    response = model.generate_content(parts)
    return _parse_response(response.text)


async def analyze_audio(audio_bytes: bytes, mime_type: str) -> VerificationCard:
    model = _build_model()
    parts: list = [
        {"mime_type": mime_type, "data": audio_bytes},
        "Transcribe and analyze this emergency voice report.",
    ]
    response = model.generate_content(parts)
    return _parse_response(response.text)
