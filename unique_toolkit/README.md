# Unique Toolkit

This package provides highlevel abstractions and methods on top of `unique_sdk` to ease application development for the Unique Platform. 

The Toolkit is structured along the following domains:
- `unique_toolkit.chat`
- `unique_toolkit.content`
- `unique_toolkit.embedding`
- `unique_toolkit.language_model`
- `unique_toolkit.short_term_memory`

Each domain comprises a set of schemas (in `schemas.py`) are used in functions (in `functions.py`) which encapsulates the basic functionalities to interact with the plattform. 
The above domains represent the internal structure of the Unique platform.

For the `developers` we expose interfaces via `services` classes that correspond directly to an frontend or an entity the `user` interacts with. 

The following services are currently available:

| Service | Responsability |
|--|--|
| ChatService | All interactions with the chat interface | 
| KnowledgeBaseService | All interaction with the knowledgebase |

The services can be directly import as 

```
from unique_toolkit import ChatService, KnowledgeBaseService


In addition, the `unique_toolkit.app` module provides functions to initialize apps and dev utilities to interact with the Unique platform. 

## Changelog

See the [CHANGELOG.md](https://github.com/Unique-AG/ai/blob/main/unique_toolkit/CHANGELOG.md) file for details on changes and version history.

# Domains

## App

The `unique_toolkit.app` module encompasses functions for initializing and securing apps that will interact with the Unique platform.

- `init_logging.py` can be used to initalize the logger either with unique dictConfig or an any other dictConfig.
- `init_sdk.py` can be used to initialize the sdk using the correct env variables and retrieving the endpoint secret.
- `schemas.py` contains the Event schema which can be used to parse and validate the unique.chat.external-module.chosen event.
- `verification.py` can be used to verify the endpoint secret and construct the event.

## Chat

The `unique_toolkit.chat` module encompasses all chat related functionality.

- `functions.py` comprises the functions to manage and load the chat history and interact with the chat ui, e.g., creating a new assistant message.
- `schemas.py` comprises all relevant schemas, e.g., ChatMessage, used in the ChatService.
- `utils.py` comprises utility functions to use and convert ChatMessage objects in assistants, e.g., convert_chat_history_to_injectable_string converts the chat history to a string that can be injected into a prompt. 

## Content

The `unique_toolkit.content` module encompasses all content related functionality. Content can be any type of textual data that is stored in the Knowledgebase on the Unique platform. During the ingestion of the content, the content is parsed, split in chunks, indexed, and stored in the database.

- `functions.py` comprises the functions to manage and load the chat history and interact with the chat ui, e.g., creating a new assistant message.
- `schemas.py` comprises all relevant schemas, e.g., Content and ContentChunk, used in the ContentService.
- `utils.py` comprise utility functions to manipulate Content and ContentChunk objects, e.g., sort_content_chunks and merge_content_chunks.

## Embedding (To be Deprecated)

The `unique_toolkit.embedding` module encompasses all embedding related functionality. Embeddings are used to represent textual data in a high-dimensional space. The embeddings can be used to calculate the similarity between two texts, for instance.

- `functions.py` comprises the functions to embed text and calculate the similarity between two texts.
- `service.py` encompasses the EmbeddingService and provides an interface to interact with the embeddings, e.g., embed text and calculate the similarity between two texts.
- `schemas.py` comprises all relevant schemas, e.g., Embeddings, used in the EmbeddingService.

## Language Model 

The `unique_toolkit.language_model` module encompasses all language model related functionality and information on the different language models deployed through the 
Unique platform.

- `infos.py` comprises the information on all language models deployed through the Unique platform. We recommend to use the LanguageModel class, initialized with the LanguageModelName, e.g., LanguageModel(LanguageModelName.AZURE_GPT_4o_2024_1120) to get the information on the specific language model like the name, version, token limits or retirement date.
- `functions.py` comprises the functions to complete and stream complete to chat.
- `schemas.py` comprises all relevant schemas, e.g., LanguageModelResponse, used in the LanguageModelService.
- `utils.py` comprises utility functions to parse the output of the language model, e.g., convert_string_to_json finds and parses the last json object in a string.

## Short Term Memory 

The `unique_toolkit.short_term_memory` module encompasses all short term memory related functionality.

- `functions.py` comprises the functions to manage and load the chat history and interact with the chat ui, e.g., creating a new assistant message.
- `schemas.py` comprises all relevant schemas, e.g., ShortTermMemory, used in the ShortTermMemoryService.