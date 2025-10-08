"""
Citation management for deep research tool.

This module provides centralized citation registration and tracking across
parallel research agents, ensuring all citations are validated and preventing
LLM hallucination of sources.
"""

import asyncio
import logging
from typing import Dict, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CitationMetadata(BaseModel):
    """Metadata for a registered citation source."""

    number: int
    type: str
    name: str
    url: str
    source_id: str


class GlobalCitationManager:
    """
    Thread-safe citation manager shared across all research subgraphs.

    This manager:
    - Registers sources as they are fetched by tools
    - Assigns unique sequential citation numbers
    - Prevents duplicate registrations
    - Provides thread-safe access for parallel researchers
    - Enables validation of citations in final reports
    """

    def __init__(self):
        self._registry: Dict[str, CitationMetadata] = {}
        self._counter = 0
        self._lock = asyncio.Lock()

    async def register_source(
        self,
        source_id: str,
        source_type: str,
        name: str,
        url: str,
    ) -> CitationMetadata:
        """
        Register a source and return its citation metadata.

        If the source is already registered, returns the existing metadata.
        Otherwise, assigns a new sequential number and returns new metadata.

        Args:
            source_id: Unique identifier (URL or content_id)
            source_type: Either "web" or "internal"
            name: Human-readable name/title
            url: URL or content_id for the source

        Returns:
            CitationMetadata with citation number and source information
        """
        async with self._lock:
            if source_id in self._registry:
                return self._registry[source_id]

            self._counter += 1
            citation = CitationMetadata(
                number=self._counter,
                type=source_type,
                name=name,
                url=url,
                source_id=source_id,
            )
            self._registry[source_id] = citation

            return citation

    def get_all_citations(self) -> Dict[str, CitationMetadata]:
        """
        Get complete citation registry.

        Returns:
            Dictionary mapping source_id to CitationMetadata
        """
        return self._registry.copy()

    def get_citation_by_number(self, num: int) -> Optional[CitationMetadata]:
        """
        Lookup citation metadata by citation number.

        Args:
            num: Citation number to lookup

        Returns:
            CitationMetadata if found, None otherwise
        """
        for meta in self._registry.values():
            if meta.number == num:
                return meta
        return None

    def get_citation_count(self) -> int:
        """Get total number of registered citations."""
        return len(self._registry)

    def get_used_numbers(self) -> set[int]:
        """Get set of all citation numbers currently in use."""
        return {meta.number for meta in self._registry.values()}
