"""Integration contract test (real seeded DB): drive every documented input form
from MCP_SERVERS.md and assert the documented output. Skipped if no DB.
"""

import json

import pytest

pytestmark = pytest.mark.integration

from common.db import get_conn  # noqa: E402

try:
    _c = get_conn(); _c.close()
except Exception:  # pragma: no cover
    pytest.skip("no Postgres reachable", allow_module_level=True)

import house_views  # noqa: E402
import lombard  # noqa: E402
import model_portfolios  # noqa: E402
import portfolios  # noqa: E402
import transactions  # noqa: E402


@pytest.fixture
def tools(fake_mcp):
    for mod in (house_views, portfolios, transactions, model_portfolios, lombard):
        mod.register(fake_mcp)
    return fake_mcp.tools


def call(tools, name, **kwargs):
    return json.loads(tools[name](**kwargs))


# --- input equivalence: name == canonical id == legacy numeric id ------------------------------
def test_client_input_forms_resolve_identically(tools):
    by_name = call(tools, "get_holdings", input="Markus")
    by_id = call(tools, "get_holdings", input="CH-PB-0049217")
    by_legacy = call(tools, "get_holdings", input="804323515592")
    by_cidarg = call(tools, "get_holdings", client_id="CH-PB-0049217")
    for r in (by_name, by_id, by_legacy, by_cidarg):
        assert r["client_id"] == "CH-PB-0049217"
    assert by_name == by_id == by_legacy == by_cidarg


# --- portfolios / transactions: documented output keys -----------------------------------------
@pytest.mark.parametrize("tool,required", [
    ("get_holdings", {"client_id", "account_id", "reporting_currency", "as_of", "total_market_value", "positions", "held_away_assets"}),
    ("get_performance", {"client_id", "basis", "periods", "since_inception", "benchmark_name"}),
    ("get_portfolio_transactions", {"client_id", "items", "count"}),
    ("get_attribution", {"client_id", "contribution_by_position", "contribution_by_asset_class", "top_contributors", "top_detractors"}),
    ("get_risk_exposure", {"client_id", "asset_allocation", "flags"}),
    ("get_corporate_actions", {"client_id", "items", "count"}),
    ("get_elections", {"client_id", "items", "count"}),
    ("get_orders", {"client_id", "items", "count"}),
    ("get_tax_lots", {"client_id", "lots", "unrealised_gain_loss", "estimated_transaction_cost", "estimated_tax_impact"}),
    ("get_transaction_monitoring", {"client_id", "alerts", "status", "open_cases"}),
])
def test_advisory_output_keys(tools, tool, required):
    out = call(tools, tool, input="Markus")
    assert required <= set(out), f"{tool} missing {required - set(out)}"


def test_risk_exposure_currency_exposure_where_present(tools):
    # MCP_SERVERS.md: currency_exposure is present for some clients (PTY-0002002 has it).
    assert "currency_exposure" in call(tools, "get_risk_exposure", input="Hofer")


# --- house view: no-args (full) / asset-class filter + synonyms / unknown -----------------------
def test_house_view_no_args_is_full(tools):
    out = call(tools, "get_house_view")
    assert {"house", "as_of", "valid_until", "count", "views"} <= set(out)
    assert out["count"] == len(out["views"]) == 5


def test_house_view_family_consistent_shape(tools):
    # The three bank-wide House-View tools share the SAME metadata shape — all called with NO args.
    meta = {"house", "as_of", "valid_until", "count"}
    for tool, field in [("get_house_view", "views"), ("get_cio_themes", "themes"),
                        ("get_tactical_calls", "calls")]:
        out = call(tools, tool)
        assert meta <= set(out), f"{tool} missing {meta - set(out)}"
        assert out["count"] == len(out[field])


@pytest.mark.parametrize("arg,expected", [
    ("equities", "Equities"), ("fixed income", "Fixed income"), ("alternatives", "Alternatives"),
    ("fx", "FX"), ("cash", "Cash"),
    ("bonds", "Fixed income"), ("equity", "Equities"), ("alts", "Alternatives"),  # synonyms
])
def test_house_view_asset_class_filter_and_synonyms(tools, arg, expected):
    out = call(tools, "get_house_view", asset_class=arg)
    assert out["asset_class"] == expected and "stance" in out


def test_house_view_unknown_class_is_graceful(tools):
    out = call(tools, "get_house_view", asset_class="crypto")
    assert "error" in out and "available" in out


def test_cio_themes_and_tactical_calls(tools):
    th = call(tools, "get_cio_themes")
    assert {"house", "as_of", "valid_until", "count", "themes"} <= set(th)
    assert th["count"] == len(th["themes"])
    tc = call(tools, "get_tactical_calls")
    assert {"house", "as_of", "valid_until", "count", "calls"} <= set(tc)
    assert tc["count"] == len(tc["calls"])


# --- models: list / by-code / by-name / unknown / recommend ------------------------------------
def test_list_then_get_every_model_by_code(tools):
    cat = call(tools, "list_model_portfolios")
    assert cat["count"] >= 4
    for m in cat["models"]:
        full = call(tools, "get_model_portfolio", input=m["code"])
        assert full["code"] == m["code"]
        assert {"name", "risk_band", "allocation", "expected_max_drawdown"} <= set(full)


def test_get_model_by_name_and_unknown(tools):
    assert call(tools, "get_model_portfolio", input="balanced").get("code")  # name substring match
    err = call(tools, "get_model_portfolio", input="ZZ-9")
    assert "error" in err and "available" in err


def test_recommend_model_shape(tools):
    out = call(tools, "recommend_model", input="Markus")
    # reconciled doc: {client_id, model, note}
    assert {"client_id", "model", "note"} <= set(out) and out["client_id"] == "CH-PB-0049217"


# --- lombard: every scenario_id + fuzzy + unknowns ---------------------------------------------
@pytest.mark.parametrize("scenario", [
    "baseline", "cash_topup_100k", "partial_repay_200k", "trim_collateral_200k", "hold",
])
def test_lombard_each_scenario(tools, scenario):
    out = call(tools, "get_coverage_scenario", client_id="Markus", scenario_id=scenario)
    assert out["scenario_id"] == scenario
    assert {"baseline", "projected", "narrative", "compliance_notes", "options"} <= set(out)


def test_lombard_fuzzy_scenario_and_client_forms(tools):
    assert call(tools, "get_coverage_scenario", client_id="Markus", scenario_id="cash top up")["scenario_id"] == "cash_topup_100k"
    assert call(tools, "get_coverage_scenario", client="Markus", scenario_id="baseline")["scenario_id"] == "baseline"


def test_lombard_unknowns_are_graceful(tools):
    assert "error" in call(tools, "get_coverage_scenario", client_id="Hofer", scenario_id="baseline")
    assert "error" in call(tools, "get_coverage_scenario", client_id="Markus", scenario_id="zzz")


# --- unknown client → standard hint ------------------------------------------------------------
def test_unknown_client_hint(tools):
    out = call(tools, "get_holdings", input="Nobody McGhost")
    assert "Unknown client" in out["error"]
