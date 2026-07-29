from __future__ import annotations

import pytest
from mcp_dashboards.binding import enrich_binding_row, flatten_dotted_paths


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
        "case_action": {"status": "Needs Remediation"},
    }

    flat = flatten_dotted_paths(row)

    assert flat["identity.name"] == "Dmitry Volkov"
    assert flat["case_action.status"] == "Needs Remediation"


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
