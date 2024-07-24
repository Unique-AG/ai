from logging import Formatter
from logging.config import dictConfig
from time import gmtime


class UTCFormatter(Formatter):
    converter = gmtime


unique_log_config = {
    "version": 1,
    "root": {"level": "DEBUG", "handlers": ["console"]},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "utc",
        }
    },
    "formatters": {
        "utc": {
            "()": UTCFormatter,
            "format": "%(asctime)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
}


def init_logging(config: dict = unique_log_config):
    return dictConfig(config)
