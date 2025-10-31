# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.10] - 2025-10-31
- Make agent aware of limitation in data access
- Apply metadata filter to agent

## [3.0.9] - 2025-10-31
- Clear original response message when starting new run
- Forced tool calls fix for setting research completed at max iterations
- Reduce web search results returned to 10 to reduce api load

## [3.0.8] - 2025-10-29
- Include DeepResearch Bench results

## [3.0.7] - 2025-10-28
- Removing unused tool specific `get_tool_call_result_for_loop_history` function

## [3.0.6] - 2025-10-20
- Include find on website events in message log

## [3.0.5] - 2025-10-17
- Add all reviewed sources to message log

## [3.0.4] - 2025-10-14
- Fix ordering issue of messages in unique implementation with too early cleanup
- Don't include the visited websites without a nice title in message log

## [3.0.3] - 2025-10-13
- Fix potential error in open website logic if response not defined
- Better token limit handeling
- Internal knowledge base page referencing

## [3.0.2] - 2025-10-10
- Get website title for OpenAI agent
- Bolding of message logs
- Clarifying questions and research brief dependent on engine type

## [3.0.1] - 2025-10-08
- Improved citation logic supporting internal search documents
- Fixed bug in referencing of internal sources not giving the correct title of sources
- OpenAI engine converted to async processing to not be blocking
- Prompt improvements
- Small changes to message logs
- Improve success rate of website title extraction
- Web_fetch tool improvements on error handeling for llm

## [3.0.0] - 2025-10-07
- Simplification and better descriptions of configuration
- Dynamic tool descriptions and improved prompts
- Reduce OpenAI engine logging 

## [2.1.3] - 2025-10-06
- Error handeling on context window limits

## [2.1.2] - 2025-10-02
- Remove temperature param to allow for more models used in unique custom
- Research prompt improvements
- Citation rendering improvements with extra llm call
- Additional logging for openai and custom agent

## [2.1.1] - 2025-10-01
- bugfix of langgraph state issue
- more logging

## [2.1.0] - 2025-10-01
Prompt improvements
- Pushing agent for deeper analysis and including tool descriptions

## [2.0.0] - 2025-09-26
Simplification, bugfixes, and performance improvements
- Improve lead and research agent prompts
- Simplify configuration of tool
- root try-catch for error handeling
- Prompt engineering on report writer prompt to ensure inline citations
- Simplify thinking messages
- Include url title for web_fetch

## [1.1.1] - 2025-09-23
Minor bugfixes:
- Message log entry at the completion of the report
- Improved instruction on followup questions to use numbered list instead of bullets
- Bugfix of internalsearch and internalfetch due to breaking change in toolkit
- Stronger citation requirements in prompt

## [1.1.0] - 2025-09-23
- Use streaming for followup questions and only a single iteration allowed
- Set default models to GPT 4o for followup and GPT 4.1 for research brief

## [1.0.0] - 2025-09-18
- Bump toolkit version to allow for both patch and minor updates

## [0.0.11] - 2025-09-17
- Updated to latest toolkit

## [0.0.10] - 2025-09-12
- Upgrade web search version

## [0.0.9] - 2025-09-11
- Bugfixes of statemanagement
- missing tool call handlers
- small performance improvements

## [0.0.8] - 2025-09-09
- Implement custom deep research logic using langgraph

## [0.0.7] - 2025-09-05
- Set message execution to completed
- Better error protection
- Formatting of final output report

## [0.0.6] - 2025-09-04
- Fix null pointer issue in web search action query handling

## [0.0.5] - 2025-09-04
- Additional messages in message log and add formatted messages in details

## [0.0.4] - 2025-09-02
- Introducing handover capability.

## [0.0.3] - 2025-09-03
- Bump toolkit version to get bugfix and small cleanup of getting client

## [0.0.2] - 2025-09-02
- Update standard config to use existing LMI objects

## [0.0.1] - 2025-09-01
- Initial release of `deep_research`