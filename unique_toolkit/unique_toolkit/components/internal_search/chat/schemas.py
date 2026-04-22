from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unique_toolkit._common.chunk_relevancy_sorter.service import (
        ChunkRelevancySorter,
    )
    from unique_toolkit.services.chat_service import ChatService


@dataclass
class ChatInternalSearchDeps:
    chunk_relevancy_sorter: ChunkRelevancySorter
    chat_service: ChatService


__all__ = ["ChatInternalSearchDeps"]
