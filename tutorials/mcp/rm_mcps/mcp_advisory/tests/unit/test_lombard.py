"""Env-agnostic unit tests for lombard — the pure party/scenario resolvers and
the coverage tool (DB monkeypatched)."""

import json

import lombard as lb


def test_resolve_party_aliases():
    for v in ["Markus", "brunner", "Markus Brunner", "CH-PB-0049217", "50318", "LMB 50318.001.0001"]:
        assert lb._resolve_party(v) == "50318"


def test_resolve_party_unknown():
    assert lb._resolve_party("Hofer") == ""
    assert lb._resolve_party("") == ""


def test_resolve_scenario_exact_and_fuzzy():
    assert lb._resolve_scenario("baseline") == "baseline"
    assert lb._resolve_scenario("cash top up") == "cash_topup_100k"
    assert lb._resolve_scenario("partial repay") == "partial_repay_200k"
    assert lb._resolve_scenario("trim collateral") == "trim_collateral_200k"
    assert lb._resolve_scenario("hold and monitor") == "hold"


def test_resolve_scenario_unknown():
    assert lb._resolve_scenario("teleport") == ""


def test_coverage_returns_record(fake_mcp, monkeypatch):
    rec = {"scenario_id": "baseline", "baseline": {"coverage_pct": 115.0}, "reporting_ccy": "CHF"}
    monkeypatch.setattr(lb, "query_one", lambda sql, params=(): {"data": dict(rec)})
    lb.register(fake_mcp)
    out = json.loads(fake_mcp.tools["get_coverage_scenario"](client_id="Markus", scenario_id="baseline"))
    assert out["scenario_id"] == "baseline"


def test_coverage_ccy_override_adds_fx_note(fake_mcp, monkeypatch):
    rec = {"scenario_id": "baseline", "reporting_ccy": "CHF"}
    monkeypatch.setattr(lb, "query_one", lambda sql, params=(): {"data": dict(rec)})
    lb.register(fake_mcp)
    out = json.loads(fake_mcp.tools["get_coverage_scenario"](
        client_id="Markus", scenario_id="baseline", reporting_ccy="usd"))
    assert out["reporting_ccy"] == "USD" and "fx_note" in out


def test_coverage_unknown_client_errors(fake_mcp, monkeypatch):
    # A non-empty client that doesn't resolve must error, not serve Markus's record.
    monkeypatch.setattr(lb, "query_one", lambda sql, params=(): {"data": {}})
    lb.register(fake_mcp)
    out = json.loads(fake_mcp.tools["get_coverage_scenario"](client_id="Hofer", scenario_id="baseline"))
    assert "error" in out and "Unknown client" in out["error"]


def test_coverage_unknown_scenario_is_graceful(fake_mcp, monkeypatch):
    monkeypatch.setattr(lb, "query_one", lambda sql, params=(): None)
    lb.register(fake_mcp)
    out = json.loads(fake_mcp.tools["get_coverage_scenario"](client_id="Markus", scenario_id="zzz"))
    assert "error" in out and "Unknown scenario_id" in out["error"]
