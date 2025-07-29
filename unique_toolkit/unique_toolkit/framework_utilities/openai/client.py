import importlib.util
import logging
from pathlib import Path

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.utils import get_default_headers

logger = logging.getLogger("toolkit.framework_utilities.openai")


class OpenAINotInstalledError(ImportError):
    """Raised when OpenAI package is not installed but functionality requiring it is accessed."""

    def __init__(self):
        super().__init__(
            "OpenAI package is not installed. Install it with 'poetry install --with openai'."
        )


if importlib.util.find_spec("openai") is not None:
    from openai import OpenAI
else:
    raise OpenAINotInstalledError()


def get_openai_client(env_file: Path | None = None) -> OpenAI:
    """Get an OpenAI client instance.

    Args:
        env_file: Optional path to environment file

    Returns:
        OpenAI client instance

    Raises:
        OpenAINotInstalledError: If OpenAI package is not installed
    """
    settings = UniqueSettings.from_env(env_file=env_file)
    default_headers = get_default_headers(settings.app, settings.auth)

    return OpenAI(
        api_key=settings.app.key.get_secret_value(),
        base_url=settings.app.base_url + "/openai-proxy/",
        default_headers=default_headers,
    )
