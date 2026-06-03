import pytest

from unique_search_proxy.web.core.schema import SearchEngineRaw
from unique_search_proxy.web.core.search_engines.pagination import (
    PageRequest,
    iter_page_requests,
)


class TestIterPageRequests:
    @pytest.mark.ai
    def test_single_page_when_fetch_size_below_max(self) -> None:
        pages = list(iter_page_requests(5, max_page_size=10))
        assert pages == [PageRequest(page_index=1, offset=1, count=5)]

    @pytest.mark.ai
    def test_multiple_pages(self) -> None:
        pages = list(iter_page_requests(15, max_page_size=10))
        assert pages == [
            PageRequest(page_index=1, offset=1, count=10),
            PageRequest(page_index=2, offset=11, count=5),
        ]


class TestSearchEngineRaw:
    @pytest.mark.ai
    def test_model_dump_uses_camel_case(self) -> None:
        raw = SearchEngineRaw(pages=[])
        raw.append({"items": [], "pageIndex": 1, "requestedCount": 10})
        dumped = raw.model_dump(by_alias=True)
        assert dumped["pages"][0]["pageIndex"] == 1
        assert dumped["pages"][0]["requestedCount"] == 10
