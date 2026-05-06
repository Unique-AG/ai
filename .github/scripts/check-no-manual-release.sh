#!/usr/bin/env bash
set -euo pipefail

# Checks that a PR does not manually modify files owned by release-please:
#   - CHANGELOG.md in any package
#   - .release-please-manifest.json
#   - version = "..." lines in pyproject.toml
#
# Usage: check-no-manual-release.sh <base-sha> <head-sha>

BASE="${1:?Usage: $0 <base-sha> <head-sha>}"
HEAD="${2:?Usage: $0 <base-sha> <head-sha>}"

# Diff from the merge-base, not the base tip, so changes landed on the
# base branch (e.g. release-please merges) don't show up as if the PR
# author made them.
MERGE_BASE=$(git merge-base "$BASE" "$HEAD")
CHANGED=$(git diff --name-only "$MERGE_BASE" "$HEAD")
ERRORS=()

while IFS= read -r file; do
  if [[ "$file" == */CHANGELOG.md || "$file" == "CHANGELOG.md" ]]; then
    ERRORS+=("$file")
  fi
done <<< "$CHANGED"

if echo "$CHANGED" | grep -qx '.release-please-manifest.json'; then
  ERRORS+=(".release-please-manifest.json")
fi

TOMLS=$(echo "$CHANGED" | grep 'pyproject.toml$' || true)
for toml in $TOMLS; do
  if git diff "$MERGE_BASE" "$HEAD" -- "$toml" | grep -qE '^\+version = '; then
    ERRORS+=("$toml (version changed)")
  fi
done

if [[ ${#ERRORS[@]} -gt 0 ]]; then
  echo "::error::Manual version/changelog changes are not allowed — release-please manages these automatically."
  echo ""
  echo "The following files must not be changed in regular PRs:"
  for err in "${ERRORS[@]}"; do
    echo "  - $err"
  done
  exit 1
fi

echo "No forbidden version/changelog changes detected."
