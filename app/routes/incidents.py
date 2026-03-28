"""Router for fetching incident history from Firestore."""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from app.services import firestore

router = APIRouter()

@router.get("/incidents", tags=["history"])
async def get_history() -> list[dict[str, Any]]:
    """Retrieve the 3 most recent analyzed incidents for the dashboard."""
    return await firestore.get_recent_incidents(limit=3)
