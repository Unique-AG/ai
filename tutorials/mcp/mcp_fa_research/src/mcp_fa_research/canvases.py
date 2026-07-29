"""canvases.py — VENDORED from sandbox python/fa-demo/build_reviews.py (keep in sync).

Nightly, the MCP regenerates the six coverage reviews + coverage cards itself and
uploads them via the Unique SDK (see nightly.py). Ids for openDocument buttons come
from per-env maps (seed.REVIEW_IDS_BY_ENV + FA_NOTE_IDS_BY_ENV_JSON), not sidecars.
"""

from __future__ import annotations

import html
import json as _json
import os

import chart_pack
import impact
import seed

REVIEW_IDS: dict = {}
NOTE_IDS: dict = {}
_FA_ENV = "qa"
_STAMP = ""

SEV = {  # severity → (label, css class)
    "alert": ("Profit warning", "sev-alert"),
    "positive": ("Upside", "sev-ok"),
    "watch": ("Watch", "sev-warn"),
    "info": ("Note", "sev-info"),
}


def e(s) -> str:
    return html.escape(str(s), quote=True)


def _current_overnight() -> dict:
    """Per-env mutable overnight map (live brief edits, seed fallback) — see seed.current_overnight."""
    return seed.current_overnight()


CSS = """
  .rv{--ink:#171717;--ink2:#404040;--mut:#6E7572;--line:#E7E8E7;--paper:#fff;--wash:#F4F6F5;
      --mint:#3E8E7E;--mint-dot:#5FAE9E;--mint-wash:#EFF6F4;--ok:#2E8B57;--ok-wash:#E6F4EA;--ok-line:#BFE3CC;
      --warn:#B9770E;--warn-wash:#FBF1E0;--warn-line:#EAD6AC;--red:#B42318;--red-wash:#FEF3F2;--red-line:#FECDCA;
      font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
      color:var(--ink);background:#F7F9F8;padding:22px;max-width:1024px;margin:0 auto;font-size:14px;line-height:1.45;}
  .rv *{box-sizing:border-box;}
  .rv h1{font-size:22px;font-weight:700;margin:0;letter-spacing:-.01em;}
  .rv h2{font-size:14px;font-weight:700;margin:0 0 10px;}
  .rv .mut{color:var(--mut);font-weight:500;}
  .rv a{color:inherit;text-decoration:none;}
  .live-tag{display:inline-flex;align-items:center;gap:6px;font-size:10.5px;font-weight:700;letter-spacing:.05em;
            text-transform:uppercase;color:var(--mint);background:var(--mint-wash);border-radius:999px;padding:3px 10px;margin-left:8px;}
  .live-tag::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--mint-dot);}
  /* coverage switcher */
  .switch{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:16px;}
  .sw{font-size:12.5px;font-weight:600;border:1px solid var(--line);color:var(--ink2);background:#fff;
      border-radius:999px;padding:6px 13px;cursor:pointer;}
  .sw:hover{border-color:var(--mint-dot);background:var(--mint-wash);}
  .sw.active{background:var(--ink);border-color:var(--ink);color:#fff;cursor:default;}
  .hdr{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;margin-bottom:6px;}
  .rate{font-size:11px;font-weight:700;letter-spacing:.03em;text-transform:uppercase;border-radius:999px;padding:4px 12px;border:1px solid;}
  .rate.Outperform{color:var(--ok);background:var(--ok-wash);border-color:var(--ok-line);}
  .rate.Neutral{color:var(--mut);background:var(--wash);border-color:var(--line);}
  .rate.Underperform{color:var(--warn);background:var(--warn-wash);border-color:var(--warn-line);}
  .sub{color:var(--mut);font-size:12.5px;margin:6px 0 16px;}
  /* cards + tiles */
  .card{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin-bottom:14px;}
  .tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px;}
  .tile{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:12px 14px;}
  .tile .k{font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;color:var(--mut);}
  .tile .v{font-size:17px;font-weight:700;margin-top:4px;font-variant-numeric:tabular-nums;}
  .tile .s{font-size:11px;color:var(--mut);margin-top:2px;}
  /* overnight banner */
  .ov{border:1px solid;border-left-width:3px;border-radius:12px;padding:14px 16px;margin-bottom:14px;}
  .ov.sev-alert{border-color:var(--red-line);border-left-color:var(--red);background:var(--red-wash);}
  .ov.sev-ok{border-color:var(--ok-line);border-left-color:var(--ok);background:var(--ok-wash);}
  .ov.sev-warn{border-color:var(--warn-line);border-left-color:var(--warn);background:var(--warn-wash);}
  .ov.sev-info{border-color:var(--line);border-left-color:var(--mut);background:var(--wash);}
  .ov .tag{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;}
  .ov.sev-alert .tag{color:var(--red);} .ov.sev-ok .tag{color:var(--ok);}
  .ov.sev-warn .tag{color:var(--warn);} .ov.sev-info .tag{color:var(--mut);}
  .ov .h{font-weight:700;margin:4px 0;}
  .ov .imp{color:var(--ink2);}
  /* quote strip (live) */
  .quote{display:flex;align-items:center;gap:14px;background:var(--paper);border:1px solid var(--line);
         border-radius:12px;padding:11px 16px;margin-bottom:14px;font-variant-numeric:tabular-nums;}
  .quote .qt{font-weight:700;} .quote .qp{font-weight:700;} .quote .up{color:var(--ok);} .quote .dn{color:var(--red);}
  .quote .state{color:var(--mut);font-size:12.5px;}
  .blkt{font-size:10.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--mut);
        font-weight:700;margin:2px 2px 6px;}
  .thl{margin:0 0 4px;padding-left:20px;color:var(--ink2);}
  .thl li{margin:3px 0;}
  .qwrap{padding:12px 16px 10px;margin-bottom:14px;}
  .qwrap .quote{border:none;padding:8px 0 0;margin-bottom:0;background:none;}
  .qc{color:var(--ok);font-weight:600;} .qc[data-chg^="-"],.qc[data-chg^="−"]{color:var(--red);}
  .qsrc{color:var(--mut);font-size:10.5px;margin-left:auto;text-align:right;}
  .spark{height:24px;width:120px;vertical-align:middle;flex-shrink:0;}
  .bigchart{width:100%;height:auto;display:block;}
  .crow{display:none;}
  .qtape{display:flex;flex-direction:column;gap:0;align-items:stretch;}
  .qrow{display:flex;align-items:center;gap:12px;padding:5px 6px;border-bottom:1px dashed var(--line);
        border-radius:8px;font-variant-numeric:tabular-nums;}
  .qrow:last-of-type{border-bottom:none;}
  .qrow .qt{min-width:105px;font-weight:700;}

  .prow{display:flex;align-items:center;gap:10px;margin:6px 0;}
  .prow .pcb{width:15px;height:15px;accent-color:#0E7C7B;flex-shrink:0;}
  .ai-input{flex:1;min-width:220px;border:1px solid var(--line);border-radius:8px;padding:8px 10px;
            font:inherit;font-size:12px;color:var(--ink);background:var(--paper);}
  .statbtn{border:none;background:none;color:inherit;font:inherit;text-decoration:underline dotted;
           cursor:pointer;padding:0;}
  .spin{width:14px;height:14px;border:2px solid var(--line);border-top-color:var(--mint);border-radius:50%;
        display:inline-block;animation:rvspin .8s linear infinite;vertical-align:middle;}
  @keyframes rvspin{to{transform:rotate(360deg);}}
  /* tables + lists */
  table.est{width:100%;border-collapse:collapse;font-size:13px;}
  .est th{text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);
          padding:6px 10px;border-bottom:1px solid var(--line);}
  .est td{padding:8px 10px;border-bottom:1px solid var(--line);}
  .est td.num{text-align:right;font-variant-numeric:tabular-nums;}
  .est tr:last-child td{border-bottom:none;}
  ul.log{list-style:none;padding:0;margin:0;} ul.log li{padding:6px 0;border-bottom:1px solid var(--line);font-size:13px;color:var(--ink2);}
  ul.log li:last-child{border-bottom:none;}
  /* key-financials table — estimate columns get the mint wash */
  .est td.e,.est th.e{background:var(--mint-wash);}
  .est td:first-child{font-weight:600;}
  /* Exane-style figures: teal caption rule, CSS bar charts, source line */
  .figgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;}
  .fig{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:12px 14px;}
  .figcap{font-size:12.5px;font-weight:700;color:#0E7C7B;border-top:2px solid #0E7C7B;padding-top:7px;margin-bottom:10px;}
  .figsrc{font-size:10px;color:var(--mut);font-style:italic;margin-top:8px;}
  .chart{display:flex;gap:7px;}
  .col{flex:1;display:flex;flex-direction:column;align-items:center;min-width:0;}
  .val{font-size:10px;font-weight:700;color:var(--ink2);margin-bottom:3px;font-variant-numeric:tabular-nums;white-space:nowrap;}
  .zones{width:100%;height:96px;display:flex;flex-direction:column;}
  .zone{position:relative;width:100%;display:flex;justify-content:center;}
  .zone.pos{align-items:flex-end;border-bottom:1.5px solid #B9C4C0;}
  .zone.neg{align-items:flex-start;}
  .bar{display:block;width:58%;background:#137F7B;border-radius:2px 2px 0 0;min-height:2px;}
  .zone.neg .bar{background:#C4622D;border-radius:0 0 2px 2px;}
  .bar.e{background-image:repeating-linear-gradient(45deg,rgba(255,255,255,.45) 0 3px,transparent 3px 6px);}
  .xl{font-size:9.5px;color:var(--mut);margin-top:4px;}
  /* actions */
  .acts{display:flex;gap:9px;flex-wrap:wrap;margin-top:2px;}
  .btn{font-size:12.5px;font-weight:600;cursor:pointer;border-radius:9px;padding:9px 14px;border:1px solid var(--line);
       color:var(--ink);background:#fff;display:inline-flex;align-items:center;gap:7px;}
  .btn:hover{border-color:var(--mint-dot);background:var(--mint-wash);}
  .btn.primary{background:var(--ink);border-color:var(--ink);color:#fff;}
  .foot{color:var(--mut);font-size:11px;margin-top:16px;text-align:center;}
"""




def _switch(cur: str, names: list[tuple]) -> str:
    """Coverage switcher. All reviews are PRECOMPUTED (the nightly build) — switching opens
    the sibling document directly via openDocument (baked contentId: no agent turn, no
    regeneration). Falls back to sendPrompt only while a name has no known contentId yet
    (first upload; run fetch-ids then rebuild to bake the ids)."""
    out = []
    ck = REVIEW_IDS.get("__cockpit__", "")
    if ck:
        out.append(f'<button class="sw" data-unique-action="openDocument" '
                   f"data-unique-payload='{{\"contentId\":\"{e(ck)}\"}}'>⌂ Overview</button>")
    for tk, nm in names:
        if tk == cur:
            out.append(f'<span class="sw active">{e(nm)}</span>')
            continue
        cid = REVIEW_IDS.get(tk, "")
        if cid:
            out.append(f'<button class="sw" data-unique-action="openDocument" '
                       f"data-unique-payload='{{\"contentId\":\"{e(cid)}\"}}'>{e(nm)}</button>")
        else:
            prompt = f"Open the coverage review for {nm} ({tk}) — the review.html in CIB - Sell-Side Equity Analyst/names/{tk}/."
            out.append(f'<button class="sw" data-unique-action="sendPrompt" '
                       f"data-unique-payload='{{\"prompt\":\"{e(prompt)}\"}}'>{e(nm)}</button>")
    out.append(f'<button class="sw" title="Edit the demo data — opens the console in a new tab" '
               f'data-unique-action="openExternal" data-unique-payload='
               f"'{{\"url\":\"https://fa-research-mcp.azurewebsites.net/{_FA_ENV}/admin\"}}'"
               f'>⚙ Demo data</button>')
    return '<div class="switch">' + "".join(out) + "</div>"


def _tile(k, v, s=""):
    return f'<div class="tile"><div class="k">{e(k)}</div><div class="v">{v}</div>' + \
           (f'<div class="s">{e(s)}</div>' if s else "") + "</div>"


def _fmt_ccy(v, ccy):
    sym = {"EUR": "€", "CHF": "CHF ", "USD": "$", "GBP": "£"}.get(ccy, "")
    return f"{sym}{v:,.0f}" if isinstance(v, (int, float)) else e(v)


def _chart_fig(n: int, series: dict) -> str:
    """One Exane-style figure card: teal caption, CSS bar chart (geometry precomputed
    by the MCP chart pack: zero_pct axis split, per-point pct heights, estimate bars
    striped, negatives orange below the axis), source line."""
    zero = series["zero_pct"]
    has_neg = series["has_neg"]
    cols = []
    for p in series["points"]:
        est = " e" if p["kind"] == "e" else ""
        bar_pos = f'<i class="bar{est}" style="height:{p["pct"]}%"></i>' if not p["neg"] else ""
        bar_neg = f'<i class="bar{est}" style="height:{p["pct"]}%"></i>' if p["neg"] else ""
        if has_neg:
            zones = (f'<div class="zones">'
                     f'<div class="zone pos" style="height:{zero}%">{bar_pos}</div>'
                     f'<div class="zone neg" style="height:{100 - zero:g}%">{bar_neg}</div>'
                     f'</div>')
        else:
            zones = (f'<div class="zones">'
                     f'<div class="zone pos" style="height:100%">{bar_pos}</div>'
                     f'</div>')
        cols.append(f'<div class="col"><b class="val">{e(p["value_label"])}</b>{zones}'
                    f'<span class="xl">{e(p["label"])}</span></div>')
    return (f'<div class="fig"><div class="figcap">Figure {n}: {e(series["title"])}</div>'
            f'<div class="chart">{"".join(cols)}</div>'
            f'<div class="figsrc">{e(series["source"])}</div></div>')


def _fundamentals(tk: str) -> str:
    """The 'detailed numbers + charts' block: key-financials table (FY23-28e, estimate
    columns washed) + the Exane-style figure grid. Data = chart_pack (the MCP's
    get_financials) — same source the agent quotes in chat."""
    fin = chart_pack.get_financials(tk)
    if not fin:
        return ""
    kf = fin["key_financials"]
    est_cols = set(kf["estimate_cols"])
    head = "".join(
        f'<th class="num{" e" if i in est_cols else ""}">{e(h)}</th>' if i else "<th></th>"
        for i, h in enumerate(kf["header"]))
    body = "".join(
        "<tr>" + "".join(
            f'<td class="num{" e" if j in est_cols else ""}">{e(v)}</td>' if j else f"<td>{e(v)}</td>"
            for j, v in enumerate(row)) + "</tr>"
        for row in kf["rows"])
    table = (f'<div class="card"><h2>Key financials <span class="mut">· FY2023-28e · '
             f'FA Research MCP (synthetic)</span></h2>'
             f'<table class="est fin"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
             f'<p class="mut" style="margin:10px 0 0;font-size:11px;font-style:italic">{e(kf["source"])}</p></div>')
    figs = "".join(_chart_fig(i + 1, s) for i, s in enumerate(fin["charts"]))
    return table + f'<div class="card"><h2>Exane figures <span class="mut">· FY2023-28e · actuals 'f'vs estimates (synthetic)</span></h2><div class="figgrid">{figs}</div></div>'


_PRODUCTS = [  # (key in NOTE_IDS, icon, label)
    ("initiation", "📄", "Coverage initiation (PDF)"),
    ("preview", "📄", "Pre-release review (PDF)"),
    ("postview", "📄", "Post-release review (PDF)"),
    ("scenarios", "📄", "Scenario analysis (PDF)"),
    ("deck", "📊", "Company deck (PPTX)"),
    ("model", "📈", "Sell-side model (XLSX)"),
]

# Inline script: rewrites the action buttons' data-unique-payload from the ticked
# checkboxes + the free-text instruction on EVERY change. The bridge reads the
# attribute at click time (verified in the monorepo bridge implementation), and
# canvas <script> runs inside the sandboxed iframe — no bridge changes needed.
_PRODUCTS_SCRIPT = """
<script>
(function(){
  var card = document.getElementById('prodcard');
  if (!card) return;
  var NAME = card.getAttribute('data-name'), TK = card.getAttribute('data-tk');
  function sel(){
    var docs = [];
    card.querySelectorAll('.pcb:checked').forEach(function(cb){ docs.push(cb.getAttribute('data-doc')); });
    return docs;
  }
  function set(id, prompt){
    var el = document.getElementById(id);
    if (el) el.setAttribute('data-unique-payload', JSON.stringify({prompt: prompt}));
  }
  function sync(){
    var docs = sel(), n = docs.length, list = docs.join('; ');
    var extraEl = card.querySelector('.ai-input');
    var instr = extraEl ? extraEl.value.trim() : '';
    var extra = instr ? ' Additional instructions: "' + instr + '".' : '';
    var scope = n ? 'these ' + n + ' selected research product(s): ' + list
                  : 'ALL research products (none ticked - treat as all)';
    set('regen-sel', 'Regenerate ' + scope + ' for ' + NAME + ' (' + TK + '). Rebuild note '
      + 'products with the exane-desknote skill, decks with the exane-roadshow-deck skill, '
      + 'and the Excel model with the exane-financial-model skill.' + extra);
    set('submit-sel', 'Submit ' + scope + ' for ' + NAME + ' (' + TK + ') for pre-publication '
      + 'control: one submit_for_control call per product (kind: note for PDFs and the model, '
      + 'pack for the scenario analysis, deck for PPTX). Ask me for the priority first '
      + '(one question), then confirm the queue item ids.' + extra);
    set('ai-sel', instr
      ? 'Apply this instruction to ' + scope + ' for ' + NAME + ' (' + TK + '): "' + instr
        + '". Use the matching skills (exane-desknote / exane-roadshow-deck / '
        + 'exane-financial-model) and show me exactly what changed.'
      : 'I want to edit the ' + NAME + ' (' + TK + ') research products with AI but have not '
        + 'typed an instruction yet - ask me what to change on: ' + (list || 'the product set') + '.');
  }
  card.addEventListener('change', sync);
  card.addEventListener('input', sync);
  sync();
})();
</script>"""




# Generic Edit-with-AI wiring: rewrites the button's payload from the sibling
# input on every keystroke (bridge reads the attribute at click time).
_EDIT_AI_SCRIPT = """
<script>
(function(){
  function wire(){
  document.querySelectorAll('[data-ai-card]').forEach(function(card){
    var inp = card.querySelector('.ai-input'), btn = card.querySelector('.ai-go');
    if (!inp || !btn) return;
    var base = btn.getAttribute('data-ai-base') || '';
    function sync(){
      var v = inp.value.trim();
      var prompt = v ? base.replace('__INSTR__', v)
                     : 'I want to edit this with AI but have not typed an instruction — '
                       + 'ask me what to change. Context: ' + base.replace('__INSTR__', '(pending)');
      btn.setAttribute('data-unique-payload', JSON.stringify({prompt: prompt}));
    }
    if (card.getAttribute('data-ai-wired')) return;
    card.setAttribute('data-ai-wired', '1');
    card.addEventListener('input', sync);
    sync();
  });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wire);
  } else { wire(); }
})();
</script>"""


def _edit_rows(placeholder: str, base_prompt: str) -> str:
    """Input on one line, the Edit-with-AI button on the next (house layout)."""
    fallback = _json.dumps({"prompt": base_prompt.replace(
        "__INSTR__", "(no instruction typed yet — ask me what to change first)")})
    return ('<div class="prow"><input type="text" class="ai-input" placeholder="'
            + e(placeholder) + '"></div>'
            '<div class="prow"><button class="btn primary ai-go" '
            'data-unique-action="sendPrompt" '
            "data-unique-payload='" + fallback.replace("'", "&#39;") + "' "
            "data-ai-base='" + e(base_prompt).replace("'", "&#39;") + "'>"
            '✨ Edit with AI</button></div>')


def _products(tk: str, name: str) -> str:
    """'Ready to review' card — pre-generated products with per-document CHECKBOX
    selection: regenerate / submit-for-control act on the ticked set, and a free-text
    'Edit with AI' instruction is woven into the prompts (payloads rewritten live by
    _PRODUCTS_SCRIPT)."""
    ids = NOTE_IDS.get(tk, {})
    rows = []
    for key, icon, label in _PRODUCTS:
        cid = ids.get(key)
        if not cid:
            continue
        payload = _json.dumps({"contentId": cid})
        rows.append(
            '<div class="prow">'
            f'<input type="checkbox" class="pcb" data-doc="{e(label)}" checked>'
            '<button class="btn" data-unique-action="openDocument" '
            "data-unique-payload='" + payload + "'>"
            f'{icon} {e(label)}</button></div>')
    if not rows:
        return ""
    fb_regen = _json.dumps({"prompt": f"Regenerate the research products for {name} "
                            f"({tk}): note products with the exane-desknote skill, decks "
                            f"with exane-roadshow-deck, the Excel model with "
                            f"exane-financial-model."}).replace("'", "&#39;")
    fb_submit = _json.dumps({"prompt": f"Submit the {name} ({tk}) research products for "
                             f"pre-publication control (one submit_for_control per "
                             f"product); ask me for the priority first."}).replace("'", "&#39;")
    fb_ai = _json.dumps({"prompt": f"I want to edit the {name} ({tk}) research products "
                         f"with AI — ask me what to change, then use the matching "
                         f"skills."}).replace("'", "&#39;")
    fb_model = _json.dumps({"prompt": (
        f"Update the {name} ({tk}) sell-side Excel model with the LATEST data — "
        "use the exane-financial-model skill in UPDATE mode: pull fresh figures "
        "(get_financials, get_coverage, get_note_pack for LVMH), overwrite the "
        "changed inputs/actuals in the existing workbook (keep every formula "
        "live), save it back to CIB - Sell-Side Equity Analyst/names/" + tk +
        "/notes/ under the SAME filename, and report the delta: EPS by year and "
        "target price vs the prior version.")}).replace("'", "&#39;")
    controls = (
        '<div class="prow" style="margin-top:10px;flex-wrap:wrap;gap:8px">'
        + '<button class="btn" id="regen-sel" data-unique-action="sendPrompt" '
        + "data-unique-payload='" + fb_regen + "'>\u21bb Regenerate selected</button>"
        + '<button class="btn" id="submit-sel" data-unique-action="sendPrompt" '
        + "data-unique-payload='" + fb_submit + "'>\u21ea Submit selected for control</button>"
        + '<button class="btn" data-unique-action="sendPrompt" '
        + "data-unique-payload='" + fb_model + "'>\U0001f4c8 Update model with latest data</button>"
        + '</div>'
        + '<div class="prow" style="margin-top:6px"><input type="text" class="ai-input" '
        + 'placeholder="Edit with AI \u2014 e.g. refresh with the post-warning numbers, exec '
        + 'summary in French"></div>'
        + '<div class="prow">'
        + '<button class="btn primary" id="ai-sel" data-unique-action="sendPrompt" '
        + "data-unique-payload='" + fb_ai + "'>\u2728 Edit with AI</button></div>")
    return (f'<div class="card" id="prodcard" data-tk="{e(tk)}" data-name="{e(name)}">'
            '<h2>Research products <span class="mut">· pre-generated overnight · tick the '
            'documents, then regenerate, submit for control or edit with AI</span></h2>'
            + "".join(rows) + controls +
            '<p class="mut" style="margin:10px 0 0;font-size:11px">Exane house format · '
            'SYNTHETIC data · drafts for the analyst — route through pre-publication '
            'control before any distribution.</p></div>' + _PRODUCTS_SCRIPT + _EDIT_AI_SCRIPT)


def build_review(tk: str, names: list[tuple]) -> str:
    c = next(x for x in seed.current_coverage() if x["ticker"] == tk)
    d = seed.current_dossiers()[tk]
    ov = _current_overnight().get(tk)
    est = seed.OUR_ESTIMATES.get(tk)
    cons = seed.CONSENSUS.get(tk)

    # header + tiles
    tp = ov["new_target_price"] if (ov and ov.get("new_target_price")) else c["target_price"]
    up = ov.get("new_upside_pct") if (ov and ov.get("new_upside_pct") is not None) else c["upside_pct"]
    tp_note = "revised overnight" if (ov and ov.get("new_target_price")) else "house target"
    tiles = "".join([
        _tile("Rating", f'<span class="rate {e(c["rating"])}">{e(c["rating"])}</span>'),
        _tile("Target price", _fmt_ccy(tp, c["ccy"]), f'upside {up:+.1f}% · {tp_note}'),
        _tile("Last price", _fmt_ccy(c["price"], c["ccy"]), f'pre-mkt {c["premarket_pct"]:+.1f}%'),
        _tile("Next catalyst", e(c["next_catalyst"]), e(c.get("reporting", ""))),
    ])


    # clickable status — coherence affordance: the pill shows its backing items
    status_prompt = ('What is behind the status "' + c["status"] + '" for ' + c["name"] +
                     ' (' + tk + ')? Show the backing items — note drafts, control-queue '
                     'entries, open reviews — from get_dossier and get_control_queue, '
                     'with what is still pending.')
    status_btn = ('<button class="statbtn" title="Show the items behind this status" '
                  "data-unique-action=\"sendPrompt\" data-unique-payload='" +
                  _json.dumps({"prompt": status_prompt}).replace("'", "&#39;") +
                  "'>" + e(c["status"]) + '</button>')

    # investment thesis — bullets, editable with AI (update_thesis)
    th_bullets = "".join(f"<li>{e(b.strip())}</li>"
                         for b in d["thesis"].split(";") if b.strip())
    th_prompt = ('Apply this instruction to the INVESTMENT THESIS of ' + c["name"] +
                 ' (' + tk + '): "__INSTR__". Current thesis: "' + d["thesis"] + '". '
                 'Produce the revised thesis as short semicolon-separated bullets and '
                 'store it with update_thesis(ticker, thesis); confirm what changed and '
                 'remind me the dashboard bakes it at the next regeneration.')
    thesis_card = ('<div class="card" data-ai-card><h2>Investment thesis '
                   '<span class="mut">· editable — the agent stores it via update_thesis'
                   '</span></h2><ul class="thl">' + th_bullets + '</ul>'
                   + _edit_rows('Edit with AI — e.g. add a bullet on China entry-price risk',
                                th_prompt) + '</div>')

    # overnight banner
    ov_html = ""
    if ov:
        label, klass = SEV[ov["severity"]]
        newtp = (f' · target {_fmt_ccy(ov["new_target_price"], c["ccy"])}'
                 if ov.get("new_target_price") else "")
        act = (f'<div class="acts" style="margin-top:10px"><button class="btn primary" '
               f"data-unique-action=\"sendPrompt\" data-unique-payload='{{\"prompt\":"
               f"\"{e(ov['suggested_action'])} for {c['name']} ({tk}) — use the {ov['suggested_skill']} skill.\"}}'>"
               f'{e(ov["suggested_action"])}</button></div>')
        ov_html = (f'<div class="ov {klass}"><div class="tag">Overnight · {e(label)}{e(newtp)}</div>'
                   f'<div class="h">{e(ov["headline"])}</div>'
                   f'<div class="imp">{e(ov["valuation_impact"])}</div>{act}</div>')

    # live coverage tape — the PROVEN unfiltered get_live_quotes call (the
    # per-ticker arg trips stale connector registries); this page's name is
    # highlighted via baked CSS on data-tk.
    quote = (
        '<div class="card qwrap"><h2>Live quotes <span class="mut">· Yahoo Finance '
        'via FA Research MCP · 24-month sparkline · red = 12m target · 5-min '
        'refresh</span></h2>'
        '<div class="quote qtape" data-unique-list="q" '
        'data-unique-source-server="Demo - CIB - Sell-Side Equity Analyst" '
        'data-unique-source-tool="get_live_quotes" '
        'data-unique-source-args="{}" '
        'data-unique-source-path="rows" data-unique-source-poll="300000">'
        '<template data-unique-item>'
        '<span class="qrow" data-unique-key="ticker" data-unique-attr-data-tk="ticker">'
        '<span class="qt" data-unique-field="name"></span>'
        '<img class="spark" alt="24m" data-unique-attr-src="spark_uri" '
        'data-unique-attr-title="spark_title">'
        '<span class="qp" data-unique-field="price_label"></span>'
        '<span class="qc" data-unique-attr-data-chg="chg_label" data-unique-field="chg_label"></span>'
        '<span class="qc" data-unique-attr-data-chg="chg_label">%</span>'
        '<span class="qsrc"><span data-unique-field="tp_label"></span> target · '
        '<span data-unique-field="tp_vs_price_label"></span></span>'
        '</span>'
        '</template>'
        '<span class="state" data-unique-state="loading"><span class="spin"></span> live quotes…</span>'
        '<span class="state" data-unique-state="error">live quotes unavailable — check the '
        'Demo - CIB - Sell-Side Equity Analyst connector</span>'
        '</div></div>'
    )

    # detailed 2-year weekly chart for THIS name — same proven unfiltered call;
    # every row carries the chart image, baked CSS displays only this page's
    # ticker (the per-ticker arg trips stale connector registries).
    chart = (
        '<div class="card"><h2>Price vs target — 2 years <span class="mut">· weekly '
        'closes · Yahoo Finance via FA Research MCP · red = 12m target · dot = last '
        'close · 5-min refresh</span></h2>'
        '<div class="chwrap" data-unique-list="ch" '
        'data-unique-source-server="Demo - CIB - Sell-Side Equity Analyst" '
        'data-unique-source-tool="get_live_quotes" '
        'data-unique-source-args="{}" '
        'data-unique-source-path="rows" data-unique-source-poll="300000">'
        '<template data-unique-item>'
        '<div class="crow" data-unique-key="ticker" data-unique-attr-data-tk="ticker">'
        '<img class="bigchart" alt="2y weekly price chart" '
        'data-unique-attr-src="chart_uri" data-unique-attr-title="chart_title">'
        '</div>'
        '</template>'
        '<span class="state" data-unique-state="loading"><span class="spin"></span> '
        'loading the price chart…</span>'
        '<span class="state" data-unique-state="error">price chart unavailable — check '
        'the Demo - CIB - Sell-Side Equity Analyst connector</span>'
        '</div></div>'
    )

    # estimates table
    est_html = ""
    if est:
        # pre-release: Ours / Consensus.  post-release: Ours / Consensus / Company (published).
        post = any("company" in r for r in est["rows"])
        head = ('<th>Metric</th><th class="num">Ours</th><th class="num">Consensus</th>'
                + ('<th class="num">Company (published)</th>' if post else '')
                + '<th class="num">Δ ours vs cons.</th>')
        rows = "".join(
            f'<tr><td>{e(r["metric"])}</td><td class="num">{e(r["ours"])}</td>'
            f'<td class="num">{e(r["consensus"])}</td>'
            + (f'<td class="num"><b>{e(r.get("company", "—"))}</b></td>' if post else '')
            + f'<td class="num">{e(r["delta"])}</td></tr>'
            for r in est["rows"])
        title = ("Ours / Consensus / Company — post-view" if post
                 else "Our estimates vs consensus — preview")
        est_html = (f'<div class="card"><h2>{title} <span class="mut">· {e(est["period"])}</span></h2>'
                    f'<table class="est"><thead><tr>{head}</tr></thead>'
                    f'<tbody>{rows}</tbody></table>'
                    f'<p class="mut" style="margin:10px 0 0;font-size:12.5px">{e(est["stance"])}</p></div>')

    cons_html = ""
    if cons:
        rt = cons["ratings"]
        cons_html = (f'<div class="card"><h2>Sell-side consensus <span class="mut">· {e(cons["as_of"])} · '
                     f'{cons["analysts"]} analysts</span></h2>'
                     f'<p style="margin:0 0 6px">EPS mean <b>{cons["eps_mean"]}</b> '
                     f'(range {cons["eps_low"]}–{cons["eps_high"]}) · mean target {_fmt_ccy(cons["tp_mean"], c["ccy"])} · '
                     f'{rt["buy"]} buy / {rt["hold"]} hold / {rt["sell"]} sell</p>'
                     f'<p class="mut" style="margin:0;font-size:12.5px">{e(cons["note"])}</p></div>')

    def act(label, prompt, primary=False):
        cls = "btn primary" if primary else "btn"
        return (f'<button class="{cls}" data-unique-action="sendPrompt" '
                f"data-unique-payload='{{\"prompt\":\"{e(prompt)}\"}}'>{e(label)}</button>")

    # scenario analysis — the buy-side / roadshow what-if material with our hypotheses
    sc = seed.current_scenarios().get(tk)
    sc_html = ""
    if sc:
        sc_rows = "".join(
            f'<tr><td><b>{e(r["scenario"])}</b><br><span style="color:var(--mut);font-size:12px">'
            f'{e(r["assumption"])}</span></td>'
            f'<td class="num">{e(r["eps_impact"])}</td>'
            f'<td class="num">{e(r["tp_impact"])}</td>'
            f'<td class="num">{e(r.get("probability", ""))}</td>'
            f'<td style="color:var(--ink2);font-size:12.5px">{e(r["hypothesis"])}</td></tr>'
            for r in sc["rows"])
        lab_id = REVIEW_IDS.get("__scenario_lab__", "") if tk == "MC FP" else ""
        lab_btn = (f'<button class="btn primary" data-unique-action="openDocument" '
                   f"data-unique-payload='{{\"contentId\":\"{e(lab_id)}\"}}'>🧪 Open the "
                   f"Scenario Lab</button>") if lab_id else ""
        engine_btns = (
            '<div class="acts" style="margin-top:10px">'
            + lab_btn
            + act("Compute: EUR +5% FX shock",
                  f"Use compute_scenario on {c['name']} ({tk}) with fx_eur_move_pct=5 and "
                  f"walk me through the cascade — revenue, EBIT, EPS by year, the "
                  f"target-price bridge and the assumption trail.")
            + act("Compute: China recovery Q2-26",
                  f"Use compute_scenario on {c['name']} ({tk}) with china_recovery=q2_26 "
                  f"and walk me through the cascade and the TP bridge.")
            + act("Custom scenario…",
                  f"I want a custom what-if on {c['name']} ({tk}). Ask me for the FX move, "
                  f"China timing and (if LVMH) destocking end, then run compute_scenario "
                  f"and explain every number.")
            + "</div>")
        sc_html = (f'<div class="card" data-ai-card><h2>Scenario analysis — our hypotheses '
                   f'<span class="mut">· {e(sc["period"])} · base {e(sc["base_tp"])}</span></h2>'
                   '<table class="est"><thead><tr><th>Scenario / assumption</th>'
                   '<th class="num">EPS</th><th class="num">Target price</th>'
                   '<th class="num">Prob.</th><th>Our hypothesis</th></tr></thead>'
                   f'<tbody>{sc_rows}</tbody></table>'
                   f'<p class="mut" style="margin:10px 0 0;font-size:12.5px">{e(sc["note"])} '
                   f'Any other shock: the scenario engine computes it live.</p>'
                   + f'{engine_btns}'
                   + _edit_rows('Edit with AI — e.g. raise the China-recovery probability to 25%',
                                'Apply this instruction to the SCENARIO HYPOTHESES of '
                                + c["name"] + ' (' + tk + '): "__INSTR__". Use '
                                'update_scenario_case (match by scenario title); if the '
                                'shock itself changes, RECOMPUTE eps/tp with '
                                'compute_scenario first — never invent numbers; keep '
                                'probabilities summing to 100%. Confirm the updated row.')
                   + '</div>')

    log = "".join(f"<li>{e(x)}</li>" for x in d["interaction_log"])
    notes = "".join(
        (lambda p: f'<li><span class="mut" style="font-size:11px">{e(p[0])}</span> · {e(p[2])}</li>'
         if len(p) == 3 else f"<li>{e(x)}</li>")(x.partition(" · "))
        for x in d["note_history"])

    actions = "".join([
        act("Run first-take", f"Run the results first-take for {c['name']} ({tk})."),
        act("Tone × guidance", f"Run tone × guidance analysis on {c['name']} ({tk})'s recent earnings calls."),
        act("Build / update model", f"Build or update the financial model for {c['name']} ({tk})."),
        act("Draft desknote", f"Draft an Exane desknote for {c['name']} ({tk})."),
        act("Open coverage dossier", f"Open the coverage dossier for {c['name']} ({tk})."),
    ])

    return f"""<!doctype html>
<meta charset="utf-8" />
<!-- Coverage review — {e(c['name'])} ({tk}). Unique-themed canvas for the FA demo.
     Live quote bound to the yahoo-finance connector; coverage data as of the 07:00
     overnight run (FA Research MCP). SYNTHETIC — DEMO USE ONLY. -->
<style>{CSS}</style>
<div class="rv">
  {_switch(tk, names)}
  <div class="hdr">
    <div><h1>{e(c['name'])} <span class="mut">· {tk}</span><span class="live-tag">Live</span></h1>
      <div class="sub">{e(c['sector'])} · {status_btn}</div></div>
    <span class="rate {e(c['rating'])}">{e(c['rating'])}</span>
  </div>
  {quote}
  {chart}
  <style>.rv .qrow[data-tk="{tk}"]{{background:var(--mint-wash);outline:1px solid var(--mint-dot);}}
  .rv .crow[data-tk="{tk}"]{{display:block;}}</style>
  <div class="tiles">{tiles}</div>
  {ov_html}
  {thesis_card}
  {_products(tk, c['name'])}
  {_fundamentals(tk)}
  {est_html}
  {cons_html}
  {sc_html}
  <div class="card"><h2>Interaction log</h2><ul class="log">{log}</ul></div>
  <div class="card"><h2>Note history</h2><ul class="log">{notes}</ul></div>
  <div class="card"><h2>Actions <span class="mut">· drafts for your review, nothing sent</span></h2>
    <div class="acts">{actions}</div></div>
  <div class="foot">SYNTHETIC — DEMO USE ONLY · coverage as of the 07:00 overnight run · live quotes via FA Research MCP (Yahoo Finance, timestamped)</div>
</div>
"""


def build_card(tk: str) -> str:
    c = next(x for x in seed.current_coverage() if x["ticker"] == tk)
    d = seed.current_dossiers()[tk]
    ov = _current_overnight().get(tk)
    est = seed.OUR_ESTIMATES.get(tk)
    lines = [
        f"# {c['name']} ({tk}) — coverage card",
        "",
        "> SYNTHETIC — DEMO USE ONLY. Coverage as of the 07:00 overnight run.",
        "",
        f"- **Sector:** {c['sector']}  |  **Rating:** {c['rating']}",
        f"- **Target price:** {c['target_price']:.0f} {c['ccy']} (upside {c['upside_pct']:+.1f}%)",
        f"- **Last price:** {c['price']:.0f} {c['ccy']} (pre-market {c['premarket_pct']:+.1f}%)",
        f"- **Next catalyst:** {c['next_catalyst']}",
        f"- **Status:** {c['status']}",
        "",
        "## Thesis", d["thesis"], "",
        "## Estimates", d["estimates"], "",
    ]
    if ov:
        lines += ["## Overnight move",
                  f"**{ov['headline']}** — {ov['detail']}", "",
                  f"*Valuation:* {ov['valuation_impact']}",
                  f"*Suggested:* {ov['suggested_action']} (skill: `{ov['suggested_skill']}`)", ""]
    if est:
        lines += [f"## Our estimates vs consensus ({est['period']})", "",
                  "| Metric | Ours | Consensus | Δ |", "|---|---|---|---|"]
        lines += [f"| {r['metric']} | {r['ours']} | {r['consensus']} | {r['delta']} |" for r in est["rows"]]
        lines += ["", f"_{est['stance']}_", ""]
    fin = chart_pack.get_financials(tk)
    if fin:
        kf = fin["key_financials"]
        lines += ["## Key financials (FY2023-28e, synthetic)", "",
                  "| " + " | ".join(h or "Metric" for h in kf["header"]) + " |",
                  "|" + "---|" * len(kf["header"])]
        lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in kf["rows"]]
        lines += ["", f"_{kf['source']}_", ""]
    lines += ["## Interaction log"] + [f"- {x}" for x in d["interaction_log"]] + [""]
    lines += ["## Note history"] + [f"- {x}" for x in d["note_history"]] + [""]
    return "\n".join(lines)




_IMPACT_CSS = """
  .oi{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
      max-width:900px;margin:0 auto;padding:20px;color:#171717;font-size:13.5px;line-height:1.5;}
  .oi h1{font-size:19px;margin:0 0 2px;}
  .oi .sub{color:#6E7572;font-size:12px;margin-bottom:16px;}
  .oi .ev{background:#fff;border:1px solid #E7E8E7;border-left:3px solid #6E7572;border-radius:12px;
          padding:14px 16px;margin-bottom:12px;}
  .oi .ev.sev-alert{border-left-color:#B42318;} .oi .ev.sev-positive{border-left-color:#2E8B57;}
  .oi .ev.sev-watch{border-left-color:#B9770E;}
  .oi .chip{font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
            border:1px solid #E7E8E7;border-radius:999px;padding:2px 8px;color:#6E7572;margin-right:8px;}
  .oi .nm{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.03em;}
  .oi .hd{font-weight:700;margin:6px 0 3px;font-size:14px;}
  .oi table{border-collapse:collapse;margin:10px 0 4px;font-variant-numeric:tabular-nums;}
  .oi th{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#fff;background:#14354A;
         padding:5px 12px;text-align:left;}
  .oi td{border-bottom:1px solid #E7E8E7;padding:5px 12px;font-size:12.5px;}
  .oi td.old{color:#008000;} .oi td.new{font-weight:700;}
  .oi .dt{color:#404040;font-size:12.5px;}
  .oi .st{font-size:11.5px;color:#6E7572;font-style:italic;margin-top:6px;}
  .oi .acts{display:flex;gap:8px;flex-wrap:wrap;margin-top:9px;}
  .oi .btn{font:inherit;font-size:11.5px;font-weight:600;cursor:pointer;border-radius:8px;
           padding:6px 10px;border:1px solid #E7E8E7;background:#fff;}
  .oi .foot{color:#6E7572;font-size:11px;margin-top:14px;}
"""


def _impact_page(env: str, review_ids: dict, note_ids: dict, stamp: str) -> str:
    """overnight-impact.html — one card per overnight event: the impacted equity,
    what happened, and the diff table (PREVIOUS values kept next to NEW), with
    links to the final documents (review · post-view · updated Excel model)."""
    cards = []
    for ev in impact.events():
        rows = ""
        if ev["rows"]:
            rows = ("<table><tr><th>Metric</th><th>Previous</th><th>New</th><th>Δ</th></tr>"
                    + "".join(f'<tr><td>{e(r["metric"])}</td><td class="old">{e(r["old"])}</td>'
                              f'<td class="new">{e(r["new"])}</td><td>{e(r["delta"])}</td></tr>'
                              for r in ev["rows"]) + "</table>")
        btns = []
        nid = note_ids.get(ev["key"], {})
        for label, cid in (("Open the review", review_ids.get(ev["key"])),
                           ("Post-view note (PDF)", nid.get("postview")),
                           ("Excel model (updated)", nid.get("model"))):
            if cid:
                btns.append('<button class="btn" data-unique-action="openDocument" '
                            "data-unique-payload='" + _json.dumps({"contentId": cid}) + "'>"
                            + label + "</button>")
        cards.append(
            f'<div class="ev sev-{e(ev["severity"])}">'
            f'<span class="chip">{e(ev["severity_label"])}</span>'
            f'<span class="nm">{e(ev["name_label"])}</span>'
            f'<div class="hd">{e(ev["headline"])}</div>'
            f'<div class="dt">{e(ev["valuation_impact"])}</div>'
            f'{rows}<div class="st">{e(ev["status"])}</div>'
            + (f'<div class="acts">{"".join(btns)}</div>' if btns else "")
            + "</div>")
    return (f'<!doctype html>\n<!-- fa-nightly: {stamp} env={env} -->\n'
            f'<meta charset="utf-8"><style>{_IMPACT_CSS}</style><div class="oi">'
            f'<h1>Overnight impact report</h1>'
            f'<div class="sub">What changed per event — previous values vs new · generated by '
            f'the overnight run · SYNTHETIC demo data · env {e(env)}</div>'
            + "".join(cards) +
            '<div class="foot">Every diff is reproducible: the models keep both value sets '
            '(LVMH: Assumptions!B5 switch); estimate changes via get_note_pack forecast '
            'changes.</div></div>')


def build_all(env: str, review_ids: dict, note_ids: dict, stamp: str) -> dict[str, str]:
    """All six reviews + cards for one environment. Returns {kb_relpath: text}."""
    global REVIEW_IDS, NOTE_IDS, _FA_ENV, _STAMP
    REVIEW_IDS, NOTE_IDS, _FA_ENV, _STAMP = review_ids, note_ids, env, stamp
    names = [(c["ticker"], c["name"]) for c in seed.current_coverage()]
    out: dict[str, str] = {}
    for tk, _ in names:
        html_text = build_review(tk, names)
        if stamp:
            html_text = html_text.replace("<!doctype html>",
                                          f"<!doctype html>\n<!-- fa-nightly: {stamp} env={env} -->", 1)
        out[f"names/{tk}/review.html"] = html_text
        out[f"names/{tk}/coverage-card.md"] = build_card(tk)
    out["overnight-impact.html"] = _impact_page(env, review_ids, note_ids, stamp)
    return out
