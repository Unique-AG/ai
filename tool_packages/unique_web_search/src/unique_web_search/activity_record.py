"""One Activity Record per outgoing web search query, plus one per call that sent none."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypedDict
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

_LOGGER = logging.getLogger(__name__)

_USER_PROMPT_MAX_LENGTH = 4096
ENABLE_WEB_SEARCH_ACTIVITY_RECORDS_FLAG = (
    "FEATURE_FLAG_ENABLE_WEB_SEARCH_ACTIVITY_RECORDS_UN_28965"
)

Outcome = Literal["called", "denied", "failed"]


class _Screening(TypedDict):
    status: str
    reason: str | None


class _Elicitation(TypedDict):
    status: str
    proposedQueries: list[str]


# total=False subclasses, not NotRequired: under the __future__ import Python 3.12
# reports NotRequired keys as required.
class _SharedRequired(TypedDict):
    chatId: str
    messageId: str
    toolCallId: str
    userPrompt: str
    args: Any
    argumentScreening: _Screening
    elicitation: _Elicitation


class _SharedCriticalData(_SharedRequired, total=False):
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
    company_id: str
    user_id: str
    assistant_id: str
    executor_mode: str
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
        # build() cuts over-long metadata instead of raising, so the record is never dropped.
        event = ActivityCloudEvent.build(
            source="web-search",
            type=type_,
            data={
                "actor": {"id": record.user_id, "type": "user"},
                "agent": {"id": record.assistant_id},
                "companyId": record.company_id,
                "targetType": "searchEngine",
                "targetId": record.engine_id,
                "targetName": record.engine_name,
                "subtype": record.executor_mode,
                "criticalData": build_critical_data(),
            },
        )
        enqueue(event)
    except Exception as exc:
        _LOGGER.error(
            "Could not emit the web search activity record (errorName=%s)",
            type(exc).__name__,
        )


_current: ContextVar[ActivityRecord | None] = ContextVar(
    "web_search_activity_record", default=None
)


async def start(
    tool: WebSearchTool, tool_call: LanguageModelFunction
) -> ActivityRecord | None:
    if not is_running():
        return None
    # Imported here: the registry imports search_engine.base, which imports this module.
    from unique_web_search.services.search_engine.registry import (
        SEARCH_ENGINE_REGISTRY,
    )

    try:
        # A flag read that raises lands in the except below and records nothing.
        # On outages the client itself falls back to its stale cache or env default.
        if not await get_feature_flag_client().is_enabled(
            ENABLE_WEB_SEARCH_ACTIVITY_RECORDS_FLAG, company_id=tool.company_id
        ):
            return None
        payload = tool.event.payload
        engine = tool.search_engine_service.config.engine
        prompt = payload.user_message.text
        record = ActivityRecord(
            company_id=tool.company_id,
            user_id=tool.event.user_id,
            assistant_id=payload.assistant_id,
            executor_mode=tool.config.web_search_mode_config.mode.value,
            engine_id=engine.value,
            engine_name=SEARCH_ENGINE_REGISTRY[engine].config_display_name,
            critical_data={
                "chatId": payload.chat_id,
                "messageId": payload.assistant_message.id,
                "toolCallId": tool_call.id,
                "userPrompt": prompt[:_USER_PROMPT_MAX_LENGTH],
                # Replaced by the validated parameters once _run has parsed them.
                "args": tool_call.arguments,
                "argumentScreening": {"status": "notRun", "reason": None},
                "elicitation": {"status": "notRun", "proposedQueries": []},
            },
        )
        if len(prompt) > _USER_PROMPT_MAX_LENGTH:
            record.critical_data["userPromptTruncated"] = True
        return record
    except Exception as exc:
        # Class name only: a validation error message can echo client data.
        _LOGGER.error(
            "Could not start the web search activity record (errorName=%s)",
            type(exc).__name__,
        )
        return None


@contextmanager
def active(record: ActivityRecord | None) -> Iterator[None]:
    """Collect into ``record`` for the block. A call that sent no query emits one call row."""
    token = _current.set(record)
    try:
        yield
    except BaseException as exc:
        # Cancellation (user Stop) is a BaseException the callers' except Exception skips.
        if record is not None:
            _note_failure(record, exc)
        raise
    finally:
        _current.reset(token)
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
    if (record := _current.get()) is not None:
        record.critical_data[key] = value


def set_outcome(outcome: Outcome) -> None:
    if (record := _current.get()) is not None:
        record.outcome = outcome


def set_failure(exc: Exception) -> None:
    if (record := _current.get()) is not None:
        _note_failure(record, exc)


def set_args(args: dict[str, Any]) -> None:
    _put("args", args)


def set_screening(go: bool, reason: str) -> None:
    _put(
        "argumentScreening",
        {"status": "approved" if go else "rejected", "reason": reason},
    )
    if not go:
        _put("reason", "ArgumentScreeningBlocked")


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
    if (record := _current.get()) is None:
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
