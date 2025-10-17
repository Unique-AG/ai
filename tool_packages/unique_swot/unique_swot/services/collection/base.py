from logging import getLogger

from pydantic import BaseModel, ConfigDict
from unique_toolkit import KnowledgeBaseService
from unique_toolkit.app.schemas import ChatEvent

from unique_swot.services.collection.earnings_call import collect_earnings_calls
from unique_swot.services.collection.knowledge_base import collect_knowledge_base
from unique_swot.services.collection.web import collect_web_sources
from unique_swot.services.schemas import Source

_LOGGER = getLogger(__name__)


class CollectionContext(BaseModel):
    model_config = ConfigDict(frozen=True)
    use_earnings_calls: bool
    use_web_sources: bool

    @classmethod
    def from_event(cls, event: ChatEvent) -> "CollectionContext":
        _LOGGER.warning(
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
        self._context = context
        self._knowledge_base_service = knowledge_base_service
        self._where_clause = where_clause

    def collect_sources(self) -> list[Source]:
        sources = self.collect_internal_documents()

        if self._context.use_earnings_calls:
            sources.extend(self.collect_earnings_calls())
        if self._context.use_web_sources:
            sources.extend(self.collect_web_sources())
        return sources

    def collect_earnings_calls(self) -> list[Source]:
        return collect_earnings_calls()

    def collect_web_sources(self) -> list[Source]:
        return collect_web_sources()

    def collect_internal_documents(self) -> list[Source]:
        return collect_knowledge_base(
            knowledge_base_service=self._knowledge_base_service,
            where_clause=self._where_clause,
        )
