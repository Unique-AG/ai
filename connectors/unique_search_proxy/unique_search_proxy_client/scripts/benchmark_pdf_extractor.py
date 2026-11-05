#!/usr/bin/env python3
"""Benchmark harness for PdfExtractor adapters (OCR disabled).

Example:
  uv run python scripts/benchmark_pdf_extractor.py
  uv run python scripts/benchmark_pdf_extractor.py --adapter pypdf --fixture ./sample.pdf
"""

from __future__ import annotations

import argparse
import asyncio
import tempfile
import time
from pathlib import Path

from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.adapters.pypdf_adapter import (
    PyPdfExtractor,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.extractor import (
    FakePdfExtractor,
    PdfExtractor,
    UnconfiguredPdfExtractor,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.runner import (
    InProcessExtractionRunner,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.types import (
    ExtractionLimits,
    ExtractionOutcome,
    ExtractionResult,
    PageChunk,
)


def _build_adapter(name: str) -> PdfExtractor:
    if name == "fake":
        return FakePdfExtractor(
            result=ExtractionResult(
                outcome=ExtractionOutcome.EXTRACTED,
                chunks=(
                    PageChunk(
                        page_number=1,
                        text=(
                            "| Agency | USD | EUR |\n| --- | --- | --- |\n"
                            "| S&P | A | AA |\n"
                        ),
                    ),
                ),
                total_page_count=1,
                adapter_name="fake",
            )
        )
    if name in {"none", "unconfigured", "off"}:
        return UnconfiguredPdfExtractor()
    if name in {"pypdf", "default"}:
        return PyPdfExtractor()
    raise SystemExit(f"Unknown adapter: {name}")


async def _run_one(
    adapter: PdfExtractor,
    path: Path,
    limits: ExtractionLimits,
) -> tuple[ExtractionResult, float]:
    runner = InProcessExtractionRunner(adapter)
    started = time.perf_counter()
    result = await runner.run(path, limits)
    return result, time.perf_counter() - started


async def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--adapter",
        default="pypdf",
        choices=("pypdf", "fake", "unconfigured", "none", "off", "default"),
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="Optional PDF path (defaults to a minimal synthetic PDF header file)",
    )
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--max-page-chars", type=int, default=20_000)
    parser.add_argument("--max-document-chars", type=int, default=100_000)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    adapter = _build_adapter(args.adapter)
    limits = ExtractionLimits(
        max_pages=args.max_pages,
        max_page_chars=args.max_page_chars,
        max_document_chars=args.max_document_chars,
        timeout_seconds=args.timeout,
        ocr_enabled=False,
    )

    if args.fixture is not None:
        path = args.fixture
        result, duration = await _run_one(adapter, path, limits)
    else:
        with tempfile.TemporaryDirectory(prefix="usp-pdf-bench-") as scratch:
            path = Path(scratch) / "fixture.pdf"
            path.write_bytes(b"%PDF-1.4\n%benchmark-fixture\n")
            result, duration = await _run_one(adapter, path, limits)

    print(f"adapter={adapter.name}")
    print(f"outcome={result.outcome.value}")
    print(f"pages={result.total_page_count}")
    print(f"chunks={len(result.chunks)}")
    print(f"duration_seconds={duration:.4f}")
    print(f"reason={result.reason}")
    if result.outcome is ExtractionOutcome.FAILED and adapter.name == "unconfigured":
        return 0
    if result.outcome in {
        ExtractionOutcome.EXTRACTED,
        ExtractionOutcome.EMPTY,
        ExtractionOutcome.UNSUPPORTED,
    }:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
