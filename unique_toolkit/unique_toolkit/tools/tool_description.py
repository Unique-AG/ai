from datetime import datetime
from enum import StrEnum
from typing import Any, TypeVar

from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition
from pydantic import BaseModel, Field, create_model, field_serializer

T = TypeVar("T", bound=BaseModel)


class BaseToolDescription(BaseModel):
    name: str = Field(
        ...,
        pattern=r"^[a-zA-Z1-9_-]+$",
        description="Name must adhere to the pattern ^[a-zA-Z1-9_-]+$",
    )
    description: str = Field(
        ...,
        description="Description of what the tool is doing the tool",
    )

    # TODO: This should be default `True` but if this is the case
    # the parameter_model needs to include additional properties
    strict: bool = Field(
        default=False,
        description="Setting strict to true will ensure function calls reliably adhere "
        "to the function schema, instead of being best effort. If set to True the `parameter_model` "
        "set `model_config = {'extra':'forbid'}` must be set for on all BaseModels.",
    )


class ElementaryType(StrEnum):
    TEXT = "text"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"


def elementary_type_to_python(elementary_type: ElementaryType) -> type:
    match elementary_type:
        case ElementaryType.TEXT:
            return str
        case ElementaryType.NUMBER:
            return float
        case ElementaryType.INTEGER:
            return int
        case ElementaryType.BOOLEAN:
            return bool
        case ElementaryType.DATE:
            return datetime
        case ElementaryType.DATETIME:
            return datetime
        case _:
            raise ValueError(f"Invalid elementary type: {elementary_type}")


class ParameterDescription(BaseModel):
    model_config = {"frozen": True}

    name: str = Field(
        ...,
        description="Name of the parameter",
    )
    type: ElementaryType = Field(
        ...,
        description="Type of the parameter",
    )
    description: str = Field(
        ...,
        description="Description of the parameter",
    )


class FrontendToolDescription(BaseToolDescription):
    parameter_description: list[ParameterDescription] = Field(
        ...,
        description="A list of parameter descriptions",
    )


def build_base_model_from_parameter_description(
    parameter_description: list[ParameterDescription],
) -> type[BaseModel]:
    fields = {}
    for param in parameter_description:
        python_type = elementary_type_to_python(param.type)
        fields[param.name] = (python_type, Field(..., description=param.description))

    return create_model("DynamicParameters", **fields)


class LLMToolDescription(BaseToolDescription):
    parameters: type[BaseModel] = Field(
        ...,
        description="Pydantic model for the tool parameters or "
        "a dictionary that is a json schema",
    )

    @field_serializer("parameters")
    def serialize_parameters(self, parameters: T) -> dict[str, Any]:
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

    @classmethod
    def from_frontend_tool_description(
        cls, frontend_tool_description: FrontendToolDescription
    ) -> "LLMToolDescription":
        return cls(
            name=frontend_tool_description.name,
            description=frontend_tool_description.description,
            parameters=build_base_model_from_parameter_description(
                frontend_tool_description.parameter_description
            ),
        )


if __name__ == "__main__":
    import json
    from pathlib import Path

    # This is the schema of the frontend tool description
    with open(Path(__file__).parent / "frontend_tool_schema.json", "w") as f:
        json.dump(FrontendToolDescription.model_json_schema(), f, indent=4)

    # This is the instance of the frontend tool description for the json we use as default to fill the form in the frontend
    frontend_tool_description = FrontendToolDescription(
        name="my_tool",
        description="My tool",
        parameter_description=[
            ParameterDescription(
                name="a", type=ElementaryType.INTEGER, description="A number"
            ),
            ParameterDescription(
                name="b", type=ElementaryType.INTEGER, description="A number"
            ),
        ],
    )

    with open(Path(__file__).parent / "frontend_tool_description.json", "w") as f:
        json.dump(frontend_tool_description.model_dump(), f, indent=4)

    # You can get a feel for the form here https://rjsf-team.github.io/react-jsonschema-form/
    # Passing the two json files we create above

    ## LLM Tool Description from Frontend Tool Description that allows to use the tool in a language model
    my_llm_tool_description = LLMToolDescription.from_frontend_tool_description(
        frontend_tool_description
    )

    my_llm_tool_description.to_openai()
