"""Tests for UniqueContextProvider."""

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
from unique_mcp.provider.context_provider import (
    _CLAIM_COMPANY_ID,
    _CLAIM_USER_ID,
    UniqueContextProvider,
    UniqueUserInfo,
)

_MOD = "unique_mcp.provider.context_provider"


@pytest.fixture
def base_settings() -> UniqueSettings:
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
    return ZitadelOAuthProxySettings()


@pytest.fixture
def provider(
    base_settings: UniqueSettings,
    zitadel_settings: ZitadelOAuthProxySettings,
) -> UniqueContextProvider:
    return UniqueContextProvider(
        settings=base_settings,
        zitadel_settings=zitadel_settings,
    )


@pytest.fixture
def empty_env_settings() -> UniqueSettings:
    """Settings with no env auth so _resolve_auth can only use meta/JWT."""
    return UniqueSettings(
        auth=AuthContext(
            user_id=SecretStr(""),
            company_id=SecretStr(""),
        ),
        app=UniqueApp(),
        api=UniqueApi(),
    )


@pytest.fixture
def provider_no_env_auth(
    empty_env_settings: UniqueSettings,
    zitadel_settings: ZitadelOAuthProxySettings,
) -> UniqueContextProvider:
    return UniqueContextProvider(
        settings=empty_env_settings,
        zitadel_settings=zitadel_settings,
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


def _mock_http_client(response: MagicMock) -> AsyncMock:
    c = AsyncMock()
    c.get = AsyncMock(return_value=response)
    return c


@pytest.mark.ai
class TestResolveAuth:
    @pytest.mark.asyncio
    async def test_from_jwt_claims(self, provider: UniqueContextProvider):
        tok = _token({_CLAIM_USER_ID: "u1", _CLAIM_COMPANY_ID: "c1"})
        with patch(f"{_MOD}.get_access_token", return_value=tok):
            s = await provider.get_settings()
        assert s.authcontext.get_confidential_user_id() == "u1"
        assert s.authcontext.get_confidential_company_id() == "c1"

    @pytest.mark.asyncio
    async def test_fallback_to_userinfo(self, provider: UniqueContextProvider):
        """Incomplete JWT is completed via Zitadel userinfo (company from userinfo)."""
        tok = _token({_CLAIM_USER_ID: "u1"})
        resp = _userinfo_response({"sub": "u1", _CLAIM_COMPANY_ID: "c-info"})
        provider._http_client = _mock_http_client(resp)
        with patch(f"{_MOD}.get_access_token", return_value=tok):
            s = await provider.get_settings()
        assert s.authcontext.get_confidential_company_id() == "c-info"

    @pytest.mark.asyncio
    async def test_fallback_when_claims_empty(self, provider: UniqueContextProvider):
        """Empty JWT claims: user and company come from userinfo."""
        tok = _token({})
        resp = _userinfo_response({"sub": "u-info", _CLAIM_COMPANY_ID: "c-info"})
        provider._http_client = _mock_http_client(resp)
        with patch(f"{_MOD}.get_access_token", return_value=tok):
            s = await provider.get_settings()
        assert s.authcontext.get_confidential_user_id() == "u-info"

    @pytest.mark.asyncio
    async def test_raises_when_no_token(
        self, provider_no_env_auth: UniqueContextProvider
    ):
        """Without meta, JWT, or env auth, _resolve_auth raises."""
        with (
            patch(f"{_MOD}.get_access_token", return_value=None),
            pytest.raises(RuntimeError, match="Auth context must be provided"),
        ):
            await provider_no_env_auth.get_settings()

    @pytest.mark.asyncio
    async def test_raises_when_userinfo_incomplete(
        self, provider: UniqueContextProvider
    ):
        """
        Incomplete userinfo response fails auth resolution (ValueError propagates).
        """
        tok = _token({})
        resp = _userinfo_response({"sub": "u1"})
        provider._http_client = _mock_http_client(resp)
        with (
            patch(f"{_MOD}.get_access_token", return_value=tok),
            pytest.raises(ValueError, match="incomplete"),
        ):
            await provider.get_settings()

    @pytest.mark.asyncio
    async def test_reuses_app_api_refs(self, provider: UniqueContextProvider):
        tok = _token({_CLAIM_USER_ID: "u", _CLAIM_COMPANY_ID: "c"})
        with patch(f"{_MOD}.get_access_token", return_value=tok):
            s = await provider.get_settings()
        assert s.app is provider._settings.app
        assert s.api is provider._settings.api

    @pytest.mark.asyncio
    async def test_from_meta(self, provider: UniqueContextProvider):
        with (
            patch(
                f"{_MOD}.fastmcp_context_to_auth_context",
                return_value=AuthContext(
                    user_id=SecretStr("mu"),
                    company_id=SecretStr("mc"),
                ),
            ),
            patch(f"{_MOD}.get_access_token", return_value=None),
        ):
            s = await provider.get_settings()
        assert s.authcontext.get_confidential_user_id() == "mu"
        assert s.authcontext.get_confidential_company_id() == "mc"

    @pytest.mark.asyncio
    async def test_meta_wins_over_jwt(self, provider: UniqueContextProvider):
        """Meta IDs take priority even when a valid JWT is present."""
        tok = _token({_CLAIM_USER_ID: "jwt-u", _CLAIM_COMPANY_ID: "jwt-c"})
        with (
            patch(
                f"{_MOD}.fastmcp_context_to_auth_context",
                return_value=AuthContext(
                    user_id=SecretStr("meta-u"),
                    company_id=SecretStr("meta-c"),
                ),
            ),
            patch(f"{_MOD}.get_access_token", return_value=tok),
        ):
            s = await provider.get_settings()
        assert s.authcontext.get_confidential_user_id() == "meta-u"
        assert s.authcontext.get_confidential_company_id() == "meta-c"

    @pytest.mark.asyncio
    async def test_meta_partial_falls_through_to_jwt(
        self, provider: UniqueContextProvider
    ):
        """Meta with only user-id (no company-id) falls through to JWT."""
        tok = _token({_CLAIM_USER_ID: "jwt-u", _CLAIM_COMPANY_ID: "jwt-c"})
        with (
            patch(f"{_MOD}.fastmcp_context_to_auth_context", return_value=None),
            patch(f"{_MOD}.get_access_token", return_value=tok),
        ):
            s = await provider.get_settings()
        assert s.authcontext.get_confidential_user_id() == "jwt-u"
        assert s.authcontext.get_confidential_company_id() == "jwt-c"

    @pytest.mark.asyncio
    async def test_userinfo_timeout_propagates(self, provider: UniqueContextProvider):
        """httpx timeout in userinfo call propagates from _resolve_auth."""
        tok = _token({})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        provider._http_client = mock_client
        with (
            patch(f"{_MOD}.get_access_token", return_value=tok),
            pytest.raises(httpx.TimeoutException),
        ):
            await provider.get_settings()


@pytest.mark.ai
class TestGetContext:
    @pytest.mark.asyncio
    async def test_returns_context_with_auth(self, provider: UniqueContextProvider):
        tok = _token({_CLAIM_USER_ID: "u", _CLAIM_COMPANY_ID: "c"})
        with patch(f"{_MOD}.get_access_token", return_value=tok):
            ctx = await provider.get_context()
        assert ctx.auth.get_confidential_user_id() == "u"
        assert ctx.chat is None


@pytest.mark.ai
class TestGetUserinfo:
    @pytest.mark.asyncio
    async def test_returns_full_userinfo(self, provider: UniqueContextProvider):
        """
        get_userinfo maps Zitadel JSON to UniqueUserInfo (requires sub + company claim).
        """
        tok = _token({})
        data = {
            "sub": "u1",
            "email": "u@example.com",
            "name": "User",
            _CLAIM_COMPANY_ID: "c1",
        }
        resp = _userinfo_response(data)
        provider._http_client = _mock_http_client(resp)
        with patch(f"{_MOD}.get_access_token", return_value=tok):
            info = await provider.get_userinfo()
        assert info == UniqueUserInfo(
            user_id="u1",
            company_id="c1",
            email="u@example.com",
        )

    @pytest.mark.asyncio
    async def test_returns_none_when_no_token(self, provider: UniqueContextProvider):
        """Without a bearer token, get_userinfo returns None."""
        with patch(f"{_MOD}.get_access_token", return_value=None):
            assert await provider.get_userinfo() is None
