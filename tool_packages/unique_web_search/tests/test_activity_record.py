import asyncio
import logging
from datetime import date
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_toolkit.elicitation import ElicitationStatus
from unique_toolkit.experimental.resources.activity_records import ActivityCloudEvent

from unique_web_search import activity_record
from unique_web_search.schema import WebSearchDebugInfo
from unique_web_search.service import WebSearchTool
from unique_web_search.services.argument_screening.config import (
    ArgumentScreeningConfig,
)
from unique_web_search.services.argument_screening.service import (
    ArgumentScreeningService,
)
from unique_web_search.services.executors.modes import WebSearchMode
from unique_web_search.services.executors.v1.schema import WebSearchToolParameters
from unique_web_search.services.query_elicitation import (
    QueryElicitationConfig,
    QueryElicitationService,
)
from unique_web_search.services.search_engine.base import SearchEngine

pytestmark = pytest.mark.ai


class _Params(ExposedParams):
    max_results: int | None = None
    freshness: str | None = None


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


@pytest.fixture(autouse=True)
def legacy_search_path(mocker: Any) -> None:
    mocker.patch(
        "unique_web_search.services.search_engine.base.search_proxy_client_enabled",
        False,
    )


@pytest.fixture
def flag_client(mocker: Any) -> Mock:
    client = Mock(is_enabled=AsyncMock(return_value=True))
    mocker.patch(
        "unique_web_search.activity_record.get_feature_flag_client",
        return_value=client,
    )
    return client


@pytest.fixture
def enqueue_mock(mocker: Any, flag_client: Mock) -> Mock:
    mocker.patch("unique_web_search.activity_record.is_running", return_value=True)
    return mocker.patch("unique_web_search.activity_record.enqueue")


def _emitted(enqueue_mock: Mock) -> ActivityCloudEvent:
    enqueue_mock.assert_called_once()
    return enqueue_mock.call_args.args[0]


def _rows(enqueue_mock: Mock) -> list[dict[str, Any]]:
    return [call.args[0].to_wire() for call in enqueue_mock.call_args_list]


async def _run(tool: WebSearchTool, query: str = "news") -> None:
    await tool.run(Mock(id="call-1", arguments={"query": query}))


@pytest.mark.asyncio
async def test_called__records_one_query_row_with_full_critical_data(
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
    assert wire["source"] == "chat"
    assert wire["type"] == "web-search.query.sent"
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
        "query": "edited",
        "params": None,
        "egress": {"viaSearchProxy": False, "endpoint": None},
        "responseReceived": True,
        "argumentScreening": {"status": "approved", "reason": "safe"},
        "elicitation": {"status": "edited", "proposedQueries": ["proposed"]},
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
    assert critical["query"] == "proposed"
    assert critical["responseReceived"] is True


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
    assert critical["userPrompt"] == "what is new?"
    assert "egress" not in critical
    assert critical["reason"] == "ArgumentScreeningBlocked"


@pytest.mark.asyncio
async def test_failed__when_the_rejection_response_cannot_be_built__keeps_the_real_error(
    mocker: Any, enqueue_mock: Mock
) -> None:
    screening = AsyncMock(return_value=Mock(go=False, reason="unsafe"))
    screening.build_rejection_response = Mock(side_effect=RuntimeError("no template"))
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

    await _run(tool)

    event = _emitted(enqueue_mock)
    critical = event.to_wire()["data"]["criticalData"]
    assert event.type == "web-search.tool.failed"
    assert critical["reason"] == "RuntimeError"


@pytest.mark.asyncio
async def test_denied__when_screening_approves_but_elicitation_cancels__keeps_the_elicitation_reason(
    mocker: Any, enqueue_mock: Mock
) -> None:
    screening = AsyncMock(return_value=Mock(go=True, reason="fine"))
    screening.build_step_debug_info_from_result = Mock()
    tool = _tool(
        mocker,
        engine=_Engine(),
        elicitation=_elicitation(mocker, ElicitationStatus.CANCELLED, None),
        screening=screening,
    )

    await _run(tool)

    critical = _emitted(enqueue_mock).to_wire()["data"]["criticalData"]
    assert critical["argumentScreening"] == {"status": "approved", "reason": "fine"}
    assert critical["elicitation"]["status"] == "cancelled"
    assert critical["reason"] == "ElicitationCancelledException"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "submitted", "recorded", "reason"),
    [
        (ElicitationStatus.DECLINED, None, "declined", "ElicitationDeclinedException"),
        (
            ElicitationStatus.CANCELLED,
            None,
            "cancelled",
            "ElicitationCancelledException",
        ),
        (ElicitationStatus.ACCEPTED, [], "edited", "ElicitationFailedException"),
        (ElicitationStatus.PENDING, None, "expired", "ElicitationExpiredException"),
    ],
    ids=["declined", "cancelled", "all-queries-removed", "expired"],
)
async def test_denied__at_elicitation(
    mocker: Any,
    enqueue_mock: Mock,
    status: ElicitationStatus,
    submitted,
    recorded: str,
    reason: str,
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
    assert critical["reason"] == reason


@pytest.mark.asyncio
async def test_failed__when_search_engine_raises__the_query_row_carries_the_error(
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
    assert enqueue_mock.call_count == 1
    assert event.type == "web-search.query.sent"
    assert critical["query"] == "proposed"
    assert critical["responseReceived"] is False
    assert critical["error"] == "RuntimeError"
    assert critical["args"] == {"query": "news"}
    assert "engine down" not in str(event.to_wire())


@pytest.mark.asyncio
async def test_failed__before_any_query__records_a_call_row_with_args_and_reason(
    mocker: Any, enqueue_mock: Mock
) -> None:
    async def failing_executor() -> list:
        raise RuntimeError("executor down")

    tool = _tool(
        mocker,
        engine=_Engine(),
        elicitation=_elicitation(mocker, None),
        run_executor=failing_executor,
    )

    await _run(tool)

    event = _emitted(enqueue_mock)
    critical = event.to_wire()["data"]["criticalData"]
    assert event.type == "web-search.tool.failed"
    assert critical["args"] == {"query": "news"}
    assert critical["userPrompt"] == "what is new?"
    assert critical["reason"] == "RuntimeError"
    assert "egress" not in critical
    assert "executor down" not in str(event.to_wire())


@pytest.mark.asyncio
async def test_failed__when_error_handling_also_raises__keeps_first_error_type(
    mocker: Any, enqueue_mock: Mock
) -> None:
    async def failing_executor() -> list:
        raise RuntimeError("executor down")

    tool = _tool(
        mocker,
        engine=_Engine(),
        elicitation=_elicitation(mocker, None),
        run_executor=failing_executor,
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
async def test_failed__when_cancelled_before_any_query__records_a_call_row(
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
    await asyncio.wait_for(started.wait(), timeout=5)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    event = _emitted(enqueue_mock)
    assert event.type == "web-search.tool.failed"
    assert event.to_wire()["data"]["criticalData"]["reason"] == "CancelledError"


def _screening_denied_tool(mocker: Any) -> WebSearchTool:
    screening = AsyncMock(return_value=Mock(go=False, reason="unsafe"))
    screening.build_rejection_response = Mock(return_value="blocked")
    screening.build_step_debug_info_from_result = Mock()
    mocker.patch(
        "unique_web_search.service.WebSearchDebugInfo"
    ).return_value.model_dump.return_value = {}
    return _tool(
        mocker,
        engine=_Engine(),
        elicitation=_elicitation(mocker, None),
        screening=screening,
    )


def _long_prompt_query_tool(mocker: Any) -> WebSearchTool:
    tool = _tool(mocker, engine=_Engine(), elicitation=_elicitation(mocker, None))
    tool._event.payload.user_message.text = "x" * 4097
    return tool


async def _failing_executor() -> list[Any]:
    raise RuntimeError("executor down")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("make_tool", "type_", "shape"),
    [
        (
            _long_prompt_query_tool,
            "web-search.query.sent",
            activity_record._QueryCriticalData,
        ),
        (
            _screening_denied_tool,
            "web-search.tool.denied",
            activity_record._CallCriticalData,
        ),
        (
            lambda m: _tool(
                m,
                engine=_Engine(),
                elicitation=_elicitation(m, ElicitationStatus.DECLINED),
            ),
            "web-search.tool.denied",
            activity_record._CallCriticalData,
        ),
        (
            lambda m: _tool(
                m,
                engine=_Engine(),
                elicitation=_elicitation(m, None),
                run_executor=_failing_executor,
            ),
            "web-search.tool.failed",
            activity_record._CallCriticalData,
        ),
    ],
    ids=["query-sent", "screening-denied", "elicitation-denied", "tool-failed"],
)
async def test_critical_data__keys_match_the_typed_shape(
    mocker: Any, enqueue_mock: Mock, make_tool: Any, type_: str, shape: Any
) -> None:
    await _run(make_tool(mocker))

    event = _emitted(enqueue_mock)
    critical = event.to_wire()["data"]["criticalData"]
    keys = critical.keys()
    assert event.type == type_
    assert "callOrigin" not in critical
    assert {"chatId", "messageId", "toolCallId", "userPrompt"} <= keys
    assert shape.__required_keys__ <= keys
    assert keys <= shape.__required_keys__ | shape.__optional_keys__


@pytest.mark.asyncio
async def test_failed__when_cancelled_mid_query__the_query_row_carries_the_error(
    mocker: Any, enqueue_mock: Mock
) -> None:
    started = asyncio.Event()

    class BlockedEngine(_Engine):
        async def _legacy_search(self, query, params):
            started.set()
            await asyncio.Event().wait()

    tool = _tool(mocker, engine=BlockedEngine(), elicitation=_elicitation(mocker, None))
    task = asyncio.create_task(_run(tool))
    await asyncio.wait_for(started.wait(), timeout=5)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    event = _emitted(enqueue_mock)
    critical = event.to_wire()["data"]["criticalData"]
    assert event.type == "web-search.query.sent"
    assert critical["error"] == "CancelledError"
    assert critical["responseReceived"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("length", "truncated"), [(4096, False), (4097, True)], ids=["at-cap", "over-cap"]
)
async def test_user_prompt__capped_at_4096_characters_on_call_rows(
    mocker: Any, enqueue_mock: Mock, length: int, truncated: bool
) -> None:
    tool = _tool(
        mocker,
        engine=_Engine(),
        elicitation=_elicitation(mocker, ElicitationStatus.DECLINED),
    )
    tool._event.payload.user_message.text = "x" * length

    await _run(tool)

    critical = _emitted(enqueue_mock).to_wire()["data"]["criticalData"]
    assert critical["userPrompt"] == "x" * 4096
    assert critical.get("userPromptTruncated", False) is truncated


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("length", "truncated"), [(4096, False), (4097, True)], ids=["at-cap", "over-cap"]
)
async def test_user_prompt__capped_at_4096_characters_on_query_rows(
    mocker: Any, enqueue_mock: Mock, length: int, truncated: bool
) -> None:
    tool = _tool(mocker, engine=_Engine(), elicitation=_elicitation(mocker, None))
    tool._event.payload.user_message.text = "x" * length

    await _run(tool)

    event = _emitted(enqueue_mock)
    critical = event.to_wire()["data"]["criticalData"]
    assert event.type == "web-search.query.sent"
    assert critical["userPrompt"] == "x" * 4096
    assert critical.get("userPromptTruncated", False) is truncated


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

    sent: dict[str, list[str]] = {"chat-a": [], "chat-b": []}
    for row in _rows(enqueue_mock):
        critical = row["data"]["criticalData"]
        sent[critical["chatId"]].append(critical["query"])
        assert critical["toolCallId"] == critical["chatId"].replace("chat", "call")
        assert critical["args"] == {"query": critical["chatId"][-1]}
    assert enqueue_mock.call_count == 5
    assert {k: sorted(v) for k, v in sent.items()} == {
        "chat-a": ["a1", "a2"],
        "chat-b": ["b1", "b2", "b3"],
    }


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
    assert event.type == "web-search.query.sent"
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

    tool = _tool(
        mocker,
        engine=_Engine(),
        elicitation=_elicitation(mocker, ElicitationStatus.DECLINED),
    )
    tool.tool_parameter_calls = DatedParameters

    await _run(tool)

    critical = _emitted(enqueue_mock).to_wire()["data"]["criticalData"]
    assert critical["args"]["since"] == "2026-01-02"


@pytest.mark.asyncio
async def test_screening_config_disabled__stays_not_run(
    mocker: Any, enqueue_mock: Mock
) -> None:
    service = ArgumentScreeningService(
        language_model_service=Mock(),
        language_model=Mock(),
        config=ArgumentScreeningConfig(enabled=False),
    )
    tool = _tool(
        mocker,
        engine=_Engine(),
        elicitation=_elicitation(mocker, None),
        screening=service,
    )

    await _run(tool)

    event = _emitted(enqueue_mock)
    assert event.type == "web-search.query.sent"
    assert event.to_wire()["data"]["criticalData"]["argumentScreening"] == {
        "status": "notRun",
        "reason": None,
    }


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
    assert "destination" not in critical["egress"]


@pytest.mark.asyncio
async def test_egress_endpoint__malformed_port_does_not_fail_the_search(
    mocker: Any, enqueue_mock: Mock
) -> None:
    class BadPort(_Engine):
        @property
        def endpoint(self) -> str | None:
            return "https://api.example.com:99999/search?key=SECRET"

    tool = _tool(mocker, engine=BadPort(), elicitation=_elicitation(mocker, None))

    await _run(tool)

    event = _emitted(enqueue_mock)
    critical = event.to_wire()["data"]["criticalData"]
    assert event.type == "web-search.query.sent"
    assert critical["egress"]["endpoint"] is None
    assert "SECRET" not in str(event.to_wire())


@pytest.mark.parametrize(
    ("url", "origin"),
    [
        ("https://[2001:db8::1]:8443/search?key=secret", "https://[2001:db8::1]:8443"),
        ("https://[2001:db8::1]/search", "https://[2001:db8::1]"),
    ],
    ids=["with-port", "without-port"],
)
def test_origin__keeps_the_brackets_of_an_ipv6_host(url: str, origin: str) -> None:
    assert activity_record._origin(url) == origin


@pytest.mark.asyncio
async def test_egress_endpoint__malformed_url_does_not_fail_the_search(
    mocker: Any, enqueue_mock: Mock
) -> None:
    class BadUrl(_Engine):
        @property
        def endpoint(self) -> str | None:
            return "http://[::1"

    tool = _tool(mocker, engine=BadUrl(), elicitation=_elicitation(mocker, None))

    await _run(tool)

    critical = _emitted(enqueue_mock).to_wire()["data"]["criticalData"]
    assert critical["responseReceived"] is True
    assert critical["egress"]["endpoint"] is None


@pytest.mark.asyncio
async def test_query_row__when_building_the_row_raises__the_search_is_unaffected(
    mocker: Any, enqueue_mock: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "SECRET-MARKER"
    mocker.patch.object(_Params, "model_dump", side_effect=RuntimeError(secret))
    engine = _Engine()
    results: dict[str, list] = {}

    async def with_params() -> list:
        results["found"] = await engine.search("news", _Params(max_results=3))
        return []

    tool = _tool(
        mocker,
        engine=engine,
        elicitation=_elicitation(mocker, None),
        run_executor=with_params,
    )

    with caplog.at_level(logging.ERROR):
        response = await tool.run(Mock(id="call-1", arguments={"query": "news"}))

    assert results == {"found": []}
    assert not response.error_message
    enqueue_mock.assert_not_called()
    assert any("errorName=RuntimeError" in r.getMessage() for r in caplog.records)
    assert secret not in caplog.text


@pytest.mark.asyncio
async def test_called__sequential_queries__one_row_each_with_shared_call_fields(
    mocker: Any, enqueue_mock: Mock
) -> None:
    engine = _Engine()
    elicitation = _elicitation(mocker, ElicitationStatus.ACCEPTED, ["proposed"])

    async def three_queries() -> list:
        await elicitation(["proposed"])
        for query in ["q1", "q2", "q3"]:
            await engine.search(query)
        return []

    screening = AsyncMock(return_value=Mock(go=True, reason="safe"))
    screening.build_step_debug_info_from_result = Mock()
    tool = _tool(
        mocker,
        engine=engine,
        elicitation=elicitation,
        screening=screening,
        run_executor=three_queries,
    )

    await _run(tool)

    rows = _rows(enqueue_mock)
    criticals = [row["data"]["criticalData"] for row in rows]
    assert [row["type"] for row in rows] == ["web-search.query.sent"] * 3
    assert [c["query"] for c in criticals] == ["q1", "q2", "q3"]
    assert {c["toolCallId"] for c in criticals} == {"call-1"}
    assert all(c["argumentScreening"]["status"] == "approved" for c in criticals)
    assert all(c["elicitation"]["status"] == "approved" for c in criticals)


@pytest.mark.asyncio
async def test_called__parallel_queries__one_row_each_and_errors_stay_per_query(
    mocker: Any, enqueue_mock: Mock
) -> None:
    class FlakyEngine(_Engine):
        async def _legacy_search(self, query, params):
            await asyncio.sleep(0)
            if query == "bad":
                raise TimeoutError("slow")
            return []

    engine = FlakyEngine()

    async def parallel() -> list:
        await asyncio.gather(
            *[engine.search(q) for q in ["ok1", "bad", "ok2"]],
            return_exceptions=True,
        )
        return []

    tool = _tool(
        mocker,
        engine=engine,
        elicitation=_elicitation(mocker, None),
        run_executor=parallel,
    )

    await _run(tool)

    by_query = {c["query"]: c for c in _sent(enqueue_mock)}
    assert sorted(by_query) == ["bad", "ok1", "ok2"]
    assert by_query["bad"]["error"] == "TimeoutError"
    assert by_query["bad"]["responseReceived"] is False
    assert "error" not in by_query["ok1"]
    assert "error" not in by_query["ok2"]
    assert enqueue_mock.call_count == 3
    assert all(r["type"] == "web-search.query.sent" for r in _rows(enqueue_mock))


@pytest.mark.asyncio
async def test_called__with_no_queries__emits_nothing(
    mocker: Any, enqueue_mock: Mock
) -> None:
    async def no_queries() -> list:
        return []

    tool = _tool(
        mocker,
        engine=_Engine(),
        elicitation=_elicitation(mocker, None),
        run_executor=no_queries,
    )

    await _run(tool)

    enqueue_mock.assert_not_called()


@pytest.mark.asyncio
async def test_query_row__records_the_exposed_params(
    mocker: Any, enqueue_mock: Mock
) -> None:
    engine = _Engine()
    params = _Params(max_results=3, freshness=None)

    async def with_params() -> list:
        await engine.search("news", params)
        return []

    tool = _tool(
        mocker,
        engine=engine,
        elicitation=_elicitation(mocker, None),
        run_executor=with_params,
    )

    await _run(tool)

    critical = _emitted(enqueue_mock).to_wire()["data"]["criticalData"]
    assert critical["params"] == {"maxResults": 3}
    assert critical["args"] == {"query": "news"}


@pytest.mark.asyncio
async def test_custom_api__via_search_proxy__records_destination_origin(
    mocker: Any, enqueue_mock: Mock
) -> None:
    from unique_web_search.services.search_engine.custom_api import (
        CustomAPI,
        CustomAPIConfig,
    )
    from unique_web_search.settings import CUSTOM_API_REQUEST_METHOD

    base = "unique_web_search.services.search_engine.base"
    mocker.patch(f"{base}.search_proxy_client_enabled", True)
    mocker.patch(f"{base}.env_settings.search_proxy_base_url", "http://proxy")
    mocker.patch.object(
        CustomAPI, "_proxy_routing_enabled", AsyncMock(return_value=True)
    )
    mocker.patch.object(CustomAPI, "_proxy_search", AsyncMock(return_value=[]))
    engine = CustomAPI(
        CustomAPIConfig(
            api_endpoint="https://api.example.com/search?key=SECRET",
            api_headers="{}",
            api_additional_query_params="{}",
            api_additional_body_params="{}",
            api_request_method=CUSTOM_API_REQUEST_METHOD.GET,
        )
    )
    token = activity_record._current_record.set(_record("customApi"))
    try:
        await engine.search("news")
    finally:
        activity_record._current_record.reset(token)

    [critical] = _sent(enqueue_mock)
    assert critical["egress"] == {
        "viaSearchProxy": True,
        "endpoint": "http://proxy",
        "destination": "https://api.example.com",
    }
    assert "SECRET" not in str(critical)


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


@pytest.fixture
def no_outbox(mocker: Any, flag_client: Mock) -> Mock:
    mocker.patch("unique_web_search.activity_record.is_running", return_value=False)
    activity_record._warn_outbox_down.cache_clear()
    metrics = Mock()
    mocker.patch(
        "unique_toolkit.experimental.resources.activity_records.metrics."
        "get_or_create_activity_event_outbox_metrics",
        return_value=metrics,
    )
    return metrics


@pytest.mark.asyncio
async def test_no_outbox__flag_off__stays_silent(
    mocker: Any,
    no_outbox: Mock,
    flag_client: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    flag_client.is_enabled.return_value = False
    enqueue_mock = mocker.patch("unique_web_search.activity_record.enqueue")
    tool = _tool(mocker, engine=_Engine(), elicitation=_elicitation(mocker, None))

    with caplog.at_level(logging.WARNING):
        await _run(tool)

    enqueue_mock.assert_not_called()
    no_outbox.record_failures.inc.assert_not_called()
    assert not caplog.records


@pytest.mark.asyncio
async def test_no_outbox__flag_on__counts_every_call_and_warns_once(
    mocker: Any, no_outbox: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    enqueue_mock = mocker.patch("unique_web_search.activity_record.enqueue")
    tool = _tool(mocker, engine=_Engine(), elicitation=_elicitation(mocker, None))

    with caplog.at_level(logging.WARNING):
        await _run(tool)
        await _run(tool)

    enqueue_mock.assert_not_called()
    assert no_outbox.record_failures.inc.call_count == 2
    assert (
        len(
            [
                r
                for r in caplog.records
                if "no Activity Records outbox" in r.getMessage()
            ]
        )
        == 1
    )


@pytest.mark.asyncio
async def test_no_outbox__flag_read_fails__stays_silent(
    mocker: Any,
    no_outbox: Mock,
    flag_client: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    flag_client.is_enabled.side_effect = RuntimeError("flag backend down")
    tool = _tool(mocker, engine=_Engine(), elicitation=_elicitation(mocker, None))

    with caplog.at_level(logging.DEBUG, logger="unique_web_search.activity_record"):
        await _run(tool)

    no_outbox.record_failures.inc.assert_not_called()
    assert [r for r in caplog.records if r.levelno >= logging.INFO] == []
    assert any("errorName=RuntimeError" in r.getMessage() for r in caplog.records)
    assert "flag backend down" not in caplog.text


@pytest.mark.asyncio
async def test_flag_off__records_nothing(
    mocker: Any, enqueue_mock: Mock, flag_client: Mock
) -> None:
    flag_client.is_enabled.return_value = False
    tool = _tool(mocker, engine=_Engine(), elicitation=_elicitation(mocker, None))

    await _run(tool)

    enqueue_mock.assert_not_called()
    flag_client.is_enabled.assert_awaited_once_with(
        "FEATURE_FLAG_ENABLE_WEB_SEARCH_ACTIVITY_RECORDS_UN_28965",
        company_id="company-1",
        user_id="user-1",
    )


@pytest.mark.asyncio
async def test_flag_read_error__records_nothing_and_search_still_runs(
    mocker: Any,
    enqueue_mock: Mock,
    flag_client: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    flag_client.is_enabled.side_effect = RuntimeError("flag backend down")
    engine = _Engine()
    search = mocker.spy(engine, "_legacy_search")
    tool = _tool(mocker, engine=engine, elicitation=_elicitation(mocker, None))

    with caplog.at_level(logging.ERROR):
        response = await tool.run(Mock(id="call-1", arguments={"query": "news"}))

    assert not response.error_message
    search.assert_called_once()
    enqueue_mock.assert_not_called()
    assert any("Could not start" in r.getMessage() for r in caplog.records)


def _record(engine_id: str) -> activity_record.ActivityRecord:
    return activity_record.ActivityRecord(
        source="chat",
        company_id="c",
        user_id="u",
        assistant_id="a",
        executor_mode="v1",
        engine_id=engine_id,
        engine_name=engine_id,
        critical_data={
            "chatId": "chat",
            "messageId": "msg",
            "toolCallId": "call",
            "userPrompt": "prompt",
            "args": {},
            "argumentScreening": {"status": "notRun", "reason": None},
            "elicitation": {"status": "notRun", "proposedQueries": []},
        },
    )


def _sent(enqueue_mock: Mock) -> list[dict[str, Any]]:
    return [row["data"]["criticalData"] for row in _rows(enqueue_mock)]


@pytest.mark.asyncio
async def test_custom_api_error_status__counts_as_a_response(
    mocker: Any, enqueue_mock: Mock
) -> None:
    from unique_web_search.services.search_engine.custom_api import (
        CustomAPI,
        CustomAPIConfig,
    )
    from unique_web_search.settings import CUSTOM_API_REQUEST_METHOD

    response = Mock(is_success=False, status_code=429)
    client = AsyncMock()
    client.request = AsyncMock(return_value=response)
    client_cm = AsyncMock()
    client_cm.__aenter__.return_value = client
    mocker.patch(
        "unique_web_search.services.search_engine.custom_api.AsyncClient",
        return_value=client_cm,
    )
    mocker.patch.object(CustomAPI, "_report_url_safety", AsyncMock())
    mocker.patch(
        "unique_web_search.services.search_engine.base.search_proxy_client_enabled",
        False,
    )
    engine = CustomAPI(
        CustomAPIConfig(
            api_endpoint="https://api.example.com/search",
            api_headers="{}",
            api_additional_query_params="{}",
            api_additional_body_params="{}",
            api_request_method=CUSTOM_API_REQUEST_METHOD.GET,
        )
    )
    record = _record("customApi")
    token = activity_record._current_record.set(record)
    try:
        with pytest.raises(ValueError, match="429"):
            await engine.search("news")
    finally:
        activity_record._current_record.reset(token)

    [row] = _sent(enqueue_mock)
    assert row["query"] == "news"
    assert row["responseReceived"] is True
    assert row["error"] == "ValueError"
    assert "destination" not in row["egress"]


@pytest.mark.asyncio
async def test_google_transport_failure__is_not_a_response(
    mocker: Any, enqueue_mock: Mock
) -> None:
    import httpx
    from unique_search_proxy_core.search_engines.google.schema import GoogleConfig

    from unique_web_search.services.search_engine.google import GoogleSearch

    settings = SimpleNamespace(
        is_configured=True,
        search_engine_id="cx",
        api_key="key",
        api_endpoint="https://www.googleapis.com/customsearch/v1",
    )
    mocker.patch(
        "unique_web_search.services.search_engine.google.get_google_search_settings",
        return_value=settings,
    )
    client = AsyncMock()
    client.get = AsyncMock(side_effect=httpx.ConnectError("down"))
    mocker.patch(
        "unique_web_search.services.search_engine.google.client_for",
        AsyncMock(return_value=client),
    )
    mocker.patch(
        "unique_web_search.services.search_engine.base.search_proxy_client_enabled",
        False,
    )
    record = _record("google")
    token = activity_record._current_record.set(record)
    try:
        assert await GoogleSearch(GoogleConfig()).search("news") == []
    finally:
        activity_record._current_record.reset(token)

    [row] = _sent(enqueue_mock)
    assert row["responseReceived"] is False
    assert "error" not in row


@pytest.mark.asyncio
async def test_google_parse_error_after_a_response__stays_received(
    mocker: Any, enqueue_mock: Mock
) -> None:
    from unique_search_proxy_core.search_engines.google.schema import GoogleConfig

    from unique_web_search.services.search_engine.google import GoogleSearch

    settings = SimpleNamespace(
        is_configured=True,
        search_engine_id="cx",
        api_key="key",
        api_endpoint="https://www.googleapis.com/customsearch/v1",
    )
    mocker.patch(
        "unique_web_search.services.search_engine.google.get_google_search_settings",
        return_value=settings,
    )
    client = AsyncMock()
    client.get = AsyncMock(return_value=Mock())
    mocker.patch(
        "unique_web_search.services.search_engine.google.client_for",
        AsyncMock(return_value=client),
    )
    mocker.patch.object(GoogleSearch, "_extract_urls", side_effect=ValueError("bad"))
    mocker.patch(
        "unique_web_search.services.search_engine.base.search_proxy_client_enabled",
        False,
    )
    record = _record("google")
    token = activity_record._current_record.set(record)
    try:
        assert await GoogleSearch(GoogleConfig()).search("news") == []
    finally:
        activity_record._current_record.reset(token)

    [row] = _sent(enqueue_mock)
    assert row["responseReceived"] is True
    assert "error" not in row


@pytest.mark.asyncio
async def test_overlapping_searches__keep_their_own_response_flag(
    enqueue_mock: Mock,
) -> None:
    record = _record("google")
    a_in = asyncio.Event()
    b_in = asyncio.Event()
    a_noted = asyncio.Event()

    async def first() -> None:
        with activity_record.search_request(
            "a", params=None, via_search_proxy=False, endpoint=None
        ):
            a_in.set()
            await b_in.wait()
            activity_record.note_response_received()
            a_noted.set()
            raise ValueError("429")

    async def second() -> None:
        await a_in.wait()
        with activity_record.search_request(
            "b", params=None, via_search_proxy=False, endpoint=None
        ):
            b_in.set()
            await a_noted.wait()
            activity_record.note_no_response()

    token = activity_record._current_record.set(record)
    try:
        await asyncio.gather(first(), second(), return_exceptions=True)
    finally:
        activity_record._current_record.reset(token)

    by_query = {row["query"]: row for row in _sent(enqueue_mock)}
    assert by_query["a"]["responseReceived"] is True
    assert by_query["a"]["error"] == "ValueError"
    assert by_query["b"]["responseReceived"] is False
    assert "error" not in by_query["b"]


@pytest.mark.asyncio
async def test_proxy_parse_failure__counts_as_a_response(
    mocker: Any, enqueue_mock: Mock
) -> None:
    from unique_search_proxy_core.search_engines.google.schema import GoogleConfig

    from unique_web_search.services.search_engine.google import GoogleSearch

    client = AsyncMock()
    client.search.search = AsyncMock(return_value=Mock())
    mocker.patch(
        "unique_web_search.services.search_engine.base.search_proxy_client_enabled",
        True,
    )
    mocker.patch(
        "unique_web_search.services.search_engine.base.env_settings.search_proxy_base_url",
        "http://proxy",
    )
    opener = mocker.patch(
        "unique_web_search.services.search_engine.base.open_search_proxy_client"
    )
    opener.return_value.__aenter__.return_value = client
    mocker.patch(
        "unique_web_search.services.search_engine.base.map_search_response",
        side_effect=ValueError("bad"),
    )
    record = _record("google")
    token = activity_record._current_record.set(record)
    try:
        with pytest.raises(ValueError, match="bad"):
            await GoogleSearch(GoogleConfig()).search("news")
    finally:
        activity_record._current_record.reset(token)

    [row] = _sent(enqueue_mock)
    assert row["responseReceived"] is True
    assert row["egress"]["viaSearchProxy"] is True
    assert row["error"] == "ValueError"


def _proxy_client_over(mocker: Any, handler: Any) -> None:
    from unique_web_search.services.proxy import bridge

    real = bridge.UniqueSearchProxyClient
    httpx_logger = logging.getLogger("httpx")
    mocker.patch.object(httpx_logger, "filters", list(httpx_logger.filters))
    mocker.patch.object(bridge.env_settings, "search_proxy_base_url", "http://proxy")
    mocker.patch.object(
        bridge,
        "UniqueSearchProxyClient",
        lambda **kwargs: real(
            http_client=httpx.AsyncClient(
                base_url="http://proxy", transport=httpx.MockTransport(handler)
            ),
            **kwargs,
        ),
    )


async def _proxy_search_in_record() -> None:
    from unique_web_search.services.proxy import open_search_proxy_client

    with activity_record.search_request(
        "news", params=None, via_search_proxy=True, endpoint="http://proxy"
    ):
        async with open_search_proxy_client(timeout=5) as client:
            await client.search.search(query="news", engine="google")


@pytest.mark.asyncio
async def test_proxy_error_status__counts_as_a_response(
    mocker: Any, enqueue_mock: Mock
) -> None:
    _proxy_client_over(mocker, lambda request: httpx.Response(429, json={}))
    token = activity_record._current_record.set(_record("google"))
    try:
        with pytest.raises(Exception) as raised:
            await _proxy_search_in_record()
    finally:
        activity_record._current_record.reset(token)

    [row] = _sent(enqueue_mock)
    assert row["responseReceived"] is True
    assert row["error"] == type(raised.value).__name__


@pytest.mark.asyncio
async def test_proxy_connection_failure__is_not_a_response(
    mocker: Any, enqueue_mock: Mock
) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    _proxy_client_over(mocker, refuse)
    token = activity_record._current_record.set(_record("google"))
    try:
        with pytest.raises(httpx.ConnectError):
            await _proxy_search_in_record()
    finally:
        activity_record._current_record.reset(token)

    [row] = _sent(enqueue_mock)
    assert row["responseReceived"] is False
    assert row["error"] == "ConnectError"


def _called_query(record: activity_record.ActivityRecord, query: str) -> None:
    with activity_record.active(record):
        activity_record.set_outcome("called")
        with activity_record.search_request(
            query, params=None, via_search_proxy=False, endpoint=None
        ):
            pass


_DIRECT = {
    "company_id": "company-1",
    "user_id": "user-1",
    "engine": SearchEngineType.GOOGLE,
    "args": {"query": "news"},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("call_origin", ["conduct", "api"])
@pytest.mark.parametrize(
    "ids",
    [
        {"assistant_id": "assistant-1", "chat_id": "chat-1", "message_id": "msg-1"},
        {"assistant_id": "assistant-1", "chat_id": "chat-1"},
        {"assistant_id": "", "chat_id": "", "message_id": ""},
        {},
    ],
    ids=["all-ids", "no-message", "blank", "none"],
)
async def test_start_direct__records_a_valid_query_row(
    enqueue_mock: Mock, call_origin: str, ids: dict[str, str]
) -> None:
    record = await activity_record.start_direct(
        **_DIRECT, call_origin=call_origin, **ids
    )

    assert record is not None
    _called_query(record, "news")

    event = _emitted(enqueue_mock)
    wire = event.to_wire()
    ActivityCloudEvent.from_wire(wire)
    critical = wire["data"]["criticalData"]
    assert event.source == call_origin
    assert wire["type"] == "web-search.query.sent"
    assert "callOrigin" not in critical
    assert critical["args"] == {"query": "news"}
    assert ("agent" in wire["data"]) is bool(ids.get("assistant_id"))
    assert ("chatId" in critical) is bool(ids.get("chat_id"))
    assert ("messageId" in critical) is bool(ids.get("message_id"))
    assert "subtype" not in wire["data"]
    assert not {"toolCallId", "userPrompt"} & critical.keys()


@pytest.mark.asyncio
async def test_start_direct__setup_failure__emits_tool_failed(
    enqueue_mock: Mock,
) -> None:
    record = await activity_record.start_direct(**_DIRECT, call_origin="api")

    assert record is not None
    with activity_record.active(record):
        activity_record.set_failure(RuntimeError("setup blew up"))

    wire = _emitted(enqueue_mock).to_wire()
    ActivityCloudEvent.from_wire(wire)
    assert wire["type"] == "web-search.tool.failed"
    assert wire["data"]["criticalData"]["reason"] == "RuntimeError"
    assert "setup blew up" not in str(wire)


@pytest.mark.asyncio
@pytest.mark.parametrize(("company_id", "user_id"), [("", "user-1"), ("company-1", "")])
async def test_start_direct__unattributed__emits_nothing(
    enqueue_mock: Mock, flag_client: Mock, company_id: str, user_id: str
) -> None:
    record = await activity_record.start_direct(
        **{**_DIRECT, "company_id": company_id, "user_id": user_id},
        call_origin="api",
    )

    assert record is None
    enqueue_mock.assert_not_called()
    flag_client.is_enabled.assert_not_called()


@pytest.mark.asyncio
async def test_start__blank_assistant_id__omits_agent_instead_of_dropping_the_row(
    mocker: Any, enqueue_mock: Mock
) -> None:
    tool = _tool(
        mocker,
        engine=_Engine(),
        elicitation=_elicitation(mocker, ElicitationStatus.DECLINED),
    )
    tool._event.payload.assistant_id = ""

    await _run(tool)

    wire = _emitted(enqueue_mock).to_wire()
    ActivityCloudEvent.from_wire(wire)
    assert wire["type"] == "web-search.tool.denied"
    assert "agent" not in wire["data"]
