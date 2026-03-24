from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp.server.dependencies import get_access_token, get_context
from pydantic import SecretStr
from unique_toolkit.app.unique_settings import (
    AuthContext,
    UniqueContext,
    UniqueSettings,
)

from unique_mcp.auth.zitadel.oauth_proxy import ZitadelOAuthProxySettings

logger = logging.getLogger(__name__)

_CLAIM_USER_ID = "sub"
_CLAIM_COMPANY_ID = "urn:zitadel:iam:user:resourceowner:id"

_META_USER_ID = "unique.app/user-id"
_META_COMPANY_ID = "unique.app/company-id"

_USERINFO_TIMEOUT = 10.0


def _make_auth(user_id: str, company_id: str) -> AuthContext:
    return AuthContext(
        user_id=SecretStr(user_id),
        company_id=SecretStr(company_id),
    )


def _read_meta() -> dict[str, Any] | None:
    """Read ``_meta`` from the active FastMCP request, if available."""
    try:
        ctx = get_context()
    except (RuntimeError, LookupError):
        return None
    rc = ctx.request_context
    if rc is None or rc.meta is None:
        return None
    return dict(rc.meta) or None


class UniqueContextProvider:
    """Resolves per-request auth from the active MCP request.

    Priority (highest wins):
      1. ``_meta`` keys (``unique.app/user-id``, ``unique.app/company-id``)
      2. JWT claims
      3. Zitadel userinfo endpoint

    Usage::

        settings = await provider.get_settings()
    """

    def __init__(
        self,
        *,
        settings: UniqueSettings | None = None,
        zitadel_settings: ZitadelOAuthProxySettings | None = None,
    ) -> None:
        self._settings = settings or UniqueSettings.from_env_auto_with_sdk_init()
        self._zitadel = zitadel_settings or ZitadelOAuthProxySettings()
        self._http = httpx.AsyncClient(timeout=_USERINFO_TIMEOUT)

    async def get_settings(self) -> UniqueSettings:
        """Per-request UniqueSettings (swaps auth, keeps app/api)."""
        return UniqueSettings(
            auth=await self._resolve_auth(),
            app=self._settings.app,
            api=self._settings.api,
        )

    async def get_context(self) -> UniqueContext:
        """Per-request UniqueContext (auth only, no chat)."""
        return UniqueContext(auth=await self._resolve_auth())

    async def get_userinfo(self) -> dict[str, Any]:
        """Full Zitadel userinfo for the current request's token.

        Useful when you need fields beyond user_id/company_id (e.g. email).
        """
        token = get_access_token()
        if token is None:
            raise RuntimeError("No access token. Is OAuth configured?")
        return await self._fetch_userinfo(token.token)

    async def _resolve_auth(self) -> AuthContext:
        """_meta > JWT claims > Zitadel userinfo."""

        meta = _read_meta()
        if meta:
            uid = meta.get(_META_USER_ID)
            cid = meta.get(_META_COMPANY_ID)
            if uid and cid:
                logger.debug("Auth from _meta (user=%s)", uid)
                return _make_auth(uid, cid)

        token = get_access_token()
        if token is None:
            raise RuntimeError("No access token. Is OAuth configured?")

        uid = token.claims.get(_CLAIM_USER_ID)
        cid = token.claims.get(_CLAIM_COMPANY_ID)
        if uid and cid:
            logger.debug("Auth from JWT (user=%s)", uid)
            return _make_auth(uid, cid)

        logger.debug("JWT incomplete, falling back to userinfo")
        info = await self._fetch_userinfo(token.token)
        uid = info.get("sub")
        cid = info.get(_CLAIM_COMPANY_ID)
        if not uid or not cid:
            raise ValueError(
                f"Zitadel userinfo incomplete: sub={uid!r}, company_id={cid!r}"
            )
        logger.debug("Auth from userinfo (user=%s)", uid)
        return _make_auth(uid, cid)

    async def close(self) -> None:
        """Close the underlying HTTP client (call on shutdown)."""
        await self._http.aclose()

    async def _fetch_userinfo(self, bearer: str) -> dict[str, Any]:
        resp = await self._http.get(
            self._zitadel.userinfo_endpoint,
            headers={"Authorization": f"Bearer {bearer}"},
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]
