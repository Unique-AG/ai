from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_toolkit.elicitation import (
    ElicitationDeclinedException,
    ElicitationExpiredException,
    ElicitationFailedException,
    ElicitationStatus,
)
from unique_toolkit.monitoring import REGISTRY

from unique_web_search.schema import WebSearchDebugInfo
from unique_web_search.services.query_elicitation import (
    QueryElicitationConfig,
    QueryElicitationService,
)


def _build_service(
    *,
    enabled: bool = True,
    max_query_length: int | None = None,
    engine: str = "google",
) -> tuple[QueryElicitationService, Mock, WebSearchDebugInfo]:
    chat_service = Mock()
    chat_service.elicitation.create_async = AsyncMock(
        return_value=SimpleNamespace(id="elicitation-id")
    )
    chat_service.elicitation.get_async = AsyncMock()
    debug_info = WebSearchDebugInfo(parameters={})
    service = QueryElicitationService(
        chat_service=chat_service,
        display_name="Web Search",
        config=QueryElicitationConfig(
            enable_elicitation=enabled,
            timeout_seconds=1,
            max_query_length=max_query_length,
        ),
        debug_info=debug_info,
        engine=engine,
    )
    return service, chat_service, debug_info


@pytest.mark.ai
@pytest.mark.parametrize(
    ("submitted_queries", "expected_prompt_change"),
    [
        (["original query"], False),
        (["modified query"], True),
    ],
)
async def test_query_elicitation__records_accepted_outcome(
    submitted_queries: list[str],
    expected_prompt_change: bool,
) -> None:
    """
    Purpose: Verify accepted elicitations record approval and whether queries changed.
    Why this matters: Analytics must distinguish approved unchanged and modified prompts.
    Setup summary: Return an accepted response and assert the queries and debug fields.
    """
    service, chat_service, debug_info = _build_service()
    chat_service.elicitation.get_async.return_value = SimpleNamespace(
        id="elicitation-id",
        status=ElicitationStatus.ACCEPTED,
        response_content={"queries": submitted_queries},
    )

    with patch(
        "unique_web_search.services.query_elicitation.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        result = await service(["original query"])

    serialized_debug_info = debug_info.model_dump()
    assert result == submitted_queries
    assert serialized_debug_info["elicitation_approval"] is True
    assert serialized_debug_info["elicitation_prompt_change"] is expected_prompt_change


@pytest.mark.ai
async def test_query_elicitation__truncates_proposed_queries__to_max_query_length() -> (
    None
):
    """
    Purpose: Verify proposed queries are cut to the limit and the form receives the limit.
    Why this matters: The review form must never be pre-filled beyond what the user may submit.
    Setup summary: Propose one over-long query, accept the defaults, assert schema and result.
    """
    service, chat_service, debug_info = _build_service(max_query_length=10)
    chat_service.elicitation.get_async.return_value = SimpleNamespace(
        id="elicitation-id",
        status=ElicitationStatus.ACCEPTED,
        response_content={"queries": ["0123456789", "short"]},
    )

    with patch(
        "unique_web_search.services.query_elicitation.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        result = await service(["0123456789 overflow", "short"])

    queries_schema = chat_service.elicitation.create_async.call_args.kwargs[
        "json_schema"
    ]["properties"]["queries"]
    assert queries_schema["default"] == ["0123456789", "short"]
    assert queries_schema["items"]["maxLength"] == 10
    assert result == ["0123456789", "short"]
    assert debug_info.elicitation_prompt_change is False


@pytest.mark.ai
async def test_query_elicitation__keeps_queries_whole__when_no_max_query_length() -> (
    None
):
    """
    Purpose: Verify the length limit is opt-in: without it queries are neither cut nor limited.
    Why this matters: Agent-mode engines propose long natural-language queries that must stay intact.
    Setup summary: Leave the limit unset, propose and accept a long query, assert schema and result.
    """
    long_query = "a" * 500
    service, chat_service, _ = _build_service()
    chat_service.elicitation.get_async.return_value = SimpleNamespace(
        id="elicitation-id",
        status=ElicitationStatus.ACCEPTED,
        response_content={"queries": [long_query]},
    )

    with patch(
        "unique_web_search.services.query_elicitation.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        result = await service([long_query])

    queries_schema = chat_service.elicitation.create_async.call_args.kwargs[
        "json_schema"
    ]["properties"]["queries"]
    assert queries_schema["default"] == [long_query]
    assert "maxLength" not in queries_schema["items"]
    assert result == [long_query]


@pytest.mark.ai
@pytest.mark.parametrize("enabled", [True, False])
async def test_query_elicitation__records_proposed_query_lengths__by_engine_and_query_review(
    enabled: bool,
) -> None:
    """
    Purpose: Verify every proposed query's length is recorded before truncation, with or without review.
    Why this matters: The metric shows how long each engine's queries are, to tune the limit.
    Setup summary: Propose two queries under a 10-character limit, then read the histogram sum and count.
    """
    engine = f"pytest_query_length_{enabled}"
    labels = {"engine": engine, "query_review": str(enabled).lower()}
    service, chat_service, _ = _build_service(
        enabled=enabled, max_query_length=10, engine=engine
    )
    chat_service.elicitation.get_async.return_value = SimpleNamespace(
        id="elicitation-id",
        status=ElicitationStatus.ACCEPTED,
        response_content={"queries": ["short"]},
    )

    with patch(
        "unique_web_search.services.query_elicitation.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        await service(["0123456789 overflow", "short"])

    metric = "unique_web_search_query_length_characters"
    assert REGISTRY.get_sample_value(f"{metric}_count", labels) == 2
    assert REGISTRY.get_sample_value(f"{metric}_sum", labels) == 24


@pytest.mark.ai
async def test_query_elicitation__raises__when_submitted_query_exceeds_max_query_length() -> (
    None
):
    """
    Purpose: Verify a submitted query over the limit is rejected before any search runs.
    Why this matters: Clients that bypass the form's limit must not send long text to the engine.
    Setup summary: Accept a response with an over-long query and assert the failure.
    """
    service, chat_service, _ = _build_service(max_query_length=10)
    chat_service.elicitation.get_async.return_value = SimpleNamespace(
        id="elicitation-id",
        status=ElicitationStatus.ACCEPTED,
        response_content={"queries": ["01234567890"]},
    )

    with (
        patch(
            "unique_web_search.services.query_elicitation.asyncio.sleep",
            new_callable=AsyncMock,
        ),
        pytest.raises(ElicitationFailedException, match="10-character limit"),
    ):
        await service(["original query"])


@pytest.mark.ai
async def test_query_elicitation__records_not_approved__when_declined() -> None:
    """
    Purpose: Verify declined elicitations are recorded before the exception propagates.
    Why this matters: Failed WebSearch calls must still contribute to approval analytics.
    Setup summary: Return a declined response, assert the exception and false outcomes.
    """
    service, chat_service, debug_info = _build_service()
    chat_service.elicitation.get_async.return_value = SimpleNamespace(
        id="elicitation-id",
        status=ElicitationStatus.DECLINED,
    )

    with (
        patch(
            "unique_web_search.services.query_elicitation.asyncio.sleep",
            new_callable=AsyncMock,
        ),
        pytest.raises(ElicitationDeclinedException),
    ):
        await service(["original query"])

    assert debug_info.elicitation_approval is False
    assert debug_info.elicitation_prompt_change is False


@pytest.mark.ai
async def test_query_elicitation__records_not_approved__when_timed_out() -> None:
    """
    Purpose: Verify timed-out elicitations retain a non-approved analytics outcome.
    Why this matters: Timeout exceptions must not erase that elicitation was presented.
    Setup summary: Keep the response pending through the timeout and assert false outcomes.
    """
    service, chat_service, debug_info = _build_service()
    chat_service.elicitation.get_async.return_value = SimpleNamespace(
        id="elicitation-id",
        status=ElicitationStatus.PENDING,
    )

    with (
        patch(
            "unique_web_search.services.query_elicitation.asyncio.sleep",
            new_callable=AsyncMock,
        ),
        pytest.raises(ElicitationExpiredException),
    ):
        await service(["original query"])

    assert debug_info.elicitation_approval is False
    assert debug_info.elicitation_prompt_change is False


@pytest.mark.ai
async def test_query_elicitation__omits_outcome__when_disabled() -> None:
    """
    Purpose: Verify analytics fields are absent when no elicitation is presented.
    Why this matters: Absence distinguishes disabled elicitation from non-approval.
    Setup summary: Disable elicitation, assert passthrough queries and omitted fields.
    """
    service, chat_service, debug_info = _build_service(enabled=False)

    result = await service(["original query"])

    assert result == ["original query"]
    assert "elicitation_approval" not in debug_info.model_dump()
    assert "elicitation_prompt_change" not in debug_info.model_dump()
    chat_service.elicitation.create_async.assert_not_awaited()
