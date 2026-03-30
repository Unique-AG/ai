"""Tests that _prepare_all_completions_params_util_v2 and _v3 produce
identical output to the original _prepare_all_completions_params_util for
every supported combination of inputs.
"""

from __future__ import annotations

import copy
import warnings
from typing import Any

import pytest
from pydantic import BaseModel

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.functions import (
    _prepare_all_completions_params_util,
    _prepare_all_completions_params_util_v2,
    _prepare_all_completions_params_util_v3,
)
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelTool,
    LanguageModelToolDescription,
    LanguageModelToolParameterProperty,
    LanguageModelToolParameters,
    LanguageModelUserMessage,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_lm_messages() -> LanguageModelMessages:
    """Empty LanguageModelMessages list."""
    return LanguageModelMessages([])


@pytest.fixture
def simple_lm_messages() -> LanguageModelMessages:
    """LanguageModelMessages with one user message."""
    return LanguageModelMessages(
        [
            LanguageModelUserMessage(content="Hello world"),
        ]
    )


@pytest.fixture
def openai_messages() -> list[dict[str, Any]]:
    """OpenAI-style message dicts with snake_case keys."""
    return [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Tell me a joke."},
    ]


@pytest.fixture
def openai_messages_with_nested_snake() -> list[dict[str, Any]]:
    """OpenAI-style messages with nested snake_case keys that need camelizing."""
    return [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"location": "Zurich"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": '{"temp": 20}',
        },
    ]


@pytest.fixture
def mock_tool() -> LanguageModelTool:
    """A LanguageModelTool for testing."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return LanguageModelTool(
            name="get_weather",
            description="Get current weather",
            parameters=LanguageModelToolParameters(
                type="object",
                properties={
                    "location": LanguageModelToolParameterProperty(
                        type="string",
                        description="City name",
                    ),
                },
                required=["location"],
            ),
        )


class _WeatherParams(BaseModel):
    location: str
    unit: str = "celsius"


@pytest.fixture
def mock_tool_description() -> LanguageModelToolDescription:
    """A LanguageModelToolDescription for testing."""
    return LanguageModelToolDescription(
        name="get_forecast",
        description="Get weather forecast",
        parameters=_WeatherParams,
    )


@pytest.fixture
def content_chunks() -> list[ContentChunk]:
    """Sample content chunks for search context testing."""
    return [
        ContentChunk(
            id="cont_aaaaaaaaaaaaaaaaaaaaaaaa",
            chunk_id="chunk_bbbbbbbbbbbbbbbbbbbbbb",
            key="doc.pdf",
            title="Test Document",
            url="https://example.com/doc.pdf",
            start_page=1,
            end_page=3,
            order=0,
            text="Sample chunk text",
            object="content",
        ),
        ContentChunk(
            id="cont_cccccccccccccccccccccccc",
            chunk_id="chunk_dddddddddddddddddddddd",
            key="doc2.pdf",
            title="Second Document",
            url=None,
            start_page=None,
            end_page=None,
            order=1,
            text="Another chunk",
            object="content",
        ),
    ]


class _StructuredOutput(BaseModel):
    """Pydantic model used as structured_output_model."""

    answer: str
    confidence: float


@pytest.fixture
def structured_output_dict() -> dict[str, Any]:
    """Dict-based structured output schema."""
    return {
        "title": "MySchema",
        "type": "object",
        "properties": {
            "result": {"type": "string"},
        },
        "required": ["result"],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Models that have default_options and temperature_bounds (reasoning models)
MODEL_WITH_DEFAULTS = LanguageModelName.AZURE_GPT_51_THINKING_2025_1113
# Model with no default_options (plain GPT-4)
MODEL_WITHOUT_DEFAULTS = LanguageModelName.AZURE_GPT_4_0613
# A plain string model name
STRING_MODEL = "custom-model-v1"


_IMPLEMENTATIONS = {
    "v2": _prepare_all_completions_params_util_v2,
    "v3": _prepare_all_completions_params_util_v3,
}


def _call_all(
    **kwargs: Any,
) -> dict[str, tuple[Any, ...]]:
    """Call v1, v2, and v3 with identical (deep-copied) kwargs and return results keyed by version."""
    results: dict[str, tuple[Any, ...]] = {}
    results["v1"] = _prepare_all_completions_params_util(**copy.deepcopy(kwargs))
    for name, fn in _IMPLEMENTATIONS.items():
        results[name] = fn(**copy.deepcopy(kwargs))
    return results


_SR_KEYS_FULL = (
    "id",
    "chunkId",
    "key",
    "title",
    "url",
    "startPage",
    "endPage",
    "order",
)
_SR_KEYS_V3 = ("id", "chunkId", "key", "title", "url")


def _sr_to_dict(sr: Any, keys: tuple[str, ...] = _SR_KEYS_FULL) -> dict[str, Any]:
    """Normalize a SearchResult (object or dict) to a plain dict for comparison."""
    if isinstance(sr, dict):
        return {k: sr.get(k) for k in keys}
    return {k: getattr(sr, k, None) for k in keys}


def _assert_search_contexts_match(ref_ctx: Any, ctx: Any, version: str) -> None:
    if ref_ctx is None:
        assert ctx is None, f"{version} search_context should be None"
        return
    assert ctx is not None, f"{version} search_context should not be None"
    assert len(ctx) == len(ref_ctx), f"{version} search_context length differs"
    keys = _SR_KEYS_V3 if version == "v3" else _SR_KEYS_FULL
    for a, b in zip(ref_ctx, ctx):
        assert _sr_to_dict(a, keys) == _sr_to_dict(b, keys), (
            f"{version} search_context item differs"
        )


def _assert_all_match(results: dict[str, tuple[Any, ...]]) -> None:
    """Assert v2 and v3 each produce identical output to v1."""
    ref_options, ref_model, ref_msgs, ref_ctx = results["v1"]
    for version in ("v2", "v3"):
        options, model, msgs, ctx = results[version]
        assert options == ref_options, (
            f"{version} options differ:\n{version}={options}\nv1={ref_options}"
        )
        assert model == ref_model, (
            f"{version} model differs: {version}={model} v1={ref_model}"
        )
        assert msgs == ref_msgs, (
            f"{version} messages differ:\n{version}={msgs}\nv1={ref_msgs}"
        )
        _assert_search_contexts_match(ref_ctx, ctx, version)


# ---------------------------------------------------------------------------
# Tests — basic / minimal
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_v2__matches_v1__empty_lm_messages_string_model(
    empty_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 for the simplest case — empty messages, string model.
    Why this matters: Baseline correctness for the most minimal invocation.
    Setup summary: Call both with empty LanguageModelMessages and a plain string model.
    """
    results = _call_all(
        messages=empty_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.5,
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__simple_lm_messages_enum_model(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 with a real LanguageModelName enum (no default_options).
    Why this matters: Ensures model name resolution from enum works identically.
    Setup summary: Call both with a simple message and AZURE_GPT_4_0613.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=MODEL_WITHOUT_DEFAULTS,
        temperature=0.7,
    )
    _assert_all_match(results)


# ---------------------------------------------------------------------------
# Tests — OpenAI-style messages (dict list)
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_v2__matches_v1__openai_messages_string_model(
    openai_messages: list[dict[str, Any]],
) -> None:
    """
    Purpose: Verify v2 matches v1 when messages are OpenAI dicts, not LanguageModelMessages.
    Why this matters: The two branches (LanguageModelMessages vs dict list) use different serialization.
    Setup summary: Call both with OpenAI-style dicts and a string model name.
    """
    results = _call_all(
        messages=openai_messages,
        model_name=STRING_MODEL,
        temperature=0.3,
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__openai_messages_with_nested_snake_case(
    openai_messages_with_nested_snake: list[dict[str, Any]],
) -> None:
    """
    Purpose: Verify camelization of nested snake_case keys is identical in v2.
    Why this matters: tool_calls -> toolCalls conversion must match the custom __camelize_keys.
    Setup summary: Call both with messages containing nested snake_case keys.
    """
    results = _call_all(
        messages=openai_messages_with_nested_snake,
        model_name=STRING_MODEL,
        temperature=0.0,
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__openai_messages_enum_model_with_defaults(
    openai_messages: list[dict[str, Any]],
) -> None:
    """
    Purpose: Verify v2 matches v1 when OpenAI dicts are used with a model that has default_options.
    Why this matters: Ensures default_options merging + OpenAI message serialization both work.
    Setup summary: Call both with OpenAI dicts and a reasoning model (has default_options).
    """
    results = _call_all(
        messages=openai_messages,
        model_name=MODEL_WITH_DEFAULTS,
        temperature=0.5,
    )
    _assert_all_match(results)


# ---------------------------------------------------------------------------
# Tests — tools
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_v2__matches_v1__with_legacy_tool(
    simple_lm_messages: LanguageModelMessages,
    mock_tool: LanguageModelTool,
) -> None:
    """
    Purpose: Verify v2 matches v1 when a LanguageModelTool is provided.
    Why this matters: Tool serialization into options must be identical.
    Setup summary: Call both with a single LanguageModelTool.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.0,
        tools=[mock_tool],
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__with_tool_description(
    simple_lm_messages: LanguageModelMessages,
    mock_tool_description: LanguageModelToolDescription,
) -> None:
    """
    Purpose: Verify v2 matches v1 when a LanguageModelToolDescription is provided.
    Why this matters: Both tool types must serialize identically in options.
    Setup summary: Call both with a single LanguageModelToolDescription.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.0,
        tools=[mock_tool_description],
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__with_multiple_tools(
    simple_lm_messages: LanguageModelMessages,
    mock_tool: LanguageModelTool,
    mock_tool_description: LanguageModelToolDescription,
) -> None:
    """
    Purpose: Verify v2 matches v1 when multiple tools of different types are provided.
    Why this matters: Mixed tool lists must serialize identically.
    Setup summary: Call both with a list containing both tool types.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.2,
        tools=[mock_tool, mock_tool_description],
    )
    _assert_all_match(results)


# ---------------------------------------------------------------------------
# Tests — tool_choice
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.parametrize(
    "tool_choice",
    [
        "auto",
        "none",
        "required",
        {"type": "function", "function": {"name": "get_weather"}},
    ],
    ids=["auto", "none", "required", "specific-function"],
)
def test_AI_v2__matches_v1__tool_choice_variants(
    simple_lm_messages: LanguageModelMessages,
    tool_choice: Any,
) -> None:
    """
    Purpose: Verify v2 matches v1 for every tool_choice variant.
    Why this matters: tool_choice insertion into other_options must follow same logic.
    Setup summary: Parametrize over string and dict tool_choice values.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.0,
        tool_choice=tool_choice,
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__tool_choice_does_not_override_existing(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when other_options already contains toolChoice.
    Why this matters: Caller-specified toolChoice in other_options must not be overwritten.
    Setup summary: Pass tool_choice param AND other_options with toolChoice already set.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.0,
        tool_choice="auto",
        other_options={"toolChoice": "none"},
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__tool_choice_with_model_defaults(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when tool_choice is used with a model that has default_options.
    Why this matters: Order of tool_choice insertion vs default_options merge matters.
    Setup summary: Use tool_choice with a reasoning model.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=MODEL_WITH_DEFAULTS,
        temperature=0.5,
        tool_choice="auto",
    )
    _assert_all_match(results)


# ---------------------------------------------------------------------------
# Tests — other_options
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_v2__matches_v1__other_options_basic(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when arbitrary other_options are passed.
    Why this matters: other_options should be merged into final options identically.
    Setup summary: Call both with max_tokens and top_p in other_options.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.5,
        other_options={"max_tokens": 1024, "top_p": 0.9},
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__other_options_override_temperature(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when other_options contains a temperature override.
    Why this matters: other_options is merged after temperature is set, so it can override.
    Setup summary: Pass temperature=0.5 but other_options with temperature=0.9.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.5,
        other_options={"temperature": 0.9},
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__other_options_with_model_defaults(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when other_options are merged with model default_options.
    Why this matters: Caller other_options must override model defaults, not vice versa.
    Setup summary: Use a model with default_options and provide conflicting other_options.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=MODEL_WITH_DEFAULTS,
        temperature=0.5,
        other_options={"reasoning_effort": "high", "custom_key": "custom_value"},
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__none_other_options(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when other_options is explicitly None.
    Why this matters: None handling must be identical.
    Setup summary: Pass other_options=None explicitly.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.5,
        other_options=None,
    )
    _assert_all_match(results)


# ---------------------------------------------------------------------------
# Tests — structured output
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_v2__matches_v1__structured_output_pydantic_model(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when structured_output_model is a Pydantic BaseModel class.
    Why this matters: json_schema generation and responseFormat construction must be identical.
    Setup summary: Pass _StructuredOutput as structured_output_model.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.0,
        structured_output_model=_StructuredOutput,
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__structured_output_dict(
    simple_lm_messages: LanguageModelMessages,
    structured_output_dict: dict[str, Any],
) -> None:
    """
    Purpose: Verify v2 matches v1 when structured_output_model is a dict schema.
    Why this matters: Dict-based schemas use "title" for name, not __name__.
    Setup summary: Pass a dict schema as structured_output_model.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.0,
        structured_output_model=structured_output_dict,
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__structured_output_dict_no_title(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when dict schema has no "title" key (falls back to "DefaultName").
    Why this matters: Edge case for the dict branch of response format building.
    Setup summary: Pass a dict schema without a "title" key.
    """
    schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.0,
        structured_output_model=schema,
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__structured_output_enforce_schema(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when structured_output_enforce_schema is True.
    Why this matters: "strict" flag in responseFormat must be set identically.
    Setup summary: Pass structured_output_model with enforce_schema=True.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.0,
        structured_output_model=_StructuredOutput,
        structured_output_enforce_schema=True,
    )
    _assert_all_match(results)


# ---------------------------------------------------------------------------
# Tests — content chunks / search context
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_v2__matches_v1__with_content_chunks(
    simple_lm_messages: LanguageModelMessages,
    content_chunks: list[ContentChunk],
) -> None:
    """
    Purpose: Verify v2 matches v1 when content_chunks produce a search context.
    Why this matters: SearchResult construction must be identical.
    Setup summary: Call both with two content chunks.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.0,
        content_chunks=content_chunks,
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__empty_content_chunks(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when content_chunks is an empty list.
    Why this matters: Empty list should produce None search_context in both.
    Setup summary: Pass content_chunks=[].
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.0,
        content_chunks=[],
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__none_content_chunks(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when content_chunks is None.
    Why this matters: None should produce None search_context in both.
    Setup summary: Pass content_chunks=None explicitly.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.0,
        content_chunks=None,
    )
    _assert_all_match(results)


# ---------------------------------------------------------------------------
# Tests — temperature clamping
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.parametrize(
    "temperature",
    [0.0, 0.5, 1.0, 1.5, 2.0, -0.5],
    ids=["zero", "mid", "one", "above-one", "two", "negative"],
)
def test_AI_v2__matches_v1__temperature_clamping_with_bounded_model(
    simple_lm_messages: LanguageModelMessages,
    temperature: float,
) -> None:
    """
    Purpose: Verify v2 matches v1 temperature clamping for models with temperature_bounds.
    Why this matters: Temperature must be clamped identically regardless of input value.
    Setup summary: Parametrize over a wide range of temperatures with a bounded model.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=MODEL_WITH_DEFAULTS,
        temperature=temperature,
    )
    _assert_all_match(results)


@pytest.mark.ai
@pytest.mark.parametrize(
    "temperature",
    [0.0, 0.5, 1.0, 1.5, 2.0],
    ids=["zero", "mid", "one", "above-one", "two"],
)
def test_AI_v2__matches_v1__temperature_no_clamping_string_model(
    simple_lm_messages: LanguageModelMessages,
    temperature: float,
) -> None:
    """
    Purpose: Verify v2 matches v1 when no temperature clamping should occur (string model).
    Why this matters: Temperature must pass through unmodified when there are no bounds.
    Setup summary: Parametrize over temperatures with a string model name.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=temperature,
    )
    _assert_all_match(results)


# ---------------------------------------------------------------------------
# Tests — model default_options merging
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_v2__matches_v1__model_defaults_applied(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when model has default_options that should appear in output.
    Why this matters: Model-level defaults (e.g. reasoning_effort) must be present in options.
    Setup summary: Use a model with default_options and no other_options.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=MODEL_WITH_DEFAULTS,
        temperature=0.5,
    )
    _assert_all_match(results)
    assert "reasoning_effort" in results["v1"][0]


@pytest.mark.ai
def test_AI_v2__matches_v1__caller_overrides_model_defaults(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when caller other_options override model default_options.
    Why this matters: Caller intent must take precedence over model defaults.
    Setup summary: Pass other_options that conflict with model default_options.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=MODEL_WITH_DEFAULTS,
        temperature=0.5,
        other_options={"reasoning_effort": "high"},
    )
    _assert_all_match(results)
    assert results["v1"][0]["reasoning_effort"] == "high"


# ---------------------------------------------------------------------------
# Tests — does not mutate inputs
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.parametrize("impl", ["v2", "v3"])
def test_AI__does_not_mutate_other_options(
    simple_lm_messages: LanguageModelMessages,
    impl: str,
) -> None:
    """
    Purpose: Verify v2/v3 do not mutate the caller's other_options dict.
    Why this matters: Callers may reuse the same dict; mutation would be a bug.
    Setup summary: Snapshot other_options before call, compare after.
    """
    fn = _IMPLEMENTATIONS[impl]
    original = {"max_tokens": 512}
    snapshot = copy.deepcopy(original)
    fn(
        messages=simple_lm_messages,
        model_name=MODEL_WITH_DEFAULTS,
        temperature=0.5,
        other_options=original,
        tool_choice="auto",
    )
    assert original == snapshot


@pytest.mark.ai
@pytest.mark.parametrize("impl", ["v2", "v3"])
def test_AI__does_not_mutate_openai_messages(
    openai_messages: list[dict[str, Any]],
    impl: str,
) -> None:
    """
    Purpose: Verify v2/v3 do not mutate the caller's OpenAI messages list.
    Why this matters: Callers may reuse the same message list across calls.
    Setup summary: Snapshot messages before call, compare after.
    """
    fn = _IMPLEMENTATIONS[impl]
    snapshot = copy.deepcopy(openai_messages)
    fn(
        messages=openai_messages,
        model_name=STRING_MODEL,
        temperature=0.5,
    )
    assert openai_messages == snapshot


# ---------------------------------------------------------------------------
# Tests — full kitchen sink
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_v2__matches_v1__all_params_combined(
    simple_lm_messages: LanguageModelMessages,
    mock_tool: LanguageModelTool,
    content_chunks: list[ContentChunk],
) -> None:
    """
    Purpose: Verify v2 matches v1 when every parameter is provided simultaneously.
    Why this matters: Interaction between all features must produce identical output.
    Setup summary: Call both with tools, tool_choice, other_options, content_chunks,
    structured_output_model, and a model with default_options.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=MODEL_WITH_DEFAULTS,
        temperature=0.7,
        tools=[mock_tool],
        tool_choice="auto",
        other_options={"max_tokens": 2048, "stop": ["\n"]},
        content_chunks=content_chunks,
        structured_output_model=_StructuredOutput,
        structured_output_enforce_schema=True,
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__all_params_with_openai_messages(
    openai_messages: list[dict[str, Any]],
    mock_tool: LanguageModelTool,
    content_chunks: list[ContentChunk],
    structured_output_dict: dict[str, Any],
) -> None:
    """
    Purpose: Verify v2 matches v1 with OpenAI messages and every parameter combined.
    Why this matters: Ensures the OpenAI branch also handles all features identically.
    Setup summary: Call both with OpenAI messages, tools, chunks, dict schema, and model defaults.
    """
    results = _call_all(
        messages=openai_messages,
        model_name=MODEL_WITH_DEFAULTS,
        temperature=0.3,
        tools=[mock_tool],
        tool_choice="required",
        other_options={"top_p": 0.95},
        content_chunks=content_chunks,
        structured_output_model=structured_output_dict,
        structured_output_enforce_schema=False,
    )
    _assert_all_match(results)


# ---------------------------------------------------------------------------
# Tests — edge cases
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_v2__matches_v1__empty_other_options_dict(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when other_options is an empty dict (not None).
    Why this matters: Empty dict and None should behave differently for deep-copy logic.
    Setup summary: Pass other_options={}.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.5,
        other_options={},
    )
    _assert_all_match(results)


@pytest.mark.ai
def test_AI_v2__matches_v1__tools_empty_list(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when tools is an empty list.
    Why this matters: Empty tools list should not add a "tools" key to options.
    Setup summary: Pass tools=[].
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.0,
        tools=[],
    )
    _assert_all_match(results)
    assert "tools" not in results["v1"][0]


@pytest.mark.ai
def test_AI_v2__matches_v1__tool_choice_none_value(
    simple_lm_messages: LanguageModelMessages,
) -> None:
    """
    Purpose: Verify v2 matches v1 when tool_choice parameter is None (default).
    Why this matters: None tool_choice should not add toolChoice to options.
    Setup summary: Pass tool_choice=None explicitly.
    """
    results = _call_all(
        messages=simple_lm_messages,
        model_name=STRING_MODEL,
        temperature=0.0,
        tool_choice=None,
    )
    _assert_all_match(results)
    assert "toolChoice" not in results["v1"][0]
