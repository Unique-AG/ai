from __future__ import annotations

import copy
import logging
import logging.config
import os
from typing import Any

from uvicorn.config import LOG_LEVELS, LOGGING_CONFIG

_APP_LOGGER_NAMES = (
    "unique_search_proxy_client",
    "unique_search_proxy_core",
)


def build_logging_config(log_level: str | None = None) -> dict[str, Any]:
    """Extend Uvicorn's logging config with application loggers."""
    level_key = (log_level or os.getenv("LOG_LEVEL", "info")).lower()
    if level_key not in LOG_LEVELS:
        level_key = "info"
    level_name = level_key.upper()

    config = copy.deepcopy(LOGGING_CONFIG)
    for logger_name in _APP_LOGGER_NAMES:
        config["loggers"][logger_name] = {
            "handlers": ["default"],
            "level": level_name,
            "propagate": False,
        }
    config["loggers"]["uvicorn"]["level"] = level_name
    config["loggers"]["uvicorn.error"]["level"] = level_name
    config["loggers"]["uvicorn.access"]["level"] = level_name
    return config


def configure_logging(log_level: str | None = None) -> None:
    """Configure app and Uvicorn loggers with Uvicorn's colored formatter."""
    logging.config.dictConfig(build_logging_config(log_level))
