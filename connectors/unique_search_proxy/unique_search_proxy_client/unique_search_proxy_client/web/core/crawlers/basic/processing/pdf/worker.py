"""Read the text of one document in a separate, resource-limited process.

Run as ``python -I worker.py <media_type> <max_pages> <max_chars> <memory_bytes>
<cpu_seconds>`` with the document bytes on stdin; prints one JSON object to stdout.
The parent starts it with an empty environment, and this file imports only the
standard library and the reader libraries, so a hostile file never runs next to
the proxy's settings or credentials.
"""

from __future__ import annotations

import io
import itertools
import json
import resource
import sys
from collections.abc import Callable
from typing import Any

_PAGE_SEPARATOR = "\n\n"

# Takes the file bytes, max_pages and max_chars; returns the JSON result.
Reader = Callable[[bytes, int, int], dict[str, Any]]


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


def _clean(text: str) -> str:
    # NUL breaks downstream storage, and lone surrogates from broken font maps
    # would fail UTF-8 encoding of the whole crawl response.
    return text.replace("\x00", "").encode("utf-8", "replace").decode("utf-8")


def _read_pdf(data: bytes, max_pages: int, max_chars: int) -> dict[str, Any]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted and not reader.decrypt(""):
            return {"status": "encrypted"}
        total_pages = len(reader.pages)
    except MemoryError:
        raise
    except Exception:  # noqa: BLE001 - any parser failure means unreadable
        return {"status": "unreadable"}

    parts: list[str] = []
    used = 0
    pages_read = 0
    truncated = total_pages > max_pages
    for page in itertools.islice(reader.pages, max_pages):
        pages_read += 1
        try:
            text = _clean(page.extract_text() or "").strip()
        except MemoryError:
            raise
        except Exception:  # noqa: BLE001 - keep the pages that can be read
            continue
        if not text:
            continue
        separator = _PAGE_SEPARATOR if parts else ""
        room = max_chars - used - len(separator)
        if len(text) > room:
            if room > 0:
                parts.append(separator + text[:room])
            truncated = True
            break
        parts.append(separator + text)
        used += len(separator) + len(text)

    if not parts:
        return {"status": "no_text", "total_pages": total_pages}
    return {
        "status": "ok",
        "text": "".join(parts),
        "total_pages": total_pages,
        "pages_read": pages_read,
        "truncated": truncated,
    }


# Readers by media type. To support another file type, add a reader for it here
# (it may ignore limits that do not apply to its format) and send that media type
# to this worker from the crawler. The process isolation, limits, error handling
# and metrics around the reader stay the same for every type.
_READERS: dict[str, Reader] = {
    "application/pdf": _read_pdf,
}


def main(argv: list[str]) -> int:
    media_type = argv[1]
    max_pages, max_chars, memory_bytes, cpu_seconds = (int(arg) for arg in argv[2:6])
    _limit_resources(memory_bytes, cpu_seconds)
    reader = _READERS.get(media_type)
    data = sys.stdin.buffer.read()
    try:
        result = (
            reader(data, max_pages, max_chars)
            if reader is not None
            else {"status": "unsupported"}
        )
    except MemoryError:
        result = {"status": "memory_limit"}
    json.dump(result, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
