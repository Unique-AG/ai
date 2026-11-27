from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol

from unique_toolkit.monitoring import MetricNamespace


class _ObservesSeconds(Protocol):
    def observe(self, amount: float) -> None: ...


m = MetricNamespace("unique_user_memory")

_DURATION_BUCKETS = (0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0)
_TOKEN_BUCKETS = (
    0.0,
    100.0,
    250.0,
    500.0,
    1000.0,
    1500.0,
    2000.0,
    3000.0,
    5000.0,
    8000.0,
)
_CHAR_BUCKETS = (
    0.0,
    200.0,
    500.0,
    1000.0,
    2000.0,
    4000.0,
    8000.0,
    16000.0,
    32000.0,
)

# End-to-end
load_duration = m.histogram(
    "load_duration_seconds",
    "load_user_memory() duration",
    [],
    buckets=_DURATION_BUCKETS,
)
load_total = m.counter(
    "load_total",
    "Memory load attempts by outcome",
    ["outcome"],
)

postprocessor_duration = m.histogram(
    "postprocessor_duration_seconds",
    "UserMemoryPostprocessor.run() duration",
    [],
    buckets=_DURATION_BUCKETS,
)
postprocessor_total = m.counter(
    "postprocessor_total",
    "Postprocessor runs by outcome",
    ["outcome"],
)

errors = m.counter(
    "errors_total",
    "User memory infrastructure failures",
    ["stage", "error_type"],
)

# LLM
llm_duration = m.histogram(
    "llm_duration_seconds",
    "User memory LLM call duration",
    ["purpose", "model"],
    buckets=_DURATION_BUCKETS,
)
llm_errors = m.counter(
    "llm_errors_total",
    "User memory LLM call failures",
    ["purpose", "model", "error_type"],
)

# Decisions
gate_decisions = m.counter(
    "gate_decisions_total",
    "Consolidation gate decisions",
    ["decision"],
)
scrub_decisions = m.counter(
    "scrub_decisions_total",
    "CID/PII scrub decisions",
    ["decision"],
)
consolidation_results = m.counter(
    "consolidation_results_total",
    "Full-profile rewrite results",
    ["result"],
)

# Storage
storage_duration = m.histogram(
    "storage_duration_seconds",
    "Folder and content store latency",
    ["op"],
    buckets=_DURATION_BUCKETS,
)
storage_total = m.counter(
    "storage_total",
    "Folder and content store calls",
    ["op", "outcome"],
)

# Size / budget
memory_length_tokens = m.histogram(
    "memory_length_tokens",
    "Memory profile size in tokens",
    ["phase"],
    buckets=_TOKEN_BUCKETS,
)
memory_length_chars = m.histogram(
    "memory_length_chars",
    "Memory profile size in characters",
    ["phase"],
    buckets=_CHAR_BUCKETS,
)
condense_total = m.counter(
    "condense_total",
    "Over-budget condensation attempts",
    ["trigger", "result"],
)


def record_error(stage: str, exc: BaseException) -> None:
    errors.labels(stage=stage, error_type=type(exc).__name__).inc()


def record_load(outcome: str) -> None:
    load_total.labels(outcome=outcome).inc()


def record_postprocessor(outcome: str) -> None:
    postprocessor_total.labels(outcome=outcome).inc()


def record_gate(decision: str) -> None:
    gate_decisions.labels(decision=decision).inc()


def record_scrub(decision: str) -> None:
    scrub_decisions.labels(decision=decision).inc()


def record_consolidation(result: str) -> None:
    consolidation_results.labels(result=result).inc()


def record_storage(op: str, outcome: str) -> None:
    storage_total.labels(op=op, outcome=outcome).inc()


def record_condense(trigger: str, result: str) -> None:
    condense_total.labels(trigger=trigger, result=result).inc()


def model_label(model_name: object) -> str:
    """Stable Prometheus label for a language-model name (enum or string)."""
    value = getattr(model_name, "value", model_name)
    return str(value)


def observe_memory_length(*, phase: str, content: str, tokens: float) -> None:
    memory_length_tokens.labels(phase=phase).observe(tokens)
    memory_length_chars.labels(phase=phase).observe(len(content))


def condense_trigger(invocation_source: str) -> str:
    if invocation_source == "user_memory_load_condense":
        return "load"
    if invocation_source == "user_memory_post_consolidation_condense":
        return "post_consolidation"
    return "condense"


@contextmanager
def observe_unlabeled(histogram: _ObservesSeconds) -> Iterator[None]:
    """Time a block on a histogram that has no labels.

    ``metric_scope`` always calls ``labels()``, which prometheus_client
    rejects when the instrument was declared with an empty label set.
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        histogram.observe(time.perf_counter() - start)


__all__ = [
    "condense_total",
    "condense_trigger",
    "consolidation_results",
    "errors",
    "gate_decisions",
    "llm_duration",
    "llm_errors",
    "load_duration",
    "load_total",
    "memory_length_chars",
    "memory_length_tokens",
    "model_label",
    "observe_memory_length",
    "observe_unlabeled",
    "postprocessor_duration",
    "postprocessor_total",
    "record_condense",
    "record_consolidation",
    "record_error",
    "record_gate",
    "record_load",
    "record_postprocessor",
    "record_scrub",
    "record_storage",
    "scrub_decisions",
    "storage_duration",
    "storage_total",
]
