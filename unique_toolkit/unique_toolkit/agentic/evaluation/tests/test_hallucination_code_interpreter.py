"""Tests for hallucination evaluation with code interpreter (UN-18759).

Relates to BugBash UN-18562.

Scenario
--------
When code interpreter is combined with a search tool (which triggers the hallucination
check), the LLM's final response legitimately describes computed results (charts, stats)
and does NOT include sourceN citations — because it is reporting computation, not document
retrieval.

Before fix:
  context_text_from_stream_response() → [] (no sourceN found)
  _get_msgs() → has_context=False → "no sources" judge prompt
  Judge → HIGH hallucination (false positive)

After fix:
  code_execution_contexts extracted from code_interpreter_calls
  _get_msgs() → has_context=True, has_code_execution=True → grounded judge prompt
  Judge → low/medium (correct)
"""

from typing import List

import pytest
from openai.types.responses import ResponseCodeInterpreterToolCall
from openai.types.responses.response_code_interpreter_tool_call import OutputLogs

from unique_toolkit.agentic.evaluation.hallucination.constants import (
    HallucinationConfig,
    SourceSelectionMode,
)
from unique_toolkit.agentic.evaluation.hallucination.hallucination_evaluation import (
    _extract_code_execution_contexts,
)
from unique_toolkit.agentic.evaluation.hallucination.utils import (
    _get_msgs,
    context_text_from_stream_response,
)
from unique_toolkit.agentic.evaluation.schemas import (
    CodeExecutionContext,
    EvaluationMetricInput,
)
from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.schemas import (
    LanguageModelStreamResponse,
    ResponsesLanguageModelStreamResponse,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def kb_chunks() -> List[ContentChunk]:
    """KB chunks returned by internal search before code interpreter ran."""
    return [
        ContentChunk(
            id="doc_001",
            chunk_id="chunk_001",
            text="Revenue data for Q1 2024: Jan=42000, Feb=48000, Mar=51000",
            order=0,
        ),
        ContentChunk(
            id="doc_001",
            chunk_id="chunk_002",
            text="Expense data for Q1 2024: Jan=31000, Feb=33000, Mar=35000",
            order=1,
        ),
    ]


@pytest.fixture
def ci_call_with_stdout() -> ResponseCodeInterpreterToolCall:
    """A code interpreter call that produced a chart with stdout output."""
    return ResponseCodeInterpreterToolCall(
        id="call_abc123",
        container_id="container_xyz",
        status="completed",
        type="code_interpreter_call",
        code=(
            "import pandas as pd\n"
            "import matplotlib.pyplot as plt\n"
            "df = pd.DataFrame({\n"
            "    'Month': ['Jan', 'Feb', 'Mar'],\n"
            "    'Revenue': [42000, 48000, 51000],\n"
            "    'Expenses': [31000, 33000, 35000],\n"
            "})\n"
            "df['Profit'] = df['Revenue'] - df['Expenses']\n"
            "df.plot(x='Month', y=['Revenue', 'Expenses', 'Profit'])\n"
            "plt.savefig('/mnt/data/revenue_chart.png')\n"
            "print(df.to_string())\n"
        ),
        outputs=[
            OutputLogs(
                type="logs",
                logs=(
                    "  Month  Revenue  Expenses  Profit\n"
                    "0   Jan    42000     31000   11000\n"
                    "1   Feb    48000     33000   15000\n"
                    "2   Mar    51000     35000   16000\n"
                ),
            )
        ],
    )


@pytest.fixture
def ci_call_no_stdout() -> ResponseCodeInterpreterToolCall:
    """A code interpreter call where outputs are not available (fence FF off)."""
    return ResponseCodeInterpreterToolCall(
        id="call_def456",
        container_id="container_xyz",
        status="completed",
        type="code_interpreter_call",
        code=(
            "df.plot(x='Month', y=['Revenue'])\n"
            "plt.savefig('/mnt/data/revenue_chart.png')\n"
        ),
        outputs=None,
    )


def _make_ci_response(
    message_text: str,
    ci_call: ResponseCodeInterpreterToolCall,
    original_text: str | None = None,
) -> ResponsesLanguageModelStreamResponse:
    """Build a ResponsesLanguageModelStreamResponse with a code interpreter call."""
    msg = ChatMessage(
        id="msg_ci_001",
        chat_id="chat_001",
        previous_message_id=None,
        role=ChatMessageRole.ASSISTANT,
        text=message_text,
        original_text=original_text or message_text,
        references=[],
    )
    return ResponsesLanguageModelStreamResponse(
        message=msg,
        output=[ci_call],
    )


# ---------------------------------------------------------------------------
# Bug reproduction: context extraction
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_context_texts__empty__when_ci_response_has_no_source_citations(
    kb_chunks: List[ContentChunk],
    ci_call_with_stdout: ResponseCodeInterpreterToolCall,
) -> None:
    """
    Purpose: Confirm that context_texts is still empty for a CI response without sourceN
             citations — this is expected and correct. The fix does NOT change this; instead
             it provides code_execution_contexts as the grounding source instead.
    Why this matters: Documents that the existing chunk-selection path is unchanged.
    Setup summary: CI response describing a chart with no sourceN markers in text.
    """
    response = _make_ci_response(
        message_text=(
            "Here's the line chart showing Revenue, Expenses, and Profit by Month.\n\n"
            "X-axis: Months (Jan–Mar)\n"
            "Y-axis: Amount\n"
            "Series: Revenue, Expenses, Profit\n\n"
            "Revenue grew from 42,000 in January to 51,000 in March."
        ),
        ci_call=ci_call_with_stdout,
    )

    context_texts = context_text_from_stream_response(
        response=response,
        selected_chunks=kb_chunks,
        source_selection_mode=SourceSelectionMode.FROM_ORIGINAL_RESPONSE,
    )

    # context_texts is empty — no sourceN citations in the response text.
    # This is intentional: the fix supplies code_execution_contexts separately
    # rather than forcing chunk-selection to work for CI responses.
    assert context_texts == []


@pytest.mark.ai
def test_no_sources_judge_branch__selected__when_context_texts_empty_and_no_ci() -> (
    None
):
    """
    Purpose: Confirm the 'no sources' branch is still used when there is truly nothing
             to ground against (no chunks, no history, no code execution).
    Why this matters: This is the correct behaviour for a genuinely ungrounded response.
                      The fix must NOT change this path.
    Setup summary: has_context=False when context_texts, history, and code_execution are all empty.
    """
    config = HallucinationConfig(enabled=True)

    input_without_context = EvaluationMetricInput(
        input_text="Plot monthly revenue",
        context_texts=[],
        history_messages=[],
        output_text="Revenue grew from 42k to 51k.",
    )

    msgs = _get_msgs(input_without_context, config)
    system_prompt = msgs.root[0].content
    assert isinstance(system_prompt, str)
    assert "NO references were found" in system_prompt
    assert "no sources to support it" in system_prompt


@pytest.mark.ai
def test_grounded_branch__selected__when_code_execution_context_present() -> None:
    """
    Purpose: Verify that code_execution_contexts alone is sufficient to route to the
             grounded judge branch — fixing the false positive for CI-only responses.
    Why this matters: This is the core fix for UN-18759. A CI response with no chunk
                      citations must NOT fall into the 'no sources' penalty branch.
    Setup summary: EvaluationMetricInput with only code_execution_contexts populated.
    """
    config = HallucinationConfig(enabled=True)

    input_with_ci = EvaluationMetricInput(
        input_text="Plot monthly revenue",
        context_texts=[],
        history_messages=[],
        output_text="Revenue grew from 42k to 51k.",
        code_execution_contexts=[
            CodeExecutionContext(
                code="df.plot()\nplt.savefig('/mnt/data/chart.png')",
                stdout="Revenue: 42000, 51000",
            )
        ],
    )

    msgs = _get_msgs(input_with_ci, config)
    system_prompt = msgs.root[0].content
    user_prompt = msgs.root[1].content
    assert isinstance(system_prompt, str)
    assert isinstance(user_prompt, str)

    # Must use the grounded branch
    assert "NO references were found" not in system_prompt
    # Must include code-execution-specific guidance
    assert "code execution" in system_prompt.lower()
    # Code context must appear in the user prompt
    assert "Code Execution" in user_prompt
    assert "df.plot()" in user_prompt
    assert "Revenue: 42000" in user_prompt


@pytest.mark.ai
def test_extract_code_execution_contexts__extracts_code_and_stdout(
    ci_call_with_stdout: ResponseCodeInterpreterToolCall,
) -> None:
    """
    Purpose: Verify _extract_code_execution_contexts pulls code and stdout correctly.
    Why this matters: This is the extraction step in hallucination_evaluation.run().
    Setup summary: ResponsesLanguageModelStreamResponse with one CI call with stdout.
    """
    response = _make_ci_response(
        message_text="Here is the chart.",
        ci_call=ci_call_with_stdout,
    )

    contexts = _extract_code_execution_contexts(response)

    assert len(contexts) == 1
    ctx = contexts[0]
    assert "Revenue" in ctx.code
    assert "/mnt/data/revenue_chart.png" in ctx.code
    assert "42000" in ctx.stdout
    assert "11000" in ctx.stdout


@pytest.mark.ai
def test_extract_code_execution_contexts__code_only__when_outputs_none(
    ci_call_no_stdout: ResponseCodeInterpreterToolCall,
) -> None:
    """
    Purpose: Verify graceful fallback when outputs=None (fence FF is off).
    Why this matters: The fix must still provide code as grounding even without stdout.
    Setup summary: CI call with outputs=None; stdout should be empty string.
    """
    response = _make_ci_response(
        message_text="Here is the chart.",
        ci_call=ci_call_no_stdout,
    )

    contexts = _extract_code_execution_contexts(response)

    assert len(contexts) == 1
    assert contexts[0].code is not None
    assert contexts[0].stdout == ""


@pytest.mark.ai
def test_extract_code_execution_contexts__returns_empty__for_non_responses_api() -> (
    None
):
    """
    Purpose: Verify that the classic completions API path returns no CI contexts.
    Why this matters: The classic LanguageModelStreamResponse has no code_interpreter_calls.
                      The extractor must not crash or return incorrect data.
    Setup summary: Pass a base LanguageModelStreamResponse, expect empty list.
    """
    msg = ChatMessage(
        id="msg_classic",
        chat_id="chat_classic",
        previous_message_id=None,
        role=ChatMessageRole.ASSISTANT,
        text="Some answer.",
        references=[],
    )
    response = LanguageModelStreamResponse(message=msg)

    contexts = _extract_code_execution_contexts(response)

    assert contexts == []


# ---------------------------------------------------------------------------
# get_joined_code_contexts rendering
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_get_joined_code_contexts__renders_code_and_stdout__in_tagged_blocks() -> None:
    """
    Purpose: Verify the rendered output for the judge contains code and stdout correctly.
    Why this matters: The judge receives this as its primary grounding when CI was used.
    Setup summary: Single CodeExecutionContext; assert tagged block structure.
    """
    ctx = CodeExecutionContext(
        code="df.plot()\nplt.savefig('/mnt/data/chart.png')",
        stdout="Revenue: 42000",
    )
    metric_input = EvaluationMetricInput(
        input_text="Plot revenue",
        output_text="Revenue is 42k.",
        code_execution_contexts=[ctx],
    )

    rendered = metric_input.get_joined_code_contexts()

    assert "<code-execution-1>" in rendered
    assert "</code-execution-1>" in rendered
    assert "```python" in rendered
    assert "df.plot()" in rendered
    assert "<stdout>" in rendered
    assert "Revenue: 42000" in rendered


@pytest.mark.ai
def test_get_joined_code_contexts__shows_placeholder__when_stdout_absent() -> None:
    """
    Purpose: Verify a clear placeholder is shown when stdout is empty (fence FF off).
    Why this matters: The judge must know stdout is unavailable, not misread empty as output.
    Setup summary: CodeExecutionContext with stdout=''; assert placeholder text.
    """
    ctx = CodeExecutionContext(code="df.plot()", stdout="")
    metric_input = EvaluationMetricInput(
        input_text="q",
        output_text="o",
        code_execution_contexts=[ctx],
    )

    rendered = metric_input.get_joined_code_contexts()

    assert "no output captured" in rendered


@pytest.mark.ai
def test_get_joined_code_contexts__truncates_long_code_and_stdout() -> None:
    """
    Purpose: Verify truncation prevents overly long code/stdout from blowing context budget.
    Why this matters: Untruncated multi-thousand-line stdout could exceed LLM context limits.
    Setup summary: Very long code and stdout strings; assert truncation markers present.
    """
    long_code = "x = 1\n" * 1000
    long_stdout = "line output\n" * 500

    ctx = CodeExecutionContext(code=long_code, stdout=long_stdout)
    metric_input = EvaluationMetricInput(
        input_text="q",
        output_text="o",
        code_execution_contexts=[ctx],
    )

    rendered = metric_input.get_joined_code_contexts()

    assert "truncated" in rendered


# ---------------------------------------------------------------------------
# Coverage: all five scenarios
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_scenario_a__pure_search_with_citations__existing_logic_unaffected(
    kb_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Confirm that Scenario A (search + source citations) still works
             correctly with the existing logic — fix must not regress this.
    Why this matters: Scenario A is the primary intended use case.
    Setup summary: Response with sourceN citations, FROM_ORIGINAL_RESPONSE mode.
    """
    msg = ChatMessage(
        id="msg_a",
        chat_id="chat_a",
        previous_message_id=None,
        role=ChatMessageRole.ASSISTANT,
        text="Revenue was 42k in January [source0] and 48k in February [source1].",
        original_text="Revenue was 42k in January [source0] and 48k in February [source1].",
        references=[],
    )
    response = LanguageModelStreamResponse(message=msg)

    context_texts = context_text_from_stream_response(
        response=response,
        selected_chunks=kb_chunks,
        source_selection_mode=SourceSelectionMode.FROM_ORIGINAL_RESPONSE,
    )

    # Scenario A: citations present → both chunks extracted → judge has grounding
    assert len(context_texts) == 2
    assert "Revenue data" in context_texts[0]
    assert "Expense data" in context_texts[1]
