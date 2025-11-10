import json
import re
from typing import Any, Iterable, Sequence
from uuid import uuid4


def _is_elementary_type(value: Any) -> bool:
    """Check if a value is an elementary type (str, int, float, bool, None)."""
    return isinstance(value, (str, int, float, bool, type(None)))


def _is_elementary_dict(data: dict[str, Any]) -> bool:
    """Check if all values in the dictionary are elementary types."""
    return all(_is_elementary_type(value) for value in data.values())


def dict_to_markdown_table(data: dict[str, Any]) -> str:
    """
    Convert a dictionary to a markdown table if all values are elementary types,
    otherwise return stringified JSON.

    Args:
        data: Dictionary to convert

    Returns:
        Markdown table string or JSON string
    """
    if not isinstance(data, dict):
        return json.dumps(data, indent=2)

    if not _is_elementary_dict(data):
        return json.dumps(data, indent=2)

    if not data:  # Empty dict
        return "| Key | Value |\n|-----|-------|\n| (empty) | (empty) |"

    # Create markdown table
    table_lines = ["| Key | Value |", "|-----|-------|"]

    for key, value in data.items():
        # Handle None values
        if value is None:
            value_str = "null"
        # Handle boolean values
        elif isinstance(value, bool):
            value_str = "true" if value else "false"
        # Handle other values
        else:
            value_str = str(value)

        # Escape pipe characters in the content
        key_escaped = str(key).replace("|", "\\|")
        value_escaped = value_str.replace("|", "\\|")

        table_lines.append(f"| {key_escaped} | {value_escaped} |")

    return "\n".join(table_lines) + "\n"


def extract_dicts_from_string(text: str) -> list[dict[str, Any]]:
    """
    Extract and parse a JSON dictionary from a string.

    The string should be wrapped in ```json tags. Example:

    ```json
    {"key": "value"}
    ```

    Args:
        text: String that may contain JSON

    Returns:
        Parsed dictionary or None if no valid JSON found
    """
    # Find JSON-like content between ```json and ``` tags
    pattern = r"```json\s*(\{.*?\})\s*```"
    matches = re.findall(pattern, text, re.DOTALL)

    dictionaries = []
    for match in matches:
        try:
            # Try to parse as JSON
            parsed = json.loads(match)
            if isinstance(parsed, dict):
                dictionaries.append(parsed)
        except json.JSONDecodeError:
            continue

    return dictionaries


def _replace_in_text_non_overlapping(
    text: str, repls: Iterable[tuple[str | re.Pattern[str], str]]
) -> str:
    for pattern, replacement in repls:
        text = re.sub(pattern, replacement, text)
    return text


def replace_in_text(
    text: str, repls: Sequence[tuple[str | re.Pattern[str], str]]
) -> str:
    """
    Replace multiple patterns in text without replacement interference.

    This function performs all replacements independently, preventing cases where
    a replacement value matches another pattern, which would cause unintended
    cascading replacements.

    Why this is needed:
    - Naive sequential replacements can interfere with each other
    - Example: replacing "foo" -> "bar" and "bar" -> "baz" would incorrectly
      turn "foo" into "baz" if done sequentially
    - This function uses a two-phase approach with UUID placeholders to ensure
      each pattern is replaced exactly once with its intended value

    Args:
        text: The input text to perform replacements on
        repls: Sequence of (pattern, replacement) tuples where pattern can be
               a string or compiled regex pattern

    Returns:
        Text with all patterns replaced by their corresponding replacements

    Example:
        >>> text = "foo and bar"
        >>> repls = [("foo", "bar"), ("bar", "baz")]
        >>> replace_in_text(text, repls)
        "bar and baz"  # Both replacements applied independently
    """
    if len(repls) == 0:
        return text

    placeholders = [uuid4().hex for _ in range(len(repls))]
    orig, repls = zip(*repls)

    # 2 phase replacement, since the map keys and values can overlap
    text = _replace_in_text_non_overlapping(text, zip(orig, placeholders))
    return _replace_in_text_non_overlapping(text, zip(placeholders, repls))


def remove_chat_prefix(text):
    pattern = r"Chat_\d{4}-\d{2}-\d{2}_\d{2}:\d{2}_"
    return re.sub(pattern, "", text)
