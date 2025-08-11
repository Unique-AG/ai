import re
from string import Template

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.unique_toolkit.tools.utils.source_handling.schema import SourceFormatConfig



def _format_page_range(chunk: ContentChunk) -> str:
    """Format page range string from chunk metadata."""
    if not (
        chunk.start_page
        and chunk.end_page
        and chunk.start_page > 0
        and chunk.end_page > 0
    ):
        return ""
    return (
        str(chunk.start_page)
        if chunk.start_page == chunk.end_page
        else f"{chunk.start_page} - {chunk.end_page}"
    )


def _parse_chunk(
    chunk: ContentChunk, section_templates: dict[str, str]
) -> dict[str, str]:
    """Extract sections from chunk text using regex patterns."""
    text = chunk.text
    result = dict()

    for section, template in section_templates.items():
        # Document and info are the only sections that are included in the text
        if section in [
            "document",
            "info",
        ]:  # Skip page as it's derived from metadata
            pattern = SourceFormatConfig.template_to_pattern(template)
            match = re.search(pattern, text, re.DOTALL)
            result[section] = match.group(1) if match else ""
            text = text.replace(match.group(0), "") if match else text

    result["text"] = text.strip()
    return result


def format_chunk(
    index: int, chunk: ContentChunk, config: SourceFormatConfig
) -> str:
    """
    This function formats a content chunk based on a given configuration template and its sections. Each chunk in the database includes a document section, an optional info section, and a text section, with the text section being the primary content. Typically, chunks are added to sources in search modules without any changes. However, certain scenarios necessitate extra formatting, such as incorporating page numbers or other metadata. This function enables the custom formatting of chunks when they are appended as sources.

    Args:
        index (int): The source index number to be used in the template.
        chunk (ContentChunk): A ContentChunk object containing:
            - text (str): The main content text
            - start_page (int, optional): Starting page number
            - end_page (int, optional): Ending page number
            - metadata (dict, optional): Additional metadata key-value pairs
        config (SourceFormatConfig): Configuration object containing:
            - source_template (str): The overall template for the output
            - sections (dict): Mapping of section names to their format templates

    Returns:
        str: Formatted string according to the template

    Examples:
        Using XML-style config without page numbers (default):
        >>> config = SourceFormatConfig(
        ...     source_template="<source${index}>${document}${info}${text}</source${index}>",
        ...     sections={
        ...         "document": "<|document|>{}<|/document|>\n",
        ...         "info": "<|info|>{}<|/info|>\n",
        ...     },
        ... )
        >>> chunk = ContentChunk(
        ...     text="<|document|>Sample Doc.pdf</|document|>\n<|info|>Important info</|info|>\nMain content"
        ... )
        >>> format_chunk(1, chunk, config)
        '<source1><|document|>Sample Doc.pdf</|document|>\n<|info|>Important info</|info|>\nMain content</source1>'

        Using XML-style config with page numbers:
        >>> config = SourceFormatConfig(
        ...     source_template="<source${index}>${document}${page}${info}${text}</source${index}>",
        ...     sections={
        ...         "document": "<|document|>{}<|/document|>\n",
        ...         "info": "<|info|>{}<|/info|>\n",
        ...         "page": "<|page|>{}<|/page|>\n",
        ...     },
        ... )
        >>> chunk = ContentChunk(
        ...     text="<|document|>Sample Doc.pdf</|document|>\n<|info|>Important info</|info|>\nMain content",
        ...     start_page=1,
        ...     end_page=3,
        ... )
        >>> format_chunk(1, chunk, config)
        '<source1><|document|>Sample Doc.pdf</|document|>\n<|page|>1 - 3</|page|>\n<|info|>Important info</|info|>\nMain content</source1>'

        Using XML-style config with metadata:
        >>> config = SourceFormatConfig(
        ...     source_template="<source${index}>${document}${date}${text}</source${index}>",
        ...     sections={
        ...         "document": "<|document|>{}<|/document|>\n",
        ...         "date": "<|DateFromMetaData|>{}<|/DateFromMetaData|>\n",
        ...     },
        ... )
        >>> chunk = ContentChunk(
        ...     text="<|document|>Sample Doc.pdf</|document|>\nMain content",
        ...     metadata={
        ...         "key": "metadata-key",
        ...         "mimeType": "text/plain",
        ...         "date": "12.03.2025",
        ...     },
        ... )
        >>> format_chunk(1, chunk, config)
        '<source1><|document|>Sample Doc.pdf</|document|>\n<|DateFromMetaData|>12.03.2025</|DateFromMetaData|>\nMain content</source1>'

        Using JSON-style config:
        >>> config = SourceFormatConfig(
        ...     source_template="{'source_number': ${index}, 'content': '${document}${page}${info}${text}'}",
        ...     sections={
        ...         "document": "<|document|>{}<|/document|>\n",
        ...         "info": "<|info|>{}<|/info|>\n",
        ...         "page": "<|page|>{}<|/page|>\n",
        ...     },
        ... )
        >>> chunk = ContentChunk(
        ...     text="<|document|>Sample Doc.pdf</|document|>\n<|info|>Important info</|info|>\nMain content",
        ...     start_page=5,
        ...     end_page=5,
        ... )
        >>> format_chunk(1, chunk, config)
        "{'source_number': 1, 'content': '<|document|>Sample Doc.pdf</|document|>\n<|page|>5</|page|>\n<|info|>Important info</|info|>\nMain content'}"

    Notes:
        - The function extracts document and info sections from the chunk text using regex patterns
        - Page numbers are formatted as single numbers when start_page equals end_page
        - Page numbers are formatted as ranges (e.g., "1 - 3") when start_page differs from end_page
        - If page numbers are not available (None or 0), the page section will be empty
        - Metadata keys that match section names (except 'document' and 'text') will be included in the output
        - Metadata is processed by the _process_metadata function to update the parsed dictionary
        - When using custom metadata tags like '<|DateFromMetaData|>', the key in chunk.metadata must match
          the key in the sections dictionary (e.g., 'date' in the example above), not the tag name
    """
    sections = config.sections
    source_template = config.source_template

    parsed = _parse_chunk(chunk, sections)
    parsed["page"] = _format_page_range(chunk)

    # Update parsed with metadata values
    parsed = _process_metadata(chunk, parsed, sections)

    # Create a new dictionary to hold the formatted sections
    formatted_sections = {}

    # Process each section
    for section, template in sections.items():
        if parsed.get(section):
            formatted_sections[section] = template.format(
                parsed.get(section, "")
            )
        else:
            formatted_sections[section] = ""

    # Add the text section
    formatted_sections["text"] = parsed["text"]

    return Template(source_template).substitute(
        index=index, **formatted_sections
    )


def _process_metadata(
    chunk: ContentChunk, parsed: dict[str, str], sections: dict[str, str]
) -> dict[str, str]:
    """
    Process metadata from chunk and update the parsed dictionary.

    This function extracts metadata from a ContentChunk object and updates the parsed
    dictionary with values whose keys match section names defined in SourceFormatConfig.

    Args:
        chunk (ContentChunk): The content chunk containing metadata
        parsed (dict): The dictionary of already parsed sections to update

    Returns:
        dict: The updated parsed dictionary with metadata values added

    Notes:
        - Keys 'document' and 'text' are explicitly excluded from metadata processing
        - Only metadata keys that match section names in SourceFormatConfig will be processed
        - If chunk.metadata is None or not iterable, the parsed dict is returned unchanged
        - Metadata values are added directly to the parsed dictionary using their original keys
    """
    # Return unchanged parsed dict if metadata is None
    if not hasattr(chunk, "metadata") or chunk.metadata is None:
        return parsed

    # Ensure metadata is a dictionary
    metadata_dict = (
        dict(chunk.metadata) if hasattr(chunk.metadata, "__iter__") else {}
    )

    # Define keys that should not be treated as metadata keys
    excluded_keys = {"document", "info"}

    # Get the keys from SourceFormatConfig.sections
    valid_section_keys = set(sections.keys()) - excluded_keys

    # Update parsed with valid metadata entries
    for key, value in metadata_dict.items():
        if key in valid_section_keys:
            parsed[key] = value

    return parsed
