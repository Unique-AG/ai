from unittest.mock import AsyncMock, Mock

import pytest

from unique_web_search.services.argument_screening import (
    DEFAULT_GUIDELINES,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT_TEMPLATE,
    ArgumentScreeningConfig,
    ArgumentScreeningException,
    ArgumentScreeningResult,
    ArgumentScreeningService,
)
from unique_web_search.services.argument_screening.exceptions import (
    ArgumentScreeningUnparseableResponseException,
)


class TestArgumentScreeningConfig:
    def test_defaults_enabled_to_false(self):
        config = ArgumentScreeningConfig()
        assert config.enabled is False

    def test_defaults_system_prompt(self):
        config = ArgumentScreeningConfig()
        assert config.system_prompt == DEFAULT_SYSTEM_PROMPT

    def test_defaults_user_prompt_template(self):
        config = ArgumentScreeningConfig()
        assert config.user_prompt_template == DEFAULT_USER_PROMPT_TEMPLATE

    def test_defaults_guidelines(self):
        config = ArgumentScreeningConfig()
        assert config.guidelines == DEFAULT_GUIDELINES

    def test_accepts_custom_values(self):
        config = ArgumentScreeningConfig(
            enabled=True,
            system_prompt="Custom system",
            user_prompt_template="Custom {{ arguments }} template {{ guidelines }}",
            guidelines="Custom guidelines",
        )
        assert config.enabled is True
        assert config.system_prompt == "Custom system"
        assert (
            config.user_prompt_template
            == "Custom {{ arguments }} template {{ guidelines }}"
        )
        assert config.guidelines == "Custom guidelines"


class TestArgumentScreeningResult:
    def test_go_result(self):
        result = ArgumentScreeningResult(go=True, reason="All clear")
        assert result.go is True
        assert result.reason == "All clear"

    def test_no_go_result(self):
        result = ArgumentScreeningResult(go=False, reason="Contains PII")
        assert result.go is False
        assert result.reason == "Contains PII"

    def test_model_validate(self):
        result = ArgumentScreeningResult.model_validate(
            {"go": False, "reason": "Sensitive data detected"}
        )
        assert result.go is False
        assert result.reason == "Sensitive data detected"


class TestArgumentScreeningException:
    def test_default_instruction(self):
        exc = ArgumentScreeningException(reason="Contains PII")
        assert "Contains PII" in str(exc)
        assert "Instruction:" in str(exc)
        assert "argument screening agent" in str(exc)

    def test_custom_instruction(self):
        exc = ArgumentScreeningException(
            reason="Bad input", instruction="Custom instruction text"
        )
        assert "Bad input" in str(exc)
        assert "Custom instruction text" in str(exc)

    def test_is_exception(self):
        exc = ArgumentScreeningException(reason="test")
        assert isinstance(exc, Exception)


class TestArgumentScreeningService:
    @pytest.fixture
    def disabled_config(self):
        return ArgumentScreeningConfig(enabled=False)

    @pytest.fixture
    def enabled_config(self):
        return ArgumentScreeningConfig(enabled=True)

    @pytest.fixture
    def mock_language_model_service(self):
        service = Mock()
        service.complete_async = AsyncMock()
        return service

    @pytest.fixture
    def mock_language_model(self):
        lm = Mock()
        lm.name = "test-model"
        return lm

    @pytest.mark.asyncio
    async def test_skips_when_disabled(
        self, disabled_config, mock_language_model_service, mock_language_model
    ):
        service = ArgumentScreeningService(
            language_model_service=mock_language_model_service,
            language_model=mock_language_model,
            config=disabled_config,
        )
        await service({"query": "test query"})
        mock_language_model_service.complete_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_allows_when_go(
        self, enabled_config, mock_language_model_service, mock_language_model
    ):
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(parsed={"go": True, "reason": "Safe query"}))
        ]
        mock_language_model_service.complete_async.return_value = mock_response

        service = ArgumentScreeningService(
            language_model_service=mock_language_model_service,
            language_model=mock_language_model,
            config=enabled_config,
        )
        await service({"query": "Python best practices"})
        mock_language_model_service.complete_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_no_go_result(
        self, enabled_config, mock_language_model_service, mock_language_model
    ):
        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    parsed={"go": False, "reason": "Contains credit card number"}
                )
            )
        ]
        mock_language_model_service.complete_async.return_value = mock_response

        service = ArgumentScreeningService(
            language_model_service=mock_language_model_service,
            language_model=mock_language_model,
            config=enabled_config,
        )
        result = await service({"query": "my card is 4111-1111-1111-1111"})

        assert result.go is False
        assert "credit card number" in result.reason

    @pytest.mark.asyncio
    async def test_raises_when_response_unparseable(
        self, enabled_config, mock_language_model_service, mock_language_model
    ):
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(parsed=None))]
        mock_language_model_service.complete_async.return_value = mock_response

        service = ArgumentScreeningService(
            language_model_service=mock_language_model_service,
            language_model=mock_language_model,
            config=enabled_config,
        )
        with pytest.raises(ArgumentScreeningUnparseableResponseException):
            await service({"query": "test query"})

    @pytest.mark.asyncio
    async def test_passes_correct_messages(
        self, mock_language_model_service, mock_language_model
    ):
        config = ArgumentScreeningConfig(
            enabled=True,
            system_prompt="System: screen this",
            user_prompt_template="Args: {{ arguments }} Rules: {{ guidelines }}",
            guidelines="No secrets allowed",
        )
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(parsed={"go": True, "reason": "OK"}))
        ]
        mock_language_model_service.complete_async.return_value = mock_response

        service = ArgumentScreeningService(
            language_model_service=mock_language_model_service,
            language_model=mock_language_model,
            config=config,
        )
        await service({"query": "hello"})

        call_args = mock_language_model_service.complete_async.call_args
        messages = call_args[0][0]

        system_msg = next(m for m in messages if m.role.value == "system")
        user_msg = next(m for m in messages if m.role.value == "user")

        assert system_msg.content == "System: screen this"
        assert "hello" in user_msg.content
        assert "No secrets allowed" in user_msg.content

    @pytest.mark.asyncio
    async def test_uses_structured_output(
        self, enabled_config, mock_language_model_service, mock_language_model
    ):
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(parsed={"go": True, "reason": "OK"}))
        ]
        mock_language_model_service.complete_async.return_value = mock_response

        service = ArgumentScreeningService(
            language_model_service=mock_language_model_service,
            language_model=mock_language_model,
            config=enabled_config,
        )
        await service({"query": "test"})

        call_kwargs = mock_language_model_service.complete_async.call_args[1]
        assert call_kwargs["structured_output_model"] is ArgumentScreeningResult
        assert call_kwargs["structured_output_enforce_schema"] is True
        assert call_kwargs["model_name"] == "test-model"
