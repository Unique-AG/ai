"""Env-agnostic unit tests for meetings (calendar) — client/rm/week filtering
and next-meeting sorting. DB monkeypatched."""

import json

import meetings as mt


def test_events_by_client(monkeypatch):
    evts = [{"start": "2026-06-25", "title": "A", "client_id": "PTY-1"}]
    monkeypatch.setattr(mt, "resolve_client", lambda v: "PTY-1" if v else None)
    monkeypatch.setattr(mt, "query_all",
                        lambda sql, params=(): [{"data": e} for e in evts] if "client_id =" in sql else [])
    out, cid = mt._events("Brunner")
    assert cid == "PTY-1" and len(out) == 1


def test_events_week_returns_all(monkeypatch):
    all_evts = [{"start": "2026-06-25", "title": "A"}, {"start": "2026-06-26", "title": "B"}]
    monkeypatch.setattr(mt, "resolve_client", lambda v: None)
    monkeypatch.setattr(mt, "query_all", lambda sql, params=(): [{"data": e} for e in all_evts])
    out, cid = mt._events("week")
    assert cid is None and len(out) == 2


def test_events_by_rm(monkeypatch):
    rm_evts = [{"start": "2026-06-25", "rm": "marc.dubois", "title": "A"}]
    monkeypatch.setattr(mt, "resolve_client", lambda v: None)

    def query_all(sql, params=()):
        return [{"data": e} for e in rm_evts] if "lower(rm)" in sql else []

    monkeypatch.setattr(mt, "query_all", query_all)
    out, cid = mt._events("marc.dubois")
    assert cid is None and len(out) == 1


def test_next_meeting_sorts_by_start(fake_mcp, monkeypatch):
    all_evts = [{"start": "2026-06-26", "title": "B"}, {"start": "2026-06-25", "title": "A"}]
    monkeypatch.setattr(mt, "resolve_client", lambda v: None)
    monkeypatch.setattr(mt, "query_all", lambda sql, params=(): [{"data": e} for e in all_evts])
    mt.register(fake_mcp)
    r = json.loads(fake_mcp.tools["get_next_meeting"](input="week"))
    assert r["next_meeting"]["title"] == "A"


def test_next_meeting_unknown_client_errors(fake_mcp, monkeypatch):
    # A named client that doesn't resolve must error, not return the global earliest.
    monkeypatch.setattr(mt, "resolve_client", lambda v: None)
    monkeypatch.setattr(mt, "query_all", lambda sql, params=(): [{"data": {"start": "2026-06-25"}}])
    mt.register(fake_mcp)
    r = json.loads(fake_mcp.tools["get_next_meeting"](input="Ghost Client"))
    assert "error" in r and "Unknown client" in r["error"]


def test_get_meetings_shape(fake_mcp, monkeypatch):
    monkeypatch.setattr(mt, "resolve_client", lambda v: None)
    monkeypatch.setattr(mt, "query_all", lambda sql, params=(): [])
    mt.register(fake_mcp)
    r = json.loads(fake_mcp.tools["get_meetings"](input="week"))
    assert r == {"count": 0, "meetings": []}
