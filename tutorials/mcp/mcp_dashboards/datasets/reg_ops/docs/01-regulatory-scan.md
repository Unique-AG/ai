# Regulatory scan — notifications → policies → vendors

The agent evaluates three knowledge-base inputs in one pass, then lands a summary
on the dashboard.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'actorBkg': 'transparent', 'actorBorder': '#818cf8', 'actorTextColor': '#e5e7eb', 'signalColor': '#818cf8', 'signalTextColor': '#e5e7eb', 'labelTextColor': '#e5e7eb', 'labelBoxBkgColor': 'transparent', 'noteBkgColor': 'transparent', 'noteTextColor': '#e5e7eb', 'noteBorderColor': '#818cf8', 'textColor': '#e5e7eb', 'primaryTextColor': '#e5e7eb', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
sequenceDiagram
  autonumber
  participant Inbox as Regulatory inbox
  participant Agent as Reg Ops agent
  participant KB_P as Policy manuals KB
  participant KB_V as Vendor contracts KB
  participant Dash as Reg Ops dashboard
  participant Ops as Reg / Ops user

  Note over Inbox,KB_V: Seeded demo inputs
  Inbox-->>Agent: 6 notifications<br/>(SEC, FINRA, ESMA, …)
  KB_P-->>Agent: policy manuals<br/>(some in scope, some extras)
  KB_V-->>Agent: vendor contracts<br/>(most touch the new regs)

  Note over Agent,Dash: Single evaluation pass
  Agent->>Agent: score each notification
  Agent->>KB_P: which policies are affected?
  Agent->>KB_V: which contracts have gaps?
  Agent->>Dash: summary + work queues

  Note over Dash,Ops: Morning triage
  Dash->>Ops: 6 changes · 4 policies · 5 vendor gaps
  Ops->>Dash: open filters / take next-best action
```

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'primaryTextColor': '#e5e7eb', 'secondaryTextColor': '#e5e7eb', 'tertiaryTextColor': '#e5e7eb', 'textColor': '#e5e7eb', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'titleColor': '#e5e7eb', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart TB
  subgraph inputs["Knowledge-base inputs"]
    N["6 regulatory notifications"]
    P["Policy manuals<br/>(affected + extras for future demos)"]
    V["Vendor contracts"]
  end

  subgraph eval["Agent evaluation"]
    E1["Read notification"]
    E2["Map to policies"]
    E3["Map to vendor contracts"]
    E4["Decide: awareness vs change required"]
  end

  subgraph out["Dashboard summary"]
    O1["6 regulatory changes"]
    O2["4 policies affected<br/>→ 1 needs change"]
    O3["5 / 6 vendors<br/>to renegotiate"]
  end

  N --> E1 --> E2 --> E3 --> E4
  P --> E2
  V --> E3
  E4 --> O1 & O2 & O3

  style N fill:none,stroke:#38bdf8,stroke-width:2px
  style P fill:none,stroke:#fb923c,stroke-width:2px
  style V fill:none,stroke:#e879f9,stroke-width:2px
  style E4 fill:none,stroke:#818cf8,stroke-width:2px
  style O1 fill:none,stroke:#38bdf8,stroke-width:2px
  style O2 fill:none,stroke:#fb923c,stroke-width:2px
  style O3 fill:none,stroke:#e879f9,stroke-width:2px
```

| | |
| --- | --- |
| **Sources** | Regulatory inbox + policy KB + vendor-contract KB |
| **Trigger** | Initial load · **Rerun scan** · (ideal demo) new seventh email |
| **Output** | KPI strip + vendor queue + policy queue + change list |
| **Extras** | Extra policies intentionally unused today — room to grow the demo |

← [index](./README.md) · [lifecycle](./lifecycle.md) · [next →](./02-vendor-followup.md)
