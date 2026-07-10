"""Tests for flat engine-exposed parameter injection (V1 and V3)."""

from typing import Any

import pytest
from pydantic import ValidationError
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_search_proxy_core.search_engines.google.schema import (
    ExposableStrOrNone,
    GoogleConfig,
)
from unique_toolkit.content import ContentChunk
from unique_toolkit.language_model import LanguageModelFunction

from unique_web_search.services.executors.base_executor import BaseWebSearchExecutor
from unique_web_search.services.executors.context import (
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
)
from unique_web_search.services.executors.v1.schema import WebSearchToolParameters
from unique_web_search.services.executors.v3.schema import (
    SearchPayload,
    WebSearchV3ToolParameters,
)


class _StubExecutor(BaseWebSearchExecutor[Any]):
    """Concrete executor for unit-testing ``_extract_search_params``."""

    async def run(self) -> list[ContentChunk]:
        return []


def _make_stub_executor(
    exposed_params_cls: type[ExposedParams] | None,
) -> _StubExecutor:
    return _StubExecutor(
        services=ExecutorServiceContext(
            search_engine_service=None,  # type: ignore[arg-type]
            crawler_service=None,  # type: ignore[arg-type]
            content_processor=None,  # type: ignore[arg-type]
            language_model_service=None,  # type: ignore[arg-type]
            chunk_relevancy_sorter=None,
        ),
        config=ExecutorConfiguration(
            chunk_relevancy_sort_config=None,  # type: ignore[arg-type]
            company_id="test",
            debug_info=None,  # type: ignore[arg-type]
        ),
        callbacks=ExecutorCallbacks(
            message_log_callback=None,  # type: ignore[arg-type]
            content_reducer=lambda x: x,
            query_elicitation=None,  # type: ignore[arg-type]
            tool_progress_reporter=None,
        ),
        tool_call=LanguageModelFunction(id="1", name="WebSearch", arguments={}),
        tool_parameters=WebSearchToolParameters(query="q"),
        exposed_params_cls=exposed_params_cls,
    )


class TestV1FlatExposedParams:
    @pytest.mark.ai
    def test_v1_tool_schema_includes_flat_exposed_fields(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="us"),
        )
        exposed = config.exposed_params_model()
        tool_model = WebSearchToolParameters.with_exposed_params(exposed)
        assert "gl" in tool_model.model_fields
        assert "parameters" not in tool_model.model_fields

    @pytest.mark.ai
    def test_v1_tool_schema_has_no_legacy_date_restrict_without_exposure(self) -> None:
        config = GoogleConfig()
        exposed = config.exposed_params_model()
        tool_model = WebSearchToolParameters.with_exposed_params(exposed)
        assert "date_restrict" not in tool_model.model_fields

    @pytest.mark.ai
    def test_v1_json_schema_uses_camel_case_aliases(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=True, value="d7"),
        )
        exposed = config.exposed_params_model()
        tool_model = WebSearchToolParameters.with_exposed_params(exposed)
        props = tool_model.model_json_schema()["properties"]
        assert "dateRestrict" in props
        assert "date_restrict" not in props
        assert "title" not in props["dateRestrict"]
        assert "default" not in props["dateRestrict"]

    @pytest.mark.ai
    def test_v1_rejects_misspelled_param(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=True, value=None),
        )
        exposed = config.exposed_params_model()
        tool_model = WebSearchToolParameters.with_exposed_params(exposed)
        with pytest.raises(ValidationError):
            tool_model.model_validate(
                {"query": "q", "search_domainfilter": "example.com"}
            )


class TestV3FlatExposedParams:
    @pytest.mark.ai
    def test_search_payload_includes_flat_exposed_fields(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="us"),
        )
        exposed = config.exposed_params_model()
        payload_model = SearchPayload.with_exposed_params(exposed)
        assert "gl" in payload_model.model_fields
        assert "parameters" not in payload_model.model_fields

    @pytest.mark.ai
    def test_search_payload_unchanged_when_nothing_exposed(self) -> None:
        config = GoogleConfig()
        exposed = config.exposed_params_model()
        assert exposed is None
        assert SearchPayload.with_exposed_params(exposed) is SearchPayload

    @pytest.mark.ai
    def test_v3_tool_schema_has_no_parameters_key(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="us"),
            date_restrict=ExposableStrOrNone(expose=True, value="d7"),
        )
        exposed = config.exposed_params_model()
        tool_model = WebSearchV3ToolParameters.with_exposed_params(exposed)
        schema = tool_model.model_json_schema()
        payload_props = schema["$defs"]["SearchPayload"]["properties"]
        assert "parameters" not in payload_props
        assert "gl" in payload_props
        # Exposed to the LLM under the camelCase alias, not the snake_case name.
        assert "dateRestrict" in payload_props
        assert "date_restrict" not in payload_props
        assert "title" not in payload_props["gl"]
        assert "default" not in payload_props["gl"]

    @pytest.mark.ai
    def test_schema_hint_renders_camel_case_aliases(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=True, value=None),
        )
        exposed = config.exposed_params_model()
        hint = WebSearchV3ToolParameters.schema_hint(exposed)
        assert "dateRestrict" in hint
        assert "date_restrict" not in hint


class TestExtractSearchParams:
    @pytest.mark.ai
    def test_extract_omits_none_and_tool_only_fields(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="us"),
            date_restrict=ExposableStrOrNone(expose=True, value="d7"),
        )
        exposed = config.exposed_params_model()
        assert exposed is not None
        PayloadModel = SearchPayload.with_exposed_params(exposed)
        payload = PayloadModel(gap="facet", query="q", gl="ch")

        executor = _make_stub_executor(exposed)
        params = executor._extract_search_params(payload)

        assert params is not None
        assert params.model_dump(by_alias=True, exclude_none=True) == {"gl": "ch"}
        dumped = params.model_dump(exclude_none=True)
        assert "gap" not in dumped
        assert "query" not in dumped

    @pytest.mark.ai
    def test_extract_returns_none_when_no_class(self) -> None:
        executor = _make_stub_executor(None)
        params = executor._extract_search_params(WebSearchToolParameters(query="q"))
        assert params is None
