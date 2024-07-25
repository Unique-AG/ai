# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.1] - 2024-07-23
- correct documentation

## [0.5.0] - 2024-07-23
### Added
- Added `unique_toolkit.app` module with the following components:
  - `init_logging.py` for initializing the logger.
  - `init_sdk.py` for initializing the SDK with environment variables.
  - `schemas.py` containing the Event schema.
  - `verification.py` for verifying the endpoint secret and constructing the event.

- Added `unique_toolkit.chat` module with the following components:
  - `state.py` containing the `ChatState` class.
  - `service.py` containing the `ChatService` class for managing chat interactions.
  - `schemas.py` containing relevant schemas such as `ChatMessage`.
  - `utils.py` with utility functions for chat interactions.

- Added `unique_toolkit.content` module with the following components:
  - `service.py` containing the `ContentService` class for interacting with content.
  - `schemas.py` containing relevant schemas such as `Content` and `ContentChunk`.
  - `utils.py` with utility functions for manipulating content objects.

- Added `unique_toolkit.embedding` module with the following components:
  - `service.py` containing the `EmbeddingService` class for working with embeddings.
  - `schemas.py` containing relevant schemas such as `Embeddings`.

- Added `unique_toolkit.language_model` module with the following components:
  - `infos.py` containing information on language models deployed on the Unique platform.
  - `service.py` containing the `LanguageModelService` class for interacting with language models.
  - `schemas.py` containing relevant schemas such as `LanguageModelResponse`.
  - `utils.py` with utility functions for parsing language model output.

## [0.0.2] - 2024-07-10
- Initial release of `unique_toolkit`.