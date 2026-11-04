"""Env-agnostic unit tests for house_views — synonyms, shapes, unknown-asset
handling — with the DB monkeypatched."""

import json

import pytest

import house_views as hv

META = {"house": "ABC Wealth Management — CIO Office", "as_of": "2026-06-20", "valid_until": "2026-09-30"}
VIEWS = [
    {"asset_class": "Equities", "stance": "Neutral", "conviction": 0, "rationale": "r1"},
    {"asset_class": "Fixed income", "stance": "Overweight", "conviction": 1, "rationale": "r2"},
    {"asset_class": "Alternatives", "stance": "Selective", "conviction": 1, "rationale": "r3"},
]
THEMES = [{"theme": "Quality", "horizon": "6-12m", "conviction": "High", "rationale": "r"}]
CALLS = [{"dimension": "Credit", "call": "Overweight", "detail": "d", "magnitude": "+",
          "conviction": "High", "rationale": "r"}]


@pytest.fixture(autouse=True)
def _patch_db(monkeypatch):
    monkeypatch.setattr(hv, "query_one", lambda sql, params=(): META)

    def query_all(sql, params=()):
        if "FROM house_view " in sql:
            return VIEWS
        if "cio_themes" in sql:
            return THEMES
        if "tactical_calls" in sql:
            return CALLS
        return []

    monkeypatch.setattr(hv, "query_all", query_all)


def test_house_view_all():
    r = hv._house_view("all")
    assert {"house", "as_of", "valid_until", "count", "views"} <= set(r)  # consistent HV shape
    assert r["count"] == len(r["views"]) == 3


def test_house_view_synonyms():
    assert hv._house_view("bonds")["asset_class"] == "Fixed income"
    assert hv._house_view("equity")["asset_class"] == "Equities"
    assert hv._house_view("alts")["asset_class"] == "Alternatives"


def test_house_view_exact_class():
    assert hv._house_view("fixed income")["stance"] == "Overweight"


def test_house_view_unknown_class():
    r = hv._house_view("crypto")
    assert "error" in r and "Fixed income" in r["available"]


def test_cio_themes_and_tactical_calls():
    # All three House-View tools share the SAME metadata shape: house/as_of/valid_until/count.
    th = hv._cio_themes()
    assert {"house", "as_of", "valid_until", "count", "themes"} <= set(th)
    assert th["count"] == 1 and th["themes"][0]["theme"] == "Quality"
    tc = hv._tactical_calls()
    assert {"house", "as_of", "valid_until", "count", "calls"} <= set(tc)
    assert tc["count"] == 1 and tc["calls"][0]["call"] == "Overweight"


def test_tools_registered_and_serialise(fake_mcp):
    hv.register(fake_mcp)
    assert {"get_house_view", "get_cio_themes", "get_tactical_calls"} <= set(fake_mcp.tools)
    out = json.loads(fake_mcp.tools["get_house_view"](asset_class="bonds"))
    assert out["asset_class"] == "Fixed income"
