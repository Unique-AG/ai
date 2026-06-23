import logging

import pytest
from uvicorn.logging import DefaultFormatter

from unique_search_proxy_client.web.logging_config import (
    build_logging_config,
    configure_logging,
)


class TestLoggingConfig:
    @pytest.mark.ai
    def test_build_logging_config_includes_app_loggers(self) -> None:
        config = build_logging_config("debug")

        assert config["loggers"]["unique_search_proxy_client"]["handlers"] == [
            "default"
        ]
        assert config["loggers"]["unique_search_proxy_core"]["level"] == "DEBUG"
        assert config["formatters"]["default"]["()"] == (
            "uvicorn.logging.DefaultFormatter"
        )

    @pytest.mark.ai
    def test_configure_logging_uses_uvicorn_formatter(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("LOG_LEVEL", "info")
        configure_logging()

        logger = logging.getLogger("unique_search_proxy_client")
        assert logger.handlers
        assert isinstance(logger.handlers[0].formatter, DefaultFormatter)
        assert not logger.propagate
