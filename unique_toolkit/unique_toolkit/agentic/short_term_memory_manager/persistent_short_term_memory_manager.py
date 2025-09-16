import base64
import zlib
from logging import getLogger
from typing import Generic, Type, TypeVar

from pydantic import BaseModel

from unique_toolkit.agentic.tools.utils.execution.execution import SafeTaskExecutor
from unique_toolkit.short_term_memory.schemas import ShortTermMemory
from unique_toolkit.short_term_memory.service import ShortTermMemoryService

TSchema = TypeVar("TSchema", bound=BaseModel)


logger = getLogger(__name__)


def _default_short_term_memory_name(schema: type[BaseModel]) -> str:
    return f"{schema.__name__}Key"


def _compress_data_zlib_base64(data: str) -> str:
    """Compress data using ZLIB and encode as base64 string."""
    compressed = zlib.compress(data.encode("utf-8"))
    return base64.b64encode(compressed).decode("utf-8")


def _decompress_data_zlib_base64(compressed_data: str) -> str:
    """Decompress base64 encoded ZLIB data."""
    decoded = base64.b64decode(compressed_data.encode("utf-8"))
    return zlib.decompress(decoded).decode("utf-8")


class PersistentShortMemoryManager(Generic[TSchema]):
    """
    Manages the storage, retrieval, and processing of short-term memory in a persistent manner.

    This class is responsible for:
    - Saving and loading short-term memory data, both synchronously and asynchronously.
    - Compressing and decompressing memory data for efficient storage.
    - Validating and processing memory data using a predefined schema.
    - Logging the status of memory operations, such as whether memory was found or saved.

    Key Features:
    - Persistent Storage: Integrates with a short-term memory service to store and retrieve memory data.
    - Compression Support: Compresses memory data before saving and decompresses it upon retrieval.
    - Schema Validation: Ensures memory data adheres to a specified schema for consistency.
    - Synchronous and Asynchronous Operations: Supports both sync and async methods for flexibility.
    - Logging and Debugging: Provides detailed logs for memory operations, including success and failure cases.

    The PersistentShortMemoryManager is designed to handle short-term memory efficiently, ensuring data integrity and optimized storage.
    """

    def __init__(
        self,
        short_term_memory_service: ShortTermMemoryService,
        short_term_memory_schema: Type[TSchema],
        short_term_memory_name: str | None = None,
    ) -> None:
        self._short_term_memory_name = (
            short_term_memory_name
            if short_term_memory_name
            else _default_short_term_memory_name(short_term_memory_schema)
        )
        self._short_term_memory_schema = short_term_memory_schema
        self._short_term_memory_service = short_term_memory_service

        self._executor = SafeTaskExecutor(
            log_exceptions=False,
        )

    def _log_not_found(self) -> None:
        logger.warning(
            f"No short term memory found for chat {self._short_term_memory_service.chat_id} and key {self._short_term_memory_name}"
        )

    def _log_found(self) -> None:
        logger.debug(
            f"Short term memory found for chat {self._short_term_memory_service.chat_id} and key {self._short_term_memory_name}"
        )

    def _find_latest_memory_sync(self) -> ShortTermMemory | None:
        result = self._executor.execute(
            self._short_term_memory_service.find_latest_memory,
            self._short_term_memory_name,
        )

        self._log_not_found() if not result.success else self._log_found()

        return result.unpack(default=None)

    async def _find_latest_memory_async(self) -> ShortTermMemory | None:
        result = await self._executor.execute_async(
            self._short_term_memory_service.find_latest_memory_async,
            self._short_term_memory_name,
        )

        self._log_not_found() if not result.success else self._log_found()

        return result.unpack(default=None)

    def save_sync(self, short_term_memory: TSchema) -> None:
        json_data = short_term_memory.model_dump_json()
        compressed_data = _compress_data_zlib_base64(json_data)
        logger.info(
            f"Saving memory with {len(compressed_data)} characters compressed from {len(json_data)} characters for memory {self._short_term_memory_name}"
        )
        self._short_term_memory_service.create_memory(
            key=self._short_term_memory_name,
            value=compressed_data,
        )

    async def save_async(self, short_term_memory: TSchema) -> None:
        json_data = short_term_memory.model_dump_json()
        compressed_data = _compress_data_zlib_base64(json_data)
        logger.info(
            f"Saving memory with {len(compressed_data)} characters compressed from {len(json_data)} characters for memory {self._short_term_memory_name}"
        )
        await self._short_term_memory_service.create_memory_async(
            key=self._short_term_memory_name,
            value=compressed_data,
        )

    def _process_compressed_memory(
        self, memory: ShortTermMemory | None
    ) -> TSchema | None:
        if memory is not None and memory.data is not None:
            if isinstance(memory.data, str):
                data = _decompress_data_zlib_base64(memory.data)
                return self._short_term_memory_schema.model_validate_json(data)
            elif isinstance(memory.data, dict):
                return self._short_term_memory_schema.model_validate(memory.data)
        return None

    def load_sync(self) -> TSchema | None:
        memory: ShortTermMemory | None = self._find_latest_memory_sync()
        return self._process_compressed_memory(memory)

    async def load_async(self) -> TSchema | None:
        memory: ShortTermMemory | None = await self._find_latest_memory_async()
        return self._process_compressed_memory(memory)
