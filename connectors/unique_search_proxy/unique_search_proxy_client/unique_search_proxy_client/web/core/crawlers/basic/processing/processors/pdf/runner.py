from __future__ import annotations

import asyncio
import contextlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Protocol

from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.extractor import (
    PdfExtractor,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.types import (
    ExtractionLimits,
    ExtractionOutcome,
    ExtractionResult,
    extraction_result_from_payload,
)
from unique_search_proxy_client.web.monitoring.metrics import (
    record_crawl_pdf_extraction_wait,
)

PYPDF_TEXT_SCRIPT = Path(__file__).parent / "adapters" / "pypdf_text.py"
_READ_CHUNK_BYTES = 64 * 1024
# JSON escapes one character into at most six bytes; the rest is framing.
_OUTPUT_BYTES_PER_CHAR = 6
_OUTPUT_OVERHEAD_BYTES = 64 * 1024


class ExtractionRunner(Protocol):
    """Runs an extractor under a wall-clock timeout."""

    async def run(
        self,
        path: Path,
        limits: ExtractionLimits,
    ) -> ExtractionResult: ...


class InProcessExtractionRunner:
    """In-process runner for pure-Python extractors such as pypdf."""

    def __init__(self, extractor: PdfExtractor) -> None:
        self._extractor = extractor

    async def run(
        self,
        path: Path,
        limits: ExtractionLimits,
    ) -> ExtractionResult:
        try:
            return await asyncio.wait_for(
                self._extractor.extract(path, limits),
                timeout=limits.timeout_seconds,
            )
        except TimeoutError:
            return ExtractionResult(
                outcome=ExtractionOutcome.FAILED,
                reason=(f"PDF extraction timed out after {limits.timeout_seconds}s"),
                adapter_name=self._extractor.name,
            )


class SubprocessExtractionRunner:
    """Runs pypdf in a child process with no environment, memory and CPU limits.

    At most ``max_concurrent`` run per worker; raises ``TimeoutError`` after killing the child.
    """

    def __init__(
        self,
        *,
        max_concurrent: int,
        max_memory_bytes: int,
        script: Path = PYPDF_TEXT_SCRIPT,
        adapter_name: str = "pypdf",
    ) -> None:
        self._slots = asyncio.Semaphore(max_concurrent)
        self._max_memory_bytes = max_memory_bytes
        self._script = script
        self._adapter_name = adapter_name

    async def run(
        self,
        path: Path,
        limits: ExtractionLimits,
    ) -> ExtractionResult:
        queued_at = time.monotonic()
        async with self._slots:
            record_crawl_pdf_extraction_wait(time.monotonic() - queued_at)
            return await self._run_child(path, limits)

    async def _run_child(
        self,
        path: Path,
        limits: ExtractionLimits,
    ) -> ExtractionResult:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            str(self._script),
            str(path),
            str(limits.max_pages),
            str(limits.max_page_chars),
            str(limits.max_document_chars),
            str(self._max_memory_bytes),
            str(math.ceil(limits.timeout_seconds) + 1),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env={},
        )
        output_limit = (
            limits.max_document_chars * _OUTPUT_BYTES_PER_CHAR + _OUTPUT_OVERHEAD_BYTES
        )
        try:
            async with asyncio.timeout(limits.timeout_seconds):
                stdout = await _read_capped(process, limit=output_limit)
                if stdout is not None:
                    await process.wait()
        finally:
            if process.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    process.kill()
                await process.wait()

        if stdout is None or process.returncode != 0:
            # Killed by its memory or CPU limit, crashed, or flooded its output.
            return self._failed("PDF extraction process failed")
        try:
            return extraction_result_from_payload(
                json.loads(stdout),
                adapter_name=self._adapter_name,
            )
        except ValueError:
            return self._failed("PDF extraction process returned invalid output")

    def _failed(self, reason: str) -> ExtractionResult:
        return ExtractionResult(
            outcome=ExtractionOutcome.FAILED,
            reason=reason,
            adapter_name=self._adapter_name,
        )


async def _read_capped(
    process: asyncio.subprocess.Process,
    *,
    limit: int,
) -> bytes | None:
    """Read the child's stdout, or return None once it exceeds ``limit`` bytes."""
    if process.stdout is None:
        raise RuntimeError("PDF extraction process has no stdout pipe")
    chunks: list[bytes] = []
    size = 0
    while chunk := await process.stdout.read(_READ_CHUNK_BYTES):
        size += len(chunk)
        if size > limit:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


__all__ = [
    "PYPDF_TEXT_SCRIPT",
    "ExtractionRunner",
    "InProcessExtractionRunner",
    "SubprocessExtractionRunner",
]
