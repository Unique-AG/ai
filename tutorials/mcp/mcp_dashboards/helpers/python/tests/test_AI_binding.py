from __future__ import annotations

from datetime import date

import pytest
from mcp_dashboards.binding import (
    due_date_bucket,
    enrich_binding_row,
    flatten_dotted_paths,
)


@pytest.mark.ai
def test_AI_flatten_dotted_paths__mirrors_nested_domain_fields__as_dotted_keys() -> (
    None
):
    """
    Purpose: Verify nested client rows gain flat dotted-path mirror keys.
    Why this matters: The Unique platform iframe host resolves data-unique-field via item["a.b"].
    Setup summary: Flatten a small nested dict and assert dotted keys are present alongside nesting.
    """
    row = {
        "id": 3,
        "identity": {"name": "Dmitry Volkov", "reference": "CH-priv-0231"},
        "case_action": {"status": "Screening hit"},
    }

    flat = flatten_dotted_paths(row)

    assert flat["identity.name"] == "Dmitry Volkov"
    assert flat["case_action.status"] == "Screening hit"


@pytest.mark.ai
def test_AI_enrich_binding_row__adds_platform_attr_helpers__without_dropping_nested_shape() -> (
    None
):
    """
    Purpose: Verify binding enrichment keeps nested JSON and adds platform-only helper fields.
    Why this matters: Live-local hosts traverse nested rows while the platform needs flat keys and precomputed attrs.
    Setup summary: Enrich one client-like dict and assert helper href/id/tooltip/bar fields exist.
    """
    row = {
        "id": 7,
        "identity": {"name": "Test Client"},
        "compliance": {"risk_level": "High"},
        "figures": {"mandate": [{"label": "Equity", "pct": 66.0}]},
    }

    enriched = enrich_binding_row(row)

    assert enriched["identity"]["name"] == "Test Client"
    assert enriched["identity.name"] == "Test Client"
    assert enriched["client_href"] == "#client-7"
    assert enriched["client_dom_id"] == "client-7"
    assert enriched["compliance.risk_level_tooltip"] == "High risk"
    assert enriched["figures.mandate.0.pct_bar_style"] == "width:66.0%"
    assert enriched["case_action.due_bucket"] == "none"


@pytest.mark.ai
def test_AI_due_date_bucket__classifies_iso_dates__relative_to_today() -> None:
    """
    Purpose: Verify due dates map to urgent/scheduled/none for portfolio filters.
    Why this matters: Platform live filtering is CSS-only and needs a precomputed data-due bucket.
    Setup summary: Classify empty, past, and future ISO dates against a fixed reference day.
    """
    today = date(2026, 7, 29)

    assert due_date_bucket(None, today=today) == "none"
    assert due_date_bucket("", today=today) == "none"
    assert due_date_bucket("2026-07-29", today=today) == "urgent"
    assert due_date_bucket("2026-07-28", today=today) == "urgent"
    assert due_date_bucket("2026-08-01", today=today) == "scheduled"
    assert due_date_bucket("not-a-date", today=today) == "none"
