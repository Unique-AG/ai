from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Sequence
from typing import NamedTuple

import openai
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (
    BingGroundingSearchConfiguration,
    BingGroundingSearchToolParameters,
    BingGroundingTool,
    PromptAgentDefinition,
)
from httpx import AsyncClient
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
)
from unique_search_proxy_core.schema import AnswerSpanCitation

from unique_search_proxy_client.web.core.agent_engines.bing.client import (
    get_openai_client,
)
from unique_search_proxy_client.web.settings.providers import bing_agent as settings
from unique_search_proxy_client.web.settings.secret_str import NOT_PROVIDED, read_secret

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "BingStreamChunk",
    "create_bing_agent",
    "get_bing_grounding_tool",
    "resolve_bing_agent_name",
    "stream_bing_grounding_agent",
]


class BingStreamChunk(NamedTuple):
    """One step of a Bing Responses stream.

    ``answer`` and ``citations`` are set only for the completed response, and
    the citation offsets point into ``answer``.
    """

    delta: str
    raw_event: dict
    answer: str | None = None
    citations: Sequence[AnswerSpanCitation] = ()


def resolve_bing_agent_name(
    *,
    model: str,
    instructions: str,
    grounding: BingGroundingConfiguration,
) -> str:
    """Return the hash-based agent name to use for Responses (no Foundry round-trip)."""
    return bing_agent_name(
        model=model,
        instructions=instructions,
        grounding=grounding,
    )


def get_bing_grounding_tool(
    grounding: BingGroundingConfiguration,
) -> BingGroundingTool:
    """Build the grounding tool, letting Bing default the knobs left unset."""
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
                    count=grounding.fetch_size,
                    market=grounding.market,
                    freshness=grounding.freshness,
                )
            ]
        )
    )


async def create_bing_agent(
    project_client: AIProjectClient,
    *,
    agent_name: str,
    model: str,
    instructions: str,
    grounding: BingGroundingConfiguration,
) -> str:
    """Create a Foundry agent version and return its name."""
    started = time.perf_counter()
    agent = await project_client.agents.create_version(
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
    http_client: AsyncClient | None = None,
    query: str,
    model: str,
    instructions: str,
    grounding: BingGroundingConfiguration,
    timeout: float,
) -> AsyncIterator[BingStreamChunk]:
    """Stream Bing-grounded Responses events as :class:`BingStreamChunk` items.

    Optimistically calls Responses with a hash-derived agent name. If the agent
    is missing, creates it once and retries.

    Instructions must already be baked into the agent version — Foundry returns
    ``invalid_payload`` if ``instructions`` is passed alongside ``agent_reference``.
    """
    resolved_name = resolve_bing_agent_name(
        model=model,
        instructions=instructions,
        grounding=grounding,
    )
    openai_client = get_openai_client(
        project_client,
        http_client=http_client,
    )

    try:
        stream = await _create_responses_stream(
            openai_client,
            agent_name=resolved_name,
            query=query,
            timeout=timeout,
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
                project_client,
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
            timeout=timeout,
        )

    emitted_text = False
    async with stream:
        async for event in stream:
            if isinstance(event, ResponseTextDeltaEvent):
                if event.delta:
                    emitted_text = True
                    yield BingStreamChunk(
                        event.delta, event.model_dump(mode="json", warnings="none")
                    )
            elif isinstance(event, ResponseCompletedEvent):
                response = event.response
                output_text = response.output_text
                citations = _extract_response_url_citations(response)
                raw_completed = {
                    "type": event.type,
                    "response": response.model_dump(mode="json", warnings="none"),
                }
                # Foundry sometimes delivers the full answer only on completion.
                if output_text and not emitted_text:
                    emitted_text = True
                    yield BingStreamChunk(
                        output_text,
                        raw_completed,
                        answer=output_text,
                        citations=citations,
                    )
                else:
                    yield BingStreamChunk(
                        "", raw_completed, answer=output_text, citations=citations
                    )


async def _create_responses_stream(
    openai_client: openai.AsyncOpenAI,
    *,
    agent_name: str,
    query: str,
    timeout: float,
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
        # The shared egress client defaults to 30s, while Bing requests allow
        # longer runs. The API's outer deadline still caps total request time.
        timeout=timeout,
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
) -> list[AnswerSpanCitation]:
    """Turn the URL annotations on one output message into citations.

    Args:
        item: A completed assistant message. Its text can be split across
            several ``output_text`` parts, and each annotation's offsets are
            relative to the part it is attached to.
        start_index_offset: Length of the answer text before this message, so
            the returned offsets point into the full answer.

    Returns:
        One citation per URL annotation, carrying the marker text the
        annotation spans and its offsets into the full answer. Annotations
        without a URL or with an empty span are skipped.
    """
    if not item.content:
        return []

    citations: list[AnswerSpanCitation] = []
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
                    AnswerSpanCitation(
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
) -> list[AnswerSpanCitation]:
    """Extract citations with offsets into ``response.output_text``."""
    citations: list[AnswerSpanCitation] = []
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
        "Foundry Bing citation annotations response_id=%s citation_count=%d",
        response.id,
        len(citations),
    )
    return citations
