# Unique Toolkit

This package provides highlevel abstractions and methods on top of `unique_sdk` to ease application development for the Unique Platform. 

The Toolkit is structured along the following domains:
- `unique_toolkit.chat`
- `unique_toolkit.content`
- `unique_toolkit.embedding`
- `unique_toolkit.language_model`

Each domain comprises a service class (in `service.py`) which encapsulates the basic functionalities to interact with the domain entities, the schemas 
(in `schemas.py`) used in the service and required for interacting with the service functions, utility functions (in `utils.py`) which give additional
functionality to interact with the domain entities (all domains except Embedding) and other domain specific functionalities which are explained in the respective domain documentation.

In addition, the `app` module provides functions to initialize and secure apps and perform parallel reuqests (only with async app like Flask) that will interact with the Unique platform. 

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

- `state.py` comprises the ChatState which is used to store the current state of the chat interaction and the user information.
- `service.py` comprises the ChatService and provides an interface to manage and load the chat history and interact with the chat ui, e.g., creating a new assistant message.
- `schemas.py` comprises all relevant schemas, e.g., ChatMessage, used in the ChatService.
- `utils.py` comprises utility functions to use and convert ChatMessage objects in assistants, e.g., convert_chat_history_to_injectable_string converts the chat history to a string that can be injected into a prompt. 

## Content

The `unique_toolkit.content` module encompasses all content related functionality. Content can be any type of textual data that is stored in the Knowledgebase on the Unique platform. During the ingestion of the content, the content is parsed, split in chunks, indexed, and stored in the database.

- `service.py` comprises the ContentService and provides an interface to interact with the content, e.g., search content, search content chunks, upload and download content.
- `schemas.py` comprises all relevant schemas, e.g., Content and ContentChunk, used in the ContentService.
- `utils.py` comprise utility functions to manipulate Content and ContentChunk objects, e.g., sort_content_chunks and merge_content_chunks.

## Embedding

The `unique_toolkit.embedding` module encompasses all embedding related functionality. Embeddings are used to represent textual data in a high-dimensional space. The embeddings can be used to calculate the similarity between two texts, for instance.

- `service.py` encompasses the EmbeddingService and provides an interface to interact with the embeddings, e.g., embed text and calculate the similarity between two texts.
- `schemas.py` comprises all relevant schemas, e.g., Embeddings, used in the EmbeddingService.

## Language Model

The `unique_toolkit.language_model` module encompasses all language model related functionality and information on the different language models deployed through the 
Unique platform.

- `infos.py` comprises the information on all language models deployed through the Unique platform. We recommend to use the LanguageModel class, initialized with the LanguageModelName, e.g., LanguageModel(LanguageModelName.AZURE_GPT_35_TURBO_16K) to get the information on the specific language model like the name, version, token limits or retirement date.
- `service.py` comprises the LanguageModelService and provides an interface to interact with the language models, e.g., complete or stream_complete. 
- `schemas.py` comprises all relevant schemas, e.g., LanguageModelResponse, used in the LanguageModelService.
- `utils.py` comprises utility functions to parse the output of the language model, e.g., convert_string_to_json finds and parses the last json object in a string.

# Development instructions

1. Install poetry on your system (through `brew` or `pipx`).

2. Install `pyenv` and install python 3.11. `pyenv` is recommended as otherwise poetry uses the python version used to install itself and not the user preferred python version.

3. If you then run `python --version` in your terminal, you should be able to see python version as specified in `.python-version`.

4. Then finally run `poetry install` to install the package and all dependencies.