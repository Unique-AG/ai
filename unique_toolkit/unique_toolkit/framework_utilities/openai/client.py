import importlib.util
import logging

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


def get_openai_client(unique_settings: UniqueSettings) -> OpenAI:
    """Get an OpenAI client instance.

    Args:
        env_file: Optional path to environment file

    Returns:
        OpenAI client instance

    Raises:
        OpenAINotInstalledError: If OpenAI package is not installed
    """
    default_headers = get_default_headers(unique_settings.app, unique_settings.auth)

    return OpenAI(
        api_key=unique_settings.app.key.get_secret_value(),
        base_url=unique_settings.api.openai_proxy_url(),
        default_headers=default_headers,
    )
