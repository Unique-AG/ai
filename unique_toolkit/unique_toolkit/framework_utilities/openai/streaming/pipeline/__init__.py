"""Streaming pipeline primitives (protocols, handlers, pipelines, runners)."""

from __future__ import annotations

from unique_toolkit.framework_utilities.openai.streaming.reference_replacer import (
    ReferenceResolutionReplacer,
)

from .chat_completion_accumulator import (
    ChatCompletionStreamAccumulator,
    iter_chat_completion_chunks_until_tool_calls,
)
from .chat_completion_pipeline import ChatCompletionStreamPipeline
from .chat_completion_sdk_persistence import ChatCompletionSdkPersistence
from .chat_completion_streaming_handler import PipelineChatCompletionsStreamingHandler
from .chat_completion_text_handler import ChatCompletionTextHandler
from .chat_completion_tool_call_handler import ChatCompletionToolCallHandler
from .protocols import (
    ChatCompletionTextHandlerProtocol,
    ChatCompletionToolCallHandlerProtocol,
    ResponsesCodeInterpreterHandlerProtocol,
    ResponsesCompletedHandlerProtocol,
    ResponsesStreamAccumulatorProtocol,
    ResponsesTextDeltaHandlerProtocol,
    ResponsesToolCallHandlerProtocol,
    ResponseStreamPersistenceProtocol,
    ResponseStreamSource,
    StreamAccumulatorProtocol,
    StreamHandlerProtocol,
    StreamPersistenceProtocol,
    StreamSource,
)
from .responses_accumulator import ResponsesStreamAccumulator
from .responses_code_interpreter_handler import ResponsesCodeInterpreterHandler
from .responses_completed_handler import ResponsesCompletedHandler
from .responses_pipeline import ResponsesStreamPipeline
from .responses_sdk_persistence import ResponsesSdkPersistence
from .responses_streaming_handler import PipelineResponsesStreamingHandler
from .responses_text_delta_handler import ResponsesTextDeltaHandler
from .responses_tool_call_handler import ResponsesToolCallHandler
from .run import (
    run_chat_completions_stream_pipeline,
    run_responses_stream_pipeline,
    run_stream_pipeline,
)

__all__ = [
    # --- Pipeline classes ---
    "ChatCompletionStreamPipeline",
    "ResponsesStreamPipeline",
    # --- Handler protocols ---
    "StreamHandlerProtocol",
    "ChatCompletionTextHandlerProtocol",
    "ChatCompletionToolCallHandlerProtocol",
    "ResponsesTextDeltaHandlerProtocol",
    "ResponsesToolCallHandlerProtocol",
    "ResponsesCompletedHandlerProtocol",
    "ResponsesCodeInterpreterHandlerProtocol",
    # --- Handler implementations ---
    "ChatCompletionTextHandler",
    "ChatCompletionToolCallHandler",
    "ResponsesTextDeltaHandler",
    "ResponsesToolCallHandler",
    "ResponsesCompletedHandler",
    "ResponsesCodeInterpreterHandler",
    # --- Streaming handlers (public API) ---
    "PipelineChatCompletionsStreamingHandler",
    "PipelineResponsesStreamingHandler",
    # --- Replacers ---
    "ReferenceResolutionReplacer",
    # --- Legacy (backward compat) ---
    "ChatCompletionSdkPersistence",
    "ChatCompletionStreamAccumulator",
    "ResponseStreamPersistenceProtocol",
    "ResponseStreamSource",
    "ResponsesSdkPersistence",
    "ResponsesStreamAccumulator",
    "ResponsesStreamAccumulatorProtocol",
    "StreamAccumulatorProtocol",
    "StreamPersistenceProtocol",
    "StreamSource",
    "iter_chat_completion_chunks_until_tool_calls",
    "run_chat_completions_stream_pipeline",
    "run_responses_stream_pipeline",
    "run_stream_pipeline",
]
