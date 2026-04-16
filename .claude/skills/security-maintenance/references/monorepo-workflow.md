# Monorepo Security Workflow — Assistants Bundles

## Scope

Services under `python/assistants/bundles/` in `Unique-AG/monorepo`:
- **assistants-core** — `python/assistants/bundles/core/src/pyproject.toml`
- **agentic-table** — `python/assistants/bundles/agentic-table/pyproject.toml`
- **Shared Dockerfile** — `python/assistants/bundles/Dockerfile`

## Security scanning infrastructure

### Trivy (container image scanning)
- **Workflow**: `.github/workflows/uniqueai-security-scans.yaml` → calls `template-security-trivy-image-scan.yaml`
- **Schedule**: Daily
- **Severity**: `CRITICAL,HIGH`
- **Key setting**: `ignore-unfixed: true` — only flags CVEs with available Debian/upstream fixes
- **Output**: SARIF uploaded to GitHub security tab → https://github.com/Unique-AG/monorepo/security/code-scanning

### Renovate (dependency and base image updates)
- **Workflow**: `.github/workflows/platform-renovate-assistants-bundles.yaml`
- **Config**: `python/assistants/bundles/renovate-config.json`
- **Schedule**: Weekly (Saturday 3am CET)
- **Scope**: `python/assistants/bundles/**` — Dockerfiles + pyproject.toml/uv.lock
- **Major updates**: Disabled
- **Stability window**: 14 days
- **Vulnerability alerts**: Immediate (bypass stability window), labeled `security`

### Dependabot
- **Status**: Disabled for the monorepo. Do not rely on it.

## Listing open alerts

```bash
# All Trivy alerts for assistants bundles (core, agentic-table, shared Dockerfile)
gh api repos/Unique-AG/monorepo/code-scanning/alerts --paginate \
  --jq '.[] | select(.state=="open") | select(.most_recent_instance.location.path // "" | test("python/assistants/bundles/")) | "\(.number)\t\(.rule.security_severity_level)\t\(.rule.id)\t\(.most_recent_instance.location.path)"'
```

## Handling Renovate PRs

Renovate opens two kinds of PRs:

- **Dockerfile base image / tool image digest bumps** — these update SHA256 pins. Review and merge directly.
- **Python dependency bumps** (minor/patch) — these update `pyproject.toml` ranges and `uv.lock`. For routine updates, review and merge directly.

**For security vulnerability fixes**, do not just merge the Renovate PR. Instead, add the minimum safe version to `constraint-dependencies` in the service's `pyproject.toml`, then relock. This ensures the security floor survives future relocks and documents *why* the minimum version exists. Close the Renovate PR after your fix is merged.

This mirrors the ai repo principle: **never patch just the lockfile for security fixes — persist the floor in `constraint-dependencies`.**

## Classifying CVEs

Every CVE falls into one of three categories:

### 1. Python dependency CVE
**Indicator**: Alert path points to a Python file or package in `uv.lock`.
**Fix**: Add/bump `constraint-dependencies` in the service's `pyproject.toml`, then `uv lock --refresh`. Do not just patch the lockfile — the constraint documents the security reason and survives relocks.

```toml
# python/assistants/bundles/core/src/pyproject.toml
[tool.uv]
constraint-dependencies = [
    "langchain-core>=1.2.22",  # CVE-2026-34070
    "pillow>=12.2.0",          # CVE-2026-40192
]
```

If the vulnerable package uses an **exact pin** (e.g. `==1.2.5`), relax it to a range first (e.g. `>=1.2.22,<2`), otherwise the constraint cannot take effect.

**Note**: Unlike the ai repo, the monorepo does not use `exclude-newer`, so constraints take effect immediately without timestamp overrides.

### 2. OS-level CVE with fix available
**Indicator**: Trivy flags a Debian package (e.g. `openssl`, `libssl3`) and shows a `FixedVersion`.
**Fix options** (in order of preference):
1. **Update base image digest** — if a newer `python:3.12-slim-bookworm` image contains the fix, update the `@sha256:...` pin in the Dockerfile
2. **Explicit apt-get install** — if no rebuilt image exists yet, add the fixed package to the `apt-get install` block in the Dockerfile with a dated comment explaining why

```dockerfile
# CVE-YYYY-NNNNN: <package> explicitly installed because the base image
# predates the Debian fix (<version>). Remove once the base image is
# rebuilt with the patch (added YYYY-MM-DD).
RUN ... apt-get install ... <package> ...
```

To find base image dates, query Docker Hub:
```bash
curl -s "https://hub.docker.com/v2/repositories/library/python/tags?name=3.12-slim-bookworm&page_size=5" | python3 -c "
import json, sys
for t in json.load(sys.stdin)['results']:
    print(f\"{t['name']}  pushed {t['tag_last_pushed'][:10]}  digest {t['digest'][:20]}...\")
"
```

### 3. OS-level CVE without fix (assess and document)
**Indicator**: Trivy flags a Debian package but `FixedVersion` is empty.
**Action**: Assess real-world exploitability in the container context. Most are false positives.

Common container false positives:
| CVE pattern | Package | Why it's a false positive |
|---|---|---|
| MiniZip overflow | `zlib1g` | Affects MiniZip contrib, not the zlib library — MiniZip is not installed |
| `infocmp` buffer overflow | `ncurses-*` | Affects CLI tool; requires local access + user interaction |
| systemd IPC crash | `libsystemd0`, `libudev1` | Targets PID 1 systemd; containers don't run systemd |
| `memalign` overflow | `libc6`, `libc-bin` | Requires attacker-controlled alignment parameter; AC:H |
| SQLite integer overflow | `libsqlite3-0` | Requires arbitrary SQL execution against SQLite; service uses PostgreSQL |
| Kernel header CVEs | `linux-libc-dev` | Build-time headers only; kernel code doesn't run in the container |

**Do not migrate base images** to address unfixed CVEs unless they are genuinely exploitable. The CI scan uses `ignore-unfixed: true` which correctly filters these.

## Local validation

### Build the image
```bash
cd /path/to/monorepo
docker build -f python/assistants/bundles/Dockerfile \
  --build-arg BUNDLE=core \
  -t assistants-core-test:latest \
  python/
```

### Verify fixed versions inside the container
```bash
docker run --rm --entrypoint bash assistants-core-test:latest -c "
  openssl version
  python -c 'import PIL; print(PIL.__version__)'
  python -c 'import langchain_core; print(langchain_core.__version__)'
"
```

### Run Trivy locally (full scan, including unfixed)

Pin the Trivy image by digest. Update the digest periodically.

```bash
TRIVY_IMAGE=ghcr.io/aquasecurity/trivy:0.69.3@sha256:bcc376de8d77cfe086a917230e818dc9f8528e3c852f7b1aff648949b6258d1c

docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  $TRIVY_IMAGE image \
  --severity CRITICAL,HIGH \
  assistants-core-test:latest
```

To match CI behavior (only fixable CVEs):
```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  $TRIVY_IMAGE image \
  --severity CRITICAL,HIGH \
  --ignore-unfixed \
  assistants-core-test:latest
```
