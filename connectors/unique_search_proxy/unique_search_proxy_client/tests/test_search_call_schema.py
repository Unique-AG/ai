import pytest
from unique_search_proxy_core.search_engines.call_schema import (
    resolve_search_call_schema,
)


class TestResolveSearchCallSchema:
    @pytest.mark.ai
    def test_query_and_fetch_size_in_schema(self) -> None:
        descriptor = resolve_search_call_schema("google")
        assert descriptor.engine == "google"
        assert descriptor.mode == "standard"
        properties = descriptor.call_schema.get("properties", {})
        assert "query" in properties
        assert "fetchSize" not in properties
        assert "dateRestrict" not in properties

    @pytest.mark.ai
    def test_expose_without_value_accepted_and_llm_fields_required(self) -> None:
        descriptor = resolve_search_call_schema(
            "google",
            config={
                "engine": "google",
                "fetchSize": 10,
                "safe": "active",
                "gl": {"expose": True},
            },
        )
        call_schema = descriptor.call_schema
        assert set(call_schema["required"]) == {"query", "gl"}
        assert "default" not in call_schema["properties"]["gl"]
        assert "default" not in call_schema["properties"]["query"]

    @pytest.mark.ai
    def test_strict_false_allows_optional_llm_fields(self) -> None:
        descriptor = resolve_search_call_schema(
            "google",
            config={
                "engine": "google",
                "hl": {"expose": True},
            },
            strict=False,
        )
        call_schema = descriptor.call_schema
        assert "hl" in call_schema["properties"]
        assert "hl" not in call_schema.get("required", [])
        hl_prop = call_schema["properties"]["hl"]
        assert hl_prop.get("default") is None

    @pytest.mark.ai
    def test_strict_false_inherits_admin_default_on_exposed_field(self) -> None:
        descriptor = resolve_search_call_schema(
            "google",
            config={
                "engine": "google",
                "fetchSize": 10,
                "safe": "active",
                "gl": {"expose": True, "value": "ch"},
            },
            strict=False,
        )
        call_schema = descriptor.call_schema
        assert call_schema["properties"]["gl"]["default"] == "ch"

    @pytest.mark.ai
    def test_expose_fields_from_config_appear_in_schema(self) -> None:
        descriptor = resolve_search_call_schema(
            "google",
            config={
                "engine": "google",
                "gl": {"expose": True, "value": "ch"},
                "dateRestrict": {"expose": False, "value": "d7"},
            },
        )
        properties = descriptor.call_schema.get("properties", {})
        assert "query" in properties
        assert "fetchSize" not in properties
        assert "gl" in properties
        assert "dateRestrict" not in properties

    @pytest.mark.ai
    def test_post_call_schema_for_google(self) -> None:
        descriptor = resolve_search_call_schema(
            "google",
            config={
                "engine": "google",
                "gl": {"expose": True, "value": "ch"},
            },
        )
        assert descriptor.engine == "google"
        assert descriptor.mode == "standard"
        assert "query" in descriptor.call_schema["properties"]
        assert "fetchSize" not in descriptor.call_schema["properties"]
        assert "gl" in descriptor.call_schema["properties"]

    @pytest.mark.ai
    def test_brave_call_schema_defaults(self) -> None:
        descriptor = resolve_search_call_schema("brave")
        assert descriptor.engine == "brave"
        assert descriptor.mode == "standard"
        properties = descriptor.call_schema.get("properties", {})
        assert "query" in properties
        assert "fetchSize" not in properties
        assert "extraSnippets" not in properties
        assert "safesearch" not in properties

    @pytest.mark.ai
    def test_brave_exposed_fields_appear_in_call_schema(self) -> None:
        descriptor = resolve_search_call_schema(
            "brave",
            config={
                "engine": "brave",
                "country": {"expose": True, "value": "CH"},
                "freshness": {"expose": False, "value": "pw"},
            },
        )
        properties = descriptor.call_schema.get("properties", {})
        assert "query" in properties
        assert "country" in properties
        assert "freshness" not in properties

    @pytest.mark.ai
    def test_perplexity_call_schema_defaults(self) -> None:
        descriptor = resolve_search_call_schema("perplexity")
        assert descriptor.engine == "perplexity"
        assert descriptor.mode == "standard"
        properties = descriptor.call_schema.get("properties", {})
        assert "query" in properties
        assert "fetchSize" not in properties
        assert "searchContextSize" not in properties

    @pytest.mark.ai
    def test_perplexity_exposed_fields_appear_in_call_schema(self) -> None:
        descriptor = resolve_search_call_schema(
            "perplexity",
            config={
                "engine": "perplexity",
                "country": {"expose": True, "value": "US"},
                "searchRecencyFilter": {"expose": False, "value": "week"},
                "searchDomainFilter": {"expose": True, "value": ["example.com"]},
            },
        )
        properties = descriptor.call_schema.get("properties", {})
        assert "query" in properties
        assert "country" in properties
        assert "searchDomainFilter" in properties
        assert "searchRecencyFilter" not in properties

    @pytest.mark.ai
    def test_unknown_engine_raises(self) -> None:
        with pytest.raises(ValueError, match="No search_engine config registered"):
            resolve_search_call_schema("bing")

    @pytest.mark.ai
    def test_invalid_engine_id_raises_when_config_provided(self) -> None:
        with pytest.raises(ValueError, match="does not match engine"):
            resolve_search_call_schema(
                "brave",
                config={"engine": "google"},
            )
