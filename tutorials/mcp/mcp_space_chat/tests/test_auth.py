"""Tests for per-request identity resolution and SDK wiring."""

from unittest.mock import AsyncMock, patch

import pytest
from mcp_space_chat.auth import resolve_chat_settings, sdk_identity
from pydantic import SecretStr

from unique_toolkit.app.unique_settings import (
    AuthContext,
    UniqueApi,
    UniqueApp,
    UniqueSettings,
)

pytestmark = pytest.mark.ai


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
        "mcp_space_chat.auth.get_unique_settings_async",
        new=AsyncMock(return_value=expected),
    ) as mock_resolve:
        resolved = await resolve_chat_settings(_settings())

    mock_resolve.assert_awaited_once_with()
    assert resolved is expected


@pytest.mark.asyncio
async def test_resolve_propagates_refuse_env_fallback():
    with (
        patch(
            "mcp_space_chat.auth.get_unique_settings_async",
            new=AsyncMock(
                side_effect=ValueError("Refusing UNIQUE_AUTH_* env fallback")
            ),
        ),
        pytest.raises(ValueError, match="Refusing UNIQUE_AUTH_"),
    ):
        await resolve_chat_settings(_settings())


def test_sdk_identity_configures_sdk_and_returns_pair():
    import unique_sdk

    settings = _settings(user="user_1", company="company_1")
    user_id, company_id = sdk_identity(settings)

    assert (user_id, company_id) == ("user_1", "company_1")
    assert unique_sdk.api_key == "key"
    assert unique_sdk.app_id == "app"
