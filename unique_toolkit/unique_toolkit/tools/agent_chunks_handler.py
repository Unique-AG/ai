from unique_toolkit.content.schemas import ContentChunk, ContentReference


class AgentChunksHandler:
    def __init__(self):
        self._tool_chunks = {}
        self._chunks: list[ContentChunk] = []
        self._references: list[list[ContentReference]] = []

    @property
    def chunks(self) -> list[ContentChunk]:
        return self._chunks

    @property
    def tool_chunks(self) -> dict:
        return self._tool_chunks

    def extend(self, chunks: list[ContentChunk]):
        self._chunks.extend(chunks)

    def replace(self, chunks: list[ContentChunk]):
        self._chunks = chunks

    def add_references(
        self,
        references: list[ContentReference],
    ):
        self._references.append(references)

    @property
    def all_references(
        self,
    ) -> list[list[ContentReference]]:
        return self._references

    @property
    def latest_references(
        self,
    ) -> list[ContentReference]:
        if not self._references:
            return []
        return self._references[-1]

    @property
    def latest_referenced_chunks(self) -> list[ContentChunk]:
        if not self._references:
            return []
        return self._get_referenced_chunks_from_references(
            self._references[-1]
        )

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
                if ref.source_id == str(chunk.id) + "_" + str(chunk.chunk_id):
                    referenced_chunks.append(chunk)
        return referenced_chunks
