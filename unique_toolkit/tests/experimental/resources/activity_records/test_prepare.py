"""Cases ported from the Node ``fit-event-to-limit``, ``truncate-json-value``, config and
relay batching specs, so both implementations prepare events identically."""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, SpanContext
from pydantic import ValidationError

from unique_toolkit.experimental.resources.activity_records import (
    ACTIVITY_METADATA_MAX_LENGTH,
    ActivityActor,
    ActivityCloudEvent,
    ActivityEventData,
)
from unique_toolkit.experimental.resources.activity_records.config import (
    DEFAULT_MAX_BATCH_SIZE_BYTES,
    DEFAULT_MAX_DATA_SIZE_BYTES,
    EVENT_ENVELOPE_RESERVE_BYTES,
    MIN_MAX_DATA_SIZE_BYTES,
    ActivityRecordsConfig,
)
from unique_toolkit.experimental.resources.activity_records.json_size import (
    MAX_JSON_DEPTH,
    json_byte_length,
    json_byte_length_if_within_limit,
    truncate_json_value_to_bytes,
)
from unique_toolkit.experimental.resources.activity_records.prepare import (
    fit_event_to_limit,
    fit_events_to_limit,
    is_oversized,
    prepare_rows,
    split_into_batches_under_limit,
    to_last_error,
    with_correlation_id,
    with_postgres_safe_strings,
)

pytestmark = pytest.mark.ai

_IDENTIFIER = ACTIVITY_METADATA_MAX_LENGTH["identifier"]
_IP = ACTIVITY_METADATA_MAX_LENGTH["ip"]
_TEXT = ACTIVITY_METADATA_MAX_LENGTH["text"]


def byte_length(value: Any) -> int:
    """Size of the compact serialisation; a lone surrogate counts the 3 bytes of U+FFFD."""
    text = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return len(text.encode("utf-8", "surrogatepass"))


def wire_event(**data: Any) -> dict[str, Any]:
    return {
        "specversion": "1.0",
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "source": "billing-service",
        "type": "ai.unique.activity.invoice.approved",
        "time": "2026-07-14T12:00:00.000Z",
        "data": {
            "actor": {"id": "user-1", "type": "user"},
            "companyId": "company-1",
            **data,
        },
    }


def model_event(**data: Any) -> ActivityCloudEvent:
    return ActivityCloudEvent(
        source="billing-service",
        type="ai.unique.activity.invoice.approved",
        data=ActivityEventData(
            actor=ActivityActor(id="user-1", type="user"),
            company_id="company-1",
            **data,
        ),
    )


class TestFitEventToLimitCriticalData:
    def test_leaves_critical_data_untouched_when_data_already_fits(self) -> None:
        event = wire_event(criticalData={"a": 1})

        result = fit_event_to_limit(event, byte_length(event["data"]) + 100)

        assert result.event is event
        assert result.critical_data_truncated is False

    def test_shrinks_and_wraps_critical_data_once_data_exceeds_the_budget(self) -> None:
        event = wire_event(criticalData={"toolResult": "x" * 10_000})

        result = fit_event_to_limit(event, 400)

        assert result.critical_data_truncated is True
        wrapper = result.event["data"]["criticalData"]
        assert wrapper["truncated"] is True
        assert wrapper["maxDataSizeBytes"] == 400
        assert wrapper["originalSizeBytesAtLeast"] == 401
        assert wrapper["value"]["toolResult"]
        assert ("x" * 10_000).startswith(wrapper["value"]["toolResult"])
        assert byte_length(result.event["data"]) <= 400

    def test_is_a_no_op_when_data_has_no_critical_data(self) -> None:
        event = wire_event(targetName="x" * _TEXT)

        result = fit_event_to_limit(event, 10)

        assert result.event["data"]["targetName"] == "x" * _TEXT
        assert result.critical_data_truncated is False
        assert "criticalData" not in result.event["data"]

    def test_preserves_sibling_fields(self) -> None:
        event = wire_event(
            targetName="invoice-service", criticalData={"toolResult": "x" * 10_000}
        )

        result = fit_event_to_limit(event, 400)

        assert result.event["data"]["targetName"] == "invoice-service"

    def test_defaults_the_limit_to_the_default_max_data_size(self) -> None:
        event = wire_event(
            criticalData={"toolResult": "x" * DEFAULT_MAX_DATA_SIZE_BYTES}
        )

        result = fit_event_to_limit(event)

        assert result.critical_data_truncated is True
        assert result.event["data"]["criticalData"]["value"]["toolResult"]
        assert byte_length(result.event["data"]) <= DEFAULT_MAX_DATA_SIZE_BYTES

    def test_fits_a_multi_megabyte_field_without_sizing_it(self) -> None:
        event = wire_event(criticalData={"toolResult": "x" * 5_000_000})

        result = fit_event_to_limit(event, 400)

        assert result.event["data"]["criticalData"]["value"]["toolResult"]
        assert byte_length(result.event["data"]) <= 400

    def test_shrinks_into_the_budget_left_after_the_other_fields(self) -> None:
        event = wire_event(
            targetName="x" * _TEXT, criticalData={"toolResult": "y" * 10_000}
        )

        result = fit_event_to_limit(event, 500)

        assert len(result.event["data"]["targetName"]) == _TEXT
        assert result.critical_data_truncated is True
        value = result.event["data"]["criticalData"]["value"]["toolResult"]
        assert value and ("y" * 10_000).startswith(value)
        assert byte_length(result.event["data"]) <= 500

    def test_never_drops_the_event_when_siblings_alone_exceed_the_budget(self) -> None:
        event = wire_event(companyId="c" * 5_000_000, criticalData={"toolResult": "y"})

        result = fit_event_to_limit(event, 400)

        assert result.critical_data_truncated is True
        assert result.event["data"]["criticalData"]["value"] is None


class TestTooDeepCriticalData:
    @staticmethod
    def _nested(depth: int) -> dict[str, Any]:
        value: dict[str, Any] = {"leaf": 1}
        for _ in range(depth):
            value = {"d": value}
        return value

    def test_a_depth_cut_is_marked_and_listed_once_without_being_oversized(
        self,
    ) -> None:
        deep = self._nested(MAX_JSON_DEPTH + 5)
        event = wire_event(criticalData=deep)

        result = fit_events_to_limit([event], DEFAULT_MAX_DATA_SIZE_BYTES)

        assert len(result.truncated_events) == 1
        fitted = result.events[0]
        assert not is_oversized(fitted, DEFAULT_MAX_DATA_SIZE_BYTES)
        critical = fitted["data"]["criticalData"]
        assert critical["truncated"] is True
        assert critical["originalSizeBytesAtLeast"] == byte_length(event["data"])
        assert critical["value"] is not None

    def test_a_depth_cut_together_with_a_byte_cut_stays_within_the_depth_limit(
        self,
    ) -> None:
        cap = 2000
        event = wire_event(
            criticalData={"big": "x" * 5000, "deep": self._nested(MAX_JSON_DEPTH + 50)}
        )

        result = fit_event_to_limit(event, cap)

        assert result.critical_data_truncated
        assert not is_oversized(result.event, cap)

    def test_an_absurdly_deep_value_is_cut_without_overflowing_the_stack(self) -> None:
        event = wire_event(criticalData=self._nested(5000))

        result = fit_event_to_limit(event, DEFAULT_MAX_DATA_SIZE_BYTES)

        assert result.critical_data_truncated
        assert not is_oversized(result.event, DEFAULT_MAX_DATA_SIZE_BYTES)

    def test_a_value_inside_the_depth_limit_is_untouched(self) -> None:
        event = wire_event(criticalData=self._nested(MAX_JSON_DEPTH - 10))

        result = fit_event_to_limit(event, DEFAULT_MAX_DATA_SIZE_BYTES)

        assert not result.critical_data_truncated
        assert result.event is event

    def test_a_depth_cut_with_a_lone_surrogate_is_measured(self) -> None:
        event = wire_event(
            criticalData={"note": "\ud800", "deep": self._nested(MAX_JSON_DEPTH + 5)}
        )

        result = fit_event_to_limit(event, DEFAULT_MAX_DATA_SIZE_BYTES)

        critical = result.event["data"]["criticalData"]
        assert critical["originalSizeBytesAtLeast"] == byte_length(event["data"])


class TestJsonbNumberSize:
    @pytest.mark.parametrize(
        ("number", "size"),
        [
            (1e300, 301),
            (2.5e20, 21),
            (-2.5e20, 22),
            (1.5e16, 17),
            (1e16, 17),
            (1e-7, 9),
            (0.1, 3),
            (1.0, 3),
            (123456.789, 10),
        ],
    )
    def test_sizes_a_float_as_jsonb_prints_it(self, number: float, size: int) -> None:
        assert json_byte_length_if_within_limit(number, float("inf")) == size

    def test_a_fitted_event_stays_under_the_cap_after_the_round_trip(self) -> None:
        cap = 20_000
        event = wire_event(criticalData={"values": [2.5e20] * 2000})

        fitted = fit_event_to_limit(event, cap).event

        # jsonb stores 2.5e20 as a numeric and prints it back as an integer.
        read_back = json.loads(
            json.dumps(fitted["data"]), parse_float=lambda text: int(float(text))
        )
        assert fitted["data"]["criticalData"]["truncated"] is True
        assert byte_length(read_back) <= cap


class TestSizeConstants:
    def test_min_max_data_size_holds_every_field_at_its_cap(self) -> None:
        event = wire_event(
            actor={"id": "x" * _IDENTIFIER, "type": "user", "ip": "x" * _IP},
            agent={"id": "x" * _IDENTIFIER},
            companyId="x" * _IDENTIFIER,
            targetType="x" * _IDENTIFIER,
            targetId="x" * _IDENTIFIER,
            targetName="x" * _TEXT,
            subtype="x" * _TEXT,
            correlationId="x" * _IDENTIFIER,
            criticalData={"toolResult": "x" * 10_000},
        )

        result = fit_event_to_limit(event, MIN_MAX_DATA_SIZE_BYTES)

        assert result.event["data"]["criticalData"]["value"]["toolResult"]
        assert byte_length(result.event["data"]) <= MIN_MAX_DATA_SIZE_BYTES

    def test_values_equal_the_node_constants(self) -> None:
        assert MIN_MAX_DATA_SIZE_BYTES == 1626
        assert EVENT_ENVELOPE_RESERVE_BYTES == 416


class TestTruncateJsonValueToBytes:
    def test_returns_the_value_unchanged_when_it_fits(self) -> None:
        value = {"a": 1, "b": "short"}

        assert truncate_json_value_to_bytes(value, byte_length(value)) == value
        assert truncate_json_value_to_bytes({"a": 1}, 1000) == {"a": 1}

    def test_cuts_a_string_to_the_byte_budget(self) -> None:
        result = truncate_json_value_to_bytes("abcdefghij", byte_length("abcde"))

        assert result == "abcde"

    def test_never_exceeds_the_budget_for_multi_byte_characters(self) -> None:
        result = truncate_json_value_to_bytes("€" * 10, 10)

        assert byte_length(result) <= 10

    def test_keeps_astral_characters_whole(self) -> None:
        budget = byte_length("😀😀")

        result = truncate_json_value_to_bytes("😀" * 5, budget)

        assert result == "😀😀"

    def test_returns_an_empty_string_when_even_the_quotes_do_not_fit(self) -> None:
        assert truncate_json_value_to_bytes("anything", 1) == ""

    def test_cuts_a_long_mixed_string(self) -> None:
        unit = "a€😀"
        value = unit * 20_000
        budget = byte_length(unit * 1_000) + 1

        result = truncate_json_value_to_bytes(value, budget)

        assert byte_length(result) <= budget
        assert value.startswith(result)
        assert len(result) >= 3_000

    def test_cuts_a_multi_megabyte_string_to_a_small_budget(self) -> None:
        value = "a" * 5_000_000

        result = truncate_json_value_to_bytes(value, 100)

        assert byte_length(result) == 100
        assert value.startswith(result)

    def test_keeps_the_leading_array_items_that_fit(self) -> None:
        value = ["aaaa", "bbbb", "cccc", "dddd"]

        result = truncate_json_value_to_bytes(value, byte_length(["aaaa", "bbbb"]))

        assert result == ["aaaa", "bbbb"]

    def test_truncates_the_boundary_array_item_when_there_is_room(self) -> None:
        budget = byte_length(["a", "bb"])

        result = truncate_json_value_to_bytes(["a", "bbbbbbbbbb"], budget)

        assert result[0] == "a"
        assert isinstance(result[1], str)
        assert result[1] and "bbbbbbbbbb".startswith(result[1])
        assert byte_length(result) <= budget

    def test_returns_an_empty_array_when_nothing_fits(self) -> None:
        assert truncate_json_value_to_bytes(["aaaaaaaaaa"], 1) == []

    def test_recurses_into_nested_arrays(self) -> None:
        budget = byte_length([[1, 2]])

        result = truncate_json_value_to_bytes([list(range(1, 11))], budget)

        assert result == [[1, 2]]
        assert byte_length(result) <= budget

    def test_truncates_the_largest_object_field_first(self) -> None:
        value = {"small": "keep-me", "huge": "x" * 1000}
        budget = byte_length(value["small"]) + 40

        result = truncate_json_value_to_bytes(value, budget)

        assert result["small"] == "keep-me"
        assert result["huge"] and value["huge"].startswith(result["huge"])
        assert byte_length(result) <= budget

    def test_drops_a_field_that_cannot_be_shrunk_to_fit(self) -> None:
        value = {"a": "a" * 1000, "b": "keep"}

        result = truncate_json_value_to_bytes(value, byte_length({"b": "keep"}))

        assert result == {"b": "keep"}

    def test_recurses_into_nested_objects(self) -> None:
        budget = byte_length({"outer": {"inner": "xxxx"}})

        result = truncate_json_value_to_bytes({"outer": {"inner": "x" * 1000}}, budget)

        assert result["outer"]["inner"]
        assert ("x" * 1000).startswith(result["outer"]["inner"])
        assert byte_length(result) <= budget

    def test_shrinks_an_object_with_many_keys_keeping_the_smallest_whole(self) -> None:
        value = {f"key{i}": "short" if i % 2 == 0 else "x" * 1000 for i in range(500)}
        budget = byte_length({f"key{i * 2}": "short" for i in range(250)})

        result = truncate_json_value_to_bytes(value, budget)

        assert byte_length(result) <= budget
        assert result["key0"] == "short"

    def test_passes_numbers_booleans_and_null_through_even_over_budget(self) -> None:
        assert truncate_json_value_to_bytes(123_456, 1) == 123_456
        assert truncate_json_value_to_bytes(True, 1) is True
        assert truncate_json_value_to_bytes(None, 0) is None

    def test_cuts_a_string_full_of_escaped_characters(self) -> None:
        value = '"quoted"\\back\nslash\ttab\x01control€3byte😀astral'
        budget = byte_length(value[:10])

        result = truncate_json_value_to_bytes(value, budget)

        assert byte_length(result) <= budget
        assert value.startswith(result)

    def test_keeps_an_escape_heavy_string_whole_when_it_fits(self) -> None:
        value = '"\\\n\t€😀'

        assert truncate_json_value_to_bytes(value, byte_length(value)) == value

    def test_counts_a_lone_surrogate_as_three_bytes(self) -> None:
        value = "\ud800a"
        budget = byte_length("\ud800")

        result = truncate_json_value_to_bytes(value, budget)

        assert byte_length(result) <= budget
        assert value.startswith(result)

    def test_stays_within_budget_with_several_oversized_siblings(self) -> None:
        value = {"first": "a" * 1000, "second": "b" * 2000}
        budget = byte_length(value["first"]) - 100

        result = truncate_json_value_to_bytes(value, budget)

        assert byte_length(result) <= budget
        assert result["second"] and value["second"].startswith(result["second"])
        assert all(isinstance(item, str) for item in result.values())

    def test_stays_within_budget_for_a_realistic_mixed_payload(self) -> None:
        value = {
            "toolName": "search",
            "args": {"query": "x" * 5000, "filters": ["a", "b", "c"]},
            "toolResult": {"items": [{"id": i, "text": "y" * 200} for i in range(200)]},
        }

        result = truncate_json_value_to_bytes(value, 2000)

        assert result["toolResult"]["items"]
        assert byte_length(result) <= 2000

    def test_does_not_overflow_the_stack_on_a_very_deep_value(self) -> None:
        value: dict[str, Any] = {}
        for _ in range(3000):
            value = {"a": value}

        assert json_byte_length_if_within_limit(value, float("inf")) is None
        truncate_json_value_to_bytes(value, 10_000_000)

    def test_accepts_a_value_at_the_depth_ceiling(self) -> None:
        value: Any = "x"
        for _ in range(MAX_JSON_DEPTH):
            value = [value]

        assert json_byte_length_if_within_limit(value, float("inf")) == byte_length(
            value
        )


_SAMPLES: list[Any] = [
    None,
    True,
    False,
    0,
    -1,
    3.14,
    1.5,
    -1.5,
    "",
    "hello world",
    "café ☕ 日本語",
    "a" * 10_000,
    'quote:" backslash:\\ tab:\t newline:\n cr:\r formfeed:\f backspace:\b',
    "\x00\x01\x1f control chars",
    "emoji: 😀 flag: 🇨🇭",
    "unpaired high: \ud800 unpaired low: \udc00",
    {},
    [],
    {
        "a": [1, 2, {"b": "x", "c": [None, False, "café"]}],
        "d": {"e": {"f": []}, "g": {}},
    },
    {"k\ud800": "v", "ключ": ["значение"]},
    [1, "two", {"three": 3}, [4, 5], None, False],
    {
        "toolName": "search",
        "args": {"query": "x" * 5000, "filters": ["a", "b", "c"], "emoji": "🔍"},
        "toolResult": {"items": [{"id": i, "text": "y" * 200} for i in range(50)]},
    },
]


class TestJsonByteLengthIfWithinLimit:
    @pytest.mark.parametrize("sample", _SAMPLES, ids=lambda s: repr(s)[:30])
    def test_matches_the_serialised_size(self, sample: Any) -> None:
        assert json_byte_length_if_within_limit(sample, float("inf")) == byte_length(
            sample
        )

    @pytest.mark.parametrize("number", [float("nan"), float("inf"), float("-inf")])
    def test_encodes_non_finite_numbers_as_null(self, number: float) -> None:
        assert json_byte_length(number) == 4
        assert json_byte_length_if_within_limit(number, float("inf")) == 4

    def test_returns_none_once_the_budget_is_exceeded(self) -> None:
        value = {"a": "x" * 100}
        size = byte_length(value)

        assert json_byte_length_if_within_limit(value, size) == size
        assert json_byte_length_if_within_limit(value, size - 1) is None

    def test_rejects_a_value_that_is_not_json(self) -> None:
        with pytest.raises(TypeError):
            json_byte_length_if_within_limit({"a": object()}, 100)


class TestActivityRecordsConfig:
    def test_applies_the_documented_defaults(self) -> None:
        config = ActivityRecordsConfig()

        assert config.max_data_size_bytes == DEFAULT_MAX_DATA_SIZE_BYTES == 1_048_576
        assert config.max_batch_size_bytes == DEFAULT_MAX_BATCH_SIZE_BYTES == 8_388_608

    def test_reads_and_coerces_the_env_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ACTIVITY_RECORDS_MAX_DATA_SIZE_BYTES", "2048")
        monkeypatch.setenv("ACTIVITY_RECORDS_MAX_BATCH_SIZE_BYTES", "4096")

        config = ActivityRecordsConfig()

        assert (config.max_data_size_bytes, config.max_batch_size_bytes) == (2048, 4096)

    def test_rejects_a_data_size_below_the_minimum(self) -> None:
        with pytest.raises(ValidationError):
            ActivityRecordsConfig(max_data_size_bytes=MIN_MAX_DATA_SIZE_BYTES - 1)

        ActivityRecordsConfig(
            max_data_size_bytes=MIN_MAX_DATA_SIZE_BYTES,
            max_batch_size_bytes=MIN_MAX_DATA_SIZE_BYTES + EVENT_ENVELOPE_RESERVE_BYTES,
        )

    def test_rejects_a_batch_size_short_of_the_envelope_reserve(self) -> None:
        with pytest.raises(ValidationError, match="envelope reserve"):
            ActivityRecordsConfig(
                max_data_size_bytes=MIN_MAX_DATA_SIZE_BYTES,
                max_batch_size_bytes=MIN_MAX_DATA_SIZE_BYTES
                + EVENT_ENVELOPE_RESERVE_BYTES
                - 1,
            )


class TestWithPostgresSafeStrings:
    def test_replaces_nul_in_strings_and_keys(self) -> None:
        value = {"k\x00": ["x\x00", {"n\x00": "a\x00b"}], "n": 1}

        assert with_postgres_safe_strings(value) == {
            "k\ufffd": ["x\ufffd", {"n\ufffd": "a\ufffdb"}],
            "n": 1,
        }

    def test_replaces_lone_surrogates_but_keeps_astral_characters(self) -> None:
        value = "lone\ud83d high, pair 😀, lone\ude00 low"

        assert (
            with_postgres_safe_strings(value)
            == "lone\ufffd high, pair 😀, lone\ufffd low"
        )
        safe = with_postgres_safe_strings({"a\ud800": "b\x00\udc00"})
        assert safe == {"a�": "b��"}
        json.dumps(safe, ensure_ascii=False).encode("utf-8")


def _trace_span(trace_id: int) -> Any:
    context = SpanContext(trace_id=trace_id, span_id=1, is_remote=False)
    return trace.use_span(NonRecordingSpan(context))


class TestWithCorrelationId:
    def test_stamps_the_active_trace_id_and_keeps_an_existing_one(self) -> None:
        kept = wire_event(correlationId="existing-trace")
        stamped = wire_event()

        with _trace_span(0xABC):
            result = with_correlation_id([kept, stamped])

        assert result[0]["data"]["correlationId"] == "existing-trace"
        assert result[1]["data"]["correlationId"] == format(0xABC, "032x")
        assert "correlationId" not in stamped["data"]

    def test_leaves_events_alone_without_an_active_trace(self) -> None:
        event = wire_event()

        assert with_correlation_id([event]) == [event]


def test_to_last_error_is_the_class_name_only() -> None:
    assert to_last_error(ValueError("secret payload")) == "ValueError"


class TestPrepareRows:
    def test_builds_rows_with_the_camel_case_wire_payload(self) -> None:
        event = model_event(target_type="invoice", target_id="1")

        prepared = prepare_rows("company-1", [event])

        (row,) = prepared.rows
        assert row.id == str(event.id)
        assert row.company_id == "company-1"
        assert row.source == "billing-service"
        assert row.payload == event.to_wire()
        assert row.payload["data"]["targetType"] == "invoice"
        assert prepared.truncated_events == []

    def test_stamps_the_trace_id_of_the_callers_context(self) -> None:
        with _trace_span(0x1234):
            prepared = prepare_rows("company-1", [model_event()])

        assert prepared.rows[0].payload["data"]["correlationId"] == format(
            0x1234, "032x"
        )

    def test_replaces_unsafe_characters_in_the_payload(self) -> None:
        event = model_event(target_name="a\x00b", critical_data={"k\x00": ["x\x00"]})

        (row,) = prepare_rows("company-1", [event]).rows

        assert row.company_id == "company-1"
        assert row.payload["data"]["targetName"] == "a\ufffdb"
        assert row.payload["data"]["criticalData"] == {"k\ufffd": ["x\ufffd"]}
        assert "\\u0000" not in json.dumps(row.payload)

    @pytest.mark.parametrize("company_id", ["co\x00mpany", "co\ud800mpany"])
    def test_rejects_a_company_id_that_sanitization_would_change(
        self, company_id: str
    ) -> None:
        event = model_event()
        event.data.company_id = company_id

        with pytest.raises(ValueError, match="characters Postgres rejects") as raised:
            prepare_rows(company_id, [event])

        assert company_id not in str(raised.value)

    def test_rejects_an_event_of_another_company(self) -> None:
        own, other = model_event(), model_event()
        other.data.company_id = "company-2"

        with pytest.raises(ValueError, match="another company") as raised:
            prepare_rows("company-1", [own, other])

        assert "company-2" not in str(raised.value)

    def test_truncates_an_oversized_event_and_reports_it(self) -> None:
        oversized = model_event(critical_data={"blob": "x" * 10_000})
        untouched = model_event()

        prepared = prepare_rows("company-1", [oversized, untouched], 2_000)

        big, small = prepared.rows
        assert byte_length(big.payload["data"]) <= 2_000
        assert big.payload["data"]["criticalData"]["truncated"] is True
        assert small.payload == untouched.to_wire()
        assert [e["id"] for e in prepared.truncated_events] == [str(oversized.id)]

    def test_does_not_modify_the_events(self) -> None:
        event = model_event(critical_data={"blob": "x" * 10_000})
        snapshot = event.model_dump()

        prepare_rows("company-1", [event], 2_000)

        assert event.model_dump() == snapshot


class TestFitEventsToLimit:
    def test_truncation_warnings_do_not_include_payload_values(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        sentinel = "do-not-log-this-payload"
        event = wire_event(criticalData={"secret": sentinel * 1_000})

        with caplog.at_level(logging.WARNING):
            result = fit_events_to_limit([event], 400)

        assert result.truncated_events
        assert "criticalData truncated" in caplog.text
        assert sentinel not in caplog.text

    def test_reports_still_oversized_events_as_truncated(self) -> None:
        event = wire_event(companyId="c" * 2_000)

        result = fit_events_to_limit([event], 1_000)

        assert result.events == [event]
        assert result.truncated_events == [event]


def _blob_event(size: int, event_id: str = "1") -> dict[str, Any]:
    event = wire_event(criticalData={"blob": "x" * size})
    event["id"] = event_id
    return event


class TestSplitIntoBatchesUnderLimit:
    def test_splits_rows_under_the_batch_size_limit_keeping_order(self) -> None:
        events = [_blob_event(900, str(i)) for i in range(4)]

        batches = split_into_batches_under_limit(events, lambda e: e, 3_000, 2_000)

        assert len(batches) > 1
        assert [e for batch in batches for e in batch] == events
        for batch in batches:
            assert byte_length(batch) <= 3_000

    def test_keeps_everything_in_one_batch_when_it_fits(self) -> None:
        events = [_blob_event(10, str(i)) for i in range(3)]

        batches = split_into_batches_under_limit(
            events,
            lambda e: e,
            DEFAULT_MAX_BATCH_SIZE_BYTES,
            DEFAULT_MAX_DATA_SIZE_BYTES,
        )

        assert batches == [events]

    def test_sends_an_event_over_the_data_cap_in_a_message_of_its_own(self) -> None:
        small = wire_event()
        oversized = wire_event(companyId="x" * 2_000)
        after = wire_event()

        batches = split_into_batches_under_limit(
            [small, oversized, after], lambda e: e, DEFAULT_MAX_BATCH_SIZE_BYTES, 1_000
        )

        assert batches == [[small], [oversized], [after]]

    def test_sends_an_event_over_the_batch_cap_alone_instead_of_dropping_it(
        self,
    ) -> None:
        small = wire_event()
        huge = _blob_event(5_000)

        batches = split_into_batches_under_limit(
            [small, huge, small], lambda e: e, 1_000, 10_000
        )

        assert batches == [[small], [huge], [small]]

    def test_returns_no_batches_for_no_items(self) -> None:
        assert split_into_batches_under_limit([], lambda e: e, 3_000, 2_000) == []
