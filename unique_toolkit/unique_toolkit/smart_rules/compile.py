import warnings

from unique_toolkit.content.smart_rules import (
    AndStatement,
    BaseStatement,
    Operator,
    OrStatement,
    Statement,
    UniqueQL,
    array_operator,
    binary_operator,
    calculate_current_date,
    calculate_earlier_date,
    calculate_later_date,
    empty_operator,
    eval_nested_operator,
    eval_operator,
    get_fallback_values,
    is_array_of_strings,
    null_operator,
    parse_uniqueql,
    replace_tool_parameters_patterns,
    replace_user_metadata_patterns,
    replace_variables,
)

warnings.warn(
    "unique_toolkit.smart_rules.compile is deprecated. "
    "Please use unique_toolkit.content.smart_rules instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "AndStatement",
    "BaseStatement",
    "Operator",
    "OrStatement",
    "Statement",
    "UniqueQL",
    "array_operator",
    "binary_operator",
    "calculate_current_date",
    "calculate_earlier_date",
    "calculate_later_date",
    "empty_operator",
    "eval_nested_operator",
    "eval_operator",
    "get_fallback_values",
    "is_array_of_strings",
    "null_operator",
    "parse_uniqueql",
    "replace_tool_parameters_patterns",
    "replace_user_metadata_patterns",
    "replace_variables",
]
