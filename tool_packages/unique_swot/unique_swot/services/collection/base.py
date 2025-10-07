from dataclasses import dataclass
from logging import getLogger

from pydantic import Field
from unique_toolkit import KnowledgeBaseService
from unique_toolkit.app.schemas import ChatEvent

from unique_swot.services.collection.earnings_call import collect_earnings_calls
from unique_swot.services.collection.knowledge_base import collect_knowledge_base
from unique_swot.services.collection.web import collect_web_sources
from unique_swot.services.schemas import Source

logger = getLogger(__name__)


@dataclass
class CollectionContext:
    use_earnings_calls: bool = Field(
        default=True,
        description="Whether to use earnings calls as a data source.",
    )
    use_web_sources: bool = Field(
        default=True,
        description="Whether to use web sources as a data source.",
    )

    @classmethod
    def from_event(cls, event: ChatEvent) -> "CollectionContext":
        logger.warning(
            "CollectionContext.from_event is not implemented yet. Defaulting to False for use_earnings_calls and use_web_sources."
        )
        return cls(
            use_earnings_calls=False,
            use_web_sources=False,
        )


class SourceCollectionManager:
    def __init__(
        self,
        *,
        context: CollectionContext,
        knowledge_base_service: KnowledgeBaseService,
        where_clause: dict,
    ):
        self.context = context
        self.knowledge_base_service = knowledge_base_service
        self.where_clause = where_clause

    def collect_sources(self) -> list[Source]:
        sources = self.collect_internal_documents()

        if self.context.use_earnings_calls:
            sources.extend(self.collect_earnings_calls())
        if self.context.use_web_sources:
            sources.extend(self.collect_web_sources())
        return sources

    def collect_earnings_calls(self) -> list[Source]:
        return collect_earnings_calls()

    def collect_web_sources(self) -> list[Source]:
        return collect_web_sources()

    def collect_internal_documents(self) -> list[Source]:
        return collect_knowledge_base(
            knowledge_base_service=self.knowledge_base_service,
            where_clause=self.where_clause,
        )
