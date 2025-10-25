from unique_toolkit.content.schemas import ContentChunk

from unique_internal_search.config import InternalSearchConfig
from unique_internal_search.schema import ChunkMetadataSection


def append_metadata_in_chunks(
    chunks: list[ContentChunk],
    config: InternalSearchConfig,
) -> list[ContentChunk]:
    for chunk in chunks:
        meta_dict = chunk.metadata.model_dump(exclude_none=True, by_alias=True)

        # Format metadata according to sections config and prepend to text
        formatted_text = _append_metadata_in_chunk(chunk.text, meta_dict, config)
        chunk.text = formatted_text

    return chunks


def _append_metadata_in_chunk(
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
    metadata_sections: list[ChunkMetadataSection] = config.metadata_sections

    parts: list[str] = []
    for section in metadata_sections:
        if section.key in meta_dict:
            section_pattern = ChunkMetadataSection.pattern_from_template(section.template)
            parts.append(section_pattern.format(meta_dict[section.key]))

    # Combine metadata parts with the main text
    if parts:
        return "\n".join(parts) + "\n" + text
    return text
