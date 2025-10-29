from unique_toolkit.content.schemas import ContentChunk


def append_metadata_in_chunks(
    chunks: list[ContentChunk],
    metadata_chunk_sections: dict[str, str] | None = None,
) -> list[ContentChunk]:
    """
    Append metadata to chunks.
    Args:
        chunks: List of ContentChunk objects
        metadata_chunk_sections: Dictionary of metadata sections to add to the chunk text
    Returns:
        List of ContentChunk objects with metadata appended
    """
    if metadata_chunk_sections is None:
        return chunks
    for chunk in chunks:
        if chunk.metadata is None:
            continue
        chunk = _append_metadata_in_chunk(
            chunk=chunk, metadata_chunk_sections=metadata_chunk_sections
        )
    return chunks


def _append_metadata_in_chunk(
    chunk: ContentChunk, metadata_chunk_sections: dict[str, str]
) -> ContentChunk:
    """
    Format chunk text by prepending metadata according to sections config.
    Args:
        chunk: ContentChunk object
        metadata_chunk_sections: Dictionary of metadata sections to add to the chunk text
    Returns:
        Formatted text with metadata prepended
    """

    if chunk.metadata is None:
        return chunk

    meta_dict = chunk.metadata.model_dump(exclude_none=True, by_alias=True)

    parts: list[str] = []
    for key, template in metadata_chunk_sections.items():
        if key in meta_dict:
            formatted_section = template.format(meta_dict[key])
            parts.append(formatted_section)

    # Combine metadata parts with the main text
    if parts:
        chunk.text = "\n".join(parts) + "\n" + chunk.text

    return chunk
