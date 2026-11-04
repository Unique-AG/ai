# Documentation

| Document | What it covers |
| --- | --- |
| [architecture.md](./architecture.md) | The framework as a whole: sources of truth, the generation pipeline, SQLite storage design, reuse boundaries, and an [Implementation Status](./architecture.md#implementation-status) table recording where the code differs from the design |
| [dashboard-build.md](./dashboard-build.md) | How Astro produces a script-free `live` artifact, how the three build modes relate, and how the dashboard stays reusable across datasets |
| [dom-contract.md](./dom-contract.md) | The `data-unique-*` attribute reference — how markup declares which tool feeds which element, and how hosts interpret it at runtime |

Package-level READMEs cover their own subject in more depth:

| Package | What it covers |
| --- | --- |
| [`helpers/python/`](../helpers/python/README.md) | Shared server machinery: settings, the SQLite repository, the Excel loader, error handling |
| [`helpers/astro/`](../helpers/astro/README.md) | The shared browser host: the DOM interpreter, MCP client, elicitation form, and `live-local` host |
| [`helpers/contracts/`](../helpers/contracts/README.md) | The TypeSpec → OpenAPI → Pydantic + Zod generation script and its reproducibility guarantees |
| [`datasets/account_review/astro/`](../datasets/account_review/astro/README.md) | The reference dashboard: build modes, commands, and what it owns |
| [`datasets/account_review/docs/`](../datasets/account_review/docs/README.md) | RM remediation use cases: visual process docs (Mermaid) for the six rule codes |

## Where to start

Reading `architecture.md` end to end gives the full picture, but for a specific
task the shorter path is usually:

- **Adding a dataset** — the [authoring workflow](./architecture.md#authoring-workflow),
  then `helpers/contracts/README.md` for generation and
  `helpers/python/README.md` for the server.
- **Changing the dashboard** — `dom-contract.md` for the attributes, then
  `dashboard-build.md` for what the build will and will not allow.
- **Deciding what to share** — [Reuse Boundaries](./architecture.md#reuse-boundaries),
  which explains why the browser side has a large shared package and the server
  side deliberately does not.
