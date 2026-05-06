---
name: trace
description: Navigate execution flow from an entry point, mapping call chains, external dependencies, and side effects.
license: MIT
compatibility: claude cursor opencode
metadata:
  version: "1.0.0"
  languages: all
  audience: developers
  workflow: analysis
  since: "2026-02-24"
---

## What I do

I map execution flow from a given entry point — a file path, function name, or class name — and produce two things:

1. **Mermaid flow diagram** — a `graph TD` call graph showing which functions call which, with external dependencies (APIs, databases, queues, file I/O) styled distinctly. Ambiguous callees, truncation points, and cycles are marked explicitly in the diagram.
2. **Structured markdown summary** — a full breakdown covering: call chain narrative, key files and their roles, external dependencies (name, protocol, call site), side effects (file writes, network calls, state mutations), ambiguities and truncations, and a one-paragraph entry-to-exit narrative.

I trace the call graph depth-first up to 3 levels by default. I work with any programming language — I read the code semantically, so no static analysis tools are required.

## When to use me

Use me when you:
- Pick up an unfamiliar module or function and need to understand what it does and what it touches before making changes
- Are about to refactor a function or class and need to know the blast radius — what calls into it, what it calls out to, and what side effects are involved
- Want a specific question answered about a piece of code (e.g., "what external services does this touch?") without reading every file manually
- Need to orient a new team member in a complex flow
- Are debugging an unexpected side effect and need to map where state mutations happen

## Example usage

```
/trace src/payments/checkout.py
```
→ Full trace from the `checkout.py` entry point: call chain, all files involved, external dependencies highlighted

```
/trace AuthService.authenticate
```
→ Blast-radius map: everything that calls `authenticate` (callers) and everything it delegates to (callees + side effects)

```
/trace payments/checkout.py "what external services does this touch?"
```
→ Focused trace: leads with a direct answer listing all external services, then provides the full trace for context

## How to respond

### Step 1 — Parse input

Extract the entry point from the invocation:
- Accept a **file path** (e.g., `src/payments/checkout.py`), a **function name** (e.g., `process_order`), or a **class name** (e.g., `AuthService`)
- Accept an optional **focus question** as a second argument — plain text after the entry point
- If the entry point is ambiguous (name matches multiple functions/files), ask the user to clarify before proceeding

### Step 2 — Locate the entry point

Search the codebase for the entry point:
- For file paths: confirm the file exists; identify the top-level functions/classes as the trace root
- For function/class names: search across all files; if multiple matches exist, list them and ask which to trace
- If the entry point is **not found**: stop immediately and report: "Entry point `<name>` not found in the codebase. Check the spelling or provide the file path directly."

### Step 3 — Trace the call graph (depth-first, 3 levels)

Starting from the entry point, traverse outbound calls:
- For each function/method: record its **name**, **file path**, and all **outbound calls** it makes
- Recurse into each callee, up to **3 levels deep** (configurable — user can request deeper: "trace up to 5 levels")
- When the depth limit is reached: mark the node as `[TRUNCATED at depth N]` and stop recursing that branch
- **Do not re-read files you have already traced** — if a node appears again, mark it as `[CYCLE]` and stop

### Step 4 — Classify each node

For every node in the call graph, classify it as one of:

| Classification | Label | Criteria |
|---|---|---|
| **Internal** | (no label) | Function/method owned by the project |
| **External** | `[EXTERNAL]` | Crosses the codebase boundary: HTTP calls, DB queries, file I/O, message queue publish/consume, event emissions |
| **Ambiguous** | `[AMBIGUOUS]` | Callee cannot be statically determined: dynamic dispatch, dependency injection, reflection, `eval()` |

For External nodes, record: what system it connects to (e.g., "Stripe API", "PostgreSQL", "S3"), the call site (file + line or function), and the protocol/method (HTTP POST, SQL SELECT, etc.).

### Step 5 — Detect side effects

Identify and list all side effects encountered during the trace:
- File writes (creating, updating, or deleting files)
- Network calls (HTTP requests, socket connections)
- State mutations (writes to shared state, cache updates, session changes)
- External integrations (database writes, queue publishes, event emissions)

### Step 6 — Handle cycles and truncations

- **Cycles**: When a node would be visited a second time, insert a `[CYCLE → <original-node>]` marker in the diagram and note it in the Ambiguities section
- **Truncations**: When the depth limit stops recursion, insert a `[TRUNCATED]` node in the diagram and note it in the Ambiguities section with the path that was cut off

### Step 7 — Apply focus question (if provided)

If a focus question was given:
- Identify which nodes and edges in the call graph are most relevant to answering it
- Prepare a **direct answer** (1–3 sentences) to lead the output — answer the question first, before the diagram
- Emphasise relevant nodes in the summary (list them first in their respective sections)
- The full trace is still produced — the focus question changes prioritisation, not scope

### Step 8 — Produce output

Always produce **two parts in this order**:

---

#### Part 1: Mermaid diagram

```
graph TD
    entryNode["file.py\nfunction_name()"]
    internalNode["other_file.py\ncalled_function()"]
    extNode["[EXTERNAL]\nStripe API (HTTP POST)"]:::external
    ambigNode["[AMBIGUOUS]\ndynamic_handler()"]:::ambiguous
    truncNode["[TRUNCATED at depth 3]"]:::truncated
    cycleNode["[CYCLE → entryNode]"]:::cycle

    entryNode --> internalNode
    entryNode --> extNode
    internalNode --> ambigNode
    internalNode --> truncNode
    entryNode -.-> cycleNode

    classDef external fill:#fef3c7,stroke:#d97706,stroke-dasharray: 5 5
    classDef ambiguous fill:#fee2e2,stroke:#dc2626,stroke-dasharray: 3 3
    classDef truncated fill:#f3f4f6,stroke:#9ca3af
    classDef cycle fill:#ede9fe,stroke:#7c3aed
```

Node label format: `"filename.ext\nfunction_name()"` — file on the first line, function on the second.

---

#### Part 2: Structured summary

Always include all eight sections. Use "None" for empty sections — never omit a section.

**Entry point**: `function_name()` in `path/to/file.ext`

**Call chain**: [Prose narrative — describe the flow in plain English. E.g.: "`process_order` validates the cart via `validate_cart`, then delegates payment to `charge()`, which calls the Stripe API synchronously. On success, the order record is persisted to PostgreSQL via the ORM."]

**Key files & their roles**:
| File | Role |
|---|---|
| `src/payments/checkout.py` | Entry point — orchestrates the order flow |
| `src/validators.py` | Validates cart contents before payment |
| `src/payment.py` | Handles Stripe integration |

**External dependencies**:
- `Stripe API` — HTTP POST — called from `payment.py::charge()`
- `PostgreSQL` — SQL INSERT — called from `checkout.py::process_order()` via ORM

**Side effects**:
- Database write: order record created in `orders` table
- Network call: Stripe charge initiated (synchronous)

**Ambiguities & truncations**:
- `[AMBIGUOUS]` `dynamic_handler()` in `checkout.py` — callee determined at runtime via DI container; cannot be statically resolved
- `[TRUNCATED]` `notification_service.send()` branch cut at depth 3 — may contain additional side effects

**Narrative**: [One paragraph summarising the full entry-to-exit flow, written for a developer who has never seen this code. Cover: what the function does, the key path through the call graph, what external systems are touched, and any important ambiguities or side effects to be aware of.]

---

### Blast radius section (when entry point is a function or class)

When the entry point is a function or class (not a file), add this additional section to the summary:

**Blast radius**:
- **Callers** (code that calls `<entry>`): [list each caller with file path]
- **Callees** (code `<entry>` delegates to): [list each callee with file path]
- **Impact statement**: Modifying `<entry>` is likely to affect: [caller list]

Search the codebase for direct callers of the entry point and include them. This is the pre-refactor scoping view.

### Focus question mode (when a second argument is provided)

When a focus question is provided (e.g., `/trace checkout.py "what external services does this touch?"`):

1. **Run the full trace** as normal — do not skip any step
2. **Before producing output**, identify which nodes and edges most directly answer the question:
   - "what external services does this touch?" → prioritise all `[EXTERNAL]` nodes
   - "what writes to the database?" → prioritise nodes with SQL/ORM side effects
   - "what could fail due to a network error?" → prioritise external HTTP calls
   - "what does this mutate?" → prioritise state mutation side effects
3. **Lead the output with a Focus Answer section**:

   **Focus Answer**: [1–3 sentences directly answering the question. E.g.: "This flow touches two external services: the Stripe API (HTTP POST from `payment.py::charge()`) and PostgreSQL (SQL INSERT from `checkout.py::process_order()`)."]

4. **In the structured summary**, list the most relevant items first in their sections (external deps, side effects, etc.) — do not remove other items, just reorder to foreground what the question asks about
5. **In the Mermaid diagram**, add a comment above relevant nodes (e.g., `%% answers focus question`) — the visual structure is not changed, but the comment aids orientation

The focus question narrows attention, not scope. The complete trace is always produced.

