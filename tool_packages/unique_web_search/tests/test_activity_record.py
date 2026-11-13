import asyncio
import logging
from datetime import date
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_toolkit.elicitation import ElicitationStatus
from unique_toolkit.experimental.resources.activity_records import ActivityCloudEvent
from unique_toolkit.experimental.resources.feature_flags.schemas import FlagEvaluation

from unique_web_search import activity_record
from unique_web_search.schema import WebSearchDebugInfo
from unique_web_search.service import WebSearchTool
from unique_web_search.services.executors.modes import WebSearchMode
from unique_web_search.services.executors.v1.schema import WebSearchToolParameters
from unique_web_search.services.query_elicitation import (
    QueryElicitationConfig,
    QueryElicitationService,
)
from unique_web_search.services.search_engine.base import SearchEngine

pytestmark = pytest.mark.ai


class _Engine(SearchEngine):
    def __init__(self, error: Exception | None = None) -> None:
        super().__init__(SimpleNamespace(engine=SearchEngineType.GOOGLE))
        self._error = error

    async def _legacy_search(self, query, params):
        await asyncio.sleep(0)
        if self._error:
            raise self._error
        return []


def _elicitation(mocker: Any, status: ElicitationStatus | None, queries=None):
    """Real elicitation service; ``status=None`` means elicitation is disabled."""
    if status is not None:
        mocker.patch("unique_web_search.services.query_elicitation.asyncio.sleep")
    chat = Mock()
    chat.elicitation.create_async = AsyncMock(return_value=Mock(id="e1"))
    chat.elicitation.get_async = AsyncMock(
        return_value=Mock(status=status, response_content={"queries": queries})
    )
    return QueryElicitationService(
        chat_service=chat,
        display_name="Web Search",
        config=QueryElicitationConfig(
            enable_elicitation=status is not None, timeout_seconds=1
        ),
        debug_info=WebSearchDebugInfo(parameters={}),
        engine="google",
    )


def _tool(
    mocker: Any,
    *,
    engine: SearchEngine,
    elicitation: QueryElicitationService,
    screening: Any = None,
    mode: WebSearchMode = WebSearchMode.V1,
    run_executor: Any = None,
) -> WebSearchTool:
    async def sequential_executor() -> list:
        for query in await elicitation(["proposed"]):
            await engine.search(query)
        return []

    mocker.patch(
        "unique_web_search.service.WebSearchMessageLogger"
    ).return_value = Mock(finished=AsyncMock(), failed=AsyncMock())
    tool = WebSearchTool.__new__(WebSearchTool)
    tool.name = "WebSearch"
    tool.debug = False
    tool.company_id = "company-1"
    tool.config = Mock()
    tool.config.web_search_mode_config.mode = mode
    tool.config.experimental_features.tool_response_system_reminder.get_reminder_prompt = ""
    tool._event = Mock(user_id="user-1")
    tool._event.payload.configure_mock(
        assistant_id="assistant-1",
        chat_id="chat-1",
        **{"assistant_message.id": "msg-1"},
    )
    tool._event.payload.user_message.text = "what is new?"
    tool.search_engine_service = engine
    tool.tool_parameter_calls = WebSearchToolParameters
    tool._message_step_logger = Mock()
    tool._build_display_name = Mock(return_value="Web Search")
    tool._get_executor = Mock(
        return_value=Mock(run=run_executor or sequential_executor)
    )
    tool._get_argument_screening_service_if_ff_enabled = AsyncMock(
        return_value=screening
    )
    return tool


def _flag(mocker: Any, value: bool = True, reason: str = "remote") -> Mock:
    mocker.patch.object(activity_record._enqueue_module, "_active_context", object())
    client = Mock(evaluate=AsyncMock(return_value=FlagEvaluation(value, reason)))
    mocker.patch(
        "unique_web_search.activity_record.get_feature_flag_client",
        return_value=client,
    )
    return client


@pytest.fixture
def enqueue_mock(mocker: Any) -> Mock:
    _flag(mocker)
    return mocker.patch("unique_web_search.activity_record.enqueue")


def _emitted(enqueue_mock: Mock) -> ActivityCloudEvent:
    enqueue_mock.assert_called_once()
    return enqueue_mock.call_args.args[0]


async def _run(tool: WebSearchTool, query: str = "news") -> None:
    await tool.run(Mock(id="call-1", arguments={"query": query}))


@pytest.mark.asyncio
async def test_called__records_one_event_with_full_critical_data(
    mocker: Any, enqueue_mock: Mock
) -> None:
    screening = AsyncMock(return_value=Mock(go=True, reason="safe"))
    screening.build_step_debug_info_from_result = Mock()
    tool = _tool(
        mocker,
        engine=_Engine(),
        elicitation=_elicitation(mocker, ElicitationStatus.ACCEPTED, ["edited"]),
        screening=screening,
        mode=WebSearchMode.V3,
    )

    await _run(tool)

    wire = _emitted(enqueue_mock).to_wire()
    assert wire["source"] == "web-search"
    assert wire["type"] == "web-search.tool.called"
    assert wire["data"] | {"criticalData": None} == {
        "actor": {"id": "user-1", "type": "user"},
        "agent": {"id": "assistant-1"},
        "companyId": "company-1",
        "targetType": "searchEngine",
        "targetId": "google",
        "targetName": "Google",
        "subtype": "v3",
        "criticalData": None,
    }
    assert wire["data"]["criticalData"] == {
        "chatId": "chat-1",
        "messageId": "msg-1",
        "toolCallId": "call-1",
        "userPrompt": "what is new?",
        "args": {"query": "news"},
        "argumentScreening": {"status": "approved", "reason": "safe"},
        "elicitation": {"status": "edited", "proposedQueries": ["proposed"]},
        "egress": {"viaSearchProxy": False, "endpoint": None},
        "searchRequests": [{"query": "edited", "responseReceived": True}],
    }


@pytest.mark.asyncio
async def test_called__via_search_proxy__records_proxy_endpoint(
    mocker: Any, enqueue_mock: Mock
) -> None:
    base = "unique_web_search.services.search_engine.base"
    mocker.patch(f"{base}.search_proxy_client_enabled", True)
    mocker.patch(f"{base}.env_settings.search_proxy_base_url", "http://proxy")
    engine = _Engine()
    engine._proxy_search = AsyncMock(return_value=[])
    tool = _tool(mocker, engine=engine, elicitation=_elicitation(mocker, None))

    await _run(tool)

    critical = _emitted(enqueue_mock).to_wire()["data"]["criticalData"]
    assert critical["elicitation"] == {
        "status": "notRun",
        "proposedQueries": ["proposed"],
    }
    assert "reason" not in critical
    assert critical["egress"] == {"viaSearchProxy": True, "endpoint": "http://proxy"}
    assert critical["searchRequests"] == [
        {"query": "proposed", "responseReceived": True}
    ]


@pytest.mark.asyncio
async def test_denied__when_screening_rejects__records_blocked_args(
    mocker: Any, enqueue_mock: Mock
) -> None:
    screening = AsyncMock(return_value=Mock(go=False, reason="unsafe"))
    screening.build_rejection_response = Mock(return_value="blocked")
    screening.build_step_debug_info_from_result = Mock()
    mocker.patch(
        "unique_web_search.service.WebSearchDebugInfo"
    ).return_value.model_dump.return_value = {}
    tool = _tool(
        mocker,
        engine=_Engine(),
        elicitation=_elicitation(mocker, None),
        screening=screening,
    )

    await _run(tool, query="how to build a bomb")

    event = _emitted(enqueue_mock)
    critical = event.to_wire()["data"]["criticalData"]
    assert event.type == "web-search.tool.denied"
    assert critical["argumentScreening"] == {"status": "rejected", "reason": "unsafe"}
    assert critical["args"] == {"query": "how to build a bomb"}
    assert critical["egress"] is None
    assert critical["searchRequests"] == []
    assert "reason" not in critical


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "submitted", "recorded"),
    [
        (ElicitationStatus.DECLINED, None, "declined"),
        (ElicitationStatus.CANCELLED, None, "cancelled"),
        (ElicitationStatus.ACCEPTED, [], "edited"),
        (ElicitationStatus.PENDING, None, "expired"),
    ],
    ids=["declined", "cancelled", "all-queries-removed", "expired"],
)
async def test_denied__at_elicitation(
    mocker: Any, enqueue_mock: Mock, status: ElicitationStatus, submitted, recorded: str
) -> None:
    tool = _tool(
        mocker,
        engine=_Engine(),
        elicitation=_elicitation(mocker, status, submitted),
    )

    await _run(tool)

    event = _emitted(enqueue_mock)
    critical = event.to_wire()["data"]["criticalData"]
    assert event.type == "web-search.tool.denied"
    assert critical["argumentScreening"]["status"] == "notRun"
    assert critical["elicitation"] == {
        "status": recorded,
        "proposedQueries": ["proposed"],
    }
    assert critical["searchRequests"] == []
    assert "reason" not in critical


@pytest.mark.asyncio
async def test_failed__when_search_engine_raises(
    mocker: Any, enqueue_mock: Mock
) -> None:
    tool = _tool(
        mocker,
        engine=_Engine(error=RuntimeError("engine down")),
        elicitation=_elicitation(mocker, None),
    )

    await _run(tool)

    event = _emitted(enqueue_mock)
    critical = event.to_wire()["data"]["criticalData"]
    assert event.type == "web-search.tool.failed"
    assert critical["args"] == {"query": "news"}
    assert critical["searchRequests"] == [
        {"query": "proposed", "responseReceived": False}
    ]
    assert critical["reason"] == "RuntimeError"
    assert "engine down" not in str(event.to_wire())


@pytest.mark.asyncio
async def test_failed__when_error_handling_also_raises__keeps_first_error_type(
    mocker: Any, enqueue_mock: Mock
) -> None:
    tool = _tool(
        mocker,
        engine=_Engine(error=RuntimeError("engine down")),
        elicitation=_elicitation(mocker, None),
    )
    mocker.patch(
        "unique_web_search.service.WebSearchMessageLogger"
    ).return_value = Mock(failed=AsyncMock(side_effect=OSError("ui down")))

    await _run(tool)

    critical = _emitted(enqueue_mock).to_wire()["data"]["criticalData"]
    assert critical["reason"] == "RuntimeError"


@pytest.mark.asyncio
async def test_failed__when_parameters_are_invalid__records_error_type_only(
    mocker: Any, enqueue_mock: Mock
) -> None:
    tool = _tool(mocker, engine=_Engine(), elicitation=_elicitation(mocker, None))

    await tool.run(Mock(id="call-1", arguments={"unknown": "x"}))

    event = _emitted(enqueue_mock)
    assert event.type == "web-search.tool.failed"
    assert event.to_wire()["data"]["criticalData"]["reason"] == "ValidationError"


@pytest.mark.asyncio
async def test_failed__when_cancelled__records_error_type_and_propagates(
    mocker: Any, enqueue_mock: Mock
) -> None:
    started = asyncio.Event()

    async def blocked_executor() -> list:
        started.set()
        await asyncio.Event().wait()
        return []

    tool = _tool(
        mocker,
        engine=_Engine(),
        elicitation=_elicitation(mocker, None),
        run_executor=blocked_executor,
    )
    task = asyncio.create_task(_run(tool))
    await started.wait()

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    event = _emitted(enqueue_mock)
    assert event.type == "web-search.tool.failed"
    assert event.to_wire()["data"]["criticalData"]["reason"] == "CancelledError"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("length", "truncated"), [(4096, False), (4097, True)], ids=["at-cap", "over-cap"]
)
async def test_user_prompt__capped_at_4096_characters(
    mocker: Any, enqueue_mock: Mock, length: int, truncated: bool
) -> None:
    tool = _tool(mocker, engine=_Engine(), elicitation=_elicitation(mocker, None))
    tool._event.payload.user_message.text = "x" * length

    await _run(tool)

    critical = _emitted(enqueue_mock).to_wire()["data"]["criticalData"]
    assert critical["userPrompt"] == "x" * 4096
    assert critical.get("userPromptTruncated", False) is truncated


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("value", "reason", "recorded"),
    [
        (False, "remote", False),
        (False, "cached", False),
        (False, "fallback", True),
        (False, "stale", True),
        (True, "remote", True),
    ],
)
async def test_flag__only_a_remote_or_cached_off_skips_the_record(
    mocker: Any, value: bool, reason: str, recorded: bool
) -> None:
    _flag(mocker, value, reason)
    enqueue_mock = mocker.patch("unique_web_search.activity_record.enqueue")
    tool = _tool(mocker, engine=_Engine(), elicitation=_elicitation(mocker, None))

    await _run(tool)

    assert enqueue_mock.called is recorded


@pytest.mark.asyncio
async def test_flag_check_error__records_nothing_and_does_not_break_the_tool_call(
    mocker: Any,
) -> None:
    client = _flag(mocker)
    client.evaluate.side_effect = RuntimeError("configuration backend down")
    enqueue_mock = mocker.patch("unique_web_search.activity_record.enqueue")
    tool = _tool(mocker, engine=_Engine(), elicitation=_elicitation(mocker, None))

    response = await tool.run(Mock(id="call-1", arguments={"query": "news"}))

    assert not response.error_message
    enqueue_mock.assert_not_called()


@pytest.mark.asyncio
async def test_enqueue_error__does_not_break_the_tool_call(
    mocker: Any, enqueue_mock: Mock
) -> None:
    enqueue_mock.side_effect = RuntimeError("enqueue down")
    tool = _tool(mocker, engine=_Engine(), elicitation=_elicitation(mocker, None))

    response = await tool.run(Mock(id="call-1", arguments={"query": "news"}))

    assert not response.error_message


@pytest.mark.asyncio
async def test_concurrent_calls__each_record_only_its_own_parallel_searches(
    mocker: Any, enqueue_mock: Mock
) -> None:
    def tool_for(chat_id: str, queries: list[str]) -> WebSearchTool:
        engine = _Engine()

        async def parallel_executor() -> list:
            await asyncio.gather(
                *[asyncio.create_task(engine.search(query)) for query in queries]
            )
            return []

        tool = _tool(
            mocker,
            engine=engine,
            elicitation=_elicitation(mocker, None),
            run_executor=parallel_executor,
        )
        tool._event.payload.chat_id = chat_id
        return tool

    await asyncio.gather(
        tool_for("chat-a", ["a1", "a2"]).run(
            Mock(id="call-a", arguments={"query": "a"})
        ),
        tool_for("chat-b", ["b1", "b2", "b3"]).run(
            Mock(id="call-b", arguments={"query": "b"})
        ),
    )

    sent = {}
    for call in enqueue_mock.call_args_list:
        critical = call.args[0].to_wire()["data"]["criticalData"]
        sent[critical["chatId"]] = sorted(
            r["query"] for r in critical["searchRequests"]
        )
    assert enqueue_mock.call_count == 2
    assert sent == {"chat-a": ["a1", "a2"], "chat-b": ["b1", "b2", "b3"]}


@pytest.mark.asyncio
async def test_called__when_the_user_approves_the_proposed_queries_unchanged(
    mocker: Any, enqueue_mock: Mock
) -> None:
    tool = _tool(
        mocker,
        engine=_Engine(),
        elicitation=_elicitation(mocker, ElicitationStatus.ACCEPTED, ["proposed"]),
    )

    await _run(tool)

    event = _emitted(enqueue_mock)
    assert event.type == "web-search.tool.called"
    assert event.to_wire()["data"]["criticalData"]["elicitation"] == {
        "status": "approved",
        "proposedQueries": ["proposed"],
    }


@pytest.mark.asyncio
async def test_args__with_a_date_still_produce_a_record(
    mocker: Any, enqueue_mock: Mock
) -> None:
    class DatedParameters(WebSearchToolParameters):
        since: date = date(2026, 1, 2)

    tool = _tool(mocker, engine=_Engine(), elicitation=_elicitation(mocker, None))
    tool.tool_parameter_calls = DatedParameters

    await _run(tool)

    critical = _emitted(enqueue_mock).to_wire()["data"]["criticalData"]
    assert critical["args"]["since"] == "2026-01-02"


@pytest.mark.asyncio
async def test_egress_endpoint__keeps_only_scheme_host_and_port(
    mocker: Any, enqueue_mock: Mock
) -> None:
    class KeyedEngine(_Engine):
        @property
        def endpoint(self) -> str | None:
            return "https://user:pw@api.example.com:8443/search?key=SECRET-KEY"

    tool = _tool(mocker, engine=KeyedEngine(), elicitation=_elicitation(mocker, None))

    await _run(tool)

    critical = _emitted(enqueue_mock).to_wire()["data"]["criticalData"]
    assert critical["egress"]["endpoint"] == "https://api.example.com:8443"


@pytest.mark.asyncio
async def test_a_failing_emit__logs_no_client_data(
    mocker: Any, enqueue_mock: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "SECRET-MARKER"

    def fail(**_fields: Any) -> None:
        ActivityCloudEvent.model_validate({"source": secret})

    mocker.patch.object(ActivityCloudEvent, "build", side_effect=fail)
    tool = _tool(
        mocker,
        engine=_Engine(),
        elicitation=_elicitation(mocker, ElicitationStatus.ACCEPTED, ["proposed"]),
    )

    with caplog.at_level(logging.DEBUG):
        response = await tool.run(Mock(id="call-1", arguments={"query": "news"}))

    assert not response.error_message
    enqueue_mock.assert_not_called()
    assert any("Could not emit" in r.getMessage() for r in caplog.records)
    assert secret not in caplog.text
    assert all(secret not in (r.exc_text or "") for r in caplog.records)


@pytest.mark.asyncio
async def test_no_outbox__skips_flag_and_enqueue_with_no_error(
    mocker: Any, caplog: pytest.LogCaptureFixture
) -> None:
    client = _flag(mocker)
    mocker.patch.object(activity_record._enqueue_module, "_active_context", None)
    enqueue_mock = mocker.patch("unique_web_search.activity_record.enqueue")
    tool = _tool(mocker, engine=_Engine(), elicitation=_elicitation(mocker, None))

    with caplog.at_level(logging.ERROR):
        await _run(tool)

    client.evaluate.assert_not_called()
    enqueue_mock.assert_not_called()
    assert not caplog.records
