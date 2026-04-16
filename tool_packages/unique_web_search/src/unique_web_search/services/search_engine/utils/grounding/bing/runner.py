import logging

from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    BingGroundingTool,
    MessageTextContent,
    MessageTextUrlCitationAnnotation,
    RunStatus,
    ThreadMessageOptions,
)
from azure.ai.projects.aio import AIProjectClient

from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.services.search_engine.utils.grounding import (
    ResponseParser,
    convert_response_to_search_results,
)
from unique_web_search.services.search_engine.utils.grounding.bing.models import (
    RESPONSE_RULE,
)
from unique_web_search.settings import env_settings

_LOGGER = logging.getLogger(__name__)
_AGENT_NAME_IDENTIFIER = "UNIQUE_GROUNDING_WITH_BING_AGENT"


# ---------------------------------------------------------------------------
# Agent management
# ---------------------------------------------------------------------------


async def _get_agent_id(agent_client: AIProjectClient) -> str:
    """Look up the existing Bing grounding agent by name.

    Raises:
        Exception: If no agent with the expected name exists.
    """
    list_agents = agent_client.agents.list_agents()

    async for agent in list_agents:
        if agent.name == _AGENT_NAME_IDENTIFIER:
            return agent.id

    raise Exception(f"Agent {_AGENT_NAME_IDENTIFIER} not found")


async def _create_agent_id(agent_client: AIProjectClient) -> str:
    """Provision a new Bing grounding agent using the configured model."""
    agent = await agent_client.agents.create_agent(
        name=_AGENT_NAME_IDENTIFIER,
        model=env_settings.azure_ai_bing_agent_model,
    )
    return agent.id


async def get_or_create_agent_id(agent_client: AIProjectClient) -> str:
    """Return the Bing grounding agent id, creating one if it doesn't exist yet."""
    if env_settings.azure_ai_assistant_id:
        return env_settings.azure_ai_assistant_id

    try:
        return await _get_agent_id(agent_client)
    except Exception as e:
        _LOGGER.exception(f"Error getting agent: {e}")
        return await _create_agent_id(agent_client)


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
    connection_id = env_settings.azure_ai_bing_resource_connection_string
    if not connection_id:
        raise ValueError("Azure AI Bing Resource Connection String is not set")
    return BingGroundingTool(connection_id=connection_id, count=fetch_size)


# ---------------------------------------------------------------------------
# Run orchestration
# ---------------------------------------------------------------------------


async def create_and_process_run(
    agent_client: AIProjectClient,
    agent_id: str,
    query: str,
    fetch_size: int,
    response_parsers_strategies: list[ResponseParser],
    generation_instructions: str,
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
    if not agent_id:
        _LOGGER.warning("No agent ID provided, creating a new agent")
        thread = await _create_agent_and_run_thread(
            agent_client, query, fetch_size, generation_instructions
        )
    else:
        _LOGGER.warning(f"Using existing agent ID: {agent_id}")
        thread = await _create_agent_run_with_agent_id(agent_client, agent_id, query)

    if thread.status in [RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.EXPIRED]:
        raise Exception(f"Run failed: {thread.last_error}")

    answer = await _get_answer_from_thread(thread.thread_id, agent_client)

    search_results = await convert_response_to_search_results(
        answer, response_parsers_strategies
    )

    return search_results


async def _create_agent_run_with_agent_id(
    agent_client: AIProjectClient,
    agent_id: str,
    query: str,
):
    """Execute a Bing-grounded agent run and return parsed search results."""
    agent_run = await agent_client.agents.create_thread_and_process_run(
        agent_id=agent_id,
        thread=AgentThreadCreationOptions(
            messages=[ThreadMessageOptions(role="user", content=query)]
        ),
    )
    return agent_run


async def _create_agent_and_run_thread(
    agent_client: AIProjectClient,
    query: str,
    fetch_size: int,
    generation_instructions: str,
):
    agent_id = await get_or_create_agent_id(agent_client)

    instructions = f"{generation_instructions}\n{RESPONSE_RULE}"

    agent_run = await agent_client.agents.create_thread_and_process_run(
        agent_id=agent_id,
        model=env_settings.azure_ai_bing_agent_model,
        toolset=get_bing_grounding_tool(fetch_size=fetch_size),  # type: ignore
        instructions=instructions,
        thread=AgentThreadCreationOptions(
            messages=[ThreadMessageOptions(role="user", content=query)]
        ),
    )
    return agent_run


async def _get_answer_from_thread(thread_id: str, agent_client: AIProjectClient) -> str:
    """Concatenate all assistant text messages from a thread into a single string."""
    messages = agent_client.agents.messages.list(thread_id=thread_id)
    answer = ""
    citations: list[MessageTextUrlCitationAnnotation] = []

    async for message in messages:
        if message.role == "assistant":
            for content in message.content:
                if isinstance(content, MessageTextContent):
                    answer += content.text.value
                elif isinstance(content, MessageTextUrlCitationAnnotation):
                    citations.append(content)

    for citation in citations:
        answer = answer.replace(
            citation.text,
            f"[{citation.url_citation.title}]({citation.url_citation.url})",
        )

    return answer
