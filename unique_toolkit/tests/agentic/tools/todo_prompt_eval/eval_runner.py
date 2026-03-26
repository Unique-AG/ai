"""Automated prompt evaluation for todo_write system prompt and execution reminder.

Simulates multi-turn tool-calling conversations through the Unique platform's
OpenAI proxy, then scores each conversation against behavioral criteria with
an LLM-as-judge.

Usage:
    # Default: run all scenarios with current prompts
    python -m tests.agentic.tools.todo_prompt_eval.eval_runner

    # With a specific model
    python -m tests.agentic.tools.todo_prompt_eval.eval_runner --model AZURE_GPT_4o_2024_1120

    # Auto-refine mode: run, score, propose better prompts, re-test
    python -m tests.agentic.tools.todo_prompt_eval.eval_runner --refine

Prerequisites:
    Local backend running at http://localhost:8092/ (or set UNIQUE_API_BASE_URL).
    No API keys needed — uses the platform's OpenAI proxy with dummy credentials.
"""

from __future__ import annotations

import argparse
import json
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from openai import OpenAI

from unique_toolkit.framework_utilities.openai.client import get_openai_client

SCENARIO_FILE = Path(__file__).parent / "scenarios.yaml"

MAX_RETRIES = 5
RETRY_BASE_DELAY = 2.0
INTER_TURN_DELAY = 0.5


def _call_with_retry(fn, *args, **kwargs):
    """Call fn with exponential backoff on transient server errors."""
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            error_str = str(e)
            if attempt < MAX_RETRIES - 1 and (
                "500" in error_str or "404" in error_str or "429" in error_str
            ):
                delay = RETRY_BASE_DELAY * (2**attempt)
                print(
                    f"\n    Retrying in {delay}s (attempt {attempt + 2}/{MAX_RETRIES})...",
                    end=" ",
                    flush=True,
                )
                time.sleep(delay)
            else:
                raise


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

SEARCH_WEB_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": (
            "Search the web for current information. Returns a list of results "
            "with titles, snippets, and URLs. Use for questions requiring "
            "up-to-date data, facts, or research."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
            },
            "required": ["query"],
        },
    },
}

SEND_EMAIL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "send_email",
        "description": (
            "Send an email to the specified recipient. Returns a confirmation "
            "with message ID."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body content"},
            },
            "required": ["to", "subject", "body"],
        },
    },
}

WRITE_DOCUMENT_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "write_document",
        "description": (
            "Create or update a document with the given title and content. "
            "Returns the document ID and URL."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Document title"},
                "content": {
                    "type": "string",
                    "description": "Document content (markdown)",
                },
            },
            "required": ["title", "content"],
        },
    },
}

READ_DATABASE_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "read_database",
        "description": (
            "Query a database table and return matching records. "
            "Use to look up customer records, orders, inventory, etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "table": {"type": "string", "description": "Table name to query"},
                "query": {"type": "string", "description": "Search query or filter"},
            },
            "required": ["table", "query"],
        },
    },
}

ALL_TOOL_SCHEMAS = [
    TODO_WRITE_SCHEMA,
    SEARCH_WEB_SCHEMA,
    SEND_EMAIL_SCHEMA,
    WRITE_DOCUMENT_SCHEMA,
    READ_DATABASE_SCHEMA,
]


_SEARCH_COUNTER = 0


def _simulate_work_tool(tool_name: str, args: dict[str, Any]) -> str:
    """Return realistic canned responses for mock work tools."""
    global _SEARCH_COUNTER

    if tool_name == "search_web":
        query = args.get("query", "unknown")
        _SEARCH_COUNTER += 1
        return json.dumps(
            {
                "results": [
                    {
                        "title": f"Result 1 for: {query}",
                        "snippet": f"Comprehensive analysis of {query}. Key findings include market trends, "
                        "competitive positioning, and growth trajectory based on latest data.",
                        "url": f"https://example.com/result-{_SEARCH_COUNTER}-1",
                    },
                    {
                        "title": f"Result 2 for: {query}",
                        "snippet": f"Recent developments in {query}. Industry experts weigh in on "
                        "current challenges and future outlook.",
                        "url": f"https://example.com/result-{_SEARCH_COUNTER}-2",
                    },
                ]
            }
        )

    if tool_name == "send_email":
        to = args.get("to", "unknown")
        subject = args.get("subject", "")
        return json.dumps(
            {
                "status": "sent",
                "message_id": f"msg-{hash(to + subject) % 10000:04d}",
                "to": to,
            }
        )

    if tool_name == "write_document":
        title = args.get("title", "Untitled")
        content = args.get("content", "")
        return json.dumps(
            {
                "document_id": f"doc-{hash(title) % 10000:04d}",
                "title": title,
                "url": f"https://docs.example.com/doc-{hash(title) % 10000:04d}",
                "chars_written": len(content),
            }
        )

    if tool_name == "read_database":
        table = args.get("table", "unknown")
        query = args.get("query", "")
        query_str = json.dumps(args) if isinstance(query, dict) else str(query)

        import re

        vendor_match = re.search(r"V(\d{3})", query_str)
        if vendor_match or "vendor" in table.lower():
            vid = vendor_match.group(0) if vendor_match else "V001"
            num = int(vendor_match.group(1)) if vendor_match else 1
            if num % 3 == 0:
                cert_status = "expired"
            elif num % 5 == 0:
                cert_status = "missing"
            else:
                cert_status = "valid"
            return json.dumps(
                {
                    "table": table,
                    "records": [
                        {
                            "vendor_id": vid,
                            "name": f"Vendor {vid} Corp",
                            "contact_email": f"contact@vendor-{vid.lower()}.com",
                            "compliance_cert_status": cert_status,
                            "cert_expiry": "2025-06-15"
                            if cert_status == "expired"
                            else None,
                            "last_audit": "2025-01-10",
                        }
                    ],
                    "total_count": 1,
                }
            )

        if "SKU-7742" in query_str or "product" in table.lower():
            return json.dumps(
                {
                    "table": table,
                    "records": [
                        {
                            "sku": "SKU-7742",
                            "name": "Industrial Widget Pro",
                            "supplier_id": "SUP-331",
                            "supplier_name": "Acme Industrial Supply",
                            "unit_price": 24.50,
                            "category": "industrial_components",
                        }
                    ],
                    "total_count": 1,
                }
            )

        if "SUP-" in query_str or "supplier" in table.lower():
            sup_id = "SUP-331"
            import re as _re

            sup_match = _re.search(r"SUP-\d+", query_str)
            if sup_match:
                sup_id = sup_match.group(0)
            is_alternative = "alternative" in query_str.lower() or sup_id != "SUP-331"
            return json.dumps(
                {
                    "table": table,
                    "records": [
                        {
                            "supplier_id": sup_id,
                            "name": "Global Parts Co"
                            if is_alternative
                            else "Acme Industrial Supply",
                            "contact_email": f"orders@{'globalparts' if is_alternative else 'acme-industrial'}.com",
                            "inventory_SKU7742": 45 if not is_alternative else 500,
                            "unit_price": 22.00 if is_alternative else 24.50,
                            "lead_time_days": 3,
                            "rating": 4.7 if is_alternative else 4.2,
                        }
                    ],
                    "total_count": 1,
                }
            )

        if "alert" in table.lower() or "alert" in query_str.lower():
            return json.dumps(
                {
                    "table": table,
                    "records": [
                        {
                            "alert_id": "ALT-20260324-001",
                            "severity": "critical",
                            "service": "payment-gateway",
                            "error_type": "connection_timeout",
                            "started_at": "2026-03-24T14:32:00Z",
                            "affected_region": "eu-west-1",
                            "error_rate": "47%",
                            "description": "Payment gateway connection timeouts spiking. Upstream provider Stripe reporting degraded API performance.",
                        }
                    ],
                    "total_count": 1,
                }
            )

        if "runbook" in table.lower():
            return json.dumps(
                {
                    "table": table,
                    "records": [
                        {
                            "runbook_id": "RB-PAY-003",
                            "title": "Payment Gateway Connection Timeout Remediation",
                            "steps": [
                                "1. Verify upstream provider status page",
                                "2. Enable circuit breaker fallback to secondary payment processor",
                                "3. Increase connection timeout to 30s",
                                "4. Monitor error rate for 15 minutes",
                                "5. If not resolved, failover to backup gateway",
                            ],
                            "escalation_contact": "payments-oncall@engineering.com",
                        }
                    ],
                    "total_count": 1,
                }
            )

        if "ticket" in table.lower() or "C-4419" in query_str:
            return json.dumps(
                {
                    "table": table,
                    "records": [
                        {
                            "ticket_id": "TK-8891",
                            "customer_id": "C-4419",
                            "subject": "Slow dashboard loading",
                            "created_at": "2026-03-20T09:15:00Z",
                            "first_response_at": "2026-03-21T14:30:00Z",
                            "response_time_hours": 29.25,
                            "status": "open",
                            "priority": "high",
                        },
                        {
                            "ticket_id": "TK-8910",
                            "customer_id": "C-4419",
                            "subject": "Export feature timeout",
                            "created_at": "2026-03-22T11:00:00Z",
                            "first_response_at": None,
                            "response_time_hours": None,
                            "status": "open",
                            "priority": "medium",
                        },
                    ],
                    "total_count": 2,
                }
            )

        if "C-4419" in query_str or "customer" in table.lower():
            return json.dumps(
                {
                    "table": table,
                    "records": [
                        {
                            "customer_id": "C-4419",
                            "company": "NovaTech Solutions",
                            "contact_name": "Sarah Chen",
                            "contact_email": "sarah.chen@novatech.com",
                            "sla_tier": "premium",
                            "sla_response_hours": 4,
                            "account_manager": "James Wilson",
                            "account_manager_email": "j.wilson@ourcompany.com",
                            "plan": "Enterprise",
                            "arr": 125000,
                        }
                    ],
                    "total_count": 1,
                }
            )

        return json.dumps(
            {
                "table": table,
                "query": query,
                "records": [
                    {
                        "id": 1,
                        "name": f"Record matching '{query}'",
                        "status": "active",
                        "details": f"Sample data from {table} table for query '{query}'.",
                    },
                    {
                        "id": 2,
                        "name": f"Related record for '{query}'",
                        "status": "active",
                        "details": f"Additional matching data from {table}.",
                    },
                ],
                "total_count": 2,
            }
        )

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


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
        lines.append(
            f"{marker.get(t['status'], '[ ]')} {t.get('id', '?')}: {t.get('content', t.get('description', '(no content)'))}"
        )

    summary = "\n".join(lines)
    return summary, state


def run_scenario(
    client: OpenAI,
    scenario: dict[str, Any],
    system_prompt: str,
    execution_reminder: str,
    model: str,
    max_turns: int | None = None,
    reminder_mode: str = "system_message",
) -> dict[str, Any]:
    """Run a single scenario through a simulated agent loop.

    Args:
        reminder_mode: How the execution reminder is injected after todo_write.
            "system_message" — appends a separate system message (current default).
            "tool_result" — appends the reminder text to the todo_write tool
            response content, matching the real orchestrator's behavior.
    """
    if max_turns is None:
        scenario_override = scenario.get("max_turns")
        if scenario_override:
            max_turns = scenario_override
        else:
            min_items = scenario.get("expected", {}).get("min_todo_items", 0)
            max_turns = max(30, min_items * 5)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": scenario["user_message"]},
    ]

    todo_state: list[dict[str, Any]] = []
    todo_tool_calls: list[dict[str, Any]] = []
    work_tool_calls: list[dict[str, Any]] = []
    turn = 0
    used_todos = False
    asked_questions = False
    followups = list(scenario.get("followup_messages", []))

    tools_for_scenario = list(ALL_TOOL_SCHEMAS)

    context_overflow = False
    while turn < max_turns:
        turn += 1
        if turn > 1:
            time.sleep(INTER_TURN_DELAY)
        try:
            response = _call_with_retry(
                client.chat.completions.create,
                model=model,
                messages=messages,
                tools=tools_for_scenario,
                tool_choice="auto",
            )
        except Exception as e:
            if "context_length_exceeded" in str(e):
                context_overflow = True
                break
            raise

        choice = response.choices[0]
        msg = choice.message

        if msg.tool_calls:
            messages.append(msg.model_dump())

            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)

                if tc.function.name == "todo_write":
                    used_todos = True
                    todo_tool_calls.append(args)

                    summary, todo_state = _simulate_todo_response(
                        args, todo_state, execution_reminder
                    )

                    has_pending = any(
                        t["status"] in ("pending", "in_progress") for t in todo_state
                    )

                    if has_pending and reminder_mode == "tool_result":
                        tool_content = summary + "\n\n" + execution_reminder
                    else:
                        tool_content = summary

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_content,
                        }
                    )

                    if has_pending and reminder_mode == "system_message":
                        messages.append(
                            {
                                "role": "system",
                                "content": execution_reminder,
                            }
                        )
                else:
                    work_tool_calls.append({"tool": tc.function.name, "args": args})
                    result = _simulate_work_tool(tc.function.name, args)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result,
                        }
                    )
        else:
            content = msg.content or ""
            messages.append({"role": "assistant", "content": content})

            if "?" in content and turn > 1:
                asked_questions = True

            if choice.finish_reason == "stop":
                if followups:
                    followup = followups.pop(0)
                    messages.append({"role": "user", "content": followup})
                elif any(
                    t.get("status") in ("pending", "in_progress") for t in todo_state
                ):
                    messages.append({"role": "user", "content": execution_reminder})
                else:
                    break

    result_dict: dict[str, Any] = {
        "scenario_id": scenario["id"],
        "reminder_mode": reminder_mode,
        "turns": turn,
        "used_todos": used_todos,
        "asked_questions": asked_questions,
        "total_todo_items": len(todo_state),
        "final_todo_state": todo_state,
        "todo_tool_call_count": len(todo_tool_calls),
        "work_tool_call_count": len(work_tool_calls),
        "todo_tool_calls": todo_tool_calls,
        "work_tool_calls": work_tool_calls,
        "messages": messages,
    }
    if context_overflow:
        result_dict["context_overflow"] = True
    return result_dict


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
    - Todo tool calls: {todo_tool_call_count}
    - Work tool calls: {work_tool_call_count}

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
        todo_tool_call_count=result["todo_tool_call_count"],
        work_tool_call_count=result["work_tool_call_count"],
        final_state_json=json.dumps(result["final_todo_state"], indent=2),
    )

    response = _call_with_retry(
        client.chat.completions.create,
        model=judge_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"scores": {}, "reasoning": f"Failed to parse: {content[:200]}"}


def _create_client() -> OpenAI:
    """Create an OpenAI client routed through the Unique platform proxy."""
    return get_openai_client()


def run_eval(
    system_prompt: str,
    execution_reminder: str,
    model: str = "AZURE_GPT_4o_MINI_2024_0718",
    judge_model: str = "AZURE_GPT_4o_2024_1120",
    reminder_mode: str = "system_message",
) -> dict[str, Any]:
    """Run all scenarios, score with judge, return aggregate results."""
    client = _create_client()
    scenarios = load_scenarios()

    results: list[dict[str, Any]] = []

    for i, scenario in enumerate(scenarios):
        if i > 0:
            time.sleep(1.0)
        print(f"  Running: {scenario['id']}...", end=" ", flush=True)
        try:
            result = run_scenario(
                client,
                scenario,
                system_prompt,
                execution_reminder,
                model,
                reminder_mode=reminder_mode,
            )
        except Exception as e:
            err_msg = str(e)
            is_context_overflow = "context_length_exceeded" in err_msg
            label = "CONTEXT_OVERFLOW" if is_context_overflow else "ERROR"
            print(f"{label} ({err_msg[:80]})")
            result = {
                "scenario": scenario["id"],
                "error": label,
                "error_detail": err_msg[:500],
                "turns": 0,
                "todo_tool_call_count": 0,
                "work_tool_call_count": 0,
                "total_todo_items": 0,
                "final_todo_state": [],
                "messages": [],
                "judgment": {
                    "scores": {
                        "todo_usage": 0,
                        "item_count": 0,
                        "completeness": 0,
                        "autonomy": 0,
                        "overall": 0,
                    },
                    "reasoning": f"Scenario failed with {label}: {err_msg[:200]}",
                },
            }
            results.append(result)
            continue

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
        "reminder_mode": reminder_mode,
        "scenario_count": len(scenarios),
        "averages": averages,
        "results": [
            {
                "scenario_id": r["scenario_id"],
                "turns": r["turns"],
                "used_todos": r["used_todos"],
                "total_todo_items": r["total_todo_items"],
                "todo_tool_call_count": r["todo_tool_call_count"],
                "work_tool_call_count": r["work_tool_call_count"],
                "final_todo_state": r["final_todo_state"],
                "judgment": r["judgment"],
                "messages": r["messages"],
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
    parser.add_argument(
        "--model",
        default="AZURE_GPT_4o_MINI_2024_0718",
        help="Agent model (LanguageModelName enum value)",
    )
    parser.add_argument(
        "--judge-model",
        default="AZURE_GPT_4o_2024_1120",
        help="Judge model (LanguageModelName enum value)",
    )
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
    parser.add_argument(
        "--reminder-mode",
        choices=["system_message", "tool_result", "compare"],
        default="system_message",
        help="How to inject the execution reminder after todo_write. "
        "'compare' runs both modes and outputs side-by-side results.",
    )
    args = parser.parse_args()

    from unique_toolkit.agentic.tools.todo.service import (
        _TODO_EXECUTION_REMINDER,
        _TODO_SYSTEM_PROMPT,
    )

    current_system_prompt = _TODO_SYSTEM_PROMPT
    current_reminder = _TODO_EXECUTION_REMINDER

    modes = (
        ["system_message", "tool_result"]
        if args.reminder_mode == "compare"
        else [args.reminder_mode]
    )

    all_rounds: list[dict[str, Any]] = []
    best_score = 0.0

    for mode in modes:
        for round_num in range(1, args.max_refine_rounds + 1 if args.refine else 2):
            print(f"\n{'=' * 60}")
            label = f"Round {round_num}"
            if len(modes) > 1:
                label += f" [reminder_mode={mode}]"
            print(f"{label}: evaluating prompts")
            print(f"{'=' * 60}")

            system_prompt = _build_system_prompt(current_system_prompt)
            results = run_eval(
                system_prompt,
                current_reminder,
                args.model,
                args.judge_model,
                reminder_mode=mode,
            )

            overall = results["averages"].get("overall", 0)
            print(f"\nOverall: {overall:.0%}")
            for k, v in results["averages"].items():
                if k != "overall":
                    print(f"  {k}: {v:.0%}")

            round_data = {
                "round": round_num,
                "reminder_mode": mode,
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
            client = _create_client()
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
            current_system_prompt = refinement.get(
                "system_prompt", current_system_prompt
            )
            current_reminder = refinement.get("execution_reminder", current_reminder)
            round_data["refinement"] = refinement

    output_data = {
        "best_overall_score": best_score,
        "rounds": all_rounds,
    }

    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    if args.output:
        out_path = Path(args.output)
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = results_dir / f"eval-{ts}.json"

    out_path.write_text(json.dumps(output_data, indent=2))
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
