from typing import Callable

from pydantic import BaseModel, Field
from unique_toolkit.tools.config import get_configuration_dict

from unique_web_search.services.preprocessing.cleaning.patterns import (
    PATTERNS,
    get_cleaner,
)


class CleaningStrategyConfig(BaseModel):
    model_config = get_configuration_dict()

    markdown_cleaning_timeout: float = Field(
        default=5.0,
        description="Timeout for markdown cleaning.",
    )
    remove_nested_images_and_links: bool = Field(
        default=False,
        description="Whether to clean nested images and links in the content.",
    )
    remove_simple_images_and_links: bool = Field(
        default=False,
        description="Whether to clean simple images and links in the content.",
    )
    remove_multiple_linebreaks: bool = Field(
        default=False,
        description="Whether to clean multiple linebreaks in the content.",
    )
    remove_repeating_patterns: bool = Field(
        default=False,
        description="Whether to clean repeating patterns in the content.",
    )


def _encoding_cleanup(text: str) -> str:
    """Fast encoding cleanup - most expensive operations."""
    text = text.encode("utf-8", "ignore").decode()
    return text


def get_cleaning_strategy(
    config: CleaningStrategyConfig,
) -> Callable[[str], str]:
    timeout = config.markdown_cleaning_timeout
    fun_stack = []
    if config.remove_nested_images_and_links:
        fun_stack.append(get_cleaner(PATTERNS.NESTED_IMAGES_AND_LINKS, timeout))
    if config.remove_simple_images_and_links:
        fun_stack.append(get_cleaner(PATTERNS.IMAGES_AND_LINKS, timeout))
    if config.remove_multiple_linebreaks:
        fun_stack.append(get_cleaner(PATTERNS.MULTIPLE_LINEBREAKS, timeout))
    if config.remove_repeating_patterns:
        fun_stack.append(get_cleaner(PATTERNS.REPEATING_PATTERNS, timeout))

    fun_stack.append(_encoding_cleanup)

    def cleaning_function(text: str) -> str:
        for fn in fun_stack:
            text = fn(text)
        return text

    return cleaning_function
