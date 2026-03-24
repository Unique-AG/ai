"""Automated prompt evaluation for todo_write system prompt and execution reminder.

Simulates multi-turn tool-calling conversations using the OpenAI API, then
scores each conversation against behavioral criteria with an LLM-as-judge.

Usage:
    # Default: run all scenarios with current prompts
    python -m tests.agentic.tools.todo_prompt_eval.eval_runner

    # With a specific model
    python -m tests.agentic.tools.todo_prompt_eval.eval_runner --model gpt-4o

    # Auto-refine mode: run, score, propose better prompts, re-test
    python -m tests.agentic.tools.todo_prompt_eval.eval_runner --refine

Environment variables:
    OPENAI_API_KEY: Required for API access.
    EVAL_MODEL: Model to use for agent simulation (default: gpt-4o-mini).
    JUDGE_MODEL: Model to use for LLM-as-judge (default: gpt-4o).
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

try:
    from openai import OpenAI
except ImportError:
    print("Install openai: pip install openai")
    sys.exit(1)


SCENARIO_FILE = Path(__file__).parent / "scenarios.yaml"

TODO_WRITE_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "todo_write",
        "description": (
            "Create or update a task list to track progress on multi-step work. "
            "Use for multi-step workflows and batch operations where every item "
            "must be processed. Mark items in_progress when starting, "
            "completed when done. Only one item should be in_progress at a time."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "content": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": [
                                    "pending",
                                    "in_progress",
                                    "completed",
                                    "cancelled",
                                ],
                            },
                        },
                        "required": ["id", "content", "status"],
                    },
                },
                "merge": {"type": "boolean", "default": False},
            },
            "required": ["todos"],
        },
    },
}


def load_scenarios() -> list[dict[str, Any]]:
    return yaml.safe_load(SCENARIO_FILE.read_text())


def _build_system_prompt(todo_system_prompt: str) -> str:
    return (
        "You are a helpful AI assistant. You have access to tools.\n\n"
        + todo_system_prompt
    )


def _simulate_todo_response(
    tool_call_args: dict[str, Any],
    state: list[dict[str, Any]],
    execution_reminder: str,
) -> tuple[str, list[dict[str, Any]]]:
    """Simulate the todo_write tool: merge/replace state, return summary."""
    incoming = tool_call_args.get("todos", [])
    merge = tool_call_args.get("merge", False)

    if merge and state:
        existing_map = {t["id"]: t for t in state}
        for item in incoming:
            existing_map[item["id"]] = item
        state = list(existing_map.values())
    else:
        state = list(incoming)

    counts = {"pending": 0, "in_progress": 0, "completed": 0, "cancelled": 0}
    for t in state:
        counts[t.get("status", "pending")] += 1

    lines = [f"Total: {len(state)} items"]
    for s, c in counts.items():
        if c > 0:
            lines.append(f"  {s}: {c}")
    lines.append("")
    for t in state:
        marker = {
            "pending": "[ ]",
            "in_progress": "[>]",
            "completed": "[x]",
            "cancelled": "[-]",
        }
        lines.append(f"{marker.get(t['status'], '[ ]')} {t['id']}: {t['content']}")

    summary = "\n".join(lines)
    return summary, state


def run_scenario(
    client: OpenAI,
    scenario: dict[str, Any],
    system_prompt: str,
    execution_reminder: str,
    model: str,
    max_turns: int = 30,
) -> dict[str, Any]:
    """Run a single scenario through a simulated agent loop."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": scenario["user_message"]},
    ]

    todo_state: list[dict[str, Any]] = []
    all_tool_calls: list[dict[str, Any]] = []
    turn = 0
    used_todos = False
    asked_questions = False

    while turn < max_turns:
        turn += 1
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[TODO_WRITE_SCHEMA],
            tool_choice="auto",
        )

        choice = response.choices[0]
        msg = choice.message

        if msg.tool_calls:
            messages.append(msg.model_dump())

            for tc in msg.tool_calls:
                if tc.function.name == "todo_write":
                    used_todos = True
                    args = json.loads(tc.function.arguments)
                    all_tool_calls.append(args)

                    summary, todo_state = _simulate_todo_response(
                        args, todo_state, execution_reminder
                    )

                    tool_response_content = summary
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_response_content,
                        }
                    )

                    if any(
                        t["status"] in ("pending", "in_progress") for t in todo_state
                    ):
                        messages.append(
                            {
                                "role": "system",
                                "content": execution_reminder,
                            }
                        )
        else:
            content = msg.content or ""
            messages.append({"role": "assistant", "content": content})

            if "?" in content and turn > 1:
                asked_questions = True

            if choice.finish_reason == "stop":
                break

    return {
        "scenario_id": scenario["id"],
        "turns": turn,
        "used_todos": used_todos,
        "asked_questions": asked_questions,
        "total_todo_items": len(todo_state),
        "final_todo_state": todo_state,
        "tool_call_count": len(all_tool_calls),
        "all_tool_calls": all_tool_calls,
        "messages": messages,
    }


JUDGE_PROMPT = textwrap.dedent("""\
    You are evaluating an AI agent's behavior when given a task.
    The agent has a `todo_write` tool for tracking multi-step work.

    ## Scenario
    {scenario_description}

    ## User message
    {user_message}

    ## Expected behavior
    {expected_json}

    ## Actual behavior
    - Used todos: {used_todos}
    - Todo item count: {total_todo_items}
    - Total turns: {turns}
    - Asked mid-execution questions: {asked_questions}
    - Tool calls: {tool_call_count}

    ## Final todo state
    {final_state_json}

    ## Scoring criteria
    For each criterion below, score 1 (pass) or 0 (fail):

    1. **todo_usage**: Did the agent correctly use/not-use todos based on expected behavior?
    2. **item_count**: If todos were expected, did the agent create at least the minimum number?
    3. **completeness**: If should_complete_all is true, did every item reach completed/cancelled?
    4. **autonomy**: If should_not_ask_mid_execution is true, did the agent avoid asking questions during execution?
    5. **overall**: Considering all factors, did the agent behave appropriately?

    Respond with ONLY a JSON object:
    {{
        "scores": {{
            "todo_usage": 0 or 1,
            "item_count": 0 or 1,
            "completeness": 0 or 1,
            "autonomy": 0 or 1,
            "overall": 0 or 1
        }},
        "reasoning": "Brief explanation of scoring"
    }}""")


def judge_result(
    client: OpenAI,
    scenario: dict[str, Any],
    result: dict[str, Any],
    judge_model: str,
) -> dict[str, Any]:
    """Use an LLM to score the agent's behavior."""
    prompt = JUDGE_PROMPT.format(
        scenario_description=scenario["description"],
        user_message=scenario["user_message"],
        expected_json=json.dumps(scenario["expected"], indent=2),
        used_todos=result["used_todos"],
        total_todo_items=result["total_todo_items"],
        turns=result["turns"],
        asked_questions=result["asked_questions"],
        tool_call_count=result["tool_call_count"],
        final_state_json=json.dumps(result["final_todo_state"], indent=2),
    )

    response = client.chat.completions.create(
        model=judge_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"scores": {}, "reasoning": f"Failed to parse: {content[:200]}"}


def run_eval(
    system_prompt: str,
    execution_reminder: str,
    model: str = "gpt-4o-mini",
    judge_model: str = "gpt-4o",
) -> dict[str, Any]:
    """Run all scenarios, score with judge, return aggregate results."""
    client = OpenAI()
    scenarios = load_scenarios()

    results: list[dict[str, Any]] = []

    for scenario in scenarios:
        print(f"  Running: {scenario['id']}...", end=" ", flush=True)
        result = run_scenario(
            client, scenario, system_prompt, execution_reminder, model
        )
        judgment = judge_result(client, scenario, result, judge_model)
        result["judgment"] = judgment
        results.append(result)

        scores = judgment.get("scores", {})
        overall = scores.get("overall", "?")
        print(
            f"{'PASS' if overall == 1 else 'FAIL'} ({judgment.get('reasoning', '')[:80]})"
        )

    all_scores: dict[str, list[int]] = {}
    for r in results:
        for k, v in r.get("judgment", {}).get("scores", {}).items():
            all_scores.setdefault(k, []).append(v)

    averages = {k: sum(v) / len(v) for k, v in all_scores.items()}

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "judge_model": judge_model,
        "scenario_count": len(scenarios),
        "averages": averages,
        "results": [
            {
                "scenario_id": r["scenario_id"],
                "turns": r["turns"],
                "used_todos": r["used_todos"],
                "total_todo_items": r["total_todo_items"],
                "judgment": r["judgment"],
            }
            for r in results
        ],
    }


REFINE_PROMPT = textwrap.dedent("""\
    You are an expert prompt engineer. An AI agent has a `todo_write` tool for
    tracking multi-step work. The agent is guided by two prompts:

    ## Current system prompt section (injected into the main system prompt)
    ```
    {current_system_prompt}
    ```

    ## Current execution reminder (injected as system_reminder with each tool response)
    ```
    {current_execution_reminder}
    ```

    ## Eval results
    Overall score: {overall_score:.0%}

    Failures:
    {failures}

    ## Task
    Propose improved versions of BOTH prompts that address the failures
    while maintaining the strengths. Return ONLY a JSON object:
    {{
        "system_prompt": "your improved system prompt section",
        "execution_reminder": "your improved execution reminder",
        "changes_made": "brief description of what you changed and why"
    }}""")


def propose_refinement(
    client: OpenAI,
    current_system_prompt: str,
    current_execution_reminder: str,
    eval_results: dict[str, Any],
    model: str = "gpt-4o",
) -> dict[str, Any]:
    """Propose improved prompts based on eval failures."""
    failures: list[str] = []
    for r in eval_results["results"]:
        judgment = r.get("judgment", {})
        scores = judgment.get("scores", {})
        if scores.get("overall") != 1:
            failures.append(
                f"- {r['scenario_id']}: {judgment.get('reasoning', 'no reason')}"
            )

    if not failures:
        return {"no_changes": True, "reason": "All scenarios passed."}

    prompt = REFINE_PROMPT.format(
        current_system_prompt=current_system_prompt,
        current_execution_reminder=current_execution_reminder,
        overall_score=eval_results["averages"].get("overall", 0),
        failures="\n".join(failures),
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"error": f"Failed to parse: {content[:200]}"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Todo prompt eval runner")
    parser.add_argument("--model", default="gpt-4o-mini", help="Agent model")
    parser.add_argument("--judge-model", default="gpt-4o", help="Judge model")
    parser.add_argument(
        "--refine",
        action="store_true",
        help="Auto-refine prompts after scoring",
    )
    parser.add_argument(
        "--max-refine-rounds",
        type=int,
        default=3,
        help="Max refinement rounds (with --refine)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for results JSON",
    )
    args = parser.parse_args()

    from unique_toolkit.agentic.tools.todo.service import (
        _TODO_EXECUTION_REMINDER,
        _TODO_SYSTEM_PROMPT,
    )

    current_system_prompt = _TODO_SYSTEM_PROMPT
    current_reminder = _TODO_EXECUTION_REMINDER

    all_rounds: list[dict[str, Any]] = []
    best_score = 0.0

    for round_num in range(1, args.max_refine_rounds + 1 if args.refine else 2):
        print(f"\n{'=' * 60}")
        print(f"Round {round_num}: evaluating prompts")
        print(f"{'=' * 60}")

        system_prompt = _build_system_prompt(current_system_prompt)
        results = run_eval(
            system_prompt, current_reminder, args.model, args.judge_model
        )

        overall = results["averages"].get("overall", 0)
        print(f"\nOverall: {overall:.0%}")
        for k, v in results["averages"].items():
            if k != "overall":
                print(f"  {k}: {v:.0%}")

        round_data = {
            "round": round_num,
            "system_prompt": current_system_prompt,
            "execution_reminder": current_reminder,
            "results": results,
        }
        all_rounds.append(round_data)

        if overall > best_score:
            best_score = overall

        if overall == 1.0:
            print("\nAll scenarios passed! No refinement needed.")
            break

        if not args.refine or round_num >= args.max_refine_rounds:
            break

        print("\nProposing refined prompts...")
        client = OpenAI()
        refinement = propose_refinement(
            client,
            current_system_prompt,
            current_reminder,
            results,
            args.judge_model,
        )

        if refinement.get("no_changes"):
            print("No changes proposed.")
            break

        if "error" in refinement:
            print(f"Refinement error: {refinement['error']}")
            break

        print(f"Changes: {refinement.get('changes_made', 'N/A')}")
        current_system_prompt = refinement.get("system_prompt", current_system_prompt)
        current_reminder = refinement.get("execution_reminder", current_reminder)
        round_data["refinement"] = refinement

    output_data = {
        "best_overall_score": best_score,
        "rounds": all_rounds,
    }

    if args.output:
        out_path = Path(args.output)
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = Path(f"/tmp/todo-prompt-eval-{ts}.json")

    out_path.write_text(json.dumps(output_data, indent=2))
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
