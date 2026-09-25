"""Env-agnostic unit tests for common/db.py — the shaping/factory/resolution
logic, with the actual DB calls monkeypatched out (no Postgres needed)."""

import json

import common.db as db


def test_unknown_shape():
    r = db.unknown("Nobody")
    assert r["client_id"] == "Nobody"
    assert "Unknown client" in r["error"]


def test_get_record_dict(monkeypatch):
    monkeypatch.setattr(db, "resolve_client", lambda v: "PTY-1")
    monkeypatch.setattr(db, "query_one", lambda sql, params=(): {"data": {"a": 1, "b": 2}})
    assert db.get_record("holdings", "x") == {"client_id": "PTY-1", "a": 1, "b": 2}


def test_get_record_no_row(monkeypatch):
    monkeypatch.setattr(db, "resolve_client", lambda v: "PTY-1")
    monkeypatch.setattr(db, "query_one", lambda sql, params=(): None)
    r = db.get_record("holdings", "x")
    assert r == {"client_id": "PTY-1", "error": db.NO_DATA}


def test_get_record_unknown_client(monkeypatch):
    monkeypatch.setattr(db, "resolve_client", lambda v: None)
    r = db.get_record("holdings", "ghost")
    assert "Unknown client" in r["error"]


def test_get_list_shape(monkeypatch):
    monkeypatch.setattr(db, "resolve_client", lambda v: "PTY-1")
    monkeypatch.setattr(db, "query_one", lambda sql, params=(): {"data": [1, 2, 3]})
    assert db.get_list("orders", "x", "orders") == {
        "client_id": "PTY-1", "orders": [1, 2, 3], "count": 3,
    }


def test_get_list_missing_is_empty(monkeypatch):
    monkeypatch.setattr(db, "resolve_client", lambda v: "PTY-1")
    monkeypatch.setattr(db, "query_one", lambda sql, params=(): None)
    r = db.get_list("orders", "x", "orders")
    assert r["count"] == 0 and r["orders"] == []


def test_reset_create_table_regex():
    sql = (
        'CREATE TABLE IF NOT EXISTS holdings (client_id TEXT);\n'
        'CREATE TABLE IF NOT EXISTS  "weird_name" (id INT);\n'
        'INSERT INTO holdings VALUES (1);'
    )
    names = db._CREATE_TABLE_RE.findall(sql)
    assert names == ["holdings", "weird_name"]


def test_make_client_tools_registers_and_calls(fake_mcp, monkeypatch):
    monkeypatch.setattr(db, "get_record", lambda t, v: {"client_id": "PTY-1", "table": t, "in": v})
    monkeypatch.setattr(db, "get_list", lambda t, v, f: {"client_id": "PTY-1", "field": f})
    specs = [
        {"name": "get_x", "table": "x", "style": "record", "description": "d"},
        {"name": "get_y", "table": "y", "style": "list", "field": "items", "description": "d"},
    ]
    db.make_client_tools(fake_mcp, specs)
    assert set(fake_mcp.tools) == {"get_x", "get_y"}
    # `input` and `client_id` both feed the same resolution value
    assert json.loads(fake_mcp.tools["get_x"](input="Brunner"))["in"] == "Brunner"
    assert json.loads(fake_mcp.tools["get_x"](client_id="PTY-1"))["in"] == "PTY-1"
    assert json.loads(fake_mcp.tools["get_y"](input="a"))["field"] == "items"
