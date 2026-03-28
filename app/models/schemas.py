from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class LocationModel(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    description: str = "Unknown location"


class ActionPayload(BaseModel):
    dispatch_type: str = "other"
    units_needed: int = 1
    urgency_minutes: int = 60
    notes: str = ""


class VerificationCard(BaseModel):
    priority: Literal["P1", "P2", "P3", "P4"]
    category: Literal["Medical", "Infrastructure", "Safety", "Other"]
    location: LocationModel
    summary: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    action_payload: ActionPayload


class ConfirmRequest(BaseModel):
    card: VerificationCard
    confirmed_by: Optional[str] = "anonymous"


class DispatchAck(BaseModel):
    dispatch_id: str
    status: str
    message: str
