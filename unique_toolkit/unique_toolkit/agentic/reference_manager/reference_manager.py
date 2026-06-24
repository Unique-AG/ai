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
        self._external_context_texts: list[str] = []

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

    def add_external_context_texts(self, texts: list[str]) -> None:
        """Register groundedness context that is not backed by ContentChunks.

        Some retrieval sources (e.g. MCP tool output) provide text the answer
        is built on but are deliberately *not* modelled as ContentChunks — they
        are a different entity from ingested document chunks and must not flow
        through the chunk/reference pipeline. They still need to ground the
        hallucination check, so they are stored here and appended to the
        evaluation context alongside the chunk-derived texts.
        """
        self._external_context_texts.extend(text for text in texts if text)

    def get_external_context_texts(self) -> list[str]:
        return self._external_context_texts

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
                if ref.source_id == f"{chunk.id}_{chunk.chunk_id}":
                    referenced_chunks.append(chunk)
        return referenced_chunks
