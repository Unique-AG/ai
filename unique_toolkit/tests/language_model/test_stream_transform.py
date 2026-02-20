"""Tests for stream_transform.py and stream_complete_with_references()."""

from types import TracebackType
from unittest.mock import MagicMock, patch

import pytest

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.functions import (
    stream_complete_with_references_openai,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelFunctionCall,
    LanguageModelMessages,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)
from unique_toolkit.language_model.stream_transform import (
    NormalizationTransform,
    ReferenceInjectionTransform,
    TextTransformPipeline,
)


def _make_chunk(id: str, key: str, title: str) -> ContentChunk:
    return ContentChunk(
        id=id,
        chunk_id=None,
        key=key,
        title=title,
        text="content",
        start_page=1,
        end_page=1,
        order=0,
        object="search_result",
        url=None,
        internally_stored_at=None,
    )


# ---------------------------------------------------------------------------
# 1. ReferenceInjectionTransform.finalize() — happy path
# ---------------------------------------------------------------------------


def test_reference_injection_resolves_references():
    chunk1 = _make_chunk("id1", "key1", "Title One")
    chunk2 = _make_chunk("id2", "key2", "Title Two")
    transform = ReferenceInjectionTransform([chunk1, chunk2])

    text, refs = transform.finalize("Hello [1] and [2] world")

    assert "<sup>1</sup>" in text
    assert "<sup>2</sup>" in text
    assert len(refs) == 2
    names = {r.name for r in refs}
    assert "Title One" in names
    assert "Title Two" in names


# ---------------------------------------------------------------------------
# 2. Hallucinated reference [99] with only 1 chunk → removed, not in refs
# ---------------------------------------------------------------------------


def test_reference_injection_drops_hallucinated_reference():
    chunk1 = _make_chunk("id1", "key1", "Title One")
    transform = ReferenceInjectionTransform([chunk1])

    text, refs = transform.finalize("Hello [99] world")

    assert "[99]" not in text
    assert len(refs) == 0


# ---------------------------------------------------------------------------
# 3. NormalizationTransform.finalize() passthrough
# ---------------------------------------------------------------------------


def test_normalization_transform_passthrough():
    transform = NormalizationTransform()
    input_text = "Hello world [1]"
    text, refs = transform.finalize(input_text)
    assert text == input_text
    assert refs == []


# ---------------------------------------------------------------------------
# 4. TextTransformPipeline.run() chains both transforms correctly
# ---------------------------------------------------------------------------


def test_pipeline_chains_transforms():
    chunk1 = _make_chunk("id1", "key1", "Source A")
    pipeline = (
        TextTransformPipeline()
        .add(NormalizationTransform())
        .add(ReferenceInjectionTransform([chunk1]))
    )

    text, refs = pipeline.run("See [1] for details")

    assert "<sup>1</sup>" in text
    assert "[1]" not in text
    assert len(refs) == 1
    assert refs[0].name == "Source A"


# ---------------------------------------------------------------------------
# Helpers for async mocking
# ---------------------------------------------------------------------------


class FakeDelta:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeChoice:
    def __init__(self, delta):
        self.delta = delta


class FakeChunk:
    def __init__(self, content=None, tool_calls=None):
        self.choices = [FakeChoice(FakeDelta(content=content, tool_calls=tool_calls))]


class FakeStream:
    """Fake async context manager wrapping an async iterator of chunks."""

    def __init__(self, chunks):
        self._chunks = chunks

    async def __aenter__(self):
        return self._aiter()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass

    async def _aiter(self):
        for chunk in self._chunks:
            yield chunk

    def __aiter__(self):
        return self._aiter()


class FakeStreamCtx:
    """Context manager that returns an async-iterable stream."""

    def __init__(self, chunks):
        self._stream = FakeStream(chunks)

    async def __aenter__(self):
        return self._stream

    async def __aexit__(self, *args) -> None:
        pass


# ---------------------------------------------------------------------------
# 5. stream_complete_with_references() — text streaming with references
# ---------------------------------------------------------------------------


@patch(
    "unique_toolkit.framework_utilities.openai.client.get_async_openai_client",
    create=True,
)
@pytest.mark.asyncio
async def test_stream_complete_with_references_text(mock_get_client):
    chunk1 = _make_chunk("id1", "key1", "My Source")

    chunks = [
        FakeChunk(content="Hello "),
        FakeChunk(content="[1] world"),
    ]

    fake_client = MagicMock()
    fake_client.chat.completions.stream.return_value = FakeStreamCtx(chunks)
    mock_get_client.return_value = fake_client

    result = await stream_complete_with_references_openai(
        messages=[{"role": "user", "content": "hi"}],
        model_name="test-model",
        content_chunks=[chunk1],
    )

    assert "<sup>1</sup>" in result.message.text
    assert len(result.message.references) == 1
    assert result.message.references[0].name == "My Source"
    assert result.message.original_text == "Hello [1] world"
    assert result.tool_calls is None


# ---------------------------------------------------------------------------
# 6. Tool call streaming: mocked deltas → result.tool_calls populated
# ---------------------------------------------------------------------------


class FakeToolCallFunction:
    def __init__(self, name=None, arguments=None):
        self.name = name
        self.arguments = arguments


class FakeToolCallDelta:
    def __init__(self, index, id=None, name=None, arguments=None):
        self.index = index
        self.id = id
        self.function = FakeToolCallFunction(name=name, arguments=arguments)


class FakeDeltaWithToolCalls:
    def __init__(self, tool_calls):
        self.content = None
        self.tool_calls = tool_calls


class FakeChunkWithToolCalls:
    def __init__(self, tool_calls):
        self.choices = [FakeChoice(FakeDeltaWithToolCalls(tool_calls=tool_calls))]


@patch(
    "unique_toolkit.framework_utilities.openai.client.get_async_openai_client",
    create=True,
)
@pytest.mark.asyncio
async def test_stream_complete_tool_calls(mock_get_client):
    chunks = [
        FakeChunkWithToolCalls(
            [
                FakeToolCallDelta(
                    index=0, id="call_abc", name="get_weather", arguments=""
                ),
            ]
        ),
        FakeChunkWithToolCalls(
            [
                FakeToolCallDelta(
                    index=0, id=None, name=None, arguments='{"location": "Paris"}'
                ),
            ]
        ),
    ]

    fake_client = MagicMock()
    fake_client.chat.completions.stream.return_value = FakeStreamCtx(chunks)
    mock_get_client.return_value = fake_client

    result = await stream_complete_with_references_openai(
        messages=[{"role": "user", "content": "weather?"}],
        model_name="test-model",
    )

    assert result.tool_calls is not None
    assert len(result.tool_calls) == 1
    tc = result.tool_calls[0]
    assert tc.name == "get_weather"
    assert tc.arguments == {"location": "Paris"}


# ---------------------------------------------------------------------------
# 7. Pre-normalized reference formats — full preprocessing path
# ---------------------------------------------------------------------------


def test_reference_injection_handles_prenormalized_formats():
    chunk1 = _make_chunk("id1", "key1", "Revenue Report")
    chunk2 = _make_chunk("id2", "key2", "Budget Doc")
    transform = ReferenceInjectionTransform([chunk1, chunk2])

    text, refs = transform.finalize("revenue grew source 1 and source_2")

    assert "<sup>1</sup>" in text
    assert "<sup>2</sup>" in text
    assert len(refs) == 2


# ---------------------------------------------------------------------------
# 8. start_text is correctly prepended and participates in reference injection
# ---------------------------------------------------------------------------


@patch(
    "unique_toolkit.framework_utilities.openai.client.get_async_openai_client",
    create=True,
)
@pytest.mark.asyncio
async def test_stream_complete_start_text_prepended(mock_get_client):
    chunk1 = _make_chunk("id1", "key1", "Intro Source")

    # start_text contains a reference, streamed text adds more
    chunks = [FakeChunk(content=" more text")]

    fake_client = MagicMock()
    fake_client.chat.completions.stream.return_value = FakeStreamCtx(chunks)
    mock_get_client.return_value = fake_client

    result = await stream_complete_with_references_openai(
        messages=[{"role": "user", "content": "hi"}],
        model_name="test-model",
        content_chunks=[chunk1],
        start_text="Preamble [1]",
    )

    assert result.message.original_text == "Preamble [1] more text"
    assert "<sup>1</sup>" in result.message.text
    assert len(result.message.references) == 1


# ---------------------------------------------------------------------------
# 9. LanguageModelMessages input type (model_dump branch)
# ---------------------------------------------------------------------------


@patch(
    "unique_toolkit.framework_utilities.openai.client.get_async_openai_client",
    create=True,
)
@pytest.mark.asyncio
async def test_stream_complete_language_model_messages_input(mock_get_client):
    chunks = [FakeChunk(content="answer")]

    fake_client = MagicMock()
    fake_client.chat.completions.stream.return_value = FakeStreamCtx(chunks)
    mock_get_client.return_value = fake_client

    messages = LanguageModelMessages([LanguageModelUserMessage(content="hello")])

    result = await stream_complete_with_references_openai(
        messages=messages,
        model_name="test-model",
    )

    assert result.message.text == "answer"
    # Verify model_dump was used: messages list was passed to the client
    call_kwargs = fake_client.chat.completions.stream.call_args[1]
    assert isinstance(call_kwargs["messages"], list)
    assert call_kwargs["messages"][0]["role"] == "user"


# ---------------------------------------------------------------------------
# 9b. LanguageModelMessages with tool_calls / tool_call_id → snake_case for OpenAI
# ---------------------------------------------------------------------------


@patch(
    "unique_toolkit.framework_utilities.openai.client.get_async_openai_client",
    create=True,
)
@pytest.mark.asyncio
async def test_stream_complete_language_model_messages_snake_case_tool_fields(
    mock_get_client,
):
    """LanguageModelMessages must be serialized with by_alias=False so OpenAI receives tool_calls and tool_call_id (snake_case), not camelCase."""
    chunks = [FakeChunk(content="ok")]

    fake_client = MagicMock()
    fake_client.chat.completions.stream.return_value = FakeStreamCtx(chunks)
    mock_get_client.return_value = fake_client

    tool_call_id = "call_abc123"
    messages = LanguageModelMessages(
        [
            LanguageModelUserMessage(content="run search"),
            LanguageModelAssistantMessage(
                content="",
                tool_calls=[
                    LanguageModelFunctionCall(
                        id=tool_call_id,
                        type="function",
                        function=LanguageModelFunction(
                            id=tool_call_id,
                            name="search",
                            arguments={"query": "x"},
                        ),
                    )
                ],
            ),
            LanguageModelToolMessage(
                name="search",
                tool_call_id=tool_call_id,
                content='{"results": []}',
            ),
        ]
    )

    await stream_complete_with_references_openai(
        messages=messages,
        model_name="test-model",
    )

    call_kwargs = fake_client.chat.completions.stream.call_args[1]
    sent = call_kwargs["messages"]

    # OpenAI expects snake_case; camelCase would drop tool info
    assert sent[0]["role"] == "user"
    assert "tool_calls" in sent[1]
    assert "toolCalls" not in sent[1]
    assert sent[1]["tool_calls"][0]["function"]["name"] == "search"
    assert "tool_call_id" in sent[2]
    assert "toolCallId" not in sent[2]
    assert sent[2]["tool_call_id"] == tool_call_id


# ---------------------------------------------------------------------------
# 10. process_delta is called once per streamed chunk
# ---------------------------------------------------------------------------


def test_pipeline_feed_delta_called_per_chunk():
    calls = []

    class SpyTransform:
        def process_delta(self, delta: str) -> None:
            calls.append(delta)

        def finalize(self, text: str):
            return text, []

    pipeline = TextTransformPipeline()
    pipeline.add(SpyTransform())

    pipeline.feed_delta("foo")
    pipeline.feed_delta("bar")

    assert calls == ["foo", "bar"]


# ---------------------------------------------------------------------------
# 11. Tool definitions conversion (LanguageModelToolDescription + LanguageModelTool)
# ---------------------------------------------------------------------------


@patch(
    "unique_toolkit.framework_utilities.openai.client.get_async_openai_client",
    create=True,
)
@pytest.mark.asyncio
async def test_stream_complete_tool_definitions_converted(mock_get_client):
    from unique_toolkit.language_model.schemas import (
        LanguageModelTool,
        LanguageModelToolDescription,
        LanguageModelToolParameterProperty,
        LanguageModelToolParameters,
    )

    chunks: list = []  # no content, just verify tool definitions were forwarded

    fake_client = MagicMock()
    fake_client.chat.completions.stream.return_value = FakeStreamCtx(chunks)
    mock_get_client.return_value = fake_client

    tool_desc = LanguageModelToolDescription(
        name="search",
        description="Search docs",
        parameters={"type": "object", "properties": {}, "required": []},
    )
    tool_raw = LanguageModelTool(
        name="lookup",
        description="Lookup a value",
        parameters=LanguageModelToolParameters(
            type="object",
            properties={
                "key": LanguageModelToolParameterProperty(
                    type="string", description="key"
                )
            },
            required=["key"],
        ),
    )

    await stream_complete_with_references_openai(
        messages=[{"role": "user", "content": "hi"}],
        model_name="test-model",
        tools=[tool_desc, tool_raw],
    )

    call_kwargs = fake_client.chat.completions.stream.call_args[1]
    sent_tools = call_kwargs["tools"]
    assert len(sent_tools) == 2
    tool_names = {t["function"]["name"] for t in sent_tools}
    assert "search" in tool_names
    assert "lookup" in tool_names
