import regex as re
from unique_toolkit.content.schemas import ContentChunk

from unique_internal_search.config import InternalSearchConfig


def modify_metadata_in_chunks(
    chunks: list[ContentChunk],
    config: InternalSearchConfig,
) -> list[ContentChunk]:
    for chunk in chunks:
        # Extract metadata from leading tags in the text
        extracted_metadata, remaining_text = _extract_leading_metadata_tags(chunk.text)

        # Merge extracted metadata with existing chunk metadata
        meta_dict = chunk.metadata.model_dump(exclude_none=True, by_alias=True)
        meta_dict.update(extracted_metadata)

        # Format metadata according to sections config and prepend to text
        formatted_text = _format_chunk_with_metadata(remaining_text, meta_dict, config)
        chunk.text = formatted_text

    return chunks


def _extract_leading_metadata_tags(text: str) -> tuple[dict[str, str], str]:
    """
    Extract metadata tags from the beginning of the text.
    Supports both <|key|>value<|/key|> and <key>value</key> formats.
    Stops when text no longer follows the tag structure.

    Returns:
        tuple of (extracted_metadata_dict, remaining_text)
    """
    metadata: dict[str, str] = {}
    remaining_text = text

    while True:
        match = _match_leading_tag(remaining_text)
        if not match:
            break

        key, value, matched_length = match
        metadata[key] = value
        remaining_text = remaining_text[matched_length:]

    return metadata, remaining_text.strip()


def _match_leading_tag(text: str) -> tuple[str, str, int] | None:
    """
    Try to match a metadata tag at the start of the text.
    Supports both <|key|>value<|/key|> and <key>value</key> formats.

    Returns:
        tuple of (key, value, matched_length) if found, None otherwise
    """
    # Try to match either format at the start of the text
    # Pattern 1: <|key|>value<|/key|>
    # Pattern 2: <key>value</key>
    match = re.match(
        r"^(?:<\|([^|]+)\|>(.*?)<\|/\1\|>|<([^>]+)>(.*?)</\3>)\s*", text, re.DOTALL
    )

    if not match:
        return None

    # Extract key and value (group 1,2 for <|key|> format, group 3,4 for <key> format)
    if match.group(1):  # <|key|> format matched
        key = match.group(1)
        value = match.group(2)
    else:  # <key> format matched
        key = match.group(3)
        value = match.group(4)

    return key, value, match.end()


def _format_chunk_with_metadata(
    text: str, meta_dict: dict[str, str], config: InternalSearchConfig
) -> str:
    """
    Format chunk text by prepending metadata according to sections config.

    Args:
        text: The main content text (without metadata tags)
        meta_dict: Dictionary of metadata key-value pairs

    Returns:
        Formatted text with metadata prepended
    """
    sections = config.source_format_config.sections

    parts: list[str] = []
    for key, template in sections.items():
        if key in meta_dict:
            parts.append(template.format(meta_dict[key]))

    # Combine metadata parts with the main text
    if parts:
        return "\n".join(parts) + "\n" + text
    return text
