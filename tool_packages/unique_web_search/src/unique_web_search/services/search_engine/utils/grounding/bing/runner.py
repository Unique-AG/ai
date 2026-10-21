from __future__ import annotations

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
from openai.types.responses.response import Response
from openai.types.responses.response_completed_event import ResponseCompletedEvent
from openai.types.responses.response_output_message import ResponseOutputMessage
from openai.types.responses.response_output_text import (
    AnnotationURLCitation,
    ResponseOutputText,
)
from openai.types.responses.response_text_delta_event import ResponseTextDeltaEvent
from unique_search_proxy_core.agent_engines.bing.grounding import (
    BingGroundingConfiguration,
    bing_agent_name,
    build_bing_citation_instructions,
)
from unique_search_proxy_core.schema import GroundingCitation

from unique_web_search.invocation_stats import collector
from unique_web_search.services.search_engine.utils.grounding.bing.client import (
    get_openai_client,
)
from unique_web_search.services.search_engine.utils.grounding.bing.models import (
    RESPONSE_RULE,
)
from unique_web_search.settings import env_settings

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent naming
# ---------------------------------------------------------------------------


def resolve_bing_agent_name(
    *,
    model: str,
    instructions: str,
    grounding: BingGroundingConfiguration,
) -> str:
    """Return the hash-based agent name to use for Responses (no Foundry round-trip).

    Derives a stable name from everything baked into the agent version: the
    model, the instructions, and the Bing grounding tool configuration.
    """
    return bing_agent_name(
        model=model,
        instructions=instructions,
        grounding=grounding,
    )


async def create_bing_agent(
    agent_client: AIProjectClient,
    *,
    agent_name: str,
    model: str,
    instructions: str,
    grounding: BingGroundingConfiguration,
) -> str:
    """Create a Foundry agent version and return its name."""
    started = time.perf_counter()
    agent = await agent_client.agents.create_version(
        agent_name=agent_name,
        definition=PromptAgentDefinition(
            model=model,
            instructions=instructions,
            tools=[get_bing_grounding_tool(grounding)],
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
        instructions=RESPONSE_RULE,
        grounding=BingGroundingConfiguration(fetch_size=5),
    )


# ---------------------------------------------------------------------------
# Bing grounding tool
# ---------------------------------------------------------------------------


def get_bing_grounding_tool(
    grounding: BingGroundingConfiguration,
) -> BingGroundingTool:
    """Build a BingGroundingTool configured with the environment connection string.

    Args:
        grounding: Bing tool knobs; knobs left unset keep Bing's own defaults.

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
                    count=grounding.fetch_size,
                    market=grounding.market,
                    freshness=grounding.freshness,
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
    query: str,
    grounding: BingGroundingConfiguration,
    generation_instructions: str,
) -> tuple[str, list[GroundingCitation]]:
    """Execute a Bing-grounded agent run and return its answer and citations.

    Optimistically calls Responses with a hash-derived agent name. If the agent
    is missing, creates it once and retries.

    Args:
        agent_client: Azure AI project client used to manage agents.
        query: The search query to send to the agent.
        grounding: Bing tool knobs (result count, market, language, freshness).
        generation_instructions: Per-request system instructions for the agent.

    Returns:
        The answer text and its citations, with offsets into that text.

    Raises:
        Exception: If the agent run fails.
    """
    model = env_settings.azure_ai_bing_agent_model
    return await _run_responses_agent(
        agent_client,
        query=query,
        model=model,
        instructions=build_bing_citation_instructions(generation_instructions),
        grounding=grounding,
    )


async def _run_responses_agent(
    agent_client: AIProjectClient,
    *,
    query: str,
    model: str,
    instructions: str,
    grounding: BingGroundingConfiguration,
) -> tuple[str, list[GroundingCitation]]:
    """Invoke the agent via Responses API and return the full output text.

    Instructions must already be baked into the agent version — Foundry returns
    ``invalid_payload`` if ``instructions`` is passed alongside ``agent_reference``.
    Missing agents are auto-provisioned on first miss.
    """
    resolved_name = resolve_bing_agent_name(
        model=model,
        instructions=instructions,
        grounding=grounding,
    )
    openai_client = get_openai_client(agent_client)

    try:
        stream = await _create_responses_stream(
            openai_client,
            agent_name=resolved_name,
            query=query,
        )
    except Exception as exc:
        if not _is_missing_agent_error(exc, agent_name=resolved_name):
            raise
        _LOGGER.info(
            "Responses failed for missing Bing agent %s; creating then retrying: %s",
            resolved_name,
            exc,
        )
        try:
            await create_bing_agent(
                agent_client,
                agent_name=resolved_name,
                model=model,
                instructions=instructions,
                grounding=grounding,
            )
        except UnicodeDecodeError:
            # Foundry can persist the agent but return a compressed create response
            # that azure-core fails to decode. The Responses retry below verifies
            # whether creation actually succeeded.
            _LOGGER.warning(
                "Could not decode create response for Bing agent %s; "
                "verifying creation through Responses",
                resolved_name,
            )
        stream = await _create_responses_stream(
            openai_client,
            agent_name=resolved_name,
            query=query,
        )

    answer_parts: list[str] = []
    citations: list[GroundingCitation] = []
    completed_answer: str | None = None

    async with stream:
        async for event in stream:
            if isinstance(event, ResponseTextDeltaEvent):
                if event.delta:
                    answer_parts.append(event.delta)
            elif isinstance(event, ResponseCompletedEvent):
                completed_answer = event.response.output_text
                citations = _extract_response_url_citations(event.response)
                collector.record_token_usage(
                    model_name=model,
                    usage=event.response.usage,
                    source="web_search.grounding.bing",
                )

    answer = completed_answer if completed_answer is not None else "".join(answer_parts)
    return answer, citations


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


def _extract_message_url_citations(
    item: ResponseOutputMessage,
    *,
    start_index_offset: int = 0,
) -> list[GroundingCitation]:
    if not item.content:
        return []

    citations: list[GroundingCitation] = []
    text_offset = start_index_offset
    for text_content in item.content:
        if not isinstance(text_content, ResponseOutputText):
            continue
        for annotation in text_content.annotations or []:
            if not isinstance(annotation, AnnotationURLCitation):
                continue
            marker = text_content.text[annotation.start_index : annotation.end_index]
            if annotation.url and marker:
                citations.append(
                    GroundingCitation(
                        url=annotation.url,
                        title=annotation.title,
                        marker=marker,
                        start_index=text_offset + annotation.start_index,
                        end_index=text_offset + annotation.end_index,
                        output_item_id=item.id,
                    )
                )
        text_offset += len(text_content.text)
    return citations


def _extract_response_url_citations(
    response: Response,
) -> list[GroundingCitation]:
    """Extract citations with offsets into ``response.output_text``."""
    citations: list[GroundingCitation] = []
    text_offset = 0
    for item in response.output or []:
        if not isinstance(item, ResponseOutputMessage):
            continue
        citations.extend(
            _extract_message_url_citations(
                item,
                start_index_offset=text_offset,
            )
        )
        text_offset += sum(
            len(content.text)
            for content in item.content or []
            if isinstance(content, ResponseOutputText)
        )

    _LOGGER.info(
        "Foundry Bing citation annotations response_id=%s "
        "citation_count=%d citations=%s",
        response.id,
        len(citations),
        [citation.model_dump(mode="json", by_alias=True) for citation in citations],
    )
    return citations
