"""Generates a short title for a new chat from its first user message."""

from http import HTTPStatus
from logging import Logger
from typing import Any

from unique_sdk import UniqueError

from unique_toolkit.agentic.chat_title.prompts import (
    CHAT_TITLE_SYSTEM_PROMPT,
    CHAT_TITLE_USER_PROMPT_TEMPLATE,
)
from unique_toolkit.chat.service import ChatService
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.invocation_stats import (
    LanguageModelInvocationStats,
)
from unique_toolkit.language_model.service import LanguageModelService

INVOCATION_SOURCE = "chat_title"

_USER_MESSAGE_MAX_CHARS = 2_000
_TITLE_MAX_CHARS = 80
_TITLE_MAX_WORDS = 8
_COMPLETION_TIMEOUT_MS = 10_000

_WRAPPING_CHARS = "\"'`*«»“”„ \n"
_TRAILING_PUNCTUATION = ".!?"


def without_reasoning_options(language_model: LanguageModelInfo) -> dict[str, Any]:
    """Return completion options that run *language_model* with the least reasoning it allows.

    Models that accept ``none`` get it. Models that only reason when an effort is
    set (e.g. Claude) get no effort at all. Models that always reason get their
    lightest supported effort.
    """
    efforts = language_model.supported_reasoning_efforts
    if not efforts:
        return {}
    if "none" in efforts:
        return {"reasoning_effort": "none"}
    if "reasoning_effort" not in language_model.default_options:
        return {}
    return {"reasoning_effort": efforts[0]}


def clean_title(raw: str) -> str | None:
    """Normalise a model reply to a title, or ``None`` if it is not a usable title."""
    title = raw.strip(_WRAPPING_CHARS).rstrip(_TRAILING_PUNCTUATION)
    title = " ".join(title.strip(_WRAPPING_CHARS).split())

    if not title or len(title) > _TITLE_MAX_CHARS:
        return None
    if len(title.split()) > _TITLE_MAX_WORDS:
        return None
    return title


class ChatTitleGenerator:
    """Replaces the prompt-based title of a new chat with a short generated one.

    Runs once per chat: it does nothing when the chat already has earlier turns.
    Never raises; on any failure the existing title is kept. Logs carry no
    prompt or title text.
    """

    def __init__(
        self,
        *,
        logger: Logger,
        chat_service: ChatService,
        llm_service: LanguageModelService,
        language_model: LanguageModelInfo,
    ) -> None:
        self._logger = logger
        self._chat_service = chat_service
        self._llm_service = llm_service
        self._language_model = language_model
        self._invocation_stats: list[LanguageModelInvocationStats] = []

    @property
    def invocation_stats(self) -> list[LanguageModelInvocationStats]:
        return list(self._invocation_stats)

    async def run(self, user_message: str) -> str | None:
        """Generate and store a title for *user_message*. Returns the stored title."""
        self._invocation_stats = []
        user_message = user_message.strip()
        if not user_message:
            return None

        try:
            if await self._chat_service.get_full_history_async():
                return None

            title = await self._generate(user_message[:_USER_MESSAGE_MAX_CHARS])
            if title is None:
                self._logger.info("Chat title generation returned no usable title.")
                return None

            await self._chat_service.update_chat_title_async(title, is_generated=True)
        except UniqueError as e:
            if e.http_status == HTTPStatus.CONFLICT:
                self._logger.info("Chat title kept: it is no longer provisional.")
            else:
                self._logger.warning(
                    "Chat title generation failed: %s", type(e).__name__
                )
            return None
        except Exception as e:
            self._logger.warning("Chat title generation failed: %s", type(e).__name__)
            return None

        self._logger.info("Chat title generated.")
        return title

    async def _generate(self, user_message: str) -> str | None:
        messages = (
            MessagesBuilder()
            .system_message_append(CHAT_TITLE_SYSTEM_PROMPT)
            .user_message_append(
                CHAT_TITLE_USER_PROMPT_TEMPLATE.format(user_message=user_message)
            )
            .build()
        )
        response = await self._llm_service.complete_async(
            messages=messages,
            model_name=self._language_model.name,
            timeout=_COMPLETION_TIMEOUT_MS,
            other_options=without_reasoning_options(self._language_model),
        )
        if response.usage is not None:
            self._invocation_stats.append(
                LanguageModelInvocationStats.from_usage(
                    self._language_model.name,
                    response.usage,
                    source=INVOCATION_SOURCE,
                )
            )

        content = response.choices[0].message.content
        if not isinstance(content, str):
            return None
        return clean_title(content)
