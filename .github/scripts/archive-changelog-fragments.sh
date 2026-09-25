#!/usr/bin/env bash
set -euo pipefail

# Archives the client-facing changelog fragments accumulated under
# .changelog/unreleased/ into .changelog/<version>/ (plus a rendered
# .changelog/<version>.md) after a stable release, and pushes the result
# to the base branch.
#
# This is the AI-repo counterpart of the monorepo's `changie batch`. It is
# purely housekeeping: the monorepo's sync workflow finds fragments per
# commit (`git log --diff-filter=A`), so it does not matter to it whether a
# fragment still lives in unreleased/ or has been moved here. What the
# archive buys us is a small unreleased/ directory and a per-release,
# customer-facing changelog for the AI packages themselves.
#
# The caller must be authenticated as the Release Workflow App (bypass
# actor on the `main-branch` ruleset) — see cd-release.yaml.
#
# Inputs (via flags):
#   --version VERSION   Release version to batch (e.g. 2026.36.0). Optional;
#                       defaults to unique_toolkit's entry in
#                       .release-please-manifest.json (lockstep versions).
#   --remote NAME       Remote to push to. Default: origin.
#   --branch NAME       Base branch to push to. Default: main.
#   --changie PATH      changie binary. Default: `changie` on PATH.
#
# Idempotent: exits 0 without pushing when unreleased/ has no fragments or
# when .changelog/<version>.md already exists.

REMOTE="origin"
BRANCH="main"
VERSION=""
CHANGIE="changie"
MAX_ATTEMPTS=5

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version) VERSION="$2"; shift 2 ;;
    --remote)  REMOTE="$2";  shift 2 ;;
    --branch)  BRANCH="$2";  shift 2 ;;
    --changie) CHANGIE="$2"; shift 2 ;;
    *) echo "::error::unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  VERSION="$(jq -r '.unique_toolkit // ""' .release-please-manifest.json)"
fi
if ! [[ "$VERSION" =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]+$ ]]; then
  echo "::error::invalid version '$VERSION' (expected YYYY.WW.P)" >&2
  exit 1
fi

if ! command -v "$CHANGIE" > /dev/null 2>&1; then
  echo "::error::changie binary '$CHANGIE' not found" >&2
  exit 1
fi

if ! git config user.email > /dev/null 2>&1; then
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
fi

has_fragments() {
  compgen -G ".changelog/unreleased/*.y*ml" > /dev/null
}

attempt=1
while true; do
  git fetch -q "$REMOTE" "$BRANCH"
  git reset -q --hard "${REMOTE}/${BRANCH}"

  if [[ -f ".changelog/${VERSION}.md" ]]; then
    echo "changelog-archive: .changelog/${VERSION}.md already exists on ${BRANCH}; nothing to do."
    exit 0
  fi
  if ! has_fragments; then
    echo "changelog-archive: no fragments under .changelog/unreleased/; nothing to do."
    exit 0
  fi

  "$CHANGIE" batch "$VERSION" --move-dir "$VERSION"
  git add -A .changelog
  if git diff --cached --quiet; then
    echo "changelog-archive: changie batch produced no changes; nothing to do."
    exit 0
  fi
  git commit -q -m "chore: archive changelog fragments for ${VERSION}" \
    -m "Client-facing fragments released with ${VERSION}, moved out of .changelog/unreleased/ by changie batch. The monorepo sync picks fragments up per commit, so this move does not affect the platform release notes."

  if git push -q "$REMOTE" "HEAD:${BRANCH}"; then
    echo "changelog-archive: pushed .changelog/${VERSION}.md and .changelog/${VERSION}/ to ${BRANCH}."
    exit 0
  fi

  if (( attempt >= MAX_ATTEMPTS )); then
    echo "::error::changelog-archive: push to ${BRANCH} rejected ${MAX_ATTEMPTS} times; giving up." >&2
    exit 1
  fi
  echo "changelog-archive: push rejected (attempt ${attempt}); refetching ${BRANCH} and retrying."
  attempt=$((attempt + 1))
  sleep 2
done
