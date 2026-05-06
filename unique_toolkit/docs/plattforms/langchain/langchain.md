# Langchain Client

The Langchain client integration lets you use Unique's API-backed models with [LangChain](https://python.langchain.com/), enabling chains, agents, tool calling, and other LangChain patterns while routing requests through the Unique platform.

## Overview

**Purpose**: Bridge the Unique platform's API with LangChain's `ChatOpenAI` interface so you can build LangChain applications (RAG, agents, chains) without managing model endpoints or authentication separately.

**Components**:

- `get_langchain_client()` – returns a configured `ChatOpenAI` instance (accepts `LanguageModelName` or `str` for `model`)
- `LangchainNotInstalledError` – raised when the langchain group is not installed

**Prerequisites**:

- Install the langchain group: `uv add unique_toolkit[langchain]`
- Configure `unique.env` with your app credentials (see [Getting Started](../../setup/getting_started.md))


---

## Usage

### Basic Example

Get a client and invoke a simple prompt:

```{.python #langchain_basic_invoke}
from langchain_core.messages import HumanMessage, SystemMessage

from unique_toolkit import get_langchain_client

# Client uses UniqueSettings.from_env_auto() when unique_settings is omitted
llm = get_langchain_client()

messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="Write a one-sentence bedtime story about a unicorn."),
]

response = llm.invoke(messages)
print(response.content)
```

### Custom Model and Settings

```{.python #langchain_custom_model}
from unique_toolkit import LanguageModelName, get_langchain_client
from unique_toolkit.app.unique_settings import UniqueSettings

# Use a specific model (default is LanguageModelName.AZURE_GPT_4o_2024_0806)
llm = get_langchain_client(
    model=LanguageModelName.AZURE_GPT_4o_2024_1120,
) 

# With explicit settings (e.g. from a config file)
settings = UniqueSettings.from_env_auto()
llm = get_langchain_client(
    unique_settings=settings, model=LanguageModelName.AZURE_GPT_4o_2024_1120
)
```

### Additional Headers

You can pass extra headers (e.g. for request tracing):

```{.python #langchain_additional_headers}
llm = get_langchain_client(
    additional_headers={"x-request-id": "my-trace-id"},
)
```

### With a Simple Chain

```{.python #langchain_simple_chain}
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from unique_toolkit import get_langchain_client

llm = get_langchain_client()

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant that answers briefly."),
    ("human", "{question}"),
])

chain = prompt | llm

response = chain.invoke({"question": "What is 2 + 2?"})
print(response.content)
```

---

## Error Handling

| Situation | Behavior |
|-----------|----------|
| Langchain group not installed | `LangchainNotInstalledError` on import of `unique_toolkit.framework_utilities.langchain` or when calling `get_langchain_client()` |
| Missing or invalid `unique.env` | `UniqueSettings.from_env_auto()` will raise; ensure `unique.env` exists and contains required keys |
| API errors | Propagated from the underlying `ChatOpenAI` / Unique API client |

---

## Best Practices

1. **Install the langchain group**: Use `uv add unique_toolkit[langchain]` so `langchain-openai` and `langchain-core` are available.
2. **Reuse the client**: Creating the client is cheap; you can reuse it for multiple `invoke()` or chain runs.
3. **Avoid mutable defaults**: Pass `additional_headers` as a new dict when needed; do not reuse mutable defaults across calls.

---

## Full Example

<!--
```{.python file=docs/.python_files/langchain_simple_invoke.py}
<<langchain_basic_invoke>>
```
-->

??? example "Full Example (Click to expand)"

    <!--codeinclude-->
    [Simple invoke with LangChain](../../examples_from_docs/langchain_simple_invoke.py)
    <!--/codeinclude-->
