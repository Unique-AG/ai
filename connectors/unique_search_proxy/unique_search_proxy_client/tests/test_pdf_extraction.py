from __future__ import annotations

import asyncio
import io
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path

import pytest

import unique_search_proxy_client.web.core.crawlers.basic.processing.pdf.extract as extract_module
from unique_search_proxy_client.web.core.crawlers.basic.processing.pdf import (
    PdfExtractionError,
    extract_pdf_text,
)
from unique_search_proxy_client.web.settings.pdf import PdfSettings

MakePdf = Callable[[list[str]], bytes]

_REAL_WORKER = extract_module._WORKER_SCRIPT


def _encrypt(pdf: bytes, *, user_password: str) -> bytes:
    from pypdf import PdfWriter

    writer = PdfWriter(clone_from=io.BytesIO(pdf))
    writer.encrypt(
        user_password=user_password,
        owner_password="owner-secret",
        algorithm="AES-128",
    )
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _use_settings(monkeypatch: pytest.MonkeyPatch, **overrides: object) -> None:
    monkeypatch.setattr(extract_module, "pdf_settings", PdfSettings(**overrides))


def _use_worker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source: str) -> None:
    script = tmp_path / "fake_worker.py"
    script.write_text(source)
    monkeypatch.setattr(extract_module, "_WORKER_SCRIPT", script)


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
    raise AssertionError("fake worker never started")


@pytest.mark.ai
async def test_extract_pdf_text__returns_text_of_all_pages(make_pdf: MakePdf) -> None:
    """
    Purpose: Verify a normal multi-page PDF comes back as plain text, page by page.
    Why this matters: Small, ordinary PDFs are the main case this feature serves.
    Setup summary: Extract a two-page PDF with default limits.
    """
    result = await extract_pdf_text(
        make_pdf(["Rating calendar 2026", "Second page"]),
        timeout=10,
    )

    assert result.content == "Rating calendar 2026\n\nSecond page"
    assert result.total_pages == 2
    assert result.truncated is False


@pytest.mark.ai
async def test_extract_pdf_text__truncates_long_pdf_by_pages(
    make_pdf: MakePdf,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify a PDF over the page limit returns its first pages with a note.
    Why this matters: Long PDFs must still help the model, and it must know text is missing.
    Setup summary: Limit to 2 pages and extract a 5-page PDF.
    """
    _use_settings(monkeypatch, max_pdf_pages=2)

    result = await extract_pdf_text(
        make_pdf([f"Page {number}" for number in range(1, 6)]),
        timeout=10,
    )

    assert result.truncated is True
    assert result.content == (
        "[This PDF is too large to include in full, so its text is truncated. "
        "The text below stops at page 2 of 5.]\n\nPage 1\n\nPage 2"
    )


@pytest.mark.ai
async def test_extract_pdf_text__truncates_long_pdf_by_characters(
    make_pdf: MakePdf,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify text over the character limit is cut instead of rejected.
    Why this matters: A text-heavy PDF used to return nothing at all.
    Setup summary: Limit to 20 characters and extract three 15-character pages.
    """
    _use_settings(monkeypatch, max_extracted_chars=20)

    result = await extract_pdf_text(
        make_pdf(["A" * 15, "B" * 15, "C" * 15]),
        timeout=10,
    )

    assert result.truncated is True
    assert result.text == "A" * 15 + "\n\n" + "B" * 3
    assert "stops at page 2 of 3" in result.content


@pytest.mark.ai
async def test_extract_pdf_text__reads_copy_protected_pdf(make_pdf: MakePdf) -> None:
    """
    Purpose: Verify a PDF encrypted only to restrict copying is still read.
    Why this matters: Official reports often carry permission-only encryption.
    Setup summary: Encrypt with an owner password and an empty user password.
    """
    pdf = _encrypt(make_pdf(["Restricted report"]), user_password="")

    result = await extract_pdf_text(pdf, timeout=10)

    assert result.text == "Restricted report"


@pytest.mark.ai
@pytest.mark.parametrize(
    ("body", "outcome"),
    [
        (b"<html>Not found</html>", "not_pdf"),
        (b"", "not_pdf"),
        (b"%PDF-1.7\nthis is not a pdf structure", "unreadable"),
    ],
)
async def test_extract_pdf_text__rejects_bodies_that_are_not_readable_pdfs(
    body: bytes,
    outcome: str,
) -> None:
    """
    Purpose: Verify non-PDF and damaged bodies fail with a clear outcome.
    Why this matters: Servers label error pages as PDFs; those must fail cleanly.
    Setup summary: Extract an HTML body, an empty body and a broken PDF.
    """
    with pytest.raises(PdfExtractionError) as excinfo:
        await extract_pdf_text(body, timeout=10)

    assert excinfo.value.outcome == outcome


@pytest.mark.ai
async def test_extract_pdf_text__fails_password_protected_pdf(
    make_pdf: MakePdf,
) -> None:
    """
    Purpose: Verify a PDF that needs a password fails as encrypted.
    Why this matters: The model should learn why there is no text.
    Setup summary: Encrypt with a non-empty user password.
    """
    pdf = _encrypt(make_pdf(["Secret"]), user_password="secret")

    with pytest.raises(PdfExtractionError) as excinfo:
        await extract_pdf_text(pdf, timeout=10)

    assert excinfo.value.outcome == "encrypted"


@pytest.mark.ai
async def test_extract_pdf_text__fails_pdf_without_text(make_pdf: MakePdf) -> None:
    """
    Purpose: Verify a PDF with no text layer fails as no_text.
    Why this matters: Scanned PDFs need OCR, which is out of scope; the metric tracks demand.
    Setup summary: Extract a PDF whose only page is empty.
    """
    with pytest.raises(PdfExtractionError) as excinfo:
        await extract_pdf_text(make_pdf([""]), timeout=10)

    assert excinfo.value.outcome == "no_text"


@pytest.mark.ai
async def test_worker__refuses_media_type_without_reader(make_pdf: MakePdf) -> None:
    """
    Purpose: Verify the worker only reads media types listed in its reader table.
    Why this matters: New file types must be added on purpose, never parsed by accident.
    Setup summary: Send a valid PDF to the worker labelled as a Word document.
    """
    with pytest.raises(PdfExtractionError) as excinfo:
        await extract_module._run_worker(
            make_pdf(["Text"]),
            media_type="application/msword",
            timeout=10,
        )

    assert excinfo.value.outcome == "failed"


@pytest.mark.ai
async def test_extract_pdf_text__kills_worker_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Purpose: Verify a hanging extraction is killed when its time limit is reached.
    Why this matters: Parser hangs are pypdf's most common advisory class.
    Setup summary: Use a worker that records its pid and sleeps; extract with 0.5s.
    """
    pid_file = tmp_path / "pid"
    _use_worker(
        monkeypatch,
        tmp_path,
        "import os, sys, time\n"
        f"open({str(pid_file)!r}, 'w').write(str(os.getpid()))\n"
        "time.sleep(60)\n",
    )

    started = time.monotonic()
    with pytest.raises(PdfExtractionError) as excinfo:
        await extract_pdf_text(b"%PDF-1.4", timeout=0.5)

    assert excinfo.value.outcome == "timeout"
    assert time.monotonic() - started < 5
    assert not _process_exists(int(pid_file.read_text()))


@pytest.mark.ai
async def test_extract_pdf_text__kills_worker_when_crawl_deadline_cancels_it(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Purpose: Verify cancelling the crawl (request deadline) kills the worker too.
    Why this matters: A cancelled thread kept running; a process must not.
    Setup summary: Cancel an extraction whose worker sleeps, then check its pid.
    """
    pid_file = tmp_path / "pid"
    _use_worker(
        monkeypatch,
        tmp_path,
        "import os, sys, time\n"
        f"open({str(pid_file)!r}, 'w').write(str(os.getpid()))\n"
        "time.sleep(60)\n",
    )

    task = asyncio.create_task(extract_pdf_text(b"%PDF-1.4", timeout=30))
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
    ],
    ids=["crash", "oversized-output", "garbage-output", "wrong-shape"],
)
async def test_extract_pdf_text__contains_misbehaving_worker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    source: str,
) -> None:
    """
    Purpose: Verify a crashing or misbehaving worker becomes a plain failure.
    Why this matters: Nothing a PDF does to the worker may break the crawl itself.
    Setup summary: Run workers that crash, flood stdout, or print invalid output.
    """
    _use_settings(monkeypatch, max_extracted_chars=1_000)
    _use_worker(monkeypatch, tmp_path, source)

    with pytest.raises(PdfExtractionError) as excinfo:
        await extract_pdf_text(b"%PDF-1.4", timeout=10)

    assert excinfo.value.outcome == "failed"


@pytest.mark.ai
async def test_extract_pdf_text__worker_runs_without_proxy_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Purpose: Verify the worker does not inherit the proxy's environment variables.
    Why this matters: Provider API keys live in the environment and must stay out of reach.
    Setup summary: Set a fake secret, run a worker that reports its environment.
    """
    monkeypatch.setenv("SEARCH_PROXY_TEST_SECRET", "do-not-leak")
    _use_worker(
        monkeypatch,
        tmp_path,
        "import json, os, sys\n"
        "json.dump({'status': 'ok', 'text': ','.join(sorted(os.environ)),"
        " 'total_pages': 1, 'pages_read': 1, 'truncated': False}, sys.stdout)\n",
    )

    result = await extract_pdf_text(b"%PDF-1.4", timeout=10)

    assert "SEARCH_PROXY_TEST_SECRET" not in result.text
    assert "do-not-leak" not in result.text


@pytest.mark.ai
@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="RLIMIT_AS is only enforced on Linux, where the proxy runs",
)
async def test_extract_pdf_text__memory_limit_stops_worker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Purpose: Verify the worker's memory limit stops a PDF that allocates too much.
    Why this matters: Out-of-memory inside the proxy would kill every in-flight request.
    Setup summary: Apply the real worker's limits, then allocate past them.
    """
    _use_worker(
        monkeypatch,
        tmp_path,
        "import runpy, sys\n"
        f"worker = runpy.run_path({str(_REAL_WORKER)!r})\n"
        "worker['_limit_resources'](256 * 1024 * 1024, 10)\n"
        "data = bytearray(1024 * 1024 * 1024)\n",
    )

    with pytest.raises(PdfExtractionError) as excinfo:
        await extract_pdf_text(b"%PDF-1.4", timeout=10)

    assert excinfo.value.outcome == "failed"


@pytest.mark.ai
async def test_extract_pdf_text__limits_concurrent_extractions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Purpose: Verify only the configured number of PDFs are read at once.
    Why this matters: Bounds the CPU and memory PDFs can take from one proxy worker.
    Setup summary: Allow one extraction, start two that each take 0.5s.
    """
    _use_settings(monkeypatch, max_concurrent_extractions=1)
    _use_worker(
        monkeypatch,
        tmp_path,
        "import json, sys, time\n"
        "time.sleep(0.5)\n"
        "json.dump({'status': 'ok', 'text': 'x', 'total_pages': 1,"
        " 'pages_read': 1, 'truncated': False}, sys.stdout)\n",
    )

    started = time.monotonic()
    await asyncio.gather(
        extract_pdf_text(b"%PDF-1.4", timeout=10),
        extract_pdf_text(b"%PDF-1.4", timeout=10),
    )

    assert time.monotonic() - started >= 1.0


@pytest.mark.ai
async def test_extract_pdf_text__records_outcome_metrics(
    make_pdf: MakePdf,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify each extraction records its outcome and page count.
    Why this matters: The metrics show adoption, truncation, failures and load.
    Setup summary: Capture record_pdf_extraction calls for a success and a failure.
    """
    calls: list[tuple[str, int | None]] = []
    monkeypatch.setattr(
        extract_module,
        "record_pdf_extraction",
        lambda outcome, _duration, page_count=None: calls.append((outcome, page_count)),
    )

    await extract_pdf_text(make_pdf(["One", "Two"]), timeout=10)
    with pytest.raises(PdfExtractionError):
        await extract_pdf_text(b"<html></html>", timeout=10)

    assert calls == [("extracted", 2), ("not_pdf", None)]
