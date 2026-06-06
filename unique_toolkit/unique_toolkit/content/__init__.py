from typing import TYPE_CHECKING, Any

from .constants import DOMAIN_NAME as DOMAIN_NAME
from .schemas import (
    Content as Content,
)
from .schemas import (
    ContentChunk as ContentChunk,
)
from .schemas import (
    ContentMetadata as ContentMetadata,
)
from .schemas import (
    ContentReference as ContentReference,
)
from .schemas import (
    ContentRerankerConfig as ContentRerankerConfig,
)
from .schemas import (
    ContentSearchResult as ContentSearchResult,
)
from .schemas import (
    ContentSearchType as ContentSearchType,
)
from .schemas import (
    ContentUploadInput as ContentUploadInput,
)
from .utils import (
    count_tokens as count_tokens,
)
from .utils import (
    merge_content_chunks as merge_content_chunks,
)
from .utils import (
    pick_content_chunks_for_token_window as pick_content_chunks_for_token_window,
)
from .utils import (
    sort_content_chunks as sort_content_chunks,
)

if TYPE_CHECKING:
    from .service import ContentService as ContentService

__all__ = [
    "Content",
    "ContentChunk",
    "ContentMetadata",
    "ContentReference",
    "ContentRerankerConfig",
    "ContentSearchResult",
    "ContentSearchType",
    "ContentService",
    "ContentUploadInput",
    "DOMAIN_NAME",
    "count_tokens",
    "merge_content_chunks",
    "pick_content_chunks_for_token_window",
    "sort_content_chunks",
]


def __getattr__(name: str) -> Any:
    if name == "ContentService":
        from .service import ContentService

        return ContentService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
