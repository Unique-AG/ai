"""Calendar domain — meetings (get_meetings / get_next_meeting).

Port of the n8n "RM Demo — Calendar" workflow. Reads sql/calendar.sql. The module
is named `meetings` (not `calendar`) so it never shadows the stdlib `calendar`.
"""

import json
from typing import Annotated

from pydantic import Field

from common.db import query_all, resolve_client, unknown
from common.tool_prompts import tool_meta

_MEETINGS_DESC = (
    "[CAL 1a] Calendar meetings (synthetic, consistent with RM Client Data). Input: a client name "
    "or client_id (that client's meetings); an RM username (marc.dubois / daniel.frei); or 'week' / "
    "omit for all upcoming meetings."
)
_NEXT_DESC = "[CAL 1b] The next upcoming meeting for a client. Input: client name or client_id."


def _events(value: str):
    """Return (meetings[], client_id|None) for the given filter."""
    raw = str(value or "").strip()
    cid = resolve_client(raw) if raw and raw.lower() not in ("week", "all") else None
    if cid:
        rows = query_all(
            "SELECT data FROM calendar_events WHERE client_id = %s ORDER BY start_at", (cid,)
        )
        return [r["data"] for r in rows], cid
    if raw and raw.lower() not in ("week", "all"):
        rows = query_all(
            "SELECT data FROM calendar_events WHERE lower(rm) = %s ORDER BY start_at", (raw.lower(),)
        )
        if rows:
            return [r["data"] for r in rows], None
    rows = query_all("SELECT data FROM calendar_events ORDER BY start_at")
    return [r["data"] for r in rows], None


def register(mcp) -> None:
    @mcp.tool(
        name="get_meetings",
        title="Get Meetings",
        description=_MEETINGS_DESC,
        meta=tool_meta("get_meetings", {"unique.app/icon": "calendar-days"}),
    )
    def get_meetings(
        input: Annotated[str, Field(description="Client name/id, RM username, 'week', or omit.")] = "",
    ) -> str:
        meetings, cid = _events(input)
        out = {"count": len(meetings), "meetings": meetings}
        if cid:
            out["client_id"] = cid
        return json.dumps(out)

    @mcp.tool(
        name="get_next_meeting",
        title="Get Next Meeting",
        description=_NEXT_DESC,
        meta=tool_meta("get_next_meeting", {"unique.app/icon": "calendar-check"}),
    )
    def get_next_meeting(
        input: Annotated[str, Field(description="Client name or client_id.")] = "",
    ) -> str:
        # Unlike get_meetings, this tool is scoped to a single client: a named client
        # that doesn't resolve must error (not silently fall through to the globally
        # earliest meeting). 'week'/'all'/omit keep the "all upcoming" behaviour.
        raw = str(input or "").strip()
        specific = bool(raw) and raw.lower() not in ("week", "all")
        cid = resolve_client(raw) if specific else None
        if specific and cid is None:
            return json.dumps(unknown(raw))
        if cid:
            rows = query_all(
                "SELECT data FROM calendar_events WHERE client_id = %s ORDER BY start_at", (cid,)
            )
        else:
            rows = query_all("SELECT data FROM calendar_events ORDER BY start_at")
        meetings = sorted((r["data"] for r in rows),
                          key=lambda e: e.get("start") or e.get("start_at") or e.get("date") or "")
        out = {"next_meeting": meetings[0] if meetings else None}
        if cid:
            out["client_id"] = cid
        return json.dumps(out)
