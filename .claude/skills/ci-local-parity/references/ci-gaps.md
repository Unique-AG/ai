# CI checks not fully reproducible via Poe

These jobs run in PR CI but cannot be replicated locally using `poe` tasks.
Call them out in any summary; never claim full parity.

## Dependency min-deps job (`ci-dependency-checks.yaml`)

CI installs with `--resolution lowest-direct`, reinstalls workspace packages
from source, then runs deptry and pytest in that environment.

`poe depcheck` only runs `deptry .` in the normal dev environment — it does not
test against minimum dependency versions.

To reproduce manually from the package dir:
```bash
uv venv --python 3.12
uv pip install -e . --resolution lowest-direct
# reinstall workspace packages from source (toolkit etc.)
uv pip install --no-deps -e "$REPO_ROOT/unique_toolkit"
# install dev tools from root
uv export --directory "$REPO_ROOT" --frozen --only-group dev --no-hashes | \
  uv pip install -r -
.venv/bin/deptry .
.venv/bin/pytest
```

## Config compatibility check (`ci-config-check.yaml`)

Exports `unique_toolkit._common.config_checker` defaults from the merge-base,
then validates the PR tip doesn't introduce breaking config changes.

Runs only on packages that have config checker support:
`toolkit`, `web_search`, `deep_research`, `swot`, `internal_search`,
`skill_tool`, `stock_ticker`, `follow_up_questions`, `six`.

No Poe equivalent; run manually from package dir if needed:
```bash
uv run python -m unique_toolkit._common.config_checker export --package . --output /tmp/base/
uv run python -m unique_toolkit._common.config_checker check \
  --artifacts /tmp/base/ --package . --report-defaults --fail-on-missing
```

## PR policy checks (CI-only governance)

- **PR title**: semantic PR title format validation (GitHub Action).
- **No-manual-release**: `bash .github/scripts/check-no-manual-release.sh <base_sha> <head_sha>`
- **Release-lineage** (PRs targeting `release/*` only): `git fetch origin main && bash .github/scripts/check-release-lineage.sh <base_sha> <head_sha> origin/main`
- **Gatekeeper**: aggregates all job statuses; posts commit status via `gh api`.

These are governance checks; they have no local Poe equivalent.
