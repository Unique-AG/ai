"""Streaming pipeline protocols: generic fold/persistence shapes and Responses aliases.

Generic protocols (:class:`StreamAccumulatorProtocol`, :class:`StreamPersistenceProtocol`,
:class:`StreamSource`) apply to any stream element type; OpenAI Responses–specific
:class:`ResponseStreamSource` and accumulator/persistence aliases are defined at
the bottom of this module.
"""

from __future__ import annotations

from collections.abc import AsyncIterable
from datetime import datetime
from typing import Protocol, TypeAlias, TypeVar

from openai.types.responses import ResponseStreamEvent

from unique_toolkit.language_model.schemas import LanguageModelStreamResponse

# ``apply`` takes ``TStreamEvent`` → contravariant; ``build_stream_result`` returns
# ``TStreamResult`` → covariant (PEP 544 / basedpyright).
TStreamEvent = TypeVar("TStreamEvent", contravariant=True)
TStreamResult = TypeVar("TStreamResult", covariant=True)

# Async iterator of *your* chunk/event type (OpenAI Responses, chat completions, etc.).
type StreamSource[T] = AsyncIterable[T]


class StreamAccumulatorProtocol(Protocol[TStreamEvent, TStreamResult]):
    """Fold over ``TStreamEvent`` and produce ``TStreamResult`` when the stream ends.

    Each stream family implements this with concrete event handling in
    :meth:`apply` and a matching projection in :meth:`build_stream_result`.

    **Lifecycle:** Implementations should treat a **finished** fold (after
    :meth:`build_stream_result`) as **single-use** until :meth:`reset` — calling
    :meth:`apply` or :meth:`build_stream_result` again without :meth:`reset` must
    raise. :func:`~unique_toolkit.framework_utilities.openai.streaming.pipeline.run.run_stream_pipeline`
    calls :meth:`reset` at the **start** of each run so the same instance can be
    reused safely across sequential runs.
    """

    def reset(self) -> None:
        """Clear all accumulated state and any \"finalized\" guard for a new stream."""
        ...

    def apply(self, event: TStreamEvent) -> None:
        """Update internal state from one stream element."""
        ...

    def build_stream_result(
        self,
        *,
        message_id: str,
        chat_id: str,
        created_at: datetime,
    ) -> TStreamResult:
        """Materialize the final result from accumulated state (marks the fold finished)."""
        ...


class StreamPersistenceProtocol(Protocol[TStreamEvent]):
    """Optional side effects while streaming (e.g. Unique SDK), keyed by event type.

    :meth:`reset` clears per-run buffers so the same sink instance can be used for
    another stream without mixing indices or partial state. The runner calls
    :meth:`reset` at the **start** of each :func:`~unique_toolkit.framework_utilities.openai.streaming.pipeline.run.run_stream_pipeline` invocation.
    """

    def reset(self) -> None:
        """Clear any per-run state (counters, buffers)."""
        ...

    async def on_event(
        self,
        event: TStreamEvent,
        *,
        index: int,
    ) -> None:
        """Called once per element, in order, after the accumulator has applied it."""
        ...

    async def on_stream_end(self) -> None:
        """Called once after the async iterator completes."""
        ...


# --- OpenAI Responses API (SDK / LiteLLM-shaped streams) ---

# Async stream of official OpenAI SDK Responses events (LiteLLM aligns with this shape).
ResponseStreamSource: TypeAlias = StreamSource[ResponseStreamEvent]

# Fold + build :class:`LanguageModelStreamResponse` from a Responses stream.
ResponsesStreamAccumulatorProtocol: TypeAlias = StreamAccumulatorProtocol[
    ResponseStreamEvent,
    LanguageModelStreamResponse,
]

# Optional persistence keyed by :class:`ResponseStreamEvent`.
ResponseStreamPersistenceProtocol: TypeAlias = StreamPersistenceProtocol[
    ResponseStreamEvent
]
