"""Consistent, readable logging for the demo servers and clients."""

from __future__ import annotations

import logging


def configure_logging() -> None:
    """Enable readable INFO logging for the demo servers and clients."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(name)-12s | %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet noisy third-party loggers so the demo's own `rp.*` logs stand out.
    for noisy in ("httpx", "mcp.client.streamable_http"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
