# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.36] - 2024-11-19
- Add possibility to return the response from the download file from chat request
- Add possibility to not specify a filename and use filename from response headers

## [0.5.35] - 2024-11-18
- Add the possibilty to upload files without triggering ingestion by setting `skip_ingestion` to `True` in `ContentService.upload_content`

## [0.5.34] - 2024-11-15
- Add `content_id_to_translate` to `EventAdditionalParameters`

## [0.5.33] - 2024-10-30
- Force randomizing tool_call_id. This is helpful to better identify the tool_calls.

## [0.5.32] - 2024-10-30
- Extending `LanguageModelName` with GPT-4o-2024-0806. This model is invoked using `AZURE_GPT_4o_2024_0806`.

## [0.5.31] - 2024-10-29
- Adding support for function calling. Assistant message for tool calls can be directly created with `LanguageModelFunctionCall.create_assistant_message_from_tool_calls`. Better separation of schemas for different types of `LanguageModelMessages`.

## [0.5.30] - 2024-10-28
- Correctly use `temperature` parameter in `LanguageModelService.complete` and `LanguageModelService.complete_async` methods

## [0.5.29] - 2024-10-28
- Allow numbers in `LanguageModelTool` name

## [0.5.28] - 2024-10-23
- Correctly use `temperature` parameter in `LanguageModelService.stream_complete` and `LanguageModelService.stream_complete_async` methods

## [0.5.27] - 2024-10-22
- Add encoder_name to to language model info
- Verify tool name for `LanguageModelTool` to conform with frontent requirements.
- Add `search_on_chat` to `ContentService`

## [0.5.26] - 2024-10-16
- Bump `unique_sdk` version

## [0.5.25] - 2024-09-26
- Add `evaluators` for hallucination and context relevancy evaluation

## [0.5.24] - 2024-09-26
- Add `originalText` to `_construct_message_modify_params` and `_construct_message_create_params`. This addition makes sure that the `originalText` on the database is populated with the `text`

## [0.5.23] - 2024-09-23
- Add `set_completed_at` as a boolen parameter to the following functions: `modify_user_message`, `modify_user_message_async`, `modify_assistant_message`, `modify_assistant_message_async`, `create_assistant_message` and `create_assistant_message`. This parameter allows the `completedAt` timestamp on the database to be updated when set to True.

## [0.5.22] - 2024-09-17
- Add `LanguageModelToolMessage` as additional `LanguageModelMessage`

## [0.5.21] - 2024-09-16
- Add `tool` as new role to `ChatMessage`, as well as `tool_calls` and `tool_call_id` as additional parameters

## [0.5.20] - 2024-09-16
- `LanguageModelService` now supports complete_util_async that can be called without instantiating the class, currently being used in the Hallucination service and evaluation API

## [0.5.19] - 2024-09-11
- `LanguageModelMessage` now supports content as a list of dictionary. Useful when adding image_url content along user message. 

## [0.5.18] - 2024-09-03
- Adds option to use `metadata_filter` with search.
- Adds `user_metadata`, `tool_parameters` and `metadata_filter` to `EventPayload`.
- Adds `update_debug_info` and `modify_user_message` (and the corresponding `async` variants) to `ChatService`.

## [0.5.17] - 2024-08-30
- Add option to initiate `LanguageModel` with a string.
- Add option to call `LanguageModelService` functions also with a string instead of `LanguageModelName` enum for parameter `model_name`.

## [0.5.16] - 2024-08-29
- Fix `ContentService.upload_content` function.

## [0.5.15] - 2024-08-27
- Possibility to specify root directory in `ContentService.download_content`

## [0.5.14] - 2024-08-26
- Add AZURE_GPT_4o_MINI_2024_0718 to language model infos

## [0.5.13] - 2024-08-19
- Added `items` to `LanguageModelToolParameterProperty` schema to add support for parameters with list types.
- Added `returns` to `LanguageModelTool` schema to describe the return types of tool calls.

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