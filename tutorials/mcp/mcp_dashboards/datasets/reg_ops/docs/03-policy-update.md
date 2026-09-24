# Policy update — gap → redlined draft

Of the four policies the scan marks as affected, only **one** needs a text
change in the demo: the **Business Continuity** policy. The smart action drafts
updated text with a redline for the policy owner.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'actorBkg': 'transparent', 'actorBorder': '#818cf8', 'actorTextColor': '#e5e7eb', 'signalColor': '#818cf8', 'signalTextColor': '#e5e7eb', 'labelTextColor': '#e5e7eb', 'labelBoxBkgColor': 'transparent', 'noteBkgColor': 'transparent', 'noteTextColor': '#e5e7eb', 'noteBorderColor': '#818cf8', 'textColor': '#e5e7eb', 'primaryTextColor': '#e5e7eb', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
sequenceDiagram
  autonumber
  participant Dash as Reg Ops dashboard
  participant Ops as Reg / Ops user
  participant KB as Policy manual
  participant Agent as Reg Ops agent
  participant Out as Redlined draft

  Note over Dash,Ops: Policy-changes queue
  Dash->>Ops: 1 policy requires change
  Ops->>Dash: Open policy manual
  Dash->>KB: Business Continuity policy
  Note over Ops,Dash: Today: opening the manual<br/>leaves the dashboard (see open issues)

  Ops->>Dash: return to Reg Ops dashboard
  Ops->>Dash: Draft updated policy text
  Dash->>Agent: produce redline vs current manual
  Agent->>Out: HTML / document with track-changes style markup
  Out-->>Ops: review redline

  Note over Ops,Out: Demo caveat — PDFs lose formatting;<br/>chat-supplied text may be cleaner for live demos
```

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'primaryTextColor': '#e5e7eb', 'secondaryTextColor': '#e5e7eb', 'tertiaryTextColor': '#e5e7eb', 'textColor': '#e5e7eb', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'titleColor': '#e5e7eb', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart TB
  AFF["4 policies affected"] --> SPLIT{"Change required?"}
  SPLIT -->|no · 3| AWARE["Awareness only<br/>Closed"]
  SPLIT -->|yes · 1| BC["Business Continuity"]
  BC --> OPEN["Open manual"]
  BC --> DRAFT["Draft updated policy text"]
  DRAFT --> RL["Redlined document"]
  RL --> REV["Owner review / publish"]

  style AFF fill:none,stroke:#fb923c,stroke-width:2px
  style BC fill:none,stroke:#fb923c,stroke-width:2px
  style DRAFT fill:none,stroke:#fbbf24,stroke-width:2px
  style RL fill:none,stroke:#fbbf24,stroke-width:2px
  style AWARE fill:none,stroke:#4ade80,stroke-width:2px
  style REV fill:none,stroke:#818cf8,stroke-width:2px
```

| | |
| --- | --- |
| **Source** | Policy manuals in knowledge base |
| **Demo policy** | Business Continuity |
| **Action** | Draft updated policy text → redline |
| **Format note** | PDF uploads did not preserve layout; prefer source text in chat for polished demos |

← [prev](./02-vendor-followup.md) · [index](./README.md) · [next →](./04-change-threading.md)
