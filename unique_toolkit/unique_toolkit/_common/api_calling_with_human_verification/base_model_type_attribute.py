# %%

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Generic, TypeVar

from jambo import SchemaConverter
from jambo.types.json_schema_type import JSONSchema
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    create_model,
    field_serializer,
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
    If the input is a dict (JSON schema), converts it to a BaseModel class using SchemaConverter.
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


# Create the annotated type that ensures BaseModel and generates clean JSON schema

TModel = TypeVar("TModel", bound=BaseModel)
ListOfParameters = Annotated[list[Parameter], Field(title="List of parameters")]
JSONSchemaString = Annotated[str, Field(title="JSON Schema as string")]
StandardModelType = Annotated[None, Field(title="Standard Model")]

BaseModelType = Annotated[
    type[TModel],
    BeforeValidator(
        convert_to_base_model_type,
        json_schema_input_type=ListOfParameters | JSONSchemaString | StandardModelType,
    ),
]


def make_branch_defaults_for(model: type[BaseModel], sample_params: list[Parameter]):
    """
    Returns a json_schema_extra mutator that injects defaults
    into both the 'string' and 'list[Parameter]' branches.
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


def to_parameter_list(model: type[BaseModel]) -> list[Parameter]:
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


# %%


# Base Model for model using a pydantic model as attribute
class LanguageModelToolDescription(BaseModel, Generic[TModel]):
    parameters: BaseModelType[TModel] = Field(
        ...,
        description="Json Schema for the tool parameters. Must be valid JSON Schema and able to convert to a Pydantic model",
    )

    @field_serializer("parameters")
    def serialize_parameters(self, parameters: type[BaseModel]):
        return parameters.model_json_schema()


# %%
class StandardModel(BaseModel):
    a: int = Field(..., description="Test")
    b: str = Field(..., description="Test")


example_parameters = to_parameter_list(StandardModel)


class MyTool(LanguageModelToolDescription[StandardModel]):
    parameters: BaseModelType[StandardModel] = Field(
        default=StandardModel,
        json_schema_extra=make_branch_defaults_for(StandardModel, example_parameters),
    )


# %%

file = Path(__file__).parent / "test_file.json"
with file.open("w") as f:
    f.write(json.dumps(MyTool.model_json_schema(), indent=2))


# %%

t = MyTool()
t.parameters(a=1, b="Test")
t.model_dump()
# %%
