"""Request-model derivation from deployment config classes."""

import pytest
from pydantic import ValidationError

from unique_search_proxy_core.agent_engines.bing.schema import (
    BingAgentConfig,
    BingAgentSearchRequest,
)
from unique_search_proxy_core.crawlers.basic.schema import (
    BasicConfig,
    BasicCrawlRequest,
)
from unique_search_proxy_core.search_engines.google.schema import (
    GoogleConfig,
    GoogleSearchRequest,
)


class TestSearchRequestModel:
    @pytest.mark.ai
    def test_cached_class_identity(self) -> None:
        assert GoogleConfig.request_model() is GoogleConfig.request_model()
        assert GoogleConfig.request_model() is GoogleSearchRequest

    @pytest.mark.ai
    def test_model_name_derived_from_config(self) -> None:
        assert GoogleSearchRequest.__name__ == "GoogleSearchRequest"

    @pytest.mark.ai
    def test_exposable_param_unwraps_to_optional_plain_type(self) -> None:
        field = GoogleSearchRequest.model_fields["date_restrict"]
        assert not field.is_required()
        assert field.default is None
        request = GoogleSearchRequest.model_validate(
            {"engine": "google", "query": "x", "dateRestrict": "d7"},
        )
        assert request.date_restrict == "d7"

    @pytest.mark.ai
    def test_query_is_required_and_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            GoogleSearchRequest.model_validate({"engine": "google"})
        with pytest.raises(ValidationError):
            GoogleSearchRequest.model_validate({"engine": "google", "query": ""})

    @pytest.mark.ai
    def test_camel_case_aliases_accepted(self) -> None:
        request = GoogleSearchRequest.model_validate(
            {"engine": "google", "query": "x", "fetchSize": 7},
        )
        assert request.fetch_size == 7

    @pytest.mark.ai
    def test_plain_field_constraints_preserved(self) -> None:
        with pytest.raises(ValidationError):
            GoogleSearchRequest.model_validate(
                {"engine": "google", "query": "x", "fetchSize": 0},
            )


class TestAgentRequestModel:
    @pytest.mark.ai
    def test_output_schema_excluded(self) -> None:
        assert "output_schema" not in BingAgentSearchRequest.model_fields
        assert BingAgentConfig.request_model() is BingAgentSearchRequest

    @pytest.mark.ai
    def test_model_name(self) -> None:
        assert BingAgentSearchRequest.__name__ == "BingAgentSearchRequest"


class TestCrawlRequestModel:
    @pytest.mark.ai
    def test_urls_required(self) -> None:
        with pytest.raises(ValidationError):
            BasicCrawlRequest.model_validate({"crawler": "Basic"})
        with pytest.raises(ValidationError):
            BasicCrawlRequest.model_validate({"crawler": "Basic", "urls": []})

    @pytest.mark.ai
    def test_model_name_and_identity(self) -> None:
        assert BasicCrawlRequest.__name__ == "BasicCrawlRequest"
        assert BasicConfig.request_model() is BasicCrawlRequest
