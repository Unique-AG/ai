# OpenAI Client

This tutorial demonstrates using the OpenAI chat completions API via the `unique_toolkit` package.

<!--
```{.python #openai_chat_completion_imports}
from pathlib import Path

from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition
from pydantic import BaseModel
```
-->

First we need to get an obtain the client from openai using the utitlity method `get_openai_client`. 
The secrets necessary in the `.env` file can be found [here](./secrets.md).

```{.python #openai_chat_completion_client_imports}
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)
from unique_toolkit.app.unique_settings import UniqueSettings

settings = UniqueSettings.from_env(env_file=Path(__file__).parent.parent.parent / ".env")
client = get_openai_client(unique_settings=settings)
model = "AZURE_GPT_4o_2024_0806"
```

We encourag the usage of the `OpenAIMessageBuilder` and the fluent builder pattern as it
avoids as long list of imports and helps with typing.


```{.python #openai_chat_completion_messages}
messages = (
    OpenAIMessageBuilder()
    .system_message_append(content="You are a helpful assistant")
    .user_message_append(content="How is the weather in New York")
).messages
```

Now we are ready to create our first completion using the OpenAI client

```{.python #openai_chat_completion_simple_completion}
# Simple Completion
response = client.chat.completions.create(
    messages=messages,
    model=model,
)
for c in response:
    print(c)
```

Structured output from the large language model can be obtained via pydantic models.
Be sure that the model chosen at the top supports this capability.

```{.python #openai_chat_completion_structured_output}
# Structured Output


class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]


completion = client.beta.chat.completions.parse(
    model=model,
    messages=messages,
    response_format=CalendarEvent,
)
completion.choices[0].message.content
```

Function calling enables agents and workflows to use tools. The below 
example shows how to define a function and how to pass it to the LLM.

```{.python #openai_chat_completion_function_calling}
## Function calling
weather_tool_description = ChatCompletionToolParam(
    function=FunctionDefinition(
        name="get_weather",
        description="Get current temperature for a given location.",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country e.g. Bogotá, Colombia",
                },
            },
            "required": ["location"],
            "additionalProperties": False,
        },
        strict=True,
    ),
    type="function",
)

completion = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "What is the weather like in Paris today?"}],
    tools=[weather_tool_description],
)
```

Newer models support the different kind of message roles `system`, `user`, `assistant` and `developer`. 
The former are well-known and a messages object usually follows the pattern

- system
- user
- assistant
- user 
- assistant
...

The newer `developer` messages enables us to give additional hints to the model that can be hidden in 
the frontend.


```{.python #openai_chat_completion_developer_message}
# Developer Message and logprobs
completion = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "developer", "content": "Always answer in french"},
        {"role": "user", "content": "What is the weather like in Paris today?"},
    ],
)
print(completion.choices[0].message.content)
```


<!--
```{.python file=examples/generated/openai_completions.py}
<<openai_chat_completion_imports>>
<<openai_chat_completion_client_imports>>
<<openai_chat_completion_messages>>
<<openai_chat_completion_simple_completion>>
<<openai_chat_completion_structured_output>>
<<openai_chat_completion_function_calling>>
<<openai_chat_completion_developer_message>>
```
-->
