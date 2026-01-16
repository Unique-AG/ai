from typing import Callable, Generator, TypeVar

from tiktoken import get_encoding

T = TypeVar("T")


def batch_sequence_generator(
    *,
    encoder_name: str,
    source_batches: list[T],
    max_tokens_per_extraction_batch: int,
    serializer: Callable[[T], str],
) -> Generator[list[T], None, None]:
    encoder = get_encoding(encoder_name)
    current_batch = []
    current_tokens = 0
    for batch in source_batches:
        batch_tokens = encoder.encode(serializer(batch))
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
