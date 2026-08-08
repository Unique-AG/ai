"""Integration tests against a real, seeded Postgres (the env setup).

Skipped automatically if no database is reachable. Run with:
    uv run pytest -m integration
(after `docker compose up -d` + seeding sql/*.sql).
"""

import json

import pytest

pytestmark = pytest.mark.integration

# Skip the whole module if the DB isn't reachable.
from common.db import get_conn  # noqa: E402

try:
    _c = get_conn()
    _c.close()
except Exception:  # pragma: no cover
    pytest.skip("no Postgres reachable", allow_module_level=True)

import house_views  # noqa: E402
import lombard  # noqa: E402
import model_portfolios  # noqa: E402
import portfolios  # noqa: E402
import transactions  # noqa: E402


def _call(fake_mcp, module, name, **kwargs):
    module.register(fake_mcp)
    return json.loads(fake_mcp.tools[name](**kwargs))


def test_get_holdings_markus(fake_mcp):
    r = _call(fake_mcp, portfolios, "get_holdings", input="Markus")
    assert r["client_id"] == "CH-PB-0049217"
    assert len(r["positions"]) > 0


def test_corporate_actions_list_shape(fake_mcp):
    r = _call(fake_mcp, transactions, "get_corporate_actions", input="Markus")
    assert "items" in r and r["count"] == len(r["items"])


def test_house_view_bonds_synonym(fake_mcp):
    r = _call(fake_mcp, house_views, "get_house_view", asset_class="bonds")
    assert r["asset_class"] == "Fixed income"


def test_list_models_has_catalogue(fake_mcp):
    r = _call(fake_mcp, model_portfolios, "list_model_portfolios")
    assert r["count"] >= 4 and any(m["code"] == "BI-3" for m in r["models"])


def test_lombard_baseline_coverage(fake_mcp):
    r = _call(fake_mcp, lombard, "get_coverage_scenario", client_id="Markus", scenario_id="baseline")
    assert r["baseline"]["coverage_pct"] == 115.0


def test_unknown_client_fails_gracefully(fake_mcp):
    r = _call(fake_mcp, portfolios, "get_holdings", input="Nobody McGhost")
    assert "Unknown client" in r["error"]


def test_prospect_with_no_attribution(fake_mcp):
    # Katharina is a prospect → attribution returns the n8n "no data" message, not a crash.
    r = _call(fake_mcp, portfolios, "get_attribution", input="Katharina")
    assert r["client_id"] == "PTY-0002005"
    assert "error" in r  # "No data for this client in this sub-source."
