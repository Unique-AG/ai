# Urgency vs work status

Two independent axes on every item.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'primaryTextColor': '#a3a3a3', 'secondaryTextColor': '#a3a3a3', 'tertiaryTextColor': '#a3a3a3', 'textColor': '#a3a3a3', 'titleColor': '#a3a3a3', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart TB
  subgraph urgency["Traffic-light = how urgent"]
    direction LR
    R["🔴 Red<br/>breach in effect<br/>~15d KYC window"]
    O["🟠 Orange<br/>~30d early warning<br/>value lives here"]
    G["🟢 Green<br/>picked up / done<br/>no RM action"]
  end

  subgraph work["Status = where the work sits"]
    direction LR
    P["Pending update<br/>waiting on client / system"]
    M["Remediation<br/>RM doing corrective work"]
    E["Escalated<br/>Compliance owns decision"]
    C["Compliant<br/>gap closed"]
  end

  style R fill:none,stroke:#f87171,stroke-width:2px
  style O fill:none,stroke:#fb923c,stroke-width:2px
  style G fill:none,stroke:#4ade80,stroke-width:2px
  style P fill:none,stroke:#fbbf24,stroke-width:2px
  style M fill:none,stroke:#818cf8,stroke-width:2px
  style E fill:none,stroke:#e879f9,stroke-width:2px
  style C fill:none,stroke:#4ade80,stroke-width:2px
```

## Who does what

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'primaryTextColor': '#a3a3a3', 'secondaryTextColor': '#a3a3a3', 'tertiaryTextColor': '#a3a3a3', 'textColor': '#a3a3a3', 'titleColor': '#a3a3a3', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart LR
  BG["Background agent<br/>creates card"] --> DASH["RM sees card<br/>on dashboard"]
  DASH -->|"RM initiates"| UC["Unique Conduct<br/>chat · draft · confirm send"]

  style BG fill:none,stroke:#38bdf8,stroke-width:2px
  style DASH fill:none,stroke:#fb923c,stroke-width:2px
  style UC fill:none,stroke:#818cf8,stroke-width:2px
```

## Status transitions

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'mainBkg': 'transparent', 'primaryTextColor': '#a3a3a3', 'secondaryTextColor': '#a3a3a3', 'tertiaryTextColor': '#a3a3a3', 'textColor': '#a3a3a3', 'labelTextColor': '#a3a3a3', 'titleColor': '#a3a3a3', 'lineColor': '#818cf8', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
stateDiagram-v2
  [*] --> Raised: background agent creates card

  Raised --> PendingUpdate: RM + Unique Conduct acted, waiting on others
  Raised --> Remediation: RM + Unique Conduct own corrective work
  Raised --> Escalated: Unique Conduct send → Compliance

  PendingUpdate --> Compliant: client / system responds
  Remediation --> Compliant: gap closed
  Remediation --> Escalated: RM can't adjudicate
  Escalated --> Compliant: Compliance resolves

  Compliant --> [*]

  classDef pending fill:none,stroke:#fbbf24,stroke-width:2px
  classDef rem fill:none,stroke:#818cf8,stroke-width:2px
  classDef esc fill:none,stroke:#e879f9,stroke-width:2px
  classDef ok fill:none,stroke:#4ade80,stroke-width:2px
  classDef raised fill:none,stroke:#38bdf8,stroke-width:2px

  class PendingUpdate pending
  class Remediation rem
  class Escalated esc
  class Compliant ok
  class Raised raised
```

## Typical path per use case

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'primaryTextColor': '#a3a3a3', 'secondaryTextColor': '#a3a3a3', 'tertiaryTextColor': '#a3a3a3', 'textColor': '#a3a3a3', 'titleColor': '#a3a3a3', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart LR
  D["R-DOC-EXPIRY"] --> D1["Pending update"] --> D2["Compliant"]
  A["R-SCR-ADVMEDIA"] --> A1["Escalated"]
  S["R-SUIT-ALLOC"] --> S1["Remediation"] --> S2["Compliant"]
  R["R-SUIT-REVIEW"] --> R1["Remediation<br/>or Pending"] --> R2["Compliant"]
  G["R-REG-CHANGE"] --> G1["Remediation"] --> G2["Compliant"]
  G1 -.->|can't qualify| G3["Escalated"]
  W["R-SOW-REFRESH"] --> W1["Remediation<br/>+ Pending"] --> W2["Compliant"]

  style D1 fill:none,stroke:#fbbf24,stroke-width:2px
  style D2 fill:none,stroke:#4ade80,stroke-width:2px
  style A1 fill:none,stroke:#e879f9,stroke-width:2px
  style S1 fill:none,stroke:#818cf8,stroke-width:2px
  style S2 fill:none,stroke:#4ade80,stroke-width:2px
  style R1 fill:none,stroke:#818cf8,stroke-width:2px
  style R2 fill:none,stroke:#4ade80,stroke-width:2px
  style G1 fill:none,stroke:#818cf8,stroke-width:2px
  style G2 fill:none,stroke:#4ade80,stroke-width:2px
  style G3 fill:none,stroke:#e879f9,stroke-width:2px
  style W1 fill:none,stroke:#818cf8,stroke-width:2px
  style W2 fill:none,stroke:#4ade80,stroke-width:2px
```

### Boundaries that matter

| Boundary | Meaning |
| --- | --- |
| **Background agent vs Unique Conduct** | Cards only vs chat + draft + in-platform send (after RM **sees the card** and initiates) |
| **Pending update vs Remediation** | Both open — but waiting on someone else vs RM doing the work |
| **Remediation vs Escalated** | Corrective **action** (RM) vs **decision** (Compliance) |

← [index](./README.md)
