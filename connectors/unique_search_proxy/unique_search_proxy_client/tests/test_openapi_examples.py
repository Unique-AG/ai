from __future__ import annotations

import pytest
from unique_search_proxy_core.crawlers.config_types import parse_crawl_request
from unique_search_proxy_core.search_engines.config_types import parse_search_request

from unique_search_proxy_client.web.api.v1.openapi_examples import (
    CRAWL_OPENAPI_EXAMPLES,
    SEARCH_OPENAPI_EXAMPLES,
)
from unique_search_proxy_client.web.presets import (
    ALL_PRESETS,
    CRAWL_PRESETS,
    SEARCH_PRESETS,
    get_preset,
)


class TestPresetCatalog:
    @pytest.mark.ai
    def test_preset_ids_are_unique(self) -> None:
        ids = [preset.id for preset in ALL_PRESETS]
        assert len(ids) == len(set(ids))

    @pytest.mark.ai
    def test_openapi_example_keys_match_preset_ids(self) -> None:
        search_ids = {preset.id for preset in ALL_PRESETS if preset.kind == "search"}
        crawl_ids = {preset.id for preset in ALL_PRESETS if preset.kind == "crawl"}
        assert set(SEARCH_OPENAPI_EXAMPLES) == search_ids
        assert set(CRAWL_OPENAPI_EXAMPLES) == crawl_ids

    @pytest.mark.ai
    def test_get_preset_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown preset"):
            get_preset("does_not_exist")


def _example_value(example: object) -> object:
    if isinstance(example, dict):
        return example["value"]
    return example.value  # type: ignore[union-attr, no-any-return]


class TestSearchOpenApiExamples:
    @pytest.mark.ai
    @pytest.mark.parametrize("preset", SEARCH_PRESETS, ids=lambda p: p.id)
    def test_search_preset_parses(self, preset: object) -> None:
        from unique_search_proxy_client.web.presets.types import PresetDefinition

        assert isinstance(preset, PresetDefinition)
        payload = preset.build_payload()
        parsed = parse_search_request(payload)
        assert getattr(parsed, "engine", None) is not None
        assert getattr(parsed, "query", None)

    @pytest.mark.ai
    @pytest.mark.parametrize("preset_id", [p.id for p in SEARCH_PRESETS])
    def test_openapi_search_example_matches_preset(self, preset_id: str) -> None:
        payload = get_preset(preset_id).build_payload()
        assert _example_value(SEARCH_OPENAPI_EXAMPLES[preset_id]) == payload


class TestCrawlOpenApiExamples:
    @pytest.mark.ai
    @pytest.mark.parametrize("preset", CRAWL_PRESETS, ids=lambda p: p.id)
    def test_crawl_preset_parses(self, preset: object) -> None:
        from unique_search_proxy_client.web.presets.types import PresetDefinition

        assert isinstance(preset, PresetDefinition)
        payload = preset.build_payload()
        parsed = parse_crawl_request(payload)
        assert getattr(parsed, "crawler", None) is not None
        assert len(getattr(parsed, "urls", [])) >= 1

    @pytest.mark.ai
    @pytest.mark.parametrize("preset_id", [p.id for p in CRAWL_PRESETS])
    def test_openapi_crawl_example_matches_preset(self, preset_id: str) -> None:
        payload = get_preset(preset_id).build_payload()
        assert _example_value(CRAWL_OPENAPI_EXAMPLES[preset_id]) == payload
