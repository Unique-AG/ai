from logging import Formatter
from logging.config import dictConfig
from time import gmtime


class UTCFormatter(Formatter):
    converter = gmtime

log_config = {
    "version": 1,
    "root": {"level": "DEBUG", "handlers": ["console"]},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "utc",
        },
        "formatters": {
            "utc": {
                "()": UTCFormatter,
                "format": "%(asctime)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
    },
}

def load_logging_config():
    return dictConfig(log_config)
