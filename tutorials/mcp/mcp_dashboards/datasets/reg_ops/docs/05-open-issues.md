# Open issues (asks for Data Science / platform)

Captured from the walkthrough — what blocks a polished Millennium demo today.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'primaryTextColor': '#e5e7eb', 'secondaryTextColor': '#e5e7eb', 'tertiaryTextColor': '#e5e7eb', 'textColor': '#e5e7eb', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'titleColor': '#e5e7eb', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart TB
  P["① Primary<br/>Scan latency ~10 min"]
  S["② Secondary<br/>Opening manuals / contracts<br/>overrides the dashboard"]
  T["③ Tertiary<br/>Iframe has no permanent home"]

  P --> DEMO["Live demo: send a 7th email<br/>and wait — too slow"]
  S --> NAV["Operator loses context;<br/>must re-open Reg Ops"]
  T --> HOST["Where does the HTML<br/>dashboard live long-term?"]

  style P fill:none,stroke:#f87171,stroke-width:2px
  style S fill:none,stroke:#fb923c,stroke-width:2px
  style T fill:none,stroke:#fbbf24,stroke-width:2px
  style DEMO fill:none,stroke:#f87171,stroke-width:2px
```

## ① Scan latency (~10 minutes)

Unlike the Trade Recon dashboard (auto-update), **Rerun scan** is a long agent
job. Ideal demo beat: drop a seventh regulatory email mid-session and watch the
dashboard refresh — currently impractical.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'mainBkg': 'transparent', 'primaryTextColor': '#e5e7eb', 'secondaryTextColor': '#e5e7eb', 'tertiaryTextColor': '#e5e7eb', 'textColor': '#e5e7eb', 'labelTextColor': '#e5e7eb', 'lineColor': '#818cf8', 'titleColor': '#e5e7eb', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
stateDiagram-v2
  [*] --> Seeded: 6 notifications pre-scanned
  Seeded --> Waiting: send 7th email / Rerun scan
  Waiting --> Waiting: ~10 minutes
  Waiting --> Updated: findings refresh

  classDef bad fill:none,stroke:#f87171,stroke-width:2px
  classDef ok fill:none,stroke:#4ade80,stroke-width:2px
  class Waiting bad
  class Updated ok
```

| Ask | Direction |
| --- | --- |
| Faster incremental scan | Re-score only new mail, not the full corpus |
| Demo mode | Pre-warm / stub the seventh notification |
| Progress UX | Show scan stage so the wait is narratable |

## ② Document open overrides the dashboard

Opening a policy manual or vendor contract navigates away from the Reg Ops HTML
surface. The operator must click back into the dashboard — breaks the “stay in
flow” story while drafting notices / redlines in parallel.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'primaryTextColor': '#e5e7eb', 'secondaryTextColor': '#e5e7eb', 'tertiaryTextColor': '#e5e7eb', 'textColor': '#e5e7eb', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'titleColor': '#e5e7eb', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart LR
  D["Reg Ops dashboard"] -->|Open policy / contract| DOC["Document viewer"]
  DOC -.->|context lost| D2["Re-open Reg Ops"]

  style D fill:none,stroke:#818cf8,stroke-width:2px
  style DOC fill:none,stroke:#fb923c,stroke-width:2px
  style D2 fill:none,stroke:#f87171,stroke-width:2px
```

| Ask | Direction |
| --- | --- |
| Side panel / split view | Keep dashboard mounted while previewing |
| New tab / drawer | Document open without replacing the host |
| Return deep-link | At minimum, one-click restore of scroll + filters |

## ③ Iframe permanent home

The current surface is an HTML dashboard embedded somewhere in the product. It
is unclear where the iframe should live as a first-class Reg Ops home (nav item,
agent workspace, chat side panel, etc.).

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'primaryTextColor': '#e5e7eb', 'secondaryTextColor': '#e5e7eb', 'tertiaryTextColor': '#e5e7eb', 'textColor': '#e5e7eb', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'titleColor': '#e5e7eb', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart TB
  Q["Where does Reg Ops live?"] --> A["Dedicated nav / workspace"]
  Q --> B["Agent chat side panel"]
  Q --> C["Shared dashboard host<br/>(same pattern as Trade Recon / account_review)"]

  style Q fill:none,stroke:#fbbf24,stroke-width:2px
  style C fill:none,stroke:#818cf8,stroke-width:2px
```

This repo’s direction for new dashboards is the Astro + MCP host pattern used by
[`account_review`](../../account_review/docs/README.md) — a natural candidate for
③ once the domain is modelled.

## Related demo notes (not blockers)

| Note | Detail |
| --- | --- |
| PDF formatting | Uploaded policy PDFs lost layout in the redline; prefer text-in-chat for demos |
| Extra policies | Unused manuals are intentional headroom for later scenarios |

← [prev](./04-change-threading.md) · [index](./README.md) · [glossary](./glossary.md)
