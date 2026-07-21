"""Tests that SDK sends UNIQUE_CONDUCT as-is (API layer maps to/from wire value)."""

from __future__ import annotations

from unittest.mock import patch

from unique_sdk import Space


def test_create_space_sends_unique_conduct() -> None:
    with patch.object(
        Space,
        "_static_request",
        return_value={"id": "space_1", "uiType": "UNIQUE_CONDUCT"},
    ) as mock_req:
        space = Space.create_space(
            "user_1",
            "company_1",
            name="Conduct",
            uiType="UNIQUE_CONDUCT",
            fallbackModule="SwappableIntelligence",
            modules=[{"name": "SwappableIntelligence"}],
        )

    assert mock_req.call_args.kwargs["params"]["uiType"] == "UNIQUE_CONDUCT"
    assert space["uiType"] == "UNIQUE_CONDUCT"


def test_update_space_sends_unique_conduct() -> None:
    with patch.object(
        Space,
        "_static_request",
        return_value={"id": "space_1", "uiType": "UNIQUE_CONDUCT"},
    ) as mock_req:
        Space.update_space(
            "user_1",
            "company_1",
            "space_1",
            uiType="UNIQUE_CONDUCT",
        )

    assert mock_req.call_args.kwargs["params"]["uiType"] == "UNIQUE_CONDUCT"
