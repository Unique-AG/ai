import pytest
from unique_search_proxy_core.errors import EngineNotConfiguredError

from unique_search_proxy_client.web.settings.providers.base import NOT_PROVIDED
from unique_search_proxy_client.web.settings.providers.brave import (
    _BraveCredentials,
    _get_brave_search_credentials,
)
from unique_search_proxy_client.web.settings.providers.google import (
    _get_google_search_credentials,
    _GoogleCredentials,
)

_DEFAULT_BRAVE_API_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

BRAVE_SEARCH_API_KEY_ENV = "BRAVE_SEARCH_API_KEY"
GOOGLE_SEARCH_API_KEY_ENV = "GOOGLE_SEARCH_API_KEY"
GOOGLE_SEARCH_ENGINE_ID_ENV = "GOOGLE_SEARCH_ENGINE_ID"


def _unconfigured_google_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", NOT_PROVIDED)
    monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", NOT_PROVIDED)


def _unconfigured_brave_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", NOT_PROVIDED)


class TestBraveCredentials:
    @pytest.mark.ai
    def test_defaults_use_not_provided_sentinel(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _unconfigured_brave_env(monkeypatch)
        credentials = _get_brave_search_credentials()
        assert credentials.api_key == NOT_PROVIDED

    @pytest.mark.ai
    def test_check_credentials_lists_env_vars(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _unconfigured_brave_env(monkeypatch)
        credentials = _get_brave_search_credentials()
        with pytest.raises(EngineNotConfiguredError) as exc_info:
            credentials.check_credentials()
        assert exc_info.value.missing_env_vars == [BRAVE_SEARCH_API_KEY_ENV]
        assert BRAVE_SEARCH_API_KEY_ENV in exc_info.value.message

    @pytest.mark.ai
    def test_default_endpoint_is_configured_url(self) -> None:
        assert (
            _BraveCredentials.model_fields["api_endpoint"].default
            == _DEFAULT_BRAVE_API_ENDPOINT
        )

    @pytest.mark.ai
    def test_load_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
        monkeypatch.setenv(
            "BRAVE_SEARCH_API_ENDPOINT",
            "https://api.search.brave.com/res/v1/web/search",
        )
        credentials = _get_brave_search_credentials()
        assert credentials.api_key == "test-key"


class TestGoogleCredentials:
    @pytest.mark.ai
    def test_defaults_use_not_provided_for_secrets(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _unconfigured_google_env(monkeypatch)
        credentials = _get_google_search_credentials()
        assert credentials.api_key == NOT_PROVIDED
        assert credentials.engine_id == NOT_PROVIDED

    @pytest.mark.ai
    def test_check_credentials_lists_all_missing_env_vars(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _unconfigured_google_env(monkeypatch)
        credentials = _get_google_search_credentials()
        with pytest.raises(EngineNotConfiguredError) as exc_info:
            credentials.check_credentials()
        assert GOOGLE_SEARCH_API_KEY_ENV in exc_info.value.missing_env_vars
        assert GOOGLE_SEARCH_ENGINE_ID_ENV in exc_info.value.missing_env_vars

    @pytest.mark.ai
    def test_load_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "key")
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "cx")
        monkeypatch.setenv(
            "GOOGLE_SEARCH_API_ENDPOINT",
            "https://www.googleapis.com/customsearch/v1",
        )
        credentials = _get_google_search_credentials()
        assert isinstance(credentials, _GoogleCredentials)
        assert credentials.api_key == "key"
        assert credentials.engine_id == "cx"
