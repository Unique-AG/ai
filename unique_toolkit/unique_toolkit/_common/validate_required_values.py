from typing import Sequence, TypeVar

T = TypeVar("T")


def validate_required_values(values: Sequence[T | None]) -> Sequence[T]:
    """
    Validates that all values are not None and returns the sequence.

    Args:
        values: Sequence of possibly None values

    Returns:
        The same sequence, now guaranteed to have no None values

    Raises:
        ValueError: If any values are None
    """
    if any(v is None for v in values):
        raise ValueError("Required values cannot be None")
    return values  # type: ignore  # We know these aren't None after validation
