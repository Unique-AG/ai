from logging import getLogger

from unique_toolkit.short_term_memory.service import ShortTermMemoryService

from unique_swot.services.generation import SWOTAnalysisModels
from unique_swot.services.memory.exceptions import (
    MemoryEmptyException,
)

_LOGGER = getLogger(__name__)




class SwotMemoryService:
    def __init__(self, short_term_memory_service: ShortTermMemoryService):
        self.short_term_memory_service = short_term_memory_service

    def get(self, input: type[SWOTAnalysisModels]) -> SWOTAnalysisModels | None:
        key = input.__name__
        try:
            memory = self.short_term_memory_service.find_latest_memory(key)
            if not memory.data:
                raise MemoryEmptyException(f"Memory {key} is empty")

            return input.model_validate(memory.data)
        except Exception as e:
            _LOGGER.warning(f"Error getting memory {key}: {e}. Returning None.")
            return None

    def set(self, input: SWOTAnalysisModels) -> None:
        key = input.__class__.__name__
        self.short_term_memory_service.create_memory(key, input.model_dump())
