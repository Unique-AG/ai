import importlib.util
import logging

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


def get_client(
    unique_settings: UniqueSettings | None = None, model: str = "AZURE_GPT_4o_2024_0806"
) -> ChatOpenAI:
    """Get a Langchain ChatOpenAI client instance.

    Args:
        unique_settings: UniqueSettings instance

    Returns:
        ChatOpenAI client instance

    Raises:
        LangchainNotInstalledError: If langchain-openai package is not installed
    """
    if unique_settings is None:
        unique_settings = UniqueSettings.from_env_auto()

    return ChatOpenAI(
        base_url=unique_settings.api.openai_proxy_url(),
        default_headers=get_default_headers(unique_settings.app, unique_settings.auth),
        model=model,
        api_key=unique_settings.app.key,
    )
