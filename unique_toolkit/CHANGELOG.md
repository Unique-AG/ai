# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.8.19] - 2025-08-24
- Enforce usage of ruff using pipeline

## [0.8.18] - 2025-08-22
- moved class variables into instance variables

## [0.8.17] - 2025-08-22
- fixed circular dependencies in tools

## [0.8.16] - 2025-08-19
- moved Hallucination evaluator into toolkit

## [0.8.15] - 2025-08-19
- Added history loading from database for History Manager

## [0.8.14] - 2025-08-19
- Including GPT-5 series deployed via LiteLLM into language model info

## [0.8.13] - 2025-08-18
- Adding initial versions of
  - Evaluation Manager
  - History Manager
  - Postprocessor Manager
  - Thinking Manager
- Updated tool manager

## [0.8.12] - 2025-08-18
- Fix no tool call respoonse in ChatMessage -> Open Ai messages translation
- Add simple append method to OpenAIMessageBuilder

## [0.8.11] - 2025-08-15
- Fix no tool call respoonse in ChatMessage -> Open Ai messages translation
- Add simple append method to OpenAIMessageBuilder

## [0.8.10] - 2025-08-15
- Add min and max temperature to `LanguageModelInfo`: temperature will be clamped to the min and max temperature
- Add default options to `LanguageModelInfo`: These are used by default

## [0.8.9] - 2025-08-15
- Reduce input token limits for `ANTHROPIC_CLAUDE_3_7_SONNET_THINKING`, `ANTHROPIC_CLAUDE_3_7_SONNET`, `ANTHROPIC_CLAUDE_OPUS_4` and `ANTHROPIC_CLAUDE_SONNET_4` to 180_000 from 200_000

## [0.8.8] - 2025-08-11
- Make chat service openai stream response openai compatible 
- Make `ChatMessage` openai compatible

## [0.8.7] - 2025-08-11
- Make chat service openai compatible
- Fix some bugs
- Make OpenAIMessageBuilder more congruent to MessageBuilder

## [0.8.6] - 2025-08-11
- Add GPT-5, GPT-5_MINI, GPT-5_NANO, GPT-5_CHAT to supported models list

## [0.8.5] - 2025-08-06
- Refactored tools to be in the tool-kit

## [0.8.4] - 2025-08-06
- Make unique settings compatible with legacy environment variables

## [0.8.3] - 2025-08-05
- Expose threshold field for search.

## [0.8.2] - 2025-08-05
- Implement overloads for services for clearer dev experience
- Proper typing for SSE event handling
- Enhanced unique settings. Expose usage of default values in logs
- SDK Initialization from unique settings
- Add utilities for to run llm/agent flows for devs

## [0.8.1] - 2025-08-05
- Bump SDK version to support the latest features.

## [0.8.0] - 2025-08-04
- Add MCP support

## [0.7.42] - 2025-08-01
- Added tool definitions

## [0.7.41] - 2025-07-31
- Add new chat event attribute indicating tools disabled on a company level

## [0.7.40] - 2025-07-30
- Remove `GEMINI_2_5_FLASH_PREVIEW_0417` model

## [0.7.39] - 2025-07-28
- Implement utitilites to work with openai client
- Implement utitilites to work with langchain llm 

## [0.7.38] - 2025-07-25
- Fix issues with secret strings in settings

## [0.7.36] - 2025-07-25
- Fix issues with settings
- Add testing to unique settings

## [0.7.35] - 2025-07-23
- Bump version of SDK to have access to the latest features and fixes

## [0.7.34] - 2025-05-30
- Fix incorrect mapping in `ContentService` for the `search_content` function when mapping into `ContentChunk` object

## [0.7.33] - 2025-06-25
- Update reference post-processing

## [0.7.32] - 2025-06-24
- Create `classmethod` for `LanguageModelMessages` to load raw messages to root

## [0.7.31] - 2025-06-19
- Add typings to references in payload from `LanguageModelStreamResponseMessage` 
- Add `original_index` to the base reference to reflect updated api

## [0.7.30] - 2025-06-20
- Adding litellm models `litellm:gemini-2-5-flash`, `gemini-2-5-flash-lite-preview-06-17`, `litellm:gemini-2-5-pro`, `litellm:gemini-2-5-pro-preview-06-05`

## [0.7.29] - 2025-06-19
- Fix typehintin in services
- Error on invalid initialization

## [0.7.28] - 2025-06-17
- Revert default factory change on `ChatEventPayload` for attribute `metadata_filter` due to error in `backend-ingestion` on empty dict

## [0.7.27] - 2025-06-16
- Introduce a protocol for `complete_with_references` to enable testable services
- Rename/Create functions `stream_complete` in chat service and llm service accordingly

## [0.7.26] - 2025-06-05
- Add `scope_rules` to `ChatEventPayload`
- Added `UniqueQL` compiler and pydantic classes for `UniqueQL`. Note this is functionally equivalent but not identical to `UQLOperator` or `UQLCombinator` in `unique_sdk`.

## [0.7.25] - 2025-06-05
- Adding models `AZURE_GPT_41_MINI_2025_0414`, `AZURE_GPT_41_NANO_2025_0414`

## [0.7.24] - 2025-05-30
- Adding litellm model `gemini-2-5-flash-preview-05-20`, `anthropic-claude-sonnet-4` and `anthropic-claude-opus-4`

## [0.7.23] - 2025-05-22
- add encoder for `AZURE_GPT_4o_2024_1120` to be part of the encoder function returns.

## [0.7.22] - 2025-05-22
- `messages` are now always serialized by alias. This affects `LanguageModelService.complete` and `LanguageModelService.complete_async`.

## [0.7.21] - 2025-05-21
- Extend the update the `ChatMessage` object to include the `Reference` object introduced in the public api

## [0.7.20] - 2025-05-21
- Deprecate `LanguageModelTool` and associated models in favor of `LanguageModelToolDescription`

## [0.7.19] - 2025-05-20
- Extend the `MessageBuilder` to allow for appending any `LanguageModelMessage`

## [0.7.18] - 2025-05-20
- Add the possibility to specify metadata when creating or updating a Content.

## [0.7.17] - 2025-05-16
- Change inheritance hierarchy of events for easier deprecation

## [0.7.16] - 2025-05-16
- Add classmethods to create LanguageModelAssistatnMessage from functions and stream response
- Add completion like method to chat
- Add protocol for completion like method

## [0.7.15] - 2025-05-13
- Add the possibility to specify ingestionConfig when creating or updating a Content.

## [0.7.14] - 2025-05-08
- Fix bug not selecting the correct llm
- Add LMI type for flexible init of LanguageModelInfo
- Replace LanguageModel with LanguageModelInfo in hallucination check 

## [0.7.13] - 2025-05-07
- Adding litellm models `litellm:anthropic-claude-3-7-sonnet`, `litellm:anthropic-claude-3-7-sonnet-thinking`, `litellm:gemini-2-0-flash`, `gemini-2-5-flash-preview-04-17` , `litellm:gemini-2-5-pro-exp-03-25`

## [0.7.12] - 2025-05-02
- add `AZURE_o3_2025_0416` and `AZURE_o4_MINI_2025_0416` as part of the models

## [0.7.11] - 2025-04-28
- Removing `STRUCTURED_OUTPUT` capability from `AZURE_GPT_35_TURBO_0125`, `AZURE_GPT_4_TURBO_2024_0409` and `AZURE_GPT_4o_2024_0513`

## [0.7.10] - 2025-04-22
- Deprecate internal variables of services

## [0.7.9] - 2025-04-17
- add `AZURE_GPT_41_2025_0414` as part of the models

## [0.7.8] - 2025-04-08
- add `AZURE_GPT_4o_2024_1120` as part of the models

## [0.7.7] - 2025-04-11
- Add tool choice parameter to chat event payload

## [0.7.6] - 2025-04-08
- De provisioning o1-preview

## [0.7.5] - 2025-04-07
- Skip None values when serializing to json schema for LanguageModelInfo

## [0.7.4] - 2025-03-20
- add `AZURE_GPT_45_PREVIEW_2025_0227` as part of the models

## [0.7.3] - 2025-03-20
- Enable handling tool calls in message builder

## [0.7.2] - 2025-03-17
- HotFix `ContentService.search_content_chunks` to use `chat_id` from event if provided.

## [0.7.1] - 2025-03-11
- Fix Breaking change: `ContentService.search_content_chunks` `ContentService.search_content_chunks` now accepts`chat_id` for the specific to handle chat_only instances

## [0.7.0] - 2025-03-11
- Fix the issue with `ShortTermMemoryService.create_memory_async` adding `self.chat_id` and `self.message_id` as part of the parameter.
- Breaking change: `ContentService.search_content_on_chat` now requires you pass in a `chat_id` for the specific chat instance

## [0.6.9] - 2025-03-11
- Add o1-preview as part of the language model info, make the name consistent across board.

## [0.6.8] - 2025-03-11
- Add `verify_request_and_construct_event` to `verification.py`

## [0.6.7] - 2025-03-10
- Extend language model message builder

## [0.6.6] - 2025-03-10
- Add o1, o1-mini and o3-mini models
- Remove deprecated gpt4 models
- Make token_limits and encoder a required attribute of LanguageModelInfo

## [0.6.5] - 2025-03-04
- Add `upload_content_from_bytes` to `ContentService`
- Add `download_content_to_bytes` to `ContentService`

## [0.6.3] - 2025-02-27
- Simplified imports for services. `from unique_toolkit.language_model import LanguageModelService` -> `from unique_toolkit import LanguageModelService` to reduce number of import lines.

## [0.6.3] - 2025-02-26
- Add `builder` method to `LanguageModelMessages` class

## [0.6.2] - 2025-02-25
- Deprecate `LanguageModel` in favor of `LanguageModelInfo`
- `LanguageModelTokenLimits` properties become mandatory, initialization allows 
  - init with `token_limit` and `fraction_input` or `input_token_limit` and `output_token_limit`
  - only `input_token_limit` and `output_token_limit` are members of model

## [0.6.1] - 2025-02-25
- [BREAKING] `LanguageModelService.stream_complete` and `LanguageModelService.stream_complete_async` are now moved to `ChatService.stream_complete` and `ChatService.stream_complete_async`. Correspondingly `assistant_message_id` and `user_message_id` are removed from `LanguageModelService`.
- Add `create_user_message` and `create_user_message_async` to `ChatService` (similar to `create_assistant_message` and `create_assistant_message_async`)

## [0.6.0] - 2025-02-21
- make for each domain, its base functionality accessible from `functions.py`
- make it possible to instantiate the domain services directly from different event types, inhereted from common `BaseEvent`
- extend the functionalities in the ShortTermMemoryService by adding the `find_latest_memory` and `create_memory` functions for sync and async usage
- remove logger dependency from service classes
- marked deprecated:
  - `from_chat_event` in ShortTermMemoryService, use `ShortTermMemoryService(event=event)` instead
  - `complete_async_util` in LanguageModelService, use `functions.complete_async` instead
  - `stream_complete_async` in LanguageModelService, use `stream_complete_to_chat_async` instead
  - `stream_complete` in LanguageModelService, use `stream_complete_to_chat` instead
  - `Event` and nested schemas in `app`, use `ChatEvent` and `ChatEventUserMessage`, `ChatEventAssistantMessage` and `ChatEventToolMessage` instead

## [0.5.56] - 2025-02-19
- Add `MessageAssessment` title field and change label values

## [0.5.55] - 2025-02-18
- Log `contentId` for better debugging

## [0.5.54] - 2025-02-10
- Add `created_at`, `completed_at`, `updated_at` and `gpt_request` to `ChatMessage` schema.

## [0.5.53] - 2025-02-01
- Correct `MessageAssessment` schemas

## [0.5.52] - 2025-02-01
- Add `MessageAssessment` schemas and functions to `ChatService` to handle message assessments.
- Fix `LanguageModelService.complete_async_util` to use the correct async method.

## [0.5.51] - 2025-01-30
- Add missing structured output arguments in complete_async

## [0.5.50] - 2025-01-30
- Add the possibility to define completion output structure through a pydantic class

## [0.5.49] - 2025-01-24
- Add `parsed` and `refusal` to `LanguageModelAssistantMessage` to support structured output

## [0.5.48] - 2025-01-19
- Added the possibility define tool parameters with a json schema (Useful when generating tool parameters from a pydantic object)

## [0.5.47] - 2025-01-07
- Added a message builder to build language model messages conveniently without importing all different messages.
- Move tool_calls to assistant message as not needed anywhere else.

## [0.5.46] - 2025-01-07
 - Added `AZURE_GPT_35_TURBO_0125` as new model into toolkit.

## [0.5.45] - 2025-01-03
- Added `ShortTermMemoryService` class to handle short term memory.

## [0.5.44] - 2024-12-18
- Add `event_constructor` to `verify_signature_and_construct_event` to allow for custom event construction.

## [0.5.43] - 2024-12-13
- Add `Prompt` class to handle templated prompts that can be formatted into LanguageModelSystemMessage and LanguageModelUserMessage.

## [0.5.42] - 2024-12-11
- Update `LanguageModelTokenLimits` with fix avoiding floats for token

## [0.5.41] - 2024-12-11
- Update `LanguageModelTokenLimits` includes a fraction_input now to always have input/output token limits available.

## [0.5.40] - 2024-12-11
- Add `other_options` to `LanguageModelService.complete`, `LanguageModelService.complete_async`, `LanguageModelService.stream_complete` and `LanguageModelService.stream_complete_async`

## [0.5.39] - 2024-12-09
- Add `contentIds` to `Search.create` and `Search.create_async`
- Use `metadata_filter` from event in `ContentService.search_content_chunks` and `ContentService.async_search_content_chunks` as default.

## [0.5.38] - 2024-11-26
- Added string representation to `LanguageModelMessage` and `LanguageModelMessages` class

## [0.5.37] - 2024-11-26
- `content` parameter in `ChatService.modify_assistant_message` and `ChatService.modify_assistant_message_async` is now optional
- Added optional parameter `original_content` to `ChatService.modify_assistant_message` and `ChatService.modify_assistant_message_async`
- Added optional parameter `original_content` to `ChatService.create_assistant_message` and `ChatService.create_assistant_message_async`

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