import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Self, Union

from pydantic import AliasChoices, BaseModel, Field
from pydantic.config import ConfigDict


class Operator(str, Enum):
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    IS_NULL = "IS_NULL"
    IS_NOT_NULL = "IS_NOT_NULL"
    IS_EMPTY = "IS_EMPTY"
    IS_NOT_EMPTY = "IS_NOT_EMPTY"
    NESTED = "NESTED"
    IN = "IN"
    NOT_IN = "NOT_IN"


class BaseStatement(BaseModel):
    model_config: ConfigDict = {"serialize_by_alias": True}

    def with_variables(
        self,
        user_metadata: Dict[str, Union[str, int, bool]],
        tool_parameters: Dict[str, Union[str, int, bool]],
    ) -> Self:
        return self._fill_in_variables(user_metadata, tool_parameters)

    def _fill_in_variables(
        self,
        user_metadata: Dict[str, Union[str, int, bool]],
        tool_parameters: Dict[str, Union[str, int, bool]],
    ) -> Self:
        return self.model_copy()


class Statement(BaseStatement):
    operator: Operator
    value: Union[str, int, bool, list[str], "AndStatement", "OrStatement"]
    path: List[str] = Field(default_factory=list)

    def _fill_in_variables(
        self,
        user_metadata: Dict[str, Union[str, int, bool]],
        tool_parameters: Dict[str, Union[str, int, bool]],
    ) -> Self:
        new_stmt = self.model_copy()
        new_stmt.value = eval_operator(self, user_metadata, tool_parameters)
        return new_stmt


class AndStatement(BaseStatement):
    and_list: List[Union["Statement", "AndStatement", "OrStatement"]] = Field(
        alias="and", validation_alias=AliasChoices("and", "and_list")
    )

    def _fill_in_variables(
        self,
        user_metadata: Dict[str, Union[str, int, bool]],
        tool_parameters: Dict[str, Union[str, int, bool]],
    ) -> Self:
        new_stmt = self.model_copy()
        new_stmt.and_list = [
            sub_query._fill_in_variables(user_metadata, tool_parameters)
            for sub_query in self.and_list
        ]
        return new_stmt


class OrStatement(BaseStatement):
    or_list: List[Union["Statement", "AndStatement", "OrStatement"]] = Field(
        alias="or", validation_alias=AliasChoices("or", "or_list")
    )

    def _fill_in_variables(
        self,
        user_metadata: Dict[str, Union[str, int, bool]],
        tool_parameters: Dict[str, Union[str, int, bool]],
    ) -> Self:
        new_stmt = self.model_copy()
        new_stmt.or_list = [
            sub_query._fill_in_variables(user_metadata, tool_parameters)
            for sub_query in self.or_list
        ]
        return new_stmt


# Update the forward references
Statement.model_rebuild()
AndStatement.model_rebuild()
OrStatement.model_rebuild()


UniqueQL = Union[Statement, AndStatement, OrStatement]


def is_array_of_strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def eval_operator(
    query: Statement,
    user_metadata: Dict[str, Union[str, int, bool]],
    tool_parameters: Dict[str, Union[str, int, bool]],
) -> Any:
    if query.operator in [
        Operator.EQUALS,
        Operator.NOT_EQUALS,
        Operator.GREATER_THAN,
        Operator.GREATER_THAN_OR_EQUAL,
        Operator.LESS_THAN,
        Operator.LESS_THAN_OR_EQUAL,
        Operator.CONTAINS,
        Operator.NOT_CONTAINS,
    ]:
        return binary_operator(query.value, user_metadata, tool_parameters)
    elif query.operator in [Operator.IS_NULL, Operator.IS_NOT_NULL]:
        return null_operator(query.value, user_metadata, tool_parameters)
    elif query.operator in [Operator.IS_EMPTY, Operator.IS_NOT_EMPTY]:
        return empty_operator(query.operator, user_metadata, tool_parameters)
    elif query.operator == Operator.NESTED:
        return eval_nested_operator(query.value, user_metadata, tool_parameters)
    elif query.operator in [Operator.IN, Operator.NOT_IN]:
        return array_operator(query.value, user_metadata, tool_parameters)
    else:
        raise ValueError(f"Operator {query.operator} not supported")


def eval_nested_operator(
    value: Any,
    user_metadata: Dict[str, Union[str, int, bool]],
    tool_parameters: Dict[str, Union[str, int, bool]],
) -> Union[AndStatement, OrStatement]:
    if not isinstance(value, (AndStatement, OrStatement)):
        raise ValueError("Nested operator must be an AndStatement or OrStatement")
    return value._fill_in_variables(user_metadata, tool_parameters)


def binary_operator(
    value: Any,
    user_metadata: Dict[str, Union[str, int, bool]],
    tool_parameters: Dict[str, Union[str, int, bool]],
) -> Any:
    return replace_variables(value, user_metadata, tool_parameters)


def array_operator(
    value: Any,
    user_metadata: Dict[str, Union[str, int, bool]],
    tool_parameters: Dict[str, Union[str, int, bool]],
) -> Any:
    if is_array_of_strings(value):
        return [
            replace_variables(item, user_metadata, tool_parameters) for item in value
        ]
    return value


def null_operator(
    value: Any,
    user_metadata: Dict[str, Union[str, int, bool]],
    tool_parameters: Dict[str, Union[str, int, bool]],
) -> Any:
    return value  # do nothing for now. No variables to replace


def empty_operator(
    operator: Operator,
    user_metadata: Dict[str, Union[str, int, bool]],
    tool_parameters: Dict[str, Union[str, int, bool]],
) -> Any:
    """Handle IS_EMPTY and IS_NOT_EMPTY operators."""
    if operator == Operator.IS_EMPTY:
        return ""
    elif operator == Operator.IS_NOT_EMPTY:
        return "not_empty"
    return None


def calculate_current_date() -> str:
    """Calculate current date in UTC with seconds precision."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def calculate_earlier_date(input_str: str) -> str:
    match = re.search(r"<T-(\d+)>", input_str)
    if not match:
        return calculate_current_date()  # Return current date if no match
    days = int(match.group(1))
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(
        timespec="seconds"
    )


def calculate_later_date(input_str: str) -> str:
    match = re.search(r"<T\+(\d+)>", input_str)  # Note: escaped + in regex
    if not match:
        return calculate_current_date()  # Return current date if no match
    days = int(match.group(1))
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(
        timespec="seconds"
    )


def replace_variables(
    value: Any,
    user_metadata: Dict[str, Union[str, int, bool]],
    tool_parameters: Dict[str, Union[str, int, bool]],
) -> Any:
    if isinstance(value, str):
        if "||" in value:
            return get_fallback_values(value, user_metadata, tool_parameters)
        elif value == "<T>":
            return calculate_current_date()
        elif "<T-" in value:
            return calculate_earlier_date(value)
        elif "<T+" in value:
            return calculate_later_date(value)

        value = replace_tool_parameters_patterns(value, tool_parameters)
        value = replace_user_metadata_patterns(value, user_metadata)

        if value == "":
            return value
        try:
            return int(value)
        except ValueError:
            if value.lower() in ["true", "false"]:
                return value.lower() == "true"
            return value
    return value


def replace_tool_parameters_patterns(
    value: str, tool_parameters: Dict[str, Union[str, int, bool]]
) -> str:
    def replace_match(match):
        param_name = match.group(1)
        return str(tool_parameters.get(param_name, ""))

    return re.sub(r"<toolParameters\.(\w+)>", replace_match, value)


def replace_user_metadata_patterns(
    value: str, user_metadata: Dict[str, Union[str, int, bool]]
) -> str:
    def replace_match(match):
        param_name = match.group(1)
        return str(user_metadata.get(param_name, ""))

    return re.sub(r"<userMetadata\.(\w+)>", replace_match, value)


def get_fallback_values(
    value: str,
    user_metadata: Dict[str, Union[str, int, bool]],
    tool_parameters: Dict[str, Union[str, int, bool]],
) -> Any:
    values = value.split("||")
    for val in values:
        data = replace_variables(val, user_metadata, tool_parameters)
        if data != "":
            return data
    return values


# Example usage:
def parse_uniqueql(json_data: Dict[str, Any]) -> UniqueQL:
    if "operator" in json_data:
        json_data["operator"] = json_data["operator"].upper()
        return Statement.parse_obj(json_data)
    elif "or" in json_data:
        return OrStatement.model_validate(
            {"or": [parse_uniqueql(item) for item in json_data["or"]]}
        )
    elif "and" in json_data:
        return AndStatement.model_validate(
            {"and": [parse_uniqueql(item) for item in json_data["and"]]}
        )
    else:
        raise ValueError("Invalid UniqueQL format")
