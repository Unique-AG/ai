from __future__ import annotations

import hashlib
import logging
import time

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

from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.services.search_engine.utils.grounding import (
    ResponseParser,
    convert_response_to_search_results,
)
from unique_web_search.services.search_engine.utils.grounding.bing.client import (
    get_openai_client,
)
from unique_web_search.services.search_engine.utils.grounding.bing.models import (
    RESPONSE_RULE,
)
from unique_web_search.settings import env_settings

_LOGGER = logging.getLogger(__name__)
BING_AUTO_AGENT_NAME_PREFIX = "unique-grounding-with-bing"
_CONFIG_HASH_LENGTH = 12


# ---------------------------------------------------------------------------
# Agent naming
# ---------------------------------------------------------------------------


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
    """Return the agent name to use for Responses (no Foundry round-trip).

    Prefers an explicit / env-preconfigured name; otherwise derives a stable
    hash-based name from ``model`` + ``fetch_size`` + ``instructions``.
    """
    resolved = agent_name or env_settings.azure_ai_assistant_id or None
    if resolved:
        return resolved
    return _agent_name_for_config(
        model=model, fetch_size=fetch_size, instructions=instructions
    )


async def create_bing_agent(
    agent_client: AIProjectClient,
    *,
    agent_name: str,
    model: str,
    fetch_size: int,
    instructions: str,
) -> str:
    """Create a Foundry agent version and return its name."""
    started = time.perf_counter()
    agent = await agent_client.agents.create_version(
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


async def get_or_create_agent_id(agent_client: AIProjectClient) -> str:
    """Compatibility wrapper: return the resolved Bing grounding agent name.

    Does not call Foundry. Creation happens lazily on Responses miss.
    """
    del agent_client  # kept for call-site compatibility
    return resolve_bing_agent_name(
        model=env_settings.azure_ai_bing_agent_model,
        fetch_size=5,
        instructions=RESPONSE_RULE,
    )


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


# ---------------------------------------------------------------------------
# Run orchestration
# ---------------------------------------------------------------------------


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


async def create_and_process_run(
    agent_client: AIProjectClient,
    agent_id: str,
    query: str,
    fetch_size: int,
    response_parsers_strategies: list[ResponseParser],
    generation_instructions: str,
) -> list[WebSearchResult]:
    """Execute a Bing-grounded agent run and return parsed search results.

    Optimistically calls Responses with a hashed (or preconfigured) agent name.
    If the agent is missing and the name was auto-derived, creates the agent once
    and retries. Preconfigured agent names are never auto-created.

    Args:
        agent_client: Azure AI project client used to manage agents.
        agent_id: Optional Foundry agent name; empty triggers hash-based naming.
        query: The search query to send to the agent.
        fetch_size: Maximum number of Bing results the agent should retrieve.
        response_parsers_strategies: Ordered list of parsing strategies to try
            when converting the agent's free-text response into structured results.
        generation_instructions: Per-request system instructions for the agent.

    Raises:
        Exception: If the agent run fails.
        ValueError: If none of the parser strategies can parse the response.
    """
    instructions = f"{generation_instructions}\n{RESPONSE_RULE}"
    model = env_settings.azure_ai_bing_agent_model
    preconfigured = agent_id or env_settings.azure_ai_assistant_id or None
    answer = await _run_responses_agent(
        agent_client,
        query=query,
        model=model,
        fetch_size=fetch_size,
        instructions=instructions,
        agent_name=preconfigured,
    )

    return await convert_response_to_search_results(answer, response_parsers_strategies)


async def _run_responses_agent(
    agent_client: AIProjectClient,
    *,
    query: str,
    model: str,
    fetch_size: int,
    instructions: str,
    agent_name: str | None = None,
) -> str:
    """Invoke the agent via Responses API and return the full output text.

    Instructions must already be baked into the agent version — Foundry returns
    ``invalid_payload`` if ``instructions`` is passed alongside ``agent_reference``.
    """
    # Treat empty string like unset so auto-provisioning still works.
    # Env assistant id is also preconfigured (same as resolve_bing_agent_name).
    preconfigured = agent_name or env_settings.azure_ai_assistant_id or None
    resolved_name = resolve_bing_agent_name(
        model=model,
        fetch_size=fetch_size,
        instructions=instructions,
        agent_name=preconfigured,
    )
    allow_create = preconfigured is None
    openai_client = get_openai_client(agent_client)

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
            agent_client,
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

    answer_parts: list[str] = []
    citation_replacements: list[tuple[str, str]] = []
    emitted_text = False

    async for event in stream:
        if isinstance(event, ResponseTextDeltaEvent):
            if event.delta:
                emitted_text = True
                answer_parts.append(event.delta)
        elif isinstance(event, ResponseOutputItemDoneEvent):
            citation_replacements.extend(_extract_markdown_citations(event))
        elif isinstance(event, ResponseCompletedEvent):
            output_text = event.response.output_text
            # Foundry sometimes delivers the full answer only on completion.
            if output_text and not emitted_text:
                emitted_text = True
                answer_parts.append(output_text)

    answer = "".join(answer_parts)
    for marker, markdown_link in citation_replacements:
        answer = answer.replace(marker, markdown_link)
    return answer


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


def _extract_markdown_citations(
    event: ResponseOutputItemDoneEvent,
) -> list[tuple[str, str]]:
    """Extract (placeholder, markdown-link) pairs from a message output item."""
    item = event.item
    if not isinstance(item, ResponseOutputMessage) or not item.content:
        return []
    text_content = item.content[-1]
    if not isinstance(text_content, ResponseOutputText):
        return []

    replacements: list[tuple[str, str]] = []
    for annotation in text_content.annotations:
        if not isinstance(annotation, AnnotationURLCitation):
            continue
        marker = text_content.text[annotation.start_index : annotation.end_index]
        title = annotation.title or annotation.url
        if annotation.url and marker:
            replacements.append((marker, f"[{title}]({annotation.url})"))
    return replacements
