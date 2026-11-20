# `R-SCR-ADVMEDIA` — Adverse-media / PEP hit

🔴 · Illustrative · Also covers `R-SCR-PEP` in code

Overnight Smart KYC surfaces a news match or PEP change. The **background
agent** raises the card; the RM confirms the match and, via **Unique Conduct**,
hands the **decision** to Compliance with an in-platform escalation email.

**Two agents:**

| Agent | Role |
| --- | --- |
| **Background agent** | Screening cadence → **creates the dashboard card**. Stops there. |
| **Unique Conduct** | Takes over **after the RM sees the card and initiates**. Organises match context in **chat**, drafts the Compliance note, walks the RM through in-platform review + send. |

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'actorBkg': 'transparent', 'actorBorder': '#818cf8', 'actorTextColor': '#a3a3a3', 'signalColor': '#818cf8', 'signalTextColor': '#a3a3a3', 'labelTextColor': '#a3a3a3', 'labelBoxBkgColor': 'transparent', 'noteBkgColor': 'transparent', 'noteTextColor': '#a3a3a3', 'noteBorderColor': '#818cf8', 'textColor': '#a3a3a3', 'primaryTextColor': '#a3a3a3', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
sequenceDiagram
  autonumber
  participant BG as Background agent
  participant WC as WorldCheck / screen
  participant Dash as RM dashboard
  participant RM as Relationship Manager
  participant UC as Unique Conduct<br/>(chat)
  participant Comp as Compliance
  participant CDash as Compliance dashboard

  Note over BG,WC: Overnight cadence 🔴
  BG->>WC: background screen
  WC-->>BG: adverse-media / PEP hit
  BG->>Dash: raise R-SCR-ADVMEDIA card
  Note over BG,Dash: Background agent done — card only

  Note over Dash,UC: RM sees card first, then initiates
  Dash->>RM: card — match + identifiers
  RM->>RM: sees card on dashboard
  RM->>Dash: start action — Review
  Note over Dash,UC: Unique Conduct takes over
  Dash->>UC: hand off case context
  UC->>RM: organise match in chat<br/>(article vs identifiers)
  RM->>UC: confirm true match?
  opt client comment (ongoing matter)
    UC->>RM: capture client context in chat
  end

  Note over UC,CDash: Escalated — Compliance owns decision
  UC->>RM: elicit Compliance note
  RM->>UC: review + confirm send in-platform
  UC->>Comp: deliver escalation via Outlook
  Dash-->>RM: status → Escalated
  Comp->>CDash: item appears for resolution
```

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'primaryTextColor': '#a3a3a3', 'secondaryTextColor': '#a3a3a3', 'tertiaryTextColor': '#a3a3a3', 'textColor': '#a3a3a3', 'titleColor': '#a3a3a3', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart TB
  subgraph bg["Background agent"]
    HIT["🔴 Screening hit"] --> CARD["Card on dashboard"]
  end

  CARD --> SEE["RM sees card"]
  SEE --> R["RM initiates Review"]

  subgraph uc["Unique Conduct (chat)"]
    R --> CTX["Organise match in chat"]
    CTX --> ESC["RM confirms send<br/>→ Compliance"]
  end

  subgraph comp_lane["Compliance dashboard"]
    ESC -->|escalation email| DECIDE["Adjudicate"]
    DECIDE --> RESOLVE["Resolve / restrict"]
  end

  SANC["⛔ Sanctions"] -.->|not this card<br/>Compliance-only lane| comp_lane

  style HIT fill:none,stroke:#f87171,stroke-width:2px
  style CARD fill:none,stroke:#fb923c,stroke-width:2px
  style SEE fill:none,stroke:#fb923c,stroke-width:2px
  style R fill:none,stroke:#818cf8,stroke-width:2px
  style ESC fill:none,stroke:#e879f9,stroke-width:2px
  style DECIDE fill:none,stroke:#e879f9,stroke-width:2px
  style SANC fill:none,stroke:#f87171,stroke-width:2px,stroke-dasharray: 5 5
```

| | |
| --- | --- |
| **Source** | WorldCheck / Smart KYC |
| **Card creator** | Background agent |
| **Who starts the action** | **RM** after seeing the card |
| **Chat / escalate** | **Unique Conduct** (takes over after RM sees card & initiates) |
| **Send channel** | In-platform draft → confirm → Outlook to Compliance |
| **Status path** | Escalated |
| **Division of labour** | RM = client context · Compliance = decision |
| **Code** | `cases.json` → `adverse-media` · `send_email` audience `compliance` |

← [prev](./01-doc-expiry.md) · [index](./README.md) · [next →](./03-suit-alloc.md)
