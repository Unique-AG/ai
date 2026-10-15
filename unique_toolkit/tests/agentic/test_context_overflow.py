from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_toolkit.agentic.history_manager.context_overflow import (
    WITHHELD_TOOL_RESULT_NOTICE,
    is_context_window_exceeded_error,
    provider_context_window,
    provider_count_trigger_tokens,
    provider_input_target,
    supports_provider_token_count,
)
from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
from unique_toolkit.agentic.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelTokenLimits,
    LanguageModelToolMessage,
)
from unique_toolkit.language_model.settings import ModelFamily


class ContextWindowExceededError(Exception):
    pass


@pytest.mark.ai
@pytest.mark.parametrize(
    "exc",
    [
        Exception("prompt is too long: 1012345 tokens > 1000000 maximum"),
        Exception("Error code: 400 - {'code': 'context_length_exceeded'}"),
        Exception("This model's maximum context length is 128000 tokens."),
        Exception("Input is too long for requested model."),
        Exception(
            "The input token count (1200000) exceeds the maximum number of tokens allowed (1048576)."
        ),
        ContextWindowExceededError("litellm.BadRequestError"),
        Exception("TokenLimitExceeded"),
        Exception(
            "Internal server error\n(Original error) 400: litellm.BadRequestError: "
            "OpenAIException - litellm.ContextWindowExceededError: "
            "litellm.BadRequestError: ContextWindowExceededError: Hosted_vllmException"
        ),
    ],
)
def test_is_context_window_exceeded_error__detects_provider_overflow_AI(
    exc: Exception,
) -> None:
    """
    Purpose: Provider context-overflow rejections are recognised.
    Why this matters: Unrecognised overflows crash the chat turn instead of recovering (UN-27401).
    Setup summary: Anthropic, OpenAI, Bedrock, Gemini and LiteLLM style errors -> True.
    """
    assert is_context_window_exceeded_error(exc)


@pytest.mark.ai
@pytest.mark.parametrize(
    "exc",
    [
        Exception("Rate limit reached for requests"),
        Exception(
            "Failed after 3 attempts: Internal server error\n(Original error) "
            "rate_limit_exceeded: Your requests to gpt-4o have exceeded rate limit."
        ),
        Exception("Internal server error"),
        TimeoutError("Request timed out"),
    ],
)
def test_is_context_window_exceeded_error__ignores_other_errors_AI(
    exc: Exception,
) -> None:
    """
    Purpose: Unrelated LLM errors are not treated as context overflow.
    Why this matters: Retrying them with withheld tool results would silently drop data.
    Setup summary: Rate-limit, server and timeout errors -> False.
    """
    assert not is_context_window_exceeded_error(exc)


def _chunk(chunk_id: str) -> ContentChunk:
    return ContentChunk(id="cont_1", chunk_id=chunk_id, text=f"text {chunk_id}")


def _history_manager(reference_manager: ReferenceManager) -> HistoryManager:
    hm = HistoryManager.__new__(HistoryManager)
    hm._logger = MagicMock()
    hm._loop_history = []
    hm._reference_manager = reference_manager
    hm._collected_tool_response_image_urls = []
    hm._source_offset_initialized = True
    hm._initial_source_offset = 0
    hm._source_enumerator = 0
    return hm


@pytest.mark.ai
def test_withhold_latest_tool_call_results__replaces_only_latest_batch_AI() -> None:
    """
    Purpose: Only the most recent tool-call batch is withheld, and its chunks leave the reference manager.
    Why this matters: Earlier results and their source numbers must survive the recovery.
    Setup summary: Batch 1 (one call, one chunk), batch 2 (two parallel calls, chunk + plain text)
        -> batch 2 replaced with the notice, only batch 1's chunk kept.
    """
    reference_manager = ReferenceManager()
    kept_chunk, withheld_chunk = _chunk("kept"), _chunk("withheld")
    reference_manager.extract_referenceable_chunks(
        [
            ToolCallResponse(id="call_1", name="search", content_chunks=[kept_chunk]),
            ToolCallResponse(
                id="call_2", name="search_emails", content_chunks=[withheld_chunk]
            ),
        ]
    )
    hm = _history_manager(reference_manager)
    hm._collected_tool_response_image_urls = [
        ("data:image/png;base64,a2VwdA==", "call_1"),
        ("data:image/png;base64,d2l0aGhlbGQ=", "call_2"),
    ]
    hm._loop_history = [
        LanguageModelAssistantMessage.from_functions(
            tool_calls=[LanguageModelFunction(id="call_1", name="search")]
        ),
        LanguageModelToolMessage(tool_call_id="call_1", name="search", content="r1"),
        LanguageModelAssistantMessage.from_functions(
            tool_calls=[
                LanguageModelFunction(id="call_2", name="search_emails"),
                LanguageModelFunction(id="call_3", name="search_emails"),
            ]
        ),
        LanguageModelToolMessage(
            tool_call_id="call_2", name="search_emails", content="big"
        ),
        LanguageModelToolMessage(
            tool_call_id="call_3", name="search_emails", content="bigger"
        ),
    ]

    withheld = hm.withhold_latest_tool_call_results(WITHHELD_TOOL_RESULT_NOTICE)

    assert withheld == 2
    contents = [
        m.content for m in hm._loop_history if isinstance(m, LanguageModelToolMessage)
    ]
    assert contents == ["r1", WITHHELD_TOOL_RESULT_NOTICE, WITHHELD_TOOL_RESULT_NOTICE]
    assert reference_manager.get_chunks() == [kept_chunk]
    assert reference_manager.get_chunks_of_tool("call_2") == []
    assert reference_manager.get_chunks_of_tool("call_1") == [kept_chunk]
    assert hm._collected_tool_response_image_urls == [
        ("data:image/png;base64,a2VwdA==", "call_1")
    ]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_recompose_history__preserves_tool_images_until_next_tool_batch_AI() -> (
    None
):
    """
    Purpose: Tool result images survive recomposition on the same turn and reset on the next tool batch.
    Why this matters: Preflight or overflow recomposition calls get_history_for_model_call more than once.
    Setup summary: One tool batch with an image, two get_history_for_model_call calls -> both receive the image.
    """
    hm = _history_manager(ReferenceManager())
    hm._token_reducer = MagicMock()
    hm._token_reducer.get_history_for_model_call = AsyncMock(return_value=MagicMock())
    hm.add_tool_call_results(
        [
            ToolCallResponse(
                id="call_1",
                name="render_chart",
                content="chart",
                image_data_urls=["data:image/png;base64,Y2hhcnQ="],
            )
        ]
    )

    async def _noop_clean(text: str) -> str:
        return text

    await hm.get_history_for_model_call("q", "q", "sys", _noop_clean)
    await hm.get_history_for_model_call("q", "q", "sys", _noop_clean)

    first_call_images = hm._token_reducer.get_history_for_model_call.await_args_list[
        0
    ].kwargs["image_data_urls_from_tools"]
    second_call_images = hm._token_reducer.get_history_for_model_call.await_args_list[
        1
    ].kwargs["image_data_urls_from_tools"]
    assert first_call_images == [("data:image/png;base64,Y2hhcnQ=", "call_1")]
    assert second_call_images == [("data:image/png;base64,Y2hhcnQ=", "call_1")]

    hm.add_tool_call_results(
        [ToolCallResponse(id="call_2", name="search", content="text only")]
    )
    await hm.get_history_for_model_call("q", "q", "sys", _noop_clean)
    third_call_images = hm._token_reducer.get_history_for_model_call.await_args_list[
        2
    ].kwargs["image_data_urls_from_tools"]
    assert third_call_images == []


@pytest.mark.ai
def test_withhold_latest_tool_call_results__returns_zero_without_tool_calls_AI() -> (
    None
):
    """
    Purpose: Nothing is withheld when the loop has no tool calls yet.
    Why this matters: The orchestrator re-raises the overflow in that case instead of retrying blindly.
    Setup summary: Empty loop history -> 0.
    """
    hm = _history_manager(ReferenceManager())

    assert hm.withhold_latest_tool_call_results(WITHHELD_TOOL_RESULT_NOTICE) == 0


@pytest.mark.ai
def test_provider_budget__uses_real_claude_window_and_output_reserve_AI() -> None:
    """
    Purpose: Base provider decisions on Claude's real window, not its corrected local limit.
    Why this matters: OpenAI-tokenizer safety corrections must not be applied to provider counts.
    Setup summary: Sonnet 5.5 corrected to 769k locally, 10k output reserve -> 940k input target.
    """
    model = LanguageModelInfo(
        name="litellm:claude-sonnet-5-5",
        family=ModelFamily.ANTHROPIC,
        version="claude-sonnet-5-5",
        token_limits=LanguageModelTokenLimits(
            token_limit_input=769_230,
            token_limit_output=98_461,
        ),
    )

    assert provider_context_window(model) == 1_000_000
    assert provider_input_target(model, None) == 940_000
    assert provider_input_target(model, {"max_tokens": 20_000}) == 930_000

    model.version = ""
    assert provider_context_window(model) == 1_000_000

    opus_47_without_version = LanguageModelInfo(
        name="litellm:anthropic-claude-opus-4-7",
        family=ModelFamily.ANTHROPIC,
        version="",
        token_limits=LanguageModelTokenLimits(
            token_limit_input=769_230,
            token_limit_output=98_461,
        ),
    )
    assert provider_context_window(opus_47_without_version) == 1_000_000

    sonnet_46 = LanguageModelInfo(
        name="litellm:vertex-claude-sonnet-4-6",
        family=ModelFamily.ANTHROPIC,
        version="claude-sonnet-4-6",
        token_limits=LanguageModelTokenLimits(
            token_limit_input=200_000,
            token_limit_output=64_000,
        ),
    )
    assert provider_context_window(sonnet_46) == 200_000
    assert supports_provider_token_count(sonnet_46)

    gpt_model = LanguageModelInfo(
        name="AZURE_GPT_4o_2024_1120",
        family=ModelFamily.OPENAI,
        version="2024-11-20",
        token_limits=LanguageModelTokenLimits(
            token_limit_input=128_000,
            token_limit_output=16_384,
        ),
    )
    assert not supports_provider_token_count(gpt_model)


@pytest.mark.ai
def test_provider_budget__triggers_before_local_reducer_ceiling_AI() -> None:
    """
    Purpose: Invoke provider counting before the approximate reducer reaches its own ceiling.
    Why this matters: A local undercount cannot skip the authoritative preflight check.
    Setup summary: Approximate Claude tokenizer and 600k local ceiling -> trigger at 570k.
    """
    model = LanguageModelInfo(
        name="litellm:claude-sonnet-5-5",
        family=ModelFamily.ANTHROPIC,
        version="claude-sonnet-5-5",
        token_limits=LanguageModelTokenLimits(
            token_limit_input=769_230,
            token_limit_output=98_461,
        ),
    )

    assert (
        provider_count_trigger_tokens(model, effective_local_limit=600_000) == 570_000
    )
