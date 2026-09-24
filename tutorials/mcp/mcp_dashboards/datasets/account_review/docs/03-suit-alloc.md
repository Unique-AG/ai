# `R-SUIT-ALLOC` — Portfolio breaches risk profile

🔴 · Illustrative · Drift threshold is **bank-configurable**

Holdings drift past the mandate’s allocation band (e.g. equities 72% vs 60%
ceiling). Continuous suitability — catch and fix, don’t wait for the annual
review. The **background agent** raises the card; **Unique Conduct** builds the
rebalance path in chat after the RM sees the card and initiates.

**Two agents:**

| Agent | Role |
| --- | --- |
| **Background agent** | Compares holdings vs mandate + threshold → **creates the dashboard card**. Stops there. |
| **Unique Conduct** | Takes over **after the RM sees the card and initiates**. Organises the breach in **chat**, sketches the rebalancing proposal, drafts the client email, walks the RM through in-platform review + send. |

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'actorBkg': 'transparent', 'actorBorder': '#818cf8', 'actorTextColor': '#a3a3a3', 'signalColor': '#818cf8', 'signalTextColor': '#a3a3a3', 'labelTextColor': '#a3a3a3', 'labelBoxBkgColor': 'transparent', 'noteBkgColor': 'transparent', 'noteTextColor': '#a3a3a3', 'noteBorderColor': '#818cf8', 'textColor': '#a3a3a3', 'primaryTextColor': '#a3a3a3', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
sequenceDiagram
  autonumber
  participant BG as Background agent
  participant PF as Portfolio
  participant CFG as Bank threshold setting
  participant Dash as RM dashboard
  participant RM as Relationship Manager
  participant UC as Unique Conduct<br/>(chat)
  participant Client as Client

  Note over BG,CFG: Breach detection 🔴
  BG->>PF: compare holdings vs mandate band
  BG->>CFG: drift > tolerance? (1–2% … ~5%)
  CFG-->>BG: beyond threshold
  BG->>Dash: raise R-SUIT-ALLOC card
  Note over BG,Dash: Background agent done — card only

  Note over Dash,UC: RM sees card first, then initiates
  Dash->>RM: card — allocation breach
  RM->>RM: sees card on dashboard
  RM->>Dash: start action — Rebalance
  Note over Dash,UC: Unique Conduct takes over
  Dash->>UC: hand off case context
  UC->>RM: organise breach in chat<br/>+ rebalancing proposal
  opt chat loop
    RM->>UC: "what should I sell?"
    UC-->>RM: executable trim / redeploy
  end

  Note over UC,Client: Mandate-aware ask — in-platform send
  alt advisory mandate
    UC->>RM: elicit draft — share proposal, seek agreement
  else discretionary mandate
    UC->>RM: elicit draft — confirm action within limits
  end
  RM->>UC: review + confirm send in-platform
  UC->>Client: deliver via Outlook

  Note over RM,Dash: Compliant 🟢
  RM->>Dash: allocation back in band → Compliant
```

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'primaryTextColor': '#a3a3a3', 'secondaryTextColor': '#a3a3a3', 'tertiaryTextColor': '#a3a3a3', 'textColor': '#a3a3a3', 'titleColor': '#a3a3a3', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart LR
  subgraph bg["Background agent"]
    H["Holdings"] --> CMP{"vs mandate band<br/>+ threshold"}
    CMP -->|within| OK["🟢 ok"]
    CMP -->|beyond| BR["🔴 Card on dashboard"]
  end

  BR --> SEE["RM sees card"]
  SEE --> R["RM initiates Rebalance"]

  subgraph uc["Unique Conduct (chat)"]
    R --> PROP["Proposal in chat"]
    PROP --> ADV{"Mandate?"}
    ADV -->|advisory| ASK["RM confirms send<br/>proposal"]
    ADV -->|discretionary| ACT["RM confirms send<br/>confirm action"]
  end

  ASK & ACT --> DONE["Compliant"]

  style BR fill:none,stroke:#f87171,stroke-width:2px
  style SEE fill:none,stroke:#fb923c,stroke-width:2px
  style R fill:none,stroke:#818cf8,stroke-width:2px
  style PROP fill:none,stroke:#818cf8,stroke-width:2px
  style ASK fill:none,stroke:#fbbf24,stroke-width:2px
  style ACT fill:none,stroke:#fbbf24,stroke-width:2px
  style DONE fill:none,stroke:#4ade80,stroke-width:2px
  style OK fill:none,stroke:#4ade80,stroke-width:2px
```

| | |
| --- | --- |
| **Source** | Portfolio |
| **Card creator** | Background agent |
| **Who starts the action** | **RM** after seeing the card |
| **Chat / proposal / send** | **Unique Conduct** (takes over after RM sees card & initiates) |
| **Send channel** | In-platform draft → confirm → Outlook to client |
| **Status path** | Remediation → Compliant |
| **Open design** | Surface drift threshold in UI |
| **Code** | `cases.json` → `suit-alloc` · `send_email` audience `client` |

← [prev](./02-adverse-media.md) · [index](./README.md) · [next →](./04-suit-review.md)
