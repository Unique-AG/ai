import importlib.util
import logging
from pathlib import Path

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.utils import get_default_headers

logger = logging.getLogger("toolkit.framework_utilities.langchain")


class LangchainNotInstalledError(ImportError):
    """Raised when langchain-openai package is not installed but functionality requiring it is accessed."""

    def __init__(self):
        super().__init__(
            "langchain-openai package is not installed. Install it with 'poetry install --with langchain'."
        )


if importlib.util.find_spec("langchain_openai") is not None:
    from langchain_openai import ChatOpenAI
else:
    raise LangchainNotInstalledError()


def get_client(env_file: Path | None = None) -> ChatOpenAI:
    """Get a Langchain ChatOpenAI client instance.

    Args:
        env_file: Optional path to environment file

    Returns:
        ChatOpenAI client instance

    Raises:
        LangchainNotInstalledError: If langchain-openai package is not installed
    """
    settings = UniqueSettings.from_env(env_file=env_file)

    return ChatOpenAI(
        base_url=settings.app.base_url + "/openai-proxy/",
        default_headers=get_default_headers(settings.app, settings.auth),
        model="AZURE_GPT_4o_2024_0806",
        api_key=settings.app.key,
    )
