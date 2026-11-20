# `R-SUIT-REVIEW` — Suitability review due

🟠 → 🔴 · Illustrative · Prefer “ongoing suitability”, not strictly “annual”

Review cadence from CRM is falling due. The **background agent** raises with
enough lead time; **Unique Conduct** runs the questionnaire in chat after the RM
sees the card and initiates.

**Two agents:**

| Agent | Role |
| --- | --- |
| **Background agent** | Watches CRM last-completed + cadence → **creates the dashboard card**. Stops there. |
| **Unique Conduct** | Takes over **after the RM sees the card and initiates**. Runs the suitability questionnaire in **chat**, drafts any client ask, walks the RM through in-platform review + send. |

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'actorBkg': 'transparent', 'actorBorder': '#818cf8', 'actorTextColor': '#a3a3a3', 'signalColor': '#818cf8', 'signalTextColor': '#a3a3a3', 'labelTextColor': '#a3a3a3', 'labelBoxBkgColor': 'transparent', 'noteBkgColor': 'transparent', 'noteTextColor': '#a3a3a3', 'noteBorderColor': '#818cf8', 'textColor': '#a3a3a3', 'primaryTextColor': '#a3a3a3', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
sequenceDiagram
  autonumber
  participant BG as Background agent
  participant CRM as CRM
  participant Dash as RM dashboard
  participant RM as Relationship Manager
  participant UC as Unique Conduct<br/>(chat)
  participant Client as Client
  participant Comp as Compliance

  Note over BG,CRM: 🟠 Lead-time warning
  BG->>CRM: last-completed + cadence
  CRM-->>BG: review due soon
  BG->>Dash: raise R-SUIT-REVIEW card
  Note over BG,Dash: Background agent done — card only

  Note over Dash,UC: RM sees card first, then initiates
  Dash->>RM: card — "Suitability review due"
  RM->>RM: sees card on dashboard
  RM->>Dash: start action — Complete
  Note over Dash,UC: Unique Conduct takes over
  Dash->>UC: hand off case context
  UC->>CRM: pre-fill from profile / objectives / risk
  UC->>RM: run questionnaire in chat

  alt fresh client input needed
    Note over UC,Client: Pending update — in-platform send
    UC->>RM: elicit draft — questionnaire / missing answers
    RM->>UC: review + confirm send
    UC->>Client: deliver via Outlook
    Client-->>RM: answers
  else enough on file
    UC->>RM: summarise answers ready for the file
    UC->>RM: elicit draft — confirm completed review
    RM->>UC: review + confirm send
    UC->>Client: deliver via Outlook
  end

  Note over RM,Dash: Compliant 🟢
  RM->>Dash: file current → Compliant
  Dash -.-> Comp: available for oversight
```

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'primaryTextColor': '#a3a3a3', 'secondaryTextColor': '#a3a3a3', 'tertiaryTextColor': '#a3a3a3', 'textColor': '#a3a3a3', 'titleColor': '#a3a3a3', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart LR
  subgraph bg["Background agent"]
    CAD["CRM cadence"] --> WARN["🟠 Card on dashboard"]
  end

  WARN --> SEE["RM sees card"]
  SEE --> R["RM initiates Complete"]

  subgraph uc["Unique Conduct (chat)"]
    R --> Q["Questionnaire in chat<br/>pre-filled"]
    Q --> NEED{"Fresh input?"}
    NEED -->|yes| PEND["Pending update<br/>RM confirms send"]
    NEED -->|no| RUN["Summarise + RM<br/>confirms send"]
  end

  PEND & RUN --> OK["Compliant 🟢"]

  style WARN fill:none,stroke:#fb923c,stroke-width:2px
  style SEE fill:none,stroke:#fb923c,stroke-width:2px
  style R fill:none,stroke:#818cf8,stroke-width:2px
  style Q fill:none,stroke:#818cf8,stroke-width:2px
  style PEND fill:none,stroke:#fbbf24,stroke-width:2px
  style RUN fill:none,stroke:#fbbf24,stroke-width:2px
  style OK fill:none,stroke:#4ade80,stroke-width:2px
```

| | |
| --- | --- |
| **Source** | CRM |
| **Card creator** | Background agent |
| **Who starts the action** | **RM** after seeing the card |
| **Chat / questionnaire / send** | **Unique Conduct** (takes over after RM sees card & initiates) |
| **Send channel** | In-platform draft → confirm → Outlook to client |
| **Status path** | Remediation *or* Pending update → Compliant |
| **Why it matters** | Regulators → ongoing, needs-based reviews (Consumer Duty) |
| **Code** | `cases.json` → `suit-review` · `send_email` audience `client` |

← [prev](./03-suit-alloc.md) · [index](./README.md) · [next →](./05-reg-change.md)
