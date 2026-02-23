"""Tests for code interpreter generated-files postprocessor (config, __init__, helpers)."""

from unittest.mock import MagicMock

import pytest

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors import (
    generated_files as gen_mod,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.generated_files import (
    DisplayCodeInterpreterFilesPostProcessor,
    DisplayCodeInterpreterFilesPostProcessorConfig,
)
from unique_toolkit.content.schemas import ContentReference


@pytest.mark.ai
def test_display_code_interpreter_files_config__has_defaults__when_constructed_with_no_args() -> (
    None
):
    """
    Purpose: Verify DisplayCodeInterpreterFilesPostProcessorConfig default field values.
    Why this matters: Ensures upload and concurrency defaults are correct.
    Setup summary: Instantiate config with no args; assert defaults.
    """
    # Act
    config = DisplayCodeInterpreterFilesPostProcessorConfig()

    # Assert
    assert config.upload_to_chat is True
    assert config.upload_scope_id == "<SCOPE_ID_PLACEHOLDER>"
    assert config.file_download_failed_message == "⚠️ File download failed ..."
    assert config.max_concurrent_file_downloads == 10


@pytest.mark.ai
def test_display_code_interpreter_files_post_processor__raises__when_upload_to_chat_true_and_no_chat_service() -> (
    None
):
    """
    Purpose: Verify ValueError when upload_to_chat is True but chat_service is None.
    Why this matters: Prevents misconfiguration that would fail at runtime.
    Setup summary: Construct with upload_to_chat=True, chat_service=None; assert ValueError.
    """
    # Arrange
    config = DisplayCodeInterpreterFilesPostProcessorConfig(upload_to_chat=True)
    mock_client = MagicMock()
    mock_content_service = MagicMock()

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        DisplayCodeInterpreterFilesPostProcessor(
            client=mock_client,
            content_service=mock_content_service,
            config=config,
            chat_service=None,
        )
    assert "ChatService" in str(exc_info.value)


@pytest.mark.ai
def test_display_code_interpreter_files_post_processor__accepts_no_chat_service__when_upload_to_chat_false() -> (
    None
):
    """
    Purpose: Verify constructor succeeds when upload_to_chat is False and chat_service is None.
    Why this matters: Upload to scope path does not require ChatService.
    Setup summary: Construct with upload_to_chat=False, chat_service=None; assert no raise.
    """
    # Arrange
    config = DisplayCodeInterpreterFilesPostProcessorConfig(upload_to_chat=False)
    mock_client = MagicMock()
    mock_content_service = MagicMock()

    # Act
    processor = DisplayCodeInterpreterFilesPostProcessor(
        client=mock_client,
        content_service=mock_content_service,
        config=config,
        chat_service=None,
    )

    # Assert
    assert processor._chat_service is None
    assert processor._config.upload_to_chat is False


@pytest.mark.ai
def test_get_next_ref_number__returns_one__when_references_empty() -> None:
    """
    Purpose: Verify next reference number is 1 when no references exist.
    Why this matters: First citation gets sequence number 1.
    Setup summary: Call _get_next_ref_number with empty list; assert 1.
    """
    # Act
    result = gen_mod._get_next_ref_number([])

    # Assert
    assert result == 1


@pytest.mark.ai
def test_get_next_ref_number__returns_max_plus_one__when_references_given() -> None:
    """
    Purpose: Verify next reference number is max(sequence_number) + 1.
    Why this matters: Citations are numbered sequentially without collision.
    Setup summary: References with sequence_number 2 and 5; assert 6.
    """
    # Arrange
    refs = [
        ContentReference(
            name="a",
            sequence_number=2,
            source="s",
            source_id="sid",
            url="u",
        ),
        ContentReference(
            name="b",
            sequence_number=5,
            source="s",
            source_id="sid",
            url="u",
        ),
    ]

    # Act
    result = gen_mod._get_next_ref_number(refs)

    # Assert
    assert result == 6


@pytest.mark.ai
def test_replace_container_file_error__replaces_image_markdown__with_error_message() -> (
    None
):
    """
    Purpose: Verify sandbox image markdown is replaced by error message when download fails.
    Why this matters: User sees a clear failure message instead of broken image.
    Setup summary: Text with [label](sandbox:/mnt/data/file.png); assert replaced with error message.
    """
    # Arrange
    text = "See [chart](sandbox:/mnt/data/file.png) here."
    error_message = "⚠️ File download failed ..."

    # Act
    new_text, replaced = gen_mod._replace_container_file_error(
        text, filename="file.png", error_message=error_message
    )

    # Assert
    assert replaced is True
    assert "file.png" not in new_text or "sandbox" not in new_text
    assert error_message in new_text


@pytest.mark.ai
def test_replace_container_file_error__returns_unchanged__when_no_matching_markdown() -> (
    None
):
    """
    Purpose: Verify text is unchanged when no sandbox image markdown for filename exists.
    Why this matters: Avoids incorrect replacements.
    Setup summary: Text without matching pattern for given filename; assert (text, False).
    """
    # Arrange
    text = "No sandbox link here."
    error_message = "⚠️ File download failed ..."

    # Act
    new_text, replaced = gen_mod._replace_container_file_error(
        text, filename="missing.png", error_message=error_message
    )

    # Assert
    assert replaced is False
    assert new_text == text


@pytest.mark.ai
def test_replace_container_image_citation__replaces_markdown__with_unique_content_image() -> (
    None
):
    """
    Purpose: Verify sandbox image markdown is replaced by unique://content/{id} image.
    Why this matters: Images are displayed from uploaded content.
    Setup summary: Text with image markdown for filename; assert unique://content/{content_id} in result.
    """
    # Arrange
    text = "Chart: [x](sandbox:/mnt/data/plot.png)"
    content_id = "content-123"

    # Act
    new_text, replaced = gen_mod._replace_container_image_citation(
        text, filename="plot.png", content_id=content_id
    )

    # Assert
    assert replaced is True
    assert f"unique://content/{content_id}" in new_text
    assert "sandbox" not in new_text


@pytest.mark.ai
def test_replace_container_file_citation__replaces_link__with_sup_ref_number() -> None:
    """
    Purpose: Verify file link markdown is replaced by <sup>ref_number</sup>.
    Why this matters: Non-image files are shown as reference superscripts.
    Setup summary: Text with [label](sandbox:/mnt/data/data.csv); assert <sup>1</sup> in result.
    """
    # Arrange
    text = "Data in [file](sandbox:/mnt/data/data.csv)."
    ref_number = 1

    # Act
    new_text, replaced = gen_mod._replace_container_file_citation(
        text, filename="data.csv", ref_number=ref_number
    )

    # Assert
    assert replaced is True
    assert "<sup>1</sup>" in new_text
    assert "sandbox" not in new_text


@pytest.mark.ai
def test_replace_container_html_citation__replaces_markdown__with_html_rendering_block() -> (
    None
):
    """
    Purpose: Verify sandbox HTML link is replaced by HtmlRendering code block with content URL.
    Why this matters: HTML files are rendered in chat via special block.
    Setup summary: Text with link to .html file; assert ```HtmlRendering and unique://content in result.
    """
    # Arrange
    text = "Report: [report](sandbox:/mnt/data/report.html)"
    content_id = "html-content-456"

    # Act
    new_text, replaced = gen_mod._replace_container_html_citation(
        text, filename="report.html", content_id=content_id
    )

    # Assert
    assert replaced is True
    assert "HtmlRendering" in new_text
    assert f"unique://content/{content_id}" in new_text
    assert "sandbox" not in new_text
