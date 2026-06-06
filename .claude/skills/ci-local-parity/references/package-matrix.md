# Package matrix reference

Source of truth: `.github/actions/get-packages-matrix/package_configuration.json`

## Typecheck mode per package

| Package dir | `typecheck_use_baseline` | `typecheck_require_zero_errors` | Local command |
|---|---|---|---|
| `unique_toolkit` | false | true | `uv run poe typecheck` |
| `unique_sdk` | false | true | `uv run poe typecheck` |
| `tool_packages/unique_skill_tool` | false | true | `uv run poe typecheck` |
| all others | true | false | `uv run poe ci-typecheck` |

**Strict** = no baseline, zero errors required → `poe typecheck`
**Baseline** = only new errors vs `origin/main` → `poe ci-typecheck`

## Package-specific test and install args

| Package | test_args | install_args (extras) |
|---|---|---|
| `unique_sdk` | `-m "not integration"` | — |
| `unique_toolkit` | — | `fastapi,monitoring` |
| all others | — | — |

For SDK test parity:
```bash
uv run poe test -- -m "not integration"
```

For toolkit, if extras are needed before tests or coverage:
```bash
uv sync --locked --inexact --extra fastapi --extra monitoring
```

## Python versions

- `unique_sdk`: Python 3.11
- all others: Python 3.12

## Coverage threshold

All packages: `min_coverage: 60` (diff-based, new/changed lines only in CI)

## Full package list and dirs

| id | dir |
|---|---|
| toolkit | `unique_toolkit` |
| sdk | `unique_sdk` |
| mcp | `unique_mcp` |
| orchestrator | `unique_orchestrator` |
| web_search | `tool_packages/unique_web_search` |
| swot | `tool_packages/unique_swot` |
| follow_up_questions | `postprocessors/unique_follow_up_questions` |
| stock_ticker | `postprocessors/unique_stock_ticker` |
| deep_research | `tool_packages/unique_deep_research` |
| internal_search | `tool_packages/unique_internal_search` |
| skill_tool | `tool_packages/unique_skill_tool` |
| quartr | `connectors/unique_quartr` |
| six | `connectors/unique_six` |
| search_proxy | `connectors/unique_search_proxy/unique_search_proxy_client` |
| search_proxy_core | `connectors/unique_search_proxy/unique_search_proxy_core` |
| search_proxy_sdk | `connectors/unique_search_proxy/unique_search_proxy_sdk` |

**Notes:**
- `unique_six` has no `[tool.poe.tasks]` block — call `uv run ruff check .`, `uv run pytest`, `uv run deptry .` directly.
- `unique_search_proxy` has basic Poe tasks but no `ci-typecheck` / `ci-coverage`.
