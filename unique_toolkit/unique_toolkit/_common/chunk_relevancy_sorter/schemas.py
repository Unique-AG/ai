from typing import Optional

from pydantic import BaseModel

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.evals.schemas import EvaluationMetricResult


class ChunkRelevancy(BaseModel):
    chunk: ContentChunk
    relevancy: EvaluationMetricResult | None = None

    def get_document_name(self):
        title = self.chunk.key or self.chunk.title or "Unkown"
        return title.split(":")[0]

    def get_page_number(self):
        start_page = self.chunk.start_page
        end_page = self.chunk.end_page

        if start_page is None or end_page is None:
            return start_page or end_page or "Unknown Page"
        elif start_page == end_page:
            return str(start_page)
        else:
            return f"{start_page}-{end_page}"

    def get_facts(self):
        if self.relevancy is None:
            return []
        return self.relevancy.fact_list


class ChunkRelevancySorterResult(BaseModel):
    relevancies: list[ChunkRelevancy]
    user_message: Optional[str] = None

    @staticmethod
    def from_chunks(chunks: list[ContentChunk]):
        return ChunkRelevancySorterResult(
            relevancies=[ChunkRelevancy(chunk=chunk) for chunk in chunks],
        )

    @property
    def content_chunks(self):
        return [chunk.chunk for chunk in self.relevancies]
