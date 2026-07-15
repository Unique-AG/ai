#!/usr/bin/env python3
"""Inspector for Unique Benchmark Studio runs.

Benchmark Studio does not compute aggregate metrics itself, and the judge grade
is not in `export.csv` unless a terminal block maps it. The grade lives in each
row's `evaluation[<judge_block_id>].grade`, served by the `/rows` API. This
script pulls all completed runs, groups them by benchmark + dataset (one
*arm* per assistant, mirroring the search-engine arms in `inspect_bench.py`),
and writes a single self-contained `unique_benchmark_inspect.html`:

  - a benchmark/dataset dropdown and optional category slice,
  - a per-arm summary table (accuracy ±CI, correct/incorrect/not-attempted,
    errors, mean latency, mean cost) plus paired win/loss vs the first arm,
  - a filterable per-item drill-down showing each arm's answer and grade
    side by side.

Pure stdlib; needs only a running Studio backend (default http://localhost:8000).

    python unique_benchmark_result_analysis.py            # write the inspector
    python unique_benchmark_result_analysis.py --open     # write and open it
    python unique_benchmark_result_analysis.py --api http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import math
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

DEFAULT_API = "http://localhost:8000"
OUT_PATH = Path(__file__).parent / "unique_benchmark_inspect.html"

# Friendly labels for assistant ids. Extend as new assistants are benchmarked;
# ids not listed fall back to the raw assistant id.
ASSISTANT_NAMES = {
    "assistant_hxr4ppuva5qc4fs1pows4slp": "General GPT-5.4 + Brave + Crawl4AI",
    "assistant_lzn8i2dfdx3lqczejfc4meyc": "General GPT-5.4 + Google + Crawl4AI",
}

GRADES = ("CORRECT", "INCORRECT", "NOT_ATTEMPTED")


def _get(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.URLError as err:
        raise SystemExit(
            f"Could not reach Benchmark Studio at {url}\n"
            f"  ({err}). Is the backend running? `make dev-backend` in unique_benchmarking."
        )


def arm_id(row_assistant_id: str | None) -> str:
    """`graph[1]:assistant_xxx` -> `assistant_xxx`; `graph` -> `graph`."""
    if not row_assistant_id:
        return "graph"
    return row_assistant_id.rsplit(":", 1)[-1]


def arm_label(aid: str) -> str:
    return ASSISTANT_NAMES.get(aid, aid)


def grade_of(row: dict) -> str | None:
    evaluation = row.get("evaluation") or {}
    grades = [(v or {}).get("grade") for v in evaluation.values()]
    grades = [g for g in grades if g]
    return grades[0] if len(grades) == 1 else (json.dumps(grades) if grades else None)


def answer_text(row: dict) -> str | None:
    """The assistant's answer: the block output carrying `response.text`."""
    for block in (row.get("block_outputs") or {}).values():
        output = (block or {}).get("output")
        if isinstance(output, dict):
            response = output.get("response")
            if isinstance(response, dict) and response.get("text"):
                return response["text"]
    return None


def group_key(run: dict) -> tuple:
    return (
        run.get("benchmark_name"),
        run.get("benchmark_version_number"),
        run.get("dataset_name"),
        run.get("dataset_version_number"),
    )


def group_label(run: dict) -> str:
    bench = run.get("benchmark_name")
    ds = run.get("dataset_name")
    return f"{bench} · {ds}"


# --- metrics -----------------------------------------------------------------
def arm_stats(aid: str, items: list[dict]) -> dict:
    rows = [it["byArm"][aid] for it in items if aid in it["byArm"]]
    graded = [r for r in rows if r["grade"] in GRADES]
    n = len(graded)
    correct = sum(r["grade"] == "CORRECT" for r in graded)
    incorrect = sum(r["grade"] == "INCORRECT" for r in graded)
    not_attempted = sum(r["grade"] == "NOT_ATTEMPTED" for r in graded)
    errored = sum(r["status"] != "completed" for r in rows)
    latencies = [r["latency_ms"] for r in rows if r.get("latency_ms") is not None]
    costs = [r["cost_usd"] for r in rows if r.get("cost_usd") is not None]
    accuracy = correct / n if n else 0.0
    return {
        "arm": aid,
        "label": arm_label(aid),
        "n": n,
        "correct": correct,
        "incorrect": incorrect,
        "notAttempted": not_attempted,
        "errored": errored,
        "accuracy": accuracy,
        "ci": 1.96 * math.sqrt(accuracy * (1 - accuracy) / n) if n else 0.0,
        "meanLatencyMs": round(sum(latencies) / len(latencies)) if latencies else None,
        "meanCostUsd": round(sum(costs) / len(costs), 4) if costs else None,
    }


def pair_stats(arms: list[str], items: list[dict]) -> list[dict]:
    if len(arms) < 2:
        return []
    baseline = arms[0]
    out = []
    for aid in arms[1:]:
        shared = [
            it
            for it in items
            if baseline in it["byArm"]
            and aid in it["byArm"]
            and it["byArm"][baseline]["grade"] in GRADES
            and it["byArm"][aid]["grade"] in GRADES
        ]
        base_c = [it["byArm"][baseline]["grade"] == "CORRECT" for it in shared]
        arm_c = [it["byArm"][aid]["grade"] == "CORRECT" for it in shared]
        out.append(
            {
                "arm": aid,
                "label": arm_label(aid),
                "baseline": baseline,
                "baselineLabel": arm_label(baseline),
                "armOnly": sum(a and not b for a, b in zip(arm_c, base_c)),
                "baseOnly": sum(b and not a for a, b in zip(arm_c, base_c)),
                "shared": len(shared),
            }
        )
    return out


# --- payload -----------------------------------------------------------------
def build_payload(api: str) -> dict:
    runs = _get(f"{api}/api/v2/runs?limit=100")["items"]
    completed = [r for r in runs if r.get("status") == "completed"]
    # newest first so the latest run wins when an arm was re-run
    completed.sort(key=lambda r: r.get("created_at") or "", reverse=True)

    groups: dict[tuple, dict] = {}
    for run in completed:
        key = group_key(run)
        grp = groups.setdefault(
            key,
            {"label": group_label(run), "arms_seen": {}, "rows_by_arm": {}, "created": run.get("created_at")},
        )
        rows = _get(f'{api}/api/v2/runs/{run["id"]}/rows?limit=10000')["items"]
        for row in rows:
            aid = arm_id(row.get("assistant_id"))
            # completed is newest-first, so the first run to claim an arm wins;
            # rows from any older run for the same arm are skipped.
            winning_run = grp["arms_seen"].setdefault(aid, run["id"])
            if winning_run != run["id"]:
                continue
            grp["rows_by_arm"].setdefault(aid, []).append(row)

    out_groups = []
    for key, grp in groups.items():
        arms = list(grp["rows_by_arm"].keys())
        # merge rows across arms into per-item records keyed by item id
        items_by_id: dict[str, dict] = {}
        for aid, rows in grp["rows_by_arm"].items():
            for row in rows:
                curated = row.get("curated_output") or {}
                item_id = (
                    curated.get("item_id")
                    or curated.get("question")
                    or f'row{row.get("dataset_row_index")}'
                )
                item = items_by_id.setdefault(
                    item_id,
                    {
                        "id": item_id,
                        "q": curated.get("question") or "",
                        "gold": curated.get("gold_answer") or curated.get("expected_answer") or "",
                        "cat": curated.get("category"),
                        "byArm": {},
                    },
                )
                item["byArm"][aid] = {
                    "grade": grade_of(row),
                    "answer": answer_text(row),
                    "status": row.get("status"),
                    "error": row.get("error"),
                    "latency_ms": row.get("latency_ms"),
                    "cost_usd": row.get("cost_usd"),
                }
        items = sorted(items_by_id.values(), key=lambda it: it["id"])

        categories = sorted({it["cat"] for it in items if it.get("cat")})
        ids_all = items
        slices = {"all": ids_all}
        for cat in categories:
            slices[cat] = [it for it in items if it.get("cat") == cat]
        summaries = {sk: [arm_stats(aid, subset) for aid in arms] for sk, subset in slices.items()}
        pairs = {sk: pair_stats(arms, subset) for sk, subset in slices.items()}

        out_groups.append(
            {
                "key": " · ".join(str(k) for k in key),
                "label": grp["label"],
                "arms": [{"id": aid, "label": arm_label(aid)} for aid in arms],
                "categories": categories,
                "summaries": summaries,
                "pairs": pairs,
                "items": items,
            }
        )

    out_groups.sort(key=lambda g: g["label"])
    return {"groups": out_groups}


def print_summary(payload: dict) -> None:
    for grp in payload["groups"]:
        print(f'\n=== {grp["label"]} ===')
        for s in grp["summaries"]["all"]:
            print(
                f'  {s["label"][:44]:46} n={s["n"]:<4} '
                f'acc={s["accuracy"]:.3f} ±{s["ci"]:.3f}  '
                f'C/I/NA={s["correct"]}/{s["incorrect"]}/{s["notAttempted"]}  err={s["errored"]}'
            )
        for p in grp["pairs"]["all"]:
            print(
                f'  paired vs {p["baselineLabel"]}: {p["label"]} '
                f'wins {p["armOnly"]}, loses {p["baseOnly"]} (of {p["shared"]} shared)'
            )


# --- render ------------------------------------------------------------------
TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Unique Benchmark Studio — inspector</title>
<style>
  :root { color-scheme: light; }
  body { font: 14px/1.45 -apple-system, "Segoe UI", sans-serif; margin: 0;
         color: #1f2328; background: #f6f8fa; }
  header { background: #fff; border-bottom: 1px solid #d1d9e0; padding: 14px 22px; }
  h1 { font-size: 17px; margin: 0 0 10px; }
  main { padding: 16px 22px; max-width: 1500px; margin: 0 auto; }
  table.summary { border-collapse: collapse; background: #fff; }
  table.summary th, table.summary td { border: 1px solid #d1d9e0;
    padding: 5px 10px; text-align: right; }
  table.summary th:first-child, table.summary td:first-child { text-align: left; }
  table.summary th { background: #f6f8fa; font-weight: 600; }
  .pairs { margin: 8px 0 0; color: #57606a; font-size: 13px; }
  .controls { display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
              margin: 0 0 10px; }
  header .controls { margin-bottom: 12px; }
  main .controls { margin-top: 18px; }
  .controls label { font-size: 12px; color: #57606a; display: block; }
  .controls select, .controls input { font: inherit; padding: 3px 6px;
    border: 1px solid #d1d9e0; border-radius: 6px; background: #fff; }
  .controls input { width: 260px; }
  #count { color: #57606a; font-size: 13px; }
  .empty { color: #57606a; padding: 40px; text-align: center; }
  .item { background: #fff; border: 1px solid #d1d9e0; border-radius: 8px;
          margin-bottom: 8px; }
  .item-head { display: flex; gap: 10px; align-items: center; padding: 8px 12px;
               cursor: pointer; }
  .item-head:hover { background: #f6f8fa; }
  .item-head .q { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden;
                  text-overflow: ellipsis; }
  .item-head .id { color: #8b949e; font-size: 12px; }
  .badge { font-size: 11px; font-weight: 600; padding: 1px 7px;
           border-radius: 10px; white-space: nowrap; }
  .g-CORRECT { background: #dafbe1; color: #116329; }
  .g-INCORRECT { background: #ffebe9; color: #cf222e; }
  .g-NOT_ATTEMPTED { background: #eaeef2; color: #57606a; }
  .g-none { background: #fff8c5; color: #7d4e00; }
  .detail { border-top: 1px solid #d1d9e0; padding: 12px; display: grid;
            grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 12px; }
  .gold { grid-column: 1 / -1; padding: 6px 10px; background: #fff8c5;
          border-radius: 6px; }
  .arm-col h3 { font-size: 13px; margin: 0 0 6px; display: flex; gap: 8px;
                align-items: center; flex-wrap: wrap; }
  .answer { padding: 6px 8px; background: #f6f8fa; border-radius: 6px;
            white-space: pre-wrap; }
  .err { color: #cf222e; font-size: 12px; }
  .meta { color: #8b949e; font-size: 12px; }
</style>
</head>
<body>
<header><h1>Unique Benchmark Studio — inspector</h1>
  <div class="controls" id="viewbar"></div>
  <table class="summary" id="summary"></table>
  <div class="pairs" id="pairs"></div>
</header>
<main>
  <div class="controls" id="controls"><span id="count"></span></div>
  <div id="list"></div>
</main>
<script>
const DATA = __DATA__;
const esc = s => (s ?? "").replace(/[&<>"']/g,
  c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const badge = g => `<span class="badge g-${g ?? "none"}">${g ?? "missing"}</span>`;
const fmtPct = x => (100 * x).toFixed(1) + "%";

let grpIndex = 0;
let category = "all";
let filters = {};
const grp = () => DATA.groups[grpIndex];

function addSelect(parent, labelText, options, onChange) {
  const wrap = document.createElement("span");
  wrap.innerHTML = `<label>${esc(labelText)}</label>`;
  const sel = document.createElement("select");
  for (const opt of options) sel.add(new Option(opt.label, opt.value));
  sel.onchange = () => onChange(sel.value);
  wrap.appendChild(sel);
  parent.appendChild(wrap);
  return wrap;
}

const viewbar = document.getElementById("viewbar");
if (!DATA.groups.length) {
  document.body.innerHTML =
    '<div class="empty">No completed runs found. Run a benchmark in Studio, then re-run this.</div>';
} else {
  addSelect(viewbar, "benchmark · dataset", DATA.groups.map((g, i) =>
    ({label: g.label, value: i})), v => {
      grpIndex = +v; category = "all"; rebuildControls(); renderAll(); });
  const catWrap = addSelect(viewbar, "subset", [{label: "all", value: "all"}],
    v => { category = v; renderAll(); });
  const catSel = catWrap.querySelector("select");

  const controls = document.getElementById("controls");

  function rebuildControls() {
    // category slice
    catSel.innerHTML = "";
    for (const opt of ["all", ...grp().categories]) catSel.add(new Option(opt, opt));
    catWrap.style.display = grp().categories.length ? "" : "none";
    // one grade filter per arm (arms differ per group)
    controls.innerHTML = "";
    filters = {};
    for (const arm of grp().arms) {
      filters[arm.id] = "any";
      addSelect(controls, arm.label,
        ["any", "CORRECT", "INCORRECT", "NOT_ATTEMPTED", "missing"].map(o =>
          ({label: o, value: o})), v => { filters[arm.id] = v; render(); });
    }
    const searchWrap = document.createElement("span");
    searchWrap.innerHTML = "<label>search question / answer / gold</label>";
    const search = document.createElement("input");
    search.id = "search";
    search.oninput = () => render();
    searchWrap.appendChild(search);
    controls.appendChild(searchWrap);
    const count = document.createElement("span");
    count.id = "count";
    controls.appendChild(count);
  }

  function renderSummary() {
    const rows = grp().summaries[category] ?? [];
    document.getElementById("summary").innerHTML =
      "<tr><th>assistant (arm)</th><th>n</th><th>correct</th><th>incorrect</th>" +
      "<th>not_attempted</th><th>errors</th><th>accuracy</th>" +
      "<th>mean latency</th><th>mean cost</th></tr>" +
      rows.map(s => `<tr><td>${esc(s.label)}</td><td>${s.n}</td>
        <td>${s.correct}</td><td>${s.incorrect}</td><td>${s.notAttempted}</td>
        <td>${s.errored}</td>
        <td><b>${fmtPct(s.accuracy)}</b> ±${(100 * s.ci).toFixed(1)}pp</td>
        <td>${s.meanLatencyMs != null ? (s.meanLatencyMs / 1000).toFixed(1) + "s" : "—"}</td>
        <td>${s.meanCostUsd != null ? "$" + s.meanCostUsd.toFixed(4) : "—"}</td></tr>`
      ).join("");
    document.getElementById("pairs").innerHTML =
      (grp().pairs[category] ?? []).map(p =>
        `paired vs <b>${esc(p.baselineLabel)}</b>: <b>${esc(p.label)}</b> wins ${p.armOnly}, ` +
        `loses ${p.baseOnly} (of ${p.shared} shared)`).join(" · ");
  }

  function matches(item) {
    for (const arm of grp().arms) {
      const want = filters[arm.id];
      if (want === "any") continue;
      const grade = item.byArm[arm.id]?.grade ?? "missing";
      if (grade !== want) return false;
    }
    const needle = (document.getElementById("search")?.value ?? "").toLowerCase();
    if (!needle) return true;
    const hay = [item.q, item.gold, item.cat ?? "",
      ...grp().arms.map(a => item.byArm[a.id]?.answer ?? "")].join(" ").toLowerCase();
    return hay.includes(needle);
  }

  function detailHtml(item) {
    const cols = grp().arms.map(arm => {
      const d = item.byArm[arm.id] ?? {};
      const meta = [
        d.latency_ms != null ? `${(d.latency_ms / 1000).toFixed(1)}s` : null,
        d.cost_usd != null ? `$${(+d.cost_usd).toFixed(4)}` : null,
      ].filter(Boolean).join(" · ");
      return `<div class="arm-col"><h3>${esc(arm.label)} ${badge(d.grade)}
        ${meta ? `<span class="meta">${meta}</span>` : ""}</h3>
        ${d.error ? `<div class="err">${esc(d.error)}</div>` : ""}
        ${d.answer != null
          ? `<div class="answer">${esc(d.answer)}</div>`
          : `<div class="meta">no answer recorded</div>`}</div>`;
    }).join("");
    const cat = item.cat ? ` · <span class="id">${esc(item.cat)}</span>` : "";
    return `<div class="gold">gold: <b>${esc(item.gold)}</b>${cat}</div>${cols}`;
  }

  function render() {
    const list = document.getElementById("list");
    list.innerHTML = "";
    const visible = grp().items.filter(matches);
    document.getElementById("count").textContent =
      `${visible.length} / ${grp().items.length} items`;
    for (const item of visible) {
      const div = document.createElement("div");
      div.className = "item";
      div.innerHTML = `<div class="item-head"><span class="id">${esc(item.id)}</span>
        <span class="q">${esc(item.q)}</span>
        ${grp().arms.map(a => badge(item.byArm[a.id]?.grade)).join(" ")}</div>`;
      div.querySelector(".item-head").onclick = () => {
        const open = div.querySelector(".detail");
        if (open) { open.remove(); return; }
        const detail = document.createElement("div");
        detail.className = "detail";
        detail.innerHTML = detailHtml(item);
        div.appendChild(detail);
      };
      list.appendChild(div);
    }
  }

  function renderAll() { renderSummary(); render(); }
  rebuildControls();
  renderAll();
}
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default=DEFAULT_API, help=f"backend base URL (default {DEFAULT_API})")
    parser.add_argument("--open", action="store_true", help="open the HTML after writing")
    args = parser.parse_args()

    payload = build_payload(args.api)
    if not payload["groups"]:
        print("No completed runs found. Run a benchmark in Studio first.")
    print_summary(payload)

    OUT_PATH.write_text(
        TEMPLATE.replace("__DATA__", json.dumps(payload)), encoding="utf-8"
    )
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"\nwrote {OUT_PATH} ({size_kb:.0f} KB)")
    if args.open:
        webbrowser.open(OUT_PATH.as_uri())


if __name__ == "__main__":
    main()
