"""Derive the verified caller identity from the validated access token.

Identity comes from the *verified* JWT (FastMCP has already checked signature,
issuer, audience and expiry before the tool/resource runs), never from
client-supplied `_meta`. The `sub` claim is the authenticated user id.
"""

from __future__ import annotations

from fastmcp.server.dependencies import get_access_token


def current_subject() -> str:
    """Return the authenticated caller's user id (token `sub`), or fail closed."""
    token = get_access_token()
    if token is None:
        raise PermissionError("no authenticated caller")

    subject = token.claims.get("sub")
    if not subject:
        raise PermissionError("access token has no subject (sub) claim")
    return str(subject)
