"""Tests for UniqueContextProvider."""

from unittest.mock import MagicMock, patch

import pytest

# Import the module under test — it lives in mcp_search for now (prototype),
# will move to unique_mcp later. We patch at the module level where it's used.
from mcp_search.context_provider import (
    _CLAIM_COMPANY_ID,
    _CLAIM_USER_ID,
    UniqueContextProvider,
)
from pydantic import SecretStr

from unique_mcp.auth.zitadel.oauth_proxy import ZitadelOAuthProxySettings
from unique_toolkit.app.unique_settings import (
    AuthContext,
    UniqueApi,
    UniqueApp,
    UniqueSettings,
)


@pytest.fixture
def base_settings() -> UniqueSettings:
    """UniqueSettings with default env config (app/api) for testing."""
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


def _make_access_token(claims: dict) -> MagicMock:
    """Create a mock AccessToken with the given claims."""
    token = MagicMock()
    token.claims = claims
    token.token = "mock-bearer-token"
    return token


@pytest.mark.ai
class TestResolveAuthContext:
    def test__extracts_from_claims__when_both_present(
        self, provider: UniqueContextProvider
    ) -> None:
        """
        Purpose: Verify auth context is extracted directly from JWT claims.
        Why this matters: Avoids HTTP call to Zitadel userinfo when claims are available.
        """
        token = _make_access_token(
            {_CLAIM_USER_ID: "user-123", _CLAIM_COMPANY_ID: "company-456"}
        )

        with patch("mcp_search.context_provider.get_access_token", return_value=token):
            settings = provider.get_settings()

        assert settings.authcontext.get_confidential_user_id() == "user-123"
        assert settings.authcontext.get_confidential_company_id() == "company-456"

    def test__falls_back_to_userinfo__when_company_id_missing(
        self, provider: UniqueContextProvider
    ) -> None:
        """
        Purpose: Verify fallback to userinfo when company_id is not in JWT claims.
        Why this matters: Zitadel may not include org claim in JWT depending on config.
        """
        token = _make_access_token({_CLAIM_USER_ID: "user-123"})

        userinfo_response = MagicMock()
        userinfo_response.json.return_value = {
            "sub": "user-123",
            "urn:zitadel:iam:user:resourceowner:id": "company-from-userinfo",
        }
        userinfo_response.raise_for_status = MagicMock()

        with (
            patch("mcp_search.context_provider.get_access_token", return_value=token),
            patch(
                "mcp_search.context_provider.requests.get",
                return_value=userinfo_response,
            ) as mock_get,
        ):
            settings = provider.get_settings()

        assert settings.authcontext.get_confidential_user_id() == "user-123"
        assert (
            settings.authcontext.get_confidential_company_id()
            == "company-from-userinfo"
        )
        mock_get.assert_called_once()

    def test__falls_back_to_userinfo__when_claims_empty(
        self, provider: UniqueContextProvider
    ) -> None:
        """
        Purpose: Verify fallback fires when claims dict is empty.
        Why this matters: Handles edge case where token has no claims at all.
        """
        token = _make_access_token({})

        userinfo_response = MagicMock()
        userinfo_response.json.return_value = {
            "sub": "user-from-userinfo",
            "urn:zitadel:iam:user:resourceowner:id": "company-from-userinfo",
        }
        userinfo_response.raise_for_status = MagicMock()

        with (
            patch("mcp_search.context_provider.get_access_token", return_value=token),
            patch(
                "mcp_search.context_provider.requests.get",
                return_value=userinfo_response,
            ),
        ):
            settings = provider.get_settings()

        assert settings.authcontext.get_confidential_user_id() == "user-from-userinfo"
        assert (
            settings.authcontext.get_confidential_company_id()
            == "company-from-userinfo"
        )

    def test__raises__when_no_access_token(
        self, provider: UniqueContextProvider
    ) -> None:
        """
        Purpose: Verify RuntimeError when no access token is available.
        Why this matters: Clear error message when OAuth is not configured.
        """
        with (
            patch("mcp_search.context_provider.get_access_token", return_value=None),
            pytest.raises(RuntimeError, match="No access token available"),
        ):
            provider.get_settings()

    def test__raises__when_userinfo_missing_fields(
        self, provider: UniqueContextProvider
    ) -> None:
        """
        Purpose: Verify ValueError when userinfo response is incomplete.
        Why this matters: Ensures clear error when Zitadel scope is misconfigured.
        """
        token = _make_access_token({})

        userinfo_response = MagicMock()
        userinfo_response.json.return_value = {"sub": "user-123"}
        userinfo_response.raise_for_status = MagicMock()

        with (
            patch("mcp_search.context_provider.get_access_token", return_value=token),
            patch(
                "mcp_search.context_provider.requests.get",
                return_value=userinfo_response,
            ),
            pytest.raises(ValueError, match="missing required fields"),
        ):
            provider.get_settings()

    def test__reuses_env_config__no_deepcopy(
        self, provider: UniqueContextProvider
    ) -> None:
        """
        Purpose: Verify that env config (app, api) is shared, not copied.
        Why this matters: Ensures no unnecessary deepcopy overhead per request.
        """
        token = _make_access_token(
            {_CLAIM_USER_ID: "user-1", _CLAIM_COMPANY_ID: "company-1"}
        )

        with patch("mcp_search.context_provider.get_access_token", return_value=token):
            settings = provider.get_settings()

        assert settings.app is provider._settings.app
        assert settings.api is provider._settings.api


@pytest.mark.ai
class TestGetContext:
    def test__returns_unique_context__with_auth(
        self, provider: UniqueContextProvider
    ) -> None:
        """
        Purpose: Verify get_context returns a UniqueContext with auth set.
        """
        token = _make_access_token(
            {_CLAIM_USER_ID: "user-ctx", _CLAIM_COMPANY_ID: "company-ctx"}
        )

        with patch("mcp_search.context_provider.get_access_token", return_value=token):
            context = provider.get_context()

        assert context.auth.get_confidential_user_id() == "user-ctx"
        assert context.auth.get_confidential_company_id() == "company-ctx"
        assert context.chat is None

    def test__chat_is_none__by_default(self, provider: UniqueContextProvider) -> None:
        """
        Purpose: Verify chat context is None when not provided (placeholder behavior).
        """
        token = _make_access_token({_CLAIM_USER_ID: "u", _CLAIM_COMPANY_ID: "c"})

        with patch("mcp_search.context_provider.get_access_token", return_value=token):
            settings = provider.get_settings()

        assert settings.context.chat is None
