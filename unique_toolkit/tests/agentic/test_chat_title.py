from unittest.mock import AsyncMock, MagicMock

import pytest
from unique_sdk import UniqueError

from unique_toolkit.agentic.chat_title import ChatTitleGenerator
from unique_toolkit.agentic.chat_title.service import (
    INVOCATION_SOURCE,
    clean_title,
    without_reasoning_options,
)
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelCompletionChoice,
    LanguageModelResponse,
    LanguageModelTokenUsage,
)

_MODEL = LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_56_LUNA_2026_0709)
_PROMPT = "Prépare la discovery pour Banque Audi: contexte, parties prenantes, risques."


def _response(content: str, usage: LanguageModelTokenUsage | None = None):
    return LanguageModelResponse(
        choices=[
            LanguageModelCompletionChoice(
                index=0,
                message=LanguageModelAssistantMessage(content=content),
                finish_reason="stop",
            )
        ],
        usage=usage,
    )


@pytest.fixture
def chat_service() -> MagicMock:
    service = MagicMock()
    service.get_full_history_async = AsyncMock(return_value=[])
    service.update_chat_title_async = AsyncMock()
    return service


@pytest.fixture
def llm_service() -> MagicMock:
    service = MagicMock()
    service.complete_async = AsyncMock(return_value=_response("Discovery Banque Audi"))
    return service


@pytest.fixture
def logger() -> MagicMock:
    return MagicMock()


@pytest.fixture
def generator(
    chat_service: MagicMock, llm_service: MagicMock, logger: MagicMock
) -> ChatTitleGenerator:
    return ChatTitleGenerator(
        logger=logger,
        chat_service=chat_service,
        llm_service=llm_service,
        language_model=_MODEL,
    )


class TestWithoutReasoningOptions:
    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("model_name", "expected"),
        [
            (LanguageModelName.AZURE_GPT_4o_2024_1120, {}),
            (
                LanguageModelName.AZURE_GPT_56_LUNA_2026_0709,
                {"reasoning_effort": "none"},
            ),
            (LanguageModelName.ANTHROPIC_CLAUDE_OPUS_4_5, {}),
            (
                LanguageModelName.AZURE_GPT_6_ASTRA_2026_0903,
                {"reasoning_effort": "low"},
            ),
        ],
    )
    def test_picks_least_reasoning_per_model(
        self, model_name: LanguageModelName, expected: dict[str, str]
    ) -> None:
        """No reasoning where the model allows it, else its lightest effort.

        Claude reasons only when an effort is set, so it gets none.
        """
        model = LanguageModelInfo.from_name(model_name)

        assert without_reasoning_options(model) == expected


class TestCleanTitle:
    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Discovery Banque Audi", "Discovery Banque Audi"),
            ('"Discovery Banque Audi."', "Discovery Banque Audi"),
            ("**Discovery Banque Audi**", "Discovery Banque Audi"),
            ("\n  Discovery   Banque Audi  \n", "Discovery Banque Audi"),
            ("«Stratégie FFG»", "Stratégie FFG"),
        ],
    )
    def test_normalises_model_reply(self, raw: str, expected: str) -> None:
        """Quotes, markdown, trailing punctuation and extra whitespace are removed."""
        assert clean_title(raw) == expected

    @pytest.mark.ai
    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            '""',
            "one two three four five six seven eight nine",
            "x" * 81,
        ],
    )
    def test_rejects_unusable_reply(self, raw: str) -> None:
        """Empty, too many words or too long replies are not used as a title."""
        assert clean_title(raw) is None


class TestChatTitleGenerator:
    @pytest.mark.ai
    async def test_run__first_turn__stores_generated_title(
        self,
        generator: ChatTitleGenerator,
        chat_service: MagicMock,
        llm_service: MagicMock,
    ) -> None:
        """On the first turn the generated title is written to the chat."""
        title = await generator.run(_PROMPT)

        assert title == "Discovery Banque Audi"
        chat_service.update_chat_title_async.assert_awaited_once_with(
            "Discovery Banque Audi", is_generated=True
        )
        call = llm_service.complete_async.await_args
        assert call.kwargs["model_name"] == _MODEL.name
        assert call.kwargs["other_options"] == {"reasoning_effort": "none"}
        assert _PROMPT in str(call.kwargs["messages"].root[1].content)

    @pytest.mark.ai
    async def test_run__chat_has_earlier_turns__does_nothing(
        self,
        generator: ChatTitleGenerator,
        chat_service: MagicMock,
        llm_service: MagicMock,
    ) -> None:
        """A chat with history keeps its title and no model call is made."""
        chat_service.get_full_history_async.return_value = [MagicMock()]

        assert await generator.run(_PROMPT) is None
        llm_service.complete_async.assert_not_awaited()
        chat_service.update_chat_title_async.assert_not_awaited()

    @pytest.mark.ai
    async def test_run__blank_prompt__does_nothing(
        self,
        generator: ChatTitleGenerator,
        chat_service: MagicMock,
        llm_service: MagicMock,
    ) -> None:
        """A blank first message (e.g. files only) is not sent to the model."""
        assert await generator.run("   ") is None
        chat_service.get_full_history_async.assert_not_awaited()
        llm_service.complete_async.assert_not_awaited()

    @pytest.mark.ai
    async def test_run__long_prompt__is_truncated(
        self, generator: ChatTitleGenerator, llm_service: MagicMock
    ) -> None:
        """Only the start of a long prompt is sent to the model."""
        await generator.run("a" * 10_000)

        user_content = str(
            llm_service.complete_async.await_args.kwargs["messages"].root[1].content
        )
        assert user_content.count("a") <= 2_100

    @pytest.mark.ai
    async def test_run__unusable_reply__keeps_title(
        self,
        generator: ChatTitleGenerator,
        chat_service: MagicMock,
        llm_service: MagicMock,
    ) -> None:
        """An unusable model reply leaves the existing title untouched."""
        llm_service.complete_async.return_value = _response("")

        assert await generator.run(_PROMPT) is None
        chat_service.update_chat_title_async.assert_not_awaited()

    @pytest.mark.ai
    async def test_run__model_error__keeps_title_and_does_not_raise(
        self,
        generator: ChatTitleGenerator,
        chat_service: MagicMock,
        llm_service: MagicMock,
    ) -> None:
        """A failing model call never propagates; the title stays as it is."""
        llm_service.complete_async.side_effect = RuntimeError("boom")

        assert await generator.run(_PROMPT) is None
        chat_service.update_chat_title_async.assert_not_awaited()

    @pytest.mark.ai
    async def test_run__title_no_longer_provisional__logs_info(
        self,
        generator: ChatTitleGenerator,
        chat_service: MagicMock,
        logger: MagicMock,
    ) -> None:
        """A 409 means the user renamed the chat first; that is expected, not a failure."""
        chat_service.update_chat_title_async.side_effect = UniqueError(
            "Chat title is no longer provisional", http_status=409
        )

        assert await generator.run(_PROMPT) is None
        logger.info.assert_called_once_with(
            "Chat title kept: it is no longer provisional."
        )
        logger.warning.assert_not_called()

    @pytest.mark.ai
    async def test_run__update_error__does_not_raise(
        self,
        generator: ChatTitleGenerator,
        chat_service: MagicMock,
        logger: MagicMock,
    ) -> None:
        """Any other rejected title update is swallowed and logged as a warning."""
        chat_service.update_chat_title_async.side_effect = UniqueError(
            "Internal server error", http_status=500
        )

        assert await generator.run(_PROMPT) is None
        logger.warning.assert_called_once()

    @pytest.mark.ai
    async def test_run__records_token_usage(
        self, generator: ChatTitleGenerator, llm_service: MagicMock
    ) -> None:
        """Token usage of the title call is reported under its own source."""
        llm_service.complete_async.return_value = _response(
            "Discovery Banque Audi",
            usage=LanguageModelTokenUsage(
                completion_tokens=8, prompt_tokens=56, total_tokens=64
            ),
        )

        await generator.run(_PROMPT)

        [stats] = generator.invocation_stats
        assert stats.source == INVOCATION_SOURCE
        assert stats.model_name == _MODEL.name
        assert stats.token_usage.total_tokens == 64
