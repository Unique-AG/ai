import logging

import pytest
from unique_search_proxy_core.context import EntryPoint, RequestContext
from uvicorn.logging import DefaultFormatter

from unique_search_proxy_client.web.context import (
    RequestContextLogFilter,
    bind_request_context,
    reset_request_context,
)
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
        assert config["formatters"]["default"]["fmt"] == (
            "%(levelprefix)s "
            "company=%(company_id)s user=%(user_id)s chat=%(chat_id)s "
            "entry=%(entry_point)s caller=%(caller)s %(message)s"
        )
        assert config["formatters"]["access"]["fmt"] == (
            "%(levelprefix)s "
            "company=%(company_id)s user=%(user_id)s chat=%(chat_id)s "
            "entry=%(entry_point)s caller=%(caller)s "
            '%(client_addr)s - "%(request_line)s" %(status_code)s'
        )
        assert config["handlers"]["default"]["filters"] == ["request_context"]
        assert config["handlers"]["access"]["filters"] == ["request_context"]

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

    @pytest.mark.ai
    def test_usage_line_is_bare_and_not_filtered_by_log_level(
        self,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        configure_logging("error")

        logging.getLogger("unique_search_proxy_core.usage").info('{"event": "x"}')

        assert capfd.readouterr().err == '{"event": "x"}\n'

    @pytest.mark.ai
    def test_request_context_filter_adds_entry_point_to_records(self) -> None:
        token = bind_request_context(
            RequestContext(
                company_id="1",
                user_id="2",
                chat_id="chat-1",
                entry_point=EntryPoint.CHAT_TOOL,
                caller="node-chat",
            ),
        )
        try:
            record = logging.LogRecord("x", logging.INFO, "", 0, "m", None, None)
            RequestContextLogFilter().filter(record)
        finally:
            reset_request_context(token)

        assert record.entry_point == "chat_tool"
        assert record.caller == "node-chat"
