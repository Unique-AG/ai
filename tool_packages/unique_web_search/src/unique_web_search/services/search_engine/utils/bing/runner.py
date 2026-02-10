import logging
import re

from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    BingGroundingTool,
    MessageTextContent,
    RunStatus,
    ThreadMessageOptions,
)
from azure.ai.projects import AIProjectClient

from unique_web_search.services.search_engine.schema import WebSearchResult
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
    list_agents = agent_client.agents.list_agents()

    for agent in list_agents:
        if agent.name == _AGENT_NAME_IDENTIFIER:
            return agent.id

    raise Exception(f"Agent {_AGENT_NAME_IDENTIFIER} not found")


def _create_agent_id(agent_client: AIProjectClient) -> str:
    agent = agent_client.agents.create_agent(
        name=_AGENT_NAME_IDENTIFIER,
        model=env_settings.azure_ai_bing_agent_model,
    )
    return agent.id


def get_or_create_agent_id(agent_client: AIProjectClient) -> str:
    try:
        return _get_agent_id(agent_client)
    except Exception as e:
        _LOGGER.error(f"Error getting agent: {e}")
        return _create_agent_id(agent_client)


# ---------------------------------------------------------------------------
# Bing grounding tool
# ---------------------------------------------------------------------------


def get_bing_grounding_tool(fetch_size: int) -> BingGroundingTool:
    connection_id = env_settings.azure_ai_bing_ressource_connection_string
    if not connection_id:
        raise ValueError("Azure AI Bing Resource Connection String is not set")
    return BingGroundingTool(connection_id=connection_id, count=fetch_size)


# ---------------------------------------------------------------------------
# Run orchestration
# ---------------------------------------------------------------------------


def create_and_process_run(
    agent_client: AIProjectClient, query: str, fetch_size: int
) -> list[WebSearchResult]:
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

    search_results = _convert_response_to_search_results(answer)

    return search_results


def _get_answer_from_thread(thread_id: str, agent_client: AIProjectClient):
    messages = agent_client.agents.messages.list(thread_id=thread_id)
    answer = ""
    for message in messages:
        if message.role == "assistant":
            for content in message.content:
                if isinstance(content, MessageTextContent):
                    answer += content.text.value
    return answer


def _convert_response_to_search_results(response: str) -> list[WebSearchResult]:
    try:
        json_match = _JSON_PATTERN.search(response)
        if not json_match:
            raise ValueError("No JSON found in the response")
        return GroundingWithBingResults.model_validate_json(
            json_match.group(1)
        ).to_web_search_results()
    except Exception as e:
        raise ValueError(f"Error converting response to search results: {e}")
