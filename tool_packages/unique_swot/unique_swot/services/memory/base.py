from logging import getLogger
from typing import Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel
from unique_toolkit.services.knowledge_base import KnowledgeBaseService
from unique_toolkit.short_term_memory.service import ShortTermMemoryService

_LOGGER = getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class Memory(BaseModel):
    id: str
    file_name: str


class SwotMemoryService(Generic[T]):
    def __init__(
        self,
        *,
        short_term_memory_service: ShortTermMemoryService,
        knowledge_base_service: KnowledgeBaseService,
        cache_scope_id: str,
    ):
        self._knowledge_base_service = knowledge_base_service
        self._short_term_memory_service = short_term_memory_service
        self._cache_scope_id = cache_scope_id

    def get(self, input: type[T]) -> T | None:
        key = input.__name__
        try:
            memory = self._find_latest_memory(key)
            if memory is None:
                return None

            # Download the content from the knowledge base
            _LOGGER.info(
                f"Downloading cached content from the knowledge base for key '{key}'."
            )
            content_bytes = self._knowledge_base_service.download_content_to_bytes(
                content_id=memory.id
            )

            # Parse the content into the input model
            _LOGGER.info(
                f"Parsing cached content into the input model for key '{key}'."
            )
            content_json = content_bytes.decode("utf-8")
            return input.model_validate_json(content_json)

        except Exception as e:
            self._log_memory_error(key, e, "Failed to retrieve cached SWOT analysis")
            return None

    def set(self, input: T) -> None:
        key = input.__class__.__name__

        memory = self._find_latest_memory(key)

        # First, we check if the file already saved
        if memory is not None:
            _LOGGER.info(
                f"Memory found for key '{key}'. Using existing file name '{memory.file_name}'."
            )
            file_name = memory.file_name
        # If not we create a new one
        else:
            _LOGGER.info(f"No memory found for key '{key}'. Creating a new file name.")
            file_name = f"{key}_{uuid4().hex}.json"

        # Store in knowledge base
        try:
            if not self._cache_scope_id:
                raise ValueError("Cache scope id is required. Please set it in the configuration.")
            
            content = self._knowledge_base_service.upload_content_from_bytes(
                content=input.model_dump_json(indent=1).encode("utf-8"),
                content_name=file_name,
                mime_type="text/plain",
                scope_id=self._cache_scope_id,
                skip_ingestion=True,
            )

            memory = Memory(id=content.id, file_name=file_name)
            self._short_term_memory_service.create_memory(key, memory.model_dump())
        except Exception as e:
            self._log_memory_error(key, e, "Failed to upload content to knowledge base")

    def _find_latest_memory(self, key):
        try:
            # Get the latest memory for the given key
            short_term_memory_response = (
                self._short_term_memory_service.find_latest_memory(key)
            )

            # Parse Memory
            memory = Memory.model_validate(short_term_memory_response.data)

            return memory
        except Exception as e:
            self._log_memory_error(key, e, "Failed to find latest memory")
            return None

    def _log_memory_error(self, key: str, error: Exception, message: str) -> None:
        """Log memory operation errors with consistent formatting."""
        _LOGGER.warning(f"{message} for key '{key}'. Returning None.")
        _LOGGER.debug(f"Error: {error}", exc_info=True)
