"""Per-request identity resolution for space chat tools.

Prefers :func:`unique_mcp.get_unique_settings_async` when available (monorepo /
newer releases). Falls back to composing the PyPI ``unique-mcp`` injectors
so Docker builds that install from PyPI still load tools.
"""

from __future__ import annotations

from pydantic import SecretStr

from unique_toolkit.app.unique_settings import AuthContext, UniqueSettings

try:
    from unique_mcp import get_unique_settings_async as _shared_get_unique_settings_async
except ImportError:  # PyPI unique-mcp before the async injector was published
    _shared_get_unique_settings_async = None

_CLAIM_USER_ID = "sub"
_CLAIM_COMPANY_ID = "urn:zitadel:iam:user:resourceowner:id"


async def _resolve_via_pypi_injectors() -> UniqueSettings:
    """Mirror ``get_unique_settings_async`` with APIs present on PyPI today.

    Priority: ``_meta`` auth → JWT claims → Zitadel ``/userinfo`` → env.
    When an access token is present but identity cannot be resolved, raise
    instead of using ``UNIQUE_AUTH_*`` service credentials.
    """
    from fastmcp.server.dependencies import get_access_token

    from unique_mcp import (
        META_FLAT_ALIASES,
        MetaKeys,
        get_request_meta,
        get_unique_settings,
        get_unique_userinfo,
    )

    settings = get_unique_settings()
    meta = get_request_meta()
    if meta is not None:
        uid = meta.get(MetaKeys.USER_ID) or meta.get(
            META_FLAT_ALIASES.get(MetaKeys.USER_ID, "")
        )
        cid = meta.get(MetaKeys.COMPANY_ID) or meta.get(
            META_FLAT_ALIASES.get(MetaKeys.COMPANY_ID, "")
        )
        if isinstance(uid, str) and uid and isinstance(cid, str) and cid:
            return settings

    token = get_access_token()
    if token is not None:
        claims = getattr(token, "claims", None) or {}
        uid = claims.get(_CLAIM_USER_ID)
        cid = claims.get(_CLAIM_COMPANY_ID)
        if isinstance(uid, str) and uid and isinstance(cid, str) and cid:
            return settings.with_auth(
                AuthContext(user_id=SecretStr(uid), company_id=SecretStr(cid))
            )

        userinfo = await get_unique_userinfo()
        if userinfo is not None:
            return settings.with_auth(
                AuthContext(
                    user_id=SecretStr(userinfo.user_id),
                    company_id=SecretStr(userinfo.company_id),
                )
            )

        raise ValueError(
            "Authenticated session could not be resolved to user_id and "
            "company_id (JWT claims incomplete and userinfo unavailable). "
            "Refusing UNIQUE_AUTH_* env fallback for a logged-in request."
        )

    return settings


async def get_unique_settings_async() -> UniqueSettings:
    """Resolve logged-in identity; shared injector when published, else fallback."""
    if _shared_get_unique_settings_async is not None:
        return await _shared_get_unique_settings_async()
    return await _resolve_via_pypi_injectors()


async def resolve_chat_settings(
    settings: UniqueSettings | None = None,
) -> UniqueSettings:
    """Return settings whose auth is the logged-in user (or trusted ``_meta``).

    The ``settings`` argument is accepted for call-site compatibility with
    ``Depends(get_unique_settings)`` but is ignored — resolution always goes
    through the async injector so meta/JWT/userinfo handling cannot drift.

    Raises:
        ValueError: An OAuth token is present but neither JWT claims nor
            Zitadel userinfo yield both ``user_id`` and ``company_id``.
    """
    del settings  # identity comes from the async resolver only
    return await get_unique_settings_async()


def sdk_identity(settings: UniqueSettings) -> tuple[str, str]:
    """Configure the global unique_sdk from ``settings`` and return identity.

    ``unique_sdk`` uses module-level configuration (``api_key``, ``app_id``,
    ``api_base``) plus per-call ``user_id``/``company_id``. This helper wires
    the globals from the resolved settings and returns the per-call pair.
    """
    settings.init_sdk()
    return (
        settings.auth.user_id.get_secret_value(),
        settings.auth.company_id.get_secret_value(),
    )
