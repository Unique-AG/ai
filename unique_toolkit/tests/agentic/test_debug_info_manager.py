"""Tests for DebugInfoManager and _extract_tool_calls_from_stream_response."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from openai.types.responses import ResponseCodeInterpreterToolCall

from unique_toolkit.agentic.debug_info_manager.debug_info_manager import (
    AnalyticsLanguageModel,
    DebugInfoManager,
    _extract_tool_calls_from_stream_response,
)
from unique_toolkit.agentic.tools.openai_builtin.base import OpenAIBuiltInToolName
from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats
from unique_toolkit.language_model.schemas import (
    LanguageModelMessageRole,
    LanguageModelStreamResponse,
    LanguageModelStreamResponseMessage,
    LanguageModelTokenUsage,
    ResponsesLanguageModelStreamResponse,
)

# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------


def _make_message() -> LanguageModelStreamResponseMessage:
    return LanguageModelStreamResponseMessage(
        id="msg-1",
        chat_id="chat-1",
        previous_message_id=None,
        role=LanguageModelMessageRole.ASSISTANT,
        text="hello",
    )


def _make_code_interpreter_call(
    call_id: str = "call-1",
    container_id: str = "container-1",
) -> ResponseCodeInterpreterToolCall:
    return ResponseCodeInterpreterToolCall(
        id=call_id,
        container_id=container_id,
        status="completed",
        type="code_interpreter_call",
    )


def _make_responses_stream_response(
    calls: list[ResponseCodeInterpreterToolCall],
) -> ResponsesLanguageModelStreamResponse:
    return ResponsesLanguageModelStreamResponse(
        message=_make_message(),
        output=calls,  # type: ignore[arg-type]
    )


@pytest.fixture
def debug_info_manager() -> DebugInfoManager:
    return DebugInfoManager()


@pytest.fixture
def tool_manager() -> MagicMock:
    mock = MagicMock()
    mock.get_exclusive_tools.return_value = []
    mock.get_tool_choices.return_value = []
    return mock


# ---------------------------------------------------------------------------
# _extract_tool_calls_from_stream_response
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__returns_empty__when_not_responses_stream(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify the helper returns an empty list for a plain LanguageModelStreamResponse.
    Why this matters: Only ResponsesLanguageModelStreamResponse carries code interpreter calls;
                      processing other types would raise attribute errors.
    Setup summary: Provide a base LanguageModelStreamResponse; assert empty list returned.
    """
    # Arrange
    stream_response = LanguageModelStreamResponse(
        message=_make_message(),
    )

    # Act
    result: list[dict[str, Any]] = _extract_tool_calls_from_stream_response(
        stream_response, tool_manager
    )

    # Assert
    assert result == []


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__returns_empty__when_no_code_interpreter_calls(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify the helper returns an empty list when the stream response has no code interpreter calls.
    Why this matters: Avoids polluting debug_info with empty or wrong entries.
    Setup summary: Build ResponsesLanguageModelStreamResponse with empty output; assert empty list.
    """
    # Arrange
    stream_response = _make_responses_stream_response(calls=[])

    # Act
    result: list[dict[str, Any]] = _extract_tool_calls_from_stream_response(
        stream_response, tool_manager
    )

    # Assert
    assert result == []


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__returns_one_entry__for_single_call(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify the helper returns a single tool info dict for one code interpreter call.
    Why this matters: Each call must produce exactly one analytics entry with the correct structure.
    Setup summary: One code interpreter call; assert result has one entry with name and info.
    """
    # Arrange
    call = _make_code_interpreter_call(call_id="call-1", container_id="ctr-1")
    stream_response = _make_responses_stream_response(calls=[call])

    # Act
    result: list[dict[str, Any]] = _extract_tool_calls_from_stream_response(
        stream_response, tool_manager
    )

    # Assert
    assert len(result) == 1
    assert result[0]["name"] == OpenAIBuiltInToolName.CODE_INTERPRETER
    assert result[0]["info"]["id"] == "call-1"
    assert result[0]["info"]["container_id"] == "ctr-1"
    assert result[0]["info"]["is_exclusive"] is False
    assert result[0]["info"]["is_forced"] is False


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__deduplicates_calls__with_same_id(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify duplicate code interpreter calls (same id) are deduplicated to one entry.
    Why this matters: Streaming can produce repeated events for the same call; counting them
                      twice would corrupt analytics.
    Setup summary: Two calls with identical id in output; assert only one entry returned.
    """
    # Arrange
    call_a = _make_code_interpreter_call(call_id="call-dup", container_id="ctr-1")
    call_b = _make_code_interpreter_call(call_id="call-dup", container_id="ctr-1")
    stream_response = _make_responses_stream_response(calls=[call_a, call_b])

    # Act
    result: list[dict[str, Any]] = _extract_tool_calls_from_stream_response(
        stream_response, tool_manager
    )

    # Assert
    assert len(result) == 1
    assert result[0]["info"]["id"] == "call-dup"
    assert result[0]["info"]["is_exclusive"] is False
    assert result[0]["info"]["is_forced"] is False


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__returns_multiple_entries__for_distinct_calls(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify two distinct code interpreter calls produce two separate tool info entries.
    Why this matters: Multiple code blocks in one response must each be tracked individually.
    Setup summary: Two calls with different ids; assert two entries returned in order.
    """
    # Arrange
    call_a = _make_code_interpreter_call(call_id="call-1", container_id="ctr-1")
    call_b = _make_code_interpreter_call(call_id="call-2", container_id="ctr-2")
    stream_response = _make_responses_stream_response(calls=[call_a, call_b])

    # Act
    result: list[dict[str, Any]] = _extract_tool_calls_from_stream_response(
        stream_response, tool_manager
    )

    # Assert
    assert len(result) == 2
    ids = [entry["info"]["id"] for entry in result]
    assert "call-1" in ids
    assert "call-2" in ids
    for entry in result:
        assert entry["info"]["is_exclusive"] is False
        assert entry["info"]["is_forced"] is False


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__includes_loop_iteration__when_provided(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify loop_iteration is set in the info dict when a non-None index is passed.
    Why this matters: Loop iteration tracking is critical for multi-step agentic analytics.
    Setup summary: One call, loop_iteration_index=3; assert info contains loop_iteration=3.
    """
    # Arrange
    call = _make_code_interpreter_call()
    stream_response = _make_responses_stream_response(calls=[call])

    # Act
    result: list[dict[str, Any]] = _extract_tool_calls_from_stream_response(
        stream_response, tool_manager, loop_iteration_index=3
    )

    # Assert
    assert result[0]["info"]["loop_iteration"] == 3
    assert result[0]["info"]["is_exclusive"] is False
    assert result[0]["info"]["is_forced"] is False


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__omits_loop_iteration_key__when_not_provided(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify loop_iteration key is absent from info when loop_iteration_index is None.
    Why this matters: Matches the behaviour of extract_tool_debug_info, which only sets the key
                      when a non-None index is given, so downstream consumers checking for key
                      presence behave consistently across both regular and builtin tool entries.
    Setup summary: One call, no loop_iteration_index; assert loop_iteration key is absent.
    """
    # Arrange
    call = _make_code_interpreter_call()
    stream_response = _make_responses_stream_response(calls=[call])

    # Act
    result: list[dict[str, Any]] = _extract_tool_calls_from_stream_response(
        stream_response, tool_manager
    )

    # Assert
    assert "loop_iteration" not in result[0]["info"]
    assert result[0]["info"]["is_exclusive"] is False
    assert result[0]["info"]["is_forced"] is False


# ---------------------------------------------------------------------------
# DebugInfoManager.extract_builtin_tool_debug_info
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_debug_info_manager__extract_builtin_tool_debug_info__extends_tools_list(
    debug_info_manager: DebugInfoManager,
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify extract_builtin_tool_debug_info appends code interpreter entries to debug_info tools.
    Why this matters: The manager is the single accumulation point for all debug analytics.
    Setup summary: Manager starts empty; call method with one call; assert tools list has one entry.
    """
    # Arrange
    call = _make_code_interpreter_call(call_id="call-1", container_id="ctr-1")
    stream_response = _make_responses_stream_response(calls=[call])

    # Act
    debug_info_manager.extract_builtin_tool_debug_info(stream_response, tool_manager)

    # Assert
    tools: list[dict[str, Any]] = debug_info_manager.get()["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == OpenAIBuiltInToolName.CODE_INTERPRETER
    assert tools[0]["info"]["id"] == "call-1"
    assert tools[0]["info"]["container_id"] == "ctr-1"
    assert tools[0]["info"]["is_exclusive"] is False
    assert tools[0]["info"]["is_forced"] is False


@pytest.mark.ai
def test_debug_info_manager__extract_builtin_tool_debug_info__skips_non_responses_stream(
    debug_info_manager: DebugInfoManager,
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify no entries are added to tools when the stream is a plain LanguageModelStreamResponse.
    Why this matters: Calling this method with a non-Responses stream must be a no-op, not an error.
    Setup summary: Pass a base LanguageModelStreamResponse; assert tools list remains empty.
    """
    # Arrange
    stream_response = LanguageModelStreamResponse(message=_make_message())

    # Act
    debug_info_manager.extract_builtin_tool_debug_info(stream_response, tool_manager)

    # Assert
    assert debug_info_manager.get()["tools"] == []


@pytest.mark.ai
def test_debug_info_manager__extract_builtin_tool_debug_info__accumulates_across_calls(
    debug_info_manager: DebugInfoManager,
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify multiple invocations of extract_builtin_tool_debug_info accumulate entries.
    Why this matters: In multi-iteration loops each iteration appends its calls; total must be correct.
    Setup summary: Call method twice with one call each; assert tools list has two entries total.
    """
    # Arrange
    call_a = _make_code_interpreter_call(call_id="call-1", container_id="ctr-1")
    call_b = _make_code_interpreter_call(call_id="call-2", container_id="ctr-2")
    stream_a = _make_responses_stream_response(calls=[call_a])
    stream_b = _make_responses_stream_response(calls=[call_b])

    # Act
    debug_info_manager.extract_builtin_tool_debug_info(
        stream_a, tool_manager, loop_iteration_index=0
    )
    debug_info_manager.extract_builtin_tool_debug_info(
        stream_b, tool_manager, loop_iteration_index=1
    )

    # Assert
    tools: list[dict[str, Any]] = debug_info_manager.get()["tools"]
    assert len(tools) == 2
    assert tools[0]["info"]["loop_iteration"] == 0
    assert tools[1]["info"]["loop_iteration"] == 1
    assert tools[0]["info"]["is_exclusive"] is False
    assert tools[0]["info"]["is_forced"] is False
    assert tools[1]["info"]["is_exclusive"] is False
    assert tools[1]["info"]["is_forced"] is False


@pytest.mark.ai
def test_debug_info_manager__extract_builtin_tool_debug_info__passes_loop_iteration_to_entries(
    debug_info_manager: DebugInfoManager,
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify loop_iteration_index is propagated into each tool entry's info dict.
    Why this matters: Correct loop attribution is required for per-iteration agentic analytics.
    Setup summary: Call method with loop_iteration_index=5; assert info contains loop_iteration=5.
    """
    # Arrange
    call = _make_code_interpreter_call()
    stream_response = _make_responses_stream_response(calls=[call])

    # Act
    debug_info_manager.extract_builtin_tool_debug_info(
        stream_response, tool_manager, loop_iteration_index=5
    )

    # Assert
    tools: list[dict[str, Any]] = debug_info_manager.get()["tools"]
    assert tools[0]["info"]["loop_iteration"] == 5
    assert tools[0]["info"]["is_exclusive"] is False
    assert tools[0]["info"]["is_forced"] is False


# ---------------------------------------------------------------------------
# is_exclusive / is_forced flags (new in this branch)
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__is_exclusive_false__when_not_in_exclusive_tools(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify is_exclusive is False when CODE_INTERPRETER is not in get_exclusive_tools().
    Why this matters: Incorrect True would misrepresent the tool's exclusivity to downstream consumers.
    Setup summary: tool_manager returns empty exclusive list; assert is_exclusive=False in info.
    """
    # Arrange
    call = _make_code_interpreter_call()
    stream_response = _make_responses_stream_response(calls=[call])
    tool_manager.get_exclusive_tools.return_value = []

    # Act
    result = _extract_tool_calls_from_stream_response(stream_response, tool_manager)

    # Assert
    assert result[0]["info"]["is_exclusive"] is False


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__is_exclusive_true__when_in_exclusive_tools(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify is_exclusive is True when CODE_INTERPRETER is returned by get_exclusive_tools().
    Why this matters: The flag must accurately reflect whether the tool was configured as exclusive.
    Setup summary: tool_manager returns [CODE_INTERPRETER] from get_exclusive_tools(); assert info is_exclusive=True.
    """
    # Arrange
    call = _make_code_interpreter_call()
    stream_response = _make_responses_stream_response(calls=[call])
    tool_manager.get_exclusive_tools.return_value = [
        OpenAIBuiltInToolName.CODE_INTERPRETER
    ]

    # Act
    result = _extract_tool_calls_from_stream_response(stream_response, tool_manager)

    # Assert
    assert result[0]["info"]["is_exclusive"] is True


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__is_forced_false__when_not_in_tool_choices(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify is_forced is False when CODE_INTERPRETER is not in get_tool_choices().
    Why this matters: Incorrect True would misrepresent whether the tool was force-selected.
    Setup summary: tool_manager returns empty tool_choices list; assert is_forced=False in info.
    """
    # Arrange
    call = _make_code_interpreter_call()
    stream_response = _make_responses_stream_response(calls=[call])
    tool_manager.get_tool_choices.return_value = []

    # Act
    result = _extract_tool_calls_from_stream_response(stream_response, tool_manager)

    # Assert
    assert result[0]["info"]["is_forced"] is False


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__is_forced_true__when_in_tool_choices(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify is_forced is True when CODE_INTERPRETER is returned by get_tool_choices().
    Why this matters: The flag must accurately reflect whether the tool was force-selected by the caller.
    Setup summary: tool_manager returns [CODE_INTERPRETER] from get_tool_choices(); assert info is_forced=True.
    """
    # Arrange
    call = _make_code_interpreter_call()
    stream_response = _make_responses_stream_response(calls=[call])
    tool_manager.get_tool_choices.return_value = [
        OpenAIBuiltInToolName.CODE_INTERPRETER
    ]

    # Act
    result = _extract_tool_calls_from_stream_response(stream_response, tool_manager)

    # Assert
    assert result[0]["info"]["is_forced"] is True


class TestAddAnalytics:
    language_model = AnalyticsLanguageModel(
        name="AZURE_GPT_5_2025_0807",
        family="openai",
        provider="AZURE",
    )
    tool_display_names = {
        "InternalSearch": "Knowledge Base Search",
        "WebSearch": "Web Search",
    }

    @pytest.mark.ai
    def test_add_analytics__aggregates_consumption_by_llm(
        self, debug_info_manager: DebugInfoManager
    ) -> None:
        debug_info_manager.add_analytics(
            [],
            language_model=self.language_model,
            tool_display_names=self.tool_display_names,
            invocations=[
                LanguageModelInvocationStats.from_usage(
                    "model-b",
                    LanguageModelTokenUsage(
                        prompt_tokens=10,
                        completion_tokens=2,
                        total_tokens=12,
                        cached_tokens=None,
                    ),
                    source="main_loop[1]",
                ),
                LanguageModelInvocationStats.from_usage(
                    "model-a",
                    LanguageModelTokenUsage(
                        prompt_tokens=4,
                        completion_tokens=1,
                        total_tokens=5,
                        cached_tokens=3,
                        reasoning_tokens=1,
                    ),
                    source="planning",
                ),
                LanguageModelInvocationStats.from_usage(
                    "model-b",
                    LanguageModelTokenUsage(
                        prompt_tokens=20,
                        completion_tokens=3,
                        total_tokens=23,
                        cached_tokens=5,
                    ),
                    source="follow_up_questions",
                ),
            ],
        )

        analytics = debug_info_manager.get()["analytics"]
        assert analytics["consumption_by_llm"] == [
            {
                "model_name": "model-a",
                "completion_tokens": 1,
                "prompt_tokens": 4,
                "total_tokens": 5,
                "reasoning_tokens": 1,
                "cached_tokens": 3,
                "cache_write_tokens": None,
                "cost_usd": None,
            },
            {
                "model_name": "model-b",
                "completion_tokens": 5,
                "prompt_tokens": 30,
                "total_tokens": 35,
                "reasoning_tokens": None,
                "cached_tokens": 5,
                "cache_write_tokens": None,
                "cost_usd": None,
            },
        ]
        assert analytics["consumption"] == {
            "completion_tokens": 6,
            "prompt_tokens": 34,
            "total_tokens": 40,
            "reasoning_tokens": 1,
            "cached_tokens": 8,
            "cache_write_tokens": None,
            "cost_usd": None,
        }

    @pytest.mark.ai
    def test_add_analytics__aggregates_complete_model_costs(
        self, debug_info_manager: DebugInfoManager
    ) -> None:
        """Purpose: Verify analytics sums priced invocations by model.
        Why this matters: Reporting needs a model-level total as well as call details.
        Setup summary: Supply two priced invocations and assert their aggregate cost.
        """
        invocations = [
            LanguageModelInvocationStats(
                model_name="model-a",
                token_usage=LanguageModelTokenUsage(
                    prompt_tokens=10, completion_tokens=2
                ),
                source="main_loop[1]",
                cost_usd=0.01,
            ),
            LanguageModelInvocationStats(
                model_name="model-a",
                token_usage=LanguageModelTokenUsage(
                    prompt_tokens=20, completion_tokens=3
                ),
                source="planning",
                cost_usd=0.02,
            ),
        ]

        debug_info_manager.add_analytics(
            [],
            language_model=self.language_model,
            tool_display_names=self.tool_display_names,
            invocations=invocations,
        )

        analytics = debug_info_manager.get()["analytics"]
        assert analytics["consumption_by_llm"][0]["cost_usd"] == pytest.approx(0.03)
        assert analytics["consumption"]["cost_usd"] == pytest.approx(0.03)

    @pytest.mark.ai
    def test_add_analytics__keeps_partial_model_cost_unknown(
        self, debug_info_manager: DebugInfoManager
    ) -> None:
        """Purpose: Verify partially priced model groups do not emit partial totals.
        Why this matters: A partial sum would understate actual model spend.
        Setup summary: Mix priced and unpriced invocations and assert a null total.
        """
        invocations = [
            LanguageModelInvocationStats(
                model_name="model-a",
                token_usage=LanguageModelTokenUsage(
                    prompt_tokens=10, completion_tokens=2
                ),
                source="main_loop[1]",
                cost_usd=0.01,
            ),
            LanguageModelInvocationStats(
                model_name="model-a",
                token_usage=LanguageModelTokenUsage(
                    prompt_tokens=20, completion_tokens=3
                ),
                source="planning",
            ),
        ]

        debug_info_manager.add_analytics(
            [],
            language_model=self.language_model,
            tool_display_names=self.tool_display_names,
            invocations=invocations,
        )

        analytics = debug_info_manager.get()["analytics"]
        assert analytics["consumption_by_llm"][0]["cost_usd"] is None
        assert analytics["consumption"]["cost_usd"] is None

    @pytest.mark.ai
    def test_add_analytics__consumption_empty_without_invocations(
        self, debug_info_manager: DebugInfoManager
    ) -> None:
        debug_info_manager.add_analytics(
            [],
            language_model=self.language_model,
            tool_display_names=self.tool_display_names,
        )

        analytics = debug_info_manager.get()["analytics"]
        assert analytics["consumption_by_llm"] == []
        assert analytics["consumption"] is None

    @pytest.mark.ai
    def test_add_analytics__copies_tools_and_skills__into_new_key(
        self, debug_info_manager: DebugInfoManager
    ) -> None:
        """
        Purpose: Verify add_analytics() writes an 'analytics' key containing the
        current 'tools' list plus the given skills list.
        Setup summary: Seed debug_info with one tool entry; call add_analytics with
        one skill entry; assert analytics.tools and analytics.skills both present.
        """
        debug_info_manager.debug_info["tools"] = [{"name": "WebSearch", "info": {}}]
        skills = [{"name": "plot-skill", "content_id": "c1", "is_forced": True}]

        debug_info_manager.add_analytics(
            skills,
            language_model=self.language_model,
            tool_display_names=self.tool_display_names,
            references=2,
            user_prompt_length=17,
            answer_length=42,
            loop_iteration_count=3,
            total_time_to_answer_ms=1234,
        )

        analytics = debug_info_manager.get()["analytics"]
        assert analytics["tools_used"] == [
            {"name": "WebSearch", "display_name": "Web Search"}
        ]
        assert analytics["tool_call_count"] == 1
        assert analytics["skills_used"] == skills
        assert analytics["references_count"] == 2
        assert analytics["user_prompt_length"] == 17
        assert analytics["answer_length"] == 42
        assert analytics["loop_iteration_count"] == 3
        assert analytics["total_time_to_answer_ms"] == 1234
        assert analytics["subagent_names_used"] == []
        assert analytics["mcp_tool_names_used"] == []
        assert analytics["language_model"] == {
            "name": "AZURE_GPT_5_2025_0807",
            "family": "openai",
            "provider": "AZURE",
        }
        # Reserved placeholders — always present, populated in a later step.
        assert analytics["artifacts_created_count"] is None
        assert analytics["artifacts_created_filetype"] is None
        assert analytics["output_size"] is None

    @pytest.mark.ai
    def test_add_analytics__total_time_to_answer_ms__always_present_as_null(
        self, debug_info_manager: DebugInfoManager
    ) -> None:
        """
        Purpose: Verify total_time_to_answer_ms is always emitted, as null when
        unknown, rather than being omitted from the analytics envelope.
        Why this matters: A stable schema lets consumers rely on the key existing
        (read None) instead of handling a sometimes-missing key.
        Setup summary: Call add_analytics without a timing value; assert the key is
        present and None.
        """
        debug_info_manager.add_analytics(
            [],
            language_model=self.language_model,
            tool_display_names=self.tool_display_names,
        )

        analytics = debug_info_manager.get()["analytics"]
        assert "total_time_to_answer_ms" in analytics
        assert analytics["total_time_to_answer_ms"] is None

    @pytest.mark.ai
    def test_add_analytics__artifacts__populated_from_argument(
        self, debug_info_manager: DebugInfoManager
    ) -> None:
        """
        Purpose: Verify the artifact fields are read from the artifacts argument.
        Why this matters: This is the wiring that makes the reserved keys carry real
        values once Code Interpreter has produced files.
        Setup summary: Pass artifact metadata; assert all fields mirror it.
        """
        debug_info_manager.add_analytics(
            [],
            language_model=self.language_model,
            tool_display_names=self.tool_display_names,
            artifacts={
                "count": 2,
                "filetypes": ["csv", "png"],
                "output_size": 1.5,
            },
        )

        analytics = debug_info_manager.get()["analytics"]
        assert analytics["artifacts_created_count"] == 2
        assert analytics["artifacts_created_filetype"] == ["csv", "png"]
        assert analytics["output_size"] == 1.5

    @pytest.mark.ai
    def test_add_analytics__artifacts__zero_when_code_interpreter_ran_but_empty(
        self, debug_info_manager: DebugInfoManager
    ) -> None:
        """
        Purpose: Verify a ran-but-produced-nothing Code Interpreter turn reports
        count 0 / empty filetypes / 0.0 size, distinct from the never-ran (None)
        case.
        Why this matters: Consumers must be able to tell "0 files created" from
        "no Code Interpreter this turn" — the caller passes {count:0,
        filetypes:[], output_size:0.0} in the former case and None in the latter.
        Setup summary: Pass empty artifact metadata; assert 0 / [] / 0.0 (not None).
        """
        debug_info_manager.add_analytics(
            [],
            language_model=self.language_model,
            tool_display_names=self.tool_display_names,
            artifacts={"count": 0, "filetypes": [], "output_size": 0.0},
        )

        analytics = debug_info_manager.get()["analytics"]
        assert analytics["artifacts_created_count"] == 0
        assert analytics["artifacts_created_filetype"] == []
        assert analytics["output_size"] == 0.0

    @pytest.mark.ai
    def test_add_analytics__artifacts__none_when_no_entry(
        self, debug_info_manager: DebugInfoManager
    ) -> None:
        """
        Purpose: Verify artifact fields are None when no Code Interpreter ran
        (no debug_info["artifacts"] entry) — the always-present, null-when-unknown
        contract from doc 03.
        Setup summary: No artifacts entry seeded; assert all keys present and None.
        """
        debug_info_manager.add_analytics(
            [],
            language_model=self.language_model,
            tool_display_names=self.tool_display_names,
        )

        analytics = debug_info_manager.get()["analytics"]
        assert analytics["artifacts_created_count"] is None
        assert analytics["artifacts_created_filetype"] is None
        assert analytics["output_size"] is None

    @pytest.mark.ai
    def test_add_analytics__context_memory_updated__populated_from_argument(
        self, debug_info_manager: DebugInfoManager
    ) -> None:
        """
        Purpose: Verify the context_memory_updated field mirrors the argument.
        Why this matters: This is the wiring that surfaces whether the user-memory
        postprocessor updated the stored profile this turn.
        Setup summary: Pass True/False; assert the field mirrors it.
        """
        for value in (True, False):
            debug_info_manager.add_analytics(
                [],
                language_model=self.language_model,
                tool_display_names=self.tool_display_names,
                context_memory_updated=value,
            )

            analytics = debug_info_manager.get()["analytics"]
            assert analytics["context_memory_updated"] is value

    @pytest.mark.ai
    def test_add_analytics__context_memory_updated__none_when_not_activated(
        self, debug_info_manager: DebugInfoManager
    ) -> None:
        """
        Purpose: Verify context_memory_updated is None when the user-memory
        postprocessor is not activated (argument omitted) — the always-present,
        null-when-unknown contract.
        Setup summary: Call add_analytics without the argument; assert key present
        and None.
        """
        debug_info_manager.add_analytics(
            [],
            language_model=self.language_model,
            tool_display_names=self.tool_display_names,
        )

        analytics = debug_info_manager.get()["analytics"]
        assert "context_memory_updated" in analytics
        assert analytics["context_memory_updated"] is None

    @pytest.mark.ai
    def test_add_analytics__does_not_remove_top_level_tools_or_skills_keys(
        self, debug_info_manager: DebugInfoManager
    ) -> None:
        """
        Purpose: Verify the original top-level 'tools' key survives untouched.
        Why this matters: Backward compatibility for existing consumers is an
        explicit acceptance criterion — this is the regression guard for it.
        Setup summary: Seed tools; call add_analytics; assert top-level 'tools' key
        is unchanged (identical) after the call.
        """
        tools = [{"name": "InternalSearch", "info": {}}]
        debug_info_manager.debug_info["tools"] = tools

        debug_info_manager.add_analytics(
            [],
            language_model=self.language_model,
            tool_display_names=self.tool_display_names,
        )

        assert debug_info_manager.get()["tools"] == tools

    @pytest.mark.ai
    def test_add_analytics__strips_tool_info__to_attribution_fields_only(
        self, debug_info_manager: DebugInfoManager
    ) -> None:
        """
        Purpose: Verify every analytics tool entry keeps only attribution fields,
        including whether it is a sub-agent or MCP tool.
        Why this matters: Query/filter/timing payloads must not enter the
        ROI/usage analytics envelope for any tool.
        Setup summary: Seed InternalSearch and WebSearch with full debug info;
        call add_analytics; assert both analytics entries are reduced to
        attribution fields only.
        """
        debug_info_manager.debug_info["tools"] = [
            {
                "name": "InternalSearch",
                "info": {
                    "chatOnly": False,
                    "is_forced": True,
                    "contentIds": None,
                    "is_exclusive": False,
                    "is_sub_agent": True,
                    "searchStrings": ["meaning of the character o umlaut"],
                    "loop_iteration": 0,
                    "metadataFilter": {"and": []},
                    "execution_time_s": 0.906,
                },
            },
            {
                "name": "WebSearch",
                "mcp_server": "should-be-dropped",
                "info": {
                    "query": "umlaut",
                    "execution_time_s": 1.2,
                    "is_forced": False,
                    "is_exclusive": True,
                    "loop_iteration": 1,
                },
            },
        ]

        debug_info_manager.add_analytics(
            [],
            language_model=self.language_model,
            tool_display_names=self.tool_display_names,
        )

        assert debug_info_manager.get()["analytics"]["tools_used"] == [
            {
                "name": "InternalSearch",
                "display_name": "Knowledge Base Search",
                "is_forced": True,
                "is_exclusive": False,
                "is_sub_agent": True,
                "loop_iteration": 0,
            },
            {
                "name": "WebSearch",
                "display_name": "Web Search",
                "is_forced": False,
                "is_exclusive": True,
                "is_mcp": True,
                "loop_iteration": 1,
            },
        ]
        assert debug_info_manager.get()["analytics"]["subagent_names_used"] == [
            {"name": "InternalSearch", "display_name": "Knowledge Base Search"}
        ]
        assert debug_info_manager.get()["analytics"]["mcp_tool_names_used"] == [
            {"name": "WebSearch", "display_name": "Web Search"}
        ]

    @pytest.mark.ai
    def test_add_analytics__leaves_full_tool_info__in_top_level_tools(
        self, debug_info_manager: DebugInfoManager
    ) -> None:
        """
        Purpose: Verify stripping for analytics does not mutate top-level tools.
        Why this matters: Debug consumers still need full tool payloads.
        Setup summary: Seed rich tool info; call add_analytics; assert top-level
        tools entry is identical to the seeded object.
        """
        tools = [
            {
                "name": "InternalSearch",
                "info": {
                    "searchStrings": ["how to type ö on keyboard"],
                    "is_forced": True,
                    "is_exclusive": False,
                    "loop_iteration": 0,
                    "execution_time_s": 0.906,
                },
            }
        ]
        debug_info_manager.debug_info["tools"] = tools

        debug_info_manager.add_analytics(
            [],
            language_model=self.language_model,
            tool_display_names=self.tool_display_names,
        )

        assert debug_info_manager.get()["tools"] is tools
        assert debug_info_manager.get()["tools"][0]["info"]["searchStrings"] == [
            "how to type ö on keyboard"
        ]
        assert debug_info_manager.get()["tools"][0]["info"]["execution_time_s"] == 0.906
