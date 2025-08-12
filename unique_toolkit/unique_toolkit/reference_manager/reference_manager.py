from unique_toolkit.content.schemas import ContentChunk, ContentReference
from unique_toolkit.tools.schemas import ToolCallResponse


class tool_chunks:
    def __init__(self, name: str, chunks: list) -> None:
        self.name = name
        self.chunks = chunks


class ReferenceManager:
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

    def get_tool_chunks(self) -> dict:
        return self._tool_chunks

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
