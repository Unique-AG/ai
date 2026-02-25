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
  grep -E '^version[[:space:]]*=' "$file" | head -1 | sed -E 's/^version[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/'
}

extract_version_from_ref() {
  local ref="$1"
  local path="$2"
  git show "$ref:$path" 2>/dev/null | grep -E '^version[[:space:]]*=' | head -1 | sed -E 's/^version[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/'
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

first_changelog_version() {
  local ref="$1"
  local path="$2"
  git show "$ref:$path" 2>/dev/null | grep -oE '## \[[0-9]+\.[0-9]+\.[0-9]+\]' | head -1 | sed -E 's/## \[([0-9.]+)\]/\1/'
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

  git show "$pr_ref:$changelog_path" | awk -v stop_ver="$ancestor_first_version" '
    /^## \[/ {
      if (index($0, "[" stop_ver "]") > 0) { exit }
      found=1
    }
    found { print }
  '
}

resolve_pr() {
  local pr_number="$1"
  local pr_branch="$2"
  local pr_repo_owner="$3"

  echo "::group::Processing PR #$pr_number ($pr_branch)"

  git fetch origin "$pr_branch" 2>/dev/null || { echo "Cannot fetch $pr_branch — skipping"; echo "::endgroup::"; return 0; }

  local ancestor
  ancestor=$(git merge-base "origin/main" "origin/$pr_branch" 2>/dev/null) || { echo "No common ancestor — skipping"; echo "::endgroup::"; return 0; }

  local conflicting_packages=()
  local non_version_conflicts=false

  git checkout "origin/$pr_branch" --detach -q 2>/dev/null
  if git merge origin/main --no-commit --no-ff -q 2>/dev/null; then
    git merge --abort 2>/dev/null || true
    git checkout - -q 2>/dev/null || true
    echo "No conflicts — skipping"
    echo "::endgroup::"
    return 0
  fi

  local conflicted_files
  conflicted_files=$(git diff --name-only --diff-filter=U 2>/dev/null || true)

  if [[ -z "$conflicted_files" ]]; then
    git merge --abort 2>/dev/null || true
    git checkout - -q 2>/dev/null || true
    echo "No conflicted files detected — skipping"
    echo "::endgroup::"
    return 0
  fi

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

  git merge --abort 2>/dev/null || true

  if [[ "$non_version_conflicts" == "true" ]]; then
    git checkout - -q 2>/dev/null || true
    echo "Has non-version conflicts — skipping (developer must resolve manually)"
    echo "::endgroup::"
    return 0
  fi

  if [[ ${#conflicting_packages[@]} -eq 0 ]]; then
    git checkout - -q 2>/dev/null || true
    echo "No version-related conflicts found — skipping"
    echo "::endgroup::"
    return 0
  fi

  echo "Version conflicts in: ${conflicting_packages[*]}"

  if [[ "$DRY_RUN" == "true" ]]; then
    git checkout - -q 2>/dev/null || true
    echo "[DRY RUN] Would auto-resolve version conflicts for packages: ${conflicting_packages[*]}"
    echo "::endgroup::"
    return 0
  fi

  git checkout "origin/$pr_branch" --detach -q

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

    local new_entry
    new_entry=$(extract_new_changelog_entry "$ancestor" "origin/$pr_branch" "$changelog")

    git merge origin/main --no-commit --no-ff -q 2>/dev/null || true

    git show "origin/main:$pyproject" > "$pyproject"
    sed -i -E "s/^(version[[:space:]]*=[[:space:]]*)\"[^\"]+\"/\1\"$new_ver\"/" "$pyproject"

    if [[ -n "$new_entry" ]]; then
      local updated_entry
      updated_entry=$(echo "$new_entry" | sed -E "s/## \[[0-9]+\.[0-9]+\.[0-9]+\]/## [$new_ver]/")

      local main_changelog
      main_changelog=$(git show "origin/main:$changelog")
      local header
      header=$(echo "$main_changelog" | awk '/^## \[/{exit} {print}')
      local rest
      rest=$(echo "$main_changelog" | awk '/^## \[/{found=1} found{print}')

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

  if git diff --cached --quiet; then
    echo "No changes to commit after resolution"
    git merge --abort 2>/dev/null || true
    git checkout - -q 2>/dev/null || true
    echo "::endgroup::"
    return 0
  fi

  git commit -m "chore: auto-resolve version conflicts with main

Packages: ${conflicting_packages[*]}"

  git push origin HEAD:"$pr_branch"
  echo "Pushed resolved version conflicts to $pr_branch"

  git checkout - -q 2>/dev/null || true
  echo "::endgroup::"
}

main() {
  echo "Checking open PRs for version-only conflicts..."

  local prs
  prs=$(gh pr list --state open --json number,headRefName,isCrossRepository --jq '.[] | select(.isCrossRepository == false) | "\(.number) \(.headRefName)"')

  if [[ -z "$prs" ]]; then
    echo "No open same-repo PRs found"
    exit 0
  fi

  local resolved_count=0
  local skipped_count=0

  while IFS=' ' read -r pr_number pr_branch; do
    if resolve_pr "$pr_number" "$pr_branch" ""; then
      resolved_count=$((resolved_count + 1))
    else
      skipped_count=$((skipped_count + 1))
    fi
  done <<< "$prs"

  echo ""
  echo "Done. Processed $(echo "$prs" | wc -l | tr -d ' ') PRs."
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
