#!/usr/bin/env bash
set -euo pipefail

#
# Auto-resolve version conflicts on open PRs.
#
# When a PR merges to main and changes pyproject.toml/CHANGELOG.md,
# other open PRs that touched the same packages may develop conflicts
# in those files. If the ONLY conflicts are in version-related lines
# (pyproject.toml version field + CHANGELOG.md version headers), this
# script auto-resolves them by re-computing the correct version.
#
# Usage: auto-resolve-version-conflicts.sh [--dry-run]
#

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

# Explicit allowlist of packages published to PyPI. Not auto-discovered because
# the repo also contains tutorials/examples with pyproject.toml/CHANGELOG.md.
PUBLISHABLE_PACKAGES=(
  unique_sdk
  unique_toolkit
  unique_mcp
  unique_orchestrator
  tool_packages/unique_web_search
  tool_packages/unique_swot
  tool_packages/unique_deep_research
  tool_packages/unique_internal_search
  postprocessors/unique_follow_up_questions
  postprocessors/unique_stock_ticker
  connectors/unique_quartr
  connectors/unique_six
  connectors/unique_search_proxy
)

extract_version() {
  local file="$1"
  grep -E -m1 '^version[[:space:]]*=' "$file" | sed -E 's/^version[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/'
}

extract_version_from_ref() {
  local ref="$1"
  local path="$2"
  git show "$ref:$path" 2>/dev/null | grep -E -m1 '^version[[:space:]]*=' | sed -E 's/^version[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/'
}

parse_semver() {
  local ver="$1"
  echo "$ver" | awk -F. '{print $1, $2, $3}'
}

determine_bump_type() {
  local ancestor_ver="$1"
  local pr_ver="$2"

  read -r a_major a_minor a_patch <<< "$(parse_semver "$ancestor_ver")"
  read -r p_major p_minor p_patch <<< "$(parse_semver "$pr_ver")"

  if [[ "$p_major" -gt "$a_major" ]]; then
    echo "major"
  elif [[ "$p_minor" -gt "$a_minor" ]]; then
    echo "minor"
  elif [[ "$p_patch" -gt "$a_patch" ]]; then
    echo "patch"
  else
    echo "none"
  fi
}

apply_bump() {
  local base_ver="$1"
  local bump_type="$2"

  read -r major minor patch <<< "$(parse_semver "$base_ver")"

  case "$bump_type" in
    major) echo "$((major + 1)).0.0" ;;
    minor) echo "$major.$((minor + 1)).0" ;;
    patch) echo "$major.$minor.$((patch + 1))" ;;
    *) echo "$base_ver" ;;
  esac
}

# Expects changelog entries in Keep a Changelog format: ## [MAJOR.MINOR.PATCH] - YYYY-MM-DD
first_changelog_version() {
  local ref="$1"
  local path="$2"
  git show "$ref:$path" 2>/dev/null | grep -oE -m1 '## \[[0-9]+\.[0-9]+\.[0-9]+\]' | sed -E 's/## \[([0-9.]+)\]/\1/'
}

extract_new_changelog_entry() {
  local ancestor_ref="$1"
  local pr_ref="$2"
  local changelog_path="$3"

  local ancestor_first_version
  ancestor_first_version=$(first_changelog_version "$ancestor_ref" "$changelog_path")

  if [[ -z "$ancestor_first_version" ]]; then
    return
  fi

  local pr_changelog
  pr_changelog=$(git show "$pr_ref:$changelog_path")
  awk -v stop_ver="$ancestor_first_version" '
    /^## \[/ {
      if (index($0, "[" stop_ver "]") > 0) { exit }
      found=1
    }
    found { print }
  ' <<< "$pr_changelog"
}

resolve_pr() {
  local pr_number="$1"
  local pr_branch="$2"
  local pr_repo_owner="$3"

  echo "::group::Processing PR #$pr_number ($pr_branch)"

  if ! git rev-parse "origin/$pr_branch" &>/dev/null; then
    echo "Branch origin/$pr_branch not found — skipping"
    echo "::endgroup::"
    return 0
  fi

  local ancestor
  ancestor=$(git merge-base "origin/main" "origin/$pr_branch" 2>/dev/null) || { echo "No common ancestor — skipping"; echo "::endgroup::"; return 0; }

  # In-memory conflict detection via git merge-tree (no working tree changes).
  # --name-only provides a stable, machine-friendly list of conflicted file paths.
  local merge_output merge_exit
  merge_output=$(git merge-tree --write-tree --name-only "origin/$pr_branch" origin/main 2>/dev/null) && merge_exit=0 || merge_exit=$?

  if [[ $merge_exit -eq 0 ]]; then
    echo "No conflicts — skipping"
    echo "::endgroup::"
    return 0
  fi

  # Output: line 1 = tree OID, then conflicted file paths, then blank line + messages.
  # Extract only the file paths (between OID and first blank line).
  local conflicted_files
  conflicted_files=$(echo "$merge_output" | awk 'NR==1{next} /^$/{exit} {print}')

  if [[ -z "$conflicted_files" ]]; then
    echo "merge-tree indicated issues but no conflicted files listed — skipping"
    echo "::endgroup::"
    return 0
  fi

  local conflicting_packages=()
  local non_version_conflicts=false

  for file in $conflicted_files; do
    local is_version_file=false
    for pkg in "${PUBLISHABLE_PACKAGES[@]}"; do
      if [[ "$file" == "$pkg/pyproject.toml" || "$file" == "$pkg/CHANGELOG.md" ]]; then
        is_version_file=true
        if [[ ! " ${conflicting_packages[*]:-} " =~ " $pkg " ]]; then
          conflicting_packages+=("$pkg")
        fi
        break
      fi
    done
    if [[ "$is_version_file" == "false" ]]; then
      echo "Non-version conflict in: $file"
      non_version_conflicts=true
    fi
  done

  if [[ "$non_version_conflicts" == "true" ]]; then
    echo "Has non-version conflicts — skipping (developer must resolve manually)"
    echo "::endgroup::"
    return 0
  fi

  if [[ ${#conflicting_packages[@]} -eq 0 ]]; then
    echo "No version-related conflicts found — skipping"
    echo "::endgroup::"
    return 0
  fi

  echo "Version conflicts in: ${conflicting_packages[*]}"

  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would auto-resolve version conflicts for packages: ${conflicting_packages[*]}"
    echo "::endgroup::"
    return 0
  fi

  # Only now touch the working tree: checkout PR branch and merge main once
  git checkout "origin/$pr_branch" --detach -q
  git merge origin/main --no-commit --no-ff -q 2>/dev/null || true

  local version_summary=""

  for pkg in "${conflicting_packages[@]}"; do
    local pyproject="$pkg/pyproject.toml"
    local changelog="$pkg/CHANGELOG.md"

    local ancestor_ver main_ver pr_ver
    ancestor_ver=$(extract_version_from_ref "$ancestor" "$pyproject")
    main_ver=$(extract_version_from_ref "origin/main" "$pyproject")
    pr_ver=$(extract_version_from_ref "origin/$pr_branch" "$pyproject")

    if [[ -z "$ancestor_ver" || -z "$main_ver" || -z "$pr_ver" ]]; then
      echo "Cannot extract versions for $pkg — skipping"
      continue
    fi

    local bump_type
    bump_type=$(determine_bump_type "$ancestor_ver" "$pr_ver")

    if [[ "$bump_type" == "none" ]]; then
      echo "No version bump detected in $pkg — skipping"
      continue
    fi

    local new_ver
    new_ver=$(apply_bump "$main_ver" "$bump_type")

    echo "  $pkg: ancestor=$ancestor_ver, main=$main_ver, pr=$pr_ver ($bump_type) → $new_ver"
    version_summary+="| \`$pkg\` | $pr_ver | **$new_ver** | $bump_type |"$'\n'

    local new_entry
    new_entry=$(extract_new_changelog_entry "$ancestor" "origin/$pr_branch" "$changelog")

    # Resolve conflict markers in the working tree file (preserves auto-merged
    # changes like new dependencies from both sides).
    awk -v ver="$new_ver" '
      /^<<<<<<</ { in_conflict=1; printf "version = \"%s\"\n", ver; next }
      in_conflict && /^>>>>>>>/ { in_conflict=0; next }
      in_conflict { next }
      { print }
    ' "$pyproject" > "${pyproject}.tmp" && mv "${pyproject}.tmp" "$pyproject"

    if [[ -n "$new_entry" ]]; then
      local updated_entry
      updated_entry=$(echo "$new_entry" | sed -E "s/## \[[0-9]+\.[0-9]+\.[0-9]+\]/## [$new_ver]/")

      local main_changelog
      main_changelog=$(git show "origin/main:$changelog")
      local header
      header=$(awk '/^## \[/{exit} {print}' <<< "$main_changelog")
      local rest
      rest=$(awk '/^## \[/{found=1} found{print}' <<< "$main_changelog")

      {
        echo "$header"
        echo "$updated_entry"
        echo ""
        echo "$rest"
      } > "$changelog"
    else
      git show "origin/main:$changelog" > "$changelog"
    fi

    git add "$pyproject" "$changelog"
  done

  if git diff --name-only --diff-filter=U 2>/dev/null | grep -q .; then
    echo "Unresolved files remain after version resolution — aborting"
    git merge --abort 2>/dev/null || true
    git checkout - -q 2>/dev/null || true
    echo "::endgroup::"
    return 0
  fi

  if git diff --cached --quiet; then
    echo "No changes to commit after resolution"
    git merge --abort 2>/dev/null || true
    git checkout - -q 2>/dev/null || true
    echo "::endgroup::"
    return 0
  fi

  git commit -m "chore: auto-resolve version conflicts with main

Packages: ${conflicting_packages[*]}"

  if git push origin HEAD:"$pr_branch" 2>&1; then
    echo "Pushed resolved version conflicts to $pr_branch"
    if [[ -n "$version_summary" ]]; then
      gh pr comment "$pr_number" --body "$(cat <<COMMENT
🔄 **Auto-resolved version conflicts with \`main\`**

| Package | Was | Now | Bump |
|---------|-----|-----|------|
${version_summary}
Please pull the latest changes on your branch.
COMMENT
)" 2>/dev/null || echo "Warning: failed to post PR comment"
    fi
  else
    echo "Push failed (branch may have been updated) — queued for retry"
    FAILED_PUSHES+=("$pr_number $pr_branch")
  fi

  git checkout - -q 2>/dev/null || true
  echo "::endgroup::"
}

main() {
  echo "Checking open PRs for version-only conflicts..."

  local prs
  prs=$(gh pr list --state open --limit 200 --json number,headRefName,isCrossRepository --jq '.[] | select(.isCrossRepository == false) | "\(.number) \(.headRefName)"')

  if [[ -z "$prs" ]]; then
    echo "No open same-repo PRs found"
    exit 0
  fi

  echo "Fetching all remote branches..."
  git fetch origin

  FAILED_PUSHES=()

  while IFS=' ' read -r pr_number pr_branch; do
    resolve_pr "$pr_number" "$pr_branch" ""
  done <<< "$prs"

  if [[ ${#FAILED_PUSHES[@]} -gt 0 ]]; then
    echo ""
    echo "Retrying ${#FAILED_PUSHES[@]} failed push(es) after re-fetch..."
    git fetch origin

    local retries=("${FAILED_PUSHES[@]}")
    FAILED_PUSHES=()

    for entry in "${retries[@]}"; do
      IFS=' ' read -r pr_number pr_branch <<< "$entry"
      resolve_pr "$pr_number" "$pr_branch" ""
    done

    if [[ ${#FAILED_PUSHES[@]} -gt 0 ]]; then
      echo "Still failed after retry: ${FAILED_PUSHES[*]}"
    fi
  fi

  echo ""
  echo "Done. Processed $(echo "$prs" | wc -l | tr -d ' ') PRs."
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
