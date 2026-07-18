"""Tests for per-request search identity resolution."""

from unittest.mock import AsyncMock, patch

import pytest
from mcp_search.auth import resolve_search_settings
from pydantic import SecretStr

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
async def test_resolve_delegates_to_shared_async_injector():
    expected = _settings(user="live-user", company="live-company")
    with patch(
        "mcp_search.auth.get_unique_settings_async",
        new=AsyncMock(return_value=expected),
    ) as mock_resolve:
        resolved = await resolve_search_settings(_settings())

    mock_resolve.assert_awaited_once_with()
    assert resolved is expected


@pytest.mark.asyncio
async def test_resolve_propagates_refuse_env_fallback():
    with (
        patch(
            "mcp_search.auth.get_unique_settings_async",
            new=AsyncMock(
                side_effect=ValueError("Refusing UNIQUE_AUTH_* env fallback")
            ),
        ),
        pytest.raises(ValueError, match="Refusing UNIQUE_AUTH_"),
    ):
        await resolve_search_settings(_settings())
