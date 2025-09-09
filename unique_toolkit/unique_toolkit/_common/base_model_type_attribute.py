"""
The following can be used to define a pydantic BaseModel that has has
an attribute of type Pydantic BaseModel.

This is useful for:
- Tooldefinition for large language models (LLMs) with flexible parameters.
- General Endpoint defintions from configuration
"""

import json
from enum import StrEnum
from typing import Annotated, Any, TypeVar, Union, get_args, get_origin

from jambo import SchemaConverter
from jambo.types.json_schema_type import JSONSchema
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    create_model,
)


def _get_actual_type(python_type: type) -> type | None | Any:
    if get_origin(python_type) is not None:
        origin = get_origin(python_type)
        args = get_args(python_type)

        if origin is Annotated:
            # For Annotated types, the first argument is the actual type
            if args:
                actual_type = args[0]
                # Recursively handle nested generic types (e.g., Annotated[Optional[str], ...])
                if get_origin(actual_type) is not None:
                    return _get_actual_type(actual_type)
            else:
                raise ValueError(f"Invalid Annotated type: {python_type}")
        elif origin is Union:
            # For Union types (including Optional), use the first non-None type
            if args:
                for arg in args:
                    if arg is not type(None):  # Skip NoneType
                        return _get_actual_type(arg)
                raise ValueError(f"Union type contains only None: {python_type}")
            else:
                raise ValueError(f"Invalid Union type: {python_type}")
        else:
            # Other generic types, use the origin
            actual_type = origin
    else:
        # Regular type
        actual_type = python_type

    return actual_type


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
        type_to_check = _get_actual_type(python_type)

        # Ensure we have a class before calling issubclass
        if not isinstance(type_to_check, type):
            raise ValueError(f"Invalid Python type: {python_type}")

        # Check bool first since bool is a subclass of int in Python
        if issubclass(type_to_check, bool):
            return cls.BOOLEAN
        if issubclass(type_to_check, int):
            return cls.INTEGER
        if issubclass(type_to_check, float):
            return cls.NUMBER
        if issubclass(type_to_check, str):
            return cls.STRING
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
            parameter.type.to_python_type(),
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
                required=field_info.is_required(),
            )
        )
    return parameter


# Create the annotated type that ensures BaseModel and generates clean JSON schema

TModel = TypeVar("TModel", bound=BaseModel)


class BaseModelTypeTitle(StrEnum):
    LIST_OF_PARAMETERS = "List of Parameters"
    JSON_SCHEMA_AS_STRING = "JSON Schema as String"
    USE_MODEL_FROM_CODE = "Use Model from Code"


ListOfParameters = Annotated[
    list[Parameter], Field(title=BaseModelTypeTitle.LIST_OF_PARAMETERS.value)
]
JSONSchemaString = Annotated[
    str, Field(title=BaseModelTypeTitle.JSON_SCHEMA_AS_STRING.value)
]
CodefinedModelType = Annotated[
    None, Field(title=BaseModelTypeTitle.USE_MODEL_FROM_CODE.value)
]


BaseModelType = Annotated[
    type[TModel],
    BeforeValidator(
        convert_to_base_model_type,
        json_schema_input_type=ListOfParameters | JSONSchemaString | CodefinedModelType,
    ),
]


def get_json_schema_extra_for_base_model_type(model: type[BaseModel]):
    """
    Returns a json_schema_extra mutator that injects defaults
    into both the 'string' and 'list[Parameter]' branches.

    This is used to define default for the "oneOf"/"anyOf" validation
    of the parameters attribute.
    """
    sample_params = base_model_to_parameter_list(model)

    def _mutate(schema: dict) -> None:
        json_default = json.dumps(model.model_json_schema())
        params_default = [p.model_dump() for p in sample_params]

        for key in ("oneOf", "anyOf"):
            if key in schema:
                for entry in schema[key]:
                    if (
                        entry.get("type") == "string"
                        and entry.get("title")
                        == BaseModelTypeTitle.JSON_SCHEMA_AS_STRING.value
                    ):
                        entry["default"] = json_default
                    if (
                        entry.get("type") == "array"
                        and entry.get("title")
                        == BaseModelTypeTitle.LIST_OF_PARAMETERS.value
                    ):
                        entry["default"] = params_default

    return _mutate


if __name__ == "__main__":
    import json
    from pathlib import Path
    from typing import Generic

    from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
    from openai.types.shared_params.function_definition import FunctionDefinition
    from pydantic import BaseModel, Field, field_serializer

    class ToolDescription(BaseModel, Generic[TModel]):
        name: str = Field(
            ...,
            pattern=r"^[a-zA-Z1-9_-]+$",
            description="Name must adhere to the pattern ^[a-zA-Z1-9_-]+$",
        )
        description: str = Field(
            ...,
            description="Description of what the tool is doing the tool",
        )

        strict: bool = Field(
            default=False,
            description="Setting strict to true will ensure function calls reliably adhere to the function schema, instead of being best effort.",
        )

        parameters: BaseModelType[TModel] = Field(
            ...,
            description="Json Schema for the tool parameters. Must be valid JSON Schema and able to convert to a Pydantic model",
        )

        @field_serializer("parameters")
        def serialize_parameters(self, parameters: type[BaseModel]):
            return parameters.model_json_schema()

        @overload
        def to_openai(
            self, mode: Literal["completions"]
        ) -> ChatCompletionToolParam: ...

        @overload
        def to_openai(self, mode: Literal["responses"]) -> FunctionToolParam: ...

        def to_openai(
            self, mode: Literal["completions", "responses"] = "completions"
        ) -> ChatCompletionToolParam | FunctionToolParam:
            if mode == "completions":
                return ChatCompletionToolParam(
                    function=FunctionDefinition(
                        name=self.name,
                        description=self.description,
                        parameters=self.parameters.model_json_schema(),
                        strict=self.strict,
                    ),
                    type="function",
                )
            elif mode == "responses":
                return FunctionToolParam(
                    type="function",
                    name=self.name,
                    parameters=self.parameters.model_json_schema(),
                    strict=self.strict,
                    description=self.description,
                )

    class WeatherToolParameterModel(BaseModel):
        lon: float = Field(
            ..., description="The longitude of the location to get the weather for"
        )
        lat: float = Field(
            ..., description="The latitude of the location to get the weather for"
        )
        name: str = Field(
            ..., description="The name of the location to get the weather for"
        )

    class GetWeatherTool(ToolDescription[WeatherToolParameterModel]):
        parameters: BaseModelType[WeatherToolParameterModel] = Field(
            default=WeatherToolParameterModel,
            json_schema_extra=get_json_schema_extra_for_base_model_type(
                WeatherToolParameterModel
            ),
        )

    # The json schema can be used in the RSJF library to create a valid frontend component.
    # You can test it on https://rjsf-team.github.io/react-jsonschema-form/
    file = Path(__file__).parent / "weather_tool_schema.json"
    with file.open("w") as f:
        f.write(json.dumps(GetWeatherTool.model_json_schema(), indent=2))

    # Notice that the t.parameters is a pydantic model with type annotations
    t = GetWeatherTool(
        name="GetWeather", description="Get the weather for a given location"
    )
    t.parameters(lon=100, lat=100, name="Test")
    print(t.model_dump())
