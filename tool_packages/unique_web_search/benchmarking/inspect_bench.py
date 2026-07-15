# %% [markdown]
# # Benchmark — results inspector
#
# Reads the results of all three stages and writes a single self-contained
# `results/inspect.html`: dataset and answerer dropdowns (defaulting to the
# strongest answerer), a per-arm summary table with optional category slicing
# (e.g. FreshQA fact_type), and a filterable per-item drill-down showing each
# arm's SERP, answer, and grade side by side.
#
# Pure read against results/ and the dataset cache (the dataset is reloaded
# only to map items to categories; downloads once if the cache is cold).
# Re-run after any benchmark run:
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
from qa_datasets import load_dataset
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
    EngineConfig(engine="brave", fetch_size=10, params={"extra_snippets": False}),
    EngineConfig(engine="perplexity", fetch_size=10),
    None,  # no search — closed-book baseline
]
BENCHMARK_CONFIGS = [
    BenchmarkConfig(dataset="simpleqa", sample_n=300, seed=20260714),
    BenchmarkConfig(dataset="freshqa", sample_n=None, seed=20260714),
]
# First entry is the strongest answerer — the dropdown's default view.
ANSWERER_CONFIGS = [
    AnswererConfig(model="AZURE_GPT_54_2026_0305", top_k=10),
    AnswererConfig(model="AZURE_GPT_41_2025_0414", top_k=10),
]
# Judge pinned to the strongest available model (currently GPT 5.4); see
# grade_bench.py — never varied per run.
GRADER_CONFIG = GraderConfig(model="AZURE_GPT_54_2026_0305")
RESULTS_DIR = Path(__file__).parent / "results"
OUT_PATH = RESULTS_DIR / "inspect.html"

arms = [search_engine_slug(engine) for engine in SEARCH_ENGINES]


# %% Per-arm statistics over an item subset (a category slice or everything)
def arm_stats(
    arm: str,
    serp_map: dict[str, SerpRecord],
    answer_map: dict[str, AnswerRecord],
    grade_map: dict[str, GradeRecord],
    ids: set[str],
) -> dict:
    graded = [g for i in ids if (g := grade_map.get(i)) and g.error is None]
    n = len(graded)
    correct = sum(g.grade == "CORRECT" for g in graded)
    answered = [a for i in ids if (a := answer_map.get(i)) and a.error is None]
    declined = sum(a.answer.lower().startswith("i don't know") for a in answered)
    serp_ok = [s for i in ids if (s := serp_map.get(i)) and s.error is None]
    evidence = [
        sum(len(r.snippet) + len(r.title) for r in s.results) for s in serp_ok
    ] or [0]
    accuracy = correct / n if n else 0
    return {
        "arm": arm,
        "n": n,
        "correct": correct,
        "incorrect": sum(g.grade == "INCORRECT" for g in graded),
        "notAttempted": sum(g.grade == "NOT_ATTEMPTED" for g in graded),
        "accuracy": accuracy,
        "ci": 1.96 * math.sqrt(accuracy * (1 - accuracy) / n) if n else 0,
        "declined": declined,
        "searchMeanS": round(mean([s.latency_s for s in serp_ok]), 2)
        if serp_ok
        else None,
        "evidenceChars": round(mean(evidence)),
        "serpErrors": sum(
            1 for i in ids if (s := serp_map.get(i)) and s.error is not None
        ),
    }


def pair_stats(grades_by_arm: dict[str, dict[str, GradeRecord]], ids: set[str]) -> list:
    baseline = arms[0]
    rows = []
    for arm in arms[1:]:
        shared = [
            i
            for i in sorted(ids)
            if (b := grades_by_arm[baseline].get(i))
            and b.error is None
            and (a := grades_by_arm[arm].get(i))
            and a.error is None
        ]
        base_c = {i: grades_by_arm[baseline][i].grade == "CORRECT" for i in shared}
        arm_c = {i: grades_by_arm[arm][i].grade == "CORRECT" for i in shared}
        rows.append(
            {
                "arm": arm,
                "baseline": baseline,
                "armOnly": sum(arm_c[i] and not base_c[i] for i in shared),
                "baseOnly": sum(base_c[i] and not arm_c[i] for i in shared),
                "shared": len(shared),
            }
        )
    return rows


# %% Collect one payload block per dataset
def collect_dataset(benchmark: BenchmarkConfig) -> dict:
    category_by_id = {
        item.item_id: item.category
        for item in load_dataset(benchmark.dataset, benchmark.sample_n, benchmark.seed)
    }

    serps: dict[str, dict[str, SerpRecord]] = {}
    for engine in SEARCH_ENGINES:
        arm = search_engine_slug(engine)
        serps[arm] = (
            {}
            if engine is None
            else {
                r.item_id: r
                for r in latest_by_item(
                    load_jsonl(results_path(RESULTS_DIR, engine, benchmark), SerpRecord)
                )
            }
        )

    answers: dict[str, dict[str, dict[str, AnswerRecord]]] = {}
    grades: dict[str, dict[str, dict[str, GradeRecord]]] = {}
    for answerer in ANSWERER_CONFIGS:
        answers[answerer.slug] = {}
        grades[answerer.slug] = {}
        for arm in arms:
            answers[answerer.slug][arm] = {
                r.item_id: r
                for r in latest_by_item(
                    load_jsonl(
                        answers_path(RESULTS_DIR, arm, benchmark, answerer),
                        AnswerRecord,
                    )
                )
            }
            grades[answerer.slug][arm] = {
                r.item_id: r
                for r in latest_by_item(
                    load_jsonl(
                        grades_path(
                            RESULTS_DIR, arm, benchmark, answerer, GRADER_CONFIG
                        ),
                        GradeRecord,
                    )
                )
            }

    item_ids = sorted(
        {i for arm in arms for i in serps[arm]}
        | {
            i
            for answerer in ANSWERER_CONFIGS
            for arm in arms
            for i in answers[answerer.slug][arm]
        }
    )

    def item_meta(item_id: str) -> tuple[str, str]:
        for arm in arms:
            if rec := serps[arm].get(item_id):
                return rec.question, rec.gold_answer
        for answerer in ANSWERER_CONFIGS:
            for arm in arms:
                if rec := answers[answerer.slug][arm].get(item_id):
                    return rec.question, rec.gold_answer
        return "?", "?"

    items = []
    for item_id in item_ids:
        question, gold = item_meta(item_id)
        row: dict = {
            "id": item_id,
            "q": question,
            "gold": gold,
            "cat": category_by_id.get(item_id),
            "serps": {},
            "answers": {},
        }
        for arm in arms:
            if serp := serps[arm].get(item_id):
                row["serps"][arm] = {
                    "latency": serp.latency_s,
                    "error": serp.error,
                    "results": [
                        {
                            "u": r.url,
                            "t": html.unescape(r.title),
                            "s": html.unescape(r.snippet),
                        }
                        for r in serp.results
                    ],
                }
        for answerer in ANSWERER_CONFIGS:
            per_arm = {}
            for arm in arms:
                answer = answers[answerer.slug][arm].get(item_id)
                grade = grades[answerer.slug][arm].get(item_id)
                if answer is None and grade is None:
                    continue
                per_arm[arm] = {
                    "grade": grade.grade if grade and grade.error is None else None,
                    "answer": answer.answer if answer else None,
                    "error": answer.error if answer else None,
                    "answerLatency": answer.latency_s if answer else None,
                }
            row["answers"][answerer.slug] = per_arm
        items.append(row)

    categories = sorted({c for c in category_by_id.values() if c})
    ids_by_slice = {"all": set(item_ids)} | {
        cat: {i for i in item_ids if category_by_id.get(i) == cat} for cat in categories
    }
    summaries: dict = {}
    pairs: dict = {}
    for answerer in ANSWERER_CONFIGS:
        summaries[answerer.slug] = {
            slice_key: [
                arm_stats(
                    arm,
                    serps[arm],
                    answers[answerer.slug][arm],
                    grades[answerer.slug][arm],
                    ids,
                )
                for arm in arms
            ]
            for slice_key, ids in ids_by_slice.items()
        }
        pairs[answerer.slug] = {
            slice_key: pair_stats(grades[answerer.slug], ids)
            for slice_key, ids in ids_by_slice.items()
        }

    return {
        "key": benchmark.slug,
        "label": benchmark.slug,
        "categories": categories,
        "summaries": summaries,
        "pairs": pairs,
        "items": items,
    }


payload = {
    "arms": arms,
    "answerers": [{"key": a.slug, "label": a.model} for a in ANSWERER_CONFIGS],
    "grader": GRADER_CONFIG.model,
    "datasets": [collect_dataset(benchmark) for benchmark in BENCHMARK_CONFIGS],
}

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
              margin: 0 0 10px; }
  header .controls { margin-bottom: 12px; }
  main .controls { margin-top: 18px; }
  .controls label { font-size: 12px; color: #57606a; display: block; }
  .controls select, .controls input { font: inherit; padding: 3px 6px;
    border: 1px solid #d1d9e0; border-radius: 6px; background: #fff; }
  .controls input { width: 260px; }
  .pin { display: inline-block; padding: 3px 6px; border: 1px solid #d1d9e0;
         border-radius: 6px; background: #f6f8fa; color: #57606a; }
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
const snip = s => esc(s).replaceAll("&lt;strong&gt;", "<strong>")
                        .replaceAll("&lt;/strong&gt;", "</strong>");
const badge = g => `<span class="badge g-${g ?? "none"}">${g ?? "missing"}</span>`;
const fmtPct = x => (100 * x).toFixed(1) + "%";

// view state: which dataset / answerer / category slice is shown
let dsIndex = 0;
let answererKey = DATA.answerers[0].key;
let category = "all";
const ds = () => DATA.datasets[dsIndex];

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

// header: dataset + answerer + category dropdowns, pinned grader
const viewbar = document.getElementById("viewbar");
addSelect(viewbar, "dataset", DATA.datasets.map((d, i) =>
  ({label: d.label, value: i})), v => {
    dsIndex = +v; rebuildCategorySelect(); renderAll(); });
const catWrap = addSelect(viewbar, "subset", [{label: "all", value: "all"}],
  v => { category = v; renderAll(); });
const catSel = catWrap.querySelector("select");
function rebuildCategorySelect() {
  category = "all";
  catSel.innerHTML = "";
  for (const opt of ["all", ...ds().categories]) catSel.add(new Option(opt, opt));
  catWrap.style.display = ds().categories.length ? "" : "none";
}
addSelect(viewbar, "answerer", DATA.answerers.map(a =>
  ({label: a.label, value: a.key})), v => { answererKey = v; renderAll(); });
const graderWrap = document.createElement("span");
graderWrap.innerHTML =
  `<label>grader (pinned)</label><span class="pin">${esc(DATA.grader)}</span>`;
viewbar.appendChild(graderWrap);

// item controls: one grade filter per arm, text search
const controls = document.getElementById("controls");
const filters = {};
for (const arm of DATA.arms) {
  filters[arm] = "any";
  addSelect(controls, arm,
    ["any", "CORRECT", "INCORRECT", "NOT_ATTEMPTED", "missing"].map(o =>
      ({label: o, value: o})), v => { filters[arm] = v; render(); });
}
const searchWrap = document.createElement("span");
searchWrap.innerHTML = "<label>search question / answer / gold</label>";
const search = document.createElement("input");
search.oninput = () => render();
searchWrap.appendChild(search);
controls.appendChild(searchWrap);
controls.appendChild(document.getElementById("count"));

function renderSummary() {
  const rows = ds().summaries[answererKey]?.[category] ?? [];
  document.getElementById("summary").innerHTML =
    "<tr><th>arm</th><th>n</th><th>correct</th><th>incorrect</th>" +
    "<th>not_attempted</th><th>accuracy</th><th>declined</th>" +
    "<th>mean search time</th><th>evidence chars/q</th><th>serp errors</th></tr>" +
    rows.map(s => `<tr><td>${esc(s.arm)}</td><td>${s.n}</td>
      <td>${s.correct}</td><td>${s.incorrect}</td><td>${s.notAttempted}</td>
      <td><b>${fmtPct(s.accuracy)}</b> ±${(100 * s.ci).toFixed(1)}pp</td>
      <td>${s.declined}</td><td>${s.searchMeanS != null ? s.searchMeanS + "s" : "—"}</td>
      <td>${s.evidenceChars}</td><td>${s.serpErrors}</td></tr>`
    ).join("");
  document.getElementById("pairs").innerHTML =
    (ds().pairs[answererKey]?.[category] ?? []).map(p =>
      `paired vs <b>${esc(p.baseline)}</b>: <b>${esc(p.arm)}</b> wins ${p.armOnly}, ` +
      `loses ${p.baseOnly} (of ${p.shared} shared)`).join(" · ");
}

function matches(item) {
  if (category !== "all" && item.cat !== category) return false;
  const byArm = item.answers[answererKey] ?? {};
  for (const arm of DATA.arms) {
    const want = filters[arm];
    if (want === "any") continue;
    const grade = byArm[arm]?.grade ?? "missing";
    if (grade !== want) return false;
  }
  const needle = search.value.toLowerCase();
  if (!needle) return true;
  const hay = [item.q, item.gold, item.cat ?? "",
    ...DATA.arms.map(a => byArm[a]?.answer ?? "")].join(" ").toLowerCase();
  return hay.includes(needle);
}

function detailHtml(item) {
  const byArm = item.answers[answererKey] ?? {};
  const cols = DATA.arms.map(arm => {
    const serp = item.serps[arm];
    const d = byArm[arm] ?? {};
    const error = serp?.error ?? d.error;
    const results = (serp?.results ?? []).map((r, i) => `<div class="res">
      <span class="t">[${i + 1}] ${esc(r.t)}</span><br>
      <a href="${esc(r.u)}" target="_blank" rel="noreferrer">${esc(r.u)}</a>
      <div class="s">${snip(r.s)}</div></div>`).join("");
    return `<div class="arm-col"><h3>${esc(arm)} ${badge(d.grade)}
      ${serp?.latency != null ? `<span class="id">serp ${serp.latency}s</span>` : ""}
      ${d.answerLatency != null ? `<span class="id">answer ${d.answerLatency}s</span>` : ""}</h3>
      ${error ? `<div class="err">${esc(error)}</div>` : ""}
      ${d.answer != null ? `<div class="answer">${esc(d.answer)}</div>` : ""}
      ${results}</div>`;
  }).join("");
  const cat = item.cat ? ` · <span class="id">${esc(item.cat)}</span>` : "";
  return `<div class="gold">gold: <b>${esc(item.gold)}</b>${cat}</div>${cols}`;
}

function render() {
  const list = document.getElementById("list");
  list.innerHTML = "";
  const visible = ds().items.filter(matches);
  document.getElementById("count").textContent =
    `${visible.length} / ${ds().items.length} items`;
  for (const item of visible) {
    const byArm = item.answers[answererKey] ?? {};
    const div = document.createElement("div");
    div.className = "item";
    div.innerHTML = `<div class="item-head"><span class="id">${esc(item.id)}</span>
      <span class="q">${esc(item.q)}</span>
      ${DATA.arms.map(a => badge(byArm[a]?.grade)).join(" ")}</div>`;
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
rebuildCategorySelect();
renderAll();
</script>
</body>
</html>
"""

OUT_PATH.write_text(TEMPLATE.replace("__DATA__", json.dumps(payload)), encoding="utf-8")
print(f"{OUT_PATH} ({OUT_PATH.stat().st_size / 1e6:.1f} MB)")
