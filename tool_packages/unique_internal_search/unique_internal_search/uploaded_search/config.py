from unique_internal_search.config import InternalSearchConfig
from unique_internal_search.uploaded_search.prompts import (
    DEFAULT_LANGUAGE_PARAM_DESCRIPTION,
    DEFAULT_SEARCH_STRING_PARAM_DESCRIPTION,
    DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
    DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT,
)
from unique_internal_search.validators import get_string_field_with_pattern_validation


class UploadedSearchConfig(InternalSearchConfig):
    param_description_search_string: str = get_string_field_with_pattern_validation(
        DEFAULT_SEARCH_STRING_PARAM_DESCRIPTION,
        description="`search_string` parameter description.",
    )
    param_description_language: str = get_string_field_with_pattern_validation(
        DEFAULT_LANGUAGE_PARAM_DESCRIPTION,
        description="`language` parameter description.",
    )
    tool_description_for_system_prompt: str = get_string_field_with_pattern_validation(
        DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
        description="Tool description for the system prompt.",
    )
    tool_format_information_for_system_prompt: str = (
        get_string_field_with_pattern_validation(
            DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT,
            description="Tool format information for the system prompt.",
        )
    )
