"""One Activity Record per outgoing web search query, plus one per call that sent none."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast
from urllib.parse import urlsplit

from unique_toolkit.experimental.resources.activity_records import (
    ActivityCloudEvent,
    enqueue,
    is_running,
)
from unique_toolkit.experimental.resources.feature_flags import get_feature_flag_client

if TYPE_CHECKING:
    from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
    from unique_toolkit.language_model.schemas import LanguageModelFunction

    from unique_web_search.service import WebSearchTool
    from unique_web_search.services.search_engine.registry import EngineKey

_LOGGER = logging.getLogger(__name__)

_USER_PROMPT_MAX_LENGTH = 4096
ENABLE_WEB_SEARCH_ACTIVITY_RECORDS_FLAG = (
    "FEATURE_FLAG_ENABLE_WEB_SEARCH_ACTIVITY_RECORDS_UN_28965"
)

Outcome = Literal["called", "denied", "failed"]
DirectCallOrigin = Literal["conduct", "api"]
CallOrigin = Literal["chat", DirectCallOrigin]


class _Screening(TypedDict):
    status: str
    reason: str | None


class _Elicitation(TypedDict):
    status: str
    proposedQueries: list[str]


# total=False subclasses, not NotRequired: under the __future__ import Python 3.12
# reports NotRequired keys as required.
class _SharedRequired(TypedDict):
    args: Any
    argumentScreening: _Screening
    elicitation: _Elicitation


class _SharedCriticalData(_SharedRequired, total=False):
    chatId: str
    messageId: str
    toolCallId: str
    userPrompt: str
    userPromptTruncated: bool


class _CallCriticalData(_SharedCriticalData, total=False):
    reason: str


class _EgressRequired(TypedDict):
    viaSearchProxy: bool
    endpoint: str | None


class _Egress(_EgressRequired, total=False):
    destination: str


class _QueryRequired(_SharedCriticalData):
    query: str
    params: dict[str, Any] | None
    egress: _Egress
    responseReceived: bool


class _QueryCriticalData(_QueryRequired, total=False):
    error: str


_SHARED_KEYS = (
    _SharedCriticalData.__required_keys__ | _SharedCriticalData.__optional_keys__
)


@dataclass
class ActivityRecord:
    source: CallOrigin
    company_id: str
    user_id: str
    assistant_id: str | None
    executor_mode: str | None
    engine_id: str
    engine_name: str
    critical_data: _CallCriticalData
    outcome: Outcome = "failed"
    queries_sent: int = 0


def _emit(
    record: ActivityRecord,
    type_: str,
    build_critical_data: Callable[[], Mapping[str, object]],
) -> None:
    try:
        # Empty agent id and subtype fail ActivityEventData (min_length=1); omit them.
        data: dict[str, Any] = {
            "actor": {"id": record.user_id, "type": "user"},
            "companyId": record.company_id,
            "targetType": "searchEngine",
            "targetId": record.engine_id,
            "targetName": record.engine_name,
            "criticalData": build_critical_data(),
        }
        if record.assistant_id:
            data["agent"] = {"id": record.assistant_id}
        if record.executor_mode:
            data["subtype"] = record.executor_mode
        # build() cuts over-long metadata instead of raising, so the record is never dropped.
        event = ActivityCloudEvent.build(
            source=record.source,
            type=type_,
            data=data,
        )
        enqueue(event)
    except Exception as exc:
        _LOGGER.error(
            "Could not emit the web search activity record (errorName=%s)",
            type(exc).__name__,
        )


# Ambient per-call record, like the toolkit's InvocationStatsCollector.scope(): the
# engines are plugins, so threading a recorder through their signatures is not an option.
_current_record: ContextVar[ActivityRecord | None] = ContextVar(
    "web_search_activity_record", default=None
)


@cache
def _warn_outbox_down() -> None:
    _LOGGER.warning(
        "Web search Activity Records are enabled but no Activity Records outbox is "
        "running; records are lost until the service is configured"
    )


async def _count_call_while_outbox_down(company_id: str, user_id: str) -> None:
    # Imported here: the metrics module needs prometheus, an optional extra.
    try:
        from unique_toolkit.experimental.resources.activity_records.metrics import (
            get_or_create_activity_event_outbox_metrics,
        )

        if not await get_feature_flag_client().is_enabled(
            ENABLE_WEB_SEARCH_ACTIVITY_RECORDS_FLAG,
            company_id=company_id,
            user_id=user_id,
        ):
            return
        get_or_create_activity_event_outbox_metrics().record_failures.inc()
    except Exception as exc:
        _LOGGER.debug(
            "Could not check web search activity records while no outbox is running (errorName=%s)",
            type(exc).__name__,
        )
        return
    _warn_outbox_down()


async def _start(
    source: CallOrigin,
    ids: Callable[[], tuple[str, str]],
    describe: Callable[[], tuple[EngineKey, str | None, str | None, dict[str, Any]]],
) -> ActivityRecord | None:
    """Gate on outbox and flag, then build the record. ``describe`` runs only past the gate."""
    try:
        company_id, user_id = ids()
        if not is_running():
            await _count_call_while_outbox_down(company_id, user_id)
            return None
        # A flag read that raises lands in the except below and records nothing.
        if not await get_feature_flag_client().is_enabled(
            ENABLE_WEB_SEARCH_ACTIVITY_RECORDS_FLAG,
            company_id=company_id,
            user_id=user_id,
        ):
            return None
        # Imported here: the registry imports search_engine.base, which imports this module.
        from unique_web_search.services.search_engine.registry import (
            SEARCH_ENGINE_REGISTRY,
        )

        engine, assistant_id, executor_mode, fields = describe()
        critical_data = cast(
            "_CallCriticalData",
            {
                **fields,
                "argumentScreening": {"status": "notRun", "reason": None},
                "elicitation": {"status": "notRun", "proposedQueries": []},
            },
        )
        return ActivityRecord(
            source=source,
            company_id=company_id,
            user_id=user_id,
            assistant_id=assistant_id,
            executor_mode=executor_mode,
            engine_id=engine.value,
            engine_name=SEARCH_ENGINE_REGISTRY[engine].config_display_name,
            critical_data=critical_data,
        )
    except Exception as exc:
        # Class name only: a validation error message can echo client data.
        _LOGGER.error(
            "Could not start the web search activity record (errorName=%s)",
            type(exc).__name__,
        )
        return None


async def start(
    tool: WebSearchTool, tool_call: LanguageModelFunction
) -> ActivityRecord | None:
    def describe() -> tuple[EngineKey, str | None, str | None, dict[str, Any]]:
        payload = tool.event.payload
        prompt = payload.user_message.text
        fields: dict[str, Any] = {
            "chatId": payload.chat_id,
            "messageId": payload.assistant_message.id,
            "toolCallId": tool_call.id,
            "userPrompt": prompt[:_USER_PROMPT_MAX_LENGTH],
            # Replaced by the validated parameters once _run has parsed them.
            "args": tool_call.arguments,
        }
        if len(prompt) > _USER_PROMPT_MAX_LENGTH:
            fields["userPromptTruncated"] = True
        return (
            tool.search_engine_service.config.engine,
            payload.assistant_id,
            tool.config.web_search_mode_config.mode.value,
            fields,
        )

    return await _start("chat", lambda: (tool.company_id, tool.event.user_id), describe)


async def start_direct(
    *,
    company_id: str,
    user_id: str,
    engine: EngineKey,
    call_origin: DirectCallOrigin,
    args: Mapping[str, Any],
    assistant_id: str | None = None,
    chat_id: str | None = None,
    message_id: str | None = None,
) -> ActivityRecord | None:
    if not company_id or not user_id:
        return None

    def describe() -> tuple[EngineKey, str | None, str | None, dict[str, Any]]:
        fields: dict[str, Any] = {"args": dict(args)}
        if chat_id:
            fields["chatId"] = chat_id
        if message_id:
            fields["messageId"] = message_id
        return engine, assistant_id, None, fields

    return await _start(call_origin, lambda: (company_id, user_id), describe)


@contextmanager
def active(record: ActivityRecord | None) -> Iterator[None]:
    """Collect into ``record`` for the block. A call that sent no query emits one call row."""
    token = _current_record.set(record)
    try:
        yield
    except BaseException as exc:
        # Cancellation (user Stop) is a BaseException the callers' except Exception skips.
        if record is not None:
            _note_failure(record, exc)
        raise
    finally:
        _current_record.reset(token)
        if (
            record is not None
            and record.queries_sent == 0
            and record.outcome != "called"
        ):
            _emit(
                record,
                f"web-search.tool.{record.outcome}",
                lambda: record.critical_data,
            )


def _note_failure(record: ActivityRecord, exc: BaseException) -> None:
    """Keep the first error's type only (never the message, it can hold client data)."""
    if record.outcome != "called":
        record.critical_data.setdefault("reason", type(exc).__name__)


def _put(key: str, value: Any) -> None:
    if (record := _current_record.get()) is not None:
        record.critical_data[key] = value


def set_outcome(outcome: Outcome, reason: str | None = None) -> None:
    if (record := _current_record.get()) is not None:
        record.outcome = outcome
        if reason is not None:
            record.critical_data["reason"] = reason


def set_failure(exc: Exception) -> None:
    if (record := _current_record.get()) is not None:
        _note_failure(record, exc)


def set_args(args: dict[str, Any]) -> None:
    _put("args", args)


def set_screening(go: bool, reason: str) -> None:
    _put(
        "argumentScreening",
        {"status": "approved" if go else "rejected", "reason": reason},
    )


def set_elicitation(
    status: Literal["approved", "edited", "declined", "cancelled", "expired", "notRun"],
    proposed_queries: list[str],
) -> None:
    _put("elicitation", {"status": status, "proposedQueries": list(proposed_queries)})


_NO_RESPONSE = "_finishedWithoutResponse"
# One tool call can search concurrently, so each query keeps its own entry.
_request: ContextVar[dict[str, Any] | None] = ContextVar(
    "web_search_activity_search_request", default=None
)


def note_response_received() -> None:
    """An HTTP or SDK response arrived, including an error status."""
    entry = _request.get()
    if entry is not None:
        entry["responseReceived"] = True


def note_no_response() -> None:
    """The call returns normally, but nothing answered. Do not overwrite a real response."""
    entry = _request.get()
    if entry is not None and not entry["responseReceived"]:
        entry[_NO_RESPONSE] = True


def _origin(url: str | None) -> str | None:
    """Scheme, host and port only: a path or query string can hold an API key."""
    if url is None:
        return None
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    if not parts.hostname:
        return None
    host = f"[{parts.hostname}]" if ":" in parts.hostname else parts.hostname
    suffix = f":{port}" if port else ""
    return f"{parts.scheme}://{host}{suffix}"


@contextmanager
def search_request(
    query: str,
    *,
    params: ExposedParams | None,
    via_search_proxy: bool,
    endpoint: str | None,
    destination: str | None = None,
) -> Iterator[None]:
    if (record := _current_record.get()) is None:
        yield
        return
    egress: _Egress = {
        "viaSearchProxy": via_search_proxy,
        "endpoint": _origin(endpoint),
    }
    if destination_origin := _origin(destination):
        egress["destination"] = destination_origin
    entry: dict[str, Any] = {"responseReceived": False}
    token = _request.set(entry)
    try:
        yield
    except BaseException as exc:
        entry["error"] = type(exc).__name__
        raise
    else:
        # A swallowed failure calls note_no_response(); a received error status stays True.
        if not entry.pop(_NO_RESPONSE, False):
            entry["responseReceived"] = True
    finally:
        entry.pop(_NO_RESPONSE, None)
        _request.reset(token)
        record.queries_sent += 1

        def build() -> dict[str, Any]:
            shared = {
                k: v for k, v in record.critical_data.items() if k in _SHARED_KEYS
            }
            dumped = (
                params.model_dump(mode="json", by_alias=True, exclude_none=True)
                if params
                else None
            )
            return {
                **shared,
                "query": query,
                "params": dumped,
                "egress": egress,
                **entry,
            }

        _emit(record, "web-search.query.sent", build)
