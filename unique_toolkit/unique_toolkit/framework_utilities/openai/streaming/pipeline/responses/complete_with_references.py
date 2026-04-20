"""Router-backed implementation of ``ResponsesSupportCompleteWithReferences``.

The orchestrator owns a :class:`StreamEventBus` (a routing table of typed
channels) and registers default subscribers on it. Handlers/routers stay
pure — all ``unique_sdk.Message.modify_async`` / ``MessageLog.*`` calls
live in subscribers that listen on the concrete event channels they care
about (no ``isinstance`` fan-out at the subscriber boundary).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from typing import TYPE_CHECKING, TypeGuard, overload

import httpx
from openai import AsyncOpenAI

from unique_toolkit.framework_utilities.openai.client import get_async_openai_client
from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    NORMALIZATION_MAX_MATCH_LENGTH,
    NORMALIZATION_PATTERNS,
    StreamingPatternReplacer,
    StreamingReplacerProtocol,
)
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessageOptions,
    LanguageModelMessages,
)
from unique_toolkit.protocols.streaming import ActivityProgressUpdate, TextFlushed
from unique_toolkit.protocols.support import ResponsesSupportCompleteWithReferences

from ..events import (
    ActivityProgress,
    StreamEnded,
    StreamEventBus,
    StreamStarted,
    StreamSubscriber,
    TextDelta,
)
from ..subscribers import MessagePersistingSubscriber, ProgressLogPersister
from .code_interpreter_handler import ResponsesCodeInterpreterHandler
from .completed_handler import ResponsesCompletedHandler
from .stream_event_router import ResponsesStreamEventRouter
from .text_delta_handler import ResponsesTextDeltaHandler
from .tool_call_handler import ResponsesToolCallHandler

if TYPE_CHECKING:
    from openai.types.responses import (
        ResponseIncludable,
        ResponseInputItemParam,
        ResponseInputParam,
        ResponseOutputItem,
        ResponseTextConfigParam,
        ToolParam,
        response_create_params,
    )
    from openai.types.shared_params import Metadata, Reasoning

    from unique_toolkit.app.unique_settings import UniqueSettings
    from unique_toolkit.content.schemas import ContentChunk
    from unique_toolkit.language_model.schemas import (
        LanguageModelToolDescription,
        ResponsesLanguageModelStreamResponse,
    )

from unique_toolkit.chat.responses_api import (
    _convert_messages_to_openai,
)

_LOGGER = logging.getLogger(__name__)


def _is_language_model_messages(
    msgs: "list[LanguageModelMessageOptions] | list[ResponseInputItemParam]",
) -> TypeGuard[list[LanguageModelMessageOptions]]:
    """Narrow a union of message lists to LanguageModelMessageOptions."""
    return len(msgs) > 0 and isinstance(msgs[0], LanguageModelMessageOptions)


def _is_response_input_items(
    msgs: "list[LanguageModelMessageOptions] | list[ResponseInputItemParam]",
) -> TypeGuard[list[ResponseInputItemParam]]:
    """Narrow a union of message lists to ResponseInputItemParam (TypedDicts)."""
    return len(msgs) > 0 and isinstance(msgs[0], dict)


def _convert_tools(
    tools: Sequence[LanguageModelToolDescription | ToolParam] | None,
) -> list[ToolParam] | None:
    if not tools:
        return None
    from unique_toolkit.chat.responses_api import _convert_tools_to_openai

    return _convert_tools_to_openai(tools)


def _build_default_router() -> ResponsesStreamEventRouter:
    """Construct a :class:`ResponsesStreamEventRouter` with standard defaults.

    The defaults mirror the canonical Responses chat-app example: text
    handler wired with the shared citation-normalization replacer, plus
    the standard tool-call, completed, and code-interpreter handlers.
    All handlers are pure — side-effects live in the default subscribers
    registered by :class:`ResponsesCompleteWithReferences`.
    """
    replacers: list[StreamingReplacerProtocol] = [
        StreamingPatternReplacer(
            replacements=NORMALIZATION_PATTERNS,
            max_match_length=NORMALIZATION_MAX_MATCH_LENGTH,
        )
    ]
    return ResponsesStreamEventRouter(
        text_handler=ResponsesTextDeltaHandler(replacers=replacers),
        tool_call_handler=ResponsesToolCallHandler(),
        completed_handler=ResponsesCompletedHandler(),
        code_interpreter_handler=ResponsesCodeInterpreterHandler(),
    )


class ResponsesCompleteWithReferences(ResponsesSupportCompleteWithReferences):
    """``ResponsesSupportCompleteWithReferences`` backed by the handler router.

    Wiring mirrors :class:`ChatCompletionsCompleteWithReferences`:

    * Handlers/router accumulate state only (pure), including the code
      interpreter handler which just tracks progress updates and the
      executed code.
    * This orchestrator owns its :class:`StreamEventBus` — the bus is not
      injectable so its lifecycle stays tied to the orchestrator. The bus
      is a routing table of typed channels (one per concrete event);
      publishing and subscribing happen on the concrete channel, so no
      ``isinstance`` fan-out is needed at the subscriber boundary.
    * Default subscribers are registered conditionally:
      :class:`MessagePersistingSubscriber` is always attached (text
      lifecycle + appendices concatenation for a single-roundtrip final
      persist); :class:`ProgressLogPersister` is only attached when the
      router exposes a progress producer (i.e.
      ``router.activity_bus is not None``) so it never receives events it
      would throw away. Callers can replace or augment the subscriber set
      via the ``subscribers`` constructor argument, or attach more after
      construction through :attr:`bus` (e.g.
      ``complete.bus.text_delta.subscribe(my_analytics)``).

    Two construction shapes are supported via ``@overload``:

    * **Settings-driven** (``settings`` only, optionally ``router`` /
      ``additional_headers`` / ``subscribers``): client and router are
      auto-built with sensible defaults (normalization replacers plus the
      standard tool-call, completed and code-interpreter handlers); the
      default subscribers are registered when ``subscribers`` is omitted.
    * **Instance injection** (``settings`` + explicit ``client``,
      ``router`` and ``subscribers``): nothing is auto-constructed and
      no default subscriber is added — the caller owns every collaborator.
    """

    @overload
    def __init__(
        self,
        settings: UniqueSettings,
        *,
        router: ResponsesStreamEventRouter | None = ...,
        additional_headers: dict[str, str] | None = ...,
        subscribers: Iterable[StreamSubscriber] | None = ...,
    ) -> None:
        """Settings-driven construction with sane defaults.

        Builds an :class:`AsyncOpenAI` client from ``settings`` (with any
        ``additional_headers``) and a default
        :class:`ResponsesStreamEventRouter` when ``router`` is omitted.
        When ``subscribers`` is ``None`` (default), the default subscribers
        are auto-registered on the owned bus; pass an explicit iterable
        (including an empty one) to take full control of the subscriber
        set.
        """
        ...

    @overload
    def __init__(
        self,
        settings: UniqueSettings,
        *,
        client: AsyncOpenAI,
        router: ResponsesStreamEventRouter,
        subscribers: Iterable[StreamSubscriber],
    ) -> None:
        """Instance-injection construction — reuse pre-built collaborators.

        ``settings`` is still needed at request time to resolve
        ``chat_id`` / ``message_id``. The bus is still owned internally
        (not injectable) but every subscriber on it comes from the
        ``subscribers`` argument — no default subscribers are added. Use
        an empty iterable to start with a bare bus and attach subscribers
        later via :attr:`bus`.
        """
        ...

    def __init__(
        self,
        settings: UniqueSettings,
        *,
        router: ResponsesStreamEventRouter | None = None,
        client: AsyncOpenAI | None = None,
        subscribers: Iterable[StreamSubscriber] | None = None,
        additional_headers: dict[str, str] | None = None,
    ) -> None:
        if client is not None and additional_headers is not None:
            # ``additional_headers`` only feeds the default client builder;
            # failing loudly prevents silently dropping headers when the
            # caller also passes a pre-built client.
            raise TypeError(
                "additional_headers is only honored when the client is "
                "auto-built from settings; pass a configured AsyncOpenAI "
                "client instead, or drop additional_headers."
            )

        self._settings = settings
        self._router = router if router is not None else _build_default_router()
        self._client = (
            client
            if client is not None
            else get_async_openai_client(
                unique_settings=settings,
                additional_headers=additional_headers,
            )
        )

        self._bus: StreamEventBus = StreamEventBus()
        # ``None`` means "use the default subscribers"; an explicit iterable
        # (even empty) is treated as the caller having fully specified the
        # subscriber set — defaults are deliberately not added.
        effective_subscribers: Iterable[StreamSubscriber]
        if subscribers is None:
            effective_subscribers = self._default_subscribers()
        else:
            effective_subscribers = subscribers
        for subscriber in effective_subscribers:
            subscriber.register(self._bus)

        # Per-request context for the handler-bus adapters. Set at the top
        # of :meth:`complete_with_references_async` and cleared in its
        # ``finally`` block.
        self._current_message_id: str | None = None
        self._current_chat_id: str | None = None
        self._router.text_bus.subscribe(self._on_text_flushed)
        activity_bus = self._router.activity_bus
        if activity_bus is not None:
            activity_bus.subscribe(self._on_activity_progress_update)

    def _default_subscribers(self) -> list[StreamSubscriber]:
        """Build the default subscriber set, conditional on router capabilities.

        ``ProgressLogPersister`` is only useful when the router actually
        has a progress-producing handler (i.e. ``activity_bus`` exists);
        wiring it unconditionally would leave a subscriber listening to a
        channel nothing ever publishes on. Keeping the decision here means
        the orchestrator is the single place that understands the mapping
        from handler presence to subscriber set.
        """
        subs: list[StreamSubscriber] = [MessagePersistingSubscriber(self._settings)]
        if self._router.activity_bus is not None:
            subs.append(ProgressLogPersister(self._settings))
        return subs

    @property
    def bus(self) -> StreamEventBus:
        """Expose the owned bus so callers can attach additional subscribers."""
        return self._bus

    async def _on_text_flushed(self, event: TextFlushed) -> None:
        """Adapter: lift a handler-bus :class:`TextFlushed` to an outer :class:`TextDelta`."""
        if self._current_message_id is None or self._current_chat_id is None:
            return
        await self._bus.text_delta.publish_and_wait_async(
            TextDelta(
                message_id=self._current_message_id,
                chat_id=self._current_chat_id,
                full_text=event.full_text,
                original_text=event.original_text,
            )
        )

    async def _on_activity_progress_update(
        self, update: ActivityProgressUpdate
    ) -> None:
        """Adapter: lift a handler-bus :class:`ActivityProgressUpdate` to outer :class:`ActivityProgress`.

        Attaches ``message_id`` / ``chat_id`` — handlers stay ignorant of
        bus-level identifiers, which means a future progress-producing
        handler just needs to publish :class:`ActivityProgressUpdate` on
        its own bus and the same adapter picks it up.
        """
        if self._current_message_id is None or self._current_chat_id is None:
            return
        await self._bus.activity_progress.publish_and_wait_async(
            ActivityProgress(
                correlation_id=update.correlation_id,
                message_id=self._current_message_id,
                chat_id=self._current_chat_id,
                status=update.status,
                text=update.text,
                order=update.order,
            )
        )

    def complete_with_references(  # noqa: PLR0913
        self,
        *,
        model_name: LanguageModelName | str,
        messages: str
        | LanguageModelMessages
        | Sequence[
            ResponseInputItemParam | LanguageModelMessageOptions | ResponseOutputItem
        ],
        content_chunks: list[ContentChunk] | None = None,
        tools: Sequence[LanguageModelToolDescription | ToolParam] | None = None,
        temperature: float = 0.0,
        debug_info: dict | None = None,
        start_text: str | None = None,
        include: list[ResponseIncludable] | None = None,
        instructions: str | None = None,
        max_output_tokens: int | None = None,
        metadata: Metadata | None = None,
        parallel_tool_calls: bool | None = None,
        text: ResponseTextConfigParam | None = None,
        tool_choice: response_create_params.ToolChoice | None = None,
        top_p: float | None = None,
        reasoning: Reasoning | None = None,
        other_options: dict | None = None,
    ) -> ResponsesLanguageModelStreamResponse:
        return asyncio.run(
            self.complete_with_references_async(
                model_name=model_name,
                messages=messages,
                content_chunks=content_chunks,
                tools=tools,
                temperature=temperature,
                debug_info=debug_info,
                start_text=start_text,
                include=include,
                instructions=instructions,
                max_output_tokens=max_output_tokens,
                metadata=metadata,
                parallel_tool_calls=parallel_tool_calls,
                text=text,
                tool_choice=tool_choice,
                top_p=top_p,
                reasoning=reasoning,
                other_options=other_options,
            )
        )

    async def complete_with_references_async(  # noqa: PLR0913
        self,
        *,
        model_name: LanguageModelName | str,
        messages: str
        | LanguageModelMessages
        | Sequence[
            ResponseInputItemParam | LanguageModelMessageOptions | ResponseOutputItem
        ],
        content_chunks: list[ContentChunk] | None = None,
        tools: Sequence[LanguageModelToolDescription | ToolParam] | None = None,
        temperature: float = 0.0,
        debug_info: dict | None = None,
        start_text: str | None = None,
        include: list[ResponseIncludable] | None = None,
        instructions: str | None = None,
        max_output_tokens: int | None = None,
        metadata: Metadata | None = None,
        parallel_tool_calls: bool | None = None,
        text: ResponseTextConfigParam | None = None,
        tool_choice: response_create_params.ToolChoice | None = None,
        top_p: float | None = None,
        reasoning: Reasoning | None = None,
        other_options: dict | None = None,
    ) -> ResponsesLanguageModelStreamResponse:
        settings = self._settings
        chat = settings.context.chat
        if chat is None:
            raise ValueError("Chat context is not set")

        model: str = (
            model_name.value
            if isinstance(model_name, LanguageModelName)
            else model_name
        )

        message_id = chat.last_assistant_message_id
        chat_id = chat.chat_id

        # -- Build the OpenAI request ----------------------------------------

        def input_messages(
            messages: str
            | LanguageModelMessages
            | list[LanguageModelMessageOptions]
            | list[ResponseInputItemParam],
        ) -> ResponseInputParam | str:
            if isinstance(messages, str):
                return messages

            if isinstance(messages, LanguageModelMessages):
                return _convert_messages_to_openai(messages.root)

            if len(messages) == 0:
                return []

            converted_messages: list[ResponseInputItemParam] = []
            if _is_language_model_messages(messages):
                for message in messages:
                    converted_messages.append(message.to_openai(mode="responses"))
                return converted_messages

            if _is_response_input_items(messages):
                for message in messages:
                    converted_messages.append(message)
                return converted_messages

            return converted_messages

        # TODO(UN-15891): confirm Responses input shape for mixed message types
        converted_messages = input_messages(messages)  # type: ignore

        converted_tools = _convert_tools(tools)

        self._router.reset()
        self._current_message_id = message_id
        self._current_chat_id = chat_id
        await self._bus.stream_started.publish_and_wait_async(
            StreamStarted(
                message_id=message_id,
                chat_id=chat_id,
                content_chunks=tuple(content_chunks or ()),
            )
        )

        try:
            create_kwargs: dict = {}
            if converted_tools:
                create_kwargs["tools"] = converted_tools
            if instructions is not None:
                create_kwargs["instructions"] = instructions
            if include is not None:
                create_kwargs["include"] = include
            if max_output_tokens is not None:
                create_kwargs["max_output_tokens"] = max_output_tokens
            if metadata is not None:
                create_kwargs["metadata"] = metadata
            if parallel_tool_calls is not None:
                create_kwargs["parallel_tool_calls"] = parallel_tool_calls
            if text is not None:
                create_kwargs["text"] = text
            if tool_choice is not None:
                create_kwargs["tool_choice"] = tool_choice
            if top_p is not None:
                create_kwargs["top_p"] = top_p
            if reasoning is not None:
                create_kwargs["reasoning"] = reasoning
            if other_options:
                for k, v in other_options.items():
                    create_kwargs.setdefault(k, v)

            stream = await self._client.responses.create(
                model=model,
                input=converted_messages,
                stream=True,
                temperature=temperature,
                **create_kwargs,
            )
            async for event in stream:
                await self._router.on_event(event)
        except httpx.RemoteProtocolError as exc:
            _LOGGER.warning(
                "Stream connection closed prematurely (incomplete chunked read). "
                "Finalizing with content received so far. Error: %s",
                exc,
            )
        finally:
            await self._router.on_stream_end()
            text_state = self._router.get_text()
            await self._bus.stream_ended.publish_and_wait_async(
                StreamEnded(
                    message_id=message_id,
                    chat_id=chat_id,
                    full_text=text_state.full_text,
                    original_text=text_state.original_text,
                    appendices=self._router.get_appendices(),
                )
            )
            self._current_message_id = None
            self._current_chat_id = None

        return self._router.build_result(
            message_id=message_id,
            chat_id=chat_id,
            created_at=datetime.now(timezone.utc),
        )
