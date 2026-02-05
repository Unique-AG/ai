# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.45.10] - 2026-02-05
- Add `RERUN_ROW` event type and `MagicTableRerunRowPayload` for targeted row re-execution in Agentic Tables

## [1.45.9] - 2026-02-03
- Add feature flag `FEATURE_FLAG_ENABLE_HTML_RENDERING_UN_15131` for HTML rendering support
- Put HTML rendering for code interpreter files behind the feature flag

## [1.45.8] - 2026-02-02
- Hallucination: Hide Source Selection Mode and Reference pattern from schema

## [1.45.7] - 2026-01-30
- Add JSON string parsing support for reasoning and text parameters in responses API (UI compatibility)
- Fix variable name bug in `_attempt_extract_verbosity_from_options` function
- Improve `other_options` handling to prevent overwriting explicitly set parameters

## [1.45.6] - 2026-01-30
- hallucination evaluator: Use original response to retrieve referenced chunk

## [1.45.5] - 2026-01-29
- Add HTML rendering support for code interpreter generated files

## [1.45.4] - 2026-01-26
- Add ArtifactType `AGENTIC_REPORT`

## [1.45.3] - 2026-01-26
- Include message log update in subagents and MCP tools

## [1.45.2] - 2026-01-26
- Make FileMimeType backwards compatible with legacy extensions

## [1.45.1] - 2026-01-26
- Add FileMimeType utility helpers

## [1.45.0] - 2026-01-23
- Remove unused code execution options from config

## [1.44.0] - 2026-01-23
- Add LoopIterationRunner abstraction for the responses api 

## [1.43.11] - 2026-01-23
- Add `RESPONSES_API` Capablity to some models that were missing it

## [1.43.10] - 2026-01-21
- Lowering the max iterations of the main agents and hard blocking Qwen3 from using too many agent rounds

## [1.43.9] - 2026-01-20
- Fix system message role conversion in responses API mode (was incorrectly set to "user", now correctly set to "system")

## [1.43.8] - 2026-01-16
- Add local CI testing commands via poethepoet (poe lint, poe test, poe ci-typecheck, etc.)

## [1.43.7] - 2026-01-15
- Cleanup hallucination config that is displayed in space config

## [1.43.6] - 2026-01-13
- Update message execution pipeline functions and service

## [1.43.5] - 2026-01-13
- Add deptry to dev dependencies for CI dependency checks
- Fix missing base_settings fixture parameter in FastAPI test

## [1.43.4] - 2026-01-14
- chore(deps-dev): bump aiohttp from 3.13.2 to 3.13.3

## [1.43.3] - 2026-01-13
- Changing default `assessment_type` in `SubAgentEvaluationServiceConfig` to `HALLUCINATION`

## [1.43.2] - 2026-01-12
- `DocxGeneratorService`: Alignment need to be specified by the template rather than in code

## [1.43.1] - 2026-01-12
- Remove accidental example report.md from repo

## [1.43.0] - 2026-01-11
- Add `WriteUpAgent` as an experimental service

## [1.42.9] - 2026-01-11
- Include feature flag to have message logs compatible with new ChatUI

## [1.42.8] - 2026-01-08
- Add validator to `BaseMetadata` in case `additional_sheet_information` is empty
- Add more code snippets to create references and pull file metadata

## [1.42.7] - 2026-01-08
- Add aliases for endpoint secret env var.

## [1.42.6] - 2026-01-07
- Remove double redundant condition

## [1.42.5] - 2026-01-07
- Add Mapping of metadata to the `search_content` calls
- Remove additional indentation by the markdown to docx converter

## [1.42.4] - 2026-01-07
- Added `additionalSheetInformation` to magic table event.

## [1.42.3] - 2026-01-05
- Added example code for agentic table

## [1.42.2] - 2026-01-05
- Fix naming of code interpreter tool in its `ToolPrompts`.

## [1.42.1] - 2025-01-05
- Version bump of SDK

## [1.42.0] - 2025-01-05
- Add new params for elicitation to `call_tool` api

## [1.41.0] - 2025-12-29
- Add `AgenticTable` service to unique_toolkit

## [1.40.0] - 2025-12-22
- Add option to use retrieve referenced chunks from their order
- Add `hide_in_chat` parameter to `upload_to_chat_from_bytes` and `upload_to_chat_from_bytes_async`
- Hide code interpreter files in chat 
- Code Interpreter files are now uploaded to chat by default

## [1.39.2] - 2025-12-18
- Add `litellm:gemini-3-flash-preview`, `litellm:openai-gpt-5-2` and `litellm:openai-gpt-5-2-thinking` to `language_model/info.py`

## [1.39.1] - 2025-12-17
- Add GPT-5.2, GPT-5.2_CHAT to supported models list

## [1.39.0] - 2025-12-17
- Adding simpler shortterm message abilities to chat service

## [1.38.4] - 2025-12-17
- Improving handling of tool calls with Qwen models

## [1.38.3] - 2025-12-17
- Move the failsafe exception to root folder of unique_toolkit from agentic tools

## [1.38.2] - 2025-12-17
- Fixing bug that language model infos were not loaded correctly

## [1.38.1] - 2025-12-16
- chore(deps): Bump urllib3 from 2.5.0 to 2.6.2 and unique_sdk from 0.10.48 to 0.10.58 to ensure urllib3 transitively

## [1.38.0] - 2025-12-15
- Including capability to load LanguageModelInfos in env variable

## [1.37.0] - 2025-12-15
- Adding a prompt appendix to enforce forced tool calls when using Qwen models

## [1.36.0] - 2025-12-11
- Add support for a sub agent tool system reminder when no references are present in the sub agent response.

## [1.35.4] - 2025-12-10
- Fix a potential stacktrace leak

## [1.35.3] - 2025-12-10
- Add option to ignore some options when calling the LLM for the planning step.

## [1.35.2] - 2025-12-05
- Increase speed of token reducer

## [1.35.1] - 2025-12-05
- Improve efficiency of token reducer if tool calls overshoot max token limit

## [1.35.0] - 2025-12-04
- Add `LoopIterationRunner` abstraction and support for planning before every loop iteration.

## [1.34.1] - 2025-12-02
- Update code interpreter tool instructions.

## [1.34.0] - 2025-12-02
- Add option to upload code interpreter generated files to the chat.

## [1.33.3] - 2025-12-02
- Fix serialization of ToolBuildConfig `configuration` field.

## [1.33.2] - 2025-12-01
- Upgrade numpy to >2.1.0 to ensure compatibility with langchain library

## [1.33.1] - 2025-12-01
- Add `data_extraction` to unique_toolkit

## [1.33.0] - 2025-11-28
- Add support for system reminders in sub agent responses.

## [1.32.1] - 2025-12-01
- Added documentation for the toolkit,some missing type hints and doc string fixes.

## [1.32.0] - 2025-11-28
- Add option to filter duplicate sub agent answers.

## [1.31.2] - 2025-11-27
- Added the function `filter_tool_calls_by_max_tool_calls_allowed` in `tool_manager` to limit the number of parallel tool calls permitted per loop iteration.

## [1.31.1] - 2025-11-27
- Various fixes to sub agent answers.

## [1.31.0] - 2025-11-20
- Adding model `litellm:anthropic-claude-opus-4-5` to `language_model/info.py`

## [1.30.0] - 2025-11-26
- Add option to only display parts of sub agent responses.

## [1.29.4] - 2025-11-25
- Add display name to openai builtin tools

## [1.29.3] - 2025-11-24
- Fix jinja utility helpers import

## [1.29.2] - 2025-11-21
- Add `jinja` utility helpers to `_common`

## [1.29.1] - 2025-11-21
- Add early return in `create_message_log_entry` if chat_service doesn't have assistant_message_id (relevant for agentic table)

## [1.29.0] - 2025-11-21
- Add option to force include references in sub agent responses even if unused by main agent response.

## [1.28.9] - 2025-11-21
- Remove `knolwedge_base_service` from DocXGeneratorService

## [1.28.8] - 2025-11-20
- Add query params to api operation
- Add query params to endpoint builder

## [1.28.7] - 2025-11-20
- Adding Message Step Logger Class to the agentic tools.

## [1.28.6] - 2025-11-20
- Adding tests for message role filtering in chat functions

## [1.28.5] - 2025-11-20
- Including `expired_at` parameter in content schema
- Including chatRole `SYSTEM` into chat schema

## [1.28.4] - 2025-11-20
- Bump tiktoken to 0.12.0

## [1.28.3] - 2025-11-20
- Add batch upload of files to knowledgebase
- Add create folders utilities

## [1.28.2] - 2025-11-20
- Adding model `litellm:gemini-3-pro-preview` to `language_model/info.py`

## [1.28.1] - 2025-11-19
- Remove `chat_service` from DocXGeneratorService
- Set review standards in pyright for toolkit
- Refactor type check pipeline

## [1.28.0] - 2025-11-19
- Add option to interpret sub agent responses as content chunks.
- Add option to specify a custom JSON schema for sub agent tool input.

## [1.27.2] - 2025-11-19
- Add test to token counting

## [1.27.1] - 2025-11-18
- Add missing `create_query_params_from_model` in experimental endoint_builder.py

## [1.27.0] - 2025-11-18
- Add `session_config` field to `ChatEventPayload` schema for chat session configuration support
- Add `ingestion_state` field to `Content` model for tracking content ingestion status
- Add `include_failed_content` parameter to content search functions in `KnowledgeBaseService`, `search_contents`, and `search_contents_async`
- Experimental: 
    - Fix HTTP GET requests in `build_request_requestor` to use query parameters (`params`) instead of JSON body
    - `build_requestor` to properly pass kwargs to `build_request_requestor`

## [1.26.2] - 2025-11-17
- Adding tool format information for MCP tools

## [1.26.1] - 2025-11-17
- Fix bug where forcing a tool still sends builtin tools to the LLM when using the responses api.

## [1.26.0] - 2025-11-17
- Adding model `AZURE_GPT_51_2025_1113`, `AZURE_GPT_51_THINKING_2025_1113`, `AZURE_GPT_51_CHAT_2025_1113`, `AZURE_GPT_51_CODEX_2025_1113`,  `AZURE_GPT_51_CODEX_MINI_2025_1113` and `litellm:openai-gpt-51` and `litellm:openai-gpt-51-thinking` to `language_model/info.py`

## [1.25.2] - 2025-11-12
- Standardize paths in unique toolkit settings

## [1.25.1] - 2025-11-12
- Make pipeline steps reusable
- Add pipeline checks for type errors
- Add pipeline checks for coverage

## [1.25.0] - 2025-11-10
- Download files generated by code execution in parrallel.
- Better display of files in the chat while loading.

## [1.24.5] - 2025-11-10
- Fix bug where images were not properly converted to responses api format.

## [1.24.4] - 2025-11-07
- Add `user_id` to language service for tracking
- Track `user_id` in hallucination check

## [1.24.3] - 2025-11-07
- Adding litellm models `litellm:gemini-2-5-flash-lite`

## [1.24.2] - 2025-11-06
- Fix build_requestor typehints

## [1.24.1] - 2025-11-06
- Add IconChartBar Icon to ToolIcon

## [1.24.0] - 2025-11-04
- Introduce ability to include system reminders in tools to be appended when the response is included in the tool call history

## [1.23.0] - 2025-11-04
- Refactor sub agent tools implementation for clarity and testability.

## [1.22.2] - 2025-11-03
- Updated `unique_ai_how-it-works.md` and `plan_processing.md` to document how new assistant messages are generated when the orchestrator produces output text and triggers tool calls within the same loop iteration.

## [1.22.1] - 2025-11-03
- Add missing package required markdown-it-py 

## [1.22.0] - 2025-10-31
- Add `DocxGeneratorService` for generating Word documents from markdown with template support
- Fix documentation for `update_message_execution`, `update_message_execution_async`, `update_assistant_message_execution`, and `update_assistant_message_execution_async` functions to correctly reflect that the `status` parameter is now optional

## [1.21.2] - 2025-10-30
- Fixing that system format info is only appended to system prompt if tool is called

## [1.21.1] - 2025-10-30
- Improve Spaces 2.0 display of tool progress reporter configuration.

## [1.21.0] - 2025-10-30
- Add option to customize the display of tool progress statuses.

## [1.20.1] - 2025-10-30
- Fix typing issues in `LanguageModelFunction`.

## [1.20.0] - 2025-10-30
- Fix bug where async tasks executed with `SafeTaskExecutor` did not log exceptions.
- Add option to customize sub agent response display title.
- Add option to display sub agent responses after the main agent response.
- Add option to specify postprocessors to run before or after the others in the `PostprocessorManager`.

## [1.19.3] - 2025-10-29
- More documentation on advanced rendering

## [1.19.2] - 2025-10-29
- Removing unused tool specific `get_tool_call_result_for_loop_history` function
- Removing unused experimental config `full_sources_serialize_dump` in `history_manager`

## [1.19.1] - 2025-10-29
- Make api operations more flexible
- Make verification button text adaptable

## [1.19.0] - 2025-10-28
- Enable additional headers on openai and langchain client


## [1.18.1] - 2025-10-28
- Fix bug where sub agent references were not properly displayed in the main agent response when the sub agent response was hidden.

## [1.18.0] - 2025-10-27
- Temporary fix to rendering of sub agent responses.
- Add config option `stop_condition` to `SubAgentToolConfig`
- Add config option `tool_choices` to `SubAgentToolConfig`
- Make sub agent evaluation use the name of the sub agent name if only one assessment is valid

## [1.17.3] - 2025-10-27
- Update Hallucination check citation regex parsing pattern

## [1.17.2] - 2025-10-23
- Adding model `AZURE_GPT_5_PRO_2025_1006` and `litellm:openai-gpt-5-pro` to `language_model/info.py`

## [1.17.1] - 2025-10-23
- Fix hallucination check input with all cited reference chunks.

## [1.17.0] - 2025-10-22
- Add more options to display sub agent answers in the chat.

## [1.16.5] - 2025-10-16
- Adding litellm models `litellm:anthropic-claude-haiku-4-5`

## [1.16.4] - 2025-10-18
- Fix bug with MCP tool parameters schema

## [1.16.3] - 2025-10-18
- Add logging of MCP tool schema and constructed parameters

## [1.16.2] - 2025-10-16
- Reduce operation dependency on path instead of full url

## [1.16.1] - 2025-10-16
- Update debug info for better tool call tracking

## [1.16.0] - 2025-10-16
- Add responses api support.
- Add utilities for code execution.

## [1.15.0] - 2025-10-15
- Enable to distinguish between environment and modifiable payload parameters in human verification

## [1.14.11] - 2025-10-13
- Introduce testing guidelines for AI
- Add AI tests to `tool_config` and `tool_factory.py`

## [1.14.10] - 2025-10-13
- Fix token counter if images in history

## [1.14.9] - 2025-10-13
- Fix removal of metadata

## [1.14.8] - 2025-10-13
- Use default tool icon on validation error

## [1.14.7] - 2025-10-13
- Update of token_limit parameters for Claude models

## [1.14.6] - 2025-10-10
- Fix circular import appearing in orchestrator

## [1.14.5] - 2025-10-09
- Move `DEFAULT_GPT_4o` constant from `_common/default_language_model.py` to `language_model/constants.py` and deprecate old import path

## [1.14.4] - 2025-10-09
- Small fixes when deleting content
- Fixes in documentation

## [1.14.3] - 2025-10-08
- Reorganizes documentation 
- All service interface towards a single folder
- Add main imports to __init__

## [1.14.2] - 2025-10-08
- Add utilities for testing and fix external import issue

## [1.14.1] - 2025-10-08
- Add utilities for testing

## [1.14.0] - 2025-10-07
- Manipulate Metadata with knowledge base service

## [1.13.0] - 2025-10-07
- Delete contents with knowledge base service

## [1.12.1] - 2025-10-07
- Fix bug where failed evaluations did not show an error to the user.

## [1.12.0] - 2026-10-07
- Add the `OpenAIUserMessageBuilder` for complex user messages with images
- More examples with documents/images on the chat

## [1.11.4] - 2026-10-07
- Make newer `MessageExecution` and `MessageLog` method keyword only

## [1.11.3] - 2026-10-07
- Move smart rules to content
- Add to documentation

## [1.11.2] - 2025-10-07
- Fix for empty metadata filter at info retrieval

## [1.11.1] - 2025-10-07
- Fix bug where hallucination check was taking all of the chunks as input instead of only the referenced ones.

## [1.11.0] - 2025-10-07
- Add sub-agent response referencing.

## [1.10.0] - 2025-10-07
- Introduce future proof knowledgebase service decoupled from chat
- Extend chat service to download contents in the chat
- Update documentation

## [1.9.1] - 2025-10-06
- Switch default model used in evaluation service from `GPT-3.5-turbo (0125)` to `GPT-4o (1120)`


## [1.9.0] - 2026-10-04
- Define the RequestContext and add aihttp/httpx requestors

## [1.8.1] - 2026-10-03
- Fix bug where sub agent evaluation config variable `include_evaluation` did not include aliases for previous names.

## [1.8.0] - 2026-10-03
- Sub Agents now block when executing the same sub-agent multiple times with `reuse_chat` set to `True`.
- Sub Agents tool, evaluation and post-processing refactored and tests added.

## [1.7.0] - 2025-10-01
- Add functionality to remove text in `get_user_visible_chat_history`

## [1.6.0] - 2025-10-01
- revert and simplify 1.5.0 

## [1.5.1] - 2025-10-01
- Fix filtering logic to raise a ConfigurationException if chat event filters are not specified

## [1.5.0] - 2025-10-01
- Allow history manager to fetch only ui visible text

## [1.4.4] - 2025-09-30
- Fix bugs with display of sub-agent answers and evaluations when multiple sub-agent from the same assistant run concurrently.

## [1.4.3] - 2025-09-30
- Fix bug with sub-agent post-processing reference numbers.

## [1.4.2] - 2025-09-30
- Adding litellm models `litellm:anthropic-claude-sonnet-4-5` and `litellm:anthropic-claude-opus-4-1`

## [1.4.1] - 2025-09-30
- Handle sub agent failed assessments better in sub agent evaluator.

## [1.4.0] - 2025-09-29
- Add ability to consolidate sub agent's assessments.

## [1.3.3] - 2025-09-30
- fix bug in exclusive tools not making them selectable

## [1.3.2] - 2025-09-29
- Auto-update unique settings on event arrival in SSE client

## [1.3.1] - 2025-09-29
- More documentation on referencing

## [1.3.0] - 2025-09-28
- Add utilitiy to enhance pydantic model with metadata
- Add capability to collect this metadata with same hierarchy as nested pydantic models

## [1.2.1] - 2025-09-28
- Fix bug where camel case arguments were not properly validated.

## [1.2.0] - 2025-09-24
- Add ability to display sub agent responses in the chat.

## [1.1.9] - 2025-09-24
- Fix bug in `LanguageModelFunction` to extend support mistral tool calling.

## [1.1.8] - 2025-09-23
- Revert last to version 1.1.6

## [1.1.7] - 2025-09-23
- Introduce keyword only functions in services for better backward compatibility
- Deprecatea functions that are using positional arguments in services 

## [1.1.6] - 2025-09-23
- Fix model_dump for `ToolBuildConfig`

## [1.1.5] - 2025-09-23
- Fix a circular import and add tests for `ToolBuildConfig`

## [1.1.4] - 2025-09-23
- First version human verification on api calls

## [1.1.3] - 2025-09-23
- Updated LMI JSON schema input type to include annotated string field with title

## [1.1.2] - 2025-09-22
- Fixed bug tool selection for exclusive tools

## [1.1.1] - 2025-09-18
- Fixed bug on tool config added icon name

## [1.1.0] - 2025-09-18
- Enable chat event filtering in SSE event generator via env variables

## [1.0.0] - 2025-09-18
- Bump toolkit version to allow for both patch and minor updates

## [0.9.1] - 2025-09-17
- update to python 3.12 due to security 

## [0.9.0] - 2025-09-14
- Moved agentic code into the `agentic` folder. This breaks imports of
  - `debug_info_amanager`
  - `evals`
  - `history_manager`
  - `post_processor`
  - `reference-manager`
  - `short_term_memory_manager`
  - `thinking_manager`
  - `tools`

## [0.8.57] - 2025-09-14
- Added more utils to commons

## [0.8.56] - 2025-09-12
- Fixed token counter in utils

## [0.8.55] - 2025-09-10
- Update documentation with agentic managers

## [0.8.54] - 2025-09-10
- HistoryManager: compute source numbering offset from prior serialized tool messages using `load_sources_from_string`
- LoopTokenReducer: serialize reduced tool messages as JSON arrays to keep offsets parsable

## [0.8.53] - 2025-09-09
- Add support for skip ingestion for only excel files.

## [0.8.52] - 2025-09-06
- Fix import error in token counting

## [0.8.51] - 2025-09-06
- Update token counter to latest version of monorepo.

## [0.8.50] - 2025-09-08
- Minor fix in documentation
- Updated examples

## [0.8.49] - 2025-09-05
- Fixed token reducer now has a safety margin of 10% less did not work.

## [0.8.48] - 2025-09-05
- Add documentation on language models to markdown

## [0.8.47] - 2025-09-05
- Removed old code
- Fixed small bugs in history manager & set the hallucination to use gpt4o as default.

## [0.8.46] - 2025-09-04
- Bugfix for hostname identification inside Unique cluster in `unique_settings.py`

## [0.8.45] - 2025-09-04
- Introduce handoff capability to tools. with the `takes_control()` function.

## [0.8.44] - 2025-09-03
- Refine `EndpointClass` and create `EndpointRequestor`

## [0.8.43] - 2025-09-03
- Add alias for `UniqueSettings` api base `API_BASE`

## [0.8.42] - 2025-09-02
- updated schema of `chunk_relevancy_sorter`

## [0.8.41] - 2025-09-02
- Make A2A tool auto register with tool factory

## [0.8.40] - 2025-09-02
- Add frontend compatible type for pydantic BaseModel types in pydantic BaseModels

## [0.8.39] - 2025-09-02
- include `get_async_openai_client`

## [0.8.38] - 2025-09-01
- Sanitize documentation

## [0.8.37] - 2025-09-01
- Adapt defaults and json-schema in `LanguageModelInfo`

## [0.8.36] - 2025-09-01
- Added dependency `Pillow` and `Platformsdir`

## [0.8.35] - 2025-09-01
- Initial toolkit documentation (WIP)

## [0.8.34] - 2025-09-01
- Automatic initializations of services and event generator

## [0.8.33] - 2025-08-31
- fixed tool for `web_search`

## [0.8.32] - 2025-08-30
- moved over general packages for `web_search`

## [0.8.31] - 2025-08-29
- Add various openai models to supported model list
  - o1
  - o3
  - o3-deep-research
  - o3-pro
  - o4-mini
  - o4-mini-deep-research
  - gpt-4-1-mini
  - gpt-4-1-nano

## [0.8.30] - 2025-08-28
- Added A2A manager

## [0.8.29] - 2025-08-27
- Include `MessageExecution` and `MessageLog` in toolkit 

## [0.8.28] - 2025-08-28
- Fix paths for `sdk_url` and `openai_proxy` for localhost

## [0.8.27] - 2025-08-28
- Fixed function "create_async" in language_model.functions : "user_id" argument should be optional.

## [0.8.26] - 2025-08-27
- Optimized MCP manager

## [0.8.25] - 2025-08-27
- Load environment variables automatically from plattform dirs or environment
- General Endpoint definition utility
- Expose `LanguageModelToolDescription` and `LanguageModelName` directly
- Get initial debug information from chat payload  

## [0.8.24] - 2025-08-25
- Optimized hallucination manager

## [0.8.23] - 2025-08-27
- Add MCP manager that handles MCP related logic


## [0.8.22] - 2025-08-25
- Add DeepSeek-R1, DeepSeek-V3.1, Qwen3-235B-A22B and Qwen3-235B-A22B-Thinking-2507 to supported model list

## [0.8.21] - 2025-08-26
- Fixed old (not used) function "create_async" in language_model.functions : The function always returns "Unauthorized" --> Added "user_id" argument to fix this.

## [0.8.20] - 2025-08-24
- Fixed forced-tool-calls
- Bump SDK version to support the latest features.

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
