"""Streaming pipeline primitives (generic protocols, folds, SDK persistence, runners)."""

from __future__ import annotations

from .chat_completion_accumulator import (
    ChatCompletionStreamAccumulator,
    iter_chat_completion_chunks_until_tool_calls,
)
from .chat_completion_sdk_persistence import ChatCompletionSdkPersistence
from .protocols import (
    ResponsesStreamAccumulatorProtocol,
    ResponseStreamPersistenceProtocol,
    ResponseStreamSource,
    StreamAccumulatorProtocol,
    StreamPersistenceProtocol,
    StreamSource,
)
from .responses_accumulator import ResponsesStreamAccumulator
from .responses_sdk_persistence import ResponsesSdkPersistence
from .responses_streaming_handler import PipelineResponsesStreamingHandler
from .run import (
    run_chat_completions_stream_pipeline,
    run_responses_stream_pipeline,
    run_stream_pipeline,
)

__all__ = [
    "ChatCompletionSdkPersistence",
    "ChatCompletionStreamAccumulator",
    "PipelineResponsesStreamingHandler",
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
