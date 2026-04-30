"""Tests for endpoint parsing (slot + optional URL extraction)."""

from __future__ import annotations

import pytest

from uqadm.endpoint import (
    EndpointParseError,
    extract_space_id_from_url,
    parse_endpoint,
    parse_source_endpoint,
)


def test_parse_endpoint_slot_only() -> None:
    assert parse_endpoint("qa") == ("qa", None)


def test_parse_endpoint_slot_with_empty_rest() -> None:
    assert parse_endpoint("2:") == ("2", None)
    assert parse_endpoint("  2 :  ") == ("2", None)


def test_parse_endpoint_slot_and_space_id() -> None:
    assert parse_endpoint("1:space_abc123") == ("1", "space_abc123")


def test_parse_endpoint_with_https_url() -> None:
    url = "https://app.example.com/admin/space/space_xyz789"
    assert parse_endpoint(f"prod:{url}") == ("prod", "space_xyz789")


def test_parse_endpoint_custom_space_url() -> None:
    url = "https://host/x/custom-space/my_space_id/edit"
    assert parse_endpoint(f"1:{url}") == ("1", "my_space_id")


def test_extract_space_id_rejects_create_segment() -> None:
    with pytest.raises(EndpointParseError):
        extract_space_id_from_url("https://h/app/space/create")


def test_parse_source_requires_space_id() -> None:
    with pytest.raises(EndpointParseError):
        parse_source_endpoint("onlyslot")


def test_parse_endpoint_empty_raises() -> None:
    with pytest.raises(EndpointParseError):
        parse_endpoint("")


def test_parse_endpoint_missing_slot_raises() -> None:
    with pytest.raises(EndpointParseError):
        parse_endpoint(":space_1")
