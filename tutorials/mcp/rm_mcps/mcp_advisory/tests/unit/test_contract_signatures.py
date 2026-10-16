"""Env-agnostic contract test: every Advisory tool must ACCEPT every argument the
MCP_SERVERS.md documents for it (so a documented call never fails with
'unexpected keyword argument'). No DB needed — we only inspect signatures.

This is the guard that would have caught list_clients not accepting `input`.
"""

import inspect

import house_views
import lombard
import model_portfolios
import portfolios
import transactions

# tool name -> argument names that MCP_SERVERS.md says callers may pass
CONTRACT = {
    # portfolios (per-client): name or client_id
    "get_holdings": {"input", "client_id"},
    "get_performance": {"input", "client_id"},
    "get_portfolio_transactions": {"input", "client_id"},
    "get_attribution": {"input", "client_id"},
    "get_risk_exposure": {"input", "client_id"},
    # transactions (per-client)
    "get_corporate_actions": {"input", "client_id"},
    "get_elections": {"input", "client_id"},
    "get_orders": {"input", "client_id"},
    "get_tax_lots": {"input", "client_id"},
    "get_transaction_monitoring": {"input", "client_id"},
    # house views (bank-wide) — call with no args; get_house_view optionally filters by asset_class
    "get_house_view": {"asset_class"},
    "get_cio_themes": set(),
    "get_tactical_calls": set(),
    # model portfolios
    "list_model_portfolios": set(),
    "get_model_portfolio": {"input", "code", "model"},
    "recommend_model": {"input", "client_id"},
    # lombard
    "get_coverage_scenario": {"client_id", "scenario_id", "client"},
}


def _all_tools(fake_mcp):
    for mod in (house_views, portfolios, transactions, model_portfolios, lombard):
        mod.register(fake_mcp)
    return fake_mcp.tools


def test_every_documented_arg_is_accepted(fake_mcp):
    tools = _all_tools(fake_mcp)
    missing = {}
    for name, args in CONTRACT.items():
        assert name in tools, f"tool {name} not registered"
        params = set(inspect.signature(tools[name]).parameters)
        gap = args - params
        if gap:
            missing[name] = sorted(gap)
    assert not missing, f"tools missing documented args: {missing}"


def test_all_contract_tools_exist(fake_mcp):
    tools = _all_tools(fake_mcp)
    assert set(CONTRACT) <= set(tools), f"unregistered: {set(CONTRACT) - set(tools)}"
