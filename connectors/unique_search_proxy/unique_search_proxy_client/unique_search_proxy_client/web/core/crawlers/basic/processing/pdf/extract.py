from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import math
import sys
import time
import weakref
from dataclasses import dataclass
from pathlib import Path

from unique_search_proxy_client.web.monitoring.metrics import (
    record_pdf_extraction,
    record_pdf_extraction_wait,
)
from unique_search_proxy_client.web.settings.pdf import pdf_settings

_LOGGER = logging.getLogger(__name__)

_WORKER_SCRIPT = Path(__file__).with_name("worker.py")
_PDF_MEDIA_TYPE = "application/pdf"
# The header must start within the first 1024 bytes (ISO 32000-1, 7.5.2).
_PDF_HEADER = b"%PDF-"
_PDF_HEADER_WINDOW = 1024
_READ_CHUNK_BYTES = 64 * 1024
# JSON escapes one character into at most six bytes; the rest is framing.
_OUTPUT_BYTES_PER_CHAR = 6
_OUTPUT_OVERHEAD_BYTES = 4096

# Failures that depend only on the file's bytes say so, so agents do not fetch it
# again. A timeout or crash can depend on load, and a server can send a different
# body next time, so those messages leave retrying open.
_FAILURE_MESSAGES = {
    "not_pdf": "The response is not a PDF file.",
    "unreadable": "The PDF could not be read; it may be damaged. Retrying will not help.",
    "encrypted": (
        "The PDF is password-protected, so its text cannot be read. "
        "Retrying will not help."
    ),
    "no_text": (
        "The PDF has no text layer; it may be a scanned document. "
        "Retrying will not help."
    ),
    "memory_limit": "The PDF needed too much memory to read. Retrying will not help.",
    "failed": "Reading the PDF failed.",
}

_SLOTS: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = (
    weakref.WeakKeyDictionary()
)


class PdfExtractionError(Exception):
    """No text could be read from a PDF; ``outcome`` is the metrics label."""

    def __init__(self, outcome: str, message: str) -> None:
        super().__init__(message)
        self.outcome = outcome
        self.message = message


@dataclass(frozen=True, slots=True)
class PdfText:
    text: str
    total_pages: int
    pages_read: int
    truncated: bool

    @property
    def content(self) -> str:
        """Crawl content, led by a note when the PDF was cut short."""
        if not self.truncated:
            return self.text
        note = (
            "[This PDF is too large to include in full, so its text is truncated. "
            f"The text below stops at page {self.pages_read} of {self.total_pages}.]"
        )
        return f"{note}\n\n{self.text}"


async def extract_pdf_text(body: bytes, *, timeout: float) -> PdfText:
    """Read the text layer of ``body`` in a separate, resource-limited process.

    Raises ``PdfExtractionError`` for every failure, so one bad PDF only fails its
    own URL. Cancellation (the crawl deadline) kills the process.
    """
    if _PDF_HEADER not in body[:_PDF_HEADER_WINDOW]:
        record_pdf_extraction("not_pdf", 0.0)
        raise PdfExtractionError("not_pdf", _FAILURE_MESSAGES["not_pdf"])

    queued_at = time.monotonic()
    started_at: float | None = None
    outcome = "cancelled"
    page_count: int | None = None
    try:
        async with _extraction_slot():
            started_at = time.monotonic()
            record_pdf_extraction_wait(started_at - queued_at)
            result = await _run_worker(
                body,
                media_type=_PDF_MEDIA_TYPE,
                timeout=timeout,
            )
        outcome = "truncated" if result.truncated else "extracted"
        page_count = result.total_pages
        return result
    except PdfExtractionError as exc:
        outcome = exc.outcome
        raise
    except Exception as exc:
        outcome = "failed"
        _LOGGER.exception("PDF extraction failed unexpectedly")
        raise PdfExtractionError("failed", _FAILURE_MESSAGES["failed"]) from exc
    finally:
        duration = 0.0 if started_at is None else time.monotonic() - started_at
        record_pdf_extraction(outcome, duration, page_count)


def _extraction_slot() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    slot = _SLOTS.get(loop)
    if slot is None:
        slot = asyncio.Semaphore(pdf_settings.max_concurrent_extractions)
        _SLOTS[loop] = slot
    return slot


async def _run_worker(body: bytes, *, media_type: str, timeout: float) -> PdfText:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-I",
        str(_WORKER_SCRIPT),
        media_type,
        str(pdf_settings.max_pdf_pages),
        str(pdf_settings.max_extracted_chars),
        str(pdf_settings.max_extraction_memory_bytes),
        str(math.ceil(timeout) + 1),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        env={},
    )
    output_limit = (
        pdf_settings.max_extracted_chars * _OUTPUT_BYTES_PER_CHAR
        + _OUTPUT_OVERHEAD_BYTES
    )
    try:
        async with asyncio.timeout(timeout):
            stdout = await _exchange(process, body, output_limit=output_limit)
    except TimeoutError as exc:
        raise PdfExtractionError(
            "timeout",
            f"Reading the PDF took longer than {timeout:g}s.",
        ) from exc
    finally:
        if process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                process.kill()
            await process.wait()

    if process.returncode != 0:
        # Killed by its CPU or memory limit, or crashed.
        raise PdfExtractionError("failed", _FAILURE_MESSAGES["failed"])
    return _parse_worker_output(stdout)


async def _exchange(
    process: asyncio.subprocess.Process,
    body: bytes,
    *,
    output_limit: int,
) -> bytes:
    stdin, stdout = process.stdin, process.stdout
    if stdin is None or stdout is None:
        raise RuntimeError("PDF worker pipes are not open")

    stdin.write(body)
    # A worker that already died shows up as a non-zero exit code below.
    with contextlib.suppress(BrokenPipeError, ConnectionResetError):
        await stdin.drain()
    stdin.close()

    chunks: list[bytes] = []
    size = 0
    while chunk := await stdout.read(_READ_CHUNK_BYTES):
        size += len(chunk)
        if size > output_limit:
            raise PdfExtractionError("failed", _FAILURE_MESSAGES["failed"])
        chunks.append(chunk)
    await process.wait()
    return b"".join(chunks)


def _parse_worker_output(stdout: bytes) -> PdfText:
    try:
        payload = json.loads(stdout)
        status = payload["status"]
        if status == "ok":
            return PdfText(
                text=str(payload["text"]),
                total_pages=int(payload["total_pages"]),
                pages_read=int(payload["pages_read"]),
                truncated=bool(payload["truncated"]),
            )
    except (ValueError, KeyError, TypeError) as exc:
        raise PdfExtractionError("failed", _FAILURE_MESSAGES["failed"]) from exc

    outcome = (
        status if isinstance(status, str) and status in _FAILURE_MESSAGES else "failed"
    )
    raise PdfExtractionError(outcome, _FAILURE_MESSAGES[outcome])


__all__ = [
    "PdfExtractionError",
    "PdfText",
    "extract_pdf_text",
]
