from unittest.mock import AsyncMock, Mock

import pytest
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

from unique_web_search.schema import WebSearchDebugInfo
from unique_web_search.services.argument_screening import (
    DEFAULT_GUIDELINES,
    DEFAULT_REJECTION_RESPONSE_TEMPLATE,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT_TEMPLATE,
    ArgumentScreeningConfig,
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

    def test_defaults_organization_specific_blocked_keywords_empty(self):
        config = ArgumentScreeningConfig()
        assert config.organization_specific_blocked_keywords == []

    def test_defaults_rejection_response_template(self):
        config = ArgumentScreeningConfig()
        assert config.rejection_response_template == DEFAULT_REJECTION_RESPONSE_TEMPLATE

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

    @pytest.fixture
    def mock_message_log_callback(self):
        cb = Mock()
        cb.post_message = AsyncMock()
        cb.log_progress = AsyncMock()
        return cb

    @pytest.mark.asyncio
    async def test_skips_when_disabled(
        self,
        disabled_config,
        mock_language_model_service,
        mock_language_model,
        mock_message_log_callback,
    ):
        service = ArgumentScreeningService(
            language_model_service=mock_language_model_service,
            language_model=mock_language_model,
            config=disabled_config,
        )
        await service({"query": "test query"}, mock_message_log_callback)
        mock_language_model_service.complete_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_allows_when_go(
        self,
        enabled_config,
        mock_language_model_service,
        mock_language_model,
        mock_message_log_callback,
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
        await service({"query": "Python best practices"}, mock_message_log_callback)
        mock_language_model_service.complete_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_no_go_result(
        self,
        enabled_config,
        mock_language_model_service,
        mock_language_model,
        mock_message_log_callback,
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
        result = await service(
            {"query": "my card is 4111-1111-1111-1111"}, mock_message_log_callback
        )

        assert result.go is False
        assert "credit card number" in result.reason

    @pytest.mark.asyncio
    async def test_carries_usage_into_debug_info(
        self,
        enabled_config,
        mock_language_model_service,
        mock_language_model,
        mock_message_log_callback,
    ):
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(parsed={"go": True, "reason": "Safe query"}))
        ]
        mock_response.usage = LanguageModelTokenUsage(
            completion_tokens=5, prompt_tokens=42, total_tokens=47
        )
        mock_language_model_service.complete_async.return_value = mock_response

        service = ArgumentScreeningService(
            language_model_service=mock_language_model_service,
            language_model=mock_language_model,
            config=enabled_config,
        )
        debug_info = WebSearchDebugInfo(parameters={})
        await service(
            {"query": "Python best practices"},
            mock_message_log_callback,
            debug_info=debug_info,
        )

        assert len(debug_info.invocation_stats) == 1
        stat = debug_info.invocation_stats[0]
        assert stat.model_name == "test-model"
        assert stat.token_usage == LanguageModelTokenUsage(
            completion_tokens=5, prompt_tokens=42, total_tokens=47
        )
        assert stat.source == "web_search_argument_screening"

    @pytest.mark.asyncio
    async def test_debug_info_usage_untouched_when_screening_disabled(
        self,
        disabled_config,
        mock_language_model_service,
        mock_language_model,
        mock_message_log_callback,
    ):
        service = ArgumentScreeningService(
            language_model_service=mock_language_model_service,
            language_model=mock_language_model,
            config=disabled_config,
        )
        debug_info = WebSearchDebugInfo(parameters={})
        await service(
            {"query": "test query"}, mock_message_log_callback, debug_info=debug_info
        )

        assert debug_info.invocation_stats == []

    @pytest.mark.asyncio
    async def test_raises_when_response_unparseable(
        self,
        enabled_config,
        mock_language_model_service,
        mock_language_model,
        mock_message_log_callback,
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
            await service({"query": "test query"}, mock_message_log_callback)

    @pytest.mark.asyncio
    async def test_passes_correct_messages(
        self,
        mock_language_model_service,
        mock_language_model,
        mock_message_log_callback,
    ):
        config = ArgumentScreeningConfig(
            enabled=True,
            system_prompt="System: screen this",
            user_prompt_template="Args: {{ arguments }} Rules: {{ guidelines }}",
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
        await service({"query": "hello"}, mock_message_log_callback)

        call_args = mock_language_model_service.complete_async.call_args
        messages = call_args[0][0]

        system_msg = next(m for m in messages if m.role.value == "system")
        user_msg = next(m for m in messages if m.role.value == "user")

        assert system_msg.content == "System: screen this"
        assert "hello" in user_msg.content
        assert "Configured blocked terms:" in user_msg.content
        assert "[none configured]" in user_msg.content

    @pytest.mark.asyncio
    async def test_passes_configured_blocked_keywords_in_guidelines(
        self,
        mock_language_model_service,
        mock_language_model,
        mock_message_log_callback,
    ):
        config = ArgumentScreeningConfig(
            enabled=True,
            user_prompt_template="Args: {{ arguments }} Rules: {{ guidelines }}",
            organization_specific_blocked_keywords=["EFG", "efgbank.com"],
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
        await service({"query": "hello"}, mock_message_log_callback)

        call_args = mock_language_model_service.complete_async.call_args
        messages = call_args[0][0]
        user_msg = next(m for m in messages if m.role.value == "user")

        assert "- EFG" in user_msg.content
        assert "- efgbank.com" in user_msg.content
        assert user_msg.content.count("- EFG") == 1

    @pytest.mark.asyncio
    async def test_attaches_configured_keywords_to_custom_guidelines(
        self,
        mock_language_model_service,
        mock_language_model,
        mock_message_log_callback,
    ):
        config = ArgumentScreeningConfig(
            enabled=True,
            user_prompt_template="Args: {{ arguments }} Rules: {{ guidelines }}",
            guidelines="Custom guidelines",
            organization_specific_blocked_keywords=["EFG"],
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
        await service({"query": "hello"}, mock_message_log_callback)

        call_args = mock_language_model_service.complete_async.call_args
        messages = call_args[0][0]
        user_msg = next(m for m in messages if m.role.value == "user")

        assert "Custom guidelines" in user_msg.content
        assert "- EFG" in user_msg.content

    @pytest.mark.asyncio
    async def test_uses_structured_output(
        self,
        enabled_config,
        mock_language_model_service,
        mock_language_model,
        mock_message_log_callback,
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
        await service({"query": "test"}, mock_message_log_callback)

        call_kwargs = mock_language_model_service.complete_async.call_args[1]
        assert call_kwargs["structured_output_model"] is ArgumentScreeningResult
        assert call_kwargs["structured_output_enforce_schema"] is True
        assert call_kwargs["model_name"] == "test-model"

    def test_build_rejection_response_contains_reason(
        self, enabled_config, mock_language_model_service, mock_language_model
    ):
        service = ArgumentScreeningService(
            language_model_service=mock_language_model_service,
            language_model=mock_language_model,
            config=enabled_config,
        )
        result = ArgumentScreeningResult(go=False, reason="Contains credit card number")
        response = service.build_rejection_response(result)

        assert "Contains credit card number" in response

    def test_build_rejection_response_uses_custom_template(
        self, mock_language_model_service, mock_language_model
    ):
        config = ArgumentScreeningConfig(
            enabled=True,
            rejection_response_template="Blocked: {{ reason }}",
        )
        service = ArgumentScreeningService(
            language_model_service=mock_language_model_service,
            language_model=mock_language_model,
            config=config,
        )
        result = ArgumentScreeningResult(go=False, reason="Sensitive data")
        response = service.build_rejection_response(result)

        assert response == "Blocked: Sensitive data"
