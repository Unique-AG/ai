from typing import Any

from openai.types.chat import (
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartInputAudioParam,
    ChatCompletionContentPartParam,
    ChatCompletionContentPartTextParam,
)
from openai.types.chat.chat_completion_content_part_param import (
    File as ChatCompletionContentPartFileParam,
)
from openai.types.responses import (
    ResponseInputAudioParam,
    ResponseInputFileParam,
    ResponseInputImageParam,
    ResponseInputMessageContentListParam,
    ResponseInputTextParam,
)
from pydantic import (
    TypeAdapter,
)
from pydantic.alias_generators import to_camel


def _convert_text_part_to_responses_api(
    part: ChatCompletionContentPartTextParam,
) -> ResponseInputTextParam:
    return ResponseInputTextParam(type="input_text", text=part["text"])


def _convert_image_part_to_responses_api(
    part: ChatCompletionContentPartImageParam,
) -> ResponseInputImageParam:
    detail = "auto"  # Responses API requires detail to be sent
    if "detail" in part["image_url"]:
        detail = part["image_url"]["detail"]

    return ResponseInputImageParam(
        type="input_image",
        image_url=part["image_url"]["url"],
        detail=detail,
    )


def _convert_file_part_to_responses_api(
    part: ChatCompletionContentPartFileParam,
) -> ResponseInputFileParam:
    param = ResponseInputFileParam(type="input_file")

    if "file_id" in part["file"]:
        param["file_id"] = part["file"]["file_id"]

    if "file_data" in part["file"]:
        param["file_data"] = part["file"]["file_data"]

    if "filename" in part["file"]:
        param["filename"] = part["file"]["filename"]

    return param


def _convert_audio_part_to_responses_api(
    part: ChatCompletionContentPartInputAudioParam,
) -> ResponseInputAudioParam:
    return ResponseInputAudioParam(type="input_audio", input_audio=part["input_audio"])


def convert_user_message_content_to_responses_api(
    content: str | list[dict[str, Any]],
) -> str | ResponseInputMessageContentListParam:
    """Convert user message content from Chat Completions format to Responses API format."""

    if isinstance(content, str):
        return content

    # Parse the content of the dicts in order to allow for camelCase arguments
    content_parsed = TypeAdapter(
        list[ChatCompletionContentPartParam], config={"alias_generator": to_camel}
    ).validate_python(content, by_alias=True, by_name=True)

    responses_content: ResponseInputMessageContentListParam = []

    for part in content_parsed:
        match part["type"]:
            case "text":
                responses_content.append(_convert_text_part_to_responses_api(part))
            case "image_url":
                responses_content.append(_convert_image_part_to_responses_api(part))
            case "file":
                responses_content.append(_convert_file_part_to_responses_api(part))
            case "input_audio":
                responses_content.append(_convert_audio_part_to_responses_api(part))
    return responses_content
