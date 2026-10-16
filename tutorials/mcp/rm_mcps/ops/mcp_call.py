#!/usr/bin/env python3
"""Minimal MCP streamable-HTTP client: list tools or call one.

Usage:
  mcp_call.py <url> list
  mcp_call.py <url> call <tool_name> '<json_args>'
"""
import json
import sys
import urllib.request

URL = sys.argv[1]
MODE = sys.argv[2]

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def post(payload, session=None):
    h = dict(HEADERS)
    if session:
        h["mcp-session-id"] = session
    req = urllib.request.Request(URL, json.dumps(payload).encode(), h)
    with urllib.request.urlopen(req, timeout=120) as r:
        sid = r.headers.get("mcp-session-id")
        body = r.read().decode()
    # streamable HTTP may answer as SSE: take last data: line
    if body.lstrip().startswith("event:") or "\ndata:" in body or body.startswith("data:"):
        datas = [ln[5:].strip() for ln in body.splitlines() if ln.startswith("data:")]
        body = datas[-1] if datas else "{}"
    return (json.loads(body) if body.strip() else {}), sid


init = {
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "probe", "version": "0"},
    },
}
_, sid = post(init)
post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)

if MODE == "list":
    resp, _ = post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, sid)
    names = sorted(t["name"] for t in resp["result"]["tools"])
    print(f"{len(names)} tools")
    for n in names:
        print(" ", n)
elif MODE == "call":
    tool, args = sys.argv[3], json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
    resp, _ = post({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": tool, "arguments": args}}, sid)
    res = resp.get("result", resp)
    for c in res.get("content", []):
        if c.get("type") == "text":
            txt = c["text"]
            try:
                print(json.dumps(json.loads(txt), indent=2)[:3000])
            except Exception:
                print(txt[:3000])
