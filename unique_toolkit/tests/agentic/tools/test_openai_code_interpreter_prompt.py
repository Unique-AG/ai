"""Tests for the default code interpreter system prompts (base and fence variants)."""

import pytest

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.tool import (
    OpenAICodeInterpreterConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.tool.config import (
    DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
    DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE,
)

_DEFAULT_PROMPTS = pytest.mark.parametrize(
    "prompt",
    [
        DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
        DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE,
    ],
    ids=["base", "fence"],
)


@pytest.mark.ai
@_DEFAULT_PROMPTS
def test_default_prompts__require_wrapping_pdf_layout__not_draw_string(
    prompt: str,
) -> None:
    """
    Purpose: Verify both default prompts tell the model to build PDFs with wrapping flowables.
    Why this matters: UN-28750 reported a PDF drawn line by line with `canvas.drawString`;
    lines ran up to 242% of the A4 width and 45% of the words were off the page.
    Setup summary: Assert the PDF section names Platypus flowables and bans non-wrapping calls.
    """
    assert "PDF files: CRITICAL rules" in prompt
    assert "reportlab Platypus" in prompt
    assert "`SimpleDocTemplate(path, pagesize=A4)`" in prompt
    assert "`ListFlowable`" in prompt
    assert "NEVER write running text with `canvas.drawString`" in prompt
    assert "`Preformatted`" in prompt


@pytest.mark.ai
@_DEFAULT_PROMPTS
def test_default_prompts__pdf_rules_cover_markdown_font_and_layout_check(
    prompt: str,
) -> None:
    """
    Purpose: Verify the PDF section covers Markdown conversion, escaping, font and a final check.
    Why this matters: The reported PDF kept raw bullets, used base Helvetica (which cannot draw
    many accented letters) and was linked without anyone checking it fits the page.
    Setup summary: Assert each of those rules is present in the default prompt.
    """
    assert "`**x**` into `<b>x</b>`" in prompt
    assert 'start="•"' in prompt
    assert "Escape `&`, `<` and `>`" in prompt
    assert "`colWidths` sum to `doc.width`" in prompt
    assert "DejaVuSans.ttf" in prompt
    assert "matplotlib.get_data_path()" in prompt
    assert "`registerFontFamily`" in prompt
    assert "`pdfplumber`" in prompt
    assert "`x1` is at most `page.width`" in prompt


@pytest.mark.ai
@_DEFAULT_PROMPTS
def test_default_prompts__pdf_rules_sit_before_dataframe_section(prompt: str) -> None:
    """
    Purpose: Verify the PDF section is placed with the file rules, ahead of the table section.
    Why this matters: The section is concatenated into the prompt; a misplaced join would split
    another section or drop the text that follows it.
    Setup summary: Compare the positions of the PDF heading and the dataframe heading.
    """
    pdf_index = prompt.index("PDF files: CRITICAL rules")
    tables_index = prompt.index("# Displaying Dataframes/Tables:")
    file_types_index = prompt.index("Only the following file types are allowed")

    assert file_types_index < pdf_index < tables_index
    assert prompt.count("PDF files: CRITICAL rules") == 1


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
