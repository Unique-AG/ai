from __future__ import annotations

import logging
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

import httpx

try:
    from fastmcp.server.dependencies import get_access_token, get_context
except ImportError:

    def return_none():
        return None

    get_access_token = return_none
    get_context = return_none


from pydantic import BaseModel, SecretStr
from unique_toolkit.agentic.feature_flags.feature_flags import feature_flags
from unique_toolkit.app.unique_settings import (
    AuthContext,
    ChatContext,
    UniqueSettings,
)
from unique_toolkit.services.factory import UniqueServiceFactory

from unique_mcp.auth.zitadel.oauth_proxy import ZitadelOAuthProxySettings
from unique_mcp.meta_keys import META_FLAT_ALIASES, MetaKeys

_LOGGER = logging.getLogger(__name__)

_CLAIM_USER_ID = "sub"
_CLAIM_COMPANY_ID = "urn:zitadel:iam:user:resourceowner:id"
_MCP_CHAT_CONTEXT_SENTINEL = "mcp-unknown"
_HTTP_CLIENT = httpx.AsyncClient(timeout=10.0)


def _fastmcp_read_meta_dict() -> dict[str, Any] | None:
    """Return the raw ``_meta`` dict of the active FastMCP request, if any."""
    try:
        ctx = get_context()
    except (RuntimeError, LookupError):
        return None

    if ctx is None:
        return None

    rc = ctx.request_context
    if rc is None or rc.meta is None:
        return None
    meta = dict(rc.meta)
    return meta or None


def _pick_meta(meta: Mapping[str, Any], canonical_key: str) -> str | None:
    """Look up ``canonical_key`` in ``meta``, with optional flat-camelCase fallback.

    The canonical (namespaced) key is always consulted first. The flat
    camelCase alias from :data:`META_FLAT_ALIASES` is only tried when the
    ``enable_mcp_metadata_fallback_un_19145`` feature flag is enabled AND
    the canonical key is absent. Non-string values are ignored.
    """
    value = meta.get(canonical_key)
    if isinstance(value, str) and value:
        return value

    if feature_flags.enable_mcp_metadata_fallback_un_19145.is_enabled():
        flat_alias = META_FLAT_ALIASES.get(canonical_key)
        if flat_alias is not None:
            fallback = meta.get(flat_alias)
            if isinstance(fallback, str) and fallback:
                return fallback

    return None


def _auth_from_meta(meta: Mapping[str, Any]) -> AuthContext | None:
    """Build an :class:`AuthContext` from request ``_meta`` when possible."""
    uid = _pick_meta(meta, MetaKeys.USER_ID)
    cid = _pick_meta(meta, MetaKeys.COMPANY_ID)
    if uid and cid:
        _LOGGER.debug("Auth from _meta (user=%s)", uid)
        return AuthContext(user_id=SecretStr(uid), company_id=SecretStr(cid))
    return None


def _chat_from_meta(meta: Mapping[str, Any]) -> ChatContext | None:
    """Build a :class:`ChatContext` from request ``_meta``.

    Returns ``None`` when no ``chat-id`` is present; otherwise fills the
    mandatory ``assistant_id`` and other chat-message-scope fields from
    ``_meta``, falling back to the MCP sentinel when the host did not
    forward them.
    """
    chat_id = _pick_meta(meta, MetaKeys.CHAT_ID)
    if not chat_id:
        return None

    return ChatContext(
        chat_id=chat_id,
        assistant_id=_pick_meta(meta, MetaKeys.ASSISTANT_ID)
        or _MCP_CHAT_CONTEXT_SENTINEL,
        last_user_message_id=_pick_meta(meta, MetaKeys.USER_MESSAGE_ID),
        last_assistant_message_id=_pick_meta(meta, MetaKeys.LAST_ASSISTANT_MESSAGE_ID),
        last_user_message_text=_pick_meta(meta, MetaKeys.LAST_USER_MESSAGE_TEXT),
        parent_chat_id=_pick_meta(meta, MetaKeys.PARENT_CHAT_ID),
    )


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


@lru_cache(maxsize=1)
def _base_settings() -> UniqueSettings:
    return UniqueSettings.from_env_auto_with_sdk_init()


def get_request_meta() -> dict[str, Any] | None:
    """Standard injector for raw ``_meta`` access.

    Use via ``Depends(get_request_meta)`` instead of reaching into FastMCP internals.
    Centralising here means the meta source (FastMCP today, potentially multiple
    sources in the future) can evolve without touching tool code.
    """
    return _fastmcp_read_meta_dict()


def get_unique_settings() -> UniqueSettings:
    settings = _base_settings()

    meta = get_request_meta()

    if meta is not None:
        if chat_context := _chat_from_meta(meta):
            settings = settings.with_chat(chat_context)
        if auth_context := _auth_from_meta(meta):
            return settings.with_auth(auth_context)

    # When `_meta` carries chat keys but no auth keys, we may have applied
    # `with_chat` above and still need JWT/env auth here. `with_auth` keeps
    # the already-bound chat context (see `UniqueSettings.with_auth`).
    if auth_context := _fastmcp_access_token_to_auth_context():
        return settings.with_auth(auth_context)

    return settings


def get_unique_service_factory() -> UniqueServiceFactory:
    settings = get_unique_settings()
    return UniqueServiceFactory(settings=settings)
