"""Gemini SDK Migration — stable JSON parsing with compatibility fallback."""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Optional

from google import genai
from google.genai import types

from app.models.schemas import ActionPayload, LocationModel, VerificationCard

# ---------------------------------------------------------------------------
# Config: Target model for current environment
# ---------------------------------------------------------------------------
MODEL_NAME = "models/gemini-2.5-flash"

# ---------------------------------------------------------------------------
# System Instructions: Moved to a preamble in 'contents'.
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
""".strip()


def _get_client() -> genai.Client:
    """Initialize the new google-genai Client targeting v1."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
    
    return genai.Client(
        api_key=api_key,
        http_options={'api_version': 'v1'}
    )


def _log_available_models(client: genai.Client):
    """Utility to troubleshoot model availability."""
    print(f"--- DIAGNOSTIC: Listing available models ---", file=sys.stderr)
    try:
        for model in client.models.list():
            print(f"  Supported Model: {model.name}", file=sys.stderr)
    except Exception as e:
        print(f"  Diagnostic failed: {e}", file=sys.stderr)
    print("---------------------------------------------", file=sys.stderr)


def _generate_with_diagnostic(client: genai.Client, contents: list[types.Content], config: types.GenerateContentConfig):
    """Execution wrapper with error handling and diagnostic logging."""
    try:
        return client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=config
        )
    except Exception as e:
        err_msg = str(e).lower()
        if "404" in err_msg or "not_found" in err_msg:
            print(f"ERROR: Model '{MODEL_NAME}' not found.", file=sys.stderr)
            _log_available_models(client)
        raise


def _parse_response(raw: str) -> VerificationCard:
    """Parse raw Gemini text into a VerificationCard. Raises ValueError on failure."""
    # Robust parsing: try direct JSON first, then regex for fenced or conversationally-wrapped JSON.
    cleaned = raw.strip()
    try:
         data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback 1: Strip code fences manually
        unfenced = re.sub(r"```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip().rstrip("`").strip()
        try:
            data = json.loads(unfenced)
        except json.JSONDecodeError:
            # Fallback 2: Search for first { and last }
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Gemini output is truncated or malformed: {raw[:300]}") from exc
            else:
                raise ValueError(f"Gemini failed to output a JSON object: {raw[:300]}")

    loc_raw = data.get("location", {}) or {}
    action_raw = data.get("action_payload", {}) or {}

    return VerificationCard(
        priority=data.get("priority", "P4"),
        category=data.get("category", "Other"),
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
    client = _get_client()
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=_SYSTEM_PROMPT)]),
        types.Content(role="user", parts=[types.Part.from_text(text=f"Incident report:\n{text}")])
    ]
    if geo_hint:
        contents[1].parts.append(types.Part.from_text(text=f"\n\nUser GPS: {geo_hint}"))

    response = _generate_with_diagnostic(
        client, contents, 
        types.GenerateContentConfig(
            temperature=0.2, 
            max_output_tokens=1024
            # response_mime_type removed here to resolve 400 error on v1
        )
    )
    return _parse_response(response.text)


async def analyze_image(
    image_bytes: bytes,
    mime_type: str,
    geo_hint: Optional[str] = None,
) -> VerificationCard:
    client = _get_client()
    context = "Analyze this emergency scene image."
    if geo_hint:
        context += f" User GPS: {geo_hint}."

    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=_SYSTEM_PROMPT)]),
        types.Content(role="user", parts=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            types.Part.from_text(text=context)
        ])
    ]

    response = _generate_with_diagnostic(
        client, contents, 
        types.GenerateContentConfig(temperature=0.2, max_output_tokens=1024)
    )
    return _parse_response(response.text)


async def analyze_audio(audio_bytes: bytes, mime_type: str) -> VerificationCard:
    client = _get_client()
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=_SYSTEM_PROMPT)]),
        types.Content(role="user", parts=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            types.Part.from_text(text="Transcribe and analyze this voice report.")
        ])
    ]

    response = _generate_with_diagnostic(
        client, contents, 
        types.GenerateContentConfig(temperature=0.2, max_output_tokens=1024)
    )
    return _parse_response(response.text)
