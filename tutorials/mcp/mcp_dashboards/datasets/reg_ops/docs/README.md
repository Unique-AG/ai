# Reg Ops — Regulatory & Operations Agent

Visual guide to the Millennium demo agent that sits in the **regulatory /
operations** seat. Two buckets run in tandem:

1. **Regulatory Intelligence** — read regulator notifications, map them onto
   internal policy manuals, flag what must change.
2. **Third-party risk** — for those policy / regulatory deltas, find vendor
   contracts that now have gaps and need renegotiation.

**Idea:** one morning surface that turns an inbox of SEC / FINRA / ESMA mail into
next-best actions — draft vendor notices, redline policy text, and a threadable
trail from notification → policy → contract.

Stroke colors (no fills) — readable on light and dark. Label text is `#e5e7eb`
so it stays legible on dark previews.

| Role | Stroke |
| --- | --- |
| Regulatory change | `#38bdf8` |
| Policy gap / update | `#fb923c` |
| Vendor gap / renegotiation | `#e879f9` |
| Smart action (draft) | `#fbbf24` |
| Closed / no change needed | `#4ade80` |
| Scan / agent work | `#818cf8` |
| Demo blocker | `#f87171` |

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'primaryTextColor': '#e5e7eb', 'secondaryTextColor': '#e5e7eb', 'tertiaryTextColor': '#e5e7eb', 'textColor': '#e5e7eb', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'titleColor': '#e5e7eb', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart TB
  subgraph inputs["Inputs"]
    direction LR
    MAIL["Regulatory notifications<br/>SEC · FINRA · ESMA · …"]
    POL["Policy manuals<br/>knowledge base"]
    VEN["Vendor contracts<br/>knowledge base"]
  end

  subgraph agent["Reg Ops agent"]
    SCAN["Scan / evaluate"]
    MAP_P["Map → policies affected"]
    MAP_V["Map → vendor gaps"]
  end

  subgraph dash["Reg Ops dashboard"]
    SUM["Summary KPIs"]
    NBA["Next-best actions"]
    THREAD["Change thread<br/>reg ↔ policy ↔ vendor"]
  end

  subgraph actions["Smart actions"]
    DRAFT_V["Draft Outlook notice<br/>to vendor"]
    DRAFT_P["Draft redlined<br/>policy text"]
    OPEN["Open source doc<br/>contract / policy / email"]
  end

  MAIL & POL & VEN --> SCAN
  SCAN --> MAP_P & MAP_V
  MAP_P & MAP_V --> SUM & NBA & THREAD
  NBA --> DRAFT_V & DRAFT_P
  THREAD --> OPEN

  style MAIL fill:none,stroke:#38bdf8,stroke-width:2px
  style POL fill:none,stroke:#fb923c,stroke-width:2px
  style VEN fill:none,stroke:#e879f9,stroke-width:2px
  style SCAN fill:none,stroke:#818cf8,stroke-width:2px
  style SUM fill:none,stroke:#818cf8,stroke-width:2px
  style DRAFT_V fill:none,stroke:#fbbf24,stroke-width:2px
  style DRAFT_P fill:none,stroke:#fbbf24,stroke-width:2px
```

## Demo snapshot (seed numbers)

| Metric | Count | Note |
| --- | --- | --- |
| Regulatory changes | **6** | Notifications from SEC, FINRA, ESMA, etc. |
| Policies affected | **4** | Only **1** needs a text change |
| Vendor contracts to renegotiate | **5** / 6 | Gaps vs new guidance / policy |

## Docs map

| File | Focus |
| --- | --- |
| [lifecycle.md](./lifecycle.md) | Scan → triage → close; status model |
| [01-regulatory-scan.md](./01-regulatory-scan.md) | Inputs + agent evaluation pass |
| [02-vendor-followup.md](./02-vendor-followup.md) | Next-best action → draft Outlook notice |
| [03-policy-update.md](./03-policy-update.md) | Policy gap → redlined draft |
| [04-change-threading.md](./04-change-threading.md) | Filters + needle from email → docs |
| [05-open-issues.md](./05-open-issues.md) | Scan latency, doc navigation, iframe home |
| [glossary.md](./glossary.md) | Regulators, artefacts, seat |

## Dashboard regions (as demoed)

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'primaryTextColor': '#e5e7eb', 'secondaryTextColor': '#e5e7eb', 'tertiaryTextColor': '#e5e7eb', 'textColor': '#e5e7eb', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'titleColor': '#e5e7eb', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart TB
  subgraph top["Summary strip"]
    K1["6 reg changes"]
    K2["4 policies affected<br/>1 to change"]
    K3["5 / 6 vendors<br/>to renegotiate"]
  end

  subgraph mid["Work queues"]
    VQ["Next-best vendor follow-ups<br/>+ Draft notice · Open contract"]
    PQ["Policy changes<br/>+ Open manual · Draft redline"]
  end

  subgraph bot["Browse & filter"]
    F1["All changes"]
    F2["Vendor-gap changes"]
    F3["Policy-gap changes"]
    F4["Regulatory notifications<br/>(source emails)"]
  end

  top --> mid --> bot

  style K1 fill:none,stroke:#38bdf8,stroke-width:2px
  style K2 fill:none,stroke:#fb923c,stroke-width:2px
  style K3 fill:none,stroke:#e879f9,stroke-width:2px
  style VQ fill:none,stroke:#e879f9,stroke-width:2px
  style PQ fill:none,stroke:#fb923c,stroke-width:2px
```
