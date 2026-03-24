"""View eval results and message traces in a human-readable format.

Usage:
    # View summary of latest run
    python -m tests.agentic.tools.todo_prompt_eval.view_traces

    # View summary of a specific run
    python -m tests.agentic.tools.todo_prompt_eval.view_traces results/eval-20260324T...json

    # View full trace for a specific scenario
    python -m tests.agentic.tools.todo_prompt_eval.view_traces --scenario batch_customer_outreach

    # View all traces
    python -m tests.agentic.tools.todo_prompt_eval.view_traces --all
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"


def _find_latest() -> Path | None:
    results = sorted(RESULTS_DIR.glob("eval-*.json"))
    return results[-1] if results else None


def _print_summary(data: dict) -> None:
    for round_data in data.get("rounds", []):
        results = round_data.get("results", {})
        print(
            f"Model: {results.get('model', '?')}  |  Judge: {results.get('judge_model', '?')}"
        )
        print(f"Scenarios: {results.get('scenario_count', '?')}")
        print()

        avgs = results.get("averages", {})
        overall = avgs.get("overall", 0)
        print(f"Overall: {overall:.0%}")
        for k, v in avgs.items():
            if k != "overall":
                print(f"  {k}: {v:.0%}")
        print()

        print(
            f"{'Scenario':<35} {'Result':<6} {'Turns':>5} {'Todos':>5} {'Work':>5}  Reasoning"
        )
        print("-" * 120)
        for r in results.get("results", []):
            j = r.get("judgment", {})
            scores = j.get("scores", {})
            passed = "PASS" if scores.get("overall") == 1 else "FAIL"
            reasoning = j.get("reasoning", "")[:50]
            print(
                f"{r['scenario_id']:<35} {passed:<6} {r['turns']:>5} "
                f"{r.get('todo_tool_call_count', '?'):>5} {r.get('work_tool_call_count', '?'):>5}  "
                f"{reasoning}"
            )
        print()


def _print_trace(result: dict) -> None:
    sid = result["scenario_id"]
    j = result.get("judgment", {})
    scores = j.get("scores", {})
    passed = "PASS" if scores.get("overall") == 1 else "FAIL"

    print(f"\n{'=' * 80}")
    print(f"Scenario: {sid}  [{passed}]")
    print(
        f"Turns: {result['turns']}  |  Todos: {result.get('todo_tool_call_count', 0)}  |  "
        f"Work tools: {result.get('work_tool_call_count', 0)}  |  "
        f"Todo items: {result['total_todo_items']}"
    )
    print(f"Judge: {j.get('reasoning', 'N/A')}")
    print(f"{'=' * 80}")

    final_state = result.get("final_todo_state", [])
    if final_state:
        print("\nFinal todo state:")
        markers = {
            "pending": "[ ]",
            "in_progress": "[>]",
            "completed": "[x]",
            "cancelled": "[-]",
        }
        for t in final_state:
            m = markers.get(t.get("status", "pending"), "[ ]")
            print(
                f"  {m} {t.get('id', '?')}: {t.get('content', t.get('description', ''))}"
            )
        print()

    messages = result.get("messages", [])
    if not messages:
        print("\n  (no message trace saved)")
        return

    print("\n--- Conversation Trace ---\n")
    for i, msg in enumerate(messages):
        role = msg.get("role", "?")

        if role == "system":
            content = msg.get("content", "")
            if len(content) > 200:
                print(f"  [{role.upper()}] ({len(content)} chars, truncated)")
                print(f"  {content[:150]}...")
            else:
                print(f"  [{role.upper()}] {content}")

        elif role == "user":
            content = msg.get("content", "")
            print(f"  [USER] {content[:500]}")

        elif role == "assistant":
            content = msg.get("content")
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    name = fn.get("name", "?")
                    args_str = fn.get("arguments", "{}")
                    try:
                        args = json.loads(args_str)
                        if name == "todo_write":
                            todos = args.get("todos", [])
                            merge = args.get("merge", False)
                            print(
                                f"  [ASSISTANT -> todo_write] merge={merge}, {len(todos)} items:"
                            )
                            for t in todos[:10]:
                                print(
                                    f"    {t.get('status', '?'):>12} | {t.get('id', '?')}: {t.get('content', '')[:60]}"
                                )
                            if len(todos) > 10:
                                print(f"    ... and {len(todos) - 10} more")
                        else:
                            args_preview = json.dumps(args)
                            if len(args_preview) > 150:
                                args_preview = args_preview[:150] + "..."
                            print(f"  [ASSISTANT -> {name}] {args_preview}")
                    except json.JSONDecodeError:
                        print(f"  [ASSISTANT -> {name}] {args_str[:150]}")
                if content:
                    print(f"  [ASSISTANT text] {content[:300]}")
            elif content:
                if len(content) > 500:
                    print(f"  [ASSISTANT] {content[:500]}...")
                else:
                    print(f"  [ASSISTANT] {content}")

        elif role == "tool":
            content = msg.get("content", "")
            if len(content) > 200:
                print(f"  [TOOL RESPONSE] {content[:200]}...")
            else:
                print(f"  [TOOL RESPONSE] {content}")

        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="View eval traces")
    parser.add_argument("file", nargs="?", help="Results JSON file (default: latest)")
    parser.add_argument("--scenario", "-s", help="Show trace for specific scenario")
    parser.add_argument(
        "--all", "-a", action="store_true", help="Show traces for all scenarios"
    )
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
    else:
        path = _find_latest()
        if not path:
            print(f"No results found in {RESULTS_DIR}/")
            return

    print(f"Reading: {path}\n")
    data = json.loads(path.read_text())

    _print_summary(data)

    all_results = []
    for round_data in data.get("rounds", []):
        all_results.extend(round_data.get("results", {}).get("results", []))

    if args.scenario:
        matches = [r for r in all_results if r["scenario_id"] == args.scenario]
        if not matches:
            print(f"Scenario '{args.scenario}' not found. Available:")
            for r in all_results:
                print(f"  - {r['scenario_id']}")
            return
        for r in matches:
            _print_trace(r)
    elif args.all:
        for r in all_results:
            _print_trace(r)


if __name__ == "__main__":
    main()
