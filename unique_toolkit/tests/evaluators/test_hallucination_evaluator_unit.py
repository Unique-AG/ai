from unittest.mock import AsyncMock, patch

import pytest

from unique_toolkit.agentic.evaluation.hallucination.service import (
    HallucinationEvaluator,
)


class TestHallucinationEvaluatorUnit:
    @pytest.mark.ai_generated
    def test_hallucination_evaluator__initializes_correctly__when_event_provided_AI(
        self, base_chat_event
    ):
        """
        Purpose: Verify that HallucinationEvaluator initializes correctly with an event.
        Why this matters: Proper initialization is critical for evaluator functionality.
        Setup summary: Use base_chat_event fixture to test initialization.
        """
        # Arrange & Act
        evaluator = HallucinationEvaluator(base_chat_event)

        # Assert
        assert evaluator.event == base_chat_event
        assert evaluator.logger is not None

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_analyze__returns_none__when_config_disabled_AI(
        self, base_chat_event, base_evaluation_input, disabled_evaluation_config
    ):
        """
        Purpose: Verify that analyze returns None when the config is disabled.
        Why this matters: Disabled evaluations should not run to save resources.
        Setup summary: Use disabled config to test early return behavior.
        """
        # Arrange
        evaluator = HallucinationEvaluator(base_chat_event)

        # Act
        result = await evaluator.analyze(
            base_evaluation_input, disabled_evaluation_config
        )

        # Assert
        assert result is None

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_analyze__calls_check_hallucination__when_config_enabled_AI(
        self,
        base_chat_event,
        base_evaluation_input,
        base_evaluation_config,
        base_evaluation_result,
    ):
        """
        Purpose: Verify that analyze calls check_hallucination when config is enabled.
        Why this matters: Core functionality must work when evaluation is enabled.
        Setup summary: Mock check_hallucination function to verify it's called correctly.
        """
        # Arrange
        evaluator = HallucinationEvaluator(base_chat_event)

        with patch(
            "unique_toolkit.agentic.evaluation.hallucination.service.check_hallucination",
            new_callable=AsyncMock,
        ) as mock_check:
            mock_check.return_value = base_evaluation_result

            # Act
            result = await evaluator.analyze(
                base_evaluation_input, base_evaluation_config
            )

            # Assert
            assert result == base_evaluation_result
            mock_check.assert_called_once_with(
                company_id=base_chat_event.company_id,
                input=base_evaluation_input,
                config=base_evaluation_config,
            )

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_analyze__returns_none__when_default_config_disabled_AI(
        self, base_chat_event, base_evaluation_input
    ):
        """
        Purpose: Verify that analyze returns None when default config is disabled.
        Why this matters: Default behavior should respect the disabled config setting.
        Setup summary: Test with default config which is disabled by default.
        """
        # Arrange
        evaluator = HallucinationEvaluator(base_chat_event)

        # Act
        result = await evaluator.analyze(base_evaluation_input)

        # Assert
        assert result is None

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_analyze__propagates_exception__when_check_hallucination_fails_AI(
        self, base_chat_event, base_evaluation_input, base_evaluation_config
    ):
        """
        Purpose: Verify that analyze propagates exceptions from check_hallucination.
        Why this matters: Error handling is critical for robust evaluation functionality.
        Setup summary: Mock check_hallucination to raise an exception.
        """
        # Arrange
        evaluator = HallucinationEvaluator(base_chat_event)
        expected_exception = Exception("Hallucination check failed")

        with patch(
            "unique_toolkit.agentic.evaluation.hallucination.service.check_hallucination",
            new_callable=AsyncMock,
        ) as mock_check:
            mock_check.side_effect = expected_exception

            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                await evaluator.analyze(base_evaluation_input, base_evaluation_config)

            assert exc_info.value == expected_exception

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_analyze__passes_correct_parameters__to_check_hallucination_AI(
        self,
        base_chat_event,
        base_evaluation_input,
        base_evaluation_config,
        base_evaluation_result,
    ):
        """
        Purpose: Verify that analyze passes correct parameters to check_hallucination.
        Why this matters: Parameter passing must be accurate for evaluation to work correctly.
        Setup summary: Mock check_hallucination and verify all parameters are passed correctly.
        """
        # Arrange
        evaluator = HallucinationEvaluator(base_chat_event)

        with patch(
            "unique_toolkit.agentic.evaluation.hallucination.service.check_hallucination",
            new_callable=AsyncMock,
        ) as mock_check:
            mock_check.return_value = base_evaluation_result

            # Act
            await evaluator.analyze(base_evaluation_input, base_evaluation_config)

            # Assert
            mock_check.assert_called_once()
            call_kwargs = mock_check.call_args[1]
            assert call_kwargs["company_id"] == base_chat_event.company_id
            assert call_kwargs["input"] == base_evaluation_input
            assert call_kwargs["config"] == base_evaluation_config
