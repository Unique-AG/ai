"""Per-request identity resolution for knowledge-base search.

``unique_mcp.get_unique_settings`` resolves identity as:

1. ``_meta`` ``unique.app/auth/user-id`` + ``company-id`` (Unique AI)
2. Zitadel JWT claims ``sub`` + ``urn:zitadel:iam:user:resourceowner:id``
3. Environment ``UNIQUE_AUTH_*`` (fixed service / local-dev user)

Step 3 is unsafe for a multi-user MCP server: if the JWT omits the company
claim (common), every logged-in caller would search as the env service user.

This module tightens that for search: when an OAuth access token is present,
identity must come from ``_meta``, JWT claims, or Zitadel ``/userinfo`` —
never from the fixed env credentials.
"""

from __future__ import annotations

import logging

from pydantic import SecretStr

from unique_mcp import MetaKeys, get_request_meta, get_unique_userinfo
from unique_toolkit.app.unique_settings import AuthContext, UniqueSettings

_LOGGER = logging.getLogger(__name__)

_CLAIM_USER_ID = "sub"
_CLAIM_COMPANY_ID = "urn:zitadel:iam:user:resourceowner:id"


def _get_access_token():
    try:
        from fastmcp.server.dependencies import get_access_token
    except ImportError:
        return None
    try:
        return get_access_token()
    except (RuntimeError, LookupError):
        return None


def _meta_has_auth(meta: dict | None) -> bool:
    if not meta:
        return False
    uid = meta.get(MetaKeys.USER_ID)
    cid = meta.get(MetaKeys.COMPANY_ID)
    return isinstance(uid, str) and bool(uid) and isinstance(cid, str) and bool(cid)


def _jwt_has_auth(token) -> bool:
    if token is None:
        return False
    claims = getattr(token, "claims", None) or {}
    uid = claims.get(_CLAIM_USER_ID)
    cid = claims.get(_CLAIM_COMPANY_ID)
    return isinstance(uid, str) and bool(uid) and isinstance(cid, str) and bool(cid)


async def resolve_search_settings(settings: UniqueSettings) -> UniqueSettings:
    """Return settings whose auth is the logged-in user (or trusted ``_meta``).

    Raises:
        ValueError: An OAuth token is present but neither JWT claims nor
            Zitadel userinfo yield both ``user_id`` and ``company_id``. This
            refuses the env ``UNIQUE_AUTH_*`` fallback for authenticated calls.
    """
    meta = get_request_meta()
    if _meta_has_auth(meta):
        _LOGGER.debug(
            "Search auth from _meta (user=%s)", meta.get(MetaKeys.USER_ID)  # type: ignore[union-attr]
        )
        return settings

    token = _get_access_token()
    if token is None:
        # No OAuth session — keep env/local settings (dev without login).
        _LOGGER.debug("Search auth from env (no access token)")
        return settings

    if _jwt_has_auth(token):
        _LOGGER.debug("Search auth from JWT claims")
        return settings

    userinfo = await get_unique_userinfo()
    if userinfo is not None:
        _LOGGER.debug("Search auth from userinfo (user=%s)", userinfo.user_id)
        return settings.with_auth(
            AuthContext(
                user_id=SecretStr(userinfo.user_id),
                company_id=SecretStr(userinfo.company_id),
            )
        )

    raise ValueError(
        "Authenticated session could not be resolved to a Unique user_id and "
        "company_id. Ensure the Zitadel access token includes the "
        "'urn:zitadel:iam:user:resourceowner' scope/claim, or that "
        "/oidc/v1/userinfo returns sub and "
        "urn:zitadel:iam:user:resourceowner:id. "
        "Refusing to fall back to UNIQUE_AUTH_* service credentials."
    )
