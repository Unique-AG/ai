"""Env-agnostic unit tests for crm — list_clients filtering (case-insensitive
status/segment, substring rm, q, paging) and list_available_documents shaping.
DB monkeypatched."""

import json

import crm

ROSTER = [
    {"client_id": "CH-PB-0049217", "name": "Markus Brunner", "status": "Client",
     "segment": "HNW", "rm": "marc.dubois · Zürich"},
    {"client_id": "PTY-0002005", "name": "Katharina Brunner", "status": "Prospect",
     "segment": "HNW", "rm": "stefan.keller · Zürich"},
    {"client_id": "CH-PB-0061884", "name": "Isabelle Lavanchy", "status": "Client",
     "segment": "UHNW", "rm": "marc.dubois · Geneva"},
]


def _list_clients(fake_mcp, monkeypatch):
    monkeypatch.setattr(crm, "query_all", lambda sql, params=(): [{"data": c} for c in ROSTER])
    crm.register(fake_mcp)
    return fake_mcp.tools["list_clients"]


def test_list_all(fake_mcp, monkeypatch):
    assert json.loads(_list_clients(fake_mcp, monkeypatch)())["total"] == 3


def test_filter_status_case_insensitive(fake_mcp, monkeypatch):
    lc = _list_clients(fake_mcp, monkeypatch)
    assert json.loads(lc(status="client"))["total"] == 2  # "Client" in data


def test_filter_segment_case_insensitive(fake_mcp, monkeypatch):
    lc = _list_clients(fake_mcp, monkeypatch)
    assert json.loads(lc(segment="uhnw"))["total"] == 1


def test_filter_rm_substring(fake_mcp, monkeypatch):
    lc = _list_clients(fake_mcp, monkeypatch)
    assert json.loads(lc(rm="marc.dubois"))["total"] == 2


def test_q_searches_name(fake_mcp, monkeypatch):
    lc = _list_clients(fake_mcp, monkeypatch)
    assert json.loads(lc(q="lavanchy"))["total"] == 1


def test_paging(fake_mcp, monkeypatch):
    lc = _list_clients(fake_mcp, monkeypatch)
    r = json.loads(lc(limit=1, skip=1))
    assert r["total"] == 3 and r["count"] == 1 and r["limit"] == 1 and r["skip"] == 1


def test_list_available_documents(fake_mcp, monkeypatch):
    monkeypatch.setattr(crm, "resolve_client", lambda v: "PTY-1")
    monkeypatch.setattr(crm, "query_one",
                        lambda sql, params=(): {"data": [{"title": "a", "contentId": "c", "kind": "pdf"}]})
    monkeypatch.setattr(crm, "query_all", lambda sql, params=(): [])
    crm.register(fake_mcp)
    r = json.loads(fake_mcp.tools["list_available_documents"](input="x"))
    assert r["client_id"] == "PTY-1" and r["count"] == 1 and r["documents"] == r["items"]


def test_list_available_documents_unknown(fake_mcp, monkeypatch):
    monkeypatch.setattr(crm, "resolve_client", lambda v: None)
    monkeypatch.setattr(crm, "query_all", lambda sql, params=(): [])
    crm.register(fake_mcp)
    r = json.loads(fake_mcp.tools["list_available_documents"](input="ghost"))
    assert "Unknown client" in r["error"]
