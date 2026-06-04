from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel
from unique_search_proxy_core.projection import build_request_model

if TYPE_CHECKING:
    from unique_search_proxy_core.search_engines.base import SearchEngine


@dataclass(frozen=True)
class SearchEngineDescriptor:
    """Registration metadata for a search-engine provider."""

    config_model: type[BaseModel]
    service_cls: type[SearchEngine[Any]]

    @property
    def request_model(self) -> type[BaseModel]:
        """``POST /v1/search`` body derived from ``config_model``."""
        return build_request_model(self.config_model)
