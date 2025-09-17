from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.content.schemas import ContentChunk, ContentReference


class tool_chunks:
    def __init__(self, name: str, chunks: list[ContentChunk]) -> None:
        self.name = name
        self.chunks = chunks


class ReferenceManager:
    """
    Manages content chunks and references extracted from tool responses.

    This class is responsible for:
    - Extracting and storing referenceable content chunks from tool responses.
    - Managing a collection of content chunks and their associated references.
    - Providing methods to retrieve, replace, and manipulate chunks and references.
    - Supporting the retrieval of the latest references and their corresponding chunks.

    Key Features:
    - Chunk Extraction: Extracts content chunks from tool responses and organizes them for reference.
    - Reference Management: Tracks references to content chunks and allows for easy retrieval.
    - Latest Reference Access: Provides methods to fetch the most recent references and their associated chunks.
    - Flexible Chunk Replacement: Allows for replacing the current set of chunks with a new list.
    - Reference-to-Chunk Mapping: Matches references to their corresponding chunks based on source IDs.

    The ReferenceManager serves as a utility for managing and linking content chunks with references, enabling efficient content tracking and retrieval.
    """

    def __init__(self):
        self._tool_chunks: dict[str, tool_chunks] = {}
        self._chunks: list[ContentChunk] = []
        self._references: list[list[ContentReference]] = []

    def extract_referenceable_chunks(
        self, tool_responses: list[ToolCallResponse]
    ) -> None:
        for tool_response in tool_responses:
            if not tool_response.content_chunks:
                continue
            self._chunks.extend(tool_response.content_chunks or [])
            self._tool_chunks[tool_response.id] = tool_chunks(
                tool_response.name, tool_response.content_chunks
            )

    def get_chunks(self) -> list[ContentChunk]:
        return self._chunks

    def get_tool_chunks(self) -> dict[str, tool_chunks]:
        return self._tool_chunks

    def get_chunks_of_all_tools(self) -> list[list[ContentChunk]]:
        return [tool_chunks.chunks for tool_chunks in self._tool_chunks.values()]

    def get_chunks_of_tool(self, tool_call_id: str) -> list[ContentChunk]:
        return self._tool_chunks.get(tool_call_id, tool_chunks("", [])).chunks

    def replace_chunks_of_tool(
        self, tool_call_id: str, chunks: list[ContentChunk]
    ) -> None:
        if tool_call_id in self._tool_chunks:
            self._tool_chunks[tool_call_id].chunks = chunks

    def replace(self, chunks: list[ContentChunk]):
        self._chunks = chunks

    def add_references(
        self,
        references: list[ContentReference],
    ):
        self._references.append(references)

    def get_references(
        self,
    ) -> list[list[ContentReference]]:
        return self._references

    def get_latest_references(
        self,
    ) -> list[ContentReference]:
        if not self._references:
            return []
        return self._references[-1]

    def get_latest_referenced_chunks(self) -> list[ContentChunk]:
        if not self._references:
            return []
        return self._get_referenced_chunks_from_references(self._references[-1])

    def _get_referenced_chunks_from_references(
        self,
        references: list[ContentReference],
    ) -> list[ContentChunk]:
        """
        Get _referenced_chunks by matching sourceId from _references with merged id and chunk_id from _chunks.
        """
        referenced_chunks: list[ContentChunk] = []
        for ref in references:
            for chunk in self._chunks:
                if ref.source_id == f"{chunk.id}-{chunk.chunk_id}":
                    referenced_chunks.append(chunk)
        return referenced_chunks
