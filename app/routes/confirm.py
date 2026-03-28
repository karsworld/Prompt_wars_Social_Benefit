"""
POST /api/confirm — receives an approved VerificationCard and returns
a mock dispatch acknowledgment (simulates the "Complex Systems" API).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.schemas import ConfirmRequest, DispatchAck

router = APIRouter()

_DISPATCH_MESSAGES = {
    "P1": "🚨 Priority 1 dispatch initiated. Units en route immediately.",
    "P2": "⚠️ Priority 2 incident logged. Response within 1 hour.",
    "P3": "📋 Priority 3 report filed. Response within 24 hours.",
    "P4": "ℹ️ Informational report recorded. No immediate dispatch.",
}


@router.post("/confirm", response_model=DispatchAck, tags=["core"])
async def confirm(body: ConfirmRequest) -> DispatchAck:
    """Accept a verified card, log it, and return a mock dispatch acknowledgment."""
    dispatch_id = f"BL-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()

    # In production: POST to real CAD / emergency dispatch API here
    print(
        f"[{timestamp}] DISPATCH {dispatch_id} | "
        f"{body.card.priority} {body.card.category} | "
        f"by={body.confirmed_by} | "
        f"summary={body.card.summary!r}"
    )

    message = _DISPATCH_MESSAGES.get(body.card.priority, "Report received.")
    return DispatchAck(
        dispatch_id=dispatch_id,
        status="dispatched",
        message=message,
    )
