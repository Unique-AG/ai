from __future__ import annotations

import logging

import httpx

try:
    from fastmcp.server.dependencies import get_access_token, get_context
except ImportError:

    def return_none():
        return None

    get_access_token = return_none
    get_context = return_none


from pydantic import BaseModel, SecretStr
from unique_toolkit.app.unique_settings import (
    AuthContext,
    UniqueSettings,
)
from unique_toolkit.services.factory import UniqueServiceFactory

from unique_mcp.auth.zitadel.oauth_proxy import ZitadelOAuthProxySettings

_LOGGER = logging.getLogger(__name__)

_CLAIM_USER_ID = "sub"
_CLAIM_COMPANY_ID = "urn:zitadel:iam:user:resourceowner:id"
_META_USER_ID = "unique.app/user-id"
_META_COMPANY_ID = "unique.app/company-id"
_HTTP_CLIENT = httpx.AsyncClient(timeout=10.0)


def _fastmcp_context_to_auth_context() -> AuthContext | None:
    """Read ``_meta`` from the active FastMCP request, if available."""
    try:
        ctx = get_context()
    except (RuntimeError, LookupError):
        return None
    rc = ctx.request_context
    if rc is None or rc.meta is None:
        return None
    meta = dict(rc.meta) or None
    if meta:
        uid = meta.get(_META_USER_ID, None)
        cid = meta.get(_META_COMPANY_ID, None)
        if uid and isinstance(uid, str) and cid and isinstance(cid, str):
            _LOGGER.debug("Auth from _meta (user=%s)", uid)
            return AuthContext(user_id=SecretStr(uid), company_id=SecretStr(cid))
    return None


def _fastmcp_access_token_to_auth_context() -> AuthContext | None:
    token = get_access_token()
    if token:
        uid = token.claims.get(_CLAIM_USER_ID)
        cid = token.claims.get(_CLAIM_COMPANY_ID)
        if uid and isinstance(uid, str) and cid and isinstance(cid, str):
            _LOGGER.debug("Auth from JWT (user=%s)", uid)
            return AuthContext(user_id=SecretStr(uid), company_id=SecretStr(cid))
    return None


def get_zitadel_settings() -> ZitadelOAuthProxySettings:
    return ZitadelOAuthProxySettings()


class UniqueUserInfo(BaseModel):
    user_id: str
    company_id: str
    email: str | None = None


async def get_unique_userinfo(
    http_client: httpx.AsyncClient = _HTTP_CLIENT,
) -> UniqueUserInfo | None:
    token = get_access_token()
    zitadel_settings = get_zitadel_settings()
    if token:
        resp = await http_client.get(
            zitadel_settings.userinfo_endpoint,
            headers={"Authorization": f"Bearer {token.token}"},
        )
        resp.raise_for_status()

        info = resp.json()
        uid = info.get(_CLAIM_USER_ID)
        cid = info.get(_CLAIM_COMPANY_ID)
        if not uid or not isinstance(uid, str) or not cid or not isinstance(cid, str):
            raise ValueError(
                f"Zitadel userinfo incomplete: sub={uid!r}, company_id={cid!r}"
            )
        _LOGGER.debug("Auth from userinfo (user=%s)", uid)
        return UniqueUserInfo(email=info.get("email"), user_id=uid, company_id=cid)

    return None


async def _userinfo_to_auth_context(
    http_client: httpx.AsyncClient = _HTTP_CLIENT,
) -> AuthContext | None:
    userinfo = await get_unique_userinfo(http_client)
    if userinfo:
        return AuthContext(
            user_id=SecretStr(userinfo.user_id),
            company_id=SecretStr(userinfo.company_id),
        )


def get_unique_settings() -> UniqueSettings:
    settings = UniqueSettings.from_env_auto_with_sdk_init()

    # 1. _meta of the request has highest priority
    if auth_context := _fastmcp_context_to_auth_context():
        return settings.with_auth(auth_context)

    # 2. JWT claims of IDP have second highest priority
    if auth_context := _fastmcp_access_token_to_auth_context():
        return settings.with_auth(auth_context)

    # 3. Use auth from env variables
    return settings


def get_unique_service_factory() -> UniqueServiceFactory:
    settings = get_unique_settings()
    return UniqueServiceFactory(settings=settings)
