from typing import Annotated

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
            rows=int(len(DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT.split("\n"))/2)
        ),
    ] = get_string_field_with_pattern_validation(
        DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
        description="Tool description for the system prompt.",
    )
    tool_format_information_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(len(DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT.split("\n"))/3)
        ),
    ] = get_string_field_with_pattern_validation(
        DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT,
        description="Tool format information for the system prompt.",
    )
