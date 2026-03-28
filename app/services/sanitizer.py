"""Input sanitization utilities — strips XSS vectors, enforces size limits."""
from __future__ import annotations

import io
import re

# from PIL import Image delayed to validate_image for startup performance

MAX_TEXT_LENGTH = 2_000
MAX_IMAGE_BYTES = 5 * 1024 * 1024   # 5 MB
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def sanitize_text(text: str) -> str:
    """Remove HTML/script tags and JS event handlers; truncate to safe length."""
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Strip inline JS event handlers (onclick=, onload=, etc.)
    text = re.sub(r"(?i)on\w+\s*=\s*(?:['\"].*?['\"]|\S+)", "", text)
    # Collapse whitespace and trim for payload efficiency
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_TEXT_LENGTH]


def validate_image(data: bytes, content_type: str) -> bytes:
    """Validate image MIME type, size, and integrity. Returns data unchanged."""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError(f"Invalid image type '{content_type}'. Allowed: {ALLOWED_IMAGE_TYPES}")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"Image too large: {len(data):,} bytes (max {MAX_IMAGE_BYTES:,})"
        )
    try:
        from PIL import Image, UnidentifiedImageError
        img = Image.open(io.BytesIO(data))
        img.verify()  # Raises on corrupt files
    except UnidentifiedImageError:
        raise ValueError("Cannot identify image file — possibly corrupted or unsupported format.")
    except Exception as exc:
        raise ValueError(f"Invalid image data: {exc}") from exc
    return data


def validate_audio(data: bytes) -> bytes:
    """Validate audio blob size. Returns data unchanged."""
    if len(data) > MAX_AUDIO_BYTES:
        raise ValueError(
            f"Audio too large: {len(data):,} bytes (max {MAX_AUDIO_BYTES:,})"
        )
    if len(data) == 0:
        raise ValueError("Audio data is empty.")
    return data
