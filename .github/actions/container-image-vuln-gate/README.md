# Container image vulnerability gate

Calls the live PR-label action, resolves the external runtime base from the Dockerfile, and scans the runtime base and a pre-built docker tar with one pinned Trivy database.

PRs fail only for fixable vulnerabilities introduced after the runtime base whose severity is in `fail_severity` (default `CRITICAL,HIGH`). Findings in `warn_severity` (default `MEDIUM`) that are not in the fail tier are annotated as warnings. Inherited and unfixable findings remain warnings. `security-exception` bypasses fail-tier blocking only.

Every run logs scan coverage (layers, OS and language package counts per image) and emits one `notice` annotation with the tiers, counts, and result.

Callers pass `fail_severity` and `warn_severity` to override the defaults for a single image.

`report_only: true` reports fail-tier findings as warnings instead of failing the pull request. Missing scans, coverage problems and invalid tiers still fail. This repo sets it on release-please PRs, so this input is not in the monorepo copy.

The Trivy vulnerability and Java databases are cached per UTC hour, with no fallback to older entries. Downloads try `mirror.gcr.io`, then `ghcr.io`, three times with backoff. When every attempt fails, the scan uses the cached database and emits a warning; it fails only when no cached database exists.

Base resolution supports stage aliases, global `ARG` defaults, and `docker_build_args`. Label API errors, unresolved variables, `scratch`, missing scan metadata, a base-layer mismatch, a final scan without packages, or a final image listing fewer packages than its base fail closed.

Logic in `*.mjs` is kept in sync with `Unique-AG/monorepo` `.github/actions/container-image-vuln-gate/`.

## Tests

```bash
node --test .github/actions/{container-image-vuln-gate,pull-request-labels}/*.test.mjs
```
