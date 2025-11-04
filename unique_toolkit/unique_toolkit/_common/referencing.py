"""
Utilities for handling references in the "postprocessed" format, i.e <sup>X</sup>
"""

import functools
import re
from typing import Generator

_REF_DETECTION_PATTERN = re.compile(r"<sup>\s*(?P<reference_number>\d+)\s*</sup>")


def _iter_ref_numbers(text: str) -> Generator[int, None, None]:
    for match in _REF_DETECTION_PATTERN.finditer(text):
        yield int(match.group("reference_number"))


@functools.cache
def _get_detection_pattern_for_ref(ref_number: int) -> re.Pattern[str]:
    return re.compile(rf"<sup>\s*{ref_number}\s*</sup>")


def get_reference_pattern(ref_number: int) -> str:
    return f"<sup>{ref_number}</sup>"


def get_all_ref_numbers(text: str) -> list[int]:
    return sorted(set(_iter_ref_numbers(text)))


def get_max_ref_number(text: str) -> int | None:
    return max(_iter_ref_numbers(text), default=None)


def replace_ref_number(text: str, ref_number: int, replacement: int | str) -> str:
    if isinstance(replacement, int):
        replacement = get_reference_pattern(replacement)

    return _get_detection_pattern_for_ref(ref_number).sub(replacement, text)


def remove_ref_number(text: str, ref_number: int) -> str:
    return _get_detection_pattern_for_ref(ref_number).sub("", text)


def remove_all_refs(text: str) -> str:
    return _REF_DETECTION_PATTERN.sub("", text)


def remove_consecutive_ref_space(text: str) -> str:
    """
    Remove spaces between consecutive references.
    """
    return re.sub(r"</sup>\s*<sup>", "</sup><sup>", text)
