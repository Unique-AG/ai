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
CONFIG_KEYS=$(jq -c '[.packages | keys[]]' release-please-config.json)
ERRORS=()

changelog_package_in_config() {
  jq -ne --arg pkg "$1" --argjson keys "$CONFIG_KEYS" '$keys | index($pkg) != null' >/dev/null
}

while IFS= read -r file; do
  if [[ "$file" == */CHANGELOG.md || "$file" == "CHANGELOG.md" ]]; then
    if git cat-file -e "$MERGE_BASE:$file" 2>/dev/null; then
      pkg_root=$(dirname "$file")
      if git cat-file -e "$HEAD:$file" 2>/dev/null; then
        ERRORS+=("$file")
      elif changelog_package_in_config "$pkg_root"; then
        ERRORS+=("$file")
      fi
    fi
  fi
done <<< "$CHANGED"

# Adding a brand-new package to the manifest is an onboarding action (paired
# with release-please-config.json edits, which are not guarded). Only block
# changes that touch an EXISTING entry's version or remove an entry — those are
# the manual version edits release-please owns.
if echo "$CHANGED" | grep -qx '.release-please-manifest.json'; then
  BASE_MANIFEST=$(git show "$MERGE_BASE:.release-please-manifest.json" 2>/dev/null || echo '{}')
  HEAD_MANIFEST=$(git show "$HEAD:.release-please-manifest.json" 2>/dev/null || echo '{}')
  TOUCHED_EXISTING=$(jq -rn --argjson base "$BASE_MANIFEST" --argjson head "$HEAD_MANIFEST" --argjson config_keys "$CONFIG_KEYS" \
    '[$base | to_entries[]
      | select(($head[.key] // null) != .value)
      | select(
          .key as $k
          | if ($head[$k] // null) == null then
              ($config_keys | index($k) != null)
            else
              true
            end
        )
      | .key] | join(", ")')
  if [[ -n "$TOUCHED_EXISTING" ]]; then
    ERRORS+=(".release-please-manifest.json (modified/removed existing entries: $TOUCHED_EXISTING)")
  fi
fi

TOMLS=$(echo "$CHANGED" | grep 'pyproject.toml$' || true)
for toml in $TOMLS; do
  if ! git cat-file -e "$MERGE_BASE:$toml" 2>/dev/null; then
    continue
  fi
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
