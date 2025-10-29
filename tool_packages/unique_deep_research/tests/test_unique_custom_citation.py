"""
Unit tests for unique_custom/citation.py module.
"""

import pytest

from unique_deep_research.unique_custom.citation import (
    CitationMetadata,
    GlobalCitationManager,
)


@pytest.mark.ai
def test_citation_metadata__creates_valid_instance__with_required_fields() -> None:
    """
    Purpose: Verify CitationMetadata creates valid instance with required fields.
    Why this matters: CitationMetadata is core data structure for citation management.
    Setup summary: Create CitationMetadata instance and verify field values.
    """
    # Arrange & Act
    metadata = CitationMetadata(
        number=1,
        type="web",
        name="Test Source",
        url="https://example.com",
        source_id="example-com",
    )

    # Assert
    assert metadata.number == 1
    assert metadata.type == "web"
    assert metadata.name == "Test Source"
    assert metadata.url == "https://example.com"
    assert metadata.source_id == "example-com"


@pytest.mark.ai
def test_citation_metadata__validates_number__is_positive() -> None:
    """
    Purpose: Verify CitationMetadata validates number is positive.
    Why this matters: Citation numbers must be positive for proper ordering.
    Setup summary: Attempt to create metadata with invalid number and verify validation.
    """
    # Arrange & Act & Assert
    with pytest.raises(ValueError):
        CitationMetadata(
            number=0,  # Invalid: must be > 0
            type="web",
            name="Test Source",
            url="https://example.com",
            source_id="example-com",
        )


@pytest.mark.ai
def test_citation_metadata__validates_name__is_not_empty() -> None:
    """
    Purpose: Verify CitationMetadata validates name is not empty.
    Why this matters: Citation names must be meaningful for display.
    Setup summary: Attempt to create metadata with empty name and verify validation.
    """
    # Arrange & Act & Assert
    with pytest.raises(ValueError):
        CitationMetadata(
            number=1,
            type="web",
            name="",  # Invalid: min_length=1
            url="https://example.com",
            source_id="example-com",
        )


@pytest.mark.ai
def test_citation_metadata__validates_url__is_not_empty() -> None:
    """
    Purpose: Verify CitationMetadata validates url is not empty.
    Why this matters: Citation URLs must be valid for source access.
    Setup summary: Attempt to create metadata with empty url and verify validation.
    """
    # Arrange & Act & Assert
    with pytest.raises(ValueError):
        CitationMetadata(
            number=1,
            type="web",
            name="Test Source",
            url="",  # Invalid: min_length=1
            source_id="example-com",
        )


@pytest.mark.ai
def test_citation_metadata__validates_source_id__is_not_empty() -> None:
    """
    Purpose: Verify CitationMetadata validates source_id is not empty.
    Why this matters: Source IDs must be unique identifiers for citations.
    Setup summary: Attempt to create metadata with empty source_id and verify validation.
    """
    # Arrange & Act & Assert
    with pytest.raises(ValueError):
        CitationMetadata(
            number=1,
            type="web",
            name="Test Source",
            url="https://example.com",
            source_id="",  # Invalid: min_length=1
        )


@pytest.mark.ai
def test_global_citation_manager__initializes_empty__with_no_citations() -> None:
    """
    Purpose: Verify GlobalCitationManager initializes with empty citation registry.
    Why this matters: Fresh manager should start with no registered citations.
    Setup summary: Create manager instance and verify empty registry.
    """
    # Arrange & Act
    manager = GlobalCitationManager()

    # Assert
    assert len(manager.get_all_citations()) == 0


@pytest.mark.ai
async def test_global_citation_manager__registers_citation__with_sequential_numbering() -> (
    None
):
    """
    Purpose: Verify GlobalCitationManager registers citations with sequential numbering.
    Why this matters: Sequential numbering ensures proper citation ordering.
    Setup summary: Register multiple citations and verify sequential numbering.
    """
    # Arrange
    manager = GlobalCitationManager()

    # Act
    citation1 = await manager.register_source(
        "source1", "web", "Source 1", "https://example1.com"
    )
    citation2 = await manager.register_source(
        "source2", "web", "Source 2", "https://example2.com"
    )

    # Assert
    assert citation1.number == 1
    assert citation2.number == 2
    assert citation1.name == "Source 1"
    assert citation2.name == "Source 2"


@pytest.mark.ai
async def test_global_citation_manager__prevents_duplicate_registration__for_same_source_id() -> (
    None
):
    """
    Purpose: Verify GlobalCitationManager prevents duplicate registration for same source_id.
    Why this matters: Prevents duplicate citations for the same source.
    Setup summary: Register same source_id twice and verify only one citation exists.
    """
    # Arrange
    manager = GlobalCitationManager()

    # Act
    citation1 = await manager.register_source(
        "source1", "web", "Source 1", "https://example.com"
    )
    citation2 = await manager.register_source(
        "source1", "web", "Source 1 Again", "https://example.com"
    )

    # Assert
    assert citation1.number == citation2.number
    assert citation1.name == "Source 1"
    assert citation2.name == "Source 1"
    assert len(manager.get_all_citations()) == 1


@pytest.mark.ai
async def test_global_citation_manager__get_citation__returns_registered_citation() -> (
    None
):
    """
    Purpose: Verify GlobalCitationManager.get_citation_by_number returns registered citation.
    Why this matters: Allows retrieval of citation metadata by citation number.
    Setup summary: Register citation and verify retrieval.
    """
    # Arrange
    manager = GlobalCitationManager()

    # Act
    registered_citation = await manager.register_source(
        "source1", "web", "Test Source", "https://example.com"
    )
    retrieved_citation = manager.get_citation_by_number(registered_citation.number)

    # Assert
    assert retrieved_citation is not None
    assert retrieved_citation.number == registered_citation.number
    assert retrieved_citation.name == registered_citation.name
    assert retrieved_citation.url == registered_citation.url


@pytest.mark.ai
def test_global_citation_manager__get_citation__returns_none__for_unregistered_source() -> (
    None
):
    """
    Purpose: Verify GlobalCitationManager.get_citation_by_number returns None for unregistered number.
    Why this matters: Ensures graceful handling of non-existent citations.
    Setup summary: Request citation for unregistered number and verify None result.
    """
    # Arrange
    manager = GlobalCitationManager()

    # Act
    citation = manager.get_citation_by_number(999)

    # Assert
    assert citation is None


@pytest.mark.ai
async def test_global_citation_manager__get_all_citations__returns_all_registered_citations() -> (
    None
):
    """
    Purpose: Verify GlobalCitationManager.get_all_citations returns all registered citations.
    Why this matters: Provides complete view of all registered citations.
    Setup summary: Register multiple citations and verify all are returned.
    """
    # Arrange
    manager = GlobalCitationManager()

    # Act
    await manager.register_source("source1", "web", "Source 1", "https://example1.com")
    await manager.register_source(
        "source2", "node-ingestion-chunks", "Source 2", "chunk-id-123"
    )

    all_citations = manager.get_all_citations()

    # Assert
    assert len(all_citations) == 2
    assert "source1" in all_citations
    assert "source2" in all_citations
    assert all_citations["source1"].type == "web"
    assert all_citations["source2"].type == "node-ingestion-chunks"


@pytest.mark.ai
async def test_global_citation_manager__handles_concurrent_registration__safely() -> (
    None
):
    """
    Purpose: Verify GlobalCitationManager handles concurrent registration safely.
    Why this matters: Ensures thread safety in multi-agent research scenarios.
    Setup summary: Simulate concurrent registration and verify no race conditions.
    """
    # Arrange
    manager = GlobalCitationManager()

    # Act - Simulate concurrent registration using asyncio
    import asyncio

    async def register_citation(source_id: str, name: str):
        return await manager.register_source(
            source_id, "web", name, f"https://{source_id}.com"
        )

    # Start multiple concurrent registrations
    tasks = []
    for i in range(5):
        task = register_citation(f"source{i}", f"Source {i}")
        tasks.append(task)

    results = await asyncio.gather(*tasks)

    # Assert
    assert len(results) == 5
    assert len(manager.get_all_citations()) == 5

    # Verify all citations have unique numbers
    numbers = [citation.number for citation in results]
    assert len(set(numbers)) == 5  # All numbers should be unique
    assert min(numbers) >= 1
    assert max(numbers) <= 5


@pytest.mark.ai
async def test_global_citation_manager__maintains_sequential_numbering__across_types() -> (
    None
):
    """
    Purpose: Verify GlobalCitationManager maintains sequential numbering across different types.
    Why this matters: Ensures consistent numbering regardless of citation type.
    Setup summary: Register citations of different types and verify sequential numbering.
    """
    # Arrange
    manager = GlobalCitationManager()

    # Act
    web_citation = await manager.register_source(
        "web-source", "web", "Web Source", "https://example.com"
    )
    chunk_citation = await manager.register_source(
        "chunk-source", "node-ingestion-chunks", "Chunk Source", "chunk-123"
    )

    # Assert
    assert web_citation.number == 1
    assert chunk_citation.number == 2
    assert web_citation.type == "web"
    assert chunk_citation.type == "node-ingestion-chunks"
