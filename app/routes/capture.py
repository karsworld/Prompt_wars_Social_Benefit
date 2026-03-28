"""
POST /api/capture — accepts multipart/form-data with:
  - input_type : "text" | "image" | "voice"
  - text        : optional str
  - file        : optional UploadFile (image or audio)
  - lat / lng   : optional floats from browser geolocation
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.schemas import VerificationCard
from app.services import gemini, sanitizer, storage

router = APIRouter()


@router.post("/capture", response_model=VerificationCard, tags=["core"])
async def capture(
    input_type: str = Form(..., description="text | image | voice"),
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
) -> VerificationCard:
    geo_hint: Optional[str] = f"{lat},{lng}" if lat is not None and lng is not None else None

    try:
        if input_type == "text":
            if not text:
                raise HTTPException(status_code=400, detail="text field is required for input_type='text'")
            clean = sanitizer.sanitize_text(text)
            card = await gemini.analyze_text(clean, geo_hint=geo_hint)

        elif input_type == "image":
            if file is None:
                raise HTTPException(status_code=400, detail="file is required for input_type='image'")
            data = await file.read()
            content_type = file.content_type or "image/jpeg"
            sanitizer.validate_image(data, content_type)
            card = await gemini.analyze_image(data, content_type, geo_hint=geo_hint)

        elif input_type == "voice":
            if file is None:
                raise HTTPException(status_code=400, detail="file is required for input_type='voice'")
            data = await file.read()
            sanitizer.validate_audio(data)
            content_type = file.content_type or "audio/webm"
            card = await gemini.analyze_audio(data, content_type)

        else:
            raise HTTPException(status_code=400, detail=f"Unknown input_type: '{input_type}'")

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc

    # Backfill GPS coords if Gemini couldn't extract them but browser provided them
    if geo_hint and card.location.lat is None:
        card.location.lat = lat
        card.location.lng = lng

    return card
