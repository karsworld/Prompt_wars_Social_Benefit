"""FastAPI application entry point for BridgeLink."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routes import capture, confirm, config, health

load_dotenv()  # Load .env for local development (no-op on Cloud Run)

app = FastAPI(
    title="BridgeLink",
    description="Gemini-powered crisis reporting — PromptWars Challenge",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# CORS — restrict in production to your actual domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# API routes
app.include_router(health.router)
app.include_router(capture.router, prefix="/api")
app.include_router(confirm.router, prefix="/api")
app.include_router(config.router, prefix="/api")

# Serve the SPA static files
_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_spa() -> FileResponse:
    """Serve the single-page frontend."""
    return FileResponse(str(_STATIC_DIR / "index.html"))
