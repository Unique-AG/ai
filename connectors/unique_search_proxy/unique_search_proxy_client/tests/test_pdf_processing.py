from __future__ import annotations

import asyncio
import os
import sys
import time
from collections.abc import Callable
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import pytest
from unique_search_proxy_core.schema import ProxyErrorCode

from unique_search_proxy_client.web.core.crawlers.basic.processing.errors import (
    ContentProcessingTimeoutError,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf import (
    FakePdfExtractor,
    InProcessExtractionRunner,
    PdfProcessingLimits,
    PdfProcessor,
    SubprocessExtractionRunner,
    UnconfiguredPdfExtractor,
    admit_pdf_bytes,
    join_page_chunks,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.runner import (
    PYPDF_TEXT_SCRIPT,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.types import (
    ExtractionLimits,
    ExtractionOutcome,
    ExtractionResult,
    PageChunk,
)

_PDF_BYTES = b"%PDF-1.4\n%content"


def _limits(**overrides: object) -> PdfProcessingLimits:
    base = PdfProcessingLimits(
        max_pdf_pages=50,
        max_extracted_chars=100_000,
        timeout_seconds=5.0,
    )
    if not overrides:
        return base
    data = {
        "max_pdf_pages": base.max_pdf_pages,
        "max_extracted_chars": base.max_extracted_chars,
        "timeout_seconds": base.timeout_seconds,
    }
    data.update(overrides)
    return PdfProcessingLimits(**data)  # type: ignore[arg-type]


@pytest.mark.ai
def test_admit_pdf_bytes__rejects_missing_magic() -> None:
    """
    Purpose: Verify non-PDF payloads fail admission.
    Why this matters: MIME alone is not enough to trust a download.
    Setup summary: Pass a text body with application/pdf and expect an error.
    """
    error = admit_pdf_bytes(
        b"not-a-pdf",
        media_type="application/pdf",
    )
    assert error is not None
    assert error.code == "PDF_UNSUPPORTED"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_pdf_processor__extracts_with_fake_adapter() -> None:
    """
    Purpose: Verify PdfProcessor joins fake extractor chunks into Markdown.
    Why this matters: The crawler must depend only on the extractor contract.
    Setup summary: Wire FakePdfExtractor and process a PDF.
    """
    extractor = FakePdfExtractor(
        result=ExtractionResult(
            outcome=ExtractionOutcome.EXTRACTED,
            chunks=(
                PageChunk(page_number=1, text="# Title"),
                PageChunk(page_number=2, text="Body"),
            ),
            total_page_count=2,
            adapter_name="fake",
        )
    )
    processor = PdfProcessor(
        extractor=extractor,
        runner=InProcessExtractionRunner(extractor),
    )
    outcome = await processor.process(
        _PDF_BYTES,
        url="https://example.com/doc.pdf",
        media_type="application/pdf",
        limits=_limits(),
    )
    assert outcome.error_result is None
    assert outcome.content == "# Title\n\nBody"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_pypdf_extractor__opens_real_pdf() -> None:
    """
    Purpose: Verify the default pypdf adapter parses a real PDF without licensing gates.
    Why this matters: Production extraction must work with a permissive open-source library.
    Setup summary: Write a one-page PDF with pypdf and extract it through PyPdfExtractor.
    """
    import tempfile
    from io import BytesIO
    from pathlib import Path

    from pypdf import PdfWriter

    from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.adapters.pypdf_adapter import (
        PyPdfExtractor,
    )

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)

    with tempfile.TemporaryDirectory(prefix="usp-pypdf-") as scratch:
        path = Path(scratch) / "sample.pdf"
        path.write_bytes(buffer.getvalue())
        result = await PyPdfExtractor().extract(
            path,
            ExtractionLimits(
                max_pages=50,
                max_page_chars=20_000,
                max_document_chars=100_000,
                timeout_seconds=5.0,
                ocr_enabled=False,
            ),
        )

    assert result.adapter_name == "pypdf"
    assert result.outcome is ExtractionOutcome.EMPTY
    assert result.total_page_count == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_pdf_processor__unconfigured_extractor_fails_closed() -> None:
    """
    Purpose: Verify enabling PDF without an extractor returns a typed failure.
    Why this matters: Callers must not treat unconfigured extraction as success.
    Setup summary: Use UnconfiguredPdfExtractor and assert an upstream error.
    """
    processor = PdfProcessor(extractor=UnconfiguredPdfExtractor())
    outcome = await processor.process(
        _PDF_BYTES,
        url="https://example.com/doc.pdf",
        media_type="application/pdf",
        limits=_limits(),
    )
    assert outcome.error_result is not None
    assert outcome.error_result.error is not None
    assert outcome.error_result.error.code == ProxyErrorCode.UPSTREAM_ERROR.value


@pytest.mark.ai
@pytest.mark.asyncio
async def test_pdf_processor__empty_extraction() -> None:
    """
    Purpose: Verify empty text-layer PDFs succeed with empty content.
    Why this matters: Scanned PDFs without OCR must not become hard errors.
    Setup summary: Return EMPTY from the fake extractor and assert content "".
    """
    empty = ExtractionResult(
        outcome=ExtractionOutcome.EMPTY,
        chunks=(),
        total_page_count=1,
        adapter_name="fake",
    )
    processor = PdfProcessor(
        extractor=FakePdfExtractor(result=empty),
        runner=InProcessExtractionRunner(FakePdfExtractor(result=empty)),
    )
    outcome = await processor.process(
        _PDF_BYTES,
        url="https://example.com/scan.pdf",
        media_type="application/pdf",
        limits=_limits(),
    )
    assert outcome.error_result is None
    assert outcome.content == ""


@pytest.mark.ai
def test_join_page_chunks() -> None:
    """
    Purpose: Verify page chunks join with blank-line separators.
    Why this matters: Downstream prompts expect stable Markdown boundaries.
    Setup summary: Join two chunks and assert the separator.
    """
    assert (
        join_page_chunks(
            (
                PageChunk(page_number=1, text="A"),
                PageChunk(page_number=2, text="B"),
            )
        )
        == "A\n\nB"
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_in_process_runner__maps_timeout() -> None:
    """
    Purpose: Verify the in-process runner maps timeouts to FAILED.
    Why this matters: Native hangs must surface as typed extraction failures.
    Setup summary: Use a zero timeout against a fake extractor.
    """

    class SlowExtractor(FakePdfExtractor):
        async def extract(self, path, limits):  # type: ignore[no-untyped-def]
            import asyncio

            await asyncio.sleep(1)
            return await super().extract(path, limits)

    runner = InProcessExtractionRunner(SlowExtractor())
    result = await runner.run(
        path=__import__("pathlib").Path("."),
        limits=ExtractionLimits(
            max_pages=1,
            max_page_chars=10,
            max_document_chars=10,
            timeout_seconds=0.01,
        ),
    )
    assert result.outcome is ExtractionOutcome.FAILED
    assert result.reason is not None
    assert "timed out" in result.reason.lower()


def _fake_result(*chunks: PageChunk, total_pages: int) -> FakePdfExtractor:
    return FakePdfExtractor(
        result=ExtractionResult(
            outcome=ExtractionOutcome.EXTRACTED,
            chunks=chunks,
            total_page_count=total_pages,
            adapter_name="fake",
        )
    )


async def _process(extractor: FakePdfExtractor, **limits: object) -> str | None:
    processor = PdfProcessor(
        extractor=extractor,
        runner=InProcessExtractionRunner(extractor),
    )
    outcome = await processor.process(
        _PDF_BYTES,
        url="https://example.com/doc.pdf",
        media_type="application/pdf",
        limits=_limits(**limits),
    )
    assert outcome.error_result is None
    return outcome.content


@pytest.mark.ai
@pytest.mark.asyncio
async def test_pdf_processor__truncates_over_page_limit_with_note() -> None:
    """
    Purpose: Verify a PDF over the page limit returns its first pages with a note.
    Why this matters: Long PDFs must still help the model, and it must know text is missing.
    Setup summary: The fake extractor reads 2 of 5 pages; the page limit is 2.
    """
    content = await _process(
        _fake_result(
            PageChunk(page_number=1, text="Page 1"),
            PageChunk(page_number=2, text="Page 2"),
            total_pages=5,
        ),
        max_pdf_pages=2,
    )

    assert content == (
        "[This PDF is too large to include in full, so its text is truncated. "
        "The text below stops at page 2 of 5.]\n\nPage 1\n\nPage 2"
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_pdf_processor__truncates_over_character_limit_with_note() -> None:
    """
    Purpose: Verify text over the character budget is cut, including page separators.
    Why this matters: A text-heavy PDF used to be rejected and return nothing at all.
    Setup summary: Two 10-character pages joined with a separator exceed a 20-char budget.
    """
    content = await _process(
        _fake_result(
            PageChunk(page_number=1, text="A" * 10),
            PageChunk(page_number=2, text="B" * 10),
            total_pages=2,
        ),
        max_extracted_chars=20,
    )

    assert content == (
        "[This PDF is too large to include in full, so its text is truncated. "
        "The text below stops partway through page 2 of 2.]\n\n"
        + "A" * 10
        + "\n\n"
        + "B" * 8
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_pdf_processor__records_outcome_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify each processed PDF records its outcome and page count.
    Why this matters: The metrics show adoption, truncation, failures and load.
    Setup summary: Capture record_crawl_pdf_extraction for a truncated PDF and a non-PDF.
    """
    import unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.process as process_module

    calls: list[tuple[str, int | None]] = []
    monkeypatch.setattr(
        process_module,
        "record_crawl_pdf_extraction",
        lambda outcome, _duration, page_count=None: calls.append((outcome, page_count)),
    )

    await _process(
        _fake_result(PageChunk(page_number=1, text="One"), total_pages=3),
        max_pdf_pages=1,
    )
    await PdfProcessor(extractor=FakePdfExtractor()).process(
        b"<html></html>",
        url="https://example.com/doc.pdf",
        media_type="application/pdf",
        limits=_limits(),
    )

    assert calls == [("truncated", 3), ("not_pdf", None)]


# --- SubprocessExtractionRunner ---------------------------------------------

_SUBPROCESS_LIMITS = ExtractionLimits(
    max_pages=50,
    max_page_chars=20_000,
    max_document_chars=100_000,
    timeout_seconds=10.0,
)


def _write(tmp_path: Path, pdf: bytes) -> Path:
    path = tmp_path / "document.pdf"
    path.write_bytes(pdf)
    return path


def _fake_child(tmp_path: Path, source: str) -> SubprocessExtractionRunner:
    script = tmp_path / "fake_child.py"
    script.write_text(source)
    return SubprocessExtractionRunner(
        max_concurrent=4,
        max_memory_bytes=512 * 1024 * 1024,
        script=script,
    )


def _real_runner() -> SubprocessExtractionRunner:
    return SubprocessExtractionRunner(
        max_concurrent=4,
        max_memory_bytes=512 * 1024 * 1024,
    )


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


async def _wait_for_pid(pid_file: Path) -> int:
    for _ in range(100):
        if pid_file.exists() and pid_file.read_text():
            return int(pid_file.read_text())
        await asyncio.sleep(0.05)
    raise AssertionError("fake child never started")


def _sleeping_child(pid_file: Path) -> str:
    return (
        "import os, time\n"
        f"open({str(pid_file)!r}, 'w').write(str(os.getpid()))\n"
        "time.sleep(60)\n"
    )


@pytest.mark.ai
async def test_subprocess_runner__extracts_real_pdf(
    make_pdf: Callable[[list[str]], bytes],
    tmp_path: Path,
) -> None:
    """
    Purpose: Verify the child process reads a real multi-page PDF with pypdf.
    Why this matters: This is the production path for every enabled PDF.
    Setup summary: Generate a two-page PDF and run the default pypdf child on it.
    """
    result = await _real_runner().run(
        _write(tmp_path, make_pdf(["Rating calendar 2026", "Second page"])),
        _SUBPROCESS_LIMITS,
    )

    assert result.outcome is ExtractionOutcome.EXTRACTED
    assert [chunk.text for chunk in result.chunks] == [
        "Rating calendar 2026",
        "Second page",
    ]
    assert result.total_page_count == 2
    assert result.adapter_name == "pypdf"


@pytest.mark.ai
@pytest.mark.parametrize(
    ("user_password", "outcome"),
    [("", ExtractionOutcome.EXTRACTED), ("secret", ExtractionOutcome.UNSUPPORTED)],
    ids=["copy-protected", "password-protected"],
)
async def test_subprocess_runner__handles_encrypted_pdfs(
    make_pdf: Callable[[list[str]], bytes],
    tmp_path: Path,
    user_password: str,
    outcome: ExtractionOutcome,
) -> None:
    """
    Purpose: Verify permission-only PDFs are read and password-protected ones refused.
    Why this matters: Official reports often carry permission-only encryption.
    Setup summary: Encrypt a generated PDF with an empty or a real user password.
    """
    from pypdf import PdfWriter

    writer = PdfWriter(clone_from=BytesIO(make_pdf(["Restricted report"])))
    writer.encrypt(
        user_password=user_password,
        owner_password="owner-secret",
        algorithm="AES-128",
    )
    buffer = BytesIO()
    writer.write(buffer)

    result = await _real_runner().run(
        _write(tmp_path, buffer.getvalue()),
        _SUBPROCESS_LIMITS,
    )

    assert result.outcome is outcome
    if outcome is ExtractionOutcome.UNSUPPORTED:
        assert result.reason == (
            "Encrypted PDFs are not supported. Retrying will not help."
        )


@pytest.mark.ai
async def test_subprocess_runner__kills_child_on_timeout(tmp_path: Path) -> None:
    """
    Purpose: Verify a hanging child is killed and the timeout reaches the processor.
    Why this matters: Parser hangs are pypdf's most common advisory class.
    Setup summary: Run a child that records its pid and sleeps, with a 0.5s limit.
    """
    pid_file = tmp_path / "pid"
    runner = _fake_child(tmp_path, _sleeping_child(pid_file))

    started = time.monotonic()
    with pytest.raises(TimeoutError):
        await runner.run(
            tmp_path / "unused.pdf",
            replace(_SUBPROCESS_LIMITS, timeout_seconds=0.5),
        )

    assert time.monotonic() - started < 5
    assert not _process_exists(int(pid_file.read_text()))


@pytest.mark.ai
async def test_subprocess_runner__kills_child_when_cancelled(tmp_path: Path) -> None:
    """
    Purpose: Verify cancelling the crawl (request deadline) kills the child too.
    Why this matters: A cancelled thread kept running; a process must not.
    Setup summary: Cancel a run whose child sleeps, then check its pid.
    """
    pid_file = tmp_path / "pid"
    runner = _fake_child(tmp_path, _sleeping_child(pid_file))

    task = asyncio.create_task(runner.run(tmp_path / "unused.pdf", _SUBPROCESS_LIMITS))
    pid = await _wait_for_pid(pid_file)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert not _process_exists(pid)


@pytest.mark.ai
@pytest.mark.parametrize(
    "source",
    [
        "import sys\nsys.exit(3)\n",
        "import sys\nsys.stdout.write('x' * 10_000_000)\n",
        "import sys\nsys.stdout.write('not json')\n",
        "import sys\nsys.stdout.write('[1, 2]')\n",
        'import sys\nsys.stdout.write(\'{"outcome": "bogus"}\')\n',
    ],
    ids=["crash", "oversized-output", "garbage-output", "wrong-shape", "bad-outcome"],
)
async def test_subprocess_runner__contains_misbehaving_child(
    tmp_path: Path,
    source: str,
) -> None:
    """
    Purpose: Verify a crashing or misbehaving child becomes a FAILED result.
    Why this matters: Nothing a PDF does to the child may break the crawl itself.
    Setup summary: Run children that crash, flood stdout, or print invalid output.
    """
    runner = _fake_child(tmp_path, source)

    result = await runner.run(
        tmp_path / "unused.pdf",
        replace(_SUBPROCESS_LIMITS, max_document_chars=1_000),
    )

    assert result.outcome is ExtractionOutcome.FAILED
    # A crash can depend on load, so the message leaves retrying open.
    assert "Retrying" not in (result.reason or "")


@pytest.mark.ai
async def test_subprocess_runner__child_gets_no_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify the child does not inherit the proxy's environment variables.
    Why this matters: Provider API keys live in the environment and must stay out of reach.
    Setup summary: Set a fake secret, run a child that reports its environment.
    """
    monkeypatch.setenv("SEARCH_PROXY_TEST_SECRET", "do-not-leak")
    runner = _fake_child(
        tmp_path,
        "import json, os, sys\n"
        "json.dump({'outcome': 'extracted', 'total_page_count': 1, 'chunks': "
        "[{'page_number': 1, 'text': ','.join(sorted(os.environ)), "
        "'truncated': False}]}, sys.stdout)\n",
    )

    result = await runner.run(tmp_path / "unused.pdf", _SUBPROCESS_LIMITS)

    assert result.outcome is ExtractionOutcome.EXTRACTED
    assert "SEARCH_PROXY_TEST_SECRET" not in result.chunks[0].text


@pytest.mark.ai
@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="RLIMIT_AS is only enforced on Linux, where the proxy runs",
)
async def test_subprocess_runner__memory_limit_stops_child(tmp_path: Path) -> None:
    """
    Purpose: Verify the child's memory limit stops a PDF that allocates too much.
    Why this matters: Out-of-memory inside the proxy would kill every in-flight request.
    Setup summary: Apply the real child's limits, then allocate past them.
    """
    runner = _fake_child(
        tmp_path,
        "import runpy\n"
        f"child = runpy.run_path({str(PYPDF_TEXT_SCRIPT)!r})\n"
        "child['_limit_resources'](256 * 1024 * 1024, 10)\n"
        "data = bytearray(1024 * 1024 * 1024)\n",
    )

    result = await runner.run(tmp_path / "unused.pdf", _SUBPROCESS_LIMITS)

    assert result.outcome is ExtractionOutcome.FAILED


@pytest.mark.ai
async def test_subprocess_runner__limits_concurrent_children(tmp_path: Path) -> None:
    """
    Purpose: Verify only max_concurrent children run at once per runner.
    Why this matters: Bounds the CPU and memory PDFs can take from one proxy worker.
    Setup summary: Allow one child, start two that each take 0.5s.
    """
    script = tmp_path / "slow_child.py"
    script.write_text(
        "import json, sys, time\n"
        "time.sleep(0.5)\n"
        "json.dump({'outcome': 'empty', 'chunks': [], 'total_page_count': 1}, "
        "sys.stdout)\n"
    )
    runner = SubprocessExtractionRunner(
        max_concurrent=1,
        max_memory_bytes=512 * 1024 * 1024,
        script=script,
    )

    started = time.monotonic()
    await asyncio.gather(
        runner.run(tmp_path / "unused.pdf", _SUBPROCESS_LIMITS),
        runner.run(tmp_path / "unused.pdf", _SUBPROCESS_LIMITS),
    )

    assert time.monotonic() - started >= 1.0


@pytest.mark.ai
async def test_pdf_processor__subprocess_timeout_raises_processing_timeout(
    tmp_path: Path,
) -> None:
    """
    Purpose: Verify a child timeout surfaces as ContentProcessingTimeoutError.
    Why this matters: The crawler maps it to a per-URL UPSTREAM_TIMEOUT for that URL only.
    Setup summary: Process a PDF through a runner whose child sleeps past the limit.
    """
    processor = PdfProcessor(
        extractor=FakePdfExtractor(),
        runner=_fake_child(tmp_path, _sleeping_child(tmp_path / "pid")),
    )

    with pytest.raises(ContentProcessingTimeoutError):
        await processor.process(
            _PDF_BYTES,
            url="https://example.com/doc.pdf",
            media_type="application/pdf",
            limits=_limits(timeout_seconds=0.5),
        )
