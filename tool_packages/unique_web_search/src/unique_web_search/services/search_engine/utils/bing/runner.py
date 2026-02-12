import logging
import re
from typing import Protocol

from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    BingGroundingTool,
    MessageTextContent,
    RunStatus,
    ThreadMessageOptions,
)
from azure.ai.projects import AIProjectClient
from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.language_model.service import LanguageModelService

from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
    WebSearchResults,
)
from unique_web_search.services.search_engine.utils.bing.models import (
    GENERATION_INSTRUCTIONS,
    GroundingWithBingResults,
)
from unique_web_search.settings import env_settings

_LOGGER = logging.getLogger(__name__)
_AGENT_NAME_IDENTIFIER = "GROUNDING_WITH_BING_AGENT"
_JSON_PATTERN = re.compile(r"```json\s*([\s\S]*?)\s*```")


# ---------------------------------------------------------------------------
# Agent management
# ---------------------------------------------------------------------------


def _get_agent_id(agent_client: AIProjectClient) -> str:
    """Look up the existing Bing grounding agent by name.

    Raises:
        Exception: If no agent with the expected name exists.
    """
    list_agents = agent_client.agents.list_agents()

    for agent in list_agents:
        if agent.name == _AGENT_NAME_IDENTIFIER:
            return agent.id

    raise Exception(f"Agent {_AGENT_NAME_IDENTIFIER} not found")


def _create_agent_id(agent_client: AIProjectClient) -> str:
    """Provision a new Bing grounding agent using the configured model."""
    agent = agent_client.agents.create_agent(
        name=_AGENT_NAME_IDENTIFIER,
        model=env_settings.azure_ai_bing_agent_model,
    )
    return agent.id


def get_or_create_agent_id(agent_client: AIProjectClient) -> str:
    """Return the Bing grounding agent id, creating one if it doesn't exist yet."""
    try:
        return _get_agent_id(agent_client)
    except Exception as e:
        _LOGGER.exception(f"Error getting agent: {e}")
        return _create_agent_id(agent_client)


# ---------------------------------------------------------------------------
# Bing grounding tool
# ---------------------------------------------------------------------------


def get_bing_grounding_tool(fetch_size: int) -> BingGroundingTool:
    """Build a BingGroundingTool configured with the environment connection string.

    Args:
        fetch_size: Maximum number of search results the tool should return.

    Raises:
        ValueError: If the Bing resource connection string is not configured.
    """
    connection_id = env_settings.azure_ai_bing_ressource_connection_string
    if not connection_id:
        raise ValueError("Azure AI Bing Resource Connection String is not set")
    return BingGroundingTool(connection_id=connection_id, count=fetch_size)


# ---------------------------------------------------------------------------
# Run orchestration
# ---------------------------------------------------------------------------


class ResponseParser(Protocol):
    """Protocol for strategies that parse raw agent text into search results."""

    async def __call__(self, response: str) -> list[WebSearchResult]: ...


async def create_and_process_run(
    agent_client: AIProjectClient,
    query: str,
    fetch_size: int,
    response_parsers_strategies: list[ResponseParser],
) -> list[WebSearchResult]:
    """Execute a Bing-grounded agent run and return parsed search results.

    Creates a thread with the user query, runs the agent with Bing grounding,
    then converts the unstructured response into ``WebSearchResult`` objects by
    trying each parser strategy in order until one succeeds.

    Args:
        agent_client: Azure AI project client used to manage agents and threads.
        query: The search query to send to the agent.
        fetch_size: Maximum number of Bing results the agent should retrieve.
        response_parsers_strategies: Ordered list of parsing strategies to try
            when converting the agent's free-text response into structured results.

    Raises:
        Exception: If the agent run fails, is cancelled, or expires.
        ValueError: If none of the parser strategies can parse the response.
    """
    agent_id = get_or_create_agent_id(agent_client)

    agent_run = agent_client.agents.create_thread_and_process_run(
        agent_id=agent_id,
        model=env_settings.azure_ai_bing_agent_model,
        toolset=get_bing_grounding_tool(fetch_size=fetch_size),  # type: ignore
        instructions=GENERATION_INSTRUCTIONS,
        thread=AgentThreadCreationOptions(
            messages=[ThreadMessageOptions(role="user", content=query)]
        ),
    )

    if agent_run.status in [RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.EXPIRED]:
        raise Exception(f"Run failed: {agent_run.last_error}")

    answer = _get_answer_from_thread(agent_run.thread_id, agent_client)

    search_results = await _convert_response_to_search_results(
        answer, response_parsers_strategies
    )

    return search_results


def _get_answer_from_thread(thread_id: str, agent_client: AIProjectClient) -> str:
    """Concatenate all assistant text messages from a thread into a single string."""
    messages = agent_client.agents.messages.list(thread_id=thread_id)
    answer = ""
    for message in messages:
        if message.role == "assistant":
            for content in message.content:
                if isinstance(content, MessageTextContent):
                    answer += content.text.value
    return answer


async def _convert_response_to_search_results(
    response: str, conversion_strategies: list[ResponseParser]
) -> list[WebSearchResult]:
    """Try each conversion strategy in order until one parses the response.

    Strategies are attempted sequentially; the first successful result is
    returned. Failures are logged and the next strategy is tried.

    Args:
        response: Raw text response from the Bing grounding agent.
        conversion_strategies: Ordered list of parsers to attempt.

    Raises:
        ValueError: If every strategy fails to parse the response.
    """
    for strategy in conversion_strategies:
        try:
            return await strategy(response)
        except Exception as e:
            _LOGGER.exception(f"Error converting response to search results: {e}")
            continue
    raise ValueError("No conversion strategy found for the response")


class JsonConversionStrategy(ResponseParser):
    """Extract a fenced JSON block from the response and validate it directly.

    Expects the agent to have returned a ``GroundingWithBingResults``-shaped
    JSON object wrapped in a ``` ```json ... ``` ``` code fence.

    Raises:
        ValueError: If no JSON code fence is found in the response.
    """

    async def __call__(self, response: str) -> list[WebSearchResult]:
        json_match = _JSON_PATTERN.search(response)
        if not json_match:
            raise ValueError("No JSON found in the response")
        return GroundingWithBingResults.model_validate_json(
            json_match.group(1)
        ).to_web_search_results()


class LLMParserStrategy(ResponseParser):
    """Fallback parser that uses an LLM to convert free-text into structured results.

    Sends the raw response to a language model with structured-output enforcement
    so it returns a validated ``WebSearchResults`` object. Useful when the agent
    response doesn't contain a parseable JSON code fence.

    Args:
        llm: Language model identifier to use for the conversion call.
        llm_service: Service used to invoke the language model.

    Raises:
        ValueError: If the LLM response does not contain a valid parsed result.
    """

    def __init__(self, llm: LMI, llm_service: LanguageModelService):
        self.llm = llm
        self.llm_service = llm_service

    async def __call__(self, response: str) -> list[WebSearchResult]:
        system_prompt = """You are a helpful assistant that converts an non-structured response to a structured response."""
        user_prompt = f"""The response is: {response}"""
        messages = (
            MessagesBuilder()
            .system_message_append(system_prompt)
            .user_message_append(user_prompt)
            .build()
        )
        llm_response = await self.llm_service.complete_async(
            messages=messages,
            model_name=self.llm.name,
            structured_output_model=WebSearchResults,
            structured_output_enforce_schema=True,
        )

        if not llm_response.choices[0].message.parsed:
            raise ValueError("No JSON found in the response")

        return WebSearchResults.model_validate(
            llm_response.choices[0].message.parsed
        ).results
