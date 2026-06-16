from __future__ import annotations


def join_url_path(base: str, *segments: str) -> str:
    """Join a URL base with path segments, normalizing slashes."""
    normalized_base = base.rstrip("/")
    normalized_segments = [
        segment.strip("/") for segment in segments if segment.strip("/")
    ]
    if not normalized_segments:
        return normalized_base
    return f"{normalized_base}/{'/'.join(normalized_segments)}"
