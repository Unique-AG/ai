#!/usr/bin/env bash
set -euo pipefail

# Verifies commits introduced by a PR targeting release/* are backports from main.
#
# Cherry-picks create new SHAs, so we compare patch equivalence via `git cherry`
# rather than requiring identical commit hashes on main.
# Sign convention: `-` = patch exists on upstream (backport), `+` = release-only.
#
# Usage: check-release-lineage.sh <base-sha> <head-sha> [upstream-ref]
#   upstream-ref defaults to origin/main

BASE="${1:?Usage: $0 <base-sha> <head-sha> [upstream-ref]}"
HEAD="${2:?Usage: $0 <base-sha> <head-sha> [upstream-ref]}"
UPSTREAM="${3:-origin/main}"

if ! git rev-parse --verify "$UPSTREAM" >/dev/null 2>&1; then
  echo "::error::Upstream ref $UPSTREAM not found. Fetch main before running this script."
  exit 1
fi

MERGE_BASE=$(git merge-base "$BASE" "$HEAD")
mapfile -t COMMITS < <(git rev-list --reverse "$MERGE_BASE".."$HEAD")

if [[ ${#COMMITS[@]} -eq 0 ]]; then
  echo "No commits to check."
  exit 0
fi

CHERRY_LINES=$(git cherry -v "$UPSTREAM" "$HEAD")

is_allowlisted() {
  local sha="$1"
  local subject author email

  subject=$(git log -1 --format=%s "$sha")
  author=$(git log -1 --format=%an "$sha")
  email=$(git log -1 --format=%ae "$sha")

  if [[ "$author" == "release-please[bot]" ]]; then
    return 0
  fi

  if [[ "$email" == *"github-actions"* || "$email" == *"release-workflow"* ]]; then
    return 0
  fi

  if [[ "$subject" == chore:\ hotfix\ release/* ]]; then
    return 0
  fi
  if [[ "$subject" == chore:\ stable\ release\ * ]]; then
    return 0
  fi
  if [[ "$subject" == chore:\ arm\ release\ * ]]; then
    return 0
  fi
  if [[ "$subject" == chore\(release-please\):* ]]; then
    return 0
  fi
  if [[ "$subject" == chore\(release\):* ]]; then
    return 0
  fi

  return 1
}

ERRORS=()

for sha in "${COMMITS[@]}"; do
  short_sha=${sha:0:7}
  subject=$(git log -1 --format=%s "$sha")

  if is_allowlisted "$sha"; then
    echo "allowlisted: $short_sha $subject"
    continue
  fi

  if git merge-base --is-ancestor "$sha" "$UPSTREAM" 2>/dev/null; then
    echo "on-main: $short_sha $subject"
    continue
  fi

  cherry_line=$(printf '%s\n' "$CHERRY_LINES" | grep -E "^[+-] $sha " || true)

  if [[ -z "$cherry_line" ]]; then
    ERRORS+=("$short_sha $subject (not on $UPSTREAM and no patch-equivalence result)")
    continue
  fi

  if [[ "$cherry_line" == -* ]]; then
    echo "backport: $short_sha $subject"
    continue
  fi

  ERRORS+=("$short_sha $subject (patch not found on $UPSTREAM — cherry-pick from main or use release automation)")
done

if [[ ${#ERRORS[@]} -gt 0 ]]; then
  echo "::error::Release PR contains commits without a matching patch on main."
  echo ""
  echo "Merge hotfix PRs with Rebase and merge (squash collapses commits and breaks release-please changelogs)."
  echo "Each fix commit must be cherry-picked from main so release-please can attribute changelog entries."
  echo ""
  echo "Offending commits:"
  for err in "${ERRORS[@]}"; do
    echo "  - $err"
  done
  exit 1
fi

echo "All ${#COMMITS[@]} commit(s) are on main or patch-equivalent backports."
