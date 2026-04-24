# %%
# Example: Streaming chat with references via ResponsesCompleteWithReferences
#
# This demonstrates the Python-side streaming pipeline for the OpenAI Responses API.
# Compared to the Chat Completions variant, the Responses API supports:
#   - Structured reasoning (o-series models)
#   - Built-in instructions field (system prompt separation)
#   - First-class tool definitions via ToolParam
#
# The handler streams tokens directly through the OpenAI proxy, normalises
# citation patterns, emits incremental Unique Message updates, and resolves
# [N] markers to <sup>N</sup> footnotes during streaming via StreamingPatternReplacer.
#
# Sources are serialised using the same JSON format as the history manager's
# transform_chunks_to_string, so multi-turn conversations stay consistent.
import json

from openai.types.responses.tool import CodeInterpreter

from unique_toolkit import (
    LanguageModelName,
)

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.service import OpenAICodeInterpreterTool
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.config import OpenAICodeInterpreterConfig
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.framework_utilities.openai.streaming.pipeline import (
    ResponsesCompleteWithReferences,
    ResponsesStreamEventRouter,
)
from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    NORMALIZATION_MAX_MATCH_LENGTH,
    NORMALIZATION_PATTERNS,
    StreamingPatternReplacer,
    StreamingReplacerProtocol,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses import (
    ResponsesCodeInterpreterHandler,
    ResponsesCompletedHandler,
    ResponsesTextDeltaHandler,
    ResponsesToolCallHandler,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelUserMessage,
)

settings = UniqueSettings.from_env_auto_with_sdk_init()

for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
    # Build per-event settings that include auth + chat context from the event.
    # from_chat_event populates ChatContext (chat_id, last_assistant_message_id, …)
    # while UniqueApp / UniqueApi read their credentials from the already-loaded env.
    # (get_event_generator only updates auth via update_from_event, not chat.)
    event_settings = UniqueSettings.from_chat_event(event)

    # --- Build knowledge-base chunks (normally retrieved via KnowledgeBaseService) ---
    chunks = [
        ContentChunk(
            text="Unique is a company that provides the platform for AI-powered solutions.",
            order=0,
            chunk_id="chunk_id_0",
            key="key_0",
            title="About Unique",
            start_page=1,
            end_page=1,
            url="https://www.unique.ai",
            id="id_0",
        ),
        ContentChunk(
            text=(
                "Unique is your Responsible AI Partner, with extensive experience "
                "in implementing AI solutions for enterprise clients in financial services."
            ),
            order=1,
            chunk_id="chunk_id_1",
            key="key_1",
            title="Unique – Financial Services",
            start_page=1,
            end_page=1,
            url="https://www.unique.ai/financial-services",
            id="id_1",
        ),
    ]

    # --- Serialise sources the same way as the history manager --------------
    # transform_chunks_to_string produces:
    #   [{"source_number": N, "content_id": "...", "content": "..."}, ...]
    # All chunks are attached as references unconditionally after the stream,
    # so citation markers in the model output are stripped automatically.
    def to_source_json(chunks: list[ContentChunk], start: int = 1) -> str:
        sources = [
            {"source_number": start + i, "content_id": chunk.id, "content": chunk.text}
            for i, chunk in enumerate(chunks)
        ]
        return json.dumps(sources, ensure_ascii=False)

    reference_guidelines = """
    Whenever you use information from a source, cite it inline using its source_number
    in the format '[source<source_number>]'.

    Example:
    - Unique is an AI company [source1] that focuses on financial services [source2].
    """

    messages = LanguageModelMessages(
        [
            LanguageModelUserMessage(
                content=(
                    f"<Sources>\n{to_source_json(chunks)}\n</Sources>\n\n"
                    f"User question: {event.payload.user_message.text}"
                )
            )
        ]
    )

    # --- Build handlers and stream event router -----------------------------
    replacers: list[StreamingReplacerProtocol] = [
        StreamingPatternReplacer(
            replacements=NORMALIZATION_PATTERNS,
            max_match_length=NORMALIZATION_MAX_MATCH_LENGTH,
        )
    ]

    text_handler = ResponsesTextDeltaHandler(
        replacers=replacers,
    )

    tool_call_handler = ResponsesToolCallHandler()

    completed_handler = ResponsesCompletedHandler()

    router = ResponsesStreamEventRouter(
        text_handler=text_handler,
        tool_call_handler=tool_call_handler,
        completed_handler=completed_handler,
        code_interpreter_handler=ResponsesCodeInterpreterHandler(),
    )

    # --- Stream via the Responses API orchestrator --------------------------
    # ResponsesCompleteWithReferences handles:
    #   • Live token emission to the Unique platform (users see text stream in)
    #   • Citation normalisation ("source0" → "[0]") across chunk boundaries
    #   • Citation normalisation during streaming (StreamingPatternReplacer)
    #
    # The `instructions` parameter maps to the Responses API's top-level system
    # prompt field, keeping it separate from the conversation input.
    handler = ResponsesCompleteWithReferences(
        event_settings,
        router=router,
    )

    code_interpreter_tool = OpenAICodeInterpreterTool(
        config=OpenAICodeInterpreterConfig(
            use_auto_container=True,
        ),
        container_id=None,
        company_id=event_settings.authcontext.get_confidential_company_id()
    )

    result = handler.complete_with_references(
        model_name=LanguageModelName.AZURE_GPT_4o_2024_1120,
        messages=messages,
        content_chunks=chunks,
        temperature=0.0,
        instructions=f"You are a helpful assistant.\n{reference_guidelines}",
        tools=[code_interpreter_tool.tool_description()]
            
    )

    # result.message.content  → final text with <sup>N</sup> footnotes
    # result.message.references → list[ContentReference] objects
    print(result.message.content)
    for ref in result.message.references or []:
        print(ref)
