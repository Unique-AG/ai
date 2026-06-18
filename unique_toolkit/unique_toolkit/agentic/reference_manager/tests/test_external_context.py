"""Tests for non-chunk groundedness context on the ReferenceManager.

External context texts (e.g. MCP tool output, UN-21951) ground the
hallucination check without being modelled as ContentChunks.
"""

from unique_toolkit.agentic.reference_manager.reference_manager import (
    ReferenceManager,
)


def test_external_context_starts_empty() -> None:
    manager = ReferenceManager()
    assert manager.get_external_context_texts() == []


def test_add_external_context_texts_accumulates() -> None:
    manager = ReferenceManager()
    manager.add_external_context_texts(["a", "b"])
    manager.add_external_context_texts(["c"])
    assert manager.get_external_context_texts() == ["a", "b", "c"]


def test_add_external_context_texts_drops_empty_strings() -> None:
    manager = ReferenceManager()
    manager.add_external_context_texts(["keep", "", "also"])
    assert manager.get_external_context_texts() == ["keep", "also"]


def test_external_context_is_independent_of_chunks() -> None:
    manager = ReferenceManager()
    manager.add_external_context_texts(["mcp output"])
    # External context must not leak into the chunk pipeline.
    assert manager.get_chunks() == []
    assert manager.get_external_context_texts() == ["mcp output"]
