# OpenAI Client

This tutorial demonstrates using the OpenAI chat completions API via the `unique_toolkit` package.

<!--
```{.python #common_library_imports}
from pathlib import Path
from pydantic import BaseModel
```

```{.python #openai_type_imports}
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition
```
-->

## Common Imports
In this documentation we skip some imports as the documentation provides working python code through the [Entangled](https://entangled.github.io/manual.html#), where are imports are declared. A link to the an example using the code blocks presented in this documentation will be found at the bottom of this page.

Nevertheless, we list the common imports that are particular to the unique toolkit when working with the openAI client.

```{.python #openai_toolkit_imports}
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)
```


## OpenAI Client

First we need to get an obtain the client from openai using the utitlity method `get_openai_client`. 

```{.python #get_openai_client}
client = get_openai_client()
```

## Determining the Model to be use

```{.python #toolkit_language_model}
model = LanguageModelName.AZURE_GPT_4o_2024_1120
```


## Building the messages

We encourag the usage of the `OpenAIMessageBuilder` and the fluent builder pattern as it
avoids as long list of imports and helps with typing.


```{.python #openai_chat_completion_messages}

messages = (
    OpenAIMessageBuilder()
    .system_message_append(content="You are a helpful assistant")
    .user_message_append(content="How is the weather in New York")
).messages
```

## Using the client

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

### Structured Output
Structured output from the large language model can be obtained via pydantic models.
Be sure that the model chosen at the top supports this capability.

```{.python #openai_chat_completion_structured_output}


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

### Function calling
Function calling enables agents and workflows to use tools. The below 
example shows how to define a function and how to pass it to the LLM.

<!--
```{python #tool_description_openai}
weather_tool_description_openai = ChatCompletionToolParam(
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
```
-->


```{.python #openai_chat_completion_function_calling}
from pydantic import Field
from unique_toolkit import LanguageModelToolDescription

class WeatherParameters(BaseModel):
    model_config = {"extra": "forbid"}
    location: str = Field(description="City and country e.g. Bogotá, Colombia")

weather_tool_description = LanguageModelToolDescription(
    name="get_weather",
    description="Get current temperature for a given location.",
    parameters=WeatherParameters,
    strict=True,
)

weather_tool_description_toolkit= weather_tool_description.to_openai()

messages = (
    OpenAIMessageBuilder()
    .system_message_append(content="You are a helpful assistant")
    .user_message_append(content="What is the weather like in Paris today?")
).messages

completion = client.chat.completions.create(
    model=model,
    messages=messages,
    tools=[weather_tool_description_toolkit],
)

completion.choices[0].message.tool_calls
```

### Roles
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

messages = (
    OpenAIMessageBuilder()
    .system_message_append(content="You are a helpful assistant")
    .user_message_append(content="How is the weather in New York")
).messages

completion = client.chat.completions.create(
    model=model,
    messages=messages,
)
print(completion.choices[0].message.content)
```


<!--
```{.python file=docs/.python_files/openai_completions.py}
<<common_imports>>
<<toolkit_language_model>>
<<get_openai_client>>
<<openai_chat_completion_messages>>
<<openai_chat_completion_simple_completion>>
<<openai_chat_completion_structured_output>>
<<openai_chat_completion_function_calling>>
<<openai_chat_completion_developer_message>>
```
-->
