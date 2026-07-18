"""Tests for per-request search identity resolution."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp_search.auth import resolve_search_settings
from pydantic import SecretStr

from unique_mcp import MetaKeys
from unique_mcp.unique_injectors import UniqueUserInfo
from unique_toolkit.app.unique_settings import (
    AuthContext,
    UniqueApi,
    UniqueApp,
    UniqueSettings,
)


def _settings(user: str = "env-user", company: str = "env-company") -> UniqueSettings:
    return UniqueSettings(
        auth=AuthContext(
            user_id=SecretStr(user),
            company_id=SecretStr(company),
        ),
        app=UniqueApp(
            id=SecretStr("app"),
            key=SecretStr("key"),
            endpoint="ep",
            endpoint_secret=SecretStr("sec"),
        ),
        api=UniqueApi(base_url="https://api.example/"),
    )


@pytest.mark.asyncio
async def test_resolve_keeps_meta_auth():
    settings = _settings()
    with (
        patch(
            "mcp_search.auth.get_request_meta",
            return_value={
                MetaKeys.USER_ID: "meta-user",
                MetaKeys.COMPANY_ID: "meta-company",
            },
        ),
        patch("mcp_search.auth._get_access_token", return_value=MagicMock()),
        patch(
            "mcp_search.auth.get_unique_userinfo",
            new=AsyncMock(return_value=None),
        ) as mock_userinfo,
    ):
        # get_unique_settings already applied meta; we only verify we don't
        # override with userinfo. The returned object is the same settings.
        resolved = await resolve_search_settings(settings)

    assert resolved is settings
    mock_userinfo.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_keeps_jwt_auth_without_userinfo_call_side_effects():
    settings = _settings(user="jwt-user", company="jwt-company")
    token = MagicMock()
    token.claims = {
        "sub": "jwt-user",
        "urn:zitadel:iam:user:resourceowner:id": "jwt-company",
    }
    with (
        patch("mcp_search.auth.get_request_meta", return_value=None),
        patch("mcp_search.auth._get_access_token", return_value=token),
        patch(
            "mcp_search.auth.get_unique_userinfo",
            new=AsyncMock(return_value=None),
        ) as mock_userinfo,
    ):
        resolved = await resolve_search_settings(settings)

    assert resolved is settings
    mock_userinfo.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_uses_userinfo_when_jwt_incomplete():
    settings = _settings()
    token = MagicMock()
    token.claims = {"sub": "jwt-user-only"}  # missing company claim
    with (
        patch("mcp_search.auth.get_request_meta", return_value=None),
        patch("mcp_search.auth._get_access_token", return_value=token),
        patch(
            "mcp_search.auth.get_unique_userinfo",
            new=AsyncMock(
                return_value=UniqueUserInfo(
                    user_id="live-user",
                    company_id="live-company",
                    email="u@example.com",
                )
            ),
        ),
    ):
        resolved = await resolve_search_settings(settings)

    assert resolved.authcontext.get_confidential_user_id() == "live-user"
    assert resolved.authcontext.get_confidential_company_id() == "live-company"


@pytest.mark.asyncio
async def test_resolve_refuses_env_fallback_when_logged_in_but_unresolvable():
    settings = _settings()
    token = MagicMock()
    token.claims = {"sub": "jwt-user-only"}
    with (
        patch("mcp_search.auth.get_request_meta", return_value=None),
        patch("mcp_search.auth._get_access_token", return_value=token),
        patch(
            "mcp_search.auth.get_unique_userinfo",
            new=AsyncMock(return_value=None),
        ),
        pytest.raises(ValueError, match="Refusing to fall back to UNIQUE_AUTH_"),
    ):
        await resolve_search_settings(settings)


@pytest.mark.asyncio
async def test_resolve_allows_env_when_no_access_token():
    settings = _settings()
    with (
        patch("mcp_search.auth.get_request_meta", return_value=None),
        patch("mcp_search.auth._get_access_token", return_value=None),
    ):
        resolved = await resolve_search_settings(settings)
    assert resolved is settings
