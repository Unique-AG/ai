# %%
# Example: Streaming chat with references via PipelineChatCompletionsStreamingHandler
#
# This demonstrates the Python-side streaming pipeline for the Chat Completions API.
# Tokens stream directly through the OpenAI proxy to the client, which:
#   - Normalises model-emitted citation patterns (e.g. "[source0]" → "[0]") live
#   - Emits incremental Unique Message updates so the user sees text appear word-by-word
#   - Resolves [N] markers to <sup>N</sup> footnotes and attaches ContentReference objects
#     at flush time via the ReferenceResolutionReplacer (no separate post-processing step)
#
# Sources are serialised using the same JSON format as the history manager's
# transform_chunks_to_string, so multi-turn conversations stay consistent.
import json

from unique_toolkit import (
    LanguageModelName,
)
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.framework_utilities.openai.streaming.pipeline import (
    PipelineChatCompletionsStreamingHandler,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelSystemMessage,
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

    messages: LanguageModelMessages = LanguageModelMessages(
        [
            LanguageModelSystemMessage(
                content=f"You are a helpful assistant.\n{reference_guidelines}"
            ),
            LanguageModelUserMessage(
                content=(
                    f"<Sources>\n{to_source_json(chunks)}\n</Sources>\n\n"
                    f"User question: {event.payload.user_message.text}"
                )
            ),
        ]
    )

    # --- Stream via the Chat Completions pipeline ---------------------------
    # PipelineChatCompletionsStreamingHandler handles:
    #   • Live token emission to the Unique platform (users see text stream in)
    #   • Citation normalisation ("source0" → "[0]") across chunk boundaries
    #   • Reference resolution at flush time (ReferenceResolutionReplacer)
    handler = PipelineChatCompletionsStreamingHandler(
        event_settings,
        resolve_references=True,  # attach ContentReferences + render <sup> footnotes
        send_every_n_events=3,    # emit a platform update every 3 chunks (throttle)
    )

    result = handler.complete_with_references(
        messages=messages,
        model_name=LanguageModelName.AZURE_GPT_4o_2024_1120,
        content_chunks=chunks,
        temperature=0.0,
    )

    # result.message.content  → final text with <sup>N</sup> footnotes
    # result.message.references → list[ContentReference] objects
    print(result.message.content)
    for ref in result.message.references or []:
        print(ref)
