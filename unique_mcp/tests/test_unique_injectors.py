"""Tests for unique_mcp.unique_injectors (auth resolution helpers and getters)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr
from unique_toolkit.app.unique_settings import (
    AuthContext,
    UniqueApi,
    UniqueApp,
    UniqueSettings,
)

from unique_mcp.auth.zitadel.oauth_proxy import ZitadelOAuthProxySettings
from unique_mcp.meta_keys import MetaKeys
from unique_mcp.unique_injectors import (
    _CLAIM_COMPANY_ID,
    _CLAIM_USER_ID,
    UniqueUserInfo,
    _auth_from_meta,
    _base_settings,
    _chat_from_meta,
    _pick_meta,
    _userinfo_to_auth_context,
    get_request_meta,
    get_unique_service_factory,
    get_unique_settings,
    get_unique_userinfo,
    get_zitadel_settings,
)

_MOD = "unique_mcp.unique_injectors"


@pytest.fixture(autouse=True)
def _clear_base_settings_cache() -> None:
    """Prevent the lru_cache on _base_settings from leaking state between tests."""
    _base_settings.cache_clear()


# Fixed ZitadelOAuthProxySettings fields — tests do not depend on repo .env.
_ZITADEL_FIXTURE_BASE_URL = "http://zitadel.test.local"
_ZITADEL_FIXTURE_CLIENT_ID = "fixture_client_id"
_ZITADEL_FIXTURE_CLIENT_SECRET = "fixture_client_secret"


@pytest.fixture
def base_settings() -> UniqueSettings:
    """Base UniqueSettings returned by ``from_env_auto_with_sdk_init`` when patched."""
    return UniqueSettings(
        auth=AuthContext(
            user_id=SecretStr("dummy_user"),
            company_id=SecretStr("dummy_company"),
        ),
        app=UniqueApp(),
        api=UniqueApi(),
    )


@pytest.fixture
def zitadel_settings() -> ZitadelOAuthProxySettings:
    """Zitadel settings with fixed fields; ignores .env and shell env."""
    return ZitadelOAuthProxySettings(
        base_url=_ZITADEL_FIXTURE_BASE_URL,
        client_id=_ZITADEL_FIXTURE_CLIENT_ID,
        client_secret=_ZITADEL_FIXTURE_CLIENT_SECRET,
    )


def _token(claims: dict) -> MagicMock:
    t = MagicMock()
    t.claims = claims
    t.token = "mock-bearer"
    return t


def _userinfo_response(data: dict) -> MagicMock:
    r = MagicMock()
    r.json.return_value = data
    r.raise_for_status = MagicMock()
    return r


@pytest.mark.ai
def test_unique_injectors__claim_constants__match_zitadel_oidc() -> None:
    """
    Purpose: Document expected JWT / OIDC claim names used across the module.
    Why this matters: Tests guard against accidental renames that break token parsing.
    Setup summary: Assert module-level claim string constants.
    """
    assert _CLAIM_USER_ID == "sub"
    assert _CLAIM_COMPANY_ID == "urn:zitadel:iam:user:resourceowner:id"


@pytest.mark.ai
def test_get_zitadel_settings__returns_settings_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify get_zitadel_settings returns settings reflecting ZITADEL_* env.
    Why this matters: Production uses env; tests must pin expected values.
    Setup summary: monkeypatch ZITADEL_*, call get_zitadel_settings, assert fields.
    """
    monkeypatch.setenv("ZITADEL_BASE_URL", "http://env.test")
    monkeypatch.setenv("ZITADEL_CLIENT_ID", "from_env_client")
    monkeypatch.setenv("ZITADEL_CLIENT_SECRET", "from_env_secret")
    s = get_zitadel_settings()
    assert isinstance(s, ZitadelOAuthProxySettings)
    assert s.base_url == "http://env.test"
    assert s.client_id == "from_env_client"
    assert s.client_secret == "from_env_secret"


@pytest.mark.ai
def test_get_unique_settings__uses_meta_auth__when_present(
    base_settings: UniqueSettings,
) -> None:
    """
    Purpose: _meta-derived auth overrides env when FastMCP request carries both IDs.
    Why this matters: Internal callers can override identity via MCP _meta.
    Setup summary: Patch _base_settings and _read_meta_dict with auth keys.
    """
    with (
        patch(f"{_MOD}._base_settings", return_value=base_settings),
        patch(
            f"{_MOD}._read_meta_dict",
            return_value={
                MetaKeys.USER_ID: "mu",
                MetaKeys.COMPANY_ID: "mc",
            },
        ),
    ):
        s = get_unique_settings()
    assert s.authcontext.get_confidential_user_id() == "mu"
    assert s.authcontext.get_confidential_company_id() == "mc"


@pytest.mark.ai
def test_get_unique_settings__uses_jwt_claims__when_meta_absent(
    base_settings: UniqueSettings,
) -> None:
    """
    Purpose: Full JWT claims replace env auth when _meta does not supply identity.
    Why this matters: Normal OAuth tool calls use the swapped Zitadel token claims.
    Setup summary: Meta None, access-token helper returns AuthContext from JWT.
    """
    with (
        patch(f"{_MOD}._base_settings", return_value=base_settings),
        patch(f"{_MOD}._read_meta_dict", return_value=None),
        patch(
            f"{_MOD}._fastmcp_access_token_to_auth_context",
            return_value=AuthContext(
                user_id=SecretStr("u1"),
                company_id=SecretStr("c1"),
            ),
        ),
    ):
        s = get_unique_settings()
    assert s.authcontext.get_confidential_user_id() == "u1"
    assert s.authcontext.get_confidential_company_id() == "c1"


@pytest.mark.ai
def test_get_unique_settings__meta_wins_over_jwt(
    base_settings: UniqueSettings,
) -> None:
    """
    Purpose: Meta is checked before JWT; meta identity must win when both exist.
    Why this matters: Matches documented priority for trusted internal overrides.
    Setup summary: Both meta and JWT helpers return auth; expect meta values.
    """
    with (
        patch(f"{_MOD}._base_settings", return_value=base_settings),
        patch(
            f"{_MOD}._read_meta_dict",
            return_value={
                MetaKeys.USER_ID: "meta-u",
                MetaKeys.COMPANY_ID: "meta-c",
            },
        ),
        patch(
            f"{_MOD}._fastmcp_access_token_to_auth_context",
            return_value=AuthContext(
                user_id=SecretStr("jwt-u"),
                company_id=SecretStr("jwt-c"),
            ),
        ),
    ):
        s = get_unique_settings()
    assert s.authcontext.get_confidential_user_id() == "meta-u"
    assert s.authcontext.get_confidential_company_id() == "meta-c"


@pytest.mark.ai
def test_get_unique_settings__falls_back_to_env__when_no_meta_no_jwt(
    base_settings: UniqueSettings,
) -> None:
    """
    Purpose: With no request meta and no usable JWT claims, env-loaded auth is kept.
    Why this matters: Local/dev uses UNIQUE_AUTH_* from environment.
    Setup summary: Both resolution helpers return None; expect base_settings auth.
    """
    with (
        patch(f"{_MOD}._base_settings", return_value=base_settings),
        patch(f"{_MOD}._read_meta_dict", return_value=None),
        patch(f"{_MOD}._fastmcp_access_token_to_auth_context", return_value=None),
    ):
        s = get_unique_settings()
    assert s.authcontext.get_confidential_user_id() == "dummy_user"
    assert s.authcontext.get_confidential_company_id() == "dummy_company"


@pytest.mark.ai
def test_get_unique_settings__reuses_app_and_api_from_base(
    base_settings: UniqueSettings,
) -> None:
    """
    Purpose: with_auth preserves app/api references from the env base settings.
    Why this matters: Callers expect stable app/api when only auth changes.
    Setup summary: Patch JWT path; compare app/api identity to base_settings.
    """
    with (
        patch(f"{_MOD}._base_settings", return_value=base_settings),
        patch(f"{_MOD}._read_meta_dict", return_value=None),
        patch(
            f"{_MOD}._fastmcp_access_token_to_auth_context",
            return_value=AuthContext(
                user_id=SecretStr("u"),
                company_id=SecretStr("c"),
            ),
        ),
    ):
        s = get_unique_settings()
    assert s.app is base_settings.app
    assert s.api is base_settings.api


@pytest.mark.ai
def test_get_unique_settings__binds_chat_context_when_chat_id_present(
    base_settings: UniqueSettings,
) -> None:
    """Purpose: `_meta` carrying chat-id produces settings bound with chat context."""
    with (
        patch(f"{_MOD}._base_settings", return_value=base_settings),
        patch(
            f"{_MOD}._read_meta_dict",
            return_value={
                MetaKeys.USER_ID: "u",
                MetaKeys.COMPANY_ID: "c",
                MetaKeys.CHAT_ID: "chat-1",
                MetaKeys.USER_MESSAGE_ID: "um-1",
            },
        ),
    ):
        s = get_unique_settings()

    assert s.context.chat is not None
    assert s.context.chat.chat_id == "chat-1"


@pytest.mark.ai
def test_get_unique_settings__meta_chat_only_then_jwt_auth_preserves_chat(
    base_settings: UniqueSettings,
) -> None:
    """Chat from `_meta` without auth must survive a subsequent JWT `with_auth`."""
    with (
        patch(f"{_MOD}._base_settings", return_value=base_settings),
        patch(
            f"{_MOD}._read_meta_dict",
            return_value={MetaKeys.CHAT_ID: "chat-1"},
        ),
        patch(
            f"{_MOD}._fastmcp_access_token_to_auth_context",
            return_value=AuthContext(
                user_id=SecretStr("jwt-u"),
                company_id=SecretStr("jwt-c"),
            ),
        ),
    ):
        s = get_unique_settings()

    assert s.authcontext.get_confidential_user_id() == "jwt-u"
    assert s.context.chat is not None
    assert s.context.chat.chat_id == "chat-1"


@pytest.mark.ai
def test_get_request_meta__returns_raw_meta_dict() -> None:
    """`get_request_meta` is a thin public wrapper over `_read_meta_dict`."""
    raw = {"unique.app/search/content-ids": ["c1"]}
    with patch(f"{_MOD}._read_meta_dict", return_value=raw):
        assert get_request_meta() == raw


@pytest.mark.ai
def test_pick_meta__prefers_namespaced_over_flat() -> None:
    """Canonical keys always win over flat aliases."""
    meta = {MetaKeys.USER_ID: "new", "userId": "old"}
    assert _pick_meta(meta, MetaKeys.USER_ID) == "new"


@pytest.mark.ai
def test_pick_meta__falls_back_to_flat_when_ff_enabled() -> None:
    """Flat alias is honoured when the canonical key is absent."""
    meta = {"userId": "old"}
    with patch(
        f"{_MOD}.feature_flags.enable_mcp_metadata_fallback_un_19145.is_enabled",
        return_value=True,
    ):
        assert _pick_meta(meta, MetaKeys.USER_ID) == "old"


@pytest.mark.ai
def test_pick_meta__ignores_flat_when_ff_disabled() -> None:
    """Flat alias is ignored when the fallback feature flag is off."""
    meta = {"userId": "old"}
    with patch(
        f"{_MOD}.feature_flags.enable_mcp_metadata_fallback_un_19145.is_enabled",
        return_value=False,
    ):
        assert _pick_meta(meta, MetaKeys.USER_ID) is None


@pytest.mark.ai
def test_auth_from_meta__returns_none_when_only_one_id_present() -> None:
    """Partial auth (user but no company) must not yield an AuthContext."""
    assert _auth_from_meta({MetaKeys.USER_ID: "u"}) is None


@pytest.mark.ai
def test_chat_from_meta__returns_none_without_chat_id() -> None:
    assert _chat_from_meta({}) is None


@pytest.mark.ai
def test_chat_from_meta__fills_sentinel_for_missing_assistant_id() -> None:
    chat = _chat_from_meta({MetaKeys.CHAT_ID: "chat-1"})
    assert chat is not None
    assert chat.chat_id == "chat-1"
    assert chat.assistant_id == "mcp-unknown"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_get_unique_userinfo__returns_model__when_response_complete(
    zitadel_settings: ZitadelOAuthProxySettings,
) -> None:
    """
    Purpose: get_unique_userinfo maps Zitadel userinfo JSON to UniqueUserInfo.
    Why this matters: Email and IDs must match OIDC userinfo shape.
    Setup summary: Mock httpx client GET; patch token and zitadel settings.
    """
    tok = _token({})
    data = {
        "sub": "u1",
        "email": "u@example.com",
        _CLAIM_COMPANY_ID: "c1",
    }
    resp = _userinfo_response(data)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=resp)

    with (
        patch(f"{_MOD}.get_access_token", return_value=tok),
        patch(f"{_MOD}.get_zitadel_settings", return_value=zitadel_settings),
    ):
        info = await get_unique_userinfo(http_client=mock_client)

    mock_client.get.assert_called_once_with(
        zitadel_settings.userinfo_endpoint,
        headers={"Authorization": "Bearer mock-bearer"},
    )
    assert info == UniqueUserInfo(
        user_id="u1",
        company_id="c1",
        email="u@example.com",
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_get_unique_userinfo__returns_none__when_no_token() -> None:
    """
    Purpose: Without an access token, userinfo is not fetched.
    Why this matters: Avoids calling Zitadel without a bearer token.
    Setup summary: Patch get_access_token to None.
    """
    mock_client = AsyncMock()
    with patch(f"{_MOD}.get_access_token", return_value=None):
        assert await get_unique_userinfo(http_client=mock_client) is None
    mock_client.get.assert_not_called()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_get_unique_userinfo__raises__when_userinfo_incomplete(
    zitadel_settings: ZitadelOAuthProxySettings,
) -> None:
    """
    Purpose: Incomplete userinfo JSON raises ValueError (sub/company required).
    Why this matters: Prevents silent partial identity.
    Setup summary: Mock JSON missing company claim.
    """
    tok = _token({})
    resp = _userinfo_response({"sub": "u1"})
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=resp)

    with (
        patch(f"{_MOD}.get_access_token", return_value=tok),
        patch(f"{_MOD}.get_zitadel_settings", return_value=zitadel_settings),
        pytest.raises(ValueError, match="incomplete"),
    ):
        await get_unique_userinfo(http_client=mock_client)

    mock_client.get.assert_called_once_with(
        zitadel_settings.userinfo_endpoint,
        headers={"Authorization": "Bearer mock-bearer"},
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_get_unique_userinfo__timeout_propagates(
    zitadel_settings: ZitadelOAuthProxySettings,
) -> None:
    """
    Purpose: httpx timeout from userinfo GET propagates to callers.
    Why this matters: Callers can handle retries or surface transport errors.
    Setup summary: Mock client.get raises TimeoutException.
    """
    tok = _token({})
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

    with (
        patch(f"{_MOD}.get_access_token", return_value=tok),
        patch(f"{_MOD}.get_zitadel_settings", return_value=zitadel_settings),
        pytest.raises(httpx.TimeoutException),
    ):
        await get_unique_userinfo(http_client=mock_client)

    mock_client.get.assert_called_once_with(
        zitadel_settings.userinfo_endpoint,
        headers={"Authorization": "Bearer mock-bearer"},
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_userinfo_to_auth_context__returns_auth__when_userinfo_ok() -> None:
    """
    Purpose: _userinfo_to_auth_context converts UniqueUserInfo to AuthContext.
    Why this matters: Bridge for code that needs AuthContext from userinfo.
    Setup summary: Patch get_unique_userinfo to return a model.
    """
    with patch(
        f"{_MOD}.get_unique_userinfo",
        return_value=UniqueUserInfo(user_id="a", company_id="b", email=None),
    ):
        auth = await _userinfo_to_auth_context(http_client=AsyncMock())

    assert auth is not None
    assert auth.get_confidential_user_id() == "a"
    assert auth.get_confidential_company_id() == "b"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_userinfo_to_auth_context__returns_none__when_no_userinfo() -> None:
    """
    Purpose: When get_unique_userinfo returns None, auth context is None.
    Why this matters: Distinguishes missing token from failed fetch.
    Setup summary: Patch get_unique_userinfo to None.
    """
    with patch(f"{_MOD}.get_unique_userinfo", return_value=None):
        auth = await _userinfo_to_auth_context(http_client=AsyncMock())
    assert auth is None


@pytest.mark.ai
@patch(f"{_MOD}.get_unique_settings")
@patch(f"{_MOD}.UniqueServiceFactory")
def test_get_unique_service_factory__builds_factory_with_resolved_settings(
    mock_factory_cls: MagicMock,
    mock_get_settings: MagicMock,
    base_settings: UniqueSettings,
) -> None:
    """
    Purpose: get_unique_service_factory uses get_unique_settings for the factory.
    Why this matters: Services see the same auth resolution as get_unique_settings.
    Setup summary: Patch get_unique_settings and UniqueServiceFactory; assert call.
    """
    mock_get_settings.return_value = base_settings
    mock_instance = MagicMock()
    mock_factory_cls.return_value = mock_instance

    result = get_unique_service_factory()

    mock_get_settings.assert_called_once()
    mock_factory_cls.assert_called_once_with(settings=base_settings)
    assert result is mock_instance
