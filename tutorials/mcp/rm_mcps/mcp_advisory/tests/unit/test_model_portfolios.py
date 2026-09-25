"""Env-agnostic unit tests for model_portfolios — catalogue list + code/name
matching in get_model_portfolio (DB monkeypatched)."""

import json

import model_portfolios as mp

CATALOG = {"house": "ABC", "as_of": "2026-06-20", "count": 2,
           "models": [{"code": "BI-3", "name": "Balanced Income"},
                      {"code": "GR-7", "name": "Growth"}]}
ROWS = [
    {"code": "BI-3", "data": {"code": "BI-3", "name": "Balanced Income", "risk_band": "3"}},
    {"code": "GR-7", "data": {"code": "GR-7", "name": "Growth", "risk_band": "7"}},
]


def test_list_model_portfolios(fake_mcp, monkeypatch):
    monkeypatch.setattr(mp, "query_one", lambda sql, params=(): {"data": CATALOG})
    mp.register(fake_mcp)
    out = json.loads(fake_mcp.tools["list_model_portfolios"]())
    assert out["count"] == 2 and {m["code"] for m in out["models"]} == {"BI-3", "GR-7"}


def test_get_model_by_code(fake_mcp, monkeypatch):
    monkeypatch.setattr(mp, "query_all", lambda sql, params=(): ROWS)
    mp.register(fake_mcp)
    assert json.loads(fake_mcp.tools["get_model_portfolio"](input="BI-3"))["name"] == "Balanced Income"
    # case-insensitive code
    assert json.loads(fake_mcp.tools["get_model_portfolio"](code="gr-7"))["code"] == "GR-7"


def test_get_model_by_name(fake_mcp, monkeypatch):
    monkeypatch.setattr(mp, "query_all", lambda sql, params=(): ROWS)
    mp.register(fake_mcp)
    assert json.loads(fake_mcp.tools["get_model_portfolio"](input="growth"))["code"] == "GR-7"


def test_get_model_unknown_is_graceful(fake_mcp, monkeypatch):
    monkeypatch.setattr(mp, "query_all", lambda sql, params=(): ROWS)
    mp.register(fake_mcp)
    out = json.loads(fake_mcp.tools["get_model_portfolio"](input="ZZ-9"))
    assert "error" in out and "BI-3" in out["available"]
