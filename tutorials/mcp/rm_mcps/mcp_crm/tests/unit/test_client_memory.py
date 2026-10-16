"""Env-agnostic unit tests for client_memory — upsert/delete/get shapes,
contentId quoting, and MAXLEN truncation. DB writes monkeypatched."""

import json

import client_memory as cm


def test_qcol_quotes_content_id():
    assert cm._qcol("contentId") == '"contentId"'
    assert cm._qcol("text") == "text"


def test_upsert_shape_and_sql(monkeypatch):
    captured = {}
    monkeypatch.setattr(cm, "resolve_client", lambda v: "PTY-1")
    monkeypatch.setattr(cm, "execute", lambda sql, params=(): captured.update(sql=sql, params=params))
    r = cm._upsert("rm_talking_points", ("text",), "x", 3, {"text": "hello"})
    assert r == {"client_id": "PTY-1", "position": 3, "updated": True, "text": "hello"}
    assert "ON CONFLICT (client_id, position) DO UPDATE" in captured["sql"]
    assert captured["params"] == ("PTY-1", 3, "hello")


def test_upsert_truncates_to_maxlen(monkeypatch):
    captured = {}
    monkeypatch.setattr(cm, "resolve_client", lambda v: "PTY-1")
    monkeypatch.setattr(cm, "execute", lambda sql, params=(): captured.update(params=params))
    cm._upsert("rm_talking_points", ("text",), "x", 1, {"text": "a" * 500})
    assert len(captured["params"][2]) == cm.MAXLEN


def test_upsert_response_echoes_stored_truncated_text(monkeypatch):
    # The response must reflect what was stored (truncated), not the original input.
    monkeypatch.setattr(cm, "resolve_client", lambda v: "PTY-1")
    monkeypatch.setattr(cm, "execute", lambda sql, params=(): None)
    r = cm._upsert("rm_talking_points", ("text",), "x", 1, {"text": "a" * 500})
    assert r["text"] == "a" * cm.MAXLEN


def test_upsert_document_keeps_content_id_untruncated(monkeypatch):
    captured = {}
    monkeypatch.setattr(cm, "resolve_client", lambda v: "PTY-1")
    monkeypatch.setattr(cm, "execute", lambda sql, params=(): captured.update(params=params))
    cm._upsert("rm_documents", ("title", "contentId"), "x", 1,
               {"title": "t", "contentId": "cont_" + "z" * 400})
    # title truncated, contentId left intact
    assert len(captured["params"][3]) == len("cont_" + "z" * 400)


def test_upsert_unknown_client(monkeypatch):
    monkeypatch.setattr(cm, "resolve_client", lambda v: None)
    r = cm._upsert("rm_talking_points", ("text",), "ghost", 1, {"text": "x"})
    assert "Unknown client" in r["error"]


def test_upsert_rejects_position_over_max(monkeypatch):
    monkeypatch.setattr(cm, "resolve_client", lambda v: "PTY-1")
    monkeypatch.setattr(cm, "execute", lambda sql, params=(): None)
    r = cm._upsert("rm_talking_points", ("text",), "x", cm.MAXITEMS + 1, {"text": "x"})
    assert "error" in r and "MEMORY_MAX_POINTS" in r["error"]


def test_delete_shape(monkeypatch):
    monkeypatch.setattr(cm, "resolve_client", lambda v: "PTY-1")
    monkeypatch.setattr(cm, "execute", lambda sql, params=(): 1)  # one row removed
    assert cm._delete("rm_talking_points", "x", 2) == {"client_id": "PTY-1", "position": 2, "deleted": True}


def test_delete_noop_reports_false(monkeypatch):
    # A delete that matches no row must report deleted=False, not a false success.
    monkeypatch.setattr(cm, "resolve_client", lambda v: "PTY-1")
    monkeypatch.setattr(cm, "execute", lambda sql, params=(): 0)  # nothing matched
    assert cm._delete("rm_talking_points", "x", 99) == {"client_id": "PTY-1", "position": 99, "deleted": False}


def test_get_returns_top_level_array(monkeypatch):
    monkeypatch.setattr(cm, "resolve_client", lambda v: "PTY-1")
    monkeypatch.setattr(cm, "query_all",
                        lambda sql, params=(): [{"client_id": "PTY-1", "position": 1, "text": "a"}])
    r = cm._get("rm_talking_points", "x")
    assert isinstance(r, list) and r[0]["text"] == "a"


def test_get_unknown_client(monkeypatch):
    monkeypatch.setattr(cm, "resolve_client", lambda v: None)
    r = cm._get("rm_talking_points", "ghost")
    assert "Unknown client" in r["error"]


def test_tools_registered(fake_mcp):
    cm.register(fake_mcp)
    expected = {
        "get_talking_points", "upsert_talking_point", "delete_talking_point",
        "get_open_questions", "upsert_open_question", "delete_open_question",
        "list_documents", "upsert_document", "delete_document",
    }
    assert expected <= set(fake_mcp.tools)


def test_write_tools_accept_input_alias(fake_mcp, monkeypatch):
    # upsert/delete must resolve a client name passed via `input`, like the getters.
    seen = {}
    monkeypatch.setattr(cm, "resolve_client", lambda v: "PTY-1" if v else None)
    monkeypatch.setattr(cm, "execute", lambda sql, params=(): (seen.update(params=params), 1)[1])
    cm.register(fake_mcp)
    r = json.loads(fake_mcp.tools["upsert_talking_point"](input="Brunner", position=2, text="hi"))
    assert r == {"client_id": "PTY-1", "position": 2, "updated": True, "text": "hi"}
    d = json.loads(fake_mcp.tools["delete_talking_point"](input="Brunner", position=2))
    assert d == {"client_id": "PTY-1", "position": 2, "deleted": True}


def test_get_tool_accepts_input_alias(fake_mcp, monkeypatch):
    monkeypatch.setattr(cm, "resolve_client", lambda v: "PTY-1" if v else None)
    monkeypatch.setattr(cm, "query_all", lambda sql, params=(): [])
    cm.register(fake_mcp)
    # both client_id and input should resolve
    assert json.loads(fake_mcp.tools["get_talking_points"](input="Brunner")) == []
    assert json.loads(fake_mcp.tools["get_talking_points"](client_id="PTY-1")) == []


def test_list_documents_adds_open_doc_payload(fake_mcp, monkeypatch):
    # The dashboard's §6 "Open" button attr-binds open_doc_payload; list_documents must
    # supply it as a JSON {"contentId": "..."} string per row (else documents won't open).
    monkeypatch.setattr(cm, "resolve_client", lambda v: "PTY-1")
    monkeypatch.setattr(cm, "query_all", lambda sql, params=():
                        [{"client_id": "PTY-1", "position": 1, "title": "X", "contentId": "cont_abc"}])
    cm.register(fake_mcp)
    rows = json.loads(fake_mcp.tools["list_documents"](client_id="PTY-1"))
    assert rows[0]["open_doc_payload"] == json.dumps({"contentId": "cont_abc"})
