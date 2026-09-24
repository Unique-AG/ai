# Vendor follow-up — next-best action → Outlook draft

Demo anchor: **Prime Custody** — performance instantiation methodology is
*referenced* in the contract but not attached, which is out of line with the
new guidance. Next-best action: draft a notice asking for the missing artefact.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'actorBkg': 'transparent', 'actorBorder': '#818cf8', 'actorTextColor': '#e5e7eb', 'signalColor': '#818cf8', 'signalTextColor': '#e5e7eb', 'labelTextColor': '#e5e7eb', 'labelBoxBkgColor': 'transparent', 'noteBkgColor': 'transparent', 'noteTextColor': '#e5e7eb', 'noteBorderColor': '#818cf8', 'textColor': '#e5e7eb', 'primaryTextColor': '#e5e7eb', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
sequenceDiagram
  autonumber
  participant Dash as Reg Ops dashboard
  participant Ops as Reg / Ops user
  participant Agent as Reg Ops agent
  participant OL as Outlook
  participant KB as Vendor contract
  participant Vendor as Prime Custody Partners

  Note over Dash,Ops: Next-best vendor follow-up
  Dash->>Ops: card — methodology referenced, not attached
  Ops->>Dash: Draft notice
  Dash->>Agent: kick off Outlook draft

  par while draft runs
    Ops->>Dash: Open contract
    Dash->>KB: show Prime Custody agreement
  and
    Agent->>OL: draft email to Prime Custody Partners
    OL-->>Ops: ready draft ("as part of our review… please provide…")
  end

  opt open drafted mail
    Ops->>OL: open via hyperlink
  end

  Note over Ops,Vendor: Pending update
  Ops->>Vendor: send notice
  Vendor-->>Ops: attach methodology / renegotiate terms
```

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'primaryTextColor': '#e5e7eb', 'secondaryTextColor': '#e5e7eb', 'tertiaryTextColor': '#e5e7eb', 'textColor': '#e5e7eb', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'titleColor': '#e5e7eb', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart LR
  GAP["Vendor gap card"] --> ACT{"Action"}
  ACT -->|Draft notice| DRAFT["Agent → Outlook draft"]
  ACT -->|Open contract| VIEW["Review agreement in-app"]
  DRAFT --> SEND["Human sends"]
  SEND --> WAIT["Pending vendor"]
  WAIT --> DONE["Closed / renegotiated"]

  style GAP fill:none,stroke:#e879f9,stroke-width:2px
  style DRAFT fill:none,stroke:#fbbf24,stroke-width:2px
  style VIEW fill:none,stroke:#818cf8,stroke-width:2px
  style WAIT fill:none,stroke:#fbbf24,stroke-width:2px
  style DONE fill:none,stroke:#4ade80,stroke-width:2px
```

### Demo flavour (Prime Custody)

| | |
| --- | --- |
| **Issue** | Performance instantiation methodology referenced but not attached |
| **Ask** | Provide the missing methodology / align with guidance |
| **Channel** | Outlook draft, openable via hyperlink while other work continues |
| **Repeatable** | Same draft-notice flow available for any regulatory change’s vendors |

← [prev](./01-regulatory-scan.md) · [index](./README.md) · [next →](./03-policy-update.md)
