"""Tests for the SWOTReportRegistry."""

import pytest

from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.models.base import (
    SWOTReportComponentSection,
    SWOTReportSectionEntry,
)
from unique_swot.services.generation.models.registry import SWOTReportRegistry


def _make_section(h2="Test Section", num_entries=2):
    """Helper to create a test section."""
    entries = [
        SWOTReportSectionEntry(
            preview=f"Preview {i}", content=f"Content {i} [chunk_{i}]"
        )
        for i in range(num_entries)
    ]
    return SWOTReportComponentSection(h2=h2, entries=entries)


def test_registry_register_section():
    """Test registering a section returns a unique ID."""
    registry = SWOTReportRegistry()
    section = _make_section()

    section_id = registry.register_section(SWOTComponent.STRENGTHS, section)

    assert section_id.startswith("section_Strengths")


def test_registry_retrieve_section():
    """Test retrieving a registered section by ID."""
    registry = SWOTReportRegistry()
    section = _make_section("Test Strength")

    section_id = registry.register_section(SWOTComponent.STRENGTHS, section)
    retrieved = registry.retrieve_section(section_id)

    assert retrieved == section
    assert retrieved.h2 == "Test Strength"


def test_registry_retrieve_nonexistent_section():
    """Test retrieving a non-existent section returns None."""
    registry = SWOTReportRegistry()

    result = registry.retrieve_section("nonexistent_id")

    assert result is None


def test_registry_retrieve_component_sections():
    """Test retrieving all sections for a component."""
    registry = SWOTReportRegistry()

    section1 = _make_section("Strength 1")
    section2 = _make_section("Strength 2")

    registry.register_section(SWOTComponent.STRENGTHS, section1)
    registry.register_section(SWOTComponent.STRENGTHS, section2)
    registry.register_section(SWOTComponent.WEAKNESSES, _make_section("Weakness 1"))

    strengths = registry.retrieve_component_sections(SWOTComponent.STRENGTHS)

    assert len(strengths) == 2
    assert section1 in strengths
    assert section2 in strengths


def test_registry_retrieve_sections_for_component_json():
    """Test retrieving sections as JSON string."""
    registry = SWOTReportRegistry()

    section = _make_section("Test")
    section_id = registry.register_section(SWOTComponent.STRENGTHS, section)

    json_str = registry.retrieve_sections_for_component(SWOTComponent.STRENGTHS)

    assert section_id in json_str
    assert "Test" in json_str
    assert isinstance(json_str, str)


def test_registry_update_section():
    """Test updating an existing section."""
    registry = SWOTReportRegistry()

    original_section = _make_section("Original")
    section_id = registry.register_section(SWOTComponent.STRENGTHS, original_section)

    updated_section = _make_section("Updated")
    registry.update_section(section_id, updated_section)

    retrieved = registry.retrieve_section(section_id)
    assert retrieved.h2 == "Updated"


def test_registry_update_nonexistent_section_raises():
    """Test updating a non-existent section raises KeyError."""
    registry = SWOTReportRegistry()

    section = _make_section()

    with pytest.raises(KeyError):
        registry.update_section("nonexistent_id", section)


def test_registry_multiple_components():
    """Test registry handles multiple components independently."""
    registry = SWOTReportRegistry()

    registry.register_section(SWOTComponent.STRENGTHS, _make_section("S1"))
    registry.register_section(SWOTComponent.STRENGTHS, _make_section("S2"))
    registry.register_section(SWOTComponent.WEAKNESSES, _make_section("W1"))
    registry.register_section(SWOTComponent.OPPORTUNITIES, _make_section("O1"))
    registry.register_section(SWOTComponent.OPPORTUNITIES, _make_section("O2"))
    registry.register_section(SWOTComponent.OPPORTUNITIES, _make_section("O3"))
    registry.register_section(SWOTComponent.THREATS, _make_section("T1"))

    assert len(registry.retrieve_component_sections(SWOTComponent.STRENGTHS)) == 2
    assert len(registry.retrieve_component_sections(SWOTComponent.WEAKNESSES)) == 1
    assert len(registry.retrieve_component_sections(SWOTComponent.OPPORTUNITIES)) == 3
    assert len(registry.retrieve_component_sections(SWOTComponent.THREATS)) == 1


def test_registry_empty_component():
    """Test retrieving sections from an empty component."""
    registry = SWOTReportRegistry()

    sections = registry.retrieve_component_sections(SWOTComponent.STRENGTHS)

    assert len(sections) == 0
    assert sections == []


def test_registry_section_id_uniqueness():
    """Test that section IDs are unique."""
    registry = SWOTReportRegistry()

    section = _make_section()
    id1 = registry.register_section(SWOTComponent.STRENGTHS, section)
    id2 = registry.register_section(SWOTComponent.STRENGTHS, section)
    id3 = registry.register_section(SWOTComponent.WEAKNESSES, section)

    assert id1 != id2
    assert id1 != id3
    assert id2 != id3


def test_registry_retrieve_sections_exclude_items():
    """Test retrieving sections with exclude_items parameter."""
    registry = SWOTReportRegistry()

    section = _make_section("Test", num_entries=3)
    registry.register_section(SWOTComponent.STRENGTHS, section)

    # With exclude_items=True (default)
    json_with_exclusion = registry.retrieve_sections_for_component(
        SWOTComponent.STRENGTHS, exclude_items=True
    )

    # With exclude_items=False
    json_without_exclusion = registry.retrieve_sections_for_component(
        SWOTComponent.STRENGTHS, exclude_items=False
    )

    # Both should be valid JSON strings
    assert isinstance(json_with_exclusion, str)
    assert isinstance(json_without_exclusion, str)


def test_registry_preserves_section_data():
    """Test that registry preserves all section data."""
    registry = SWOTReportRegistry()

    entries = [
        SWOTReportSectionEntry(
            preview="Strong brand",
            content="The company has strong brand recognition [chunk_a]",
        ),
        SWOTReportSectionEntry(
            preview="Market leader", content="Leading position in the market [chunk_b]"
        ),
    ]
    section = SWOTReportComponentSection(h2="Market Position", entries=entries)

    section_id = registry.register_section(SWOTComponent.STRENGTHS, section)
    retrieved = registry.retrieve_section(section_id)

    assert retrieved.h2 == "Market Position"
    assert len(retrieved.entries) == 2
    assert retrieved.entries[0].preview == "Strong brand"
    assert retrieved.entries[1].content == "Leading position in the market [chunk_b]"
