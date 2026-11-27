from __future__ import annotations

from typing import Any


def firecrawl_parsers(
    max_pdf_pages: int | None,
    pdf_mode: str = "auto",
) -> list[Any] | None:
    """Firecrawl ``parsers`` for the PDF settings, or ``None`` for Firecrawl's default.

    A ``parsers`` list turns off every parser it does not name, so ``image`` is
    listed to keep Firecrawl's default image OCR on.
    """
    if max_pdf_pages is None and pdf_mode == "auto":
        return None
    pdf: dict[str, Any] = {"type": "pdf"}
    if pdf_mode != "auto":
        pdf["mode"] = pdf_mode
    if max_pdf_pages is not None:
        pdf["maxPages"] = max_pdf_pages
    return [pdf, "image"]
