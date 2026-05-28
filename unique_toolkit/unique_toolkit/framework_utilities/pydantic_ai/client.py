import importlib.util
from typing import TYPE_CHECKING

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.client import get_async_openai_client

if TYPE_CHECKING:
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider


class PydanticAINotInstalledError(ImportError):
    """Raised when pydantic-ai is not installed but functionality requiring it is accessed."""

    def __init__(self):
        super().__init__(
            "pydantic-ai package is not installed. Install it with "
            "'uv add unique_toolkit[pydanticai]'."
        )


def _ensure_pydantic_ai_available() -> None:
    if importlib.util.find_spec("pydantic_ai") is None:
        raise PydanticAINotInstalledError()


def get_pydantic_ai_openai_provider(
    *,
    unique_settings: UniqueSettings | None = None,
    additional_headers: dict[str, str] | None = None,
) -> "OpenAIProvider":
    """Build a PydanticAI OpenAIProvider backed by Unique OpenAI proxy configuration."""
    _ensure_pydantic_ai_available()

    from pydantic_ai.providers.openai import OpenAIProvider

    openai_client = get_async_openai_client(
        unique_settings=unique_settings,
        additional_headers=additional_headers,
    )
    return OpenAIProvider(openai_client=openai_client)


def get_pydantic_ai_openai_chat_model(
    *,
    model_name: str,
    unique_settings: UniqueSettings | None = None,
    additional_headers: dict[str, str] | None = None,
) -> "OpenAIChatModel":
    """Build a PydanticAI OpenAIChatModel wired to the Unique OpenAI proxy."""
    _ensure_pydantic_ai_available()

    from pydantic_ai.models.openai import OpenAIChatModel

    provider = get_pydantic_ai_openai_provider(
        unique_settings=unique_settings,
        additional_headers=additional_headers,
    )
    return OpenAIChatModel(model_name=model_name, provider=provider)
