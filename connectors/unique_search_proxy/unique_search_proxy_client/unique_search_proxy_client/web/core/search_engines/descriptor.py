from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from unique_search_proxy_core.search_engines.base import SearchEngine


@dataclass(frozen=True)
class SearchEngineDescriptor:
    """Registration metadata for a search-engine provider."""

    config_model: type[BaseModel]
    service_cls: type[SearchEngine[Any]]
