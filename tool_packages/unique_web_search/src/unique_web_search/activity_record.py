"""One Activity Record per web search tool call."""

from __future__ import annotations

import importlib
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlsplit

from unique_toolkit.experimental.resources.activity_records import (
    ActivityCloudEvent,
    enqueue,
)

if TYPE_CHECKING:
    from unique_toolkit.language_model.schemas import LanguageModelFunction

    from unique_web_search.service import WebSearchTool

_LOGGER = logging.getLogger(__name__)

_USER_PROMPT_MAX_LENGTH = 4096

Outcome = Literal["called", "denied", "failed"]


@dataclass
class ActivityRecord:
    company_id: str
    user_id: str
    assistant_id: str
    executor_mode: str
    engine_id: str
    engine_name: str
    critical_data: dict[str, Any]
    outcome: Outcome = "failed"

    def to_event(self) -> ActivityCloudEvent:
        # build() cuts over-long metadata instead of raising, so the record is never dropped.
        return ActivityCloudEvent.build(
            source="web-search",
            type=f"web-search.tool.{self.outcome}",
            data={
                "actor": {"id": self.user_id, "type": "user"},
                "agent": {"id": self.assistant_id},
                "companyId": self.company_id,
                "targetType": "searchEngine",
                "targetId": self.engine_id,
                "targetName": self.engine_name,
                "subtype": self.executor_mode,
                "criticalData": self.critical_data,
            },
        )


_current: ContextVar[ActivityRecord | None] = ContextVar(
    "web_search_activity_record", default=None
)
# activity_records.__init__ rebinds .enqueue to the function, so import the module directly.
_enqueue_module = importlib.import_module(
    "unique_toolkit.experimental.resources.activity_records.enqueue"
)


def start(
    tool: WebSearchTool, tool_call: LanguageModelFunction
) -> ActivityRecord | None:
    if getattr(_enqueue_module, "_active_context") is None:
        return None
    # Imported here: the registry imports search_engine.base, which imports this module.
    from unique_web_search.services.search_engine.registry import (
        SEARCH_ENGINE_REGISTRY,
    )

    try:
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
                "egress": None,
                "searchRequests": [],
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
    """Collect into ``record`` for the duration of the block, then emit it once."""
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
        if record is not None:
            try:
                enqueue(record.to_event())
            except Exception as exc:
                _LOGGER.error(
                    "Could not emit the web search activity record (errorName=%s)",
                    type(exc).__name__,
                )


def _note_failure(record: ActivityRecord, exc: BaseException) -> None:
    """Keep the first error's type only (never the message, it can hold client data)."""
    if record.outcome == "failed":
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


def set_elicitation(
    status: Literal["approved", "edited", "declined", "cancelled", "expired", "notRun"],
    proposed_queries: list[str],
) -> None:
    _put("elicitation", {"status": status, "proposedQueries": list(proposed_queries)})


def _origin(url: str | None) -> str | None:
    """Scheme, host and port only: a path or query string can hold an API key."""
    if url is None:
        return None
    parts = urlsplit(url)
    if not parts.hostname:
        return None
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{parts.hostname}{port}"


@contextmanager
def search_request(
    query: str, *, via_search_proxy: bool, endpoint: str | None
) -> Iterator[None]:
    if (record := _current.get()) is None:
        yield
        return
    if record.critical_data["egress"] is None:
        record.critical_data["egress"] = {
            "viaSearchProxy": via_search_proxy,
            "endpoint": _origin(endpoint),
        }
    entry = {"query": query, "responseReceived": False}
    record.critical_data["searchRequests"].append(entry)
    yield
    entry["responseReceived"] = True
