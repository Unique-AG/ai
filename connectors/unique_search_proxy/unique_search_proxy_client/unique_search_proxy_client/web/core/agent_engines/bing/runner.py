from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import AsyncIterator

import openai
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (
    BingGroundingSearchConfiguration,
    BingGroundingSearchToolParameters,
    BingGroundingTool,
    PromptAgentDefinition,
)
from openai.types.responses import ResponseStreamEvent
from openai.types.responses.response_completed_event import ResponseCompletedEvent
from openai.types.responses.response_output_item_done_event import (
    ResponseOutputItemDoneEvent,
)
from openai.types.responses.response_output_message import ResponseOutputMessage
from openai.types.responses.response_output_text import (
    AnnotationURLCitation,
    ResponseOutputText,
)
from openai.types.responses.response_text_delta_event import ResponseTextDeltaEvent

from unique_search_proxy_client.web.core.agent_engines.bing.client import (
    get_openai_client,
)
from unique_search_proxy_client.web.settings.providers import bing_agent as settings
from unique_search_proxy_client.web.settings.secret_str import NOT_PROVIDED, read_secret

_LOGGER = logging.getLogger(__name__)
BING_AUTO_AGENT_NAME_PREFIX = "unique-grounding-with-bing"
_CONFIG_HASH_LENGTH = 12


def _config_hash(*, model: str, fetch_size: int, instructions: str) -> str:
    """Return a short hex digest of model + fetch_size + instructions for agent naming."""
    payload = f"{model}\0{fetch_size}\0{instructions}".encode()
    return hashlib.sha256(payload).hexdigest()[:_CONFIG_HASH_LENGTH]


def _agent_name_for_config(*, model: str, fetch_size: int, instructions: str) -> str:
    """Build a Foundry-safe agent name unique to this config."""
    return (
        f"{BING_AUTO_AGENT_NAME_PREFIX}-"
        f"{_config_hash(model=model, fetch_size=fetch_size, instructions=instructions)}"
    )


def resolve_bing_agent_name(
    *,
    model: str,
    fetch_size: int,
    instructions: str,
    agent_name: str | None = None,
) -> str:
    """Return the agent name to use for Responses (no Foundry round-trip)."""
    if agent_name:
        return agent_name
    return _agent_name_for_config(
        model=model, fetch_size=fetch_size, instructions=instructions
    )


def get_bing_grounding_tool(fetch_size: int) -> BingGroundingTool:
    connection_id = read_secret(
        settings.bing_agent_credentials.bing_resource_connection_string,
    )
    if not connection_id or connection_id == NOT_PROVIDED:
        msg = "Bing agent resource connection string is not configured"
        raise ValueError(msg)
    return BingGroundingTool(
        bing_grounding=BingGroundingSearchToolParameters(
            search_configurations=[
                BingGroundingSearchConfiguration(
                    project_connection_id=connection_id,
                    count=fetch_size,
                )
            ]
        )
    )


async def create_bing_agent(
    project_client: AIProjectClient,
    *,
    agent_name: str,
    model: str,
    fetch_size: int,
    instructions: str,
) -> str:
    """Create a Foundry agent version and return its name."""
    started = time.perf_counter()
    agent = await project_client.agents.create_version(
        agent_name=agent_name,
        definition=PromptAgentDefinition(
            model=model,
            instructions=instructions,
            tools=[get_bing_grounding_tool(fetch_size)],
            tool_choice="required",
        ),
        description="Unique Bing grounding agent",
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    _LOGGER.info(
        "Created Bing grounding agent version %s (id=%s) in %.0fms",
        agent.name,
        agent.id,
        elapsed_ms,
    )
    return agent.name


def _is_missing_agent_error(exc: BaseException, *, agent_name: str) -> bool:
    """Return True when Responses failed because the agent does not exist."""
    status_code = getattr(exc, "status_code", None)
    message = str(exc).lower()
    name_lower = agent_name.lower()

    if isinstance(exc, openai.NotFoundError) or status_code == 404:
        return True

    missing_markers = (
        "not found",
        "does not exist",
        "unknown agent",
        "agent_not_found",
        "no agent",
    )
    if any(marker in message for marker in missing_markers) and name_lower in message:
        return True
    if status_code in {400, 404} and any(
        marker in message for marker in missing_markers
    ):
        return True
    return False


async def stream_bing_grounding_agent(
    project_client: AIProjectClient,
    *,
    query: str,
    model: str,
    fetch_size: int,
    instructions: str,
    agent_name: str | None = None,
) -> AsyncIterator[tuple[str, dict]]:
    """Stream Bing-grounded Responses events as ``(delta_text, raw_event)`` pairs.

    Optimistically calls Responses with a hashed (or preconfigured) agent name.
    If the agent is missing and the name was auto-derived, creates the agent once
    and retries. Preconfigured agent names are never auto-created.

    Instructions must already be baked into the agent version — Foundry returns
    ``invalid_payload`` if ``instructions`` is passed alongside ``agent_reference``.
    """
    # Treat empty string like unset so auto-provisioning still works.
    preconfigured = agent_name or None
    resolved_name = resolve_bing_agent_name(
        model=model,
        fetch_size=fetch_size,
        instructions=instructions,
        agent_name=preconfigured,
    )
    allow_create = preconfigured is None
    openai_client = get_openai_client(project_client)

    try:
        stream = await _create_responses_stream(
            openai_client,
            agent_name=resolved_name,
            query=query,
        )
    except Exception as exc:
        if not allow_create or not _is_missing_agent_error(
            exc, agent_name=resolved_name
        ):
            raise
        _LOGGER.info(
            "Responses failed for missing Bing agent %s; creating then retrying: %s",
            resolved_name,
            exc,
        )
        await create_bing_agent(
            project_client,
            agent_name=resolved_name,
            model=model,
            fetch_size=fetch_size,
            instructions=instructions,
        )
        stream = await _create_responses_stream(
            openai_client,
            agent_name=resolved_name,
            query=query,
        )

    emitted_text = False
    async with stream:
        async for event in stream:
            if isinstance(event, ResponseTextDeltaEvent):
                if event.delta:
                    emitted_text = True
                    yield event.delta, event.model_dump(mode="json", warnings="none")
            elif isinstance(event, ResponseOutputItemDoneEvent):
                citations = _extract_url_citations(event)
                if citations:
                    yield (
                        "",
                        {
                            "type": event.type,
                            "citations": citations,
                            "event": event.model_dump(mode="json", warnings="none"),
                        },
                    )
            elif isinstance(event, ResponseCompletedEvent):
                response = event.response
                output_text = response.output_text
                raw_completed = {
                    "type": event.type,
                    "response": response.model_dump(mode="json", warnings="none"),
                }
                # Foundry sometimes delivers the full answer only on completion.
                if output_text and not emitted_text:
                    emitted_text = True
                    yield output_text, raw_completed
                else:
                    yield "", raw_completed


async def _create_responses_stream(
    openai_client: openai.AsyncOpenAI,
    *,
    agent_name: str,
    query: str,
) -> openai.AsyncStream[ResponseStreamEvent]:
    started = time.perf_counter()
    stream = await openai_client.responses.create(
        stream=True,
        input=query,
        extra_body={
            "agent_reference": {
                "name": agent_name,
                "type": "agent_reference",
            }
        },
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    _LOGGER.info(
        "Opened Bing Responses stream for agent %s in %.0fms",
        agent_name,
        elapsed_ms,
    )
    return stream


def _extract_url_citations(event: ResponseOutputItemDoneEvent) -> list[str]:
    item = event.item
    if not isinstance(item, ResponseOutputMessage) or not item.content:
        return []
    text_content = item.content[-1]
    if not isinstance(text_content, ResponseOutputText):
        return []
    return [
        annotation.url
        for annotation in text_content.annotations
        if isinstance(annotation, AnnotationURLCitation) and annotation.url
    ]
