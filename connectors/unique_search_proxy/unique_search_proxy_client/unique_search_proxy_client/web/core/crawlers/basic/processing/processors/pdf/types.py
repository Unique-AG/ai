from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class ExtractionOutcome(StrEnum):
    EXTRACTED = "extracted"
    EMPTY = "empty"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"


class ScanVerdict(StrEnum):
    CLEAN = "clean"
    MALICIOUS = "malicious"
    UNAVAILABLE = "unavailable"
    SKIPPED = "skipped"


class ScanPolicy(StrEnum):
    """Whether a missing or unavailable scanner blocks extraction."""

    DISABLED = "disabled"
    REQUIRED = "required"


@dataclass(frozen=True, slots=True)
class ExtractionLimits:
    max_pages: int
    max_page_chars: int
    max_document_chars: int
    timeout_seconds: float
    ocr_enabled: bool = False


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
    duration_seconds: float = 0.0
    reason: str | None = None
    adapter_name: str = "unknown"


@dataclass(frozen=True, slots=True)
class AdmittedPdf:
    """PDF bytes admitted after MIME and header checks."""

    path: Path
    byte_size: int
    media_type: str = "application/pdf"


@dataclass(frozen=True, slots=True)
class ScanResult:
    verdict: ScanVerdict
    reason: str | None = None
    scanner_name: str = "unknown"


@dataclass(frozen=True, slots=True)
class HeldPdfDocument:
    document_id: str
    token: str
    expires_at_epoch: float
    byte_size: int
    payload: bytes = field(repr=False)
    page_count: int | None = None


__all__ = [
    "AdmittedPdf",
    "ExtractionLimits",
    "ExtractionOutcome",
    "ExtractionResult",
    "HeldPdfDocument",
    "PageChunk",
    "ScanPolicy",
    "ScanResult",
    "ScanVerdict",
]
