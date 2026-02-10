from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Generator, TypeVar

if TYPE_CHECKING:
    from unique_toolkit.language_model.infos import LanguageModelInfo

T = TypeVar("T")


def batch_sequence_generator(
    *,
    language_model: LanguageModelInfo,
    source_batches: list[T],
    max_tokens_per_extraction_batch: int,
    serializer: Callable[[T], str],
) -> Generator[list[T], None, None]:
    encoder = language_model.get_encoder()
    current_batch = []
    current_tokens = 0
    for batch in source_batches:
        batch_tokens = encoder(serializer(batch))
        if current_tokens + len(batch_tokens) > max_tokens_per_extraction_batch:
            yield current_batch
            current_batch = []
            current_tokens = 0
        current_batch.append(batch)
        current_tokens += len(batch_tokens)
    yield current_batch


def create_batch_notification(
    *,
    component: str,
    batch_index: int | None = None,
    total_batches: int,
) -> str:
    """
    Create a description message for batch processing notifications.

    Args:
        component: The SWOT component being processed
        batch_index: Current batch number (1-indexed), None for initial notification
        total_batches: Total number of batches

    Returns:
        Formatted description string
    """
    if total_batches == 1:
        return f"Processing {component}..."

    if batch_index is None:
        return f"This document is too large to extract. It will be split into {total_batches} batches."

    return f"Processing {component} (Batch {batch_index} of {total_batches})..."
