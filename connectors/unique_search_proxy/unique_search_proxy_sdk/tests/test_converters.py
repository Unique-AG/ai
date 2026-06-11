import pytest
from unique_search_proxy_core.search_engines.config_types import parse_search_request

from unique_search_proxy_sdk.converters import SdkSearchBody, to_sdk_search_request


class TestToSdkSearchRequest:
    @pytest.mark.ai
    def test_google(self) -> None:
        request = parse_search_request(
            {"engine": "google", "query": "hello", "fetchSize": 5},
        )
        sdk_body = to_sdk_search_request(request)
        assert isinstance(sdk_body, SdkSearchBody)
        assert sdk_body.to_dict() == {
            "query": "hello",
            "engine": "google",
            "fetchSize": 5,
            "timeout": 30,
            "safe": "active",
        }

    @pytest.mark.ai
    def test_brave(self) -> None:
        request = parse_search_request(
            {"engine": "brave", "query": "hello", "fetchSize": 3},
        )
        sdk_body = to_sdk_search_request(request)
        assert isinstance(sdk_body, SdkSearchBody)
        body = sdk_body.to_dict()
        assert body["query"] == "hello"
        assert body["engine"] == "brave"
        assert body["fetchSize"] == 3

    @pytest.mark.ai
    def test_perplexity(self) -> None:
        request = parse_search_request(
            {
                "engine": "perplexity",
                "query": "hello",
                "fetchSize": 3,
                "searchRecencyFilter": "day",
            },
        )
        sdk_body = to_sdk_search_request(request)
        assert isinstance(sdk_body, SdkSearchBody)
        body = sdk_body.to_dict()
        assert body["query"] == "hello"
        assert body["engine"] == "perplexity"
        assert body["fetchSize"] == 3
        assert body["searchRecencyFilter"] == "day"
