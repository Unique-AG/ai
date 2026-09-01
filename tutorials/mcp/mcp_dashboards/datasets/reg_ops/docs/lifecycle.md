# Scan lifecycle & work status

Two independent axes on every finding: **what kind of gap** it is, and **where
the work sits**.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'primaryTextColor': '#e5e7eb', 'secondaryTextColor': '#e5e7eb', 'tertiaryTextColor': '#e5e7eb', 'textColor': '#e5e7eb', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'titleColor': '#e5e7eb', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart TB
  subgraph kind["Gap kind = what broke"]
    direction LR
    REG["Regulatory change<br/>notification in scope"]
    POL["Policy gap<br/>manual needs rewrite"]
    VEN["Vendor gap<br/>contract misaligned"]
  end

  subgraph work["Status = where the work sits"]
    direction LR
    NEW["Raised<br/>scan just flagged it"]
    DRAFT["Drafting<br/>agent producing notice / redline"]
    WAIT["Pending update<br/>waiting on vendor / owner"]
    DONE["Closed<br/>renegotiated / policy updated<br/>or no change required"]
  end

  style REG fill:none,stroke:#38bdf8,stroke-width:2px
  style POL fill:none,stroke:#fb923c,stroke-width:2px
  style VEN fill:none,stroke:#e879f9,stroke-width:2px
  style NEW fill:none,stroke:#818cf8,stroke-width:2px
  style DRAFT fill:none,stroke:#fbbf24,stroke-width:2px
  style WAIT fill:none,stroke:#fbbf24,stroke-width:2px
  style DONE fill:none,stroke:#4ade80,stroke-width:2px
```

## End-to-end scan

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'mainBkg': 'transparent', 'primaryTextColor': '#e5e7eb', 'secondaryTextColor': '#e5e7eb', 'tertiaryTextColor': '#e5e7eb', 'textColor': '#e5e7eb', 'labelTextColor': '#e5e7eb', 'lineColor': '#818cf8', 'titleColor': '#e5e7eb', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
stateDiagram-v2
  [*] --> Idle

  Idle --> Scanning: Rerun scan / new mail arrives
  Scanning --> Summarised: agent finishes (~10 min today)

  Summarised --> Raised: findings landed on dashboard

  Raised --> Drafting: Draft notice / Draft redline
  Drafting --> PendingUpdate: draft sent / under review
  Drafting --> Raised: user abandons draft

  PendingUpdate --> Closed: vendor replies / policy published
  Raised --> Closed: triage says no change required

  Closed --> [*]

  classDef scan fill:none,stroke:#818cf8,stroke-width:2px
  classDef draft fill:none,stroke:#fbbf24,stroke-width:2px
  classDef wait fill:none,stroke:#fbbf24,stroke-width:2px
  classDef ok fill:none,stroke:#4ade80,stroke-width:2px
  classDef raised fill:none,stroke:#38bdf8,stroke-width:2px

  class Scanning scan
  class Drafting draft
  class PendingUpdate wait
  class Closed ok
  class Raised,Summarised raised
```

## Typical path per workstream

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'primaryTextColor': '#e5e7eb', 'secondaryTextColor': '#e5e7eb', 'tertiaryTextColor': '#e5e7eb', 'textColor': '#e5e7eb', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'titleColor': '#e5e7eb', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart LR
  S["Scan"] --> R["6 reg changes"]
  R --> P["4 policies affected"]
  P --> P1["1 policy rewrite"]
  P --> P0["3 awareness only"]
  R --> V["5 vendor gaps"]
  V --> V1["Draft Outlook notices"]
  P1 --> P2["Draft redlined text"]
  V1 --> C1["Pending vendor"]
  P2 --> C2["Policy owner review"]
  P0 --> C0["Closed — no change"]

  style S fill:none,stroke:#818cf8,stroke-width:2px
  style R fill:none,stroke:#38bdf8,stroke-width:2px
  style P1 fill:none,stroke:#fb923c,stroke-width:2px
  style V fill:none,stroke:#e879f9,stroke-width:2px
  style V1 fill:none,stroke:#fbbf24,stroke-width:2px
  style P2 fill:none,stroke:#fbbf24,stroke-width:2px
  style C0 fill:none,stroke:#4ade80,stroke-width:2px
  style C1 fill:none,stroke:#fbbf24,stroke-width:2px
  style C2 fill:none,stroke:#fbbf24,stroke-width:2px
```

### Boundaries that matter

| Boundary | Meaning |
| --- | --- |
| **Affected vs needs change** | A policy can be *in scope* of a reg without requiring a text edit |
| **Vendor gap vs policy gap** | Same notification can open both queues independently |
| **Drafting vs Pending update** | Agent is still writing vs human is waiting on the counterparty |

← [index](./README.md)
