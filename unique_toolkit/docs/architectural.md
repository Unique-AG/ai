# Architecture

## Goal
The user of the `unique toolkit` interacts with the unique plattform via services, concretely the 

- Knowledge Base Service - For all operations regarding the knowledge base only
- Chat Service - For all interaction with the chat interface
- Agentic Table Service (Soon) - To steer the the agentic table interface 

and well-known clients such as the OpenAI Client.

These interfaces are to be changed only by extension and the clients guarantee that the latest generative ai features are available quicker.

## Plattform Domains

The following domains are exist 


| Domain | Description |  Used by | 
|--|--|--|
| `app`  | Useful when dealing with settings and when dealing with events coming from the platform | Stateless API and Dev Setup |
| `chat` | Useful when interacting with the chat interface | `ChatService`|
| `content` | Useful when interacting with content saved in the knowledge base and chat| `ChatService` and `KnowledgeBaseService` |
| `framework_utilities` | Utilities to use e.g. OpenAIClient or `Langchain` and potentially other frameworks| 
| `agentic` | All definitions to rebuild orchestrators and tools fully compatible with Spaces 2.0 |  `tool_packages` and `orchestrator`|


### Resuling Service

The services bundle the platform domains into services that interact with a single entity or user interface.

| Service | Description | Maturity |
|--|--|--|
| `ChatService` | All capability to interact with the chat UI | ️ ⚙️ |
| `KnowlegeBaseService` | All capabilities to interact with the knowledge base |  🧰  ⚙️ ️|
| `AgenticTableService` | All capabilites to interact with the agentic table | 🧪  |

Maturity Levels:
- 🧪 Experimental: actively developped
- 🧰 In progress:  Used in production but being extended
- ️⚙️ Stable: Widely used in production 

Some domains resulted in Services that will be slowly deprecated

| Services| Description | Replacement | Status | Usage | 
|--|--|--|--|--|
| `EmbeddingService` | Access to embedding models| Use `OpenAIClient` directly | To be moved soon | Small |
| `LanguageModelService` | Access to language models | Use `OpenAIClient` directly| Deprectated | Medium |
| `ShortTermMemoreService` | Access to memory | Use in `ChatService` directly | To be moved soon | Small |


Services and Clients utilities are always directly importable from the `unique_toolkit`.

```python
from unique_toolkit import ChatService, KnowledgeBaseService 
from unique_toolkit import get_openai_client, get_async_openai_client, get_langchain_client
```


## Data Objects
The `DTOS` and other data objects are implemented via [pydantic](https://docs.pydantic.dev/2.12/) which handles validation as well as name transformations between the plattform and the python toolkit. The data objects can be found in the `schema.py` files and changed only by extension.

## Underlying functions
Functions using the `unique_sdk` are defined in the `functions.py` files and might be changed as the plattform evolves following usual deprecation patterns. Defining functionality per plattform domains helps to test the functionality in a simpler fashion.


