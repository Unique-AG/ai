from __future__ import annotations

from typing import Any


def firecrawl_parsers(max_pdf_pages: int, pdf_mode: str = "auto") -> list[Any]:
    """Build Firecrawl ``parsers`` for the PDF page cap and reading mode.

    Args:
        max_pdf_pages (int): Most pages Firecrawl reads of each PDF.
        pdf_mode (str): ``auto``, ``fast`` or ``ocr``; ``auto`` is not sent.

    Returns:
        list[Any]: The PDF parser and ``image``, which a list would otherwise turn off.
    """
    pdf: dict[str, Any] = {"type": "pdf", "maxPages": max_pdf_pages}
    if pdf_mode != "auto":
        pdf["mode"] = pdf_mode
    return [pdf, "image"]
