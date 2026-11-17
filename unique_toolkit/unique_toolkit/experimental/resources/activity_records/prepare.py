"""Prepare Activity Records outbox rows from camelCase wire dictionaries."""

from __future__ import annotations

import contextlib
import logging
import math
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Final, overload

from unique_toolkit.experimental.resources.activity_records.config import (
    DEFAULT_MAX_DATA_SIZE_BYTES,
)
from unique_toolkit.experimental.resources.activity_records.json_size import (
    cap_depth,
    json_byte_length,
    json_byte_length_if_within_limit,
    truncate_json_value_to_bytes,
)
from unique_toolkit.experimental.resources.activity_records.schemas import (
    ActivityCloudEvent,
)

try:
    from opentelemetry import trace as otel_trace
except ImportError:  # opentelemetry-api is optional
    otel_trace = None

logger = logging.getLogger(__name__)

WireEvent = dict[str, Any]

_EMPTY_BATCH_BYTES: Final = 2
_UNSAFE_CHARACTERS = re.compile("[\x00\ud800-\udfff]")
_REPLACEMENT_CHARACTER: Final = "�"


@dataclass(frozen=True, slots=True)
class OutboxRow:
    id: str
    company_id: str
    source: str
    payload: WireEvent


@dataclass(frozen=True, slots=True)
class FitResult:
    event: WireEvent
    critical_data_truncated: bool


@dataclass(frozen=True, slots=True)
class FitEventsResult:
    events: list[WireEvent]
    # Events whose criticalData was shrunk, or that are still over the cap.
    truncated_events: list[WireEvent]


@dataclass(frozen=True, slots=True)
class PreparedRows:
    rows: list[OutboxRow]
    truncated_events: list[WireEvent]


def to_last_error(error: BaseException) -> str:
    """Error class name only: messages can echo payload content."""
    return type(error).__name__


def _shrink_critical_data(
    event: WireEvent,
    max_data_size_bytes: int,
    original_size_at_least: int | None = None,
) -> tuple[WireEvent, bool]:
    data = event["data"]
    if "criticalData" not in data:
        return event, False

    # A lower bound, not a measurement: the oversized data was never fully sized.
    if original_size_at_least is None:
        original_size_at_least = max_data_size_bytes + 1
    without_critical_data = {
        key: value for key, value in data.items() if key != "criticalData"
    }
    key_overhead = (
        json_byte_length("criticalData") + 1 + (1 if without_critical_data else 0)
    )
    size_without = json_byte_length_if_within_limit(
        without_critical_data, max_data_size_bytes
    )
    wrapper_shell = json_byte_length(
        {
            "truncated": True,
            "originalSizeBytesAtLeast": original_size_at_least,
            "maxDataSizeBytes": max_data_size_bytes,
            "value": None,
        }
    ) - json_byte_length(None)

    budget = (
        -1
        if size_without is None
        else max_data_size_bytes - size_without - key_overhead - wrapper_shell
    )
    value = (
        truncate_json_value_to_bytes(data["criticalData"], budget)
        if budget > 0
        else None
    )
    critical_data = {
        "truncated": True,
        "originalSizeBytesAtLeast": original_size_at_least,
        "maxDataSizeBytes": max_data_size_bytes,
        "value": value,
    }
    return {
        **event,
        "data": {**without_critical_data, "criticalData": critical_data},
    }, True


def _cap_critical_data_depth(event: WireEvent) -> tuple[WireEvent, bool]:
    # criticalData sits one level inside data, and its value one more once the truncation wrapper
    # holds it, so the cap starts at depth 2 and the wrapped value stays within the walk's limit.
    data = event["data"]
    if "criticalData" not in data:
        return event, False
    capped, cut = cap_depth(data["criticalData"], 2)
    if not cut:
        return event, False
    return {**event, "data": {**data, "criticalData": capped}}, True


def fit_event_to_limit(
    event: WireEvent, max_data_size_bytes: int = DEFAULT_MAX_DATA_SIZE_BYTES
) -> FitResult:
    """Fits ``event`` into ``max_data_size_bytes`` best effort and never drops it:
    ``criticalData`` shrinks into the bytes left once the rest of ``data`` is counted."""
    capped, depth_cut = _cap_critical_data_depth(event)
    if (
        not depth_cut
        and json_byte_length_if_within_limit(event["data"], max_data_size_bytes)
        is not None
    ):
        return FitResult(event, critical_data_truncated=False)
    # A depth cut gets the same marker as a size cut; its original size is measured, not a bound.
    original_size = None
    if depth_cut:
        with contextlib.suppress(RecursionError):
            original_size = json_byte_length(with_postgres_safe_strings(event["data"]))
    fitted, shrunk = _shrink_critical_data(capped, max_data_size_bytes, original_size)
    return FitResult(fitted, critical_data_truncated=shrunk)


def is_oversized(event: WireEvent, max_data_size_bytes: int) -> bool:
    return json_byte_length_if_within_limit(event["data"], max_data_size_bytes) is None


def fit_events_to_limit(
    events: Sequence[WireEvent], max_data_size_bytes: int
) -> FitEventsResult:
    fitted_events: list[WireEvent] = []
    truncated_events: list[WireEvent] = []
    for event in events:
        fit = fit_event_to_limit(event, max_data_size_bytes)
        if fit.critical_data_truncated:
            logger.warning(
                "Activity event criticalData truncated to fit the size or depth limit: "
                "eventType=%s source=%s maxDataSizeBytes=%s",
                event["type"],
                event["source"],
                max_data_size_bytes,
            )
        still_oversized = is_oversized(fit.event, max_data_size_bytes)
        if still_oversized and not fit.critical_data_truncated:
            logger.warning(
                "Activity event data still exceeds the size limit after best-effort truncation: "
                "eventType=%s source=%s maxDataSizeBytes=%s",
                event["type"],
                event["source"],
                max_data_size_bytes,
            )
        fitted_events.append(fit.event)
        if fit.critical_data_truncated or still_oversized:
            truncated_events.append(fit.event)
    return FitEventsResult(fitted_events, truncated_events)


def _active_trace_id() -> str | None:
    if otel_trace is None:
        return None
    span_context = otel_trace.get_current_span().get_span_context()
    return format(span_context.trace_id, "032x") if span_context.is_valid else None


def with_correlation_id(events: Sequence[WireEvent]) -> list[WireEvent]:
    """Stamps the active trace id on events without one. Must run in the caller's context."""
    correlation_id = _active_trace_id()
    if correlation_id is None:
        return list(events)
    return [
        event
        if event["data"].get("correlationId")
        else {**event, "data": {**event["data"], "correlationId": correlation_id}}
        for event in events
    ]


@overload
def with_postgres_safe_strings(value: str) -> str: ...
@overload
def with_postgres_safe_strings(value: WireEvent) -> WireEvent: ...
def with_postgres_safe_strings(value: Any) -> Any:
    """Replaces U+0000 and surrogate code points in every string and key: Postgres ``jsonb``
    and ``text`` reject them, and one bad event fails the whole insert it shares."""
    if isinstance(value, str):
        return _UNSAFE_CHARACTERS.sub(_REPLACEMENT_CHARACTER, value)
    if isinstance(value, list):
        return [with_postgres_safe_strings(item) for item in value]
    if isinstance(value, dict):
        return {
            with_postgres_safe_strings(key): with_postgres_safe_strings(item)
            for key, item in value.items()
        }
    return value


def prepare_rows(
    company_id: str,
    events: Sequence[ActivityCloudEvent],
    max_data_size_bytes: int = DEFAULT_MAX_DATA_SIZE_BYTES,
) -> PreparedRows:
    """Outbox rows for ``events``. Call in the caller's context: the correlation id comes
    from the active OpenTelemetry trace."""
    if with_postgres_safe_strings(company_id) != company_id:
        raise ValueError("company_id contains characters Postgres rejects")
    if any(event.data.company_id != company_id for event in events):
        raise ValueError("An event belongs to another company than company_id")
    fitted = fit_events_to_limit(
        with_correlation_id([event.to_wire() for event in events]), max_data_size_bytes
    )
    rows = []
    for event in fitted.events:
        payload = with_postgres_safe_strings(event)
        rows.append(OutboxRow(payload["id"], company_id, payload["source"], payload))
    return PreparedRows(rows, fitted.truncated_events)


def split_into_batches_under_limit[T](
    items: Sequence[T],
    event_of: Callable[[T], WireEvent],
    max_batch_size_bytes: int,
    max_data_size_bytes: int,
) -> list[list[T]]:
    """Groups ``items`` into as few messages as fit under ``max_batch_size_bytes``, in order.
    An oversized event, or one over the batch cap on its own, is sent alone, never dropped."""
    batches: list[list[T]] = []
    current: list[T] = []
    current_bytes: float = _EMPTY_BATCH_BYTES

    for item in items:
        event = event_of(item)
        if is_oversized(event, max_data_size_bytes):
            if current:
                batches.append(current)
            batches.append([item])
            current, current_bytes = [], _EMPTY_BATCH_BYTES
            continue

        event_bytes = json_byte_length_if_within_limit(event, max_batch_size_bytes)
        separator = 1 if current else 0
        if (
            event_bytes is not None
            and current_bytes + separator + event_bytes <= max_batch_size_bytes
        ):
            current.append(item)
            current_bytes += separator + event_bytes
            continue

        if current:
            batches.append(current)
        if event_bytes is None:
            logger.warning(
                "Activity event exceeds the whole-batch size limit even alone; sending it in "
                "its own message anyway: eventType=%s source=%s maxBatchSizeBytes=%s",
                event["type"],
                event["source"],
                max_batch_size_bytes,
            )
        current = [item]
        current_bytes = (
            math.inf if event_bytes is None else _EMPTY_BATCH_BYTES + event_bytes
        )

    if current:
        batches.append(current)
    return batches
