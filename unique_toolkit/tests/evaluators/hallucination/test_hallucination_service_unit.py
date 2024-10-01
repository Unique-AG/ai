from unittest.mock import MagicMock, patch

import pytest

from unique_toolkit.app.schemas import Event
from unique_toolkit.evaluators.config import EvaluationMetricConfig
from unique_toolkit.evaluators.hallucination.constants import (
    hallucination_metric_default_config,
)
from unique_toolkit.evaluators.hallucination.service import HallucinationEvaluator
from unique_toolkit.evaluators.schemas import (
    EvaluationMetricInput,
    EvaluationMetricResult,
)


class TestHallucinationEvaluator:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.event = MagicMock(spec=Event)
        self.event.company_id = "test_company_id"
        self.logger = MagicMock()
        self.evaluator = HallucinationEvaluator(self.event, self.logger)
        self.mock_input = MagicMock(spec=EvaluationMetricInput)
        self.mock_config = MagicMock(spec=EvaluationMetricConfig)

    @pytest.mark.asyncio
    async def test_analyze_metric_enabled(self):
        self.mock_config.enabled = True
        expected_result = MagicMock(spec=EvaluationMetricResult)

        with patch(
            "unique_toolkit.evaluators.hallucination.service.check_hallucination_async"
        ) as mock_check_hallucination_async:
            mock_check_hallucination_async.return_value = expected_result

            result = await self.evaluator.run(self.mock_input, self.mock_config)

            assert result == expected_result
            mock_check_hallucination_async.assert_called_once_with(
                company_id=self.event.company_id,
                input=self.mock_input,
                config=self.mock_config,
            )

    @pytest.mark.asyncio
    async def test_analyze_metric_disabled(self):
        self.mock_config.enabled = False

        result = await self.evaluator.run(self.mock_input, self.mock_config)

        assert result is None
        self.logger.info.assert_called_once_with("Hallucination metric is not enabled.")

    @pytest.mark.asyncio
    async def test_analyze_with_default_config(self):
        expected_result = MagicMock(spec=EvaluationMetricResult)

        # Temporarily modify the hallucination_metric_default_config
        original_enabled = hallucination_metric_default_config.enabled
        hallucination_metric_default_config.enabled = True

        try:
            with patch(
                "unique_toolkit.evaluators.hallucination.service.check_hallucination_async"
            ) as mock_check_hallucination_async:
                mock_check_hallucination_async.return_value = expected_result

                result = await self.evaluator.run(self.mock_input)

                assert result == expected_result
                mock_check_hallucination_async.assert_called_once_with(
                    company_id=self.event.company_id,
                    input=self.mock_input,
                    config=hallucination_metric_default_config,
                )
        finally:
            # Restore the original hallucination_metric_default_config
            hallucination_metric_default_config.enabled = original_enabled

    @pytest.mark.asyncio
    async def test_analyze_exception_handling(self):
        self.mock_config.enabled = True

        with patch(
            "unique_toolkit.evaluators.hallucination.service.check_hallucination_async"
        ) as mock_check_hallucination_async:
            mock_check_hallucination_async.side_effect = Exception("Test exception")

            with pytest.raises(Exception, match="Test exception"):
                await self.evaluator.run(self.mock_input, self.mock_config)
