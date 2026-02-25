from logging import getLogger
from pathlib import Path

from unique_toolkit._common.token import count_tokens
from unique_toolkit.language_model.infos import LanguageModelInfo

from unique_web_search.schema import WebPageChunk

_LOGGER = getLogger(__name__)


def query_params_to_human_string(query: str, date_restrict: str | None) -> str:
    """
    Converts the WebSearchToolParameters and optional date_restrict to a human-understandable string.
    Maps date_restrict codes to human-readable periods.
    """
    query_str = f"{query}"
    if date_restrict:
        # Map date_restrict codes to human-readable strings
        mapping = {
            "d": "day",
            "w": "week",
            "m": "month",
            "y": "year",
        }
        import re

        match = re.fullmatch(r"([dwmy])(\d+)", date_restrict)
        if match:
            period, number = match.groups()
            period_str = mapping.get(period, period)
            # Pluralize if number > 1
            if number == "1":
                date_str = f"1 {period_str}"
            else:
                date_str = f"{number} {period_str}s"
        else:
            date_str = date_restrict
        query_str += f" (For the last {date_str})"
    return query_str


def _get_max_tokens(
    language_model_max_input_tokens: int | None,
    percentage_of_input_tokens_for_sources: float,
    language_model: LanguageModelInfo,
    limit_token_sources: int,
) -> int:
    if language_model_max_input_tokens is not None:
        max_tokens = int(
            language_model_max_input_tokens * percentage_of_input_tokens_for_sources
        )
        _LOGGER.debug(
            "Using %s of max tokens %s as token limit: %s",
            percentage_of_input_tokens_for_sources,
            language_model_max_input_tokens,
            max_tokens,
        )
        return max_tokens
    else:
        _LOGGER.debug(
            "language model input context size is not set, using default max tokens"
        )
        return (
            min(
                limit_token_sources,
                language_model.token_limits.token_limit_input - 1000,
            )
            if language_model.token_limits
            and language_model.token_limits.token_limit_input
            else limit_token_sources
        )


def load_template(parent_dir: Path, template_name: str) -> str:
    """Load a template from a text file."""
    with open(parent_dir / template_name, "r") as file:
        return file.read().strip()


def reduce_sources_to_token_limit(
    web_page_chunks: list[WebPageChunk],
    language_model_max_input_tokens: int | None,
    percentage_of_input_tokens_for_sources: float,
    limit_token_sources: int,
    language_model: LanguageModelInfo,
    chat_history_token_length: int,
) -> list[WebPageChunk]:
    total_tokens = 0
    selected_chunks = []

    max_token_sources = _get_max_tokens(
        language_model_max_input_tokens,
        percentage_of_input_tokens_for_sources,
        language_model,
        limit_token_sources,
    )

    for chunk in web_page_chunks:
        if total_tokens < max_token_sources - chat_history_token_length:
            total_tokens += count_tokens(text=chunk.content, model=language_model)
            selected_chunks.append(chunk)
        else:
            break

    return selected_chunks
