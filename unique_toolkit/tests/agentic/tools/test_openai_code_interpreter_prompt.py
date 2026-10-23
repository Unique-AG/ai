"""Tests for the default code interpreter system prompt (fence variant)."""

import pytest

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.tool import (
    OpenAICodeInterpreterConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.tool.config import (
    DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE,
)


@pytest.mark.ai
def test_fence_prompt__requires_matplotlib_for_charts__not_for_every_png() -> None:
    """
    Purpose: Verify the matplotlib rule is scoped to charts and plots.
    Why this matters: Forcing matplotlib for every PNG pushed the model to place page
    layouts with hand-picked coordinates, which produced overlapping text.
    Setup summary: Read the default fence prompt; assert chart scoping and no blanket rule.
    """
    prompt = DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE

    assert "static charts and plots (PNG): ALWAYS use **matplotlib**" in prompt
    assert "static image outputs (PNG): ALWAYS use **matplotlib**" not in prompt
    assert "NEVER use plotly to produce a PNG" in prompt


@pytest.mark.ai
def test_fence_prompt__has_layout_rules__for_page_style_images() -> None:
    """
    Purpose: Verify the prompt tells the model how to lay out page-style images safely.
    Why this matters: UN-26625 reported overlapping text in generated "simple page" images.
    Setup summary: Assert the layout section and its measure / wrap / verify rules exist.
    """
    prompt = DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE

    assert "Page and layout images" in prompt
    assert "NEVER hardcode positions or sizes by eye" in prompt
    assert "running `y` cursor" in prompt
    assert "draw.textbbox" in prompt
    assert "get_window_extent" in prompt
    assert "textwrap.wrap" in prompt
    assert "no two text bounding boxes intersect" in prompt


@pytest.mark.ai
def test_fence_prompt__keeps_file_templates__after_layout_rules() -> None:
    """
    Purpose: Verify the Jinja file sections are still appended after the base prompt.
    Why this matters: The base prompt grew; the uploaded/generated file listings must remain.
    Setup summary: Assert the template placeholders appear in the default prompt.
    """
    prompt = DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE

    assert "{% for file in user_uploaded_files %}" in prompt
    assert "{% for file in code_interpreter_artifacts %}" in prompt
    assert "{% for file in failed_uploads %}" in prompt


@pytest.mark.ai
def test_config__uses_fence_prompt_as_default__for_system_prompt() -> None:
    """
    Purpose: Verify the tool config ships the fence prompt by default.
    Why this matters: Operators who never override the prompt get the layout rules.
    Setup summary: Instantiate the config and compare the field with the constant.
    """
    config = OpenAICodeInterpreterConfig()

    assert (
        config.tool_description_for_system_prompt
        == DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE
    )
