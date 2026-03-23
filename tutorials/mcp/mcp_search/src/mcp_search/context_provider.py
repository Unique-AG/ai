from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests
from fastmcp.server.dependencies import get_access_token
from pydantic import SecretStr

from unique_mcp.auth.zitadel.oauth_proxy import ZitadelOAuthProxySettings
from unique_toolkit.app.unique_settings import (
    AuthContext,
    ChatContext,
    UniqueContext,
    UniqueSettings,
)

if TYPE_CHECKING:
    from unique_toolkit.app.unique_settings import ChatContextProtocol

logger = logging.getLogger(__name__)

# Zitadel claim keys
_CLAIM_USER_ID = "sub"
_CLAIM_COMPANY_ID = "urn:zitadel:iam:user:resourceowner:id"


class UniqueContextProvider:
    """Resolves per-request UniqueSettings from FastMCP's AccessToken.

    Initialized once at startup with UniqueSettings (same pattern as
    UniqueServiceFactory). Each tutorial/server configures UniqueSettings
    differently — the provider reuses the env config (app, api) and swaps
    auth per request based on the OAuth token.

    Called per tool invocation to produce fresh UniqueSettings with the
    current user's auth context resolved from Zitadel.

    Example::

        # Startup
        settings = UniqueSettings.from_env_auto_with_sdk_init()
        provider = UniqueContextProvider(
            settings=settings,
            zitadel_settings=ZitadelOAuthProxySettings(),
        )

        # Per tool call
        request_settings = provider.get_settings()
        service = KnowledgeBaseService.from_settings(request_settings)
    """

    def __init__(
        self,
        *,
        settings: UniqueSettings,
        zitadel_settings: ZitadelOAuthProxySettings | None = None,
    ) -> None:
        self._settings = settings
        self._zitadel_settings = zitadel_settings or ZitadelOAuthProxySettings()

    def get_settings(self, chat: ChatContextProtocol | None = None) -> UniqueSettings:
        """Build per-request UniqueSettings (env from init + auth from token + optional chat)."""
        auth = self._resolve_auth_context()
        chat = chat or self._resolve_chat_context()
        return UniqueSettings(
            auth=auth,
            app=self._settings.app,
            api=self._settings.api,
            chat=chat,
        )

    def get_context(self, chat: ChatContextProtocol | None = None) -> UniqueContext:
        """Build per-request UniqueContext (auth + optional chat)."""
        auth = self._resolve_auth_context()
        chat = chat or self._resolve_chat_context()
        return UniqueContext(auth=auth, chat=chat)

    def _resolve_chat_context(self) -> ChatContext | None:
        """Resolve ChatContext from HTTP headers or _meta.

        Future: read X-Chat-Id, X-Assistant-Id from get_http_headers(),
        or from _meta in the MCP tool call params.
        Currently returns None (auth-only context).
        """
        return None

    def _resolve_auth_context(self) -> AuthContext:
        """Extract user identity from the current request's access token.

        Strategy: try JWT claims first (zero HTTP calls), fall back to
        Zitadel userinfo endpoint if claims don't contain company_id.
        """
        token = get_access_token()
        if token is None:
            raise RuntimeError(
                "No access token available in the current request context. "
                "Ensure the MCP server has OAuth authentication configured."
            )

        claims = token.claims
        user_id = claims.get(_CLAIM_USER_ID)
        company_id = claims.get(_CLAIM_COMPANY_ID)

        if user_id and company_id:
            logger.debug("Resolved auth context from JWT claims (user=%s)", user_id)
            return AuthContext(
                user_id=SecretStr(user_id),
                company_id=SecretStr(company_id),
            )

        logger.debug(
            "JWT claims missing user_id=%s or company_id=%s, falling back to userinfo",
            bool(user_id),
            bool(company_id),
        )
        return self._resolve_from_userinfo(token.token)

    def _resolve_from_userinfo(self, bearer_token: str) -> AuthContext:
        """Fallback: call Zitadel userinfo endpoint to get user identity."""
        response = requests.get(
            self._zitadel_settings.userinfo_endpoint,
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
        response.raise_for_status()
        info = response.json()

        user_id = info.get("sub")
        company_id = info.get("urn:zitadel:iam:user:resourceowner:id")

        if not user_id or not company_id:
            raise ValueError(
                f"Zitadel userinfo response missing required fields. "
                f"Got sub={user_id!r}, company_id={company_id!r}. "
                f"Ensure the 'urn:zitadel:iam:user:resourceowner' scope is requested."
            )

        logger.debug("Resolved auth context from Zitadel userinfo (user=%s)", user_id)
        return AuthContext(
            user_id=SecretStr(user_id),
            company_id=SecretStr(company_id),
        )
