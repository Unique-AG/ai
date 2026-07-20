from typing import Annotated

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_internal_search.config import InternalSearchConfig
from unique_internal_search.uploaded_search.prompts import (
    DEFAULT_LANGUAGE_PARAM_DESCRIPTION,
    DEFAULT_SEARCH_STRING_PARAM_DESCRIPTION,
    DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
    DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT,
)
from unique_internal_search.validators import get_string_field_with_pattern_validation


class UploadedSearchConfig(InternalSearchConfig):
    max_tokens_per_search_call: (
        Annotated[int, Field(ge=0)] | Annotated[None, Field(title="No Limit")]
    ) = Field(
        default=35_000,
        description="Hard upper bound on the token budget for a single search call's sources.",
    )
    param_description_search_string: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(DEFAULT_SEARCH_STRING_PARAM_DESCRIPTION.split("\n"))
        ),
    ] = get_string_field_with_pattern_validation(
        DEFAULT_SEARCH_STRING_PARAM_DESCRIPTION,
        description="`search_string` parameter description.",
    )
    param_description_language: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(DEFAULT_LANGUAGE_PARAM_DESCRIPTION.split("\n"))
        ),
    ] = get_string_field_with_pattern_validation(
        DEFAULT_LANGUAGE_PARAM_DESCRIPTION,
        description="`language` parameter description.",
    )
    tool_description_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(len(DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT.split("\n")) / 2)
        ),
    ] = get_string_field_with_pattern_validation(
        DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
        description="Tool description for the system prompt.",
    )
    tool_format_information_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(
                len(DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT.split("\n")) / 3
            )
        ),
    ] = get_string_field_with_pattern_validation(
        DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT,
        description="Tool format information for the system prompt.",
    )
    # This is a hack to ensure that the system reminder is enabled when the tool is forced,
    # as we cannot at the moment easily pass extra values to the tool constructor
    enable_tool_call_system_reminder: SkipJsonSchema[bool] = Field(
        default=True,
        description="Whether to attach the uploaded-search system reminder to tool responses.",
    )
