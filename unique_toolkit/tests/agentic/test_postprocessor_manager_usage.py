from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_toolkit.agentic.postprocessor.postprocessor_manager import (
    Postprocessor,
    PostprocessorManager,
)
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage


class TestPostprocessorManagerUsage:
    """Test suite for PostprocessorManager token-usage tracking.

    Mirrors test_postprocessor_manager_execution_times.py — usage is
    collected the same way timing is, since a postprocessor's LLM call
    (e.g. FollowUpPostprocessor) is otherwise silently dropped.
    """

    @pytest.fixture
    def manager(self):
        mock_logger = MagicMock()
        mock_chat_service = MagicMock()
        return PostprocessorManager(logger=mock_logger, chat_service=mock_chat_service)

    def _make_postprocessor(
        self, name: str, usage: LanguageModelTokenUsage | None
    ) -> MagicMock:
        pp = MagicMock(spec=Postprocessor)
        pp.name = name
        pp.run = AsyncMock()
        pp.get_usage = MagicMock(return_value=usage)
        return pp

    @pytest.mark.ai
    def test_default_get_usage__base_class__returns_none(self) -> None:
        """Postprocessor.get_usage() defaults to None so existing
        postprocessors that don't make LLM calls are unaffected."""

        class NoOpPostprocessor(Postprocessor):
            async def run(self, loop_response) -> None:
                return None

        pp = NoOpPostprocessor(name="noop")
        assert pp.get_usage() is None

    @pytest.mark.ai
    def test_get_usage__no_postprocessors_run__returns_none(self, manager) -> None:
        assert manager.get_usage() is None

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_postprocessors__single_postprocessor__records_usage(
        self, manager
    ) -> None:
        pp = self._make_postprocessor(
            "follow_up",
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
        )
        mock_loop_response = MagicMock()

        await manager.execute_postprocessors(
            loop_response=mock_loop_response,
            postprocessor_instance=pp,
        )

        assert manager.get_usage() == LanguageModelTokenUsage(
            completion_tokens=10, prompt_tokens=20, total_tokens=30
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_postprocessors__multiple_postprocessors__sums_usage(
        self, manager
    ) -> None:
        pp1 = self._make_postprocessor(
            "follow_up",
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
        )
        pp2 = self._make_postprocessor(
            "user_memory",
            LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=2, total_tokens=3
            ),
        )
        mock_loop_response = MagicMock()

        await manager.execute_postprocessors(
            loop_response=mock_loop_response, postprocessor_instance=pp1
        )
        await manager.execute_postprocessors(
            loop_response=mock_loop_response, postprocessor_instance=pp2
        )

        assert manager.get_usage() == LanguageModelTokenUsage(
            completion_tokens=11, prompt_tokens=22, total_tokens=33
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_postprocessors__usage_none__not_recorded(
        self, manager
    ) -> None:
        """A postprocessor that made no LLM call (get_usage() -> None) must
        not contribute a zeroed entry — it should be entirely absent."""
        pp_with_usage = self._make_postprocessor(
            "follow_up",
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
        )
        pp_without_usage = self._make_postprocessor("citation_fixer", None)
        mock_loop_response = MagicMock()

        await manager.execute_postprocessors(
            loop_response=mock_loop_response, postprocessor_instance=pp_with_usage
        )
        await manager.execute_postprocessors(
            loop_response=mock_loop_response, postprocessor_instance=pp_without_usage
        )

        assert "citation_fixer" not in manager._usage
        assert manager.get_usage() == LanguageModelTokenUsage(
            completion_tokens=10, prompt_tokens=20, total_tokens=30
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run_postprocessors__resets_usage_between_runs(self, manager) -> None:
        """A prior run's usage must not leak into a run with no postprocessors
        registered — `run_postprocessors` clears `_usage` up front."""
        pp = self._make_postprocessor(
            "follow_up",
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
        )
        mock_loop_response = MagicMock()

        # Seed state directly (bypassing routing) so a prior run's usage exists.
        await manager.execute_postprocessors(
            loop_response=mock_loop_response, postprocessor_instance=pp
        )
        assert manager.get_usage() is not None

        # No postprocessors registered on the manager itself -> nothing to
        # re-populate usage with; reset must leave it empty, not stale.
        await manager.run_postprocessors(mock_loop_response)
        assert manager.get_usage() is None
