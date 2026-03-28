"""
GET /api/config — exposes non-secret client config (Maps API key) to the frontend.
The Maps JS API key is NOT secret (it appears in browser network tab anyway),
but must still be restricted to your domain in the Google Cloud Console.
"""
import functools
import os

from fastapi import APIRouter

router = APIRouter()


@router.get("/config", tags=["system"])
@functools.lru_cache()
def get_config() -> dict[str, str]:
    """Retrieve maps keys etc. (Cached for efficiency)."""
    return {
        "GOOGLE_MAPS_API_KEY": os.getenv("GOOGLE_MAPS_API_KEY", ""),
    }
