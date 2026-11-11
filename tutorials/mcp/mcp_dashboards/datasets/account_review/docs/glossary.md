# Glossary

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'primaryTextColor': '#a3a3a3', 'textColor': '#a3a3a3', 'lineColor': '#818cf8', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
mindmap
  root((RM remediation))
    Identity
      KYC
      CDD / EDD
      PEP
      Adverse media
      Sanctions
    Portfolio
      Suitability
      Mandate
        advisory
        discretionary
      Client categorisation
        retail
        professional
        elective-professional
    Wealth
      Source of Wealth
    Systems
      CRM
      Smart KYC
      Knowledge base
    Agents
      Background agent
      Unique Conduct
    Regulators
      FCA
      FINMA
      Consumer Duty
```

| Term | Meaning |
| --- | --- |
| **Background agent** | Raises remediation cards on the RM dashboard from watches / screening / KB — no chat, no outbound mail |
| **Unique Conduct** | Chat agent that takes over after the RM **sees the card** and initiates a smart action — organises context, drafts, confirms send |
| **KYC** | Know Your Customer — verify who the client is |
| **CDD / EDD** | Customer / Enhanced Due Diligence — standard vs deeper checks |
| **PEP** | Politically Exposed Person — higher scrutiny |
| **Adverse media** | Negative news from screening |
| **Sanctions** | Government lists — Compliance/FC only (not RM-adjudicated) |
| **Suitability** | Advice & investments fit needs, objectives, risk appetite |
| **Source of Wealth** | How overall wealth was generated |
| **Mandate** | Advisory = client approves moves · Discretionary = act within limits |
| **Client categorisation** | Retail / professional / elective-professional → products & protections |
| **FCA / FINMA** | UK / Swiss financial regulators |
| **Consumer Duty** | FCA good-outcomes duty → continuous, needs-based reviews |
| **CRM** | Customer relationship system |
| **Smart KYC** | Perpetual background screening / monitoring |

## Architecture note

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': 'transparent', 'secondaryColor': 'transparent', 'tertiaryColor': 'transparent', 'mainBkg': 'transparent', 'clusterBkg': 'transparent', 'clusterBorder': '#64748b', 'primaryTextColor': '#a3a3a3', 'secondaryTextColor': '#a3a3a3', 'tertiaryTextColor': '#a3a3a3', 'textColor': '#a3a3a3', 'titleColor': '#a3a3a3', 'nodeBorder': '#818cf8', 'lineColor': '#818cf8', 'edgeLabelBackground': 'transparent', 'fontFamily': 'ui-sans-serif, system-ui'}}}%%
flowchart LR
  BG["Background agent<br/>creates cards"] --> DASH["RM sees card<br/>on dashboard"]
  DASH -->|"RM initiates"| UC["Unique Conduct<br/>chat + actions"]
  ENG["One remediation engine"] --> DASH
  ENG --> CO["Compliance dashboard<br/>(separate workstream)"]

  style BG fill:none,stroke:#38bdf8,stroke-width:2px
  style UC fill:none,stroke:#818cf8,stroke-width:2px
  style DASH fill:none,stroke:#fb923c,stroke-width:2px
  style CO fill:none,stroke:#e879f9,stroke-width:2px
  style ENG fill:none,stroke:#38bdf8,stroke-width:2px
```

Demo data honesty: screening is background cadence; regs are Compliance-uploaded
into the knowledge base — not live regulator feeds.

← [index](./README.md)
