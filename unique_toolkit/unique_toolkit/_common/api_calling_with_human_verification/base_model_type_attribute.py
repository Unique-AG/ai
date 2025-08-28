"""
The following can be used to define a pydantic BaseModel that has has
an attribute of type Pydantic BaseModel.

This is useful for:
- Tooldefinition for large language models (LLMs) with flexible parameters.
- General Endpoint defintions from configuration
"""

import json
from enum import StrEnum
from typing import Annotated, TypeVar

from jambo import SchemaConverter
from jambo.types.json_schema_type import JSONSchema
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    create_model,
)


class ParameterType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"

    def to_python_type(self) -> type:
        """Convert ParameterType to Python type"""

        match self:
            case ParameterType.STRING:
                return str
            case ParameterType.INTEGER:
                return int
            case ParameterType.NUMBER:
                return float
            case ParameterType.BOOLEAN:
                return bool
            case _:
                raise ValueError(f"Invalid ParameterType: {self}")

    @classmethod
    def from_python_type(cls, python_type: type) -> "ParameterType":
        if issubclass(python_type, str):
            return cls.STRING
        if issubclass(python_type, int):
            return cls.INTEGER
        if issubclass(python_type, float):
            return cls.NUMBER
        if issubclass(python_type, bool):
            return cls.BOOLEAN
        raise ValueError(f"Invalid Python type: {python_type}")


class Parameter(BaseModel):
    type: ParameterType
    name: str
    description: str
    required: bool


def create_pydantic_model_from_parameter_list(
    title: str, parameter_list: list[Parameter]
) -> type[BaseModel]:
    """Create a Pydantic model from MCP tool's input schema"""

    # Convert JSON schema properties to Pydantic fields
    fields = {}
    for parameter in parameter_list:
        if parameter.required:
            field = Field(description=parameter.description)
        else:
            field = Field(default=None, description=parameter.description)

        fields[parameter.name] = (
            parameter.type.to_python_type,
            field,
        )

    return create_model(title, **fields)


def convert_to_base_model_type(
    value: type[BaseModel] | str | list[Parameter] | None,
) -> type[BaseModel]:
    """
    BeforeValidator that ensures the final type is always of type[BaseModel].

    If the input is already a BaseModel class, returns it as-is.
    If the input is a list of Parameter as defined above, converts it to a BaseModel class
    If the input is a str (JSON schema), converts it to a BaseModel class using SchemaConverter from Jambo.
    """
    if isinstance(value, type) and issubclass(value, BaseModel):
        return value

    if isinstance(value, list):
        if all(isinstance(item, Parameter) for item in value):
            return create_pydantic_model_from_parameter_list("Parameters", value)

    converter = SchemaConverter()
    if isinstance(value, str):
        return converter.build(JSONSchema(**json.loads(value)))

    raise ValueError(f"Invalid value: {value}")


def base_model_to_parameter_list(model: type[BaseModel]) -> list[Parameter]:
    parameter = []
    for field_name, field_info in model.model_fields.items():
        parameter.append(
            Parameter(
                type=ParameterType.from_python_type(field_info.annotation or str),
                name=field_name,
                description=field_info.description or "",
                required=not field_info.default is not None,
            )
        )
    return parameter


# Create the annotated type that ensures BaseModel and generates clean JSON schema

TModel = TypeVar("TModel", bound=BaseModel)
ListOfParameters = Annotated[list[Parameter], Field(title="List of Parameters")]
JSONSchemaString = Annotated[str, Field(title="JSON Schema as String")]
CodefinedModelType = Annotated[None, Field(title="Use Model from Code")]

BaseModelType = Annotated[
    type[TModel],
    BeforeValidator(
        convert_to_base_model_type,
        json_schema_input_type=ListOfParameters | JSONSchemaString | CodefinedModelType,
    ),
]


def make_branch_defaults_for(model: type[BaseModel], sample_params: list[Parameter]):
    """
    Returns a json_schema_extra mutator that injects defaults
    into both the 'string' and 'list[Parameter]' branches.

    This is used to define default for the "oneOf"/"anyOf" validation
    of the parameters attribute.
    """

    def _mutate(schema: dict) -> None:
        json_default = json.dumps(model.model_json_schema())
        params_default = [p.model_dump() for p in sample_params]

        for key in ("oneOf", "anyOf"):
            if key in schema:
                for entry in schema[key]:
                    if (
                        entry.get("type") == "string"
                        and entry.get("title") == "JSON Schema as string"
                    ):
                        entry["default"] = json_default
                    if entry.get("title") == "List of parameters":
                        entry["default"] = params_default

    return _mutate
