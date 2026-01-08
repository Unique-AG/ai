from collections import defaultdict
from logging import getLogger
from typing import Callable, TypeVar

from unique_toolkit.chat import ChatMessageRole
from unique_toolkit.content import ContentChunk
from unique_toolkit.content.schemas import Content, ContentReference

logger = getLogger(__name__)


def get_file_content_getter_fn(
    user_id: str, company_id: str, chat_id: str
) -> Callable[[str], Content | None]:
    """
    Factory function to create a content retriever with authentication context.
    
    The returned function allows you to:
    - Retrieve full Content objects by file ID
    - Access file metadata (custom key-value pairs attached during upload)
    - Access file chunks (for chunked documents)
    - Access file text and other properties
    
    Returns:
        A function that retrieves Content by file_id, or None if not found
    """
    from unique_toolkit.content.functions import search_contents

    def get_content_fn(file_id: str) -> Content | None:
        # Search for content by exact ID match
        where = {"id": {"equals": file_id}}
        contents = search_contents(
            user_id=user_id, company_id=company_id, chat_id=chat_id, where=where
        )
        assert len(contents) <= 1

        if len(contents) == 0:
            logger.warning(f"No content info found for file: {file_id}")
            return None

        if contents[0].metadata is None:
            logger.warning(f"No metadata found for file: {file_id}")

        logger.info(f"Metadata for file {file_id}: {contents[0].metadata}")
        return contents[0]

    return get_content_fn


def get_downloader_fn(
    user_id: str, company_id: str, chat_id: str
) -> Callable[[str], bytes]:
    """
    Factory function to create a file downloader with authentication context.

    Returns a function that downloads files by content_id.
    """
    from unique_toolkit.content.functions import download_content_to_bytes

    return lambda file_id: download_content_to_bytes(
        user_id=user_id, company_id=company_id, chat_id=chat_id, content_id=file_id
    )


def get_uploader_fn(
    user_id: str, company_id: str, chat_id: str
) -> Callable[[bytes, str, str], Content]:
    """
    Factory function to create a file uploader with authentication context.

    Returns a function that uploads files to the chat.
    """
    from unique_toolkit.content.functions import upload_content_from_bytes

    def uploader(content: bytes, mime_type: str, content_name: str) -> Content:
        return upload_content_from_bytes(
            user_id=user_id,
            company_id=company_id,
            content=content,
            mime_type=mime_type,
            content_name=content_name,
            chat_id=chat_id,
            skip_ingestion=True,
        )

    return uploader


def convert_content_chunk_to_reference(
    *,
    message_id: str,
    content_or_chunk: Content | ContentChunk,
    sequence_number: int | None = None,
    start_page: int | None = None,
    end_page: int | None = None,
) -> ContentReference:
    title = content_or_chunk.title or content_or_chunk.key or content_or_chunk.id

    page_suffix = None
    if start_page:
        if end_page:
            page_suffix = f": {start_page} - {end_page}"
        else:
            page_suffix = f": {start_page}"

    title = f"{title}{page_suffix}" if page_suffix else title

    return ContentReference(
        message_id=message_id,
        url=f"unique://content/{content_or_chunk.id}",
        source_id=content_or_chunk.id,
        name=title,
        sequence_number=sequence_number or 0,
        source="agentic-table",
    )


def get_augmented_text_with_references_fn(
    user_id: str, company_id: str, chat_id: str, assistant_id: str
) -> Callable[[str, dict[str, Content | ContentChunk], str, str], str]:
    """
    Factory function to create a reference builder with authentication context.
    
    The returned function converts inline citations in text (e.g., [chunk_abc123]) into 
    clickable references in the Unique UI. These references:
    - Appear as numbered citations (e.g., [1], [2]) in the frontend
    - Are clickable and navigate to the source content
    - Include metadata like title, page numbers, and source ID
    
    This is useful when:
    - AI agents generate text with citations to source documents
    - You want to create audit trails linking table cells to source files
    - You need to show provenance of data in the table
    
    Returns:
        A function that converts inline citations to numbered references
    """

    import re

    from unique_toolkit.chat.functions import create_message, modify_message

    # Default pattern matches citations like [chunk_abc123] or [chunk_xyz-456]
    _DEFAULT_CITATION_PATTERN = r"\[chunk_([a-zA-Z0-9\-]+)\]"

    def reference_builder(
        text: str,
        reference_registry: dict[str, Content | ContentChunk],
        prefix: str = "chunk",
        citation_pattern: str = _DEFAULT_CITATION_PATTERN,
    ) -> str:
        """
        Converts inline citations in text to numbered references with full content metadata.

        This function:
        1. Extracts all citation IDs from the text (e.g., [chunk_abc123])
        2. Looks up each citation in the reference registry
        3. Converts them to numbered references (e.g., [1&message_id])
        4. Creates a message with the processed text and reference metadata

        Args:
            text: The text containing inline citations in format [chunk_xxx].
            reference_registry: Dictionary mapping citation IDs to their full Content or ContentChunk objects.
            citation_pattern: Regex pattern to extract citation IDs from text (default matches [chunk_xxx]).

        Returns:
            The processed text with inline citations converted to numbered references.
        """

        # Create a new assistant message to hold the references
        message = create_message(
            user_id=user_id,
            company_id=company_id,
            chat_id=chat_id,
            assistant_id=assistant_id,
            role=ChatMessageRole.ASSISTANT,
        )
        assert message.id is not None

        # Extract all citation IDs from the text (e.g., "abc123" from "[chunk_abc123]")
        chunk_ids = re.findall(citation_pattern, text)
        
        logger.info(f"Found {len(chunk_ids)} chunk IDs in text")
        logger.info(f"Chunk IDs: {chunk_ids}")

        # Track which citations we've already processed to avoid duplicates
        processed_citations = {}

        # Collect all reference metadata to attach to the message
        message_references = []

        # Process each citation found in the text
        for chunk_id in chunk_ids:
            # Check if we've already processed this citation
            if chunk_id in processed_citations:
                # Reuse the same reference notation for duplicate citations
                reference_notation = processed_citations[chunk_id]
            else:
                # Look up the full content/chunk object for this citation
                referenced_content = reference_registry.get(f"{prefix}_{chunk_id}")

                if referenced_content:
                    # This is a valid citation - create a numbered reference
                    sequence_number = len(processed_citations) + 1

                    # Add the reference metadata to the message
                    message_references.append(
                        convert_content_chunk_to_reference(
                            message_id=message.id,
                            content_or_chunk=referenced_content,
                            sequence_number=sequence_number,
                        )
                    )

                    # Format: [sequence_number&message_id] (e.g., [1&msg_123])
                    reference_notation = f"[{sequence_number}&{message.id}]"
                    processed_citations[chunk_id] = reference_notation
                else:
                    # Citation ID not found in registry - mark as invalid
                    reference_notation = "[???]"

            # Replace the inline citation with the reference notation
            text = text.replace(f"[chunk_{chunk_id}]", reference_notation)

        # Update the message with the processed text and all references
        modify_message(
            assistant_message_id=message.id,
            user_message_id=message.id,
            user_message_text=text,
            assistant=True,
            user_id=user_id,
            company_id=company_id,
            chat_id=chat_id,
            references=message_references,
            content=text,
        )

        return text

    return reference_builder


class ContentRegistry:
    """
    An EXAMPLE utility class for organizing Content objects by metadata keys.
    
    This demonstrates ONE WAY to manage content with metadata. You should implement
    your own filtering logic based on your specific requirements.
    
    Example use case:
        If your source files have metadata like {"section": "Finance"} or {"section": "Legal"},
        this class groups them by those keys so you can retrieve all Finance-related files
        when processing a Finance row in your table.
    
    This is intentionally simple to show the pattern. For production use, consider:
    - Filtering by metadata VALUES, not just keys (e.g., {"status": "approved"})
    - Complex queries (AND/OR conditions, ranges, regex patterns)
    - Multiple metadata attributes (e.g., section AND department)
    - Caching strategies for large content sets
    - Custom scoring/ranking logic for content relevance
    
    Build your own registry class that fits your business logic!
    """

    def __init__(self, keys: list[str], contents: list[Content]):
        """
        Initialize with metadata keys and a list of Content objects.
        
        This example implementation groups content by checking if metadata keys exist.
        Your implementation might filter by metadata values, use complex queries,
        or implement completely different logic.
        
        Args:
            keys: List of metadata keys to group by (e.g., ["Finance", "Legal"])
            contents: List of Content objects to organize
        """
        self.keys = keys
        self.contents = contents

        grouped: dict[str, list[Content]] = defaultdict(list)

        # Group content by metadata keys
        for content in self.contents:
            if content.metadata is None:
                logger.warning(f"No metadata found for content: {content.id}")
                continue

            # Check if any of our target keys exist in this content's metadata
            for key in keys:
                if key in content.metadata:
                    logger.info(f"Found metadata key: {key} for content: {content.id}")
                    grouped[key].append(content)

        self.contents_by_key = dict(grouped)

    def get_contents_by_metadata_key(self, key: str) -> list[Content]:
        """
        Retrieve all content items that have the specified metadata key.
        
        Args:
            key: The metadata key to filter by
            
        Returns:
            List of Content objects with that metadata key, or empty list if none found
        """
        return self.contents_by_key.get(key, [])


T = TypeVar("T")


def create_id_map(items: list[T], prefix: str) -> dict[str, T]:
    """
    Create a mapping of generated IDs to items for use in reference systems.
    
    This helper generates unique IDs for a list of items (Content or ContentChunk objects)
    so they can be cited in text and later resolved back to their full objects.
    
    Args:
        items: List of items to create IDs for (typically Content or ContentChunk objects)
        prefix: Prefix for generated IDs (e.g., "chunk" creates IDs like "chunk_a1b2c3d4")
        
    Returns:
        Dictionary mapping generated IDs to items
        
    Example:
        >>> contents = [content1, content2, content3]
        >>> id_map = create_id_map(contents, "chunk")
        >>> # Returns: {"chunk_a1b2c3d4": content1, "chunk_x9y8z7w6": content2, ...}
    """
    from uuid import uuid4

    return {f"{prefix}_{uuid4().hex[:8]}": item for item in items}
