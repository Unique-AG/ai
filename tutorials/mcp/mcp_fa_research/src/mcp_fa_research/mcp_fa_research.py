"""mcp_fa_research.py — the FA (fundamental analyst) research demo MCP server.

Synthetic data layer for the Exane BNPP CIB sell-side research demo ("fa-demo"):
the analyst cockpit feeds (coverage roster, per-name dossier, 07:00 morning brief
with the profit-warning cascade, action inbox, agenda, jobs) plus the mock
market-data connectors (consensus / price / our-estimates — à la the RM demo's
mock FactSet/CapIQ pulls). ALL DATA IS SYNTHETIC — DEMO USE ONLY.

Read-only by design: analyst state (thesis, interaction log, note history) is
persisted by the coverage-dossier skill in the Knowledge Base, not here. Live
quotes come from the separate yahoo-finance connector.

Built like the other demo servers (mcp_trade_reconciliation / rm_mcps): a
standalone FastMCP HTTP server; OAuth (Zitadel) is OPTIONAL — when the upstream
env vars are absent the server runs OPEN (no per-user login; fine for synthetic,
read-only demo data).

Run locally:   uv run python src/mcp_fa_research/mcp_fa_research.py
MCP endpoint:  http://127.0.0.1:8005/mcp
"""

import json
import os
import sys
from typing import Annotated

from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from pydantic import Field
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

import seed

load_dotenv()

PORT = int(os.getenv("PORT", "8005"))


def build_auth():
    """Zitadel OAuth proxy — only when UPSTREAM_CLIENT_ID / UPSTREAM_CLIENT_SECRET /
    ZITADEL_URL are ALL set; otherwise None (open server). Same pattern as the RM
    Agent and trade-reconciliation MCPs."""
    upstream_client_id = os.getenv("UPSTREAM_CLIENT_ID")
    upstream_client_secret = os.getenv("UPSTREAM_CLIENT_SECRET")
    zitadel_url = os.getenv("ZITADEL_URL")
    if not (upstream_client_id and upstream_client_secret and zitadel_url):
        return None

    from fastmcp.server.auth.oauth_proxy import OAuthProxy
    from fastmcp.server.auth.providers.introspection import IntrospectionTokenVerifier

    base_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv(
        "BASE_URL_ENV", f"http://localhost:{PORT}"
    )
    token_verifier = IntrospectionTokenVerifier(
        introspection_url=f"{zitadel_url}/oauth/v2/introspect",
        client_id=upstream_client_id,
        client_secret=upstream_client_secret,
        client_auth_method="client_secret_basic",
    )
    return OAuthProxy(
        upstream_authorization_endpoint=f"{zitadel_url}/oauth/v2/authorize",
        upstream_token_endpoint=f"{zitadel_url}/oauth/v2/token",
        upstream_client_id=upstream_client_id,
        upstream_client_secret=upstream_client_secret,
        upstream_revocation_endpoint=f"{zitadel_url}/oauth/v2/revoke",
        token_verifier=token_verifier,
        base_url=base_url,
        redirect_path=None,
        issuer_url=None,
        service_documentation_url=None,
        allowed_client_redirect_uris=None,
        valid_scopes=["email", "openid", "profile"],
        forward_pkce=True,
        token_endpoint_auth_method="client_secret_post",
        extra_authorize_params=None,
        extra_token_params=None,
    )


custom_middleware = [
    Middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

mcp = FastMCP("FA Research", auth=build_auth())

# Mutable demo state (the overnight run the analyst reviews in the morning). Built fresh
# from the immutable seed at startup; Reset_Demo_Data restores it. In-memory + per-process
# (single demo container) — a restart also yields a clean baseline.
STATE = seed.baseline()

_TICKER = Annotated[str, Field(description="Ticker, Bloomberg code or company name "
                                           "(e.g. MC.PA, MC FP, LVMH).")]


def _unknown(raw: str) -> str:
    return json.dumps({
        "error": f"unknown name: {raw!r}",
        "covered": [f'{c["name"]} ({c["ticker"]})' for c in seed.COVERAGE],
    })


def _ccy_fmt(v, ccy):
    sym = {"EUR": "\u20ac", "CHF": "CHF ", "USD": "$", "GBP": "\u00a3"}.get(ccy, "")
    return f"{sym}{v:,.0f}" if isinstance(v, (int, float)) else str(v)


def _cockpit_row(c: dict) -> dict:
    """Coverage row + display-ready fields so the cockpit canvas stays declarative:
    labels, direction flags, and an openDocument payload for the name's PRECOMPUTED
    review (nightly build)."""
    row = json.loads(json.dumps(c))
    ov = seed.OVERNIGHT.get(c["ticker"])
    tp = (ov or {}).get("new_target_price") or c["target_price"]
    up = (ov or {}).get("new_upside_pct") if (ov and ov.get("new_upside_pct") is not None) else c["upside_pct"]
    row["tp_label"] = _ccy_fmt(tp, c["ccy"])
    row["upside_label"] = f"{up:+.1f}%"
    row["premarket_label"] = f"{c['premarket_pct']:+.1f}%"
    row["premarket_dir"] = "dn" if c["premarket_pct"] < -0.05 else ("up" if c["premarket_pct"] > 0.05 else "flat")
    row["pills_text"] = "  ".join(pl["label"] for pl in c.get("pills", []))
    cid = seed.REVIEW_IDS.get(c["ticker"], "")
    row["review_content_id"] = cid
    row["open_review_payload"] = json.dumps({"contentId": cid}) if cid else ""
    if ov:
        row["overnight"] = {"severity": ov["severity"], "headline": ov["headline"],
                            "valuation_impact": ov["valuation_impact"],
                            "new_target_price": ov.get("new_target_price")}
    return row


@mcp.tool(name="get_coverage", title="Coverage roster",
          description="The analyst's covered names with rating, single target price + "
                      "upside % (house style), last price, workflow status pills, next "
                      "catalyst, and each name's OVERNIGHT move (headline + valuation "
                      "impact + revised target price where it changed). Returns "
                      "{as_of, count, rows:[…]}. SYNTHETIC demo data.")
def get_coverage() -> str:
    rows = [_cockpit_row(c) for c in seed.COVERAGE]
    return json.dumps({"as_of": seed.AS_OF, "count": len(rows), "rows": rows})


@mcp.tool(name="get_dossier", title="Coverage dossier (summary)",
          description="Per-name coverage dossier summary: thesis, estimates vs consensus "
                      "line, interaction log, note history — plus the roster row (rating, "
                      "target price, next catalyst). The deep, persistent record lives in "
                      "the KB via the coverage-dossier skill. SYNTHETIC demo data.")
def get_dossier(ticker: _TICKER) -> str:
    t = seed.resolve(ticker)
    if not t:
        return _unknown(ticker)
    row = next(c for c in seed.COVERAGE if c["ticker"] == t)
    d = seed.DOSSIERS[t]
    ov = seed.OVERNIGHT.get(t)
    return json.dumps({**row, **d,
                       "overnight": ov,
                       "interaction_log_text": " · ".join(d["interaction_log"]),
                       "note_history_text": " · ".join(d["note_history"])})


@mcp.tool(name="get_morning_brief", title="Morning brief (07:00)",
          description="The overnight run the analyst reviews pre-open: one item per covered "
                      "name that moved — what-changed / so-what (valuation impact) / "
                      "suggested skill + action, with an `acknowledged` flag and `severity` "
                      "(alert/positive/watch/info). The LVMH profit-warning item includes "
                      "the prepared reaction cascade (model → valuation → morning-meeting "
                      "note → buy-side email + priority call list). Drafts only — nothing "
                      "is sent. SYNTHETIC demo data.")
def get_morning_brief() -> str:
    items = []
    for it in STATE["brief"]:
        d = json.loads(json.dumps(it))
        d["severity_label"] = {"alert": "ALERT", "positive": "UPSIDE",
                               "watch": "WATCH", "info": "NOTE"}[d["severity"]]
        d["cascade_text"] = "\n".join(f"{s['step']}.  {s['label']}" for s in d.get("cascade", []))
        d["call_list_text"] = " \u00b7 ".join(
            f"{c['account']}{(' \u2014 ' + c['priority']) if c['priority'] else ''}"
            for c in d.get("call_list", []))
        d["ack_args"] = json.dumps({"ticker": d["ticker"]})
        d["ack_label"] = "\u2713 reviewed" if d.get("acknowledged") else "mark reviewed"
        d["action_payload"] = json.dumps({"prompt": f"{d['suggested_action']} for {d['name']} "
                                          f"({d['ticker']}) \u2014 use the {d['suggested_skill']} skill."})
        items.append(d)
    return json.dumps({"generated_at": STATE["generated_at"], "count": len(items), "items": items})


@mcp.tool(name="acknowledge_alert", title="Acknowledge an overnight item",
          description="Mark an overnight morning-brief item as reviewed/handled by the "
                      "analyst (by ticker/name, or 'SECTOR' for the macro item). Mutates "
                      "demo state; Reset_Demo_Data restores it. Returns the updated item.")
def acknowledge_alert(ticker: _TICKER) -> str:
    key = "SECTOR" if (ticker or "").strip().upper() == "SECTOR" else seed.resolve(ticker)
    if not key:
        return _unknown(ticker)
    for item in STATE["brief"]:
        if item["ticker"] == key:
            item["acknowledged"] = True
            return json.dumps({"acknowledged": True, "item": item})
    return json.dumps({"error": f"no overnight item for {key}",
                       "in_brief": [i["ticker"] for i in STATE["brief"]]})


@mcp.tool(name="get_action_inbox", title="Action inbox (drafts)",
          description="Emails the agent has drafted replies for (desk, buy-side, IR), each "
                      "with a `reviewed` flag. Drafts only — the analyst reviews and sends. "
                      "Returns {count, drafts:[…]}. SYNTHETIC demo data.")
def get_action_inbox() -> str:
    drafts = []
    for d0 in STATE["inbox"]:
        d = json.loads(json.dumps(d0))
        d["review_payload"] = json.dumps({"prompt": f"Open the draft reply to {d['from']} "
                                          f"({d['subject']}) for my review \u2014 do not send anything."})
        drafts.append(d)
    return json.dumps({"count": len(drafts), "drafts": drafts})


@mcp.tool(name="get_agenda", title="Agenda (roadshows & meetings)",
          description="This week's agenda: investor roadshows (analyst-led marketing) and "
                      "corporate roadshows (analyst-organised for issuer management). "
                      "Returns {count, events:[…]}. SYNTHETIC demo data.")
def get_agenda() -> str:
    events = []
    for e0 in seed.AGENDA:
        e = json.loads(json.dumps(e0))
        e["action_payload"] = json.dumps({"prompt": f"Prepare the {e['title']} ({e['role']}) \u2014 "
                                          f"{e['action']} \u2014 use the roadshow-ir-prep skill."})
        events.append(e)
    return json.dumps({"count": len(events), "events": events})


@mcp.tool(name="get_jobs", title="Jobs & notifications",
          description="Background/scheduled runs (first-take, 07:00 desk brief, tone-drift "
                      "monitor) with status, plus the latest side-panel notification. "
                      "SYNTHETIC demo data.")
def get_jobs() -> str:
    jobs = json.loads(json.dumps(STATE["jobs"]["jobs"]))
    notif = STATE["jobs"].get("notification") or ""
    return json.dumps({"count": len(jobs), "jobs": jobs,
                       "notification": notif,
                       "notifications": ([{"text": notif}] if notif else [])})


@mcp.tool(name="get_consensus", title="Sell-side consensus snapshot (mock)",
          description="Mock consensus connector (IBES/Refinitiv-style): analyst count, "
                      "EPS mean/high/low, revenue, margin, ratings split, mean target "
                      "price. Available for names with a seeded snapshot. SYNTHETIC.")
def get_consensus(ticker: _TICKER) -> str:
    t = seed.resolve(ticker)
    if not t:
        return _unknown(ticker)
    snap = seed.CONSENSUS.get(t)
    if not snap:
        return json.dumps({"ticker": t, "note": "no consensus snapshot seeded for this name",
                           "available": sorted(seed.CONSENSUS)})
    return json.dumps({"ticker": t, **snap})


@mcp.tool(name="get_estimates", title="Our estimates vs consensus (mock)",
          description="Mock estimates connector: our numbers vs consensus per metric with "
                      "deltas, and the house stance line. Available for names with seeded "
                      "estimates. SYNTHETIC demo data.")
def get_estimates(ticker: _TICKER) -> str:
    t = seed.resolve(ticker)
    if not t:
        return _unknown(ticker)
    est = seed.OUR_ESTIMATES.get(t)
    if not est:
        return json.dumps({"ticker": t, "note": "no estimates seeded for this name",
                           "available": sorted(seed.OUR_ESTIMATES)})
    return json.dumps({"ticker": t, **est})


@mcp.tool(name="get_price", title="Price indication (mock)",
          description="Mock price connector: last close + synthetic pre-market indication "
                      "per covered name. For LIVE quotes use the yahoo-finance connector; "
                      "this exists so models/notes work without it. SYNTHETIC.")
def get_price(ticker: _TICKER) -> str:
    t = seed.resolve(ticker)
    if not t:
        return _unknown(ticker)
    return json.dumps(seed.PRICES[t])


@mcp.tool(name="Reset_Demo_Data", title="Reset demo data",
          description="Restore the FA research demo to its overnight baseline: re-generate "
                      "the 07:00 morning brief (all items un-acknowledged), reset the action "
                      "inbox drafts (un-reviewed) and jobs. Coverage / consensus / prices are "
                      "static reference data. Use between demo runs for a clean morning. "
                      "SYNTHETIC demo data.",
          meta={"unique.app/icon": "rotate-ccw"})
def reset_demo_data() -> str:
    global STATE
    STATE = seed.baseline()
    return json.dumps({
        "reset": True,
        "brief_items": len(STATE["brief"]),
        "inbox_drafts": len(STATE["inbox"]),
        "jobs": len(STATE["jobs"]["jobs"]),
        "note": "Overnight run restored to baseline — all items un-acknowledged.",
    })


@mcp.custom_route("/", methods=["GET"])
async def get_status(request: Request):
    return JSONResponse({"server": "running", "name": "FA Research"})


def main():
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=PORT,
        log_level="debug",
        middleware=custom_middleware,
    )


if __name__ == "__main__":
    main()
