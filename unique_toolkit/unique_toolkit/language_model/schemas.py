import json
import math
from enum import StrEnum
from typing import Any, Self
from uuid import uuid4

from humps import camelize
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    RootModel,
    field_serializer,
    field_validator,
    model_serializer,
    model_validator,
)
from typing_extensions import deprecated

from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.utils import format_message

# set config to convert camelCase to snake_case
model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    arbitrary_types_allowed=True,
)


# Equivalent to
# from openai.types.chat.chat_completion_role import ChatCompletionRole
class LanguageModelMessageRole(StrEnum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"
    TOOL = "tool"


# This is tailored to the unique backend
class LanguageModelStreamResponseMessage(BaseModel):
    model_config = model_config

    id: str
    previous_message_id: (
        str | None
    )  # Stream response can return a null previous_message_id if an assisstant message is manually added
    role: LanguageModelMessageRole
    text: str
    original_text: str | None = None
    references: list[ContentReference] = []

    # TODO make sdk return role in lowercase
    # Currently needed as sdk returns role in uppercase
    @field_validator("role", mode="before")
    def set_role(cls, value: str):
        return value.lower()


class LanguageModelFunction(BaseModel):
    model_config = model_config

    id: str | None = None
    name: str
    arguments: dict[str, Any] | str | None = None  # type: ignore

    @field_validator("arguments", mode="before")
    def set_arguments(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value

    @field_validator("id", mode="before")
    def randomize_id(cls, value):
        return uuid4().hex

    @model_serializer()
    def serialize_model(self):
        seralization = {}
        if self.id:
            seralization["id"] = self.id
        seralization["name"] = self.name
        if self.arguments:
            seralization["arguments"] = json.dumps(self.arguments)
        return seralization

    def __eq__(self, other: Self) -> bool:
        """
        Compare two tool calls based on name and arguments.
        """
        if not isinstance(other, LanguageModelFunction):
            return False

        if self.id != other.id:
            return False

        if self.name != other.name:
            return False

        if self.arguments != other.arguments:
            return False

        return True


# This is tailored to the unique backend
class LanguageModelStreamResponse(BaseModel):
    model_config = model_config

    message: LanguageModelStreamResponseMessage
    tool_calls: list[LanguageModelFunction] | None = None


class LanguageModelFunctionCall(BaseModel):
    model_config = model_config

    id: str | None = None
    type: str | None = None
    function: LanguageModelFunction

    # TODO: Circular reference of types
    @deprecated("Use LanguageModelAssistantMessage.from_functions instead.")
    @staticmethod
    def create_assistant_message_from_tool_calls(
        tool_calls: list[LanguageModelFunction],
    ):
        assistant_message = LanguageModelAssistantMessage(
            content="",
            tool_calls=[
                LanguageModelFunctionCall(
                    id=tool_call.id,
                    type="function",
                    function=tool_call,
                )
                for tool_call in tool_calls
            ],
        )
        return assistant_message


class LanguageModelMessage(BaseModel):
    model_config = model_config
    role: LanguageModelMessageRole
    content: str | list[dict] | None = None

    def __str__(self):
        message = ""
        if isinstance(self.content, str):
            message = self.content
        elif isinstance(self.content, list):
            message = json.dumps(self.content)

        return format_message(self.role.capitalize(), message=message, num_tabs=1)


# Equivalent to
class LanguageModelSystemMessage(LanguageModelMessage):
    role: LanguageModelMessageRole = LanguageModelMessageRole.SYSTEM

    @field_validator("role", mode="before")
    def set_role(cls, value):
        return LanguageModelMessageRole.SYSTEM


# Equivalent to
# from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam


class LanguageModelUserMessage(LanguageModelMessage):
    role: LanguageModelMessageRole = LanguageModelMessageRole.USER

    @field_validator("role", mode="before")
    def set_role(cls, value):
        return LanguageModelMessageRole.USER


# Equivalent to
# from openai.types.chat.chat_completion_assistant_message_param import ChatCompletionAssistantMessageParam
class LanguageModelAssistantMessage(LanguageModelMessage):
    role: LanguageModelMessageRole = LanguageModelMessageRole.ASSISTANT
    parsed: dict | None = None
    refusal: str | None = None
    tool_calls: list[LanguageModelFunctionCall] | None = None

    @field_validator("role", mode="before")
    def set_role(cls, value):
        return LanguageModelMessageRole.ASSISTANT

    @classmethod
    def from_functions(
        cls,
        tool_calls: list[LanguageModelFunction],
    ):
        return cls(
            content="",
            tool_calls=[
                LanguageModelFunctionCall(
                    id=tool_call.id,
                    type="function",
                    function=tool_call,
                )
                for tool_call in tool_calls
            ],
        )

    @classmethod
    def from_stream_response(cls, response: LanguageModelStreamResponse):
        tool_calls = [
            LanguageModelFunctionCall(
                id=None,
                type=None,
                function=f,
            )
            for f in response.tool_calls or []
        ]

        tool_calls = tool_calls if len(tool_calls) > 0 else None

        return cls(
            content=response.message.text,
            parsed=None,
            refusal=None,
            tool_calls=tool_calls,
        )


# Equivalent to
# from openai.types.chat.chat_completion_tool_message_param import ChatCompletionToolMessageParam


class LanguageModelToolMessage(LanguageModelMessage):
    role: LanguageModelMessageRole = LanguageModelMessageRole.TOOL
    name: str
    tool_call_id: str

    def __str__(self):
        return format_message(
            user=self.role.capitalize(),
            message=f"{self.name}, {self.tool_call_id}, {self.content}",
            num_tabs=1,
        )

    @field_validator("role", mode="before")
    def set_role(cls, value):
        return LanguageModelMessageRole.TOOL


# Equivalent implementation for list of
# from openai.types.chat.chat_completion_tool_message_param import ChatCompletionToolMessageParam
# with the addition of the builder


class LanguageModelMessages(RootModel):
    root: list[
        LanguageModelMessage
        | LanguageModelToolMessage
        | LanguageModelAssistantMessage
        | LanguageModelSystemMessage
        | LanguageModelUserMessage
    ]

    @classmethod
    def load_messages_to_root(cls, data: list[dict] | dict) -> Self:
        """Convert list of dictionaries to appropriate message objects based on role."""
        # Handle case where data is already wrapped in root
        if isinstance(data, dict) and "root" in data:
            messages_list = data["root"]
        elif isinstance(data, list):
            messages_list = data
        else:
            raise ValueError("Invalid data type")

        # Convert the messages list
        converted_messages = []
        for item in messages_list:
            if isinstance(item, dict):
                role = item.get("role", "").lower()

                # Map dictionary to appropriate message class based on role
                if role == "system":
                    converted_messages.append(LanguageModelSystemMessage(**item))
                elif role == "user":
                    converted_messages.append(LanguageModelUserMessage(**item))
                elif role == "assistant":
                    converted_messages.append(LanguageModelAssistantMessage(**item))
                elif role == "tool":
                    converted_messages.append(LanguageModelToolMessage(**item))
                else:
                    # Fallback to base LanguageModelMessage
                    converted_messages.append(LanguageModelMessage(**item))
            else:
                # If it's already a message object, keep it as is
                converted_messages.append(item)
        return cls(root=converted_messages)

    def __str__(self):
        return "\n\n".join([str(message) for message in self.root])

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def builder(self):
        """Returns a MessagesBuilder instance pre-populated with existing messages."""
        from unique_toolkit.language_model.builder import MessagesBuilder

        builder = MessagesBuilder()
        builder.messages = self.root.copy()  # Start with existing messages
        return builder


# This seems similar to
# from openai.types.completion_choice import CompletionChoice
# but is missing multiple attributes and uses message instead of text


class LanguageModelCompletionChoice(BaseModel):
    model_config = model_config

    index: int
    message: LanguageModelAssistantMessage
    finish_reason: str


# This seems similar to
# from openai.types.completion import Completion
# but is missing multiple attributes
class LanguageModelResponse(BaseModel):
    model_config = model_config

    choices: list[LanguageModelCompletionChoice]

    @classmethod
    def from_stream_response(cls, response: LanguageModelStreamResponse):
        choice = LanguageModelCompletionChoice(
            index=0,
            message=LanguageModelAssistantMessage.from_stream_response(response),
            finish_reason="",
        )

        return cls(choices=[choice])


# This is tailored for unique and only used in language model info
class LanguageModelTokenLimits(BaseModel):
    token_limit_input: int
    token_limit_output: int

    _fraction_adaptable = PrivateAttr(default=False)

    @property
    @deprecated("""
    Deprecated: Use the more specific `token_limit_input` and `token_limit_output` instead.
    """)
    def token_limit(self):
        return self.token_limit_input + self.token_limit_output

    @token_limit.setter
    @deprecated("""
    Deprecated: Token limit can only be reduced
    """)
    def token_limit(self, token_limit, fraction_input=0.4):
        if self.token_limit > token_limit:
            self.token_limit_input = math.floor(fraction_input * token_limit)
            self.token_limit_output = math.floor((1 - fraction_input) * token_limit)
            self._fraction_adaptable = True

    def adapt_fraction(self, fraction_input: float):
        if self._fraction_adaptable:
            token_limit = self.token_limit_input + self.token_limit_output
            self.token_limit_input = math.floor(fraction_input * token_limit)
            self.token_limit_output = math.floor((1 - fraction_input) * token_limit)

    @model_validator(mode="before")
    def check_required_fields(cls, data):
        if isinstance(data, dict):
            if {"token_limit_input", "token_limit_output"}.issubset(data.keys()):
                return data

            if {"token_limit"}.issubset(data.keys()):
                token_limit = data.get("token_limit")
                fraction_input = data.get("fraction_input", 0.4)

                data["token_limit_input"] = math.floor(fraction_input * token_limit)
                data["token_limit_output"] = math.floor(
                    (1 - fraction_input) * token_limit,
                )
                data["_fraction_adaptpable"] = True
            return data

        raise ValueError(
            'Either "token_limit_input" and "token_limit_output" must be provided together, or "token_limit" must be provided.',
        )


# This is more restrictive than what openai allows


@deprecated(
    "Deprecated as `LanguageModelTool` is deprecated in favor of `LanguageModelToolDescription`",
)
class LanguageModelToolParameterProperty(BaseModel):
    type: str
    description: str
    enum: list[Any] | None = None
    items: Self | None = None


# Looks most like
# from openai.types.shared.function_parameters import FunctionParameters
@deprecated(
    "Deprecated as `LanguageModelTool` is deprecated in favor of `LanguageModelToolDescription`",
)
class LanguageModelToolParameters(BaseModel):
    type: str = "object"
    properties: dict[str, LanguageModelToolParameterProperty]
    required: list[str]


# Looks most like
# from openai.types.shared_params.function_definition import FunctionDefinition
# but returns parameter is not known
@deprecated(
    "Deprecated as `LanguageModelTool` use `LanguageModelToolDescription` instead",
)
class LanguageModelTool(BaseModel):
    name: str = Field(
        ...,
        pattern=r"^[a-zA-Z1-9_-]+$",
        description="Name must adhere to the pattern ^[a-zA-Z_-]+$",
    )
    description: str
    parameters: (
        LanguageModelToolParameters | dict[str, Any]
    )  # dict represents json schema dumped from pydantic
    returns: LanguageModelToolParameterProperty | LanguageModelToolParameters | None = (
        None
    )


class LanguageModelToolDescription(BaseModel):
    name: str = Field(
        ...,
        pattern=r"^[a-zA-Z1-9_-]+$",
        description="Name must adhere to the pattern ^[a-zA-Z1-9_-]+$",
    )
    description: str = Field(
        ...,
        description="Description of what the tool is doing the tool",
    )
    parameters: type[BaseModel] = Field(
        ...,
        description="Pydantic model for the tool parameters",
    )

    # TODO: This should be default `True` but if this is the case the parameter_model needs to include additional properties
    strict: bool = Field(
        default=False,
        description="Setting strict to true will ensure function calls reliably adhere to the function schema, instead of being best effort. If set to True the `parameter_model` set `model_config = {'extra':'forbid'}` must be set for on all BaseModels.",
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
