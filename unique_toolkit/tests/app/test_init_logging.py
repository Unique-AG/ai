"""Tests for init_logging.py functionality."""

import logging
from unittest.mock import patch

import pytest

from unique_toolkit.app.init_logging import (
    UTCFormatter,
    init_logging,
    unique_log_config,
)


@pytest.mark.ai_generated
class TestUTCFormatter:
    """Test the UTCFormatter class."""

    def test_utc_formatter_creation(self):
        """Test creating a UTCFormatter instance."""
        formatter = UTCFormatter()
        assert formatter.converter == formatter.converter  # Should be gmtime
        assert hasattr(formatter, "format")

    def test_utc_formatter_inheritance(self):
        """Test that UTCFormatter inherits from Formatter."""
        formatter = UTCFormatter()
        assert isinstance(formatter, logging.Formatter)


@pytest.mark.ai_generated
class TestUniqueLogConfig:
    """Test the unique_log_config dictionary."""

    def test_unique_log_config_structure(self):
        """Test the structure of unique_log_config."""
        assert "version" in unique_log_config
        assert "root" in unique_log_config
        assert "handlers" in unique_log_config
        assert "formatters" in unique_log_config

        assert unique_log_config["version"] == 1
        assert unique_log_config["root"]["level"] == "DEBUG"
        assert unique_log_config["root"]["handlers"] == ["console"]

        # Test handlers
        assert "console" in unique_log_config["handlers"]
        console_handler = unique_log_config["handlers"]["console"]
        assert console_handler["class"] == "logging.StreamHandler"
        assert console_handler["level"] == "DEBUG"
        assert console_handler["formatter"] == "utc"

        # Test formatters
        assert "utc" in unique_log_config["formatters"]
        utc_formatter = unique_log_config["formatters"]["utc"]
        assert utc_formatter["()"] == UTCFormatter
        assert utc_formatter["format"] == "%(asctime)s: %(message)s"
        assert utc_formatter["datefmt"] == "%Y-%m-%d %H:%M:%S"


@pytest.mark.ai_generated
class TestInitLogging:
    """Test the init_logging function."""

    @patch("unique_toolkit.app.init_logging.dictConfig")
    def test_init_logging_with_default_config(self, mock_dict_config):
        """Test init_logging with default configuration."""
        result = init_logging()

        mock_dict_config.assert_called_once_with(unique_log_config)
        assert result == mock_dict_config.return_value

    @patch("unique_toolkit.app.init_logging.dictConfig")
    def test_init_logging_with_custom_config(self, mock_dict_config):
        """Test init_logging with custom configuration."""
        custom_config = {
            "version": 1,
            "root": {"level": "INFO", "handlers": ["console"]},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "utc",
                }
            },
            "formatters": {
                "utc": {
                    "()": UTCFormatter,
                    "format": "%(asctime)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
        }

        result = init_logging(custom_config)

        mock_dict_config.assert_called_once_with(custom_config)
        assert result == mock_dict_config.return_value

    @patch("unique_toolkit.app.init_logging.dictConfig")
    def test_init_logging_returns_dict_config_result(self, mock_dict_config):
        """Test that init_logging returns the result of dictConfig."""
        result = init_logging()
        assert result == mock_dict_config.return_value
