import pytest
from pydantic import ValidationError

from unique_search_proxy.web.api.v1.schema import SearchRequest
from unique_search_proxy.web.core.search_engines import (
    SearchEngineType,
    parse_search_engine_config,
)
from unique_search_proxy.web.core.search_engines.google.schema import GoogleConfig


class TestSearchEngineConfigUnion:
    @pytest.mark.ai
    def test_google_config_accepts_engine_specific_fields(self) -> None:
        config = parse_search_engine_config(
            {
                "engine": "google",
                "fetchSize": 15,
                "dateRestrict": "d7",
            },
        )
        assert isinstance(config, GoogleConfig)
        assert config.engine == SearchEngineType.GOOGLE
        assert config.fetch_size == 15
        assert config.date_restrict == "d7"

    @pytest.mark.ai
    def test_search_request_parses_discriminated_config(self) -> None:
        req = SearchRequest.model_validate(
            {
                "config": {"engine": "google", "fetchSize": 8},
                "call": {"query": "hello"},
            },
        )
        assert isinstance(req.config, GoogleConfig)
        assert req.config.fetch_size == 8
        assert req.call["query"] == "hello"

    @pytest.mark.ai
    def test_unknown_engine_rejected_by_union(self) -> None:
        with pytest.raises(ValidationError):
            parse_search_engine_config({"engine": "bing"})

    @pytest.mark.ai
    def test_registered_engine_type_enum(self) -> None:
        assert SearchEngineType.GOOGLE.value == "google"
        assert SearchEngineType.GOOGLE in SearchEngineType
