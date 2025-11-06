import warnings
from collections.abc import Mapping
from typing import List, Optional


def get_fields(cls: type) -> set[str]:
    """Get all field names from the given class (excluding private/internal fields)."""
    return {
        field_name
        for field_name in cls.__annotations__.keys()
        if not field_name.startswith("_")
    }


def has_all_fields(
    data: Mapping[str, object], cls: type, skip_fields: Optional[List[str]] = None
) -> bool:
    """Check if a dictionary contains all fields required by the given class."""

    required_fields = get_fields(cls)

    if skip_fields:
        missing_fields = get_missing_fields(data, cls) - set(skip_fields)
        warnings.warn(
            f"Missing fields: {missing_fields} detected for {cls.__name__} but skipped."
        )
        required_fields = get_fields(cls) - set(skip_fields)

    return required_fields.issubset(data.keys())


def get_missing_fields(data: Mapping[str, object], cls: type) -> set[str]:
    """Get the set of fields that are missing from the dictionary for the given class."""
    required_fields = get_fields(cls)
    return required_fields - set(data.keys())
