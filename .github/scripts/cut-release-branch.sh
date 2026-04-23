#!/usr/bin/env bash
set -euo pipefail

# Creates `release/YYYY.WW` from the commit tagged with the sentinel
# release tag (`unique-toolkit-vYYYY.WW.0` by default). Intended to run
# right after release-please merges its Release PR on main.
#
# Inputs (via flags):
#   --version YYYY.WW.0   Explicit release version. If omitted, reads the
#                         highest CalVer value from
#                         .release-please-manifest.json (all 12 packages
#                         are in lockstep, so any value works).
#   --sentinel-pkg NAME   Component name whose tag pins the release commit.
#                         Default: unique-toolkit. Only relevant for tag
#                         lookup; all lockstep tags point at the same SHA.
#   --remote NAME         Remote to push to. Default: origin.
#
# Exits non-zero if the expected tag is missing or the target branch
# already exists on the remote.

REMOTE="origin"
VERSION=""
SENTINEL_PKG="unique-toolkit"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)       VERSION="$2";      shift 2 ;;
    --sentinel-pkg)  SENTINEL_PKG="$2"; shift 2 ;;
    --remote)        REMOTE="$2";       shift 2 ;;
    *) echo "::error::unknown argument: $1" >&2; exit 2 ;;
  esac
done

MANIFEST=".release-please-manifest.json"

if [[ -z "$VERSION" ]]; then
  if [[ ! -f "$MANIFEST" ]]; then
    echo "::error::$MANIFEST not found; pass --version explicitly" >&2
    exit 1
  fi
  VERSION=$(jq -r '.. | strings | select(test("^[0-9]{4}\\.[0-9]{2}\\.[0-9]+$"))' "$MANIFEST" \
            | sort -V | tail -n 1)
  if [[ -z "$VERSION" ]]; then
    echo "::error::no CalVer entries in $MANIFEST; pass --version explicitly" >&2
    exit 1
  fi
fi

if ! [[ "$VERSION" =~ ^[0-9]{4}\.[0-9]{2}\.0$ ]]; then
  echo "::error::expected stable YYYY.WW.0, got '$VERSION' — refusing to cut from a non-.0 version" >&2
  exit 1
fi

CYCLE="${VERSION%.0}"
BRANCH="release/${CYCLE}"
TAG="${SENTINEL_PKG}-v${VERSION}"

# This script runs in the `cut-and-arm` job of cd-release.yaml, which
# `needs:` the release-please job. That guarantees the sentinel tag has
# already been pushed by the time we get here, so a single fetch is
# enough — no polling or race-handling needed.
git fetch --quiet --tags "$REMOTE"
if ! git rev-parse --verify "refs/tags/${TAG}" >/dev/null 2>&1; then
  echo "::error::tag ${TAG} not found. Did release-please create the tag?" >&2
  exit 1
fi

SHA=$(git rev-list -n 1 "refs/tags/${TAG}")

if git ls-remote --heads "$REMOTE" "$BRANCH" | grep -q "$BRANCH"; then
  echo "::error::branch ${BRANCH} already exists on ${REMOTE}" >&2
  exit 1
fi

git push "$REMOTE" "${SHA}:refs/heads/${BRANCH}"
echo "Created ${BRANCH} at ${SHA} (tag ${TAG})"
