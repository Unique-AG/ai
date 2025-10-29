"""
Unit tests for unique_custom/state.py module.
"""

from unittest.mock import Mock

import pytest

from unique_deep_research.unique_custom.state import (
    AgentState,
    ResearcherOutputState,
    ResearcherState,
    SupervisorState,
    override_reducer,
)


@pytest.mark.ai
def test_override_reducer__returns_new_value__when_override_type() -> None:
    """
    Purpose: Verify override_reducer returns new value when override type is specified.
    Why this matters: Allows overriding state values in LangGraph workflow.
    Setup summary: Call reducer with override type and verify new value is returned.
    """
    # Arrange
    current_value = ["item1", "item2"]
    new_value = {"type": "override", "value": ["item3"]}

    # Act
    result = override_reducer(current_value, new_value)

    # Assert
    assert result == ["item3"]


@pytest.mark.ai
def test_override_reducer__returns_original_value__when_no_override_type() -> None:
    """
    Purpose: Verify override_reducer returns original value when no override type.
    Why this matters: Ensures normal state updates work as expected.
    Setup summary: Call reducer without override type and verify original value is returned.
    """
    # Arrange
    current_value = ["item1", "item2"]
    new_value = ["item3"]

    # Act
    result = override_reducer(current_value, new_value)

    # Assert
    assert result == ["item1", "item2", "item3"]


@pytest.mark.ai
def test_override_reducer__handles_dict_override__correctly() -> None:
    """
    Purpose: Verify override_reducer handles dict override correctly.
    Why this matters: Supports complex state overrides in LangGraph.
    Setup summary: Call reducer with dict override and verify correct handling.
    """
    # Arrange
    current_value = {"key1": "value1"}
    new_value = {"type": "override", "value": {"key2": "value2"}}

    # Act
    result = override_reducer(current_value, new_value)

    # Assert
    assert result == {"key2": "value2"}


@pytest.mark.ai
def test_agent_state__inherits_messages_state__correctly() -> None:
    """
    Purpose: Verify AgentState inherits from MessagesState correctly.
    Why this matters: AgentState needs LangGraph message handling capabilities.
    Setup summary: Check AgentState has messages field from MessagesState.
    """
    # Arrange & Act
    state = AgentState()

    # Assert
    assert isinstance(state, dict)  # TypedDict behaves like dict
    # Check that messages field is available (from MessagesState)
    assert "messages" in AgentState.__annotations__


@pytest.mark.ai
def test_agent_state__has_required_fields__for_research_workflow() -> None:
    """
    Purpose: Verify AgentState has all required fields for research workflow.
    Why this matters: Ensures state contains all necessary data for research process.
    Setup summary: Check AgentState has all expected fields.
    """
    # Arrange & Act
    annotations = AgentState.__annotations__

    # Assert - Check that state is a TypedDict with expected structure
    assert isinstance(annotations, dict)
    expected_fields = {
        "research_brief",
        "notes",
        "final_report",
        "supervisor_messages",
        "research_iterations",
        "chat_service",
        "message_id",
        "tool_progress_reporter",
    }
    for field in expected_fields:
        assert field in annotations


@pytest.mark.ai
def test_researcher_state__has_research_specific_fields__for_researcher_agent() -> None:
    """
    Purpose: Verify ResearcherState has fields specific to researcher agent.
    Why this matters: Researcher agent needs specific state for research tasks.
    Setup summary: Check ResearcherState has researcher-specific fields.
    """
    # Arrange & Act
    annotations = ResearcherState.__annotations__

    # Assert - Check TypedDict structure
    assert isinstance(annotations, dict)
    expected_fields = {
        "researcher_messages",
        "research_topic",
        "research_iterations",
        "chat_service",
        "message_id",
    }
    for field in expected_fields:
        assert field in annotations


@pytest.mark.ai
def test_supervisor_state__has_supervisor_specific_fields__for_supervisor_agent() -> (
    None
):
    """
    Purpose: Verify SupervisorState has fields specific to supervisor agent.
    Why this matters: Supervisor agent needs specific state for coordination tasks.
    Setup summary: Check SupervisorState has supervisor-specific fields.
    """
    # Arrange & Act
    annotations = SupervisorState.__annotations__

    # Assert - Check TypedDict structure
    assert isinstance(annotations, dict)
    expected_fields = {
        "supervisor_messages",
        "research_iterations",
        "research_brief",
        "notes",
        "chat_service",
        "message_id",
    }
    for field in expected_fields:
        assert field in annotations


@pytest.mark.ai
def test_researcher_output_state__has_output_fields__for_researcher_results() -> None:
    """
    Purpose: Verify ResearcherOutputState has fields for researcher output.
    Why this matters: Researcher output needs specific state structure for results.
    Setup summary: Check ResearcherOutputState has output-specific fields.
    """
    # Arrange & Act
    annotations = ResearcherOutputState.__annotations__

    # Assert
    assert isinstance(annotations, dict)
    expected_fields = {"compressed_research"}
    for field in expected_fields:
        assert field in annotations


@pytest.mark.ai
def test_agent_state__can_be_created__with_initial_values() -> None:
    """
    Purpose: Verify AgentState can be created with initial values.
    Why this matters: Allows initialization of state with specific values.
    Setup summary: Create AgentState with initial values and verify they are set.
    """
    # Arrange
    mock_chat_service = Mock()

    # Act
    state = AgentState(
        research_brief="Test research brief",
        notes=["note1", "note2"],
        final_report="Test report",
        chat_service=mock_chat_service,
        message_id="test-message-id",
    )

    # Assert
    assert state["research_brief"] == "Test research brief"
    assert state["notes"] == ["note1", "note2"]
    assert state["final_report"] == "Test report"
    assert state["chat_service"] == mock_chat_service
    assert state["message_id"] == "test-message-id"


@pytest.mark.ai
def test_researcher_state__can_be_created__with_research_topic() -> None:
    """
    Purpose: Verify ResearcherState can be created with research topic.
    Why this matters: Researcher needs specific topic for focused research.
    Setup summary: Create ResearcherState with research topic and verify it is set.
    """
    # Arrange & Act
    state = ResearcherState(
        research_topic="AI research methods",
        notes=["finding1"],
        research_iterations=1,
    )

    # Assert
    assert state["research_topic"] == "AI research methods"
    assert state["notes"] == ["finding1"]
    assert state["research_iterations"] == 1


@pytest.mark.ai
def test_supervisor_state__can_be_created__with_supervisor_data() -> None:
    """
    Purpose: Verify SupervisorState can be created with supervisor data.
    Why this matters: Supervisor needs specific state for coordination.
    Setup summary: Create SupervisorState with supervisor data and verify it is set.
    """
    # Arrange & Act
    state = SupervisorState(
        research_brief="Supervisor research brief",
        notes=["supervisor_note1"],
        research_iterations=2,
    )

    # Assert
    assert state["research_brief"] == "Supervisor research brief"
    assert state["notes"] == ["supervisor_note1"]
    assert state["research_iterations"] == 2


@pytest.mark.ai
def test_researcher_output_state__can_be_created__with_output_data() -> None:
    """
    Purpose: Verify ResearcherOutputState can be created with output data.
    Why this matters: Researcher output needs specific state for results.
    Setup summary: Create ResearcherOutputState with output data and verify it is set.
    """
    # Arrange & Act
    state = ResearcherOutputState(
        compressed_research="Synthesized research findings",
    )

    # Assert
    assert state["compressed_research"] == "Synthesized research findings"
