import logging

import pytest

from unique_search_proxy_core.logging import (
    HttpxRequestLogFilter,
    suppress_httpx_request_logs,
)


class TestHttpxRequestLogFilter:
    @pytest.mark.ai
    def test_blocks_httpx_request_info_lines(self) -> None:
        record = logging.LogRecord(
            name="httpx",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg='HTTP Request: GET https://example.com?q=secret "HTTP/1.1 200 OK"',
            args=(),
            exc_info=None,
        )
        assert HttpxRequestLogFilter().filter(record) is False

    @pytest.mark.ai
    def test_allows_other_httpx_messages(self) -> None:
        record = logging.LogRecord(
            name="httpx",
            level=logging.WARNING,
            pathname=__file__,
            lineno=1,
            msg="Connection pool timeout",
            args=(),
            exc_info=None,
        )
        assert HttpxRequestLogFilter().filter(record) is True

    @pytest.mark.ai
    def test_allows_other_loggers(self) -> None:
        record = logging.LogRecord(
            name="urllib3",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="HTTP Request: GET https://example.com",
            args=(),
            exc_info=None,
        )
        assert HttpxRequestLogFilter().filter(record) is True

    @pytest.mark.ai
    def test_suppress_is_idempotent(self) -> None:
        suppress_httpx_request_logs()
        httpx_logger = logging.getLogger("httpx")
        count = sum(isinstance(f, HttpxRequestLogFilter) for f in httpx_logger.filters)
        assert count >= 1
        suppress_httpx_request_logs()
        assert (
            sum(isinstance(f, HttpxRequestLogFilter) for f in httpx_logger.filters)
            == count
        )
