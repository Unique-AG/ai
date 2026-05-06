#!/usr/bin/env bash
set -euo pipefail

# Arms the next stable release by pushing an empty `Release-As: YYYY.WW.0`
# commit directly onto the base branch (default `main`). Once the commit
# lands, release-please rewrites its standing Release PR to target that
# version on the next workflow run.
#
# How the push works
# ==================
#   The caller is expected to authenticate `git`/`gh` as the Release
#   Workflow GitHub App, which is a bypass actor on `main-branch` and
#   `release-branches` rulesets. That makes the push to `main` legal and
#   makes the resulting commit's `push:` event fire other workflows
#   (GITHUB_TOKEN-authored pushes are blocked by GitHub's anti-recursion
#   rule). cd-release.yaml's global concurrency group serializes the
#   re-trigger behind any in-flight cd-release run.
#
# Race handling
# =============
#   Two arm runs aimed at the same `main` could race (e.g. concurrent
#   cd-release runs after a long-tailed PR merge). The script handles
#   that with a rebase+retry loop: if the push is rejected as
#   non-fast-forward, refetch the base branch, reset the working tree
#   to the new tip, recreate the empty commit, and try again. The
#   commit is empty so nothing else can conflict.
#
# Inputs (via flags):
#   --year-week YYYY.WW  Explicit target cycle (e.g. 2026.20). Optional.
#                        If omitted, compute-calver.sh derives it from the
#                        .release-please-manifest.json (manifest + 2 weeks,
#                        fallback: next even ISO week).
#   --remote NAME        Remote to push to. Default: origin.
#   --branch NAME        Base branch to push to. Default: main.
#
# Idempotent: exits 0 without pushing if the Release-As trailer is
# already on the base branch.

REMOTE="origin"
BRANCH="main"
YEAR_WEEK=""
MAX_ATTEMPTS=5

while [[ $# -gt 0 ]]; do
  case "$1" in
    --year-week) YEAR_WEEK="$2"; shift 2 ;;
    --remote)    REMOTE="$2";    shift 2 ;;
    --branch)    BRANCH="$2";    shift 2 ;;
    *) echo "::error::unknown argument: $1" >&2; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "$YEAR_WEEK" ]]; then
  YEAR_WEEK="$("$SCRIPT_DIR/compute-calver.sh")"
fi

if ! [[ "$YEAR_WEEK" =~ ^[0-9]{4}\.[0-9]{2}$ ]]; then
  echo "::error::invalid year-week '$YEAR_WEEK' (expected YYYY.WW)" >&2
  exit 1
fi

YEAR="${YEAR_WEEK%%.*}"
WEEK="${YEAR_WEEK##*.}"
if (( 10#$WEEK % 2 != 0 )); then
  echo "::error::week $WEEK is odd — releases use even-numbered weeks" >&2
  exit 1
fi

VERSION="${YEAR_WEEK}.0"
echo "Target release cycle: ${YEAR_WEEK} (version ${VERSION})"

if ! git config user.email >/dev/null 2>&1; then
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
fi

# Escape regex metachars in VERSION (dots) so the BRE below matches literally,
# while keeping `^`/`$` as line anchors. `--fixed-strings` can't be used here
# because it would also neuter the anchors and cause false positives for
# versions that share a numeric prefix (e.g. 2026.20.0 vs 2026.20.0.dev1).
ESCAPED_VERSION="${VERSION//./\\.}"

already_armed() {
  # Limit the idempotency scan to commits made after the latest release tag
  # so we don't walk the entire branch history on every run.
  local since_flag=()
  local last_tag_date
  last_tag_date=$(git log -1 --format=%aI \
    "$(git tag --list --sort=-version:refname 'unique-toolkit-v[0-9]*.[0-9]*.0' \
       | head -1)" 2>/dev/null || true)
  if [[ -n "$last_tag_date" ]]; then
    since_flag=(--since="$last_tag_date")
  fi

  git log "${REMOTE}/${BRANCH}" "${since_flag[@]}" \
        --grep "^Release-As: ${ESCAPED_VERSION}$" \
        -n 1 --format=%H | grep -q .
}

git fetch --no-tags "$REMOTE" "$BRANCH"

if already_armed; then
  echo "Release-As: ${VERSION} already present on ${REMOTE}/${BRANCH}; nothing to do."
  exit 0
fi

# Rebase+retry loop: anchor on the latest remote tip, build the empty
# commit, push. If the push is rejected because someone else advanced
# the branch in between, refetch, re-anchor, retry. Empty commit means
# there is never a real conflict to resolve — the only failure mode is
# the non-fast-forward race.
attempt=1
while (( attempt <= MAX_ATTEMPTS )); do
  echo "Attempt ${attempt}/${MAX_ATTEMPTS}: anchoring on ${REMOTE}/${BRANCH}"
  git fetch --no-tags "$REMOTE" "$BRANCH"
  git reset --hard "${REMOTE}/${BRANCH}"

  # Re-check after the fetch — another arm run could have landed
  # the same Release-As trailer between attempts.
  if already_armed; then
    echo "Release-As: ${VERSION} just landed on ${REMOTE}/${BRANCH}; nothing to do."
    exit 0
  fi

  git commit --allow-empty \
    -m "chore: arm release ${VERSION}" \
    -m "Release-As: ${VERSION}"

  if git push "$REMOTE" "HEAD:refs/heads/${BRANCH}"; then
    echo "Pushed Release-As: ${VERSION} to ${REMOTE}/${BRANCH}."
    echo "release-please will retarget the standing Release PR on the next cd-release run."
    exit 0
  fi

  # Push failed. Most likely cause: another commit landed on the base
  # branch between our fetch and our push (non-fast-forward). Back off
  # a couple seconds with jitter and try again.
  sleep_secs=$(( (RANDOM % 4) + 2 ))
  echo "::warning::Push to ${REMOTE}/${BRANCH} rejected; refetching and retrying in ${sleep_secs}s..."
  sleep "$sleep_secs"
  attempt=$(( attempt + 1 ))
done

echo "::error::Failed to push Release-As: ${VERSION} to ${REMOTE}/${BRANCH} after ${MAX_ATTEMPTS} attempts." >&2
exit 1
