from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI

from unique_swot.services.orchestrator.schema import SourceSelectionResult
from unique_swot.services.source_management.schema import Source


class SourceSelectionAgent:
    def __init__(
        self,
        *,
        llm_service: LanguageModelService,
        llm: LMI,
    ):
        self._llm_service = llm_service

    async def select(self, *, source: Source) -> SourceSelectionResult:
        return SourceSelectionResult(should_select=True, reason="")
