from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_toolkit.elicitation import (
    ElicitationDeclinedException,
    ElicitationExpiredException,
    ElicitationStatus,
)

from unique_web_search.schema import WebSearchDebugInfo
from unique_web_search.services.query_elicitation import (
    QueryElicitationConfig,
    QueryElicitationService,
)


def _build_service(
    *,
    enabled: bool = True,
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
        ),
        debug_info=debug_info,
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
