# Change threading — notification ↔ policy ↔ vendor

Below the work queues, the HTML dashboard lists each regulatory change with
links so the operator can **thread the needle** between the source email, the
impacted policy, and the impacted vendor — without leaving the change row.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'primaryTextColor': '#e5e7eb', 'secondaryTextColor': '#e5e7eb', 'tertiaryTextColor': '#e5e7eb', 'textColor': '#e5e7eb', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'titleColor': '#e5e7eb', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart LR
  EMAIL["Regulatory notification<br/>(source email)"]
  CHANGE["Change row"]
  POL["Policy impacted"]
  VEN["Vendor impacted"]
  FLAG["Policy change required?"]

  EMAIL --> CHANGE
  CHANGE --> POL & VEN & FLAG
  POL -.->|open| PM["Policy manual"]
  VEN -.->|open| VC["Vendor contract"]
  EMAIL -.->|open| RAW["Raw notification"]

  style EMAIL fill:none,stroke:#38bdf8,stroke-width:2px
  style CHANGE fill:none,stroke:#818cf8,stroke-width:2px
  style POL fill:none,stroke:#fb923c,stroke-width:2px
  style VEN fill:none,stroke:#e879f9,stroke-width:2px
  style FLAG fill:none,stroke:#fb923c,stroke-width:2px
```

## Filters

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'primaryTextColor': '#e5e7eb', 'secondaryTextColor': '#e5e7eb', 'tertiaryTextColor': '#e5e7eb', 'textColor': '#e5e7eb', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'titleColor': '#e5e7eb', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart TB
  ALL["All changes<br/>6"] --> VG["Changes → vendor gap<br/>5"]
  ALL --> PG["Changes → policy gap<br/>1"]
  ALL --> MAIL["Regulatory notifications<br/>source emails"]

  style ALL fill:none,stroke:#818cf8,stroke-width:2px
  style VG fill:none,stroke:#e879f9,stroke-width:2px
  style PG fill:none,stroke:#fb923c,stroke-width:2px
  style MAIL fill:none,stroke:#38bdf8,stroke-width:2px
```

These filters match the summary strip: five vendor-gap changes and one
policy-gap change are the same numbers called out at the top of the dashboard.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'actorBkg': 'transparent', 'actorBorder': '#818cf8', 'actorTextColor': '#e5e7eb', 'signalColor': '#818cf8', 'signalTextColor': '#e5e7eb', 'labelTextColor': '#e5e7eb', 'labelBoxBkgColor': 'transparent', 'noteBkgColor': 'transparent', 'noteTextColor': '#e5e7eb', 'noteBorderColor': '#818cf8', 'textColor': '#e5e7eb', 'primaryTextColor': '#e5e7eb', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
sequenceDiagram
  autonumber
  participant Ops as Reg / Ops user
  participant Dash as Change list
  participant Mail as Source email
  participant Pol as Policy link
  participant Ven as Vendor link

  Ops->>Dash: open All changes / filter
  alt inspect source
    Ops->>Dash: Regulatory notifications
    Dash->>Mail: show original email body
  else follow impact
    Ops->>Dash: pick a change row
    Dash-->>Ops: reg · policy · vendor · change-required?
    Ops->>Pol: open impacted policy
    Ops->>Ven: open impacted vendor
  end
```

| | |
| --- | --- |
| **Purpose** | Audit trail + navigation between artefacts for one regulatory delta |
| **Redundant path** | Vendor / policy also reachable from the queues above — links here are the alternate needle |
| **Source of truth for mail** | “Regulatory notifications” view pulls the direct email the agent scored |

← [prev](./03-policy-update.md) · [index](./README.md) · [next →](./05-open-issues.md)
