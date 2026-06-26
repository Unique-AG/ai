"""Client Memory domain — the three EDITABLE per-client lists shown live on the
investment-proposal dashboard: talking points, open questions, and pinned
documents. This is the only stateful part of the RM Agent MCPs.

Port of the n8n "RM Demo — Client Memory" Data Tables. Read tools return a
TOP-LEVEL ARRAY of rows (the dashboard binds source-path=""); write tools upsert
or delete one row by (client_id, position). Tables: sql/client_memory.sql.
"""

import json
from typing import Annotated

from pydantic import Field

from common.db import execute, query_all, resolve_client, unknown

MAXLEN = 200    # MEMORY_MAX_CHARS
MAXITEMS = 20   # MEMORY_MAX_POINTS


def _qcol(c: str) -> str:
    return '"contentId"' if c == "contentId" else c


def _rows(table: str, cid: str):
    return query_all(f"SELECT * FROM {table} WHERE client_id = %s ORDER BY position", (cid,))


def _get(table: str, value: str):
    cid = resolve_client(value)
    return _rows(table, cid) if cid else unknown(value)


def _upsert(table: str, extra: tuple, client_id: str, position: int, values: dict) -> dict:
    cid = resolve_client(client_id)
    if cid is None:
        return unknown(client_id)
    # Enforce the documented MEMORY_MAX_POINTS cap: positions are 1-based and bounded
    # to MAXITEMS, so a client's list can never grow past the n8n limit.
    if not 1 <= int(position) <= MAXITEMS:
        return {"client_id": cid, "error": f"position must be between 1 and {MAXITEMS} (MEMORY_MAX_POINTS)."}
    cols = ["client_id", "position", *extra]
    vals = [cid, int(position)] + [
        (str(values.get(k, "")) if k == "contentId" else str(values.get(k, ""))[:MAXLEN]) for k in extra
    ]
    collist = ",".join(_qcol(c) for c in cols)
    ph = ",".join(["%s"] * len(cols))
    setlist = ",".join(f"{_qcol(c)}=EXCLUDED.{_qcol(c)}" for c in extra)
    execute(
        f"INSERT INTO {table} ({collist}) VALUES ({ph}) "
        f"ON CONFLICT (client_id, position) DO UPDATE SET {setlist}",
        tuple(vals),
    )
    return {"client_id": cid, "position": int(position), "updated": True, **values}


def _delete(table: str, client_id: str, position: int) -> dict:
    cid = resolve_client(client_id)
    if cid is None:
        return unknown(client_id)
    execute(f"DELETE FROM {table} WHERE client_id = %s AND position = %s", (cid, int(position)))
    return {"client_id": cid, "position": int(position), "deleted": True}


_CID = Annotated[str, Field(description="Client name or client_id.")]
_POS = Annotated[int, Field(description="1-based row position within this client's list.")]


def register(mcp) -> None:
    # --- talking points ---------------------------------------------------------
    @mcp.tool(name="get_talking_points", title="Get Talking Points",
              description="Get the client's editable talking points (ordered list). Input: client name or client_id.",
              meta={"unique.app/icon": "message-square"})
    def get_talking_points(client_id: _CID = "", input: _CID = "") -> str:
        return json.dumps(_get("rm_talking_points", client_id or input))

    @mcp.tool(name="upsert_talking_point", title="Upsert Talking Point",
              description="Create or update one talking point at a position for a client.",
              meta={"unique.app/icon": "pencil"})
    def upsert_talking_point(client_id: _CID = "", position: _POS = 1,
                             text: Annotated[str, Field(description="Talking-point text.")] = "") -> str:
        return json.dumps(_upsert("rm_talking_points", ("text",), client_id, position, {"text": text}))

    @mcp.tool(name="delete_talking_point", title="Delete Talking Point",
              description="Delete one talking point by position for a client.",
              meta={"unique.app/icon": "trash"})
    def delete_talking_point(client_id: _CID = "", position: _POS = 1) -> str:
        return json.dumps(_delete("rm_talking_points", client_id, position))

    # --- open questions ---------------------------------------------------------
    @mcp.tool(name="get_open_questions", title="Get Open Questions",
              description="Get the client's editable open questions (ordered list). Input: client name or client_id.",
              meta={"unique.app/icon": "circle-question"})
    def get_open_questions(client_id: _CID = "", input: _CID = "") -> str:
        return json.dumps(_get("rm_open_questions", client_id or input))

    @mcp.tool(name="upsert_open_question", title="Upsert Open Question",
              description="Create or update one open question at a position for a client.",
              meta={"unique.app/icon": "pencil"})
    def upsert_open_question(client_id: _CID = "", position: _POS = 1,
                             text: Annotated[str, Field(description="Open-question text.")] = "") -> str:
        return json.dumps(_upsert("rm_open_questions", ("text",), client_id, position, {"text": text}))

    @mcp.tool(name="delete_open_question", title="Delete Open Question",
              description="Delete one open question by position for a client.",
              meta={"unique.app/icon": "trash"})
    def delete_open_question(client_id: _CID = "", position: _POS = 1) -> str:
        return json.dumps(_delete("rm_open_questions", client_id, position))

    # --- documents (pinned, with contentId) ------------------------------------
    @mcp.tool(name="list_documents", title="List Documents (Memory)",
              description="Get the client's pinned documents (ordered list with title + contentId). Input: client name or client_id.",
              meta={"unique.app/icon": "files"})
    def list_documents(client_id: _CID = "", input: _CID = "") -> str:
        return json.dumps(_get("rm_documents", client_id or input))

    @mcp.tool(name="upsert_document", title="Upsert Document (Memory)",
              description="Create or update one pinned document (title + contentId) at a position for a client.",
              meta={"unique.app/icon": "pencil"})
    def upsert_document(client_id: _CID = "", position: _POS = 1,
                        title: Annotated[str, Field(description="Document title.")] = "",
                        contentId: Annotated[str, Field(description="KB content id.")] = "") -> str:
        return json.dumps(_upsert("rm_documents", ("title", "contentId"), client_id, position,
                                  {"title": title, "contentId": contentId}))

    @mcp.tool(name="delete_document", title="Delete Document (Memory)",
              description="Delete one pinned document by position for a client.",
              meta={"unique.app/icon": "trash"})
    def delete_document(client_id: _CID = "", position: _POS = 1) -> str:
        return json.dumps(_delete("rm_documents", client_id, position))
