"""Cases ported from ``activity-event.schema.spec.ts`` so both validators agree."""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from unique_toolkit.experimental.resources.activity_records import (
    ACTIVITY_METADATA_MAX_LENGTH,
    ActivityActor,
    ActivityCloudEvent,
    ActivityEventData,
)

pytestmark = pytest.mark.ai

_VALID_EVENT: dict[str, Any] = {
    "specversion": "1.0",
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "source": "billing-service",
    "type": "ai.unique.activity.invoice.approved",
    "time": "2026-07-14T12:00:00.000Z",
    "data": {
        "actor": {"id": "user-1", "type": "user"},
        "companyId": "company-1",
        "targetType": "invoice",
        "targetId": "123",
    },
}

_MIN_DATA: dict[str, Any] = {
    "actor": _VALID_EVENT["data"]["actor"],
    "companyId": "company-1",
}


def _event(**top: Any) -> dict[str, Any]:
    return {**copy.deepcopy(_VALID_EVENT), **top}


def _with_data(**data: Any) -> dict[str, Any]:
    return _event(data={**copy.deepcopy(_VALID_EVENT["data"]), **data})


def _with_actor(**actor: Any) -> dict[str, Any]:
    return _with_data(actor=actor)


def _is_valid(payload: dict[str, Any]) -> bool:
    try:
        ActivityCloudEvent.model_validate(payload)
    except ValidationError:
        return False
    return True


def _is_wire_valid(payload: dict[str, Any]) -> bool:
    """True when the strict wire check (camelCase keys only, like zod) accepts ``payload``."""
    try:
        ActivityCloudEvent.from_wire(payload)
    except ValidationError:
        return False
    return True


# (path, cap) -> builds a payload that sets the field to a string of a given length
_CAP_CASES: list[tuple[str, int, Any]] = [
    (
        "actor.id",
        ACTIVITY_METADATA_MAX_LENGTH["identifier"],
        lambda v: _with_actor(id=v, type="user"),
    ),
    (
        "actor.ip",
        ACTIVITY_METADATA_MAX_LENGTH["ip"],
        lambda v: _with_actor(id="u", type="user", ip=v),
    ),
    (
        "agent.id",
        ACTIVITY_METADATA_MAX_LENGTH["identifier"],
        lambda v: _with_data(agent={"id": v}),
    ),
    (
        "targetType",
        ACTIVITY_METADATA_MAX_LENGTH["identifier"],
        lambda v: _with_data(targetType=v),
    ),
    (
        "targetId",
        ACTIVITY_METADATA_MAX_LENGTH["identifier"],
        lambda v: _with_data(targetId=v),
    ),
    (
        "targetName",
        ACTIVITY_METADATA_MAX_LENGTH["text"],
        lambda v: _with_data(targetName=v),
    ),
    ("subtype", ACTIVITY_METADATA_MAX_LENGTH["text"], lambda v: _with_data(subtype=v)),
    (
        "correlationId",
        ACTIVITY_METADATA_MAX_LENGTH["identifier"],
        lambda v: _with_data(correlationId=v),
    ),
]
_CAP_IDS = [c[0] for c in _CAP_CASES]


class TestValidEvents:
    def test_parses_full_event(self) -> None:
        result = ActivityCloudEvent.model_validate(
            _event(
                datacontenttype="application/json",
                data={
                    "actor": {"id": "user-1", "type": "user", "ip": "203.0.113.10"},
                    "companyId": "company-1",
                    "targetType": "invoice",
                    "targetId": "123",
                    "correlationId": "trace-abc",
                    "criticalData": {"toolName": "search", "args": {"q": "hello"}},
                },
            )
        )

        assert str(result.id) == _VALID_EVENT["id"]
        assert result.type == "ai.unique.activity.invoice.approved"
        assert result.data.company_id == "company-1"
        assert result.data.target_type == "invoice"
        assert result.data.target_id == "123"
        assert result.data.correlation_id == "trace-abc"
        assert result.data.actor.ip == "203.0.113.10"
        assert result.data.critical_data == {
            "toolName": "search",
            "args": {"q": "hello"},
        }

    def test_parses_minimal_event(self) -> None:
        result = ActivityCloudEvent.model_validate(_VALID_EVENT)

        assert result.datacontenttype == "application/json"
        assert result.data.agent is None
        assert result.data.correlation_id is None
        assert result.data.actor.ip is None
        assert result.data.critical_data is None

    def test_accepts_service_actor(self) -> None:
        result = ActivityCloudEvent.model_validate(
            _with_actor(id="mcp-hub", type="service")
        )
        assert result.data.actor.type == "service"

    def test_accepts_schemaless_critical_data(self) -> None:
        result = ActivityCloudEvent.model_validate(
            _with_data(
                criticalData={
                    "nested": True,
                    "count": 1,
                    "none": None,
                    "list": [1, "a"],
                }
            )
        )
        assert result.data.critical_data == {
            "nested": True,
            "count": 1,
            "none": None,
            "list": [1, "a"],
        }

    @pytest.mark.parametrize(("field", "max_length", "make"), _CAP_CASES, ids=_CAP_IDS)
    def test_accepts_field_at_exactly_its_cap(
        self, field: str, max_length: int, make: Any
    ) -> None:
        assert _is_valid(make("x" * max_length))

    def test_does_not_cap_company_id(self) -> None:
        assert _is_valid(_with_data(companyId="x" * 10_000))

    def test_parses_mcp_tool_call_with_agent_and_display_fields(self) -> None:
        result = ActivityCloudEvent.model_validate(
            _event(
                source="mcp-hub",
                type="ai.unique.activity.mcp.tool.called",
                data={
                    "actor": {"id": "user-1", "type": "user", "ip": "203.0.113.7"},
                    "agent": {"id": "space-1"},
                    "companyId": "company-1",
                    "targetType": "mcpServer",
                    "targetId": "cm3k9x1p40000v8h2q7r5nz1a",
                    "targetName": "Outlook Semantic MCP",
                    "subtype": "search_emails",
                },
            )
        )

        assert result.data.actor.ip == "203.0.113.7"
        assert result.data.agent is not None
        assert result.data.agent.id == "space-1"
        assert result.data.target_name == "Outlook Semantic MCP"
        assert result.data.subtype == "search_emails"

    def test_parses_event_without_target(self) -> None:
        result = ActivityCloudEvent.model_validate(
            _event(
                source="admin-service",
                type="admin.settings.viewed",
                data={
                    "actor": {"id": "user-1", "type": "user"},
                    "agent": {"id": "space-1"},
                    "companyId": "company-1",
                },
            )
        )
        assert result.data.target_type is None
        assert result.data.target_id is None

    def test_allows_target_name_without_target_id(self) -> None:
        result = ActivityCloudEvent.model_validate(
            _event(data={**_MIN_DATA, "targetName": "Google"})
        )
        assert result.data.target_name == "Google"


class TestInvalidEvents:
    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param(_event(specversion="0.3"), id="specversion"),
            pytest.param(_event(id="not-a-uuid"), id="id"),
            pytest.param(
                _event(id="550e8400-e29b-01d4-a716-446655440000"), id="id-version-0"
            ),
            pytest.param(_event(source=""), id="source"),
            pytest.param(_event(source="billing:service"), id="source-with-colon"),
            pytest.param(_event(source="billing_service"), id="source-with-underscore"),
            pytest.param(_event(type=""), id="type"),
            pytest.param(_event(time="yesterday"), id="time"),
            pytest.param(_event(datacontenttype="text/plain"), id="datacontenttype"),
            pytest.param(_with_data(companyId=""), id="data.companyId"),
            pytest.param(_with_data(targetType=""), id="data.targetType"),
            pytest.param(_with_data(targetId=""), id="data.targetId"),
            pytest.param(_with_data(correlationId=""), id="data.correlationId"),
            pytest.param(_with_actor(id="", type="user"), id="data.actor.id"),
            pytest.param(_with_actor(id="user-1", type="bot"), id="data.actor.type"),
            pytest.param(
                _with_actor(id="user-1", type="user", ip=""), id="data.actor.ip"
            ),
            pytest.param(_with_data(agent={"id": ""}), id="data.agent.id"),
            pytest.param(_with_data(targetName=""), id="data.targetName"),
            pytest.param(_with_data(subtype=""), id="data.subtype"),
        ],
    )
    def test_rejects_invalid_field(self, payload: dict[str, Any]) -> None:
        assert not _is_valid(payload)

    def test_rejects_naive_datetime_time(self) -> None:
        assert not _is_valid(_event(time=datetime(2026, 7, 14, 12, 0)))

    @pytest.mark.parametrize("field", ["source", "type", "data"])
    def test_rejects_missing_top_level_field(self, field: str) -> None:
        payload = _event()
        del payload[field]
        assert not _is_valid(payload)

    @pytest.mark.parametrize("field", ["actor", "companyId"])
    def test_rejects_missing_data_field(self, field: str) -> None:
        data = copy.deepcopy(_VALID_EVENT["data"])
        del data[field]
        assert not _is_valid(_event(data=data))

    def test_rejects_non_object_critical_data(self) -> None:
        assert not _is_valid(_with_data(criticalData=["a", 1]))

    @pytest.mark.parametrize(("field", "max_length", "make"), _CAP_CASES, ids=_CAP_IDS)
    def test_rejects_field_one_character_over_its_cap(
        self, field: str, max_length: int, make: Any
    ) -> None:
        assert not _is_valid(make("x" * (max_length + 1)))

    def test_counts_length_in_utf16_code_units_like_js(self) -> None:
        # "😀" is 1 code point in Python but 2 UTF-16 units in JS.
        assert _is_valid(_with_data(correlationId="😀" * 64))
        assert not _is_valid(_with_data(correlationId="😀" * 65))

    @pytest.mark.parametrize(
        "target",
        [
            pytest.param({"targetType": "mcpServer"}, id="targetType-without-targetId"),
            pytest.param(
                {"targetId": "cm3k9x1p40000v8h2q7r5nz1a"},
                id="targetId-without-targetType",
            ),
        ],
    )
    def test_rejects_half_a_target(self, target: dict[str, Any]) -> None:
        assert not _is_valid(_event(data={**_MIN_DATA, **target}))

    @pytest.mark.parametrize(
        ("payload", "unknown_keys"),
        [
            pytest.param(
                _with_data(toolName="search"),
                [("data", "toolName")],
                id="free-form-data-field",
            ),
            pytest.param(
                _event(receivedAt="2026-07-14T12:00:01.000Z"),
                [("receivedAt",)],
                id="receivedAt",
            ),
            pytest.param(
                _event(processedAt="2026-07-14T12:00:01.000Z"),
                [("processedAt",)],
                id="processedAt",
            ),
            pytest.param(
                _event(unexpectedField=True), [("unexpectedField",)], id="top-level"
            ),
            pytest.param(
                _with_actor(id="u", type="user", email=""),
                [("data", "actor", "email")],
                id="actor.email",
            ),
            pytest.param(
                _with_actor(id="u", type="user", name="Lorand"),
                [("data", "actor", "name")],
                id="actor.name",
            ),
            pytest.param(
                _with_actor(id="u", type="user", externalId="acme-hr-4471"),
                [("data", "actor", "externalId")],
                id="actor.externalId",
            ),
            pytest.param(
                _with_data(agent={"id": "space-1", "name": "Unique AI"}),
                [("data", "agent", "name")],
                id="agent.name",
            ),
            pytest.param(
                _with_data(agent={"id": "space-1", "slug": "unique-ai"}),
                [("data", "agent", "slug")],
                id="agent.slug",
            ),
            pytest.param(
                _event(
                    data={
                        "actor": _VALID_EVENT["data"]["actor"],
                        "companyId": "company-1",
                        "companyid": "company-1",
                        "targettype": "invoice",
                        "targetid": "123",
                    }
                ),
                [("data", "companyid"), ("data", "targettype"), ("data", "targetid")],
                id="lowercase-legacy-names",
            ),
        ],
    )
    def test_rejects_unknown_key_and_only_because_of_it(
        self, payload: dict[str, Any], unknown_keys: list[tuple[str, ...]]
    ) -> None:
        assert not _is_valid(payload)

        without = copy.deepcopy(payload)
        for path in unknown_keys:
            holder = without
            for part in path[:-1]:
                holder = holder[part]
            del holder[path[-1]]
        assert _is_valid(without)

    @pytest.mark.parametrize(
        ("wire_key", "python_name"),
        [
            ("companyId", "company_id"),
            ("targetType", "target_type"),
            ("targetId", "target_id"),
            ("targetName", "target_name"),
            ("correlationId", "correlation_id"),
            ("criticalData", "critical_data"),
        ],
    )
    def test_from_wire_rejects_a_python_field_name_that_model_validate_accepts(
        self, wire_key: str, python_name: str
    ) -> None:
        payload = _with_data(
            targetName="Invoice", correlationId="trace-1", criticalData={"k": "v"}
        )
        assert _is_wire_valid(payload)

        payload["data"][python_name] = payload["data"].pop(wire_key)

        assert _is_valid(payload)
        assert not _is_wire_valid(payload)

    def test_from_wire_rejects_lowercase_legacy_names(self) -> None:
        payload = _event(
            data={
                "actor": {"id": "user-1", "type": "user"},
                "companyId": "company-1",
                "companyid": "company-1",
                "targettype": "invoice",
                "targetid": "123",
            }
        )

        assert not _is_wire_valid(payload)
        assert not _is_valid(payload)
        for key in ("companyid", "targettype", "targetid"):
            del payload["data"][key]
        assert _is_wire_valid(payload)


class TestWireAndPythonNames:
    def test_keyword_construction_by_python_names_works(self) -> None:
        built = ActivityCloudEvent(
            source="billing-service",
            type="ai.unique.activity.invoice.approved",
            data=ActivityEventData(
                actor=ActivityActor(id="user-1", type="user"),
                company_id="company-1",
                target_type="invoice",
                target_id="123",
                critical_data={"k": "v"},
            ),
        )

        assert built.data.company_id == "company-1"
        assert built.to_wire()["data"]["companyId"] == "company-1"

    def test_model_validate_accepts_python_field_names(self) -> None:
        payload = _event(
            data={
                "actor": {"id": "user-1", "type": "user"},
                "company_id": "company-1",
                "target_type": "invoice",
                "target_id": "123",
            }
        )

        assert _is_valid(payload)
        assert not _is_wire_valid(payload)

    def test_from_wire_round_trips_to_wire(self) -> None:
        built = ActivityCloudEvent.from_wire(_event())

        assert ActivityCloudEvent.from_wire(built.to_wire()) == built


class TestEventId:
    @pytest.mark.parametrize(
        "event_id",
        [
            pytest.param("550e8400-e29b-41d4-a716-446655440000", id="v4"),
            pytest.param("018f2b1e-8f4c-7a3b-9c4d-1234567890ab", id="v7"),
            pytest.param("00000000-0000-0000-0000-000000000000", id="nil"),
            pytest.param("ffffffff-ffff-ffff-ffff-ffffffffffff", id="max"),
        ],
    )
    def test_accepts_what_zod_uuid_accepts(self, event_id: str) -> None:
        assert _is_valid(_event(id=event_id))

    @pytest.mark.parametrize(
        "event_id",
        [
            pytest.param("550e8400-e29b-41d4-c716-446655440000", id="non-rfc-variant"),
            pytest.param("550e8400-e29b-91d4-a716-446655440000", id="version-9"),
            pytest.param("not-a-uuid", id="malformed"),
        ],
    )
    def test_rejects_what_zod_uuid_rejects(self, event_id: str) -> None:
        assert not _is_valid(_event(id=event_id))

    def test_the_generated_default_is_a_v4_uuid(self) -> None:
        built = ActivityCloudEvent(
            source="web-search",
            type="web-search.tool.called",
            data=ActivityEventData(
                actor=ActivityActor(id="user-1", type="user"), company_id="company-1"
            ),
        )

        assert built.id.version == 4


class TestDefaults:
    @pytest.fixture
    def data(self) -> ActivityEventData:
        return ActivityEventData(
            actor=ActivityActor(id="user-1", type="user"), company_id="company-1"
        )

    def test_fills_envelope_fields(self, data: ActivityEventData) -> None:
        before = datetime.now(UTC)
        built = ActivityCloudEvent(
            source="web-search", type="web-search.tool.called", data=data
        )
        after = datetime.now(UTC)

        assert built.specversion == "1.0"
        assert built.datacontenttype == "application/json"
        assert built.id.version == 4
        assert before <= built.time <= after

    def test_generates_a_new_id_per_event(self, data: ActivityEventData) -> None:
        first = ActivityCloudEvent(source="web-search", type="t", data=data)
        second = ActivityCloudEvent(source="web-search", type="t", data=data)
        assert first.id != second.id

    @pytest.mark.parametrize("field", ["specversion", "id", "time"])
    def test_fills_missing_envelope_field(self, field: str) -> None:
        payload = _event()
        del payload[field]
        assert _is_valid(payload)
