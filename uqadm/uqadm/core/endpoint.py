"""Parse ``slot:space_id`` endpoints and optional HTTPS URLs."""

from __future__ import annotations

from urllib.parse import urlparse


class EndpointParseError(ValueError):
    """Invalid migrate endpoint string."""


def extract_space_id_from_url(url: str) -> str:
    """Extract space id from admin-style paths."""
    parsed = urlparse(url.strip())
    segments = [s for s in parsed.path.strip("/").split("/") if s]
    for i, seg in enumerate(segments):
        if seg in (
            "space",
            "custom-space",
            "swappable-intelligence-space",
        ):
            if i + 1 < len(segments):
                candidate = segments[i + 1]
                if candidate.lower() != "create":
                    return candidate
    detail = (
        "Could not extract space id from URL path (expected .../space/<id> / "
        + ".../custom-space/<id> / .../swappable-intelligence-space/<id>): "
        + url
    )
    raise EndpointParseError(detail)


def parse_endpoint(spec: str) -> tuple[str, str | None]:
    """Parse ``slot`` or ``slot:space_id``.

    If ``space_id`` looks like an ``http(s)`` URL, the space id is parsed from
    its path.

    Returns:
        ``(slot, space_id)`` where ``space_id`` may be ``None`` for
        create-destination cases.
    """
    raw = spec.strip()
    if not raw:
        raise EndpointParseError("Endpoint must be non-empty.")

    if ":" not in raw:
        return raw, None

    slot, rest = raw.split(":", 1)
    slot = slot.strip()
    rest_stripped = rest.strip()
    if not slot:
        raise EndpointParseError(f"Missing slot in endpoint: {spec!r}")

    if not rest_stripped:
        return slot, None

    if rest_stripped.startswith("http://") or rest_stripped.startswith("https://"):
        return slot, extract_space_id_from_url(rest_stripped)

    return slot, rest_stripped


def parse_source_endpoint(spec: str) -> tuple[str, str]:
    """Parse migrate ``--source``; space id is required."""
    slot, space_id = parse_endpoint(spec)
    if not space_id:
        raise EndpointParseError(
            "--source must include a space id, e.g. `1:space_abc` or `1:https://host/app/space/space_abc`."
        )
    return slot, space_id


def parse_bare_endpoint(spec: str) -> str:
    """Parse a bare space id or URL (no slot prefix).

    Accepts:
    - ``space_abc``          → ``"space_abc"``
    - ``https://host/.../space/space_abc``  → ``"space_abc"``

    A ``slot:id`` string is also accepted for backwards-compatibility; the slot
    portion is silently discarded because the caller already resolved the slot
    via ``--slot`` / the default slot.

    Raises:
        EndpointParseError: If no space id can be determined.
    """
    raw = spec.strip()
    if not raw:
        raise EndpointParseError("Space id must be non-empty.")

    if raw.startswith("http://") or raw.startswith("https://"):
        return extract_space_id_from_url(raw)

    if ":" in raw:
        _, rest = raw.split(":", 1)
        rest = rest.strip()
        if not rest:
            raise EndpointParseError(
                f"Could not extract a space id from {spec!r}. "
                "Pass just the space id, e.g. `space_abc`."
            )
        if rest.startswith("http://") or rest.startswith("https://"):
            return extract_space_id_from_url(rest)
        return rest

    return raw
