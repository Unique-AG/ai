import pytest
from unique_search_proxy_core.schema import SearchEngineRaw


class TestSearchEngineRaw:
    @pytest.mark.ai
    def test_model_dump_uses_camel_case(self) -> None:
        raw = SearchEngineRaw(pages=[])
        raw.append({"items": [], "pageIndex": 1, "requestedCount": 10})
        dumped = raw.model_dump(by_alias=True)
        assert dumped["pages"][0]["pageIndex"] == 1
        assert dumped["pages"][0]["requestedCount"] == 10
