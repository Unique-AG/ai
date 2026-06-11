import io
import logging
from logging import StreamHandler

from unique_toolkit.app.init_logging import init_logging, unique_log_config

_PRE_INIT_LOGGER_NAME = "unique_toolkit.tests.app.test_init_logging.pre_init"
_CUSTOM_CONFIG_LOGGER_NAME = "unique_toolkit.tests.app.test_init_logging.custom_config"


def test_pre_init_logger_stays_enabled_after_init_logging() -> None:
    logger = logging.getLogger(_PRE_INIT_LOGGER_NAME)
    stream = io.StringIO()
    handler = StreamHandler(stream)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    init_logging()

    assert logger.disabled is False

    logger.info("pre-init logger message")

    assert "pre-init logger message" in stream.getvalue()


def test_init_logging_merges_disable_existing_loggers_false_into_custom_config() -> (
    None
):
    logger = logging.getLogger(_CUSTOM_CONFIG_LOGGER_NAME)
    config = {**unique_log_config, "disable_existing_loggers": True}

    init_logging(config)

    assert logger.disabled is False
