# %% [markdown]
# # Benchmark — results inspector
#
# Reads the results of all three stages and writes a single self-contained
# `results/inspect.html`: a per-arm summary table plus a filterable per-item
# drill-down showing each arm's SERP, answer, and grade side by side.
#
# Pure read — no proxy, no gateway. Re-run after any benchmark run:
#
#     uv run python inspect_bench.py

# %%
import html
import json
import math
from pathlib import Path
from statistics import mean

from answering import AnswererConfig, AnswerRecord, answers_path, search_engine_slug
from grading import GraderConfig, GradeRecord, grades_path
from serp_records import (
    BenchmarkConfig,
    EngineConfig,
    SerpRecord,
    latest_by_item,
    load_jsonl,
    results_path,
)

# %% Parameters — must match the runs being inspected
SEARCH_ENGINES: list[EngineConfig | None] = [
    EngineConfig(engine="google", fetch_size=10),
    EngineConfig(engine="brave", fetch_size=10),
    # EngineConfig(engine="brave", fetch_size=10, params={"extra_snippets": False}),
    EngineConfig(engine="perplexity", fetch_size=10),
    None,  # no search — closed-book baseline
]
BENCHMARK_CONFIG = BenchmarkConfig(dataset="simpleqa", sample_n=300, seed=20260714)
ANSWERER_CONFIG = AnswererConfig(model="AZURE_GPT_41_2025_0414", top_k=10)
GRADER_CONFIG = GraderConfig(model="AZURE_GPT_41_2025_0414")
RESULTS_DIR = Path(__file__).parent / "results"
OUT_PATH = RESULTS_DIR / "inspect.html"

# %% Collect per-arm records
arms: list[str] = []
serps: dict[str, dict[str, SerpRecord]] = {}
answers: dict[str, dict[str, AnswerRecord]] = {}
grades: dict[str, dict[str, GradeRecord]] = {}
for engine in SEARCH_ENGINES:
    slug = search_engine_slug(engine)
    arms.append(slug)
    serps[slug] = (
        {}
        if engine is None
        else {
            r.item_id: r
            for r in latest_by_item(
                load_jsonl(
                    results_path(RESULTS_DIR, engine, BENCHMARK_CONFIG), SerpRecord
                )
            )
        }
    )
    answers[slug] = {
        r.item_id: r
        for r in latest_by_item(
            load_jsonl(
                answers_path(RESULTS_DIR, slug, BENCHMARK_CONFIG, ANSWERER_CONFIG),
                AnswerRecord,
            )
        )
    }
    grades[slug] = {
        r.item_id: r
        for r in latest_by_item(
            load_jsonl(
                grades_path(
                    RESULTS_DIR, slug, BENCHMARK_CONFIG, ANSWERER_CONFIG, GRADER_CONFIG
                ),
                GradeRecord,
            )
        )
    }

# %% Build payload
item_ids = sorted(
    {i for arm in arms for i in (answers[arm] | grades[arm] | serps[arm])}
)


def item_meta(item_id: str) -> tuple[str, str]:
    for arm in arms:
        rec = answers[arm].get(item_id) or serps[arm].get(item_id)
        if rec:
            return rec.question, rec.gold_answer
    return "?", "?"


items = []
for item_id in item_ids:
    question, gold = item_meta(item_id)
    row: dict = {"id": item_id, "q": question, "gold": gold, "arms": {}}
    for arm in arms:
        serp, answer, grade = (
            serps[arm].get(item_id),
            answers[arm].get(item_id),
            grades[arm].get(item_id),
        )
        error = (serp.error if serp else None) or (answer.error if answer else None)
        row["arms"][arm] = {
            "grade": grade.grade if grade and grade.error is None else None,
            "answer": answer.answer if answer else None,
            "error": error,
            "latency": serp.latency_s if serp else None,
            "answerLatency": answer.latency_s if answer else None,
            "results": [
                {"u": r.url, "t": html.unescape(r.title), "s": html.unescape(r.snippet)}
                for r in (serp.results if serp else [])
            ],
        }
    items.append(row)

summary = []
for arm in arms:
    graded = [g for g in grades[arm].values() if g.error is None]
    n = len(graded)
    correct = sum(g.grade == "CORRECT" for g in graded)
    answered = [a for a in answers[arm].values() if a.error is None]
    declined = sum(a.answer.lower().startswith("i don't know") for a in answered)
    serp_ok = [s for s in serps[arm].values() if s.error is None]
    evidence = [
        sum(len(r.snippet) + len(r.title) for r in s.results) for s in serp_ok
    ] or [0]
    summary.append(
        {
            "arm": arm,
            "n": n,
            "correct": correct,
            "incorrect": sum(g.grade == "INCORRECT" for g in graded),
            "notAttempted": sum(g.grade == "NOT_ATTEMPTED" for g in graded),
            "accuracy": correct / n if n else 0,
            "ci": 1.96 * math.sqrt(correct / n * (1 - correct / n) / n) if n else 0,
            "declined": declined,
            "searchMeanS": round(mean([s.latency_s for s in serp_ok]), 2)
            if serp_ok
            else None,
            "evidenceChars": round(mean(evidence)),
            "serpErrors": sum(s.error is not None for s in serps[arm].values()),
        }
    )

baseline = arms[0]
pairs = []
for arm in arms[1:]:
    shared = [
        i
        for i in item_ids
        if grades[baseline].get(i)
        and grades[baseline][i].error is None
        and grades[arm].get(i)
        and grades[arm][i].error is None
    ]
    base_c = {i: grades[baseline][i].grade == "CORRECT" for i in shared}
    arm_c = {i: grades[arm][i].grade == "CORRECT" for i in shared}
    pairs.append(
        {
            "arm": arm,
            "baseline": baseline,
            "armOnly": sum(arm_c[i] and not base_c[i] for i in shared),
            "baseOnly": sum(base_c[i] and not arm_c[i] for i in shared),
            "shared": len(shared),
        }
    )

payload = {"arms": arms, "summary": summary, "pairs": pairs, "items": items}

# %% Render
TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Web search benchmark — inspector</title>
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
              margin: 18px 0 10px; }
  .controls label { font-size: 12px; color: #57606a; display: block; }
  .controls select, .controls input { font: inherit; padding: 3px 6px;
    border: 1px solid #d1d9e0; border-radius: 6px; background: #fff; }
  .controls input { width: 260px; }
  #count { color: #57606a; font-size: 13px; }
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
            grid-template-columns: repeat(auto-fit, minmax(330px, 1fr)); gap: 12px; }
  .gold { grid-column: 1 / -1; padding: 6px 10px; background: #fff8c5;
          border-radius: 6px; }
  .arm-col h3 { font-size: 13px; margin: 0 0 6px; display: flex; gap: 8px;
                align-items: center; }
  .answer { padding: 6px 8px; background: #f6f8fa; border-radius: 6px;
            margin-bottom: 8px; }
  .err { color: #cf222e; font-size: 12px; }
  .res { border-top: 1px solid #eaeef2; padding: 6px 0; font-size: 13px; }
  .res .t { font-weight: 600; }
  .res a { color: #0969da; font-size: 12px; text-decoration: none;
           word-break: break-all; }
  .res .s { color: #424a53; margin-top: 2px; max-height: 130px; overflow-y: auto; }
  .res .s strong { background: #fff8c5; }
</style>
</head>
<body>
<header><h1>Web search benchmark — inspector</h1>
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
const snip = s => esc(s).replaceAll("&lt;strong&gt;", "<strong>")
                        .replaceAll("&lt;/strong&gt;", "</strong>");
const badge = g => `<span class="badge g-${g ?? "none"}">${g ?? "missing"}</span>`;

// summary table
const fmtPct = x => (100 * x).toFixed(1) + "%";
document.getElementById("summary").innerHTML =
  "<tr><th>arm</th><th>n</th><th>correct</th><th>incorrect</th>" +
  "<th>not_attempted</th><th>accuracy</th><th>declined</th>" +
  "<th>mean search time</th><th>evidence chars/q</th><th>serp errors</th></tr>" +
  DATA.summary.map(s => `<tr><td>${esc(s.arm)}</td><td>${s.n}</td>
    <td>${s.correct}</td><td>${s.incorrect}</td><td>${s.notAttempted}</td>
    <td><b>${fmtPct(s.accuracy)}</b> ±${(100 * s.ci).toFixed(1)}pp</td>
    <td>${s.declined}</td><td>${s.searchMeanS != null ? s.searchMeanS + "s" : "—"}</td>
    <td>${s.evidenceChars}</td><td>${s.serpErrors}</td></tr>`
  ).join("");
document.getElementById("pairs").innerHTML = DATA.pairs.map(p =>
  `paired vs <b>${esc(p.baseline)}</b>: <b>${esc(p.arm)}</b> wins ${p.armOnly}, ` +
  `loses ${p.baseOnly} (of ${p.shared} shared)`).join(" · ");

// controls: one grade filter per arm + text search
const controls = document.getElementById("controls");
const filters = {};
for (const arm of DATA.arms) {
  const wrap = document.createElement("span");
  wrap.innerHTML = `<label>${esc(arm)}</label>`;
  const sel = document.createElement("select");
  for (const opt of ["any", "CORRECT", "INCORRECT", "NOT_ATTEMPTED", "missing"])
    sel.add(new Option(opt, opt));
  sel.onchange = () => { filters[arm] = sel.value; render(); };
  filters[arm] = "any";
  wrap.appendChild(sel);
  controls.insertBefore(wrap, document.getElementById("count"));
}
const searchWrap = document.createElement("span");
searchWrap.innerHTML = "<label>search question / answer / gold</label>";
const search = document.createElement("input");
search.oninput = () => render();
searchWrap.appendChild(search);
controls.insertBefore(searchWrap, document.getElementById("count"));

function matches(item) {
  for (const arm of DATA.arms) {
    const want = filters[arm];
    if (want === "any") continue;
    const grade = item.arms[arm]?.grade ?? "missing";
    if (grade !== want) return false;
  }
  const needle = search.value.toLowerCase();
  if (!needle) return true;
  const hay = [item.q, item.gold,
    ...DATA.arms.map(a => item.arms[a]?.answer ?? "")].join(" ").toLowerCase();
  return hay.includes(needle);
}

function detailHtml(item) {
  const cols = DATA.arms.map(arm => {
    const d = item.arms[arm] ?? {};
    const results = (d.results ?? []).map((r, i) => `<div class="res">
      <span class="t">[${i + 1}] ${esc(r.t)}</span><br>
      <a href="${esc(r.u)}" target="_blank" rel="noreferrer">${esc(r.u)}</a>
      <div class="s">${snip(r.s)}</div></div>`).join("");
    return `<div class="arm-col"><h3>${esc(arm)} ${badge(d.grade)}
      ${d.latency != null ? `<span class="id">serp ${d.latency}s</span>` : ""}
      ${d.answerLatency != null ? `<span class="id">answer ${d.answerLatency}s</span>` : ""}</h3>
      ${d.error ? `<div class="err">${esc(d.error)}</div>` : ""}
      ${d.answer != null ? `<div class="answer">${esc(d.answer)}</div>` : ""}
      ${results}</div>`;
  }).join("");
  return `<div class="gold">gold: <b>${esc(item.gold)}</b></div>${cols}`;
}

function render() {
  const list = document.getElementById("list");
  list.innerHTML = "";
  const visible = DATA.items.filter(matches);
  document.getElementById("count").textContent =
    `${visible.length} / ${DATA.items.length} items`;
  for (const item of visible) {
    const div = document.createElement("div");
    div.className = "item";
    div.innerHTML = `<div class="item-head"><span class="id">${esc(item.id)}</span>
      <span class="q">${esc(item.q)}</span>
      ${DATA.arms.map(a => badge(item.arms[a]?.grade)).join(" ")}</div>`;
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
render();
</script>
</body>
</html>
"""

OUT_PATH.write_text(TEMPLATE.replace("__DATA__", json.dumps(payload)), encoding="utf-8")
print(f"{OUT_PATH} ({OUT_PATH.stat().st_size / 1e6:.1f} MB, {len(items)} items)")
