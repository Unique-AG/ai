from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_toolkit.evaluators.config import EvaluationMetricConfig
from unique_toolkit.evaluators.context_relevancy.utils import check_context_relevancy
from unique_toolkit.evaluators.exception import EvaluatorException
from unique_toolkit.evaluators.schemas import (
    EvaluationMetricInput,
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.language_model.schemas import LanguageModelMessages


class TestContextRelevancyUtils:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_input = MagicMock(spec=EvaluationMetricInput)
        self.mock_input.context_texts = ["Some context"]
        self.mock_input.custom_prompts = None
        self.mock_input.input_text = "Some input text"
        self.mock_input.get_joined_context_texts = MagicMock(
            return_value="Joined context"
        )

        self.mock_config = MagicMock(spec=EvaluationMetricConfig)
        self.mock_config.language_model = MagicMock()
        self.mock_config.language_model.name = "test_model"
        self.mock_config.custom_prompts = {}

        self.mock_logger = MagicMock()
        self.company_id = "test_company"

    @pytest.mark.asyncio
    async def test_check_context_relevancy_empty_context_texts(self):
        self.mock_input.validate_required_fields.return_value = None
        self.mock_input.context_texts = []

        with pytest.raises(EvaluatorException):
            await check_context_relevancy(
                self.company_id, self.mock_input, self.mock_config, self.mock_logger
            )

    @pytest.mark.asyncio
    async def test_check_context_relevancy_success(self):
        self.mock_input.validate_required_fields.return_value = None
        self.mock_input.context_texts = ["Some context"]
        self.mock_input.input_text = "Some input"
        self.mock_input.get_joined_context_texts.return_value = "Joined context"

        with (
            patch(
                "unique_toolkit.evaluators.context_relevancy.utils._get_msgs"
            ) as mock_get_msgs,
            patch(
                "unique_toolkit.language_model.service.LanguageModelService.complete_async_util"
            ) as mock_complete_async_util,
            patch(
                "unique_toolkit.evaluators.context_relevancy.utils.parse_eval_metric_result"
            ) as mock_parse_result,
        ):
            mock_get_msgs.return_value = MagicMock(spec=LanguageModelMessages)
            mock_complete_async_util.return_value = AsyncMock()
            mock_complete_async_util.return_value.choices = [MagicMock()]
            mock_complete_async_util.return_value.choices[
                0
            ].message.content = "Test content"
            mock_parse_result.return_value = MagicMock(spec=EvaluationMetricResult)

            result = await check_context_relevancy(
                self.company_id, self.mock_input, self.mock_config, self.mock_logger
            )

            assert result is not None
            self.mock_input.validate_required_fields.assert_called_once()
            mock_get_msgs.assert_called_once_with(self.mock_input, self.mock_config)
            mock_complete_async_util.assert_called_once()
            mock_parse_result.assert_called_once_with(
                "Test content", EvaluationMetricName.CONTEXT_RELEVANCY
            )

    @pytest.mark.asyncio
    async def test_check_context_relevancy_missing_fields(self):
        message = "Missing required fields"
        self.mock_input.validate_required_fields.side_effect = EvaluatorException(
            error_message=message, user_message=message
        )

        with pytest.raises(EvaluatorException, match="Missing required fields"):
            await check_context_relevancy(
                self.company_id, self.mock_input, self.mock_config, self.mock_logger
            )

    @pytest.mark.asyncio
    async def test_check_context_relevancy_empty_result(self):
        self.mock_input.validate_required_fields.return_value = None
        self.mock_input.context_texts = ["Some context"]

        with (
            patch(
                "unique_toolkit.evaluators.context_relevancy.utils._get_msgs"
            ) as mock_get_msgs,
            patch(
                "unique_toolkit.language_model.service.LanguageModelService.complete_async_util"
            ) as mock_complete_async_util,
        ):
            mock_get_msgs.return_value = MagicMock(spec=LanguageModelMessages)
            mock_complete_async_util.return_value = AsyncMock()
            mock_complete_async_util.return_value.choices = [MagicMock()]
            mock_complete_async_util.return_value.choices[0].message.content = None

            with pytest.raises(
                EvaluatorException,
                match="Context relevancy evaluation did not return a result.",
            ):
                await check_context_relevancy(
                    self.company_id, self.mock_input, self.mock_config, self.mock_logger
                )

    @pytest.mark.asyncio
    async def test_check_context_relevancy_exception(self):
        self.mock_input.validate_required_fields.return_value = None
        self.mock_input.context_texts = ["Some context"]

        with (
            patch(
                "unique_toolkit.evaluators.context_relevancy.utils._get_msgs"
            ) as mock_get_msgs,
            patch(
                "unique_toolkit.language_model.service.LanguageModelService.complete_async_util"
            ) as mock_complete_async_util,
        ):
            mock_get_msgs.return_value = MagicMock(spec=LanguageModelMessages)
            mock_complete_async_util.side_effect = Exception("Test exception")

            with pytest.raises(
                EvaluatorException,
                match="Error occurred during context relevancy metric analysis",
            ):
                await check_context_relevancy(
                    self.company_id, self.mock_input, self.mock_config, self.mock_logger
                )

    @pytest.mark.asyncio
    async def test_check_context_relevancy_logging(self):
        self.mock_input.validate_required_fields.return_value = None
        self.mock_input.context_texts = ["Some context"]

        with (
            patch(
                "unique_toolkit.evaluators.context_relevancy.utils._get_msgs"
            ) as mock_get_msgs,
            patch(
                "unique_toolkit.language_model.service.LanguageModelService.complete_async_util"
            ) as mock_complete_async_util,
            patch(
                "unique_toolkit.evaluators.context_relevancy.utils.parse_eval_metric_result"
            ),
        ):
            mock_get_msgs.return_value = MagicMock(spec=LanguageModelMessages)
            mock_complete_async_util.return_value = AsyncMock()
            mock_complete_async_util.return_value.choices = [MagicMock()]
            mock_complete_async_util.return_value.choices[
                0
            ].message.content = "Test content"

            await check_context_relevancy(
                self.company_id, self.mock_input, self.mock_config, self.mock_logger
            )

            self.mock_logger.info.assert_called_once_with(
                "Analyzing context relevancy with test_model."
            )
