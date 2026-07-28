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

import chart_pack
import env_state
import note_pack
import scenario_engine
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


class EnvPathMiddleware:
    """Environment rides on the URL PATH (à la the RM Agent MCPs): ``/<env>/mcp`` and
    ``/<env>/admin`` select that env's demo state; bare ``/mcp`` & ``/admin`` = the
    default env. The middleware records the env for this request (ContextVar + request
    scope) and rewrites the path so FastMCP still routes ``/mcp`` / ``/admin``."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            segments = [s for s in scope.get("path", "").split("/") if s]
            env = segments[0] if (segments and env_state.is_env_segment(segments[0])) else ""
            env_state.set_url_env(env)
            if env:
                new_path = "/" + "/".join(segments[1:])
                scope = dict(scope, path=new_path or "/",
                             raw_path=(new_path or "/").encode(), fa_env=env)
        await self.app(scope, receive, send)


custom_middleware = [
    Middleware(EnvPathMiddleware),
    Middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

mcp = FastMCP("FA Research", auth=build_auth())

# Mutable demo state is PER ENVIRONMENT (env_state.STATES), selected by the URL path
# segment and materialized lazily from seed.baseline(). Reset_Demo_Data / the console
# reset restore the active env; a restart clears every env. In-memory by design.
seed.register_state_resolver(env_state.state)
env_state.materialize_known()

_get_state = env_state.state
_reset_state = env_state.reset

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
    row["status_payload"] = json.dumps({"prompt": (
        f"What is behind the status \"{c['status']}\" for {c['name']} ({c['ticker']})? "
        f"Show the backing items — note drafts, control-queue entries, open reviews — "
        f"from get_dossier and get_control_queue, with dates and what is still pending.")})
    env = env_state.current_env()
    cid = (seed.REVIEW_IDS_BY_ENV.get(env) or {}).get(c["ticker"], "")
    row["review_content_id"] = cid
    row["open_review_payload"] = seed.review_open_payload(env, c["ticker"])
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
    rows = [_cockpit_row(c) for c in seed.current_coverage()]
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
    row = next(c for c in seed.current_coverage() if c["ticker"] == t)
    d = seed.current_dossiers()[t]
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
    for it in env_state.state()["brief"]:
        d = json.loads(json.dumps(it))
        d["severity_label"] = {"alert": "ALERT", "positive": "UPSIDE",
                               "watch": "WATCH", "info": "NOTE"}[d["severity"]]
        d["name_label"] = ("European Luxury · all covered names" if d["ticker"] == "SECTOR"
                           else f"{d['name']} · {d['ticker']}")
        d["cascade_text"] = "\n".join(f"{s['step']}.  {s['label']}" for s in d.get("cascade", []))
        d["call_list_text"] = " \u00b7 ".join(
            f"{c['account']}{(' \u2014 ' + c['priority']) if c['priority'] else ''}"
            for c in d.get("call_list", []))
        d["ack_args"] = json.dumps({"ticker": d["ticker"]})
        d["ack_label"] = "\u2713 reviewed" if d.get("acknowledged") else "mark reviewed"
        d["action_payload"] = json.dumps({"prompt": f"{d['suggested_action']} for {d['name']} "
                                          f"({d['ticker']}) \u2014 use the {d['suggested_skill']} skill."})
        items.append(d)
    return json.dumps({"generated_at": env_state.state()["generated_at"], "count": len(items), "items": items})


@mcp.tool(name="acknowledge_alert", title="Acknowledge an overnight item",
          description="Mark an overnight morning-brief item as reviewed/handled by the "
                      "analyst (by ticker/name, or 'SECTOR' for the macro item). Mutates "
                      "demo state; Reset_Demo_Data restores it. Returns the updated item.")
def acknowledge_alert(ticker: _TICKER) -> str:
    key = "SECTOR" if (ticker or "").strip().upper() == "SECTOR" else seed.resolve(ticker)
    if not key:
        return _unknown(ticker)
    for item in env_state.state()["brief"]:
        if item["ticker"] == key:
            item["acknowledged"] = True
            return json.dumps({"acknowledged": True, "item": item})
    return json.dumps({"error": f"no overnight item for {key}",
                       "in_brief": [i["ticker"] for i in env_state.state()["brief"]]})


@mcp.tool(name="get_action_inbox", title="Action inbox (drafts)",
          description="Emails the agent has drafted replies for (desk, buy-side, IR), each "
                      "with a `reviewed` flag. Drafts only — the analyst reviews and sends. "
                      "Returns {count, drafts:[…]}. SYNTHETIC demo data.")
def get_action_inbox() -> str:
    drafts = []
    for d0 in env_state.state()["inbox"]:
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
          description="Background jobs with their schedule: run_at (when the job runs, "
                      "Zurich time) and recurrence ('once' — the default, a single run — "
                      "or 'daily'), plus status and display-ready when_label. Due jobs "
                      "EXECUTE: the desk-brief job (executor sdk_regen) really rebuilds "
                      "and uploads the coverage dashboards via the Unique SDK — last_run "
                      "carries per-document progress and the generated files with their "
                      "content ids; other jobs simulate. Schedules are editable in the "
                      "demo console. Also returns notifications. SYNTHETIC demo data.")
def get_jobs() -> str:
    jobs = json.loads(json.dumps(env_state.state()["jobs"]["jobs"]))
    for jb in jobs:
        rec = jb.get("recurrence") or "once"
        jb["recurrence"] = rec
        lr = jb.get("last_run") or {}
        run_at = jb.get("run_at") or ""
        if jb.get("status") == "running":
            prog = (f"{lr.get('done', 0)}/{lr['total']} docs"
                    if lr.get("kind") == "sdk_regen" and lr.get("total") else "running…")
            jb["when_label"] = f"started {run_at} · {prog}" if run_at else prog
        else:
            verb = "ran" if jb.get("status") == "done" else "runs"
            docs = (f" · {len(lr['files'])} docs" if lr.get("files")
                    else f" · {lr['summary_short']}" if lr.get("summary_short") else "")
            jb["when_label"] = f"{verb} {run_at}{docs} · {rec}" if run_at else rec
    notif = env_state.state()["jobs"].get("notification") or ""
    return json.dumps({"count": len(jobs), "jobs": jobs,
                       "notifications": [{"text": notif}] if notif else []})


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
    c = next(x for x in seed.current_coverage() if x["ticker"] == t)
    return json.dumps({"ticker": t, "name": c["name"], "ccy": c["ccy"],
                       "last_close": c["price"], "premarket_pct": c["premarket_pct"],
                       "note": "SYNTHETIC indication — use the yahoo-finance connector "
                               "for live quotes."})


@mcp.tool(name="get_scenarios", title="Scenario analysis (what-if, mock)",
          description="The analyst's scenario analysis for a covered name — what-if cases "
                      "(e.g. a currency shock, China recovery timing, destocking duration) "
                      "with the assumption, EPS and target-price impact vs the base case, "
                      "OUR hypothesis and a probability. This is the buy-side / roadshow "
                      "material ('send me your scenario analysis with your hypotheses'). "
                      "Available for names with seeded scenarios. SYNTHETIC demo data.")
def get_scenarios(ticker: _TICKER) -> str:
    t = seed.resolve(ticker)
    if not t:
        return _unknown(ticker)
    scen = env_state.state().get("scenarios") or seed.SCENARIOS
    sc = scen.get(t)
    if not sc:
        return json.dumps({"ticker": t, "note": "no scenario analysis seeded for this name",
                           "available": sorted(scen)})
    return json.dumps({"ticker": t, **sc})


@mcp.tool(name="compute_scenario", title="Scenario engine (what-if, computed)",
          description="COMPUTE a what-if scenario for a covered name — the analyst's "
                      "hypotheses with machine arithmetic: give an FX move (e.g. "
                      "fx_eur_move_pct=5 for a 5% EUR/CHF appreciation vs the revenue "
                      "basket), a China recovery timing (none | q2_26 | q4_26 | fy27) "
                      "and/or a cognac destocking end (h1_26 base | h2_26 | fy27, LVMH "
                      "only), and the engine cascades it through per-name exposures "
                      "(currency mix, EPS beta, hedge roll-off, China gearing) to revenue "
                      "/ EBIT / EPS deltas per year, new EPS levels, a target-price "
                      "bridge and a rating read — with the full assumption_trail so every "
                      "number is explainable. Axes combine. Calibrated to reproduce the "
                      "seeded get_scenarios hypothesis cases. Use for buy-side questions "
                      "('what if the euro moves 5%?'), roadshow prep and scenario packs. "
                      "SYNTHETIC demo engine.")
def compute_scenario(
    ticker: _TICKER,
    fx_eur_move_pct: Annotated[float, Field(
        description="Reporting-currency appreciation vs the revenue basket, in % "
                    "(+5 = EUR/CHF 5% stronger; negative = weaker). Range ±15.",
        ge=-15, le=15)] = 0.0,
    china_recovery: Annotated[str, Field(
        description="China demand recovery timing: none | q2_26 | q4_26 | fy27")] = "none",
    destocking_end: Annotated[str, Field(
        description="Cognac destocking end (LVMH only): h1_26 (base) | h2_26 | fy27")] = "h1_26",
) -> str:
    return json.dumps(scenario_engine.compute(ticker, fx_eur_move_pct,
                                              china_recovery, destocking_end))


@mcp.tool(name="get_scenario_board", title="Scenario board (Lab presets, computed)",
          description="The Scenario Lab feed: ~9 PREDEFINED scenario presets (FX ±5%, "
                      "China recovery timings, cognac destocking cases, combined bull/"
                      "bear) each COMPUTED at call time by the scenario engine and "
                      "returned display-ready ({title, tag, eps26/27/28 labels, tp_arrow, "
                      "tp_delta_label, rating_note, dir, explain_payload}), plus the "
                      "anticipation grids as bindable rows (fx_rows, china_rows, "
                      "matrix_rows) and the assumption trail. Built for the script-free "
                      "Scenario Lab canvas; also useful to summarise the whole scenario "
                      "space in one call. SYNTHETIC demo data.")
def get_scenario_board(ticker: _TICKER) -> str:
    return json.dumps(scenario_engine.board(ticker))


@mcp.tool(name="get_financials", title="Multi-year financials & chart series",
          description="Multi-year key financials (FY2023-28e) + dashboard chart series "
                      "for a covered name: sales, organic growth, recurring EBIT margin, "
                      "EPS, DPS, FCF — as a display-ready {header, rows} table plus chart "
                      "series whose points carry value_label AND precomputed bar geometry "
                      "(pct height, shared positive/negative scale, actual-vs-estimate "
                      "kind) so script-free canvases can render Exane-style bar charts "
                      "from attributes alone. Seeded for ALL 6 covered names. LVMH also "
                      "carries Wines & Spirits and Selective Retailing series. SYNTHETIC "
                      "demo data.")
def get_financials(ticker: _TICKER) -> str:
    t = seed.resolve(ticker)
    if not t:
        return _unknown(ticker)
    fin = chart_pack.get_financials(t)
    if not fin:
        return json.dumps({"ticker": t, "note": "no financials seeded for this name"})
    return json.dumps(fin)


@mcp.tool(name="get_note_pack", title="Note pack (house-format note data)",
          description="The full numeric backbone for a house-format research NOTE "
                      "(initiation / revision / flash) on a covered name, DISPLAY-READY: "
                      "cover header (rating, price, target price, upside), snapshot tables "
                      "(financials by year, valuation metrics, performance), key financials "
                      "+ segment details, BNPPE-vs-consensus grid, changes-to-forecasts, "
                      "DCF model + WACC sensitivity, SOTP, peer group, company profile "
                      "(management, ownership, calendar), financial-highlights grid and "
                      "six-charts data. Tables come as {header, rows} — copy them VERBATIM "
                      "into the note spec for build_exane_note.py; never re-type numbers. "
                      "Full pack seeded for MC FP; other names return a partial cover-only "
                      "pack (enough for a flash). SYNTHETIC demo data.")
def get_note_pack(ticker: _TICKER) -> str:
    t = seed.resolve(ticker)
    if not t:
        return _unknown(ticker)
    row = next((c for c in seed.current_coverage() if c["ticker"] == t), None)
    return json.dumps({"ticker": t, **note_pack.get_pack(t, row)})


@mcp.tool(name="get_control_queue", title="Pre-publication control queue",
          description="The maker/checker queue: research products submitted by the "
                      "analyst (maker) awaiting pre-publication control. Each item: id, "
                      "title, ticker, kind, submitted_by/at, priority, checklist "
                      "([{check, state: ok|open|fail}]), status (pending/released/"
                      "blocked), verdict + verdict_notes once decided. Display-ready "
                      "fields for the Control Room canvas (checklist_text, status/dir, "
                      "release_args/block_args). The checker records the decision with "
                      "record_control_verdict; Reset_Demo_Data restores the queue. "
                      "SYNTHETIC demo data.")
def get_control_queue() -> str:
    items = []
    for it0 in env_state.state()["control_queue"]:
        it = json.loads(json.dumps(it0))
        open_n = sum(1 for c in it["checklist"] if c["state"] != "ok")
        it["checklist_text"] = "\n".join(
            f"{'✓' if c['state'] == 'ok' else '◯'}  {c['check']}" for c in it["checklist"])
        it["open_checks"] = open_n
        it["open_label"] = ("all checks green" if open_n == 0
                            else f"{open_n} check(s) still open")
        it["status_label"] = {"pending": "PENDING CONTROL", "released": "RELEASED",
                              "blocked": "DO NOT RELEASE"}[it["status"]]
        it["dir"] = {"pending": "flat", "released": "up", "blocked": "dn"}[it["status"]]
        it["release_args"] = json.dumps({"item_id": it["id"], "verdict": "RELEASE"})
        it["block_args"] = json.dumps({"item_id": it["id"], "verdict": "DO_NOT_RELEASE"})
        it["control_payload"] = json.dumps({"prompt": f"Run pre-publication control on "
                                            f"'{it['title']}' ({it['id']}) — use the "
                                            f"pre-publication-control skill: verify every "
                                            f"checklist point, then record the verdict "
                                            f"with record_control_verdict."})
        items.append(it)
    pending = sum(1 for i in items if i["status"] == "pending")
    return json.dumps({"count": len(items), "pending": pending, "items": items})


_CONTROL_CHECKLISTS = {
    "note": [
        "Every figure recomputed vs source",
        "Single target price + upside % (house style)",
        "Rating consistency with the published view",
        "MNPI screen — no non-public information",
        "Disclosures block present + synthetic marker",
    ],
    "pack": [
        "Engine numbers reproduce the published cases",
        "Probabilities sum to 100%",
        "Assumption trail included",
        "Client-suitability wording (professional investors)",
    ],
    "deck": [
        "Figures match the underlying note/model",
        "Single target price + upside % (house style)",
        "Disclosures / synthetic marker on closing slide",
    ],
    "email": [
        "Content matches released research only",
        "No selective disclosure (same facts as published)",
        "Recipient suitability (professional investors)",
    ],
}


@mcp.tool(name="submit_for_control", title="Submit a product for control (maker)",
          description="The ANALYST (maker) submits a research product to the "
                      "pre-publication control queue: title, ticker, kind (note | pack "
                      "| deck | email — selects the standard checklist), priority and "
                      "optional notes. Returns the created queue item; the checker "
                      "decides with record_control_verdict. Use after drafting a note/"
                      "pack/deck the user wants to publish or send. Reset_Demo_Data "
                      "restores the baseline queue. SYNTHETIC demo data.")
def submit_for_control(
    title: Annotated[str, Field(description="Product title, e.g. 'LVMH — results flash'")],
    ticker: _TICKER = "",
    kind: Annotated[str, Field(description="note | pack | deck | email")] = "note",
    priority: Annotated[str, Field(description="e.g. 'URGENT — publish ASAP' or 'Standard'")] = "Standard",
    notes: Annotated[str, Field(description="Optional maker notes for the checker")] = "",
) -> str:
    k = kind.strip().lower()
    if k not in _CONTROL_CHECKLISTS:
        return json.dumps({"error": f"kind must be one of {sorted(_CONTROL_CHECKLISTS)}"})
    st = env_state.state()
    tk = seed.resolve(ticker) or "" if ticker else ""
    n = 1 + max((int(i["id"].split("-")[1]) for i in st["control_queue"]
                 if i.get("id", "").startswith("C-")), default=0)
    item = {"id": f"C-{n:03d}", "title": title, "ticker": tk, "kind": k,
            "submitted_by": "Analyst (maker)",
            "submitted_at": st.get("today", seed.STORY_TODAY) + " (via agent)",
            "priority": priority, "status": "pending", "verdict": "",
            "verdict_notes": notes,
            "checklist": [{"check": c, "state": "open"} for c in _CONTROL_CHECKLISTS[k]]}
    st["control_queue"].append(item)
    return json.dumps({"submitted": True, "item": item,
                       "note": "In the control queue — the checker records the verdict."})


@mcp.tool(name="record_control_verdict", title="Record a control verdict",
          description="The CHECKER's decision on a control-queue item: verdict RELEASE "
                      "or DO_NOT_RELEASE (+ optional notes, e.g. which check failed). "
                      "Mutates the queue item's status; fully auditable in the queue; "
                      "Reset_Demo_Data restores the baseline. Only record a verdict when "
                      "the user (checker) explicitly decides — never on your own "
                      "initiative. SYNTHETIC demo data.")
def record_control_verdict(
    item_id: Annotated[str, Field(description="Queue item id, e.g. C-001")],
    verdict: Annotated[str, Field(description="RELEASE or DO_NOT_RELEASE")],
    notes: Annotated[str, Field(description="Optional checker notes")] = "",
) -> str:
    v = verdict.strip().upper().replace(" ", "_")
    if v not in ("RELEASE", "DO_NOT_RELEASE"):
        return json.dumps({"error": "verdict must be RELEASE or DO_NOT_RELEASE"})
    for it in env_state.state()["control_queue"]:
        if it["id"] == item_id:
            it["status"] = "released" if v == "RELEASE" else "blocked"
            it["verdict"] = v
            it["verdict_notes"] = notes
            return json.dumps({"recorded": True, "item": it,
                               "note": "Verdict recorded — auditable in the control queue."})
    return json.dumps({"error": f"unknown item {item_id}",
                       "items": [i["id"] for i in env_state.state()["control_queue"]]})


@mcp.tool(name="get_emails", title="Mailbox (synthetic)",
          description="The analyst's synthetic mailbox: desk, buy-side, corporate IR, "
                      "compliance and internal emails around the demo storyline (LVMH "
                      "warning day). Each email: id, ts, from_name, from_role, subject, "
                      "body, ticker, read flag. Editable from the /admin demo-data "
                      "console; Reset_Demo_Data restores the snapshot. Args: "
                      "unread_only. SYNTHETIC demo data.")
def get_emails(unread_only: Annotated[bool, Field(
        description="Return only unread emails")] = False) -> str:
    st = env_state.state()
    emails = [e for e in st["emails"] if (not unread_only or not e.get("read"))]
    emails = sorted(emails, key=lambda e: e["ts"], reverse=True)
    return json.dumps({"count": len(emails), "unread": sum(1 for e in st["emails"]
                                                           if not e.get("read")),
                       "story_today": st.get("today"), "emails": emails})


@mcp.tool(name="get_calendar", title="Calendar (synthetic)",
          description="The analyst's synthetic calendar: results dates, roadshows, "
                      "buy-side calls, morning meetings and pre-publication control "
                      "slots around the demo storyline. Each event: id, date, time, "
                      "kind (results/roadshow/call/meeting/control), title, ticker, "
                      "notes. Editable from the /admin demo-data console; "
                      "Reset_Demo_Data restores the snapshot. SYNTHETIC demo data.")
def get_calendar() -> str:
    st = env_state.state()
    events = sorted(st["calendar"], key=lambda ev: (ev["date"], ev["time"]))
    return json.dumps({"count": len(events), "story_today": st.get("today"),
                       "events": events})


def _yahoo_quote(symbol: str) -> dict | None:
    """Fetch one live quote from Yahoo Finance (v8 chart endpoint, no auth). Returns
    {price, prev_close} or None on any failure — callers fall back to the synthetic seed."""
    import urllib.request

    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
           "?range=1d&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (demo)"})
    try:
        with urllib.request.urlopen(req, timeout=4) as r:
            meta = json.loads(r.read())["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        if price is None or not prev:
            return None
        return {"price": float(price), "prev_close": float(prev)}
    except Exception:
        return None


@mcp.tool(name="get_live_quotes", title="Live quotes (Yahoo Finance, formatted)",
          description="LIVE market quotes for the coverage universe, fetched from Yahoo "
                      "Finance server-side and returned DISPLAY-READY (price and change% "
                      "formatted to 2 decimals) — the ONE quote source for every canvas "
                      "(cockpit ribbon + review quote strips). Optional ticker arg filters "
                      "to one name. Returns {count, as_of, meta:[{label}], rows:[{ticker, "
                      "name, symbol, price_label, chg_label, chg_dir, as_of, source, "
                      "live}]}. as_of = fetch time (Europe/Zurich HH:MM). Falls back to "
                      "the synthetic seed indication (live: false, source labelled "
                      "accordingly) for any symbol Yahoo doesn't answer, so displays "
                      "never die.")
def get_live_quotes(
    ticker: Annotated[str, Field(default="", description="Optional — restrict to one "
                                 "covered name (Bloomberg code, e.g. 'RMS FP').")] = "",
) -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    as_of = datetime.now(ZoneInfo("Europe/Zurich")).strftime("%H:%M")
    names = seed.current_coverage()
    if ticker:
        names = [c for c in names if c["ticker"].lower() == ticker.strip().lower()] or names
    rows = []
    for c in names:
        q = _yahoo_quote(c["yahoo"])
        if q:
            chg = (q["price"] / q["prev_close"] - 1.0) * 100.0
            rows.append({"ticker": c["ticker"], "name": c["name"], "symbol": c["yahoo"],
                         "price_label": f"{q['price']:,.2f}", "chg_label": f"{chg:+.2f}",
                         "chg_dir": "dn" if chg < -0.005 else ("up" if chg > 0.005 else "flat"),
                         "as_of": as_of, "source": f"Yahoo Finance · {as_of}",
                         "live": True})
        else:
            rows.append({"ticker": c["ticker"], "name": c["name"], "symbol": c["yahoo"],
                         "price_label": f"{c['price']:,.2f}",
                         "chg_label": f"{c['premarket_pct']:+.2f}",
                         "chg_dir": "dn" if c["premarket_pct"] < 0 else "up",
                         "as_of": as_of, "source": f"synthetic indication · {as_of}",
                         "live": False})
    live_n = sum(1 for r in rows if r["live"])
    label = (f"LIVE · YAHOO FINANCE · as of {as_of} Zurich" if live_n
             else f"SYNTHETIC INDICATION · as of {as_of} Zurich")
    return json.dumps({"count": len(rows), "as_of": as_of,
                       "meta": [{"label": label}], "rows": rows})


@mcp.tool(name="add_analyst_note", title="Add a desk note (any equities)",
          description="Store an analyst DESK NOTE impacting any combination of covered "
                      "equities (or SECTOR). Call with the AI summary (1-2 sentences), "
                      "the original note text, and the impacted tickers (comma-separated "
                      "Bloomberg codes, e.g. 'MC FP, UHR SW' — or 'SECTOR'). The note "
                      "appears on the cockpit desk-notes list immediately. Mutates demo "
                      "state; Reset_Demo_Data clears it. SYNTHETIC demo.")
def add_analyst_note(
    summary: Annotated[str, Field(description="1-2 sentence AI summary of the note.")],
    note: Annotated[str, Field(description="The analyst's original note text.")],
    tickers: Annotated[str, Field(description="Impacted equities, comma-separated "
                                  "Bloomberg codes (or 'SECTOR').")],
) -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    resolved = []
    for raw in tickers.split(","):
        raw = raw.strip()
        if not raw:
            continue
        key = "SECTOR" if raw.upper() == "SECTOR" else seed.resolve(raw)
        if not key:
            return _unknown(raw)
        if key not in resolved:
            resolved.append(key)
    if not resolved:
        return json.dumps({"error": "no tickers given",
                           "covered": [c["ticker"] for c in seed.COVERAGE] + ["SECTOR"]})
    notes = env_state.state().setdefault("analyst_notes", [])
    item = {"id": f"N-{len(notes) + 1:03d}",
            "ts": datetime.now(ZoneInfo("Europe/Zurich")).strftime("%Y-%m-%d %H:%M"),
            "summary": summary.strip(), "note": note.strip(), "tickers": resolved}
    notes.insert(0, item)
    return json.dumps({"added": True, "item": item, "count": len(notes)})


@mcp.tool(name="get_analyst_notes", title="Desk notes",
          description="The analyst's stored desk notes (newest first): id, ts, AI "
                      "summary, original text, impacted tickers + display-ready "
                      "tickers_label. Optional ticker filter (notes touching that "
                      "name or SECTOR). SYNTHETIC demo state; Reset clears.")
def get_analyst_notes(
    ticker: Annotated[str, Field(default="", description="Optional — only notes "
                                 "impacting this name (or 'SECTOR').")] = "",
) -> str:
    notes = json.loads(json.dumps(env_state.state().get("analyst_notes", [])))
    if ticker:
        key = "SECTOR" if ticker.strip().upper() == "SECTOR" else seed.resolve(ticker)
        notes = [n for n in notes if key in n.get("tickers", [])]
    for n in notes:
        n["tickers_label"] = " · ".join(n["tickers"])
    return json.dumps({"count": len(notes), "notes": notes})


@mcp.tool(name="update_thesis", title="Update the investment thesis",
          description="Rewrite a name's INVESTMENT THESIS (semicolon-separated bullet "
                      "points — each ';' renders as a bullet on the review). Used by the "
                      "review's 'Edit with AI' control. Mutates per-env demo state; the "
                      "next dashboard regeneration bakes it in; Reset restores. Returns "
                      "the updated dossier summary.")
def update_thesis(
    ticker: _TICKER,
    thesis: Annotated[str, Field(description="The revised thesis — short bullet points "
                                 "separated by '; '.")],
) -> str:
    key = seed.resolve(ticker)
    if not key:
        return _unknown(ticker)
    d = env_state.state()["dossiers"][key]
    d["thesis"] = thesis.strip()
    return json.dumps({"updated": True, "ticker": key, "thesis": d["thesis"],
                       "note": "Baked into the review at the next regeneration "
                               "(nightly, desk-brief job, or ↻ on the dashboard)."})


@mcp.tool(name="add_note_history", title="Add a note-history entry",
          description="Append a timestamped entry to a name's NOTE HISTORY (the review's "
                      "'Note history' card), e.g. after publishing/submitting a product. "
                      "ts defaults to now (Europe/Zurich). Mutates per-env state; Reset "
                      "restores.")
def add_note_history(
    ticker: _TICKER,
    label: Annotated[str, Field(description="Entry text, e.g. 'First take — published'.")],
    ts: Annotated[str, Field(default="", description="Optional 'YYYY-MM-DD HH:MM'; "
                             "default now (Zurich).")] = "",
) -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    key = seed.resolve(ticker)
    if not key:
        return _unknown(ticker)
    stamp = ts.strip() or datetime.now(ZoneInfo("Europe/Zurich")).strftime("%Y-%m-%d %H:%M")
    d = env_state.state()["dossiers"][key]
    d["note_history"].append(f"{stamp} · {label.strip()}")
    return json.dumps({"added": True, "ticker": key, "note_history": d["note_history"]})


@mcp.tool(name="update_scenario_case", title="Update a scenario hypothesis",
          description="Edit ONE scenario hypothesis row for a name (matched by scenario "
                      "title substring). Editable fields: scenario, assumption, "
                      "eps_impact, tp_impact, hypothesis, probability. IMPORTANT: when "
                      "changing shocks, recompute eps/tp via compute_scenario first — "
                      "never invent numbers. Used by the scenario card's 'Edit with AI'. "
                      "Mutates per-env state; Reset restores; probabilities should sum "
                      "to 100%.")
def update_scenario_case(
    ticker: _TICKER,
    scenario_match: Annotated[str, Field(description="Substring of the scenario title "
                                         "to edit (e.g. 'Currency shock').")],
    scenario: Annotated[str, Field(default="", description="New title (optional).")] = "",
    assumption: Annotated[str, Field(default="")] = "",
    eps_impact: Annotated[str, Field(default="")] = "",
    tp_impact: Annotated[str, Field(default="")] = "",
    hypothesis: Annotated[str, Field(default="")] = "",
    probability: Annotated[str, Field(default="")] = "",
) -> str:
    key = seed.resolve(ticker)
    if not key:
        return _unknown(ticker)
    sc = env_state.state().get("scenarios", {}).get(key)
    if not sc:
        return json.dumps({"error": f"no scenario set for {key}"})
    row = next((r for r in sc["rows"]
                if scenario_match.lower() in r["scenario"].lower()), None)
    if row is None:
        return json.dumps({"error": f"no scenario matching {scenario_match!r}",
                           "available": [r["scenario"] for r in sc["rows"]]})
    for f, v in (("scenario", scenario), ("assumption", assumption),
                 ("eps_impact", eps_impact), ("tp_impact", tp_impact),
                 ("hypothesis", hypothesis), ("probability", probability)):
        if v.strip():
            row[f] = v.strip()
    total = sum(float(r["probability"].strip("%")) for r in sc["rows"]
                if r.get("probability", "").strip().rstrip("%").replace(".", "").isdigit())
    return json.dumps({"updated": True, "ticker": key, "row": row,
                       "probability_sum": f"{total:.0f}%",
                       "note": "Baked into the review/Lab at the next regeneration."})


@mcp.tool(name="update_analyst_note", title="Edit or delete a desk note",
          description="Update a stored desk note by id (summary, note text, tickers) or "
                      "delete it (delete=true). Used by 'Edit with AI' on the desk-notes "
                      "list. Mutates per-env state; Reset clears all notes.")
def update_analyst_note(
    note_id: Annotated[str, Field(description="The note id, e.g. 'N-001'.")],
    summary: Annotated[str, Field(default="")] = "",
    note: Annotated[str, Field(default="")] = "",
    tickers: Annotated[str, Field(default="", description="Comma-separated Bloomberg "
                                  "codes or 'SECTOR' (replaces the set).")] = "",
    delete: Annotated[bool, Field(default=False)] = False,
) -> str:
    notes = env_state.state().setdefault("analyst_notes", [])
    item = next((n for n in notes if n["id"] == note_id), None)
    if item is None:
        return json.dumps({"error": f"no note {note_id!r}",
                           "ids": [n["id"] for n in notes]})
    if delete:
        notes.remove(item)
        return json.dumps({"deleted": True, "id": note_id, "count": len(notes)})
    if summary.strip():
        item["summary"] = summary.strip()
    if note.strip():
        item["note"] = note.strip()
    if tickers.strip():
        resolved = []
        for raw in tickers.split(","):
            raw = raw.strip()
            if not raw:
                continue
            k = "SECTOR" if raw.upper() == "SECTOR" else seed.resolve(raw)
            if not k:
                return _unknown(raw)
            if k not in resolved:
                resolved.append(k)
        item["tickers"] = resolved
    return json.dumps({"updated": True, "item": item})


@mcp.tool(name="Reset_Demo_Data", title="Reset demo data",
          description="Restore the FA research demo to its labeled baseline snapshot: "
                      "morning brief (un-acknowledged), action inbox, jobs, coverage "
                      "roster, mailbox and calendar — undoing any edits made in the "
                      "/admin demo-data console. Consensus / estimates / scenarios are "
                      "static reference data. Use between demo runs for a clean morning. "
                      "SYNTHETIC demo data.",
          meta={"unique.app/icon": "rotate-ccw"})
def reset_demo_data() -> str:
    st = _reset_state()
    return json.dumps({
        "reset": True,
        "environment": env_state.current_env(),
        "snapshot": st["snapshot_label"],
        "brief_items": len(st["brief"]),
        "inbox_drafts": len(st["inbox"]),
        "emails": len(st["emails"]),
        "calendar_events": len(st["calendar"]),
        "note": "Demo state restored to the baseline snapshot — all console edits undone.",
    })


@mcp.custom_route("/", methods=["GET"])
async def get_status(request: Request):
    return JSONResponse({"server": "running", "name": "FA Research",
                         "demo_data_console": "/admin"})


@mcp.custom_route("/favicon.ico", methods=["GET"])
async def favicon(request: Request):
    """The shared demo-MCP icon — the admin UI uses the server's favicon as the
    connector icon (same file as the RM Agent / trade-reconciliation MCPs)."""
    from pathlib import Path

    from fastapi.responses import FileResponse

    return FileResponse(Path(__file__).parent / "favicon.ico")


import admin_ui  # noqa: E402
import jobs_engine  # noqa: E402
import nightly  # noqa: E402

admin_ui.register(mcp, _get_state, _reset_state)


@mcp.custom_route("/admin/api/nightly", methods=["GET"])
async def nightly_status(request: Request):
    return JSONResponse(nightly.NIGHTLY_STATUS)


@mcp.custom_route("/admin/api/nightly/run", methods=["POST"])
async def nightly_run(request: Request):
    body = await request.json()
    env = body.get("env") or env_state.current_env()
    job = body.get("job", "regen")
    if env not in nightly.SDK_CREDS:
        return JSONResponse({"error": f"no SDK creds for env {env!r}"}, status_code=400)
    import anyio

    fn = nightly.run_regen if job == "regen" else nightly.run_verify
    result = await anyio.to_thread.run_sync(fn, env)
    return JSONResponse(result)


nightly.start()
jobs_engine.start()


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
