from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_toolkit.agentic.postprocessor.postprocessor_manager import (
    Postprocessor,
    PostprocessorManager,
)
from unique_toolkit.language_model.invocation_stats import (
    LanguageModelInvocationStats,
)
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

_MODEL_INFO = "gpt-4-test"


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
        self, name: str, invocation_stats: list[LanguageModelInvocationStats]
    ) -> MagicMock:
        pp = MagicMock(spec=Postprocessor)
        pp.name = name
        pp.run = AsyncMock()
        pp.get_invocation_stats = MagicMock(return_value=invocation_stats)
        return pp

    @pytest.mark.ai
    def test_default_get_invocation_stats__base_class__returns_empty_list(
        self,
    ) -> None:
        """Postprocessor.get_invocation_stats() defaults to [] so existing
        postprocessors that don't make LLM calls are unaffected."""

        class NoOpPostprocessor(Postprocessor):
            async def run(self, loop_response) -> None:
                return None

        pp = NoOpPostprocessor(name="noop")
        assert pp.get_invocation_stats() == []

    @pytest.mark.ai
    def test_get_invocation_stats__no_postprocessors_run__returns_empty_list(
        self, manager
    ) -> None:
        assert manager.get_invocation_stats() == []

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_postprocessors__single_postprocessor__records_invocation_stats(
        self, manager
    ) -> None:
        stats = LanguageModelInvocationStats.from_usage(
            _MODEL_INFO,
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
            source="follow_up",
        )
        pp = self._make_postprocessor("follow_up", [stats])
        mock_loop_response = MagicMock()

        await manager.execute_postprocessors(
            loop_response=mock_loop_response,
            postprocessor_instance=pp,
        )

        recorded = manager.get_invocation_stats()
        assert len(recorded) == 1
        assert recorded[0].source == "follow_up"
        assert recorded[0].token_usage == LanguageModelTokenUsage(
            completion_tokens=10, prompt_tokens=20, total_tokens=30
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_postprocessors__multiple_postprocessors__records_all_invocation_stats(
        self, manager
    ) -> None:
        stats1 = LanguageModelInvocationStats.from_usage(
            _MODEL_INFO,
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
            source="follow_up",
        )
        stats2 = LanguageModelInvocationStats.from_usage(
            _MODEL_INFO,
            LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=2, total_tokens=3
            ),
            source="user_memory",
        )
        pp1 = self._make_postprocessor("follow_up", [stats1])
        pp2 = self._make_postprocessor("user_memory", [stats2])
        mock_loop_response = MagicMock()

        await manager.execute_postprocessors(
            loop_response=mock_loop_response, postprocessor_instance=pp1
        )
        await manager.execute_postprocessors(
            loop_response=mock_loop_response, postprocessor_instance=pp2
        )

        recorded = manager.get_invocation_stats()
        assert len(recorded) == 2
        assert recorded[0].source == "follow_up"
        assert recorded[0].token_usage == LanguageModelTokenUsage(
            completion_tokens=10, prompt_tokens=20, total_tokens=30
        )
        assert recorded[1].source == "user_memory"
        assert recorded[1].token_usage == LanguageModelTokenUsage(
            completion_tokens=1, prompt_tokens=2, total_tokens=3
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_postprocessors__no_invocation_stats__not_recorded(
        self, manager
    ) -> None:
        """A postprocessor that made no LLM call (get_invocation_stats() -> [])
        must not contribute any entries."""
        stats = LanguageModelInvocationStats.from_usage(
            _MODEL_INFO,
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
            source="follow_up",
        )
        pp_with_stats = self._make_postprocessor("follow_up", [stats])
        pp_without_stats = self._make_postprocessor("citation_fixer", [])
        mock_loop_response = MagicMock()

        await manager.execute_postprocessors(
            loop_response=mock_loop_response, postprocessor_instance=pp_with_stats
        )
        await manager.execute_postprocessors(
            loop_response=mock_loop_response, postprocessor_instance=pp_without_stats
        )

        recorded = manager.get_invocation_stats()
        assert all(entry.source != "citation_fixer" for entry in recorded)
        assert len(recorded) == 1
        assert recorded[0].source == "follow_up"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run_postprocessors__resets_invocation_stats_between_runs(
        self, manager
    ) -> None:
        """A prior run's invocation stats must not leak into a run with no
        postprocessors registered — `run_postprocessors` clears
        `_invocation_stats` up front."""
        stats = LanguageModelInvocationStats.from_usage(
            _MODEL_INFO,
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
            source="follow_up",
        )
        pp = self._make_postprocessor("follow_up", [stats])
        mock_loop_response = MagicMock()

        # Seed state directly (bypassing routing) so a prior run's stats exist.
        await manager.execute_postprocessors(
            loop_response=mock_loop_response, postprocessor_instance=pp
        )
        assert manager.get_invocation_stats() != []

        # No postprocessors registered on the manager itself -> nothing to
        # re-populate stats with; reset must leave it empty, not stale.
        await manager.run_postprocessors(mock_loop_response)
        assert manager.get_invocation_stats() == []

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_postprocessors__preserves_producer_source(
        self, manager
    ) -> None:
        """`source` is mandatory on LanguageModelInvocationStats -- the
        manager just collects whatever each postprocessor already set,
        it does not stamp or override it."""
        stats = LanguageModelInvocationStats.from_usage(
            _MODEL_INFO,
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
            source="custom_source",
        )
        pp = self._make_postprocessor("follow_up", [stats])
        mock_loop_response = MagicMock()

        await manager.execute_postprocessors(
            loop_response=mock_loop_response, postprocessor_instance=pp
        )

        recorded = manager.get_invocation_stats()
        assert len(recorded) == 1
        assert recorded[0].source == "custom_source"
