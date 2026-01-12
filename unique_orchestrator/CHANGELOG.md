# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.11.5] - 2026-01-12
- Include feature flag to have message logs compatible with new ChatUI

## [1.11.4] - 2025-12-29
- Fixes orchestrator tests and adds a ci test pipeline for it

## [1.11.3] - 2025-12-29
- Fix system prompt with priority rule

## [1.11.2] - 2025-12-18
- Improve bullet style for tool call message logs (for consistency)

## [1.11.1] - 2025-12-11
- Improving support for forced tool call for Qwen models

## [1.11.0] - 2025-12-11
- Add support for forced tool call for Qwen models

## [1.10.0] - 2025-12-08
- Upgrading swot tool

## [1.9.0] - 2025-12-05
- Add support for planning before every loop iteration

## [1.8.2] - 2025-12-04
- Fix logging tool calls when tool takes over control

## [1.8.1] - 2025-12-03
- Logging tool calls when tool takes over control

## [1.8.0] - 2025-12-02
- Add option to upload code interpreter generated files to the chat.

## [1.7.19] - 2025-12-01
- Systemprompt formatting update

## [1.7.18] - 2025-11-27
- Improvement of message log service to indicate number of tool calls per loop iteration

## [1.7.17] - 2025-11-27
- Fixed an issue where the orchestrator failed when the number of tool calls exceeded the maximum allowed as defined in the configuration.
- Increased default value of max parallel tool calls from 5 to 15

## [1.7.16] - 2025-11-26
- Removing log of Deep Research tool call while keeping messages generated within the Deep Research call

## [1.7.15] - 2025-11-24 
- Streamlining message log service for listing tools and being compatible with SWOT and DeepSearch

## [1.7.14] - 2025-11-20
- Add message log service

## [1.7.13] - 2025-11-20
- Fix bug of handling properly uploaded files that are expired

## [1.7.12] - 2025-11-19
- Bump Swot tool

## [1.7.11] - 2025-11-17
- Fix bug where forcing a tool still sends builtin tools to the LLM when using the responses api.

## [1.7.10] - 2025-11-14
- Move pytest to dev dependencies

## [1.7.9] - 2025-11-12
- Fix bug where Responses API config was not properly validated

## [1.7.8] - 2025-11-11
- Better display of Responses API config in the UI

## [1.7.7] - 2025-11-10
- Remove direct azure client config from responses api config
- Organize Responses API config better

## [1.7.6] - 2025-11-05
- Update default system prompt (including user metadata section)

## [1.7.5] - 2025-11-05
- Adding functionality to include user metadata into user/system prompts of the orchestrator

## [1.7.4] - 2025-11-04
- Update and adapt to toolkit 1.23.0 (refactor sub agents implementation)

## [1.7.3] - 2025-11-03
- Fixed an issue where new assistant messages were not properly generated during streaming outputs with tool calls; the orchestrator now correctly creates messages via `_create_new_assistant_message_if_loop_response_contains_content` when loop_response includes text and tool invocations.

## [1.7.2] - 2025-11-03
- Add Swot tool to the orchestrator

## [1.7.1] - 2025-10-30
- Fixing that system format info is only appended to system prompt if tool is called

## [1.7.0] - 2025-10-30
- Add option to customize the display of tool progress statuses.
- Make follow-questions postprocessor run last to make sure the follow up questions are displayed last.

## [1.6.1] - 2025-10-28
- Removing unused experimental config `full_sources_serialize_dump` in `history_manager`

## [1.6.0] - 2025-10-27
- Add temporary config option `sleep_time_before_update` to avoid rendering issues with sub agent responses`

## [1.5.2] - 2025-10-23
- Run evaluation and post processing in parallel

## [1.5.1] - 2025-10-17
- revert behavior of unique ai upload and chat to 
1. Add upload and chat tool to forced tools if there are tool choices
2. Simply force it if there are no tool choices.
3. Tool not available when no uploaded documents

## [1.5.0] - 2025-10-16
- Make code interpreter configurable through spaces 2.0.

## [1.4.3] - 2025-10-16
- Fix issue with openai base url

## [1.4.2] - 2025-10-16
- Update debug info for better tool call tracking

## [1.4.1] - 2025-10-16
- Temporarily make open ai env vars configurable

## [1.4.0] - 2025-10-14
- Add responses api and code execution support.

## [1.3.0] - 2025-10-14
- Re-organize sub-agents configuration for clarity.

## [1.2.4] - 2025-10-14
- Let control taking tool itself set the message state to completed

## [1.2.3] - 2025-10-13
- Fix bug where follow-up questions were being generated even if the number of questions is set to 0 in the config.

## [1.2.2] - 2025-10-09
- update loading path of `DEFAULT_GPT_4o` from `unique_toolkit`

## [1.2.1] - 2025-10-07
- upgrade to deep research 3.0.0

## [1.2.0] - 2025-10-07
- Add sub agent response referencing.

## [1.1.1] - 2025-10-03
- Adapt orchestrator to toolkit 1.8.0.

## [1.1.0] - 2025-09-29
- Add ability to display sub agent's answers in main agent.
- Add ability to consolidate sub agent's assessment's in main agent.

## [1.0.3] - 2025-09-29
- fix UniqueAI system prompt for not activated tools
- updated README

## [1.0.2] - 2025-09-29
- updated deep-research to v2

## [1.0.1] - 2025-09-18
- updated toolkit

## [1.0.0] - 2025-09-18
- Bump toolkit version to allow for both patch and minor updates 

## [0.0.4] - 2025-09-17
- Updated to latest toolkit

## [0.0.3] - 2025-09-16
- Cleaned configuration

## [0.0.2] - 2025-09-15
- Resolve dependency bug

## [0.0.1] - 2025-08-18
- Initial release of `orchestrator`.
