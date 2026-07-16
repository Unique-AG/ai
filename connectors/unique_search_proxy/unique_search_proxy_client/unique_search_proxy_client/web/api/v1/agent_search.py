from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Body, Request
from fastapi.responses import StreamingResponse
from unique_search_proxy_core.agent_engines.base import AgentEngineType
from unique_search_proxy_core.agent_engines.config_types import AgentSearchRequest
from unique_search_proxy_core.errors import (
    ProxyError,
    UpstreamError,
    UpstreamTimeoutError,
    attach_request_context,
)
from unique_search_proxy_core.schema import (
    AgentSearchResponse,
    AgentSearchStreamEvent,
    ErrorResponse,
    ProxyErrorCode,
)

from unique_search_proxy_client.web.core.agent_engines.factory import (
    get_agent_engine_service,
)
from unique_search_proxy_client.web.monitoring.metrics import (
    record_agent_search_error,
    record_agent_search_success,
)

router = APIRouter(tags=["agent-search"])
_LOGGER = logging.getLogger(__name__)

_AGENT_SEARCH_OPENAPI_EXAMPLES = {
    "bing": {
        "summary": "Bing grounding agent",
        "value": {
            "engine": "bing",
            "query": "What changed in the EU AI Act this year?",
            "fetchSize": 5,
            "timeout": 120,
        },
    },
    "vertexai": {
        "summary": "Vertex AI grounding",
        "value": {
            "engine": "vertexai",
            "query": "Latest developments in quantum computing",
            "vertexaiModelName": "gemini-3-flash-preview",
            "timeout": 120,
        },
    },
}


def _agent_search_request_context(exc: ProxyError, *, engine_id: str) -> ProxyError:
    return attach_request_context(
        exc,
        request="agent_search",
        provider=engine_id,
    )


@router.post(
    "/agent-search",
    response_model=AgentSearchResponse,
    summary="Run an agent-based grounded search",
)
async def agent_search(
    request: Request,
    body: AgentSearchRequest = Body(openapi_examples=_AGENT_SEARCH_OPENAPI_EXAMPLES),  # type: ignore[valid-type]
) -> AgentSearchResponse:
    engine = body.engine
    engine_id = engine.value if hasattr(engine, "value") else str(engine)
    timeout = body.timeout
    started = time.perf_counter()
    _LOGGER.info(
        "agent-search start mode=sync engine=%s timeout=%ss",
        engine_id,
        timeout,
    )
    _LOGGER.debug("agent-search query=%r", body.query)

    try:
        engine_service = get_agent_engine_service(
            AgentEngineType(engine_id) if isinstance(engine, str) else engine,
        )
        async with asyncio.timeout(timeout):
            result = await engine_service.search(body)
    except TimeoutError as exc:
        record_agent_search_error(
            engine_id,
            ProxyErrorCode.UPSTREAM_TIMEOUT.value,
            time.perf_counter() - started,
        )
        _LOGGER.warning(
            "agent-search timeout mode=sync engine=%s timeout=%ss duration=%.0fms",
            engine_id,
            timeout,
            (time.perf_counter() - started) * 1000,
        )
        raise _agent_search_request_context(
            UpstreamTimeoutError(
                f"Agent engine '{engine_id}' timed out after {timeout}s",
            ),
            engine_id=engine_id,
        ) from exc
    except ProxyError as exc:
        record_agent_search_error(
            engine_id,
            exc.code.value if hasattr(exc.code, "value") else str(exc.code),
            time.perf_counter() - started,
        )
        _LOGGER.warning(
            "agent-search failed mode=sync engine=%s code=%s duration=%.0fms",
            engine_id,
            exc.code.value if hasattr(exc.code, "value") else exc.code,
            (time.perf_counter() - started) * 1000,
        )
        raise _agent_search_request_context(exc, engine_id=engine_id) from exc
    except Exception:
        record_agent_search_error(
            engine_id,
            "INTERNAL_ERROR",
            time.perf_counter() - started,
        )
        _LOGGER.exception(
            "agent-search error mode=sync engine=%s duration=%.0fms",
            engine_id,
            (time.perf_counter() - started) * 1000,
        )
        raise

    duration = time.perf_counter() - started
    record_agent_search_success(engine_id, duration)
    _LOGGER.info(
        "agent-search success mode=sync engine=%s duration=%.0fms",
        engine_id,
        duration * 1000,
    )
    return result


@router.post(
    "/agent-search/stream",
    summary="Stream an agent-based grounded search (SSE)",
)
async def agent_search_stream(
    request: Request,
    body: AgentSearchRequest = Body(openapi_examples=_AGENT_SEARCH_OPENAPI_EXAMPLES),  # type: ignore[valid-type]
) -> StreamingResponse:
    engine = body.engine
    engine_id = engine.value if hasattr(engine, "value") else str(engine)
    timeout = body.timeout
    started = time.perf_counter()
    _LOGGER.info(
        "agent-search start mode=stream engine=%s timeout=%ss",
        engine_id,
        timeout,
    )
    _LOGGER.debug("agent-search query=%r", body.query)

    try:
        engine_service = get_agent_engine_service(
            AgentEngineType(engine_id) if isinstance(engine, str) else engine,
        )
    except Exception as exc:
        record_agent_search_error(engine_id, "INTERNAL_ERROR", 0.0)
        _LOGGER.exception(
            "agent-search setup error mode=stream engine=%s",
            engine_id,
        )
        raise _agent_search_request_context(
            UpstreamError(str(exc)),
            engine_id=engine_id,
        ) from exc

    async def event_generator() -> AsyncIterator[str]:
        nonlocal started
        try:
            async with asyncio.timeout(timeout):
                async for event in engine_service.stream(body):
                    yield _format_sse_event(event)
            record_agent_search_success(engine_id, time.perf_counter() - started)
            _LOGGER.info(
                "agent-search success mode=stream engine=%s duration=%.0fms",
                engine_id,
                (time.perf_counter() - started) * 1000,
            )
        except TimeoutError:
            record_agent_search_error(
                engine_id,
                ProxyErrorCode.UPSTREAM_TIMEOUT.value,
                time.perf_counter() - started,
            )
            _LOGGER.warning(
                "agent-search timeout mode=stream engine=%s timeout=%ss duration=%.0fms",
                engine_id,
                timeout,
                (time.perf_counter() - started) * 1000,
            )
            error = _agent_search_request_context(
                UpstreamTimeoutError(
                    f"Agent engine '{engine_id}' timed out after {timeout}s",
                ),
                engine_id=engine_id,
            )
            yield _format_sse_error(error)
        except ProxyError as exc:
            record_agent_search_error(
                engine_id,
                exc.code.value if hasattr(exc.code, "value") else str(exc.code),
                time.perf_counter() - started,
            )
            _LOGGER.warning(
                "agent-search failed mode=stream engine=%s code=%s duration=%.0fms",
                engine_id,
                exc.code.value if hasattr(exc.code, "value") else exc.code,
                (time.perf_counter() - started) * 1000,
            )
            yield _format_sse_error(
                _agent_search_request_context(exc, engine_id=engine_id)
            )
        except Exception as exc:
            record_agent_search_error(
                engine_id,
                "INTERNAL_ERROR",
                time.perf_counter() - started,
            )
            _LOGGER.exception(
                "agent-search error mode=stream engine=%s duration=%.0fms",
                engine_id,
                (time.perf_counter() - started) * 1000,
            )
            yield _format_sse_error(
                _agent_search_request_context(
                    UpstreamError(str(exc)),
                    engine_id=engine_id,
                ),
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


def _format_sse_event(event: AgentSearchStreamEvent) -> str:
    payload = event.model_dump(by_alias=True)
    return f"data: {json.dumps(payload)}\n\n"


def _format_sse_error(exc: ProxyError) -> str:
    envelope = ErrorResponse(error=exc.to_detail())
    return f"data: {json.dumps(envelope.model_dump(by_alias=True))}\n\n"
