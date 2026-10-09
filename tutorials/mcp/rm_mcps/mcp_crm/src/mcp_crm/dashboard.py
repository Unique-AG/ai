"""dashboard.py — edit a client's investment-proposal dashboard SECTIONS (add/remove a whole card)
SERVER-SIDE, with the server's own KB credentials.

Why this exists: the chat agent can read a dashboard opened via openDocument but its task scope is
read-only on that one document — it cannot write the file back (the `unique-cli upload` path is
sandboxed). This tool does the toggle + KB write here, so the agent makes ONE call instead of a slow
download → script → upload → permission-denied dance. Toggle logic mirrors the `dashboard-sections`
skill: each dashboard embeds a section library (`<script id="rm-section-lib">`), so any card can be
added back deterministically.

Needs KB creds in the environment: UNIQUE_APP_KEY, UNIQUE_APP_ID, UNIQUE_API_BASE,
UNIQUE_AUTH_USER_ID, UNIQUE_AUTH_COMPANY_ID (the service identity must have write access to
/RM Client Data). All KB I/O is via unique_sdk; nothing touches Postgres.
"""

import json
import os
import re
from typing import Annotated

from pydantic import Field

import unique_sdk
from unique_sdk.utils.file_io import download_content
import unique_toolkit.chat  # noqa: F401 — prime the namespace pkg AT IMPORT TIME (the intermittent
from unique_toolkit import KnowledgeBaseService  # 'unique_toolkit.chat' KeyError only resolves when
# primed at module top, not lazily inside a tool/thread). Startup stays under Azure's warmup limit via
# WEBSITES_CONTAINER_START_TIME_LIMIT (set to 600 on the web app), so module-top imports are safe here.

from common.db import resolve_client  # canonical client_id for the KB folder path
from common.tool_prompts import tool_meta

unique_sdk.api_key = _API_KEY = os.getenv("UNIQUE_APP_KEY", "")
unique_sdk.app_id = os.getenv("UNIQUE_APP_ID", "")
unique_sdk.api_base = os.getenv("UNIQUE_API_BASE", "https://gateway.qa.unique.app/public/chat-gen2").rstrip("/")
_USER = os.getenv("UNIQUE_AUTH_USER_ID", "")
_COMPANY = os.getenv("UNIQUE_AUTH_COMPANY_ID", "")
KB_ROOT = "/RM Client Data"
_FILE = "investment-proposal.html"

# --- section toggle (ported from dashboard-sections/toggle_section.py; stdlib only) ----------------
_LIB_RE = re.compile(r'<script type="application/json" id="rm-section-lib">(.*?)</script>', re.S)


def _key(h2_inner: str) -> str:
    t = re.sub(r"<span[^>]*>.*?</span>", "", h2_inner, flags=re.S)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"^\s*\d+\.\s*", "", t).strip().lower()
    t = (t.replace("suggested model portfolio", "model_portfolio")
          .replace("open questions to confirm", "open_questions")
          .replace("facility documents", "facility_documents"))
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_") or "section"


def _find(html: str) -> list[dict]:
    out = []
    for m in re.finditer(r'<section class="card"[^>]*\bid="(mod-\d+)"', html):
        sid, start, depth, end = m.group(1), m.start(), 0, None
        for t in re.finditer(r"<(/?)section\b", html[start:]):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                end = start + html[start:].index(">", t.start()) + 1
                break
        if end is None:
            continue
        h2 = re.search(r"<h2[^>]*>(.*?)</h2>", html[start:end], re.S)
        out.append({"id": sid, "key": _key(h2.group(1)) if h2 else sid, "start": start, "end": end})
    return out


def _library(html: str) -> dict:
    m = _LIB_RE.search(html)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception:
        return {}


def _resolve(token: str, sections: list, lib: dict) -> str | None:
    keys = {s["id"]: s["key"] for s in sections}
    for sid, meta in lib.items():
        keys.setdefault(sid, meta.get("key", sid))
    t = (token or "").strip().lower()
    if t in keys:
        return t
    for sid, k in keys.items():
        if k == t:
            return sid
    hits = [sid for sid, k in keys.items() if t and t in k]
    return hits[0] if len(hits) == 1 else None


def _remove(html: str, sid: str) -> tuple[str, bool]:
    sec = next((s for s in _find(html) if s["id"] == sid), None)
    if not sec:
        return html, False
    nxt = sec["end"]
    while nxt < len(html) and html[nxt] in " \t\r\n":
        nxt += 1
    return html[:sec["start"]] + html[nxt:], True


def _add(html: str, sid: str, lib: dict) -> tuple[str, bool]:
    if sid not in lib or not lib[sid].get("html"):
        return html, False
    n = int(sid.split("-")[1])
    anchor = None
    for s in _find(html):
        if int(s["id"].split("-")[1]) > n:
            anchor = s["start"]
            break
    if anchor is None:
        foot = re.search(r'<div class="foot">', html)
        lm = _LIB_RE.search(html)
        anchor = foot.start() if foot else (lm.start() if lm else len(html))
    return html[:anchor] + lib[sid]["html"] + "\n" + html[anchor:], True


def _renumber(html: str) -> str:
    """Renumber the VISIBLE section headings to 1..K in document order, so a removed (or added) card
    never leaves a gap (e.g. 1,3,4 -> 1,2,3). The `mod-N` ids stay fixed (they key the embedded
    library and the section lookup); only each card's `<h2>` "N." prefix is rewritten. The escaped
    library blocks (in the rm-section-lib script, using `\\u003c`) aren't matched by _find, so they
    are left untouched."""
    for i, s in reversed(list(enumerate(_find(html), start=1))):
        block = html[s["start"]:s["end"]]
        new = re.sub(r'(<h2[^>]*>)\s*\d+\.\s*', f'\\g<1>{i}. ', block, count=1)
        if new != block:
            html = html[:s["start"]] + new + html[s["end"]:]
    return html


_DESC = (
    "[DASH 1] Add or remove a WHOLE section (card) of a client's investment-proposal dashboard, and "
    "write it straight back to the Knowledge Base — one call, no file download/upload on your side. "
    "action: 'list' (show present + addable sections), 'remove' (drop a card), 'add' (restore a card). "
    "section: a key (recommendation / house_view / model_portfolio / talking_points / open_questions / "
    "facility_documents) or a card id (mod-5); omit for 'list'. Pass content_id (the dashboard's cont_… "
    "from the prompt) so it edits the exact file. Removed cards stay in the embedded library, so 'add' "
    "restores them. To change a list's CONTENTS instead of toggling the card, use the client-memory tools."
)


def register(mcp) -> None:
    @mcp.tool(name="edit_dashboard_section", title="Edit Dashboard Section", description=_DESC,
              meta=tool_meta("edit_dashboard_section", {"unique.app/icon": "layout-panel-top"}))
    def edit_dashboard_section(
        client_id: Annotated[str, Field(description="Client id, e.g. CH-PROS-0119.")],
        action: Annotated[str, Field(description="list | remove | add")] = "list",
        section: Annotated[str, Field(description="Section key (open_questions, talking_points, "
                                       "facility_documents, house_view, model_portfolio, recommendation) "
                                       "or id (mod-5). Omit for list.")] = "",
        content_id: Annotated[str, Field(description="The dashboard's KB contentId (cont_…). Strongly "
                                         "recommended — it's in the Edit-with-AI prompt.")] = "",
    ) -> str:
        if not (_USER and _COMPANY and _API_KEY):
            return json.dumps({"error": "KB credentials not configured on the server (UNIQUE_* env)."})
        # Resolve a name / legacy id to the canonical client_id so the KB write lands in
        # the right /RM Client Data/<client_id>/outputs folder (downloads use content_id).
        raw = (client_id or "").strip()
        client_id = resolve_client(raw) or raw
        cid = (content_id or "").strip()
        folder = f"{KB_ROOT}/{client_id}/outputs"
        if not cid:
            return json.dumps({"error": "Provide content_id (the dashboard's cont_… id from the prompt)."})
        try:
            path = download_content(companyId=_COMPANY, userId=_USER, content_id=cid, filename=_FILE)
            html = open(path, encoding="utf-8").read()
        except Exception as e:  # noqa: BLE001
            return json.dumps({"error": f"Could not download {cid}: {e}"})

        sections, lib = _find(html), _library(html)
        present_ids = {s["id"] for s in sections}
        if (action or "list").strip().lower() == "list":
            return json.dumps({
                "client_id": client_id,
                "present": [{"id": s["id"], "key": s["key"]} for s in sections],
                "addable": [{"id": sid, "key": m.get("key", sid)} for sid, m in sorted(lib.items())
                            if sid not in present_ids],
            })

        sid = _resolve(section, sections, lib)
        if not sid:
            return json.dumps({"client_id": client_id, "error": f"No unique section matches '{section}'. "
                               "Call with action='list' to see the keys."})
        skey = next((s["key"] for s in sections if s["id"] == sid), (lib.get(sid) or {}).get("key", sid))
        act = action.strip().lower()
        if act in ("remove", "hide"):
            if sid not in present_ids:
                return json.dumps({"client_id": client_id, "section": sid, "changed": False, "note": "already removed"})
            html, ok = _remove(html, sid)
        elif act in ("add", "show"):
            if sid in present_ids:
                return json.dumps({"client_id": client_id, "section": sid, "changed": False, "note": "already present"})
            html, ok = _add(html, sid, lib)
        else:
            return json.dumps({"error": "action must be list, remove, or add."})
        if not ok:
            return json.dumps({"client_id": client_id, "section": sid, "changed": False,
                               "note": "section not available (no embedded library entry)."})
        html = _renumber(html)   # close any numbering gap left by the add/remove (1,3,4 -> 1,2,3)
        try:
            # Write via the KnowledgeBaseService ingestion flow (same path as the working uploader):
            # resolve the folder to a scope id, then upsert the bytes by name (versioned replace).
            scope_id = unique_sdk.Folder.resolve_scope_id_from_folder_path_with_create(
                user_id=_USER, company_id=_COMPANY, folder_path=folder, create_if_not_exists=True)
            KnowledgeBaseService(company_id=_COMPANY, user_id=_USER).upload_content_from_bytes(
                content=html.encode("utf-8"), content_name=_FILE, mime_type="text/html",
                scope_id=scope_id, metadata=None)
        except Exception as e:  # noqa: BLE001
            return json.dumps({"error": f"Edited locally but KB write failed: {e}"})
        return json.dumps({"client_id": client_id, "section": skey, "id": sid,
                           "action": act, "changed": True,
                           "note": "Dashboard updated — the RM can Refresh."})
