from __future__ import annotations

import logging
from typing import Any

from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    MessageTextContent,
    RunStatus,
    ThreadMessageOptions,
)
from azure.ai.agents.models._patch import BingGroundingTool
from azure.ai.projects.aio import AIProjectClient
from pydantic import BaseModel

from unique_search_proxy_client.web.core.agent_engines.serialization import (
    json_safe_sdk_object,
)
from unique_search_proxy_client.web.core.agent_engines.structured_output import (
    build_agent_instructions,
)
from unique_search_proxy_client.web.settings.providers import bing_agent as settings
from unique_search_proxy_client.web.settings.secret_str import NOT_PROVIDED, read_secret

_LOGGER = logging.getLogger(__name__)
_AGENT_NAME_IDENTIFIER = "UNIQUE_GROUNDING_WITH_BING_AGENT"


async def _get_agent_id(agent_client: AIProjectClient) -> str:
    list_agents = agent_client.agents.list_agents()
    async for agent in list_agents:
        if agent.name == _AGENT_NAME_IDENTIFIER:
            return agent.id
    msg = f"Agent {_AGENT_NAME_IDENTIFIER} not found"
    raise ValueError(msg)


async def _create_agent_id(agent_client: AIProjectClient) -> str:
    creds = settings.bing_agent_credentials
    agent = await agent_client.agents.create_agent(
        name=_AGENT_NAME_IDENTIFIER,
        model=read_secret(creds.bing_agent_model),
    )
    return agent.id


async def get_or_create_agent_id(agent_client: AIProjectClient) -> str:
    creds = settings.bing_agent_credentials
    if creds.agent_id:
        return creds.agent_id
    try:
        return await _get_agent_id(agent_client)
    except Exception:
        _LOGGER.info("No existing Bing grounding agent found; creating one")
        return await _create_agent_id(agent_client)


def get_bing_grounding_tool(fetch_size: int) -> BingGroundingTool:
    connection_id = read_secret(
        settings.bing_agent_credentials.bing_resource_connection_string,
    )
    if not connection_id or connection_id == NOT_PROVIDED:
        msg = "Bing agent resource connection string is not configured"
        raise ValueError(msg)
    return BingGroundingTool(connection_id=connection_id, count=fetch_size)


async def run_bing_grounding_agent(
    agent_client: AIProjectClient,
    *,
    agent_id: str | None,
    query: str,
    fetch_size: int,
    generation_instructions: str,
    output_schema: type[BaseModel],
) -> tuple[str, Any]:
    """Execute a Bing-grounded agent run and return answer text + raw payload."""
    instructions = build_agent_instructions(
        generation_instructions=generation_instructions,
        output_schema=output_schema,
    )
    if not agent_id:
        agent_run = await _create_agent_and_run_thread(
            agent_client,
            query=query,
            fetch_size=fetch_size,
            instructions=instructions,
        )
    else:
        agent_run = await _create_agent_run_with_agent_id(
            agent_client,
            agent_id=agent_id,
            query=query,
        )

    if agent_run.status in {RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.EXPIRED}:
        msg = f"Bing agent run failed: {agent_run.last_error}"
        raise RuntimeError(msg)

    answer, messages_raw = await _extract_answer_from_thread(
        agent_run.thread_id,
        agent_client,
    )
    raw: dict[str, Any] = {
        "run": _serialize_sdk_object(agent_run),
        "messages": messages_raw,
    }
    return answer, raw


async def _create_agent_run_with_agent_id(
    agent_client: AIProjectClient,
    *,
    agent_id: str,
    query: str,
):
    return await agent_client.agents.create_thread_and_process_run(
        agent_id=agent_id,
        thread=AgentThreadCreationOptions(
            messages=[ThreadMessageOptions(role="user", content=query)],
        ),
    )


async def _create_agent_and_run_thread(
    agent_client: AIProjectClient,
    *,
    query: str,
    fetch_size: int,
    instructions: str,
):
    creds = settings.bing_agent_credentials
    resolved_agent_id = await get_or_create_agent_id(agent_client)
    return await agent_client.agents.create_thread_and_process_run(
        agent_id=resolved_agent_id,
        model=read_secret(creds.bing_agent_model),
        toolset=get_bing_grounding_tool(fetch_size=fetch_size),  # type: ignore[arg-type]
        instructions=instructions,
        thread=AgentThreadCreationOptions(
            messages=[ThreadMessageOptions(role="user", content=query)],
        ),
    )


async def _extract_answer_from_thread(
    thread_id: str,
    agent_client: AIProjectClient,
) -> tuple[str, list[dict[str, Any]]]:
    messages = agent_client.agents.messages.list(thread_id=thread_id)
    answer_parts: list[str] = []
    messages_raw: list[dict[str, Any]] = []

    async for message in messages:
        message_dict = _serialize_sdk_object(message)
        messages_raw.append(message_dict)
        if message.role != "assistant":
            continue
        for content in message.content:
            if isinstance(content, MessageTextContent):
                answer_parts.append(content.text.value)

    return "".join(answer_parts), messages_raw


def _serialize_sdk_object(value: Any) -> Any:
    return json_safe_sdk_object(value)
