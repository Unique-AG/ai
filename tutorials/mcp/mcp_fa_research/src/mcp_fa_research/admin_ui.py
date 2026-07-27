"""admin_ui.py — the demo-data console served by the FA Research MCP itself.

GET /admin — a small single-page console (vanilla JS, no build step) where a sales
person can browse and EDIT the demo state (coverage roster, morning brief, mailbox,
calendar) and reset everything to the labeled baseline snapshot. Changes live in the
server's in-memory STATE — the same state every MCP tool serves — so the cockpit,
reviews and the agent see the edits immediately. A restart or Reset restores the
snapshot; nothing is ever persisted. ALL DATA IS SYNTHETIC — DEMO USE ONLY.

REST surface (all JSON):
  GET    /admin/api/state              full editable state + read-only reference
  POST   /admin/api/reset              restore the baseline snapshot
  PATCH  /admin/api/coverage/{ticker}  edit a roster row (whitelisted fields)
  PATCH  /admin/api/brief/{key}        edit a morning-brief item
  POST   /admin/api/email              add · PATCH/DELETE /admin/api/email/{id}
  POST   /admin/api/event              add · PATCH/DELETE /admin/api/event/{id}
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from fastapi.responses import HTMLResponse, JSONResponse
from starlette.requests import Request

import env_state
import jobs_engine
import seed


def _shift_date(s: str, delta_days: int, fmt_len: int = 10) -> str:
    """Shift the YYYY-MM-DD prefix of a date or 'YYYY-MM-DD HH:MM' string."""
    try:
        d = date.fromisoformat(s[:fmt_len])
    except ValueError:
        return s
    return (d + timedelta(days=delta_days)).isoformat() + s[fmt_len:]

_COVERAGE_FIELDS = {"rating", "target_price", "price", "premarket_pct", "status",
                    "next_catalyst"}
_BRIEF_FIELDS = {"headline", "detail", "valuation_impact", "severity", "acknowledged",
                 "new_target_price", "suggested_action"}
_EMAIL_FIELDS = {"ts", "from_name", "from_role", "subject", "body", "ticker", "read"}
_EVENT_FIELDS = {"date", "time", "kind", "title", "ticker", "notes"}
_JOB_FIELDS = {"run_at", "recurrence", "status"}
_JOB_RECURRENCE = {"once", "daily"}   # once = default: no standing token burn
_JOB_STATUS = {"scheduled", "running", "done"}
_SCENARIO_FIELDS = {"scenario", "assumption", "eps_impact", "tp_impact", "hypothesis",
                    "probability"}
_NUM = {"target_price", "price", "premarket_pct", "new_target_price"}


_CHINA_OPTS = {"none", "q2_26", "q4_26", "fy27"}
_DESTOCK_OPTS = {"h1_26", "h2_26", "fy27"}


def _apply_preset(preset: dict, body: dict) -> str | None:
    """Apply a Lab-preset edit; returns an error string on invalid args."""
    for k in ("title", "tag"):
        if k in body:
            preset[k] = str(body[k])
    args = dict(preset.get("args") or {})
    if "fx_eur_move_pct" in body:
        v = body["fx_eur_move_pct"]
        if v in (None, "", "0", 0):
            args.pop("fx_eur_move_pct", None)
        else:
            try:
                f = float(v)
            except (TypeError, ValueError):
                return f"bad fx_eur_move_pct {v!r}"
            if abs(f) > 15:
                return "fx_eur_move_pct outside ±15"
            args["fx_eur_move_pct"] = f
    if "china_recovery" in body:
        v = (body["china_recovery"] or "none").strip()
        if v not in _CHINA_OPTS:
            return f"china_recovery must be one of {sorted(_CHINA_OPTS)}"
        args.pop("china_recovery", None)
        if v != "none":
            args["china_recovery"] = v
    if "destocking_end" in body:
        v = (body["destocking_end"] or "h1_26").strip()
        if v not in _DESTOCK_OPTS:
            return f"destocking_end must be one of {sorted(_DESTOCK_OPTS)}"
        args.pop("destocking_end", None)
        if v != "h1_26":
            args["destocking_end"] = v
    preset["args"] = args
    return None


def _apply(row: dict, patch: dict, allowed: set[str]) -> dict:
    for k, v in patch.items():
        if k not in allowed:
            continue
        if k in _NUM and v not in (None, ""):
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
        row[k] = v
    return row


ENV_CLASS: dict[str, tuple[str, str]] = {
    "qa":    ("QA",         "#0E7C7B"),
    "uat":   ("UAT",        "#C4620A"),
    "bnpp":  ("PRODUCTION", "#B42318"),
    "sales": ("PRODUCTION", "#B42318"),
    "local": ("LOCAL",      "#3F4A55"),
}
_SANDBOX_CLASS = ("SANDBOX", "#5B4B8A")


def register(mcp, get_state, reset_state) -> None:
    @mcp.custom_route("/admin", methods=["GET"])
    async def admin_page(request: Request):
        env = env_state.current_env()
        label, color = ENV_CLASS.get(env, _SANDBOX_CLASS)
        badge = env.upper() if label == env.upper() else f"{env.upper()} · {label}"
        html = (ADMIN_HTML
                .replace("__ENV_COLOR__", color)
                .replace("__ENV_BADGE__", badge)
                .replace("__ENV_PATH__", f"/{env}/admin"))
        return HTMLResponse(html)

    @mcp.custom_route("/admin/api/state", methods=["GET"])
    async def admin_state(request: Request):
        st = get_state()
        return JSONResponse({
            "environment": env_state.current_env(),
            "environments": env_state.envs(),
            "snapshot_label": st.get("snapshot_label", seed.SNAPSHOT_LABEL),
            "today": st.get("today", seed.STORY_TODAY),
            "baseline_today": seed.STORY_TODAY,
            "generated_at": st.get("generated_at"),
            "coverage": st["coverage"],
            "brief": st["brief"],
            "emails": sorted(st["emails"], key=lambda e: e["ts"], reverse=True),
            "calendar": sorted(st["calendar"], key=lambda ev: (ev["date"], ev["time"])),
            "agenda": seed.AGENDA,
            "jobs": st["jobs"],
            "scenarios": st.get("scenarios", {}),
            "lab_presets": st.get("lab_presets", []),
            "reference": {
                "consensus": seed.CONSENSUS, "estimates": seed.OUR_ESTIMATES,
            },
        })

    @mcp.custom_route("/admin/api/job/{idx}", methods=["PATCH"])
    async def admin_job(request: Request):
        """Edit a job's schedule: run_at ("YYYY-MM-DD HH:MM"), recurrence (once|daily —
        once is the default so nothing recurs, and consumes tokens, unless opted in),
        and status. The job list itself is fixed by the storyline."""
        st = get_state()
        jobs = st["jobs"]["jobs"]
        try:
            idx = int(request.path_params["idx"])
            job = jobs[idx]
        except (ValueError, IndexError):
            return JSONResponse({"error": "unknown job index"}, status_code=404)
        body = await request.json()
        if "run_at" in body:
            v = str(body["run_at"]).strip()
            try:
                date.fromisoformat(v[:10])
                if len(v) > 10 and (len(v) != 16 or v[10] != " " or
                                    not (0 <= int(v[11:13]) < 24 and 0 <= int(v[14:16]) < 60)):
                    raise ValueError
            except ValueError:
                return JSONResponse({"error": f"bad run_at {v!r} — use YYYY-MM-DD HH:MM"},
                                    status_code=400)
            job["run_at"] = v
        if "recurrence" in body:
            v = str(body["recurrence"]).strip() or "once"
            if v not in _JOB_RECURRENCE:
                return JSONResponse({"error": f"recurrence must be one of {sorted(_JOB_RECURRENCE)}"},
                                    status_code=400)
            job["recurrence"] = v
        if "status" in body:
            v = str(body["status"]).strip()
            if v not in _JOB_STATUS:
                return JSONResponse({"error": f"status must be one of {sorted(_JOB_STATUS)}"},
                                    status_code=400)
            job["status"] = v
        return JSONResponse(job)

    @mcp.custom_route("/admin/api/job/{idx}/run", methods=["POST"])
    async def admin_job_run(request: Request):
        """Run a job immediately. sdk_regen jobs really regenerate + upload the
        dashboards via the Unique SDK; others simulate. Progress lands in last_run."""
        st = get_state()
        jobs = st["jobs"]["jobs"]
        try:
            job = jobs[int(request.path_params["idx"])]
        except (ValueError, IndexError):
            return JSONResponse({"error": "unknown job index"}, status_code=404)
        res = jobs_engine.launch(env_state.current_env(), job)
        return JSONResponse(res, status_code=200 if res.get("started") else 409)

    @mcp.custom_route("/admin/api/reset", methods=["POST"])
    async def admin_reset(request: Request):
        st = reset_state()
        return JSONResponse({"reset": True, "snapshot_label": st["snapshot_label"],
                             "today": st["today"]})

    @mcp.custom_route("/admin/api/rebase", methods=["POST"])
    async def admin_rebase(request: Request):
        """Shift every dated item so the storyline's 'today' becomes the given date
        (default: the caller's date). Deltas are preserved — the warning day is
        always day 0, the roadshow stays T+6/+7, yesterday's emails stay T-1.
        Idempotent day over day: the shift is relative to the CURRENT anchor."""
        st = get_state()
        body = await request.json() if (request.headers.get("content-length") or "0") != "0" else {}
        target_s = (body or {}).get("date") or date.today().isoformat()
        try:
            target = date.fromisoformat(target_s)
        except ValueError:
            return JSONResponse({"error": f"bad date {target_s!r} — use YYYY-MM-DD"},
                                status_code=400)
        anchor = date.fromisoformat(st.get("today", seed.STORY_TODAY))
        delta = (target - anchor).days
        if delta:
            for ev in st["calendar"]:
                ev["date"] = _shift_date(ev["date"], delta)
            for em in st["emails"]:
                em["ts"] = _shift_date(em["ts"], delta)
            for jb in st["jobs"]["jobs"]:
                if jb.get("run_at"):
                    jb["run_at"] = _shift_date(jb["run_at"], delta)
            st["today"] = target.isoformat()
        return JSONResponse({"rebased": True, "today": st["today"],
                             "shifted_days": delta,
                             "note": "calendar dates, email timestamps and job run_at shifted; "
                                     "deltas to the warning day preserved"})

    @mcp.custom_route("/admin/api/coverage/{ticker}", methods=["PATCH"])
    async def admin_coverage(request: Request):
        st = get_state()
        tk = request.path_params["ticker"]
        row = next((c for c in st["coverage"] if c["ticker"] == tk), None)
        if not row:
            return JSONResponse({"error": f"unknown ticker {tk}"}, status_code=404)
        _apply(row, await request.json(), _COVERAGE_FIELDS)
        if row.get("price"):
            row["upside_pct"] = round((row["target_price"] / row["price"] - 1) * 100, 1)
        return JSONResponse(row)

    @mcp.custom_route("/admin/api/brief/{key}", methods=["PATCH"])
    async def admin_brief(request: Request):
        st = get_state()
        key = request.path_params["key"]
        item = next((b for b in st["brief"] if b["ticker"] == key), None)
        if not item:
            return JSONResponse({"error": f"no brief item for {key}"}, status_code=404)
        patch = await request.json()
        if isinstance(patch.get("acknowledged"), str):
            patch["acknowledged"] = patch["acknowledged"].lower() in ("true", "1", "yes")
        _apply(item, patch, _BRIEF_FIELDS)
        return JSONResponse(item)

    @mcp.custom_route("/admin/api/email", methods=["POST"])
    async def admin_email_add(request: Request):
        st = get_state()
        body = await request.json()
        n = 1 + max((int(e["id"].split("-")[1]) for e in st["emails"]
                     if e.get("id", "").startswith("M-")), default=0)
        email = {"id": f"M-{n:03d}", "ts": st.get("today", seed.STORY_TODAY) + " 08:00",
                 "from_name": "", "from_role": "", "subject": "", "body": "",
                 "ticker": "", "read": False}
        _apply(email, body, _EMAIL_FIELDS)
        st["emails"].append(email)
        return JSONResponse(email)

    @mcp.custom_route("/admin/api/email/{eid}", methods=["PATCH", "DELETE"])
    async def admin_email(request: Request):
        st = get_state()
        eid = request.path_params["eid"]
        email = next((e for e in st["emails"] if e["id"] == eid), None)
        if not email:
            return JSONResponse({"error": f"unknown email {eid}"}, status_code=404)
        if request.method == "DELETE":
            st["emails"].remove(email)
            return JSONResponse({"deleted": eid})
        patch = await request.json()
        if isinstance(patch.get("read"), str):
            patch["read"] = patch["read"].lower() in ("true", "1", "yes")
        _apply(email, patch, _EMAIL_FIELDS)
        return JSONResponse(email)

    @mcp.custom_route("/admin/api/scenario/{ticker}", methods=["POST"])
    async def admin_scenario_add(request: Request):
        st = get_state()
        tk = request.path_params["ticker"]
        sc = st.setdefault("scenarios", {}).setdefault(
            tk, {"period": "FY2026E", "base_tp": "", "note": "", "rows": []})
        row = {"scenario": "", "assumption": "", "eps_impact": "", "tp_impact": "",
               "hypothesis": "", "probability": ""}
        _apply(row, await request.json(), _SCENARIO_FIELDS)
        sc["rows"].append(row)
        return JSONResponse(row)

    @mcp.custom_route("/admin/api/scenario/{ticker}/{idx}", methods=["PATCH", "DELETE"])
    async def admin_scenario(request: Request):
        st = get_state()
        tk = request.path_params["ticker"]
        sc = (st.get("scenarios") or {}).get(tk)
        try:
            idx = int(request.path_params["idx"])
            row = sc["rows"][idx]
        except (TypeError, KeyError, IndexError, ValueError):
            return JSONResponse({"error": "unknown scenario row"}, status_code=404)
        if request.method == "DELETE":
            sc["rows"].pop(idx)
            return JSONResponse({"deleted": idx})
        _apply(row, await request.json(), _SCENARIO_FIELDS)
        return JSONResponse(row)

    @mcp.custom_route("/admin/api/labpreset", methods=["POST"])
    async def admin_labpreset_add(request: Request):
        st = get_state()
        body = await request.json()
        preset = {"key": f"custom_{len(st.setdefault('lab_presets', [])) + 1}",
                  "title": "", "tag": "CUSTOM", "args": {}}
        err = _apply_preset(preset, body)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        st["lab_presets"].append(preset)
        return JSONResponse(preset)

    @mcp.custom_route("/admin/api/labpreset/{idx}", methods=["PATCH", "DELETE"])
    async def admin_labpreset(request: Request):
        st = get_state()
        try:
            idx = int(request.path_params["idx"])
            preset = st["lab_presets"][idx]
        except (KeyError, IndexError, ValueError):
            return JSONResponse({"error": "unknown preset"}, status_code=404)
        if request.method == "DELETE":
            st["lab_presets"].pop(idx)
            return JSONResponse({"deleted": idx})
        err = _apply_preset(preset, await request.json())
        if err:
            return JSONResponse({"error": err}, status_code=400)
        return JSONResponse(preset)

    @mcp.custom_route("/admin/api/event", methods=["POST"])
    async def admin_event_add(request: Request):
        st = get_state()
        body = await request.json()
        n = 1 + max((int(ev["id"].split("-")[1]) for ev in st["calendar"]
                     if ev.get("id", "").startswith("E-")), default=0)
        event = {"id": f"E-{n:03d}", "date": "2026-07-23", "time": "09:00",
                 "kind": "meeting", "title": "", "ticker": "", "notes": ""}
        _apply(event, body, _EVENT_FIELDS)
        st["calendar"].append(event)
        return JSONResponse(event)

    @mcp.custom_route("/admin/api/event/{eid}", methods=["PATCH", "DELETE"])
    async def admin_event(request: Request):
        st = get_state()
        eid = request.path_params["eid"]
        event = next((ev for ev in st["calendar"] if ev["id"] == eid), None)
        if not event:
            return JSONResponse({"error": f"unknown event {eid}"}, status_code=404)
        if request.method == "DELETE":
            st["calendar"].remove(event)
            return JSONResponse({"deleted": eid})
        _apply(event, await request.json(), _EVENT_FIELDS)
        return JSONResponse(event)


ADMIN_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>FA Research — Demo Data Console</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--ink:#171717;--ink2:#404040;--mut:#6E7572;--line:#E7E8E7;--paper:#fff;--wash:#F4F6F5;
      --mint:#3E8E7E;--mint-wash:#EFF6F4;--red:#B42318;--warn:#B9770E;--ok:#2E8B57;}
*{box-sizing:border-box;margin:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
     background:#F7F9F8;color:var(--ink);font-size:14px;line-height:1.45}
.banner{background:__ENV_COLOR__;color:#fff;font-size:11px;font-weight:700;
        letter-spacing:.08em;text-transform:uppercase;padding:6px 14px;
        display:flex;align-items:center;gap:14px}
.banner .envb{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.45);
        border-radius:999px;padding:2px 12px;font-size:12px;white-space:nowrap}
.banner .mid{flex:1;text-align:center;color:rgba(255,255,255,.92)}
.banner .mid b{color:#F2C94C}
.banner .path{font-size:10.5px;color:rgba(255,255,255,.75);text-transform:none;white-space:nowrap}
header{display:flex;align-items:center;gap:14px;padding:14px 26px;background:var(--paper);
       border-bottom:1px solid var(--line)}
.logo{width:34px;height:34px;border-radius:8px;background:#101820;color:#9FD5C9;display:flex;
      align-items:center;justify-content:center;font-weight:800;font-size:13px}
header h1{font-size:16px}
header .sub{font-size:11.5px;color:var(--mut)}
header .right{margin-left:auto;display:flex;align-items:center;gap:14px}
.snap{font-size:11.5px;color:var(--mut)}
.btn{font-size:12.5px;font-weight:600;cursor:pointer;border-radius:9px;padding:8px 14px;
     border:1px solid var(--line);background:#fff;color:var(--ink)}
.btn:hover{border-color:var(--mint);background:var(--mint-wash)}
.btn.danger{color:var(--red);border-color:#FECDCA}
.btn.danger:hover{background:#FEF3F2}
.btn.primary{background:var(--ink);color:#fff;border-color:var(--ink)}
nav{display:flex;gap:4px;padding:0 26px;background:var(--paper);border-bottom:1px solid var(--line)}
nav button{border:none;background:none;font-size:13px;font-weight:600;color:var(--mut);
           padding:12px 14px;cursor:pointer;border-bottom:2px solid transparent}
nav button.active{color:var(--ink);border-bottom-color:var(--mint)}
main{max-width:1160px;margin:22px auto;padding:0 26px}
.head{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.head h2{font-size:19px}
.head .mut{color:var(--mut);font-size:12.5px}
.head .btn{margin-left:auto}
table{width:100%;border-collapse:collapse;background:var(--paper);border:1px solid var(--line);
      border-radius:12px;overflow:hidden;font-size:13px}
th{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);text-align:left;
   padding:9px 12px;border-bottom:1px solid var(--line);background:var(--wash)}
td{padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:none}
tbody tr{cursor:pointer}
tbody tr:hover{background:var(--mint-wash)}
.num{text-align:right;font-variant-numeric:tabular-nums}
.pill{font-size:10.5px;font-weight:700;border-radius:999px;padding:2px 9px;white-space:nowrap}
.pill.alert{background:#FEF3F2;color:var(--red)} .pill.positive{background:#E6F4EA;color:var(--ok)}
.pill.watch{background:#FBF1E0;color:var(--warn)} .pill.info{background:var(--wash);color:var(--mut)}
.pill.unread{background:var(--mint-wash);color:var(--mint)}
.pill.k-results{background:#FEF3F2;color:var(--red)} .pill.k-roadshow{background:#EFF3FE;color:#3538CD}
.pill.k-call{background:#E6F4EA;color:var(--ok)} .pill.k-meeting{background:var(--wash);color:var(--mut)}
.pill.k-control{background:#FBF1E0;color:var(--warn)}
/* drawer */
#ov{position:fixed;inset:0;background:rgba(16,24,32,.35);display:none}
#drawer{position:fixed;top:0;right:0;bottom:0;width:430px;max-width:92vw;background:var(--paper);
        border-left:1px solid var(--line);box-shadow:-12px 0 30px rgba(0,0,0,.08);display:none;
        flex-direction:column}
#drawer header{padding:16px 20px;border-bottom:1px solid var(--line)}
#drawer .body{padding:16px 20px;overflow:auto;flex:1}
#drawer .foot{padding:14px 20px;border-top:1px solid var(--line);display:flex;gap:10px}
label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;
      color:var(--mut);margin:12px 0 4px}
#envsel{width:auto;max-width:150px}
input,textarea,select{width:100%;font:inherit;font-size:13px;padding:8px 10px;border:1px solid var(--line);
      border-radius:8px;background:#fff;color:var(--ink)}
textarea{min-height:90px;resize:vertical}
#toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:#101820;color:#fff;
       font-size:12.5px;padding:9px 18px;border-radius:999px;opacity:0;transition:opacity .25s}
.mut{color:var(--mut))}
</style></head><body>
<div class="banner"><span class="envb">● __ENV_BADGE__</span>
<span class="mid"><b>PUBLIC DEMONSTRATION</b> &nbsp;·&nbsp; Synthetic research data — changes are temporary (in-memory) and revert to the snapshot</span>
<span class="path">__ENV_PATH__</span></div>
<header>
  <div class="logo">FA</div>
  <select id="envsel" class="btn" style="min-width:90px" onchange="switchEnv(this.value)"></select>
  <div><h1>FA Research — Demo Data Console</h1>
  <div class="sub">Exane BNPP CIB sell-side demo · edits feed the cockpit, dashboards and the agent instantly</div></div>
  <div class="right"><span class="snap">Snapshot: <b id="snap"></b><br>Story day: <b id="today"></b><br>Connector: <b id="mcpurl"></b><br>Nightly: <b id="nightly"></b></span>
  <button class="btn" onclick="doRebase()" title="Shift all dates so the warning day becomes today — deltas preserved">⇥ Rebase to today</button>
  <button class="btn danger" onclick="doReset()">↺ Reset demo data</button></div>
</header>
<nav id="tabs"></nav>
<main><div class="head"><h2 id="title"></h2><span class="mut" id="count"></span>
<button class="btn primary" id="addbtn" style="display:none"></button></div>
<div id="content"></div></main>
<div id="ov" onclick="closeDrawer()"></div>
<div id="drawer"><header><h1 id="dtitle" style="font-size:15px"></h1></header>
<div class="body" id="dbody"></div>
<div class="foot"><button class="btn primary" onclick="saveDrawer()">Save</button>
<button class="btn" onclick="closeDrawer()">Cancel</button>
<button class="btn danger" id="delbtn" style="margin-left:auto;display:none" onclick="delDrawer()">Delete</button></div></div>
<div id="toast"></div>
<script>
let S=null, TAB='coverage', CUR=null;
const TABS=[["coverage","Coverage"],["brief","Morning brief"],["emails","Emails"],
            ["calendar","Calendar"],["scenarios","Scenarios"],["agenda","Agenda & jobs"],
            ["reference","Reference (read-only)"]];
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
async function load(){S=await (await fetch('admin/api/state')).json();
  const sel=document.getElementById('envsel');
  sel.innerHTML=S.environments.map(e=>`<option ${e===S.environment?'selected':''}>${e}</option>`).join('')+
    '<option value="__new__">+ new env…</option>';
  document.getElementById('snap').textContent=S.snapshot_label;
  document.getElementById('today').textContent=S.today+(S.today===S.baseline_today?' (baseline)':' (rebased)');
  document.getElementById('mcpurl').textContent=location.origin+'/'+S.environment+'/mcp';
  fetch('admin/api/nightly').then(r=>r.json()).then(n=>{
    const rg=(n.regen||{})[S.environment],vf=(n.verify||{})[S.environment];
    const f=x=>x?((x.ok?'✓ ':'✗ ')+(x.finished||'').slice(5,16)):'—';
    document.getElementById('nightly').textContent='regen '+f(rg)+' · check '+f(vf);
    document.getElementById('nightly').title=n.scheduler+' · next: '+(n.next||'');}).catch(()=>{});
  render();}
function switchEnv(v){if(v==='__new__'){const n=prompt('New environment slug (a-z, 0-9, -):');
    if(!n||!/^[a-z0-9][a-z0-9_-]{0,23}$/.test(n)){load();return;}v=n;}
  location.href='/'+v+'/admin';}
function localDate(){const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');}
async function doRebase(){const t=localDate();
  if(!confirm('Shift all calendar dates and email timestamps so the story day ('+S.today+') becomes '+t+'? Deltas are preserved; Reset returns to the baseline.'))return;
  const r=await(await fetch('admin/api/rebase',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({date:t})})).json();
  toast(r.shifted_days?('Shifted by '+r.shifted_days+' day(s)'):'Already on '+t);load();}
function toast(m){const t=document.getElementById('toast');t.textContent=m;t.style.opacity=1;
  setTimeout(()=>t.style.opacity=0,1800);}
async function doReset(){if(!confirm('Reset ALL demo data to the baseline snapshot?'))return;
  await fetch('admin/api/reset',{method:'POST'});toast('Snapshot restored');load();}
function nav(){document.getElementById('tabs').innerHTML=TABS.map(([k,l])=>
  `<button class="${k===TAB?'active':''}" onclick="TAB='${k}';render()">${l}</button>`).join('');}
function render(){nav();const c=document.getElementById('content'),add=document.getElementById('addbtn');
  add.style.display='none';
  const T={coverage:rCov,brief:rBrief,emails:rMail,calendar:rCal,scenarios:rScen,
           agenda:rAgenda,reference:rRef}[TAB];T(c,add);}
function head(t,n){document.getElementById('title').textContent=t;
  document.getElementById('count').textContent=n;}
function rCov(c){head('Coverage roster',S.coverage.length+' names — click a row to edit');
  c.innerHTML=`<table><thead><tr><th>Ticker</th><th>Name</th><th>Rating</th>
  <th class="num">Target price</th><th class="num">Price</th><th class="num">Upside</th>
  <th class="num">Pre-mkt %</th><th>Status</th><th>Next catalyst</th></tr></thead><tbody>`+
  S.coverage.map(r=>`<tr onclick='openCov(${JSON.stringify(r.ticker)})'><td><b>${esc(r.ticker)}</b></td>
  <td>${esc(r.name)}</td><td>${esc(r.rating)}</td><td class="num">${r.target_price}</td>
  <td class="num">${r.price}</td><td class="num">${(r.upside_pct>0?'+':'')+r.upside_pct}%</td>
  <td class="num">${(r.premarket_pct>0?'+':'')+r.premarket_pct}%</td>
  <td>${esc(r.status)}</td><td>${esc(r.next_catalyst)}</td></tr>`).join('')+'</tbody></table>';}
function rBrief(c){head('Morning brief — overnight items',S.brief.length+' items — click to edit');
  c.innerHTML=`<table><thead><tr><th>Severity</th><th>Name</th><th>Headline</th>
  <th class="num">New TP</th><th>Ack</th></tr></thead><tbody>`+
  S.brief.map(b=>`<tr onclick='openBrief(${JSON.stringify(b.ticker)})'>
  <td><span class="pill ${esc(b.severity)}">${esc(b.severity)}</span></td><td><b>${esc(b.name)}</b></td>
  <td>${esc(b.headline)}<div class="mut" style="font-size:11.5px">${esc(b.valuation_impact)}</div></td>
  <td class="num">${b.new_target_price??'—'}</td><td>${b.acknowledged?'✓':''}</td></tr>`).join('')+'</tbody></table>';}
function rMail(c,add){head('Mailbox',S.emails.length+' emails — click to edit');
  add.style.display='';add.textContent='+ New email';add.onclick=()=>openMail(null);
  c.innerHTML=`<table><thead><tr><th></th><th>When</th><th>From</th><th>Subject</th><th>Ticker</th></tr></thead><tbody>`+
  S.emails.map(e=>`<tr onclick='openMail(${JSON.stringify(e.id)})'>
  <td>${e.read?'':'<span class="pill unread">unread</span>'}</td><td class="mut">${esc(e.ts)}</td>
  <td><b>${esc(e.from_name)}</b><div class="mut" style="font-size:11px">${esc(e.from_role)}</div></td>
  <td>${esc(e.subject)}<div class="mut" style="font-size:11.5px">${esc(e.body.slice(0,110))}…</div></td>
  <td>${esc(e.ticker)}</td></tr>`).join('')+'</tbody></table>';}
function rCal(c,add){head('Calendar',S.calendar.length+' events — click to edit');
  add.style.display='';add.textContent='+ New event';add.onclick=()=>openCal(null);
  c.innerHTML=`<table><thead><tr><th>Date</th><th>Time</th><th>Kind</th><th>Title</th><th>Ticker</th><th>Notes</th></tr></thead><tbody>`+
  S.calendar.map(ev=>`<tr onclick='openCal(${JSON.stringify(ev.id)})'><td>${esc(ev.date)}</td>
  <td>${esc(ev.time)}</td><td><span class="pill k-${esc(ev.kind)}">${esc(ev.kind)}</span></td>
  <td><b>${esc(ev.title)}</b></td><td>${esc(ev.ticker)}</td><td class="mut">${esc(ev.notes)}</td></tr>`).join('')+'</tbody></table>';}
function jobRun(j){const lr=j.last_run;if(!lr)return '—';
  if(j.status==='running')return lr.kind==='sdk_regen'?('⏳ '+(lr.done||0)+'/'+(lr.total||'…')+' docs'):'⏳ running…';
  if(lr.ok===false)return '✗ '+esc(lr.error||'failed');
  if(lr.kind==='sdk_regen')return '✓ '+(lr.files||[]).length+' docs · '+(lr.finished||'').slice(11,16);
  return '✓ simulated · '+(lr.finished||'').slice(11,16);}
function rAgenda(c){head('Agenda & jobs','agenda read-only — click a JOB to edit its schedule or run it now');
  c.innerHTML='<table><thead><tr><th>Agenda</th><th>Role</th><th>When</th></tr></thead><tbody>'+
  S.agenda.map(a=>`<tr><td><b>${esc(a.title)}</b></td><td>${esc(a.role)}</td><td>${esc(a.when)}</td></tr>`).join('')+
  '</tbody></table><br><table><thead><tr><th>Job</th><th>Runs at</th><th>Recurrence</th><th>Executor</th><th>Status</th><th>Last run</th></tr></thead><tbody>'+
  S.jobs.jobs.map((j,i)=>`<tr onclick='openJob(${i})'><td><b>${esc(j.label)}</b></td>
  <td class="mut">${esc(j.run_at||'—')}</td><td>${esc(j.recurrence||'once')}</td>
  <td>${j.executor==='sdk_regen'?'<span class="pill positive">Unique SDK</span>':'<span class="pill info">simulated</span>'}</td>
  <td>${esc(j.status)}</td><td class="mut">${jobRun(j)}</td></tr>`).join('')+'</tbody></table>'+
  '<p class="mut" style="font-size:12px;margin-top:10px">Due jobs execute automatically (checked every 10 s, Zurich time). '+
  '<b>Unique SDK</b> jobs really regenerate the 6 coverage reviews + cards and upload them to this environment\'s '+
  'Knowledge Base — the run shows per-document progress and the generated files below. '+
  '<b>once</b> runs a single time (default — no standing token cost); <b>daily</b> re-arms for the same time next day.</p>';
  if(S.jobs.jobs.some(j=>j.status==='running')&&!CUR)setTimeout(()=>{if(TAB==='agenda'&&!CUR)load();},3000);}
function openJob(i){const j=S.jobs.jobs[i];const lr=j.last_run;
  let extra='<div style="margin:10px 0"><button class="btn primary" onclick="runJob('+i+')">▶ Run now</button> '+
    '<span class="mut" style="font-size:12px">'+(j.executor==='sdk_regen'?'real — regenerates + uploads via the Unique SDK':'simulated — status transitions only')+'</span></div>';
  if(lr&&(lr.files||[]).length)extra+='<label>Documents generated (Unique SDK · '+esc((lr.finished||lr.started||'').slice(0,16))+')</label>'+
    '<div style="max-height:180px;overflow:auto;border:1px solid #2a3742;border-radius:8px;padding:8px;font-size:11.5px;line-height:1.7">'+
    lr.files.map(f=>`<div>📄 ${esc(f.path)} <span class="mut">${esc(f.content_id)}</span></div>`).join('')+'</div>';
  else if(lr&&lr.error)extra+='<p class="mut" style="color:#e07b7b;font-size:12px">Last run: '+esc(lr.error)+'</p>';
  openDrawer('Edit job — '+j.label,
    field('run_at','Runs at (YYYY-MM-DD HH:MM, Zurich)',j.run_at||'')+
    field('recurrence','Recurrence — once (default: single run, no standing token cost) or daily',j.recurrence||'once',{sel:['once','daily']})+
    field('status','Status',j.status,{sel:['scheduled','running','done']})+extra,
    v=>patch('admin/api/job/'+i,v));}
function runJob(i){fetch('admin/api/job/'+i+'/run',{method:'POST'}).then(r=>r.json())
  .then(r=>{closeDrawer();toast(r.started?('Job started — '+r.kind):(r.error||'error'));load();});}
function argsLabel(a){const p=[];if(a.fx_eur_move_pct)p.push('FX '+(a.fx_eur_move_pct>0?'+':'')+a.fx_eur_move_pct+'%');
  if(a.china_recovery)p.push('China '+a.china_recovery);if(a.destocking_end)p.push('destock '+a.destocking_end);
  return p.join(' + ')||'base (no shock)';}
function rScen(c,add){const tks=Object.keys(S.scenarios||{});
  head('Scenario hypotheses',(tks.length?tks.join(', '):'none')+' — the cases behind get_scenarios, the Lab and the pack');
  add.style.display='';add.textContent='+ New case (MC FP)';add.onclick=()=>openScen('MC FP',null);
  c.innerHTML=tks.map(tk=>{const sc=S.scenarios[tk];
    return `<h3 style="margin:6px 0 8px">${esc(tk)} <span class="mut" style="font-size:12px">· ${esc(sc.period)} · base ${esc(sc.base_tp)}</span></h3>
    <table style="margin-bottom:16px"><thead><tr><th>Scenario</th><th>Assumption</th>
    <th class="num">EPS</th><th class="num">Target price</th><th class="num">Prob.</th><th>Hypothesis</th></tr></thead><tbody>`+
    sc.rows.map((r,i)=>`<tr onclick='openScen(${JSON.stringify(tk)},${i})'>
    <td><b>${esc(r.scenario)}</b></td><td>${esc(r.assumption)}</td>
    <td class="num">${esc(r.eps_impact)}</td><td class="num">${esc(r.tp_impact)}</td>
    <td class="num">${esc(r.probability)}</td><td class="mut">${esc(r.hypothesis)}</td></tr>`).join('')+
    '</tbody></table>';}).join('')||'<p class="mut">No scenario sets in this environment.</p>';
  c.innerHTML+=`<h3 style="margin:18px 0 4px">Scenario Lab presets <span class="mut" style="font-size:12px">· the predefined shocks the Lab computes (get_scenario_board)</span></h3>
  <div style="margin-bottom:8px"><button class="btn" onclick="openPreset(null)">+ New preset</button></div>
  <table><thead><tr><th>Tag</th><th>Title</th><th>Shock (engine args)</th></tr></thead><tbody>`+
  (S.lab_presets||[]).map((p,i)=>`<tr onclick='openPreset(${i})'>
  <td><span class="pill info">${esc(p.tag)}</span></td><td><b>${esc(p.title)}</b></td>
  <td class="mut">${esc(argsLabel(p.args||{}))}</td></tr>`).join('')+'</tbody></table>';}
function openPreset(idx){const p=idx==null?{title:'',tag:'CUSTOM',args:{}}:S.lab_presets[idx];
  const a=p.args||{};
  openDrawer(idx==null?'New Lab preset':'Edit Lab preset — '+p.title,
    field('title','Title',p.title)+field('tag','Tag (group label)',p.tag)+
    field('fx_eur_move_pct','FX move % (blank/0 = none, ±15)',a.fx_eur_move_pct??'')+
    field('china_recovery','China recovery',a.china_recovery||'none',{sel:['none','q2_26','q4_26','fy27']})+
    field('destocking_end','Destocking end (LVMH axis)',a.destocking_end||'h1_26',{sel:['h1_26','h2_26','fy27']}),
    v=>idx==null?patch('admin/api/labpreset',v,'POST'):patch('admin/api/labpreset/'+idx,v),
    idx==null?null:()=>patch('admin/api/labpreset/'+idx,{},'DELETE'));}
function openScen(tk,idx){const sc=S.scenarios[tk];
  const r=idx==null?{scenario:'',assumption:'',eps_impact:'',tp_impact:'',hypothesis:'',probability:''}:sc.rows[idx];
  openDrawer(idx==null?('New scenario case — '+tk):('Edit case — '+esc(r.scenario)),
    field('scenario','Scenario',r.scenario)+field('assumption','Assumption',r.assumption,'textarea')+
    field('eps_impact','EPS impact (e.g. −3.5%)',r.eps_impact)+
    field('tp_impact','Target price (e.g. €595)',r.tp_impact)+
    field('probability','Probability (e.g. 20%)',r.probability)+
    field('hypothesis','Our hypothesis',r.hypothesis,'textarea'),
    v=>idx==null?patch('admin/api/scenario/'+encodeURIComponent(tk),v,'POST')
               :patch('admin/api/scenario/'+encodeURIComponent(tk)+'/'+idx,v),
    idx==null?null:()=>patch('admin/api/scenario/'+encodeURIComponent(tk)+'/'+idx,{},'DELETE'));}
function rRef(c){head('Reference data','read-only — consensus and our estimates (the analyst&#39;s numbers)');
  c.innerHTML='<pre style="background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px;overflow:auto;font-size:12px">'+
  esc(JSON.stringify(S.reference,null,1))+'</pre>';}
/* drawer plumbing */
function field(k,l,v,type){if(type==='textarea')return `<label>${l}</label><textarea data-k="${k}">${esc(v)}</textarea>`;
  if(type&&type.sel)return `<label>${l}</label><select data-k="${k}">`+type.sel.map(o=>
    `<option ${String(o)===String(v)?'selected':''}>${o}</option>`).join('')+'</select>';
  return `<label>${l}</label><input data-k="${k}" value="${esc(v)}">`;}
function openDrawer(title,fields,save,del){document.getElementById('dtitle').textContent=title;
  document.getElementById('dbody').innerHTML=fields;CUR={save,del};
  document.getElementById('delbtn').style.display=del?'':'none';
  document.getElementById('ov').style.display='block';document.getElementById('drawer').style.display='flex';}
function closeDrawer(){document.getElementById('ov').style.display='none';
  document.getElementById('drawer').style.display='none';CUR=null;}
function vals(){const o={};document.querySelectorAll('#dbody [data-k]').forEach(el=>{
  o[el.dataset.k]=el.tagName==='SELECT'?el.value:el.value;});return o;}
async function saveDrawer(){await CUR.save(vals());closeDrawer();toast('Saved — the MCP now serves this');load();}
async function delDrawer(){if(!confirm('Delete this item?'))return;await CUR.del();closeDrawer();toast('Deleted');load();}
async function patch(url,body,method='PATCH'){const r=await fetch(url,{method,
  headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(!r.ok)toast('Error '+r.status);return r;}
function openCov(tk){const r=S.coverage.find(x=>x.ticker===tk);
  openDrawer('Edit coverage — '+r.name,
    field('rating','Rating',r.rating,{sel:['Outperform','Neutral','Underperform']})+
    field('target_price','Target price',r.target_price)+field('price','Last price',r.price)+
    field('premarket_pct','Pre-market %',r.premarket_pct)+field('status','Status',r.status)+
    field('next_catalyst','Next catalyst',r.next_catalyst),
    v=>patch('admin/api/coverage/'+encodeURIComponent(tk),v));}
function openBrief(tk){const b=S.brief.find(x=>x.ticker===tk);
  openDrawer('Edit brief item — '+b.name,
    field('severity','Severity',b.severity,{sel:['alert','positive','watch','info']})+
    field('headline','Headline',b.headline)+field('detail','Detail',b.detail,'textarea')+
    field('valuation_impact','Valuation impact',b.valuation_impact,'textarea')+
    field('new_target_price','New target price (blank = none)',b.new_target_price??'')+
    field('acknowledged','Acknowledged',b.acknowledged,{sel:['false','true']}),
    v=>patch('admin/api/brief/'+encodeURIComponent(tk),v));}
function openMail(id){const e=id?S.emails.find(x=>x.id===id):
    {ts:'2026-07-23 08:00',from_name:'',from_role:'',subject:'',body:'',ticker:'',read:false};
  openDrawer(id?('Edit email '+id):'New email',
    field('ts','Timestamp',e.ts)+field('from_name','From',e.from_name)+
    field('from_role','Role',e.from_role)+field('subject','Subject',e.subject)+
    field('body','Body',e.body,'textarea')+field('ticker','Ticker (optional)',e.ticker)+
    field('read','Read',e.read,{sel:['false','true']}),
    v=>id?patch('admin/api/email/'+id,v):patch('admin/api/email',v,'POST'),
    id?()=>patch('admin/api/email/'+id,{},'DELETE'):null);}
function openCal(id){const ev=id?S.calendar.find(x=>x.id===id):
    {date:'2026-07-23',time:'09:00',kind:'meeting',title:'',ticker:'',notes:''};
  openDrawer(id?('Edit event '+id):'New event',
    field('date','Date (YYYY-MM-DD)',ev.date)+field('time','Time',ev.time)+
    field('kind','Kind',ev.kind,{sel:['results','roadshow','call','meeting','control']})+
    field('title','Title',ev.title)+field('ticker','Ticker (optional)',ev.ticker)+
    field('notes','Notes',ev.notes,'textarea'),
    v=>id?patch('admin/api/event/'+id,v):patch('admin/api/event',v,'POST'),
    id?()=>patch('admin/api/event/'+id,{},'DELETE'):null);}
load();
</script></body></html>
"""
