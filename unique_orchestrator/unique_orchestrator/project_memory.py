"""Load the project memory for a project chat turn (UN-29145)."""

from __future__ import annotations

from logging import Logger

from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.experimental.resources.project_memory import ProjectMemories
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_user_memory.user_memory import count_tokens, enforce_token_cap

# The nightly job keeps a memory at about this size; reading never lets more
# through, nor more than a quarter of the model's input budget.
PROJECT_MEMORY_MAX_TOKENS = 4000
MODEL_INPUT_SHARE = 4


def project_memory_token_budget(language_model: LanguageModelInfo) -> int:
    """Tokens the project memory may take in this model's system prompt."""
    return min(
        PROJECT_MEMORY_MAX_TOKENS,
        language_model.token_limits.token_limit_input // MODEL_INPUT_SHARE,
    )


async def load_project_memory_text(
    *,
    event: ChatEvent,
    logger: Logger,
    language_model: LanguageModelInfo,
) -> str:
    """The project's memory document for the system prompt, or ``""``.

    Empty for chats outside a project and for projects without a memory yet.
    A failed read never fails the turn: it runs without project memory. A
    document over the model's budget is cut at a line, with a marker.
    """
    if not event.payload.project_id:
        return ""
    try:
        document = await ProjectMemories.from_event(event).get_document_async()
    except Exception as exc:
        logger.warning(
            "[project-memory] load failed - running without project memory: [%s]",
            type(exc).__name__,
        )
        return ""
    text = (document or "").strip()
    if not text:
        return ""
    budget = project_memory_token_budget(language_model)
    try:
        capped = enforce_token_cap(
            content=text, max_tokens=budget, language_model=language_model
        )
        if capped != text:
            logger.warning(
                "[project-memory] memory truncated to fit the model: %d -> %d tokens",
                count_tokens(content=text, language_model=language_model),
                budget,
            )
    except Exception as exc:
        # E.g. the tokenizer refuses a special-token literal in chat text.
        logger.warning(
            "[project-memory] could not fit memory - running without it: [%s]",
            type(exc).__name__,
        )
        return ""
    return capped
