"""
Reusable logging configuration for Python projects.

Usage:
    from logging_config import setup_logging
    setup_logging()                        # console only, INFO level
    setup_logging(log_file="app.log")      # console + file
    setup_logging(level="DEBUG")           # verbose

Then in any module:
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Starting process for item %s", item_id)
"""

import logging
import sys
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    fmt: str = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt: str = "%Y-%m-%d %H:%M:%S",
) -> None:
    """Configure root logger with console (and optionally file) output."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates on re-import
    root.handlers.clear()

    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    # Console handler — always added
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    # File handler — optional
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


# Example usage (remove when copying into your project):
if __name__ == "__main__":
    setup_logging(level="DEBUG", log_file="logs/app.log")
    logger = logging.getLogger(__name__)
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
