# `R-SOW-REFRESH` — Source of Wealth re-assessment

🟠 → 🔴 · Illustrative · Ties into existing SoW product

A wealth event (e.g. large inbound transfer) does not match the SoW narrative on
file → enhanced due diligence before treating money as BAU. The **background
agent** raises the card; **Unique Conduct** runs the corroboration plan in chat
after the RM sees the card and initiates.

**Two agents:**

| Agent | Role |
| --- | --- |
| **Background agent** | Compares wealth event vs SoW on file → **creates the dashboard card**. Stops there. |
| **Unique Conduct** | Takes over **after the RM sees the card and initiates**. Organises the SoW plan in **chat**, corroborates (e.g. registry), drafts the document request, walks the RM through in-platform review + send. |

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'actorBkg': 'transparent', 'actorBorder': '#818cf8', 'actorTextColor': '#a3a3a3', 'signalColor': '#818cf8', 'signalTextColor': '#a3a3a3', 'labelTextColor': '#a3a3a3', 'labelBoxBkgColor': 'transparent', 'noteBkgColor': 'transparent', 'noteTextColor': '#a3a3a3', 'noteBorderColor': '#818cf8', 'textColor': '#a3a3a3', 'primaryTextColor': '#a3a3a3', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
sequenceDiagram
  autonumber
  participant BG as Background agent
  participant TX as Transaction / Client DB
  participant SoW as SoW narrative on file
  participant Dash as RM dashboard
  participant RM as Relationship Manager
  participant UC as Unique Conduct<br/>(chat)
  participant Reg as Corporate registry
  participant Client as Client

  Note over BG,SoW: Mismatch detected 🟠
  BG->>TX: new wealth event
  BG->>SoW: compare to recorded story
  SoW-->>BG: not covered (e.g. company sale)
  BG->>Dash: raise R-SOW-REFRESH card
  Note over BG,Dash: Background agent done — card only

  Note over Dash,UC: RM sees card first, then initiates
  Dash->>RM: card — "SoW re-assessment required"
  RM->>RM: sees card on dashboard
  RM->>Dash: start action — Assess
  Note over Dash,UC: Unique Conduct takes over
  Dash->>UC: hand off case context
  UC->>RM: organise SoW plan in chat
  UC->>Reg: verify event (sale, filing, …)
  Reg-->>UC: corroboration result

  Note over UC,Client: Pending update — in-platform send
  UC->>RM: elicit draft — sale agreement / completion statement
  RM->>UC: review + confirm send
  UC->>Client: deliver via Outlook
  Client-->>RM: evidence

  Note over RM,Dash: Compliant 🟢
  RM->>Dash: narrative updated → Compliant
```

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'primaryTextColor': '#a3a3a3', 'secondaryTextColor': '#a3a3a3', 'tertiaryTextColor': '#a3a3a3', 'textColor': '#a3a3a3', 'titleColor': '#a3a3a3', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart LR
  subgraph bg["Background agent"]
    EVT["Wealth event"] --> CMP{"Matches SoW<br/>on file?"}
    CMP -->|yes| BAU["Business as usual"]
    CMP -->|no| EDD["🟠 Card on dashboard"]
  end

  EDD --> SEE["RM sees card"]
  SEE --> R["RM initiates Assess"]

  subgraph uc["Unique Conduct (chat)"]
    R --> PLAN["SoW plan in chat<br/>+ corroborate"]
    PLAN --> DOCS["RM confirms send<br/>request docs"]
  end

  DOCS --> OK["Compliant 🟢"]

  style EDD fill:none,stroke:#fb923c,stroke-width:2px
  style SEE fill:none,stroke:#fb923c,stroke-width:2px
  style R fill:none,stroke:#818cf8,stroke-width:2px
  style PLAN fill:none,stroke:#818cf8,stroke-width:2px
  style DOCS fill:none,stroke:#fbbf24,stroke-width:2px
  style OK fill:none,stroke:#4ade80,stroke-width:2px
  style BAU fill:none,stroke:#4ade80,stroke-width:2px
```

| | |
| --- | --- |
| **Source** | Client DB / transactions |
| **Card creator** | Background agent |
| **Who starts the action** | **RM** after seeing the card |
| **Chat / SoW plan / send** | **Unique Conduct** (takes over after RM sees card & initiates) |
| **Send channel** | In-platform draft → confirm → Outlook to client |
| **Status path** | Remediation + Pending update → Compliant |
| **Why it matters** | KYC + SoW + ongoing remediation on one surface |
| **Code** | `cases.json` → `sow-refresh` · `send_email` audience `client` |

← [prev](./05-reg-change.md) · [index](./README.md) · [next →](./07-sof-check.md)
