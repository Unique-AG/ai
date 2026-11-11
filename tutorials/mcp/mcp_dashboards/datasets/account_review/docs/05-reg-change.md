# `R-REG-CHANGE` — Regulatory change (client in scope)

🔴 · Illustrative · Code also accepts legacy `R-REG-NONDOM`

Compliance uploads a rule; the **background agent** maps the book and flags
affected accounts with a **versioned rule reference** (audit trail).
**Unique Conduct** runs the reassessment in chat after the RM sees the card and initiates.

**Two agents:**

| Agent | Role |
| --- | --- |
| **Background agent** | Reads new KB version, maps in-scope clients → **creates per-account cards**. Stops there. |
| **Unique Conduct** | Takes over **after the RM sees the card and initiates**. Organises the gap summary in **chat**, drafts client or Compliance email, walks the RM through in-platform review + send. |

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'actorBkg': 'transparent', 'actorBorder': '#818cf8', 'actorTextColor': '#a3a3a3', 'signalColor': '#818cf8', 'signalTextColor': '#a3a3a3', 'labelTextColor': '#a3a3a3', 'labelBoxBkgColor': 'transparent', 'noteBkgColor': 'transparent', 'noteTextColor': '#a3a3a3', 'noteBorderColor': '#818cf8', 'textColor': '#a3a3a3', 'primaryTextColor': '#a3a3a3', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
sequenceDiagram
  autonumber
  participant Comp as Compliance
  participant KB as Knowledge base
  participant BG as Background agent
  participant Book as Client book
  participant Dash as RM dashboard
  participant RM as Relationship Manager
  participant UC as Unique Conduct<br/>(chat)
  participant Client as Client

  Note over Comp,Book: External change → client-specific to-do 🔴
  Comp->>KB: upload reg / policy (e.g. KB-REG-2026-07 v2)
  BG->>KB: read new version
  BG->>Book: map who is now in scope
  Book-->>BG: matching clients + versioned ref
  BG->>Dash: raise R-REG-CHANGE card per account
  Note over BG,Dash: Background agent done — card only

  Note over Dash,UC: RM sees card first, then initiates
  Dash->>RM: card — why in scope, which rule/version
  RM->>RM: sees card on dashboard
  RM->>Dash: start action — Email client / Escalate
  Note over Dash,UC: Unique Conduct takes over
  Dash->>UC: hand off case context
  UC->>RM: gap summary in chat<br/>+ pre-fill from CRM
  UC->>RM: risk warnings / categorisation notice

  alt client can qualify
    Note over UC,Client: Pending update — in-platform send
    UC->>RM: elicit draft — evidence / re-consent / choice
    RM->>UC: review + confirm send
    UC->>Client: deliver via Outlook
    Client-->>RM: evidence or acknowledgement
    RM->>Dash: re-paper / reclassify → Compliant 🟢
  else client can't qualify
    Note over UC,Comp: Remediation → Escalated
    RM->>Dash: restrict / unwind position
    UC->>RM: elicit Compliance hand-off note
    RM->>UC: review + confirm send in-platform
    UC->>Comp: deliver escalation via Outlook
  end
```

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'primaryTextColor': '#a3a3a3', 'secondaryTextColor': '#a3a3a3', 'tertiaryTextColor': '#a3a3a3', 'textColor': '#a3a3a3', 'titleColor': '#a3a3a3', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart TB
  subgraph bg["Background agent"]
    UP["Compliance uploads rule"] --> MAP["Map book"]
    MAP --> FLAG["🔴 Cards on dashboard<br/>+ versioned ref"]
  end

  FLAG --> SEE["RM sees card"]
  SEE --> R["RM initiates"]

  subgraph uc["Unique Conduct (chat)"]
    R --> GAP["Gap summary in chat"]
    GAP --> OPT{"Can client qualify?"}
    OPT -->|yes| RE["RM confirms send<br/>re-paper / ask client"]
    OPT -->|no| DIV["RM confirms send<br/>escalate to Compliance"]
  end

  RE --> OK["Compliant 🟢"]
  DIV --> ESC["Escalated"]

  style UP fill:none,stroke:#e879f9,stroke-width:2px
  style FLAG fill:none,stroke:#f87171,stroke-width:2px
  style SEE fill:none,stroke:#fb923c,stroke-width:2px
  style R fill:none,stroke:#818cf8,stroke-width:2px
  style GAP fill:none,stroke:#818cf8,stroke-width:2px
  style RE fill:none,stroke:#fbbf24,stroke-width:2px
  style DIV fill:none,stroke:#e879f9,stroke-width:2px
  style OK fill:none,stroke:#4ade80,stroke-width:2px
  style ESC fill:none,stroke:#e879f9,stroke-width:2px
```

| | |
| --- | --- |
| **Source** | Knowledge base (Compliance-loaded) — not live regulator feed |
| **Card creator** | Background agent |
| **Who starts the action** | **RM** after seeing the card |
| **Chat / reassess / send** | **Unique Conduct** (takes over after RM sees card & initiates) |
| **Send channel** | In-platform draft → confirm → Outlook (client or Compliance) |
| **Status path** | Remediation → Compliant, *or* → Escalated |
| **Example flavour** | Product eligibility / elective-professional (not abolished non-dom tax) |
| **Code** | `cases.json` → `reg-change` · dual action (email client / escalate) |

← [prev](./04-suit-review.md) · [index](./README.md) · [next →](./06-sow-refresh.md)
