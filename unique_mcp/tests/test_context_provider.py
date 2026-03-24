"""Tests for UniqueContextProvider."""

from unittest.mock import AsyncMock, MagicMock, patch

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


def _mock_httpx(response: MagicMock) -> AsyncMock:
    c = AsyncMock()
    c.__aenter__ = AsyncMock(return_value=c)
    c.__aexit__ = AsyncMock(return_value=None)
    c.get = AsyncMock(return_value=response)
    return c


@pytest.mark.ai
class TestResolveAuth:
    @pytest.mark.asyncio
    async def test_from_jwt_claims(self, provider):
        tok = _token({_CLAIM_USER_ID: "u1", _CLAIM_COMPANY_ID: "c1"})
        with patch(f"{_MOD}.get_access_token", return_value=tok):
            s = await provider.get_settings()
        assert s.authcontext.get_confidential_user_id() == "u1"
        assert s.authcontext.get_confidential_company_id() == "c1"

    @pytest.mark.asyncio
    async def test_fallback_to_userinfo(self, provider):
        tok = _token({_CLAIM_USER_ID: "u1"})
        resp = _userinfo_response({"sub": "u1", _CLAIM_COMPANY_ID: "c-info"})
        with (
            patch(f"{_MOD}.get_access_token", return_value=tok),
            patch(f"{_MOD}.httpx.AsyncClient", return_value=_mock_httpx(resp)),
        ):
            s = await provider.get_settings()
        assert s.authcontext.get_confidential_company_id() == "c-info"

    @pytest.mark.asyncio
    async def test_fallback_when_claims_empty(self, provider):
        tok = _token({})
        resp = _userinfo_response({"sub": "u-info", _CLAIM_COMPANY_ID: "c-info"})
        with (
            patch(f"{_MOD}.get_access_token", return_value=tok),
            patch(f"{_MOD}.httpx.AsyncClient", return_value=_mock_httpx(resp)),
        ):
            s = await provider.get_settings()
        assert s.authcontext.get_confidential_user_id() == "u-info"

    @pytest.mark.asyncio
    async def test_raises_when_no_token(self, provider):
        with (
            patch(f"{_MOD}.get_access_token", return_value=None),
            pytest.raises(RuntimeError, match="No access token"),
        ):
            await provider.get_settings()

    @pytest.mark.asyncio
    async def test_raises_when_userinfo_incomplete(self, provider):
        tok = _token({})
        resp = _userinfo_response({"sub": "u1"})
        with (
            patch(f"{_MOD}.get_access_token", return_value=tok),
            patch(f"{_MOD}.httpx.AsyncClient", return_value=_mock_httpx(resp)),
            pytest.raises(ValueError, match="incomplete"),
        ):
            await provider.get_settings()

    @pytest.mark.asyncio
    async def test_reuses_app_api_refs(self, provider):
        tok = _token({_CLAIM_USER_ID: "u", _CLAIM_COMPANY_ID: "c"})
        with patch(f"{_MOD}.get_access_token", return_value=tok):
            s = await provider.get_settings()
        assert s.app is provider._settings.app
        assert s.api is provider._settings.api

    @pytest.mark.asyncio
    async def test_from_meta(self, provider):
        with (
            patch(
                f"{_MOD}._read_meta",
                return_value={
                    "unique.app/user-id": "mu",
                    "unique.app/company-id": "mc",
                },
            ),
            patch(f"{_MOD}.get_access_token", return_value=None),
        ):
            s = await provider.get_settings()
        assert s.authcontext.get_confidential_user_id() == "mu"
        assert s.authcontext.get_confidential_company_id() == "mc"


@pytest.mark.ai
class TestGetContext:
    @pytest.mark.asyncio
    async def test_returns_context_with_auth(self, provider):
        tok = _token({_CLAIM_USER_ID: "u", _CLAIM_COMPANY_ID: "c"})
        with patch(f"{_MOD}.get_access_token", return_value=tok):
            ctx = await provider.get_context()
        assert ctx.auth.get_confidential_user_id() == "u"
        assert ctx.chat is None
