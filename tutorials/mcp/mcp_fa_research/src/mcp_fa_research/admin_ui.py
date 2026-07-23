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

from fastapi.responses import HTMLResponse, JSONResponse
from starlette.requests import Request

import seed

_COVERAGE_FIELDS = {"rating", "target_price", "price", "premarket_pct", "status",
                    "next_catalyst"}
_BRIEF_FIELDS = {"headline", "detail", "valuation_impact", "severity", "acknowledged",
                 "new_target_price", "suggested_action"}
_EMAIL_FIELDS = {"ts", "from_name", "from_role", "subject", "body", "ticker", "read"}
_EVENT_FIELDS = {"date", "time", "kind", "title", "ticker", "notes"}
_NUM = {"target_price", "price", "premarket_pct", "new_target_price"}


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


def register(mcp, get_state, reset_state) -> None:
    @mcp.custom_route("/admin", methods=["GET"])
    async def admin_page(request: Request):
        return HTMLResponse(ADMIN_HTML)

    @mcp.custom_route("/admin/api/state", methods=["GET"])
    async def admin_state(request: Request):
        st = get_state()
        return JSONResponse({
            "snapshot_label": st.get("snapshot_label", seed.SNAPSHOT_LABEL),
            "generated_at": st.get("generated_at"),
            "coverage": st["coverage"],
            "brief": st["brief"],
            "emails": sorted(st["emails"], key=lambda e: e["ts"], reverse=True),
            "calendar": sorted(st["calendar"], key=lambda ev: (ev["date"], ev["time"])),
            "agenda": seed.AGENDA,
            "jobs": st["jobs"],
            "reference": {
                "consensus": seed.CONSENSUS, "estimates": seed.OUR_ESTIMATES,
                "scenarios": seed.SCENARIOS,
            },
        })

    @mcp.custom_route("/admin/api/reset", methods=["POST"])
    async def admin_reset(request: Request):
        st = reset_state()
        return JSONResponse({"reset": True, "snapshot_label": st["snapshot_label"]})

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
        email = {"id": f"M-{n:03d}", "ts": "2026-07-23 08:00", "from_name": "",
                 "from_role": "", "subject": "", "body": "", "ticker": "", "read": False}
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
.banner{background:#101820;color:#F2C94C;text-align:center;font-size:11px;font-weight:700;
        letter-spacing:.08em;text-transform:uppercase;padding:6px}
.banner b{color:#fff}
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
input,textarea,select{width:100%;font:inherit;font-size:13px;padding:8px 10px;border:1px solid var(--line);
      border-radius:8px;background:#fff;color:var(--ink)}
textarea{min-height:90px;resize:vertical}
#toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:#101820;color:#fff;
       font-size:12.5px;padding:9px 18px;border-radius:999px;opacity:0;transition:opacity .25s}
.mut{color:var(--mut))}
</style></head><body>
<div class="banner"><b>PUBLIC DEMONSTRATION</b> &nbsp;·&nbsp; Synthetic research data — changes are temporary (in-memory) and revert to the snapshot</div>
<header>
  <div class="logo">FA</div>
  <div><h1>FA Research — Demo Data Console</h1>
  <div class="sub">Exane BNPP CIB sell-side demo · edits feed the cockpit, dashboards and the agent instantly</div></div>
  <div class="right"><span class="snap">Snapshot: <b id="snap"></b></span>
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
            ["calendar","Calendar"],["agenda","Agenda & jobs"],["reference","Reference (read-only)"]];
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
async function load(){S=await (await fetch('admin/api/state')).json();
  document.getElementById('snap').textContent=S.snapshot_label;render();}
function toast(m){const t=document.getElementById('toast');t.textContent=m;t.style.opacity=1;
  setTimeout(()=>t.style.opacity=0,1800);}
async function doReset(){if(!confirm('Reset ALL demo data to the baseline snapshot?'))return;
  await fetch('admin/api/reset',{method:'POST'});toast('Snapshot restored');load();}
function nav(){document.getElementById('tabs').innerHTML=TABS.map(([k,l])=>
  `<button class="${k===TAB?'active':''}" onclick="TAB='${k}';render()">${l}</button>`).join('');}
function render(){nav();const c=document.getElementById('content'),add=document.getElementById('addbtn');
  add.style.display='none';
  const T={coverage:rCov,brief:rBrief,emails:rMail,calendar:rCal,agenda:rAgenda,reference:rRef}[TAB];T(c,add);}
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
function rAgenda(c){head('Agenda & jobs','read-only — roadshows from the seed, jobs from state');
  c.innerHTML='<table><thead><tr><th>Agenda</th><th>Role</th><th>When</th></tr></thead><tbody>'+
  S.agenda.map(a=>`<tr><td><b>${esc(a.title)}</b></td><td>${esc(a.role)}</td><td>${esc(a.when)}</td></tr>`).join('')+
  '</tbody></table><br><table><thead><tr><th>Job</th><th>Status</th></tr></thead><tbody>'+
  S.jobs.jobs.map(j=>`<tr><td>${esc(j.label)}</td><td>${esc(j.status)}</td></tr>`).join('')+'</tbody></table>';}
function rRef(c){head('Reference data','read-only — consensus, our estimates, scenario hypotheses (edited in code / by the analyst)');
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
