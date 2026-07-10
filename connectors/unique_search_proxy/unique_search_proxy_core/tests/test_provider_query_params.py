"""Config.provider_query_params: merged request -> upstream provider dict."""

import pytest

from unique_search_proxy_core.search_engines.brave.schema import BraveConfig
from unique_search_proxy_core.search_engines.google.schema import (
    ExposableStrOrNone,
    GoogleConfig,
)


class TestProviderQueryParams:
    @pytest.mark.ai
    def test_base_exclusions_never_forwarded(self) -> None:
        request = GoogleConfig().merge({}, query="hello")
        params = GoogleConfig.provider_query_params(request)
        for excluded in ("engine", "query", "fetchSize", "timeout"):
            assert excluded not in params

    @pytest.mark.ai
    def test_google_excludes_search_engine_id(self) -> None:
        config = GoogleConfig(search_engine_id="cx-internal")
        request = config.merge({}, query="hello")
        params = GoogleConfig.provider_query_params(request)
        assert "searchEngineId" not in params
        assert "search_engine_id" not in params

    @pytest.mark.ai
    def test_none_values_dropped(self) -> None:
        request = GoogleConfig().merge({}, query="hello")
        params = GoogleConfig.provider_query_params(request)
        assert None not in params.values()

    @pytest.mark.ai
    def test_by_alias_toggle(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=False, value="d7"),
        )
        request = config.merge({}, query="hello")
        assert "dateRestrict" in GoogleConfig.provider_query_params(request)
        assert "date_restrict" in GoogleConfig.provider_query_params(
            request,
            by_alias=False,
        )

    @pytest.mark.ai
    def test_brave_does_not_inherit_google_exclusion(self) -> None:
        request = BraveConfig().merge({}, query="hello")
        params = BraveConfig.provider_query_params(request, by_alias=False)
        assert "safesearch" in params
        assert "engine" not in params
