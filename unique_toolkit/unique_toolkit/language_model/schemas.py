from __future__ import annotations

import json
import math
from collections.abc import Sequence
from enum import StrEnum
from typing import Any, Iterable, Literal, Self, TypeAlias, TypeVar, cast, override
from uuid import uuid4

from humps import camelize
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.chat.chat_completion_message_function_tool_call_param import (
    ChatCompletionMessageFunctionToolCallParam,
    Function,
)
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.responses import (
    EasyInputMessageParam,
    FunctionToolParam,
    ResponseCodeInterpreterToolCall,
    ResponseFunctionToolCallParam,
    ResponseInputItemParam,
    ResponseOutputItem,
    ResponseOutputMessage,
)
from openai.types.responses.response_input_param import FunctionCallOutput
from openai.types.responses.response_output_text import AnnotationContainerFileCitation
from openai.types.shared_params import ReasoningEffort as OpenAIReasoningEffort
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
from typing_extensions import deprecated, overload

from unique_toolkit.chat.schemas import ChatMessage
from unique_toolkit.language_model._responses_api_utils import (
    convert_user_message_content_to_responses_api,
)
from unique_toolkit.language_model.utils import format_message

# set config to convert camelCase to snake_case
model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    arbitrary_types_allowed=True,
)


class LanguageModelMessageRole(StrEnum):
    ASSISTANT = "assistant"
    SYSTEM = "system"
    USER = "user"
    TOOL = "tool"


# Backward compatibility alias — use ChatMessage directly.
# LanguageModelStreamResponseMessage was a toolkit-only subclass with stricter types
# (required id/content, non-null references). The backend DTOs (PublicMessageDto,
# PublicStreamResultDto) use a single message type, so this distinction was unnecessary.
# Note: id and content are now optional (str | None) instead of required (str). This is a
# deliberate contract relaxation — the backend always returns non-null values in stream
# responses, but callers that relied on the stricter types should add explicit null checks.
LanguageModelStreamResponseMessage = ChatMessage


class LanguageModelFunction(BaseModel):
    model_config = model_config

    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    arguments: dict[str, Any] | None = None

    @field_validator("arguments", mode="before")
    def set_arguments(cls, value: Any) -> Any:
        if isinstance(value, str):
            return json.loads(value)
        return value

    @field_validator("id", mode="before")
    def randomize_id(cls, value: Any) -> Any:
        if value is None or value == "":
            return uuid4().hex
        return value

    @model_serializer()
    def serialize_model(self):
        seralization = {}
        seralization["name"] = self.name
        if self.arguments:
            seralization["arguments"] = json.dumps(self.arguments)
        return seralization

    def __eq__(self, other: object) -> bool:
        """Compare two tool calls based on name and arguments."""
        if not isinstance(other, LanguageModelFunction):
            return False

        if self.id != other.id:
            return False

        if self.name != other.name:
            return False

        if self.arguments != other.arguments:
            return False

        return True

    @overload
    def to_openai_param(
        self, mode: Literal["completions"] = "completions"
    ) -> ChatCompletionMessageFunctionToolCallParam: ...

    @overload
    def to_openai_param(
        self, mode: Literal["responses"]
    ) -> ResponseFunctionToolCallParam: ...

    def to_openai_param(
        self, mode: Literal["completions", "responses"] = "completions"
    ) -> ChatCompletionMessageFunctionToolCallParam | ResponseFunctionToolCallParam:
        arguments = ""
        if isinstance(self.arguments, dict):
            arguments = json.dumps(self.arguments)
        elif isinstance(self.arguments, str):  # pyright: ignore[reportUnnecessaryIsInstance]
            arguments = self.arguments

        if mode == "completions":
            return ChatCompletionMessageFunctionToolCallParam(
                type="function",
                id=self.id or "unknown_id",
                function=Function(name=self.name, arguments=arguments),
            )
        elif mode == "responses":
            if self.id is None:  # pyright: ignore[reportUnnecessaryComparison]
                raise ValueError("Missing tool call id")

            return ResponseFunctionToolCallParam(
                type="function_call",
                call_id=self.id,
                name=self.name,
                arguments=arguments,
            )


def _variants(*names: str) -> list[str]:
    """Expand each snake_case candidate into its snake_case and camelCase spellings."""
    expanded: list[str] = []
    for name in names:
        expanded.append(name)
        camel = camelize(name)
        if camel != name:
            expanded.append(camel)
    return expanded


def _first_value(source: object, keys: Sequence[str]) -> object | None:
    """First non-`None` value found under any of `keys`; `source` is a dict or SDK object."""
    if source is None:
        return None
    for key in keys:
        value = (
            source.get(key) if isinstance(source, dict) else getattr(source, key, None)
        )
        if value is not None:
            return value
    return None


def _first_int(source: object, keys: Sequence[str]) -> int | None:
    value = _first_value(source, keys)
    if not isinstance(value, (int, float, str)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class LanguageModelTokenUsage(BaseModel):
    model_config = model_config

    completion_tokens: int | None = None
    prompt_tokens: int | None = None
    total_tokens: int | None = None
    reasoning_tokens: int | None = None  # subset of completion_tokens
    cached_tokens: int | None = None  # subset of prompt_tokens (cache read)
    cache_write_tokens: int | None = None  # separate cost line, not cached_tokens

    @model_validator(mode="before")
    @classmethod
    def _normalize_provider_usage(cls, data: Any) -> Any:
        """Map Chat/Responses/Anthropic/litellm usage shapes onto this model's fields.

        Only fills fields absent from the payload; never overwrites an explicit value
        or invents 0 for a field the provider didn't report. Accepts a raw gateway
        dict directly, or an SDK usage object (``CompletionUsage``/``ResponseUsage``)
        via its own ``model_dump()`` -- callers never need to convert it themselves.
        """
        dump = getattr(data, "model_dump", None)
        if dump is not None:
            data = dump()
        if not isinstance(data, dict):
            return data
        data = dict(data)

        def present(field: str) -> bool:
            return field in data or camelize(field) in data

        def fill(field: str, *sources: tuple[object, Sequence[str]]) -> None:
            if present(field):
                return
            for source, keys in sources:
                value = _first_int(source, keys)
                if value is not None:
                    data[field] = value
                    return

        fill("prompt_tokens", (data, _variants("input_tokens")))
        fill("completion_tokens", (data, _variants("output_tokens")))
        if not present("total_tokens"):
            prompt_tokens = _first_int(data, _variants("prompt_tokens", "input_tokens"))
            completion_tokens = _first_int(
                data, _variants("completion_tokens", "output_tokens")
            )
            if prompt_tokens is not None and completion_tokens is not None:
                data["total_tokens"] = prompt_tokens + completion_tokens

        prompt_details = _first_value(
            data, _variants("prompt_tokens_details", "input_tokens_details")
        )
        completion_details = _first_value(
            data, _variants("completion_tokens_details", "output_tokens_details")
        )

        fill("reasoning_tokens", (completion_details, _variants("reasoning_tokens")))
        fill(
            "cached_tokens",
            (prompt_details, _variants("cached_tokens")),
            # Anthropic (via litellm) also reports this top-level, unnested.
            (data, _variants("cache_read_input_tokens")),
        )
        fill(
            "cache_write_tokens",
            (
                prompt_details,
                # cache_creation_tokens is Anthropic's name for the same concept.
                _variants("cache_write_tokens", "cache_creation_tokens"),
            ),
            (data, _variants("cache_creation_input_tokens")),
        )

        return data

    @classmethod
    def sum_usages(
        cls, usages: Iterable[LanguageModelTokenUsage | None]
    ) -> LanguageModelTokenUsage | None:
        """Sum usages, skipping `None` entries; returns `None` if none are present.

        Per field: if no entry reported it, the sum stays `None` too -- otherwise a
        field no provider ever reports (e.g. cache_write_tokens) would sum to a
        misleading `0` ("confirmed zero") instead of "unknown".
        """
        present = [u for u in usages if u is not None]
        if not present:
            return None

        def sum_field(attr: str) -> int | None:
            values = [getattr(u, attr) for u in present]
            if all(v is None for v in values):
                return None
            return sum(v or 0 for v in values)

        fields = (
            "completion_tokens",
            "prompt_tokens",
            "total_tokens",
            "reasoning_tokens",
            "cached_tokens",
            "cache_write_tokens",
        )
        return cls(**{field: sum_field(field) for field in fields})


class LanguageModelStreamResponse(BaseModel):
    model_config = model_config

    message: ChatMessage
    tool_calls: list[LanguageModelFunction] | None = None
    stopped_by_user: bool = False
    usage: LanguageModelTokenUsage | None = None

    def is_empty(self) -> bool:
        """
        Check if the stream response is empty.
        An empty stream response has no text and no tool calls.
        """
        return not self.message.original_text and not self.tool_calls

    def to_openai_param(self) -> ChatCompletionAssistantMessageParam:
        return ChatCompletionAssistantMessageParam(
            role="assistant",
            audio=None,
            content=self.message.text,
            function_call=None,
            refusal=None,
            tool_calls=[t.to_openai_param() for t in self.tool_calls or []],
        )


OutputItemType = TypeVar("OutputItemType", bound=ResponseOutputItem)


class ResponsesLanguageModelStreamResponse(LanguageModelStreamResponse):
    output: list[ResponseOutputItem]

    def filter_output(self, type: type[OutputItemType]) -> list[OutputItemType]:
        return [item for item in self.output if isinstance(item, type)]

    @property
    def code_interpreter_calls(self) -> list[ResponseCodeInterpreterToolCall]:
        return self.filter_output(ResponseCodeInterpreterToolCall)

    @property
    def container_files(self) -> list[AnnotationContainerFileCitation]:
        container_files = []
        messages = self.filter_output(ResponseOutputMessage)
        for message in messages:
            for content in message.content:
                if content.type == "output_text":
                    for annotation in content.annotations:
                        if annotation.type == "container_file_citation":
                            # Filter out ghost annotations produced as a side-effect of
                            # OutputImage being present. These entries have
                            # start_index == end_index (zero-width, no text span) and
                            # filename == file_id. The index check alone is sufficient
                            # because all legitimate citations reference an actual span
                            # of text (start_index < end_index).
                            if annotation.start_index != annotation.end_index:
                                container_files.append(annotation)
        return container_files


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
    ) -> "LanguageModelAssistantMessage":
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
    content: str | list[dict[str, Any]] | None = None

    def __str__(self):
        message = ""
        if isinstance(self.content, str):
            message = self.content
        elif isinstance(self.content, list):
            message = json.dumps(self.content)

        return format_message(self.role.capitalize(), message=message, num_tabs=1)

    @overload
    def to_openai(
        self, mode: Literal["completions"] = "completions"
    ) -> ChatCompletionMessageParam: ...

    @overload
    def to_openai(self, mode: Literal["responses"]) -> ResponseInputItemParam: ...

    def to_openai(
        self, mode: Literal["completions", "responses"] = "completions"
    ) -> ChatCompletionMessageParam | ResponseInputItemParam:
        raise NotImplementedError(
            "Subclasses must implement this. This class should not be used directly"
        )


class LanguageModelSystemMessage(LanguageModelMessage):
    role: LanguageModelMessageRole = LanguageModelMessageRole.SYSTEM

    @field_validator("role", mode="before")
    def set_role(cls, value):
        return LanguageModelMessageRole.SYSTEM

    @overload
    def to_openai(
        self, mode: Literal["completions"] = "completions"
    ) -> ChatCompletionSystemMessageParam: ...

    @overload
    def to_openai(self, mode: Literal["responses"]) -> EasyInputMessageParam: ...

    @override
    def to_openai(
        self, mode: Literal["completions", "responses"] = "completions"
    ) -> ChatCompletionSystemMessageParam | EasyInputMessageParam:
        content = self.content or ""
        if not isinstance(content, str):
            raise ValueError("Content must be a string")

        if mode == "completions":
            return ChatCompletionSystemMessageParam(role="system", content=content)
        elif mode == "responses":
            return EasyInputMessageParam(role="system", content=content)


# Equivalent to
# from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam
class LanguageModelUserMessage(LanguageModelMessage):
    role: LanguageModelMessageRole = LanguageModelMessageRole.USER

    @field_validator("role", mode="before")
    def set_role(cls, value):
        return LanguageModelMessageRole.USER

    @overload
    def to_openai(
        self, mode: Literal["completions"] = "completions"
    ) -> ChatCompletionUserMessageParam: ...

    @overload
    def to_openai(self, mode: Literal["responses"]) -> ResponseInputItemParam: ...

    @override
    def to_openai(
        self, mode: Literal["completions", "responses"] = "completions"
    ) -> ChatCompletionUserMessageParam | ResponseInputItemParam:
        if self.content is None:
            content = ""
        else:
            content = self.content

        if mode == "completions":
            return ChatCompletionUserMessageParam(role="user", content=content)  # pyright: ignore[reportArgumentType]
        elif mode == "responses":
            return EasyInputMessageParam(
                role="user",
                content=convert_user_message_content_to_responses_api(content),
            )


# Equivalent to
# from openai.types.chat.chat_completion_assistant_message_param import ChatCompletionAssistantMessageParam
class LanguageModelAssistantMessage(LanguageModelMessage):
    role: LanguageModelMessageRole = LanguageModelMessageRole.ASSISTANT
    parsed: dict[str, Any] | None = None
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
                id=f.id,
                type="function",
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

    @overload
    def to_openai(
        self, mode: Literal["completions"] = "completions"
    ) -> ChatCompletionAssistantMessageParam: ...

    @overload
    def to_openai(self, mode: Literal["responses"]) -> EasyInputMessageParam: ...

    @override
    def to_openai(
        self, mode: Literal["completions", "responses"] = "completions"
    ) -> ChatCompletionAssistantMessageParam | EasyInputMessageParam:
        content = self.content or ""
        if not isinstance(content, str):
            raise ValueError("Content must be a string")

        if mode == "completions":
            return ChatCompletionAssistantMessageParam(
                role="assistant",
                content=content,
                tool_calls=[
                    t.function.to_openai_param() for t in self.tool_calls or []
                ],
            )
        elif mode == "responses":
            """
            Responses API does not support assistant messages with tool calls
            """
            res = []
            if content != "":
                res.append(EasyInputMessageParam(role="assistant", content=content))
            if self.tool_calls:
                res.extend(
                    [
                        t.function.to_openai_param(mode="responses")
                        for t in self.tool_calls
                    ]
                )
            return res  # pyright: ignore[reportReturnType]


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

    @overload
    def to_openai(
        self, mode: Literal["completions"] = "completions"
    ) -> ChatCompletionToolMessageParam: ...

    @overload
    def to_openai(self, mode: Literal["responses"]) -> FunctionCallOutput: ...

    @override
    def to_openai(
        self, mode: Literal["completions", "responses"] = "completions"
    ) -> ChatCompletionToolMessageParam | FunctionCallOutput:
        content = self.content or ""
        if not isinstance(content, str):
            raise ValueError("Content must be a string")

        if mode == "completions":
            return ChatCompletionToolMessageParam(
                role="tool",
                content=content,
                tool_call_id=self.tool_call_id,
            )
        elif mode == "responses":
            return FunctionCallOutput(
                call_id=self.tool_call_id,
                output=content,
                type="function_call_output",
            )


# Equivalent implementation for list of
# from openai.types.chat.chat_completion_tool_message_param import ChatCompletionToolMessageParam
# with the addition of the builder

LanguageModelMessageOptions = (
    LanguageModelMessage  # TODO: Ideally we remove this
    | LanguageModelToolMessage
    | LanguageModelAssistantMessage
    | LanguageModelSystemMessage
    | LanguageModelUserMessage
)

LanguageModelMessageTypes = (
    LanguageModelAssistantMessage
    | LanguageModelUserMessage
    | LanguageModelSystemMessage
    | LanguageModelToolMessage
)


def _language_model_message_to_subtype(
    message: LanguageModelMessage,
) -> LanguageModelMessageTypes:
    """Narrow a plain ``LanguageModelMessage`` to the concrete subtype for ``role``."""
    match message.role:
        case LanguageModelMessageRole.ASSISTANT:
            return LanguageModelAssistantMessage(content=message.content)
        case LanguageModelMessageRole.SYSTEM:
            return LanguageModelSystemMessage(content=message.content)
        case LanguageModelMessageRole.USER:
            return LanguageModelUserMessage(content=message.content)
        case LanguageModelMessageRole.TOOL:
            raise ValueError(
                "Cannot convert a base LanguageModelMessage with role tool; "
                "use LanguageModelToolMessage with name and tool_call_id."
            )


class LanguageModelMessages(RootModel[list[LanguageModelMessageOptions]]):
    root: list[LanguageModelMessageOptions]

    @classmethod
    def load_messages_to_root(cls, data: list[dict[str, Any]] | dict[str, Any]) -> Self:
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
                    raise ValueError(f"Unknown message role: {item.get('role')!r}")
            else:
                # If it's already a message object, keep it as is
                converted_messages.append(item)
        return cls(root=converted_messages)

    def __str__(self):
        return "\n\n".join([str(message) for message in self.root])

    def __iter__(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def builder(self):
        """Returns a MessagesBuilder instance pre-populated with existing messages."""
        from unique_toolkit.language_model.builder import MessagesBuilder

        builder = MessagesBuilder()
        builder.messages = self.root.copy()  # Start with existing messages
        return builder

    @overload
    def to_openai(self, mode: Literal["responses"]) -> list[ResponseInputItemParam]: ...

    @overload
    def to_openai(
        self, mode: Literal["completions"] = "completions"
    ) -> list[ChatCompletionMessageParam]: ...

    def to_openai(
        self, mode: Literal["completions", "responses"] = "completions"
    ) -> list[ChatCompletionMessageParam] | list[ResponseInputItemParam]:
        # Use exact-type check: isinstance would match subclasses and would strip
        messages = [
            _language_model_message_to_subtype(m)
            if type(m) is LanguageModelMessage
            else m
            for m in self.root
        ]

        if mode == "responses":
            return [message.to_openai(mode="responses") for message in messages]
        return [message.to_openai(mode="completions") for message in messages]


ResponsesMessageSequence: TypeAlias = (
    Sequence[ResponseInputItemParam]
    | Sequence[LanguageModelMessageOptions]
    | Sequence[ResponseOutputItem]
)
ResponsesMessageInput: TypeAlias = (
    str | LanguageModelMessages | ResponsesMessageSequence
)


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
    # TODO(UN-19519): add a safe first_choice accessor that raises instead of IndexError on empty choices
    model_config = model_config

    choices: list[LanguageModelCompletionChoice]
    usage: LanguageModelTokenUsage | None = None

    @classmethod
    def from_stream_response(cls, response: LanguageModelStreamResponse):
        choice = LanguageModelCompletionChoice(
            index=0,
            message=LanguageModelAssistantMessage.from_stream_response(response),
            finish_reason="",
        )

        return cls(choices=[choice], usage=response.usage)


# The OpenAI SDK's ReasoningEffort type alias is generated from an older OpenAPI spec and is
# missing values that the API actually supports (e.g. "xhigh", "none"). We define our own
# complete type here as the source of truth.
ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]

# Ordered from lowest to highest reasoning effort. Used wherever effort levels must be
# compared or ranked (e.g. picking the maximum across multiple skill hints).
REASONING_EFFORT_ORDER: tuple[ReasoningEffort, ...] = (
    "none",
    "minimal",
    "low",
    "medium",
    "high",
    "xhigh",
)


def to_reasoning_effort(value: str) -> ReasoningEffort:
    """Narrow a raw string to ReasoningEffort, raising ValueError for unrecognised values."""
    match value:
        case "none" | "minimal" | "low" | "medium" | "high" | "xhigh":
            return value
        case _:
            raise ValueError(
                f"Unknown reasoning_effort {value!r}. "
                f"Supported values: none, minimal, low, medium, high, xhigh."
            )


def reasoning_effort_to_openai(effort: str) -> OpenAIReasoningEffort:
    """Convert our ReasoningEffort to the OpenAI SDK's type at the API boundary.

    A cast is required because OpenAIReasoningEffort is generated from an older OpenAPI spec
    that does not yet include all values present in our ReasoningEffort. The cast is safe:
    the API accepts these values even though the SDK type does not list them.
    """
    return cast(OpenAIReasoningEffort, effort)


# This is tailored for unique and only used in language model info
class LanguageModelTokenLimits(BaseModel):
    model_config = model_config

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
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Name must adhere to the pattern ^[a-zA-Z0-9_-]+$",
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
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Name must adhere to the pattern ^[a-zA-Z0-9_-]+$",
    )
    description: str = Field(
        ...,
        description="Description of what the tool is doing the tool",
    )
    parameters: type[BaseModel] | dict[str, Any] = Field(
        ...,
        description="Pydantic model for the tool parameters",
        union_mode="left_to_right",
    )

    # TODO: This should be default `True` but if this is the case the parameter_model needs to include additional properties
    strict: bool = Field(
        default=False,
        description="Setting strict to true will ensure function calls reliably adhere to the function schema, instead of being best effort. If set to True the `parameter_model` set `model_config = {'extra':'forbid'}` must be set for on all BaseModels.",
    )

    @field_serializer("parameters")
    def serialize_parameters(
        self, parameters: type[BaseModel] | dict[str, Any]
    ) -> dict[str, Any]:
        return _parameters_as_json_schema(parameters)

    @overload
    def to_openai(
        self, mode: Literal["completions"] = "completions"
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
                    parameters=_parameters_as_json_schema(self.parameters),
                    strict=self.strict,
                ),
                type="function",
            )
        elif mode == "responses":
            return FunctionToolParam(
                type="function",
                name=self.name,
                parameters=_parameters_as_json_schema(self.parameters),
                strict=self.strict,
                description=self.description,
            )


def _parameters_as_json_schema(
    parameters: type[BaseModel] | dict[str, Any],
) -> dict[str, Any]:
    if isinstance(parameters, dict):
        return parameters

    return parameters.model_json_schema()
