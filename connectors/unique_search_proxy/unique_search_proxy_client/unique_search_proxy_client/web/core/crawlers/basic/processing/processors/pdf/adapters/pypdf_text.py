"""pypdf text-layer extraction without any proxy imports.

``PyPdfExtractor`` calls :func:`extract_text_layer` in-process.
``SubprocessExtractionRunner`` runs this file as a script instead:
``python -I pypdf_text.py <path> <max_pages> <max_page_chars> <max_document_chars>
<memory_bytes> <cpu_seconds>`` prints one JSON payload to stdout. As a script it
imports only the standard library and pypdf, so the child starts in tens of
milliseconds and never loads the proxy's settings or credentials.
"""

from __future__ import annotations

import json
import resource
import sys
from typing import Any

# Only on failures that depend on the file's bytes alone, so agents do not fetch
# it again. Timeouts, crashes and non-PDF responses can differ on a retry.
_NOT_RETRYABLE = " Retrying will not help."


def _clean(text: str) -> str:
    # NUL breaks downstream storage, and lone surrogates from broken font maps
    # would fail UTF-8 encoding of the whole crawl response.
    return text.replace("\x00", "").encode("utf-8", "replace").decode("utf-8")


def extract_text_layer(
    path: str,
    *,
    max_pages: int,
    max_page_chars: int,
    max_document_chars: int,
) -> dict[str, Any]:
    """Return an extraction payload (see ``extraction_result_from_payload``)."""
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as exc:
        return {"outcome": "failed", "reason": f"pypdf is not installed: {exc}"}

    try:
        reader = PdfReader(path, strict=False)
    except PdfReadError:
        return {
            "outcome": "unsupported",
            "reason": "PDF could not be parsed." + _NOT_RETRYABLE,
        }
    except Exception as exc:  # noqa: BLE001 - library boundary
        return {
            "outcome": "failed",
            "reason": f"Failed to open PDF: {exc.__class__.__name__}",
        }

    if getattr(reader, "is_encrypted", False):
        try:
            unlocked = reader.decrypt("")
        except Exception:  # noqa: BLE001 - library boundary
            unlocked = 0
        if not unlocked:
            # The page count is unreadable until the PDF is decrypted.
            return {
                "outcome": "unsupported",
                "reason": "Encrypted PDFs are not supported." + _NOT_RETRYABLE,
            }

    total_pages = len(reader.pages)
    chunks: list[dict[str, Any]] = []
    total_chars = 0
    page_limit = min(total_pages, max_pages)

    for index in range(page_limit):
        try:
            text = _clean(reader.pages[index].extract_text() or "")
        except Exception as exc:  # noqa: BLE001 - library boundary
            return {
                "outcome": "failed",
                "reason": f"Text extraction failed: {exc.__class__.__name__}",
                "total_page_count": total_pages,
            }

        truncated = False
        if len(text) > max_page_chars:
            text = text[:max_page_chars]
            truncated = True
        remaining = max_document_chars - total_chars
        if remaining <= 0:
            break
        if len(text) > remaining:
            text = text[:remaining]
            truncated = True
        total_chars += len(text)
        chunks.append(
            {"page_number": index + 1, "text": text, "truncated": truncated},
        )

    outcome = "extracted" if any(chunk["text"].strip() for chunk in chunks) else "empty"
    return {"outcome": outcome, "chunks": chunks, "total_page_count": total_pages}


def _limit_resources(memory_bytes: int, cpu_seconds: int) -> None:
    limits = (
        (resource.RLIMIT_AS, memory_bytes, memory_bytes),
        # SIGXCPU at the soft limit, SIGKILL at the hard one: a backstop for the
        # parent's wall-clock kill.
        (resource.RLIMIT_CPU, cpu_seconds, cpu_seconds + 1),
    )
    for limit, soft, hard in limits:
        try:
            resource.setrlimit(limit, (soft, hard))
        except (ValueError, OSError):
            # macOS rejects RLIMIT_AS; refuse to run unlimited where it matters.
            if sys.platform.startswith("linux"):
                raise


def main(argv: list[str]) -> int:
    path = argv[1]
    max_pages, max_page_chars, max_document_chars, memory_bytes, cpu_seconds = (
        int(arg) for arg in argv[2:7]
    )
    _limit_resources(memory_bytes, cpu_seconds)
    try:
        payload = extract_text_layer(
            path,
            max_pages=max_pages,
            max_page_chars=max_page_chars,
            max_document_chars=max_document_chars,
        )
    except MemoryError:
        payload = {"outcome": "failed", "reason": "PDF needed too much memory"}
    json.dump(payload, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
