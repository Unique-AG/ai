# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
