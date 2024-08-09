# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.12] - 2024-08-7
- added `completedAt` datetime to `unique_sdk.Message.modify` and `unique_sdk.Message.modify_async`
- added `original_text` and `language` to `EventUserMessage`

## [0.5.11] - 2024-08-6
- made all domain specific functions and classes directly importable from `unique_toolkit.[DOMAIN_NAME]`
- renamed `RerankerConfig` to `ContentRerankerConfig`
- renamed `get_cosine_similarity` to `calculate_cosine_similarity` and moved it to `unique_toolkit.embedding.utils`
- moved `calculate_tokens` from `unique_toolkit.content.utils` to `unique_toolkit.embedding.utils`
- disabled deprecation warning in `LanguageModel`
- added `additional_parameters` to event
- removed `ChatState` and use `Event` instead

## [0.5.10] - 2024-08-6
- fix content schema

## [0.5.9] - 2024-08-6
- added `created_at` and `updated_at` to content schema

## [0.5.8] - 2024-08-1
- `RerankerConfig` serialization alias added

## [0.5.7] - 2024-07-31
- Replace mocked async service calls with async calls in `unique_sdk` 
- Change async methods name from `async_*` to `*_async`
- Remove `chat_only` and `scope_ids` attributes from `ChatState` class
- Replace `AsyncExecutor` by simpler utility function `run_async_tasks_parallel`

## [0.5.6] - 2024-07-30
- Bug fix: `ContentService.search_content_chunks` and it's `async` equivalent now accept `None` as a valid parameter value for `scope_ids`.

## [0.5.5] - 2024-07-30
- Added parameters to `ContentService.search_content_chunks` and `ContentService.async_search_content_chunks`
  - `reranker_config` to optinally rerank the search results
  - `search_language` to specify a language for full-text-search

## [0.5.4] - 2024-07-26
- correct ChatMessage schema

## [0.5.3] - 2024-07-25
- downgrade numpy version to ^1.26.4 to be compatible with langchain libraries (require numpy<2.0)

## [0.5.2] - 2024-07-25
- correct event schema

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