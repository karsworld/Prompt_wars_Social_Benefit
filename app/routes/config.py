"""
GET /api/config — exposes non-secret client config (Maps API key) to the frontend.
The Maps JS API key is NOT secret (it appears in browser network tab anyway),
but must still be restricted to your domain in the Google Cloud Console.
"""
import os
from fastapi import APIRouter

router = APIRouter()


@router.get("/config", tags=["ops"])
async def config() -> dict:
    return {
        "maps_key": os.getenv("GOOGLE_MAPS_API_KEY", ""),
    }
