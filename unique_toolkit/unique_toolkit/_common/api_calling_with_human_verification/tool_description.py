from typing import Generic

from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition
from pydantic import BaseModel, Field, field_serializer

from unique_toolkit._common.api_calling_with_human_verification.base_model_type_attribute import (
    BaseModelType,
    TModel,
    base_model_to_parameter_list,
    make_branch_defaults_for,
)

# Base Model for model using a pydantic model as attribute


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

    def to_openai(self) -> ChatCompletionToolParam:
        return ChatCompletionToolParam(
            function=FunctionDefinition(
                name=self.name,
                description=self.description,
                parameters=self.parameters.model_json_schema(),
                strict=self.strict,
            ),
            type="function",
        )


if __name__ == "__main__":
    import json
    from pathlib import Path

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

    example_parameters = base_model_to_parameter_list(WeatherToolParameterModel)

    class GetWeatherTool(ToolDescription[WeatherToolParameterModel]):
        parameters: BaseModelType[WeatherToolParameterModel] = Field(
            default=WeatherToolParameterModel,
            json_schema_extra=make_branch_defaults_for(
                WeatherToolParameterModel, example_parameters
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
