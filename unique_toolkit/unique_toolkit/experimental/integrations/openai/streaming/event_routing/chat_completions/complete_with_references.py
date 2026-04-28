"""Router-backed implementation of ``SupportCompleteWithReferences`` for Chat Completions.

The orchestrator owns a :class:`StreamEventBus` (a routing table of typed
channels) and registers default subscribers on it. Event handlers/routers stay
pure — all ``unique_sdk.Message.modify_async`` calls live in a subscriber
that listens on the concrete text-lifecycle channels, so there is no
``isinstance`` fan-out at the subscriber boundary.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast, overload

import httpx
from openai import AsyncOpenAI

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.experimental.components.streaming import TextFlushed
from unique_toolkit.experimental.components.streaming.pattern_replacer import (
    NORMALIZATION_MAX_MATCH_LENGTH,
    NORMALIZATION_PATTERNS,
    StreamingPatternReplacer,
    StreamingReplacerProtocol,
    filter_cited_sdk_references,
)
from unique_toolkit.framework_utilities.openai.client import get_async_openai_client
from unique_toolkit.language_model.constants import (
    DEFAULT_COMPLETE_TEMPERATURE,
    DEFAULT_COMPLETE_TIMEOUT,
)
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelStreamResponse,
    LanguageModelToolDescription,
)
from unique_toolkit.protocols.support import SupportCompleteWithReferences

from .._async_bridge import run_async_from_sync
from ..events import (
    StreamEnded,
    StreamEventBus,
    StreamStarted,
    StreamSubscriber,
    TextDelta,
)
from ..subscribers import MessagePersistingSubscriber
from .stream_event_router import ChatCompletionStreamEventRouter
from .text_event_handler import ChatCompletionTextEventHandler
from .tool_call_event_handler import ChatCompletionToolCallEventHandler

if TYPE_CHECKING:
    from openai.types.chat import (
        ChatCompletionMessageParam,
        ChatCompletionToolChoiceOptionParam,
    )

    from unique_toolkit.app.unique_settings import UniqueSettings
    from unique_toolkit.content.schemas import ContentChunk
    from unique_toolkit.language_model.schemas import (
        LanguageModelTool,
    )

_LOGGER = logging.getLogger(__name__)


def _convert_messages(
    messages: LanguageModelMessages | list[ChatCompletionMessageParam],
) -> list[ChatCompletionMessageParam]:
    if isinstance(messages, LanguageModelMessages):
        return messages.to_openai(mode="completions")
    return list(messages)


def _convert_tools(
    tools: Sequence[LanguageModelTool | LanguageModelToolDescription] | None,
) -> list[dict[str, Any]] | None:
    if not tools:
        return None
    result = []
    for tool in tools:
        if isinstance(tool, LanguageModelToolDescription):
            result.append(tool.to_openai(mode="completions"))
        else:
            result.append(
                {"type": "function", "function": tool.model_dump(exclude_none=True)}
            )
    return result or None


def _build_default_router() -> ChatCompletionStreamEventRouter:
    """Construct a :class:`ChatCompletionStreamEventRouter` with standard defaults.

    The defaults mirror the canonical chat-app example: a text event handler wired
    with the shared citation-normalization replacer plus the tool call
    event handler. Sufficient for the common ``[sourceN]``/``<sup>N</sup>`` flow.
    """
    replacers: list[StreamingReplacerProtocol] = [
        StreamingPatternReplacer(
            replacements=NORMALIZATION_PATTERNS,
            max_match_length=NORMALIZATION_MAX_MATCH_LENGTH,
        )
    ]
    return ChatCompletionStreamEventRouter(
        text_event_handler=ChatCompletionTextEventHandler(replacers=replacers),
        tool_call_event_handler=ChatCompletionToolCallEventHandler(),
    )


class ChatCompletionsCompleteWithReferences(SupportCompleteWithReferences):
    """``SupportCompleteWithReferences`` backed by the Chat Completions event handler router.

    Wiring:

    * Event handlers/router accumulate state only (pure).
    * This orchestrator owns its :class:`StreamEventBus` — the bus is not
      injectable so its lifecycle stays tied to the orchestrator. The bus
      is a routing table of typed channels; publishing and subscribing
      happen on the concrete channel, so no ``isinstance`` fan-out is
      needed at the subscriber boundary.
    * A default :class:`MessagePersistingSubscriber` is registered on that
      bus to handle ``Message.modify_async`` calls and reference filtering.
      Chat Completions never produces activity progress, so no progress
      subscriber is attached by default. Callers can replace or augment
      the subscriber set via the ``subscribers`` constructor argument, or
      attach more after construction through :attr:`bus` (e.g.
      ``complete.bus.text_delta.subscribe(my_analytics)``).

    Two construction shapes are supported via ``@overload``:

    * **Settings-driven** (``settings`` only, optionally ``router`` /
      ``additional_headers`` / ``subscribers``): client and router are
      auto-built with sensible defaults (normalization replacers); the
      default message persister is registered when ``subscribers`` is
      omitted.
    * **Instance injection** (``settings`` + explicit ``client``,
      ``router`` and ``subscribers``): nothing is auto-constructed and
      no default subscriber is added — the caller owns every collaborator.
    """

    @overload
    def __init__(
        self,
        settings: UniqueSettings,
        *,
        router: ChatCompletionStreamEventRouter | None = ...,
        additional_headers: dict[str, str] | None = ...,
        subscribers: Iterable[StreamSubscriber] | None = ...,
    ) -> None:
        """Settings-driven construction with sane defaults.

        Builds an :class:`AsyncOpenAI` client from ``settings`` (with any
        ``additional_headers``) and a default
        :class:`ChatCompletionStreamEventRouter` when ``router`` is omitted.
        When ``subscribers`` is ``None`` (default), a
        :class:`MessagePersistingSubscriber` is auto-registered on the
        owned bus; pass an explicit iterable (including an empty one) to
        take full control of the subscriber set.
        """
        ...

    @overload
    def __init__(
        self,
        settings: UniqueSettings,
        *,
        client: AsyncOpenAI,
        router: ChatCompletionStreamEventRouter,
        subscribers: Iterable[StreamSubscriber],
    ) -> None:
        """Instance-injection construction — reuse pre-built collaborators.

        ``settings`` is still needed at request time to resolve
        ``chat_id`` / ``message_id``. The bus is still owned internally
        (not injectable) but every subscriber on it comes from the
        ``subscribers`` argument — no default persister is added. Use an
        empty iterable to start with a bare bus and attach subscribers
        later via :attr:`bus`.
        """
        ...

    def __init__(
        self,
        settings: UniqueSettings,
        *,
        router: ChatCompletionStreamEventRouter | None = None,
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
        if client is not None and (router is None or subscribers is None):
            # Enforce the advertised instance-injection overload shape —
            # mixing a pre-built client with default-built router /
            # default-registered subscribers silently mismatches the two
            # collaborators and hides wiring mistakes.
            raise TypeError(
                "When 'client' is provided, 'router' and 'subscribers' "
                "must also be provided (instance-injection shape). Pass "
                "an explicit (even empty) 'subscribers' iterable, or drop "
                "'client' to use the settings-driven construction."
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
        # ``None`` means "use the default persister"; an explicit iterable
        # (even empty) is treated as the caller having fully specified the
        # subscriber set — the default is deliberately not added.
        effective_subscribers: Iterable[StreamSubscriber]

        if subscribers is None:
            effective_subscribers = (MessagePersistingSubscriber(settings),)
        else:
            effective_subscribers = subscribers
        for subscriber in effective_subscribers:
            subscriber.register(self._bus)

        # Per-request context for the flush-bus adapter. Set at the top of
        # :meth:`complete_with_references_async` and cleared in its
        # ``finally`` block — matches the single-request-at-a-time model
        # of ``router.reset()``. ``_in_flight`` guards against overlapping
        # requests on the same instance; see :meth:`complete_with_references_async`.
        self._current_message_id: str | None = None
        self._current_chat_id: str | None = None
        self._in_flight: bool = False
        # Keep the subscription handle so :meth:`close` can cancel it and
        # drop the reference to ``self._on_text_flushed`` the router is
        # holding — otherwise router reuse across orchestrators would leak
        # old adapter references onto the event handler bus.
        self._text_flush_subscription = self._router.text_bus.subscribe(
            self._on_text_flushed
        )

    @property
    def bus(self) -> StreamEventBus:
        """Expose the owned bus so callers can attach additional subscribers."""
        return self._bus

    def close(self) -> None:
        """Cancel adapter subscriptions so the orchestrator releases its refs.

        Safe to call multiple times. After :meth:`close` the orchestrator
        will no longer receive :class:`TextFlushed` events from the router
        — construct a fresh instance for further requests.
        """
        self._text_flush_subscription.cancel()

    async def _on_text_flushed(self, event: TextFlushed) -> None:
        """Adapter: lift an event-handler bus :class:`TextFlushed` to an outer :class:`TextDelta`.

        Guards on the per-request context — if the orchestrator is
        between requests (e.g. a late publish from a stalled event handler),
        the adapter drops the event rather than publish with stale ids.
        A warning is logged so this otherwise-silent drop surfaces wiring
        mistakes instead of masquerading as "no traffic".

        Uses ``return_exceptions=True`` so a flaky text-delta subscriber
        (e.g. analytics, tracing) cannot abort the stream loop — failures
        are logged on the bus and the remaining subscribers still run.
        """
        if self._current_message_id is None or self._current_chat_id is None:
            _LOGGER.warning(
                "ChatCompletionsCompleteWithReferences: dropping TextFlushed "
                "received while no request is in flight (full_text=%r). This "
                "usually means an event handler emitted a flush after the orchestrator "
                "cleared its per-request context.",
                event.full_text,
            )
            return
        await self._bus.text_delta.publish_and_wait_async(
            TextDelta(
                message_id=self._current_message_id,
                chat_id=self._current_chat_id,
                full_text=event.full_text,
                original_text=event.original_text,
            ),
            return_exceptions=True,
        )

    def complete_with_references(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] | None = None,
        debug_info: dict[str, Any] | None = None,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Sequence[LanguageModelTool | LanguageModelToolDescription] | None = None,
        start_text: str | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
        other_options: dict[str, Any] | None = None,
    ) -> LanguageModelStreamResponse:
        return run_async_from_sync(
            lambda: self.complete_with_references_async(
                messages=messages,
                model_name=model_name,
                content_chunks=content_chunks,
                debug_info=debug_info,
                temperature=temperature,
                timeout=timeout,
                tools=tools,
                start_text=start_text,
                tool_choice=tool_choice,
                other_options=other_options,
            )
        )

    async def complete_with_references_async(
        self,
        messages: LanguageModelMessages | list[ChatCompletionMessageParam],
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] | None = None,
        debug_info: dict[str, Any] | None = None,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Sequence[LanguageModelTool | LanguageModelToolDescription] | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
        start_text: str | None = None,
        other_options: dict[str, Any] | None = None,
    ) -> LanguageModelStreamResponse:
        # ``timeout`` and ``start_text`` are on the
        # :class:`SupportCompleteWithReferences` protocol but are not
        # forwarded to ``client.chat.completions.create``. Log when a
        # caller sets them so the silent drop is visible rather than a
        # footgun — especially ``timeout`` which callers often assume
        # applies to the HTTP request.
        if timeout != DEFAULT_COMPLETE_TIMEOUT:
            _LOGGER.warning(
                "ChatCompletionsCompleteWithReferences: 'timeout=%s' is "
                "accepted for protocol compatibility but not forwarded "
                "to the OpenAI client; configure timeouts on the client "
                "instead.",
                timeout,
            )
        if start_text is not None:
            _LOGGER.warning(
                "ChatCompletionsCompleteWithReferences: 'start_text' is "
                "accepted for protocol compatibility but not forwarded "
                "to the OpenAI client; injection of a pre-seeded "
                "assistant message is not supported here."
            )
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

        gpt_messages = (
            messages.to_openai(mode="completions")
            if isinstance(messages, LanguageModelMessages)
            else list(messages)
        )
        converted_tools = _convert_tools(tools)
        optional_create_kwargs: dict[str, Any] = {}
        if converted_tools:
            optional_create_kwargs["tools"] = converted_tools
        if tool_choice is not None:
            optional_create_kwargs["tool_choice"] = tool_choice
        if other_options:
            for k, v in other_options.items():
                optional_create_kwargs.setdefault(k, v)

        gpt_request: list[dict[str, Any]] = [
            cast("dict[str, Any]", message) for message in gpt_messages
        ]

        # Re-entry guard: per-instance state (``_current_*``, router
        # accumulators) is not safe for overlapping requests — concurrent
        # callers must build a new orchestrator. Fail fast with a clear
        # message so the constraint is visible instead of silently
        # corrupting events.
        if self._in_flight:
            raise RuntimeError(
                "ChatCompletionsCompleteWithReferences does not support "
                "concurrent complete_with_references_async calls on the "
                "same instance; construct a fresh orchestrator per "
                "in-flight request."
            )
        self._in_flight = True
        self._router.reset()
        self._current_message_id = message_id
        self._current_chat_id = chat_id
        # Outer try/finally guarantees per-request context is cleared even
        # when a ``stream_started`` subscriber raises — otherwise a stale
        # ``message_id`` / ``chat_id`` would leak into the next request via
        # ``_on_text_flushed`` / ``_on_activity_progress_update``.
        try:
            await self._bus.stream_started.publish_and_wait_async(
                StreamStarted(
                    message_id=message_id,
                    chat_id=chat_id,
                    content_chunks=tuple(content_chunks or ()),
                )
            )

            try:
                stream = await self._client.chat.completions.create(
                    model=model,
                    messages=gpt_messages,
                    stream=True,
                    temperature=temperature,
                    **optional_create_kwargs,
                )

                async for chunk in stream:
                    await self._router.on_event(chunk)

            except httpx.RemoteProtocolError as exc:
                _LOGGER.warning(
                    "Stream connection closed prematurely (incomplete chunked read). "
                    "Finalizing with content received so far. Error: %s",
                    exc,
                )
            finally:
                await self._router.on_stream_end()
                text_state = self._router.text
                await self._bus.stream_ended.publish_and_wait_async(
                    StreamEnded(
                        message_id=message_id,
                        chat_id=chat_id,
                        full_text=text_state.full_text,
                        original_text=text_state.original_text,
                        gpt_request=gpt_request,
                        debug_info=debug_info,
                    )
                )
        finally:
            self._current_message_id = None
            self._current_chat_id = None
            self._in_flight = False

        message = ChatMessage(
            id=message_id,
            chat_id=chat_id,
            role=ChatMessageRole.ASSISTANT,
            text=text_state.full_text,
            original_text=text_state.original_text,
            references=[
                ContentReference.from_sdk_reference(r)
                for r in filter_cited_sdk_references(
                    content_chunks or [], text_state.full_text
                )
            ],
            gpt_request=gpt_request,
            debug_info=debug_info if debug_info is not None else {},
            created_at=datetime.now(timezone.utc),
        )

        return LanguageModelStreamResponse(
            message=message,
            tool_calls=self._router.tool_calls,
            usage=self._router.usage,
        )
