from typing import Any, cast

import pytest
from openai.types.chat import (
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartInputAudioParam,
    ChatCompletionContentPartTextParam,
)
from openai.types.chat.chat_completion_content_part_param import (
    File as ChatCompletionContentPartFileParam,
)

from unique_toolkit.language_model._responses_api_utils import (
    _convert_audio_part_to_responses_api,
    _convert_file_part_to_responses_api,
    _convert_image_part_to_responses_api,
    _convert_text_part_to_responses_api,
    convert_user_message_content_to_responses_api,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def text_part() -> dict[str, Any]:
    """Basic text content part fixture."""
    return {"type": "text", "text": "Hello, world!"}


@pytest.fixture
def image_part_with_detail() -> dict[str, Any]:
    """Image content part with explicit detail level."""
    return {
        "type": "image_url",
        "image_url": {"url": "https://example.com/image.jpg", "detail": "high"},
    }


@pytest.fixture
def image_part_without_detail() -> dict[str, Any]:
    """Image content part without detail level."""
    return {
        "type": "image_url",
        "image_url": {"url": "https://example.com/image.jpg"},
    }


@pytest.fixture
def file_part_with_id() -> dict[str, Any]:
    """File content part with file_id only."""
    return {"type": "file", "file": {"file_id": "file-123"}}


@pytest.fixture
def file_part_complete() -> dict[str, Any]:
    """File content part with all fields."""
    return {
        "type": "file",
        "file": {
            "file_id": "file-123",
            "file_data": "base64encodeddata",
            "filename": "document.pdf",
        },
    }


@pytest.fixture
def audio_part() -> dict[str, Any]:
    """Audio content part fixture."""
    return {
        "type": "input_audio",
        "input_audio": {"data": "base64audiodata", "format": "wav"},
    }


# ============================================================================
# Tests for _convert_text_part_to_responses_api
# ============================================================================


@pytest.mark.ai
def test_convert_text_part__returns_correct_format__with_simple_text(
    text_part: dict[str, Any],
) -> None:
    """
    Purpose: Verify text content part is converted to Responses API format correctly.
    Why this matters: Text is the most common content type and must be properly formatted.
    Setup summary: Use text fixture, convert, and verify type and content.
    """
    # Arrange
    part = cast(ChatCompletionContentPartTextParam, text_part)

    # Act
    result = _convert_text_part_to_responses_api(part)

    # Assert
    assert result["type"] == "input_text"
    assert result["text"] == "Hello, world!"


@pytest.mark.ai
def test_convert_text_part__preserves_unicode__with_special_chars() -> None:
    """
    Purpose: Ensure Unicode and special characters are preserved in text conversion.
    Why this matters: International users need proper character handling.
    Setup summary: Create part with Unicode, convert, verify preservation.
    """
    # Arrange
    part = cast(
        ChatCompletionContentPartTextParam, {"type": "text", "text": "Hello 世界! 🌍"}
    )

    # Act
    result = _convert_text_part_to_responses_api(part)

    # Assert
    assert result["text"] == "Hello 世界! 🌍"


@pytest.mark.ai
def test_convert_text_part__handles_empty_string__correctly() -> None:
    """
    Purpose: Verify empty text strings are handled without errors.
    Why this matters: Edge cases must not break the conversion pipeline.
    Setup summary: Create part with empty string, convert, verify structure.
    """
    # Arrange
    part = cast(ChatCompletionContentPartTextParam, {"type": "text", "text": ""})

    # Act
    result = _convert_text_part_to_responses_api(part)

    # Assert
    assert result["type"] == "input_text"
    assert result["text"] == ""


# ============================================================================
# Tests for _convert_image_part_to_responses_api
# ============================================================================


@pytest.mark.ai
def test_convert_image_part__uses_provided_detail__when_present(
    image_part_with_detail: dict[str, Any],
) -> None:
    """
    Purpose: Verify explicit detail level is preserved during conversion.
    Why this matters: Detail level affects API behavior and costs.
    Setup summary: Use image with detail fixture, convert, verify detail preserved.
    """
    # Arrange
    part = cast(ChatCompletionContentPartImageParam, image_part_with_detail)

    # Act
    result = _convert_image_part_to_responses_api(part)

    # Assert
    assert result["type"] == "input_image"
    assert result.get("image_url") == "https://example.com/image.jpg"
    assert result.get("detail") == "high"


@pytest.mark.ai
def test_convert_image_part__defaults_to_auto__when_detail_missing(
    image_part_without_detail: dict[str, Any],
) -> None:
    """
    Purpose: Verify detail defaults to 'auto' when not provided.
    Why this matters: Responses API requires detail field; must have safe default.
    Setup summary: Use image without detail, convert, verify auto default.
    """
    # Arrange
    part = cast(ChatCompletionContentPartImageParam, image_part_without_detail)

    # Act
    result = _convert_image_part_to_responses_api(part)

    # Assert
    assert result["type"] == "input_image"
    assert result.get("image_url") == "https://example.com/image.jpg"
    assert result.get("detail") == "auto"


@pytest.mark.parametrize(
    "detail_level",
    ["low", "high", "auto"],
    ids=["low-detail", "high-detail", "auto-detail"],
)
@pytest.mark.ai
def test_convert_image_part__handles_all_detail_levels__correctly(
    detail_level: str,
) -> None:
    """
    Purpose: Verify all valid detail levels are handled correctly.
    Why this matters: API accepts multiple detail values; all must work.
    Setup summary: Parametrized test with all valid detail levels.
    """
    # Arrange
    part = cast(
        ChatCompletionContentPartImageParam,
        {
            "type": "image_url",
            "image_url": {
                "url": "https://example.com/test.png",
                "detail": detail_level,
            },
        },
    )

    # Act
    result = _convert_image_part_to_responses_api(part)

    # Assert
    assert result.get("detail") == detail_level


# ============================================================================
# Tests for _convert_file_part_to_responses_api
# ============================================================================


@pytest.mark.ai
def test_convert_file_part__includes_only_file_id__when_minimal(
    file_part_with_id: dict[str, Any],
) -> None:
    """
    Purpose: Verify file conversion with only file_id works correctly.
    Why this matters: Minimal file references are common for existing files.
    Setup summary: Use minimal file fixture, convert, verify only file_id present.
    """
    # Arrange
    part = cast(ChatCompletionContentPartFileParam, file_part_with_id)

    # Act
    result = _convert_file_part_to_responses_api(part)

    # Assert
    assert result["type"] == "input_file"
    assert result.get("file_id") == "file-123"
    assert "file_data" not in result
    assert "filename" not in result


@pytest.mark.ai
def test_convert_file_part__includes_all_fields__when_complete(
    file_part_complete: dict[str, Any],
) -> None:
    """
    Purpose: Verify file conversion preserves all provided fields.
    Why this matters: Complete file metadata must be maintained for uploads.
    Setup summary: Use complete file fixture, convert, verify all fields.
    """
    # Arrange
    part = cast(ChatCompletionContentPartFileParam, file_part_complete)

    # Act
    result = _convert_file_part_to_responses_api(part)

    # Assert
    assert result["type"] == "input_file"
    assert result.get("file_id") == "file-123"
    assert result.get("file_data") == "base64encodeddata"
    assert result.get("filename") == "document.pdf"


@pytest.mark.ai
def test_convert_file_part__handles_partial_fields__correctly() -> None:
    """
    Purpose: Verify file conversion with subset of optional fields works.
    Why this matters: Files may have varying combinations of metadata.
    Setup summary: Create file with file_id and filename only, verify conversion.
    """
    # Arrange
    part = cast(
        ChatCompletionContentPartFileParam,
        {
            "type": "file",
            "file": {"file_id": "file-456", "filename": "report.xlsx"},
        },
    )

    # Act
    result = _convert_file_part_to_responses_api(part)

    # Assert
    assert result["type"] == "input_file"
    assert result.get("file_id") == "file-456"
    assert result.get("filename") == "report.xlsx"
    assert "file_data" not in result


# ============================================================================
# Tests for _convert_audio_part_to_responses_api
# ============================================================================


@pytest.mark.ai
def test_convert_audio_part__converts_correctly__with_valid_audio(
    audio_part: dict[str, Any],
) -> None:
    """
    Purpose: Verify audio content part is converted to Responses API format.
    Why this matters: Audio input must be properly formatted for API.
    Setup summary: Use audio fixture, convert, verify structure.
    """
    # Arrange
    part = cast(ChatCompletionContentPartInputAudioParam, audio_part)

    # Act
    result = _convert_audio_part_to_responses_api(part)

    # Assert
    assert result["type"] == "input_audio"
    assert result["input_audio"]["data"] == "base64audiodata"
    assert result["input_audio"]["format"] == "wav"


@pytest.mark.ai
def test_convert_audio_part__preserves_all_audio_fields__correctly() -> None:
    """
    Purpose: Ensure all audio metadata fields are preserved during conversion.
    Why this matters: Audio processing requires complete metadata.
    Setup summary: Create audio with multiple fields, convert, verify all present.
    """
    # Arrange
    part = cast(
        ChatCompletionContentPartInputAudioParam,
        {
            "type": "input_audio",
            "input_audio": {
                "data": "base64data",
                "format": "mp3",
            },
        },
    )

    # Act
    result = _convert_audio_part_to_responses_api(part)

    # Assert
    assert result["input_audio"]["data"] == "base64data"
    assert result["input_audio"]["format"] == "mp3"


# ============================================================================
# Tests for convert_user_message_content_to_responses_api (main function)
# ============================================================================


@pytest.mark.ai
def test_convert_content__returns_string_unchanged__with_string_input() -> None:
    """
    Purpose: Verify string content is passed through without modification.
    Why this matters: Simple text messages are most common and must be efficient.
    Setup summary: Pass string, verify identical return.
    """
    # Arrange
    content = "Hello, this is a simple message."

    # Act
    result = convert_user_message_content_to_responses_api(content)

    # Assert
    assert result == "Hello, this is a simple message."
    assert isinstance(result, str)


@pytest.mark.ai
def test_convert_content__converts_text_part__in_list() -> None:
    """
    Purpose: Verify single text content part in list is converted correctly.
    Why this matters: List format is used for multimodal content.
    Setup summary: Create list with text part, convert, verify structure.
    """
    # Arrange
    content = [{"type": "text", "text": "Hello"}]

    # Act
    result = convert_user_message_content_to_responses_api(content)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["type"] == "input_text"
    assert result[0]["text"] == "Hello"


@pytest.mark.ai
def test_convert_content__converts_image_part__in_list() -> None:
    """
    Purpose: Verify image content part in list is converted with correct format.
    Why this matters: Image inputs must maintain URL and detail information.
    Setup summary: Create list with image part, convert, verify fields.
    """
    # Arrange
    content = [
        {
            "type": "image_url",
            "image_url": {"url": "https://example.com/pic.jpg", "detail": "low"},
        }
    ]

    # Act
    result = convert_user_message_content_to_responses_api(content)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["type"] == "input_image"
    assert result[0].get("image_url") == "https://example.com/pic.jpg"
    assert result[0].get("detail") == "low"


@pytest.mark.ai
def test_convert_content__handles_mixed_content__correctly() -> None:
    """
    Purpose: Verify multiple content types in one message are all converted.
    Why this matters: Multimodal messages combine text, images, files, etc.
    Setup summary: Create list with text and image, convert, verify both.
    """
    # Arrange
    content = [
        {"type": "text", "text": "Check this image:"},
        {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}},
    ]

    # Act
    result = convert_user_message_content_to_responses_api(content)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["type"] == "input_text"
    assert result[0]["text"] == "Check this image:"
    assert result[1]["type"] == "input_image"
    assert result[1].get("image_url") == "https://example.com/img.png"


@pytest.mark.ai
def test_convert_content__handles_all_content_types__in_one_message() -> None:
    """
    Purpose: Verify conversion handles all supported content types together.
    Why this matters: Complex messages may include all modalities simultaneously.
    Setup summary: Create list with text, image, file, and audio, verify all convert.
    """
    # Arrange
    content = [
        {"type": "text", "text": "Multi-modal message"},
        {"type": "image_url", "image_url": {"url": "https://example.com/img.jpg"}},
        {"type": "file", "file": {"file_id": "file-789"}},
        {"type": "input_audio", "input_audio": {"data": "audiodata", "format": "wav"}},
    ]

    # Act
    result = convert_user_message_content_to_responses_api(content)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 4
    assert result[0]["type"] == "input_text"
    assert result[1]["type"] == "input_image"
    assert result[2]["type"] == "input_file"
    assert result[3]["type"] == "input_audio"


@pytest.mark.ai
def test_convert_content__handles_camel_case_input__correctly() -> None:
    """
    Purpose: Verify camelCase argument keys are properly parsed and converted.
    Why this matters: API may receive camelCase from JavaScript clients.
    Setup summary: Use camelCase keys, verify conversion works.
    """
    # Arrange
    content = [
        {"type": "image_url", "imageUrl": {"url": "https://example.com/test.png"}}
    ]

    # Act
    result = convert_user_message_content_to_responses_api(content)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["type"] == "input_image"
    assert result[0].get("image_url") == "https://example.com/test.png"


@pytest.mark.ai
def test_convert_content__handles_empty_list__correctly() -> None:
    """
    Purpose: Verify empty content list returns empty result list.
    Why this matters: Edge case must not cause errors in processing pipeline.
    Setup summary: Pass empty list, verify empty list returned.
    """
    # Arrange
    content: list[dict[str, Any]] = []

    # Act
    result = convert_user_message_content_to_responses_api(content)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.ai
def test_convert_content__preserves_order__with_multiple_parts() -> None:
    """
    Purpose: Verify content parts maintain their original order after conversion.
    Why this matters: Message semantics depend on content part ordering.
    Setup summary: Create ordered list of parts, verify order preserved.
    """
    # Arrange
    content = [
        {"type": "text", "text": "First"},
        {"type": "text", "text": "Second"},
        {"type": "text", "text": "Third"},
    ]

    # Act
    result = convert_user_message_content_to_responses_api(content)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 3
    # All parts should be input_text type, so we can safely access text field
    assert result[0]["type"] == "input_text"
    assert result[0]["text"] == "First"
    assert result[1]["type"] == "input_text"
    assert result[1]["text"] == "Second"
    assert result[2]["type"] == "input_text"
    assert result[2]["text"] == "Third"
