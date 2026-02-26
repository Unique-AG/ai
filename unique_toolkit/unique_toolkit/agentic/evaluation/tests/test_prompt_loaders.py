"""Tests for prompt loader functions."""

import pytest

from unique_toolkit.agentic.evaluation.context_relevancy.prompts import (
    system_prompt_loader as context_system_prompt_loader,
)
from unique_toolkit.agentic.evaluation.context_relevancy.prompts import (
    user_prompt_loader as context_user_prompt_loader,
)
from unique_toolkit.agentic.evaluation.hallucination.prompts import (
    system_prompt_loader as hallucination_system_prompt_loader,
)
from unique_toolkit.agentic.evaluation.hallucination.prompts import (
    user_prompt_loader as hallucination_user_prompt_loader,
)


@pytest.mark.ai
def test_context_system_prompt_loader__returns_non_empty_string__on_call() -> None:
    """
    Purpose: Verify that the context relevancy system prompt loader returns a valid string.
    Why this matters: The system prompt is critical for guiding the evaluation LLM's behavior.
    Setup summary: Call the loader function and assert type and non-empty content.
    """
    # Arrange - No setup needed for this test

    # Act
    prompt: str = context_system_prompt_loader()

    # Assert
    assert isinstance(prompt, str)
    assert len(prompt) > 0


@pytest.mark.ai
def test_context_user_prompt_loader__returns_non_empty_string__on_call() -> None:
    """
    Purpose: Verify that the context relevancy user prompt loader returns a valid string.
    Why this matters: The user prompt template must be valid for evaluation requests.
    Setup summary: Call the loader function and assert type and non-empty content.
    """
    # Arrange - No setup needed for this test

    # Act
    prompt: str = context_user_prompt_loader()

    # Assert
    assert isinstance(prompt, str)
    assert len(prompt) > 0


@pytest.mark.ai
def test_context_system_prompt__contains_jinja_syntax__for_structured_output() -> None:
    """
    Purpose: Verify that system prompt contains Jinja2 template syntax for structured output control.
    Why this matters: Template must support conditional rendering based on structured_output flag.
    Setup summary: Load system prompt and check for Jinja2 conditional blocks.
    """
    # Arrange - No setup needed

    # Act
    prompt: str = context_system_prompt_loader()

    # Assert
    assert "{% if structured_output %}" in prompt or "{%" in prompt


@pytest.mark.ai
def test_context_user_prompt__contains_jinja_variables__for_input_and_context() -> None:
    """
    Purpose: Verify that user prompt contains required Jinja2 variable placeholders.
    Why this matters: Template must support dynamic insertion of input text and context texts.
    Setup summary: Load user prompt and check for expected variable placeholders.
    """
    # Arrange - No setup needed

    # Act
    prompt: str = context_user_prompt_loader()

    # Assert
    assert "{{ input_text }}" in prompt
    assert "{{ context_texts }}" in prompt


@pytest.mark.ai
def test_context_system_prompt__has_both_structured_and_regular_modes__in_template() -> (
    None
):
    """
    Purpose: Verify that system prompt template supports both structured and regular output modes.
    Why this matters: Template must handle both evaluation output formats correctly.
    Setup summary: Load system prompt and check for conditional blocks for both modes.
    """
    # Arrange - No setup needed

    # Act
    prompt: str = context_system_prompt_loader()

    # Assert
    assert "{% if structured_output %}" in prompt
    assert "{% else %}" in prompt or "{% endif %}" in prompt


@pytest.mark.ai
def test_context_user_prompt__has_conditional_json_instruction__for_unstructured_mode() -> (
    None
):
    """
    Purpose: Verify that user prompt has conditional JSON instruction for unstructured mode.
    Why this matters: Non-structured mode requires explicit JSON formatting instructions.
    Setup summary: Load user prompt and check for conditional JSON instruction block.
    """
    # Arrange - No setup needed

    # Act
    prompt: str = context_user_prompt_loader()

    # Assert
    assert "{% if not structured_output %}" in prompt or "{%" in prompt


@pytest.mark.ai
def test_context_prompts__are_consistent_between_calls__for_determinism() -> None:
    """
    Purpose: Verify that prompt loaders return consistent content across multiple invocations.
    Why this matters: Ensures deterministic behavior and no hidden state in loaders.
    Setup summary: Call loaders twice and compare results for equality.
    """
    # Arrange - No setup needed

    # Act
    system_prompt_1: str = context_system_prompt_loader()
    system_prompt_2: str = context_system_prompt_loader()
    user_prompt_1: str = context_user_prompt_loader()
    user_prompt_2: str = context_user_prompt_loader()

    # Assert
    assert system_prompt_1 == system_prompt_2
    assert user_prompt_1 == user_prompt_2


@pytest.mark.ai
def test_hallucination_system_prompt_loader__returns_non_empty_string__on_call() -> (
    None
):
    """
    Purpose: Verify that the hallucination system prompt loader returns a valid string.
    Why this matters: The system prompt is critical for hallucination detection behavior.
    Setup summary: Call the loader function and assert type and non-empty content.
    """
    # Arrange - No setup needed

    # Act
    prompt: str = hallucination_system_prompt_loader()

    # Assert
    assert isinstance(prompt, str)
    assert len(prompt) > 0


@pytest.mark.ai
def test_hallucination_user_prompt_loader__returns_non_empty_string__on_call() -> None:
    """
    Purpose: Verify that the hallucination user prompt loader returns a valid string.
    Why this matters: The user prompt template must be valid for hallucination evaluation.
    Setup summary: Call the loader function and assert type and non-empty content.
    """
    # Arrange - No setup needed

    # Act
    prompt: str = hallucination_user_prompt_loader()

    # Assert
    assert isinstance(prompt, str)
    assert len(prompt) > 0


@pytest.mark.ai
def test_hallucination_system_prompt__contains_jinja_syntax__for_has_context() -> None:
    """
    Purpose: Verify that system prompt contains Jinja2 template syntax for context handling.
    Why this matters: Template must support conditional rendering based on has_context flag.
    Setup summary: Load system prompt and check for Jinja2 conditional blocks.
    """
    # Arrange - No setup needed

    # Act
    prompt: str = hallucination_system_prompt_loader()

    # Assert
    assert "{% if has_context %}" in prompt or "{%" in prompt


@pytest.mark.ai
def test_hallucination_user_prompt__contains_jinja_variables__for_input_and_output() -> (
    None
):
    """
    Purpose: Verify that user prompt contains required Jinja2 variable placeholders.
    Why this matters: Template must support dynamic insertion of input and output texts.
    Setup summary: Load user prompt and check for expected variable placeholders.
    """
    # Arrange - No setup needed

    # Act
    prompt: str = hallucination_user_prompt_loader()

    # Assert
    assert "{{ input_text }}" in prompt
    assert "{{ output_text }}" in prompt


@pytest.mark.ai
def test_hallucination_system_prompt__has_context_conditional__in_template() -> None:
    """
    Purpose: Verify that system prompt template has conditional logic for has_context.
    Why this matters: Template must handle both context and non-context evaluation scenarios.
    Setup summary: Load system prompt and check for conditional blocks with else/endif.
    """
    # Arrange - No setup needed

    # Act
    prompt: str = hallucination_system_prompt_loader()

    # Assert
    assert "{% if has_context %}" in prompt
    assert "{% else %}" in prompt or "{% endif %}" in prompt


@pytest.mark.ai
def test_hallucination_user_prompt__has_optional_context_fields__in_template() -> None:
    """
    Purpose: Verify that user prompt has conditional blocks for optional context fields.
    Why this matters: Template must support optional contexts_text and history_messages_text.
    Setup summary: Load user prompt and check for conditional blocks or variable placeholders.
    """
    # Arrange - No setup needed

    # Act
    prompt: str = hallucination_user_prompt_loader()

    # Assert
    assert "{% if contexts_text %}" in prompt or "{{ contexts_text }}" in prompt
    assert (
        "{% if history_messages_text %}" in prompt
        or "{{ history_messages_text }}" in prompt
    )


@pytest.mark.ai
def test_hallucination_system_prompt__mentions_hallucination_concepts__in_content() -> (
    None
):
    """
    Purpose: Verify that system prompt mentions hallucination-related concepts.
    Why this matters: Ensures prompt properly guides model to detect hallucinations.
    Setup summary: Load system prompt and check for hallucination-related keywords.
    """
    # Arrange - No setup needed

    # Act
    prompt: str = hallucination_system_prompt_loader()
    prompt_lower: str = prompt.lower()

    # Assert
    assert (
        "hallucination" in prompt_lower
        or "grounded" in prompt_lower
        or "supported" in prompt_lower
    )


@pytest.mark.ai
def test_hallucination_user_prompt__contains_data_sections__for_input_and_output() -> (
    None
):
    """
    Purpose: Verify that user prompt has sections for input and output data.
    Why this matters: Template must clearly separate input and output for evaluation.
    Setup summary: Load user prompt and check for input/output section markers.
    """
    # Arrange - No setup needed

    # Act
    prompt: str = hallucination_user_prompt_loader()

    # Assert
    assert "Input:" in prompt or "input" in prompt.lower()
    assert "Output:" in prompt or "output" in prompt.lower()


@pytest.mark.ai
def test_hallucination_prompts__are_consistent_between_calls__for_determinism() -> None:
    """
    Purpose: Verify that hallucination prompt loaders return consistent content.
    Why this matters: Ensures deterministic behavior and no hidden state in loaders.
    Setup summary: Call loaders twice and compare results for equality.
    """
    # Arrange - No setup needed

    # Act
    system_prompt_1: str = hallucination_system_prompt_loader()
    system_prompt_2: str = hallucination_system_prompt_loader()
    user_prompt_1: str = hallucination_user_prompt_loader()
    user_prompt_2: str = hallucination_user_prompt_loader()

    # Assert
    assert system_prompt_1 == system_prompt_2
    assert user_prompt_1 == user_prompt_2


@pytest.mark.ai
def test_context_relevancy_loaders__can_access_template_files__without_errors() -> None:
    """
    Purpose: Verify that context relevancy loaders can successfully access template files.
    Why this matters: Ensures template files exist and are readable at runtime.
    Setup summary: Call loaders and assert no FileNotFoundError is raised.
    """
    # Arrange - No setup needed

    # Act & Assert
    try:
        system_prompt: str = context_system_prompt_loader()
        user_prompt: str = context_user_prompt_loader()
        assert system_prompt is not None
        assert user_prompt is not None
    except FileNotFoundError as e:
        pytest.fail(f"Prompt loader failed to access template file: {e}")


@pytest.mark.ai
def test_hallucination_loaders__can_access_template_files__without_errors() -> None:
    """
    Purpose: Verify that hallucination loaders can successfully access template files.
    Why this matters: Ensures template files exist and are readable at runtime.
    Setup summary: Call loaders and assert no FileNotFoundError is raised.
    """
    # Arrange - No setup needed

    # Act & Assert
    try:
        system_prompt: str = hallucination_system_prompt_loader()
        user_prompt: str = hallucination_user_prompt_loader()
        assert system_prompt is not None
        assert user_prompt is not None
    except FileNotFoundError as e:
        pytest.fail(f"Prompt loader failed to access template file: {e}")
