"""Tests for running chat title generation alongside the answer in UniqueAI."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from unique_toolkit.language_model.invocation_stats import (
    LanguageModelInvocationStats,
)
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

from unique_orchestrator.config import UniqueAIConfig

if TYPE_CHECKING:
    from unique_orchestrator.unique_ai import UniqueAI

MODULE = "unique_orchestrator.unique_ai_builder"

_TITLE_STATS = LanguageModelInvocationStats.from_usage(
    "title-model",
    LanguageModelTokenUsage(completion_tokens=8, prompt_tokens=56, total_tokens=64),
    source="chat_title",
)


def _make_generator(title: str | None = "Discovery Banque Audi") -> MagicMock:
    generator = MagicMock()
    generator.run = AsyncMock(return_value=title)
    generator.invocation_stats = [_TITLE_STATS]
    return generator


def _make_unique_ai(
    monkeypatch: pytest.MonkeyPatch, chat_title_generator: MagicMock | None
) -> "UniqueAI":
    monkeypatch.setitem(
        sys.modules,
        "unique_toolkit.agentic.message_log_manager.service",
        MagicMock(),
    )
    from unique_orchestrator.unique_ai import UniqueAI

    event = MagicMock()
    event.payload.assistant_message.id = "assist_1"
    event.payload.user_message.text = "expanded prompt"
    event.payload.user_message.original_text = "typed prompt"
    event.payload.skill_choices = []

    config = MagicMock()
    config.agent.experimental.open_file_tool_config.enabled = False

    chat_service = MagicMock()
    chat_service.cancellation.is_cancelled = False

    return UniqueAI(
        logger=MagicMock(),
        event=event,
        config=config,
        chat_service=chat_service,
        content_service=MagicMock(),
        debug_info_manager=MagicMock(),
        streaming_handler=MagicMock(),
        reference_manager=MagicMock(),
        thinking_manager=MagicMock(),
        tool_manager=MagicMock(),
        history_manager=MagicMock(),
        evaluation_manager=MagicMock(),
        postprocessor_manager=MagicMock(),
        message_step_logger=MagicMock(),
        mcp_servers=[],
        loop_iteration_runner=MagicMock(),
        chat_title_generator=chat_title_generator,
    )


class TestChatTitleGenerationInRun:
    @pytest.mark.ai
    async def test_without_generator__nothing_is_started(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With the feature off no task is started and nothing is awaited."""
        ua = _make_unique_ai(monkeypatch, chat_title_generator=None)

        task = ua._start_chat_title_generation()
        await ua._finish_chat_title_generation(task)

        assert task is None
        assert ua._invocation_stats == []

    @pytest.mark.ai
    async def test_title_is_generated_from_typed_prompt(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The title is based on what the user typed, not the expanded prompt."""
        generator = _make_generator()
        ua = _make_unique_ai(monkeypatch, generator)

        await ua._finish_chat_title_generation(ua._start_chat_title_generation())

        generator.run.assert_awaited_once_with("typed prompt")

    @pytest.mark.ai
    async def test_title_runs_while_the_answer_is_generated(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Starting returns at once, so the answer loop is not held back by the title."""
        started = asyncio.Event()
        release = asyncio.Event()

        async def slow_run(_: str) -> str:
            started.set()
            await release.wait()
            return "Discovery Banque Audi"

        generator = _make_generator()
        generator.run = slow_run
        ua = _make_unique_ai(monkeypatch, generator)

        task = ua._start_chat_title_generation()
        assert task is not None
        await asyncio.wait_for(started.wait(), timeout=1)
        assert not task.done()

        release.set()
        await ua._finish_chat_title_generation(task)
        assert task.done()

    @pytest.mark.ai
    async def test_token_usage_is_added_to_invocation_stats(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The title call shows up in llm_invocations next to the main loop."""
        ua = _make_unique_ai(monkeypatch, _make_generator())

        await ua._finish_chat_title_generation(ua._start_chat_title_generation())

        assert ua._invocation_stats == [_TITLE_STATS]

    @pytest.mark.ai
    async def test_cancelled_turn__title_task_is_cancelled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the user stops the answer, the title is not written either."""
        release = asyncio.Event()

        async def slow_run(_: str) -> str:
            await release.wait()
            return "Discovery Banque Audi"

        generator = _make_generator()
        generator.run = slow_run
        ua = _make_unique_ai(monkeypatch, generator)
        task = ua._start_chat_title_generation()
        assert task is not None
        ua._chat_service.cancellation.is_cancelled = True

        await ua._finish_chat_title_generation(task)
        with pytest.raises(asyncio.CancelledError):
            await task

        assert ua._invocation_stats == []

    @pytest.mark.ai
    async def test_slow_title__completion_is_not_held_back_forever(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A title that is not ready in time is dropped so the message can complete."""
        monkeypatch.setattr(
            "unique_orchestrator.unique_ai._CHAT_TITLE_WAIT_SECONDS", 0.01
        )

        async def hanging_run(_: str) -> str:
            await asyncio.Event().wait()
            return "never"

        generator = _make_generator()
        generator.run = hanging_run
        ua = _make_unique_ai(monkeypatch, generator)
        task = ua._start_chat_title_generation()

        await ua._finish_chat_title_generation(task)

        assert task is not None and task.cancelled()
        assert ua._invocation_stats == []


class TestBuildCommonChatTitle:
    @pytest.fixture(autouse=True)
    def _patch_constructors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        chat_service = MagicMock()
        chat_service.download_chat_images_and_documents_async = AsyncMock(
            return_value=([], [])
        )
        monkeypatch.setattr(f"{MODULE}.ChatService", lambda event: chat_service)
        monkeypatch.setattr(
            f"{MODULE}.LanguageModelService.from_event", lambda event: MagicMock()
        )
        monkeypatch.setattr(
            f"{MODULE}.ContentService.from_event", lambda event: MagicMock()
        )
        monkeypatch.setattr(f"{MODULE}.SubAgentResponseWatcher", MagicMock)
        monkeypatch.setattr(f"{MODULE}.ToolProgressReporter", lambda **kw: MagicMock())
        monkeypatch.setattr(f"{MODULE}.ThinkingManager", lambda **kw: MagicMock())
        monkeypatch.setattr(f"{MODULE}.ReferenceManager", MagicMock)
        monkeypatch.setattr(f"{MODULE}.EvaluationManager", lambda **kw: MagicMock())
        monkeypatch.setattr(f"{MODULE}.MCPManager", lambda **kw: MagicMock())
        monkeypatch.setattr(f"{MODULE}.A2AManager", lambda **kw: MagicMock())
        monkeypatch.setattr(f"{MODULE}.PostprocessorManager", lambda **kw: MagicMock())
        monkeypatch.setattr(f"{MODULE}.MessageStepLogger", lambda *a: MagicMock())

    @staticmethod
    def _make_event() -> MagicMock:
        event = MagicMock()
        event.payload.mcp_servers = []
        event.payload.additional_parameters = None
        return event

    @pytest.mark.ai
    async def test_flag_off__no_generator(self) -> None:
        """Without the flag the agent behaves exactly as before."""
        from unique_orchestrator.unique_ai_builder import _build_common

        result = await _build_common(self._make_event(), MagicMock(), UniqueAIConfig())

        assert result.chat_title_generator is None

    @pytest.mark.ai
    async def test_flag_on__generator_uses_space_model(self) -> None:
        """With the flag on, titles are generated with the space's model."""
        from unique_orchestrator.unique_ai_builder import _build_common

        config = UniqueAIConfig()
        result = await _build_common(
            self._make_event(),
            MagicMock(),
            config,
            enable_chat_title_generation=True,
        )

        assert result.chat_title_generator is not None
        assert result.chat_title_generator._language_model == (
            config.space.language_model
        )
