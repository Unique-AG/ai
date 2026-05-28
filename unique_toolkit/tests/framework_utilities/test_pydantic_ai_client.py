from unittest.mock import MagicMock, patch

import pytest

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.pydantic_ai.client import (
    get_pydantic_ai_openai_chat_model,
    get_pydantic_ai_openai_provider,
)

pytest.importorskip("pydantic_ai")


def test_get_pydantic_ai_openai_provider_uses_async_openai_client() -> None:
    fake_openai_client = MagicMock()
    unique_settings = UniqueSettings.from_env_auto()

    with patch(
        "unique_toolkit.framework_utilities.pydantic_ai.client.get_async_openai_client",
        return_value=fake_openai_client,
    ) as mocked_client_factory:
        provider = get_pydantic_ai_openai_provider(unique_settings=unique_settings)

    mocked_client_factory.assert_called_once_with(
        unique_settings=unique_settings,
        additional_headers=None,
    )
    assert provider.client is fake_openai_client


def test_get_pydantic_ai_openai_chat_model_returns_openai_chat_model() -> None:
    fake_openai_client = MagicMock()
    unique_settings = UniqueSettings.from_env_auto()

    with patch(
        "unique_toolkit.framework_utilities.pydantic_ai.client.get_async_openai_client",
        return_value=fake_openai_client,
    ):
        model = get_pydantic_ai_openai_chat_model(
            model_name="gpt-4o-mini",
            unique_settings=unique_settings,
            additional_headers={"x-test-header": "1"},
        )

    assert model.client is fake_openai_client
    assert getattr(model, "model_name") == "gpt-4o-mini"
