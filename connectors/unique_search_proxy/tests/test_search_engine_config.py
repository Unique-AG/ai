import pytest
from pydantic import ValidationError

from unique_search_proxy.web.api.v1.schema import SearchRequest
from unique_search_proxy.web.core.search_engines import (
    SearchEngineType,
    parse_search_engine_config,
)
from unique_search_proxy.web.core.search_engines.google.schema import (
    GoogleConfig,
    GoogleSearchRequest,
)


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
        assert config.date_restrict is not None
        assert config.date_restrict.value == "d7"

    @pytest.mark.ai
    def test_search_request_parses_flat_google_payload(self) -> None:
        req = SearchRequest.model_validate(
            {
                "engine": "google",
                "query": "hello",
                "fetchSize": 8,
                "timeout": 30,
            },
        )
        assert req.engine == SearchEngineType.GOOGLE
        assert isinstance(req, GoogleSearchRequest)
        assert req.fetch_size == 8
        assert req.query == "hello"

    @pytest.mark.ai
    def test_unknown_engine_rejected_by_union(self) -> None:
        with pytest.raises(ValidationError):
            parse_search_engine_config({"engine": "bing"})

    @pytest.mark.ai
    def test_registered_engine_type_enum(self) -> None:
        assert SearchEngineType.GOOGLE.value == "google"
        assert SearchEngineType.GOOGLE in SearchEngineType
