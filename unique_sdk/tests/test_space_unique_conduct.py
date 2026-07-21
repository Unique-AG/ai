"""Tests for SDK UNIQUE_CONDUCT → API SWAPPABLE_INTELLIGENCE mapping."""

from __future__ import annotations

from unittest.mock import patch

from unique_sdk import Space


def test_normalize_ui_type_params_maps_unique_conduct() -> None:
    assert Space._normalize_ui_type_params(
        {"uiType": "UNIQUE_CONDUCT", "name": "x"}
    ) == {
        "uiType": "SWAPPABLE_INTELLIGENCE",
        "name": "x",
    }


def test_normalize_ui_type_params_leaves_other_values() -> None:
    assert Space._normalize_ui_type_params({"uiType": "UNIQUE_AI"}) == {
        "uiType": "UNIQUE_AI"
    }
    assert Space._normalize_ui_type_params({"uiType": "SWAPPABLE_INTELLIGENCE"}) == {
        "uiType": "SWAPPABLE_INTELLIGENCE"
    }
    assert Space._normalize_ui_type_params({"name": "x"}) == {"name": "x"}


def test_create_space_sends_swappable_intelligence_for_unique_conduct() -> None:
    with patch.object(
        Space, "_static_request", return_value={"id": "space_1"}
    ) as mock_req:
        Space.create_space(
            "user_1",
            "company_1",
            name="Conduct",
            uiType="UNIQUE_CONDUCT",
            fallbackModule="SwappableIntelligence",
            modules=[{"name": "SwappableIntelligence"}],
        )

    assert mock_req.call_args.kwargs["params"]["uiType"] == "SWAPPABLE_INTELLIGENCE"


def test_update_space_sends_swappable_intelligence_for_unique_conduct() -> None:
    with patch.object(
        Space, "_static_request", return_value={"id": "space_1"}
    ) as mock_req:
        Space.update_space(
            "user_1",
            "company_1",
            "space_1",
            uiType="UNIQUE_CONDUCT",
        )

    assert mock_req.call_args.kwargs["params"]["uiType"] == "SWAPPABLE_INTELLIGENCE"
