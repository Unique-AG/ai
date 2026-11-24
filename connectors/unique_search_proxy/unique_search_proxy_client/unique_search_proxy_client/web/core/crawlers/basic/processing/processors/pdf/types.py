from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ExtractionOutcome(StrEnum):
    EXTRACTED = "extracted"
    EMPTY = "empty"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ExtractionLimits:
    max_pages: int
    max_chars: int
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class PageChunk:
    page_number: int
    text: str
    truncated: bool = False


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    outcome: ExtractionOutcome
    chunks: tuple[PageChunk, ...] = ()
    total_page_count: int | None = None
    reason: str | None = None
    adapter_name: str = "unknown"


def extraction_result_from_payload(
    payload: object,
    *,
    adapter_name: str,
) -> ExtractionResult:
    """Build a result from the JSON payload of an extraction process.

    Raises ``ValueError`` when the payload does not have the expected shape.
    """
    if not isinstance(payload, dict):
        raise ValueError("Extraction payload is not an object")
    try:
        return ExtractionResult(
            outcome=ExtractionOutcome(payload["outcome"]),
            chunks=tuple(
                PageChunk(
                    page_number=int(chunk["page_number"]),
                    text=str(chunk["text"]),
                    truncated=bool(chunk["truncated"]),
                )
                for chunk in payload.get("chunks", ())
            ),
            total_page_count=(
                None
                if payload.get("total_page_count") is None
                else int(payload["total_page_count"])
            ),
            reason=None if payload.get("reason") is None else str(payload["reason"]),
            adapter_name=adapter_name,
        )
    except (KeyError, TypeError) as exc:
        raise ValueError("Extraction payload has an unexpected shape") from exc


__all__ = [
    "ExtractionLimits",
    "ExtractionOutcome",
    "ExtractionResult",
    "PageChunk",
    "extraction_result_from_payload",
]
