#!/usr/bin/env bash
set -euo pipefail

# Arms the next stable release by pushing an empty `Release-As: YYYY.WW.0`
# commit to `main`. Release-please then rewrites its standing Release PR on
# `main` to target that version, so the PR always reflects the authoritative
# next CalVer (never a SemVer placeholder).
#
# Inputs (via flags):
#   --year-week YYYY.WW  Explicit target cycle (e.g. 2026.20). Optional.
#                        If omitted, compute-calver.sh derives it from the
#                        .release-please-manifest.json (manifest + 2 weeks,
#                        fallback: next even ISO week).
#   --remote NAME        Remote to push to. Default: origin.
#   --branch NAME        Branch to push to. Default: main.
#
# Idempotent: if a `Release-As: <version>` trailer is already present in
# unreleased main history, exits 0 without pushing.

REMOTE="origin"
BRANCH="main"
YEAR_WEEK=""

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

git fetch --no-tags "$REMOTE" "$BRANCH"
if git log "${REMOTE}/${BRANCH}" --grep "^Release-As: ${VERSION}$" \
      --fixed-strings -n 1 --format=%H | grep -q .; then
  echo "Release-As: ${VERSION} already present on ${REMOTE}/${BRANCH}; nothing to do."
  exit 0
fi

git commit --allow-empty \
  -m "chore: arm release ${VERSION}" \
  -m "Release-As: ${VERSION}"
git push "$REMOTE" "HEAD:${BRANCH}"

echo "Pushed Release-As: ${VERSION}. Release-please will update the ${BRANCH} Release PR on its next run."
