#!/usr/bin/env bash
set -euo pipefail

#
# release-cut.sh — Create a YYYY.CW.0 release for all publishable packages.
#
# Called by the release-cut workflow after the release branch has been created.
# Expects to be run from the repo root on the release branch.
#
# Usage: release-cut.sh <YEAR> <WEEK>
#
# What it does:
#   1. Sets version = "YYYY.CW.0" in every publishable package's pyproject.toml
#   2. Generates a changelog entry from conventional commits since each package's
#      last release tag (or the initial commit if no prior tag exists)
#   3. Prepends the entry to each package's CHANGELOG.md
#   4. Updates .release-please-manifest.json
#   5. Prints the list of tags to create (caller handles git tag/push)
#

YEAR="${1:?Usage: release-cut.sh <YEAR> <WEEK>}"
WEEK="${2:?Usage: release-cut.sh <YEAR> <WEEK>}"
VERSION="${YEAR}.${WEEK}.0"
TODAY=$(date +"%Y-%m-%d")

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

declare -A PACKAGES
PACKAGES=(
  ["unique-sdk"]="unique_sdk"
  ["unique-toolkit"]="unique_toolkit"
  ["unique-mcp"]="unique_mcp"
  ["unique-orchestrator"]="unique_orchestrator"
  ["unique-web-search"]="tool_packages/unique_web_search"
  ["unique-swot"]="tool_packages/unique_swot"
  ["unique-deep-research"]="tool_packages/unique_deep_research"
  ["unique-internal-search"]="tool_packages/unique_internal_search"
  ["unique-follow-up-questions"]="postprocessors/unique_follow_up_questions"
  ["unique-stock-ticker"]="postprocessors/unique_stock_ticker"
  ["unique-quartr"]="connectors/unique_quartr"
  ["unique-six"]="connectors/unique_six"
)

cd "$REPO_ROOT"

find_last_tag() {
  local component="$1"
  git tag --list "${component}-v*" --sort=-v:refname 2>/dev/null | head -1 || echo ""
}

generate_changelog_entry() {
  local component="$1"
  local dir="$2"
  local version="$3"
  local date="$4"

  local last_tag
  last_tag=$(find_last_tag "$component")

  local range
  if [[ -n "$last_tag" ]]; then
    range="${last_tag}..HEAD"
  else
    range="HEAD"
  fi

  local features="" fixes="" perf="" other=""

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue

    local subject="$line"

    if [[ "$subject" =~ ^feat(\(.*\))?:\ (.+) ]]; then
      local scope="${BASH_REMATCH[1]}"
      local msg="${BASH_REMATCH[2]}"
      scope="${scope#(}"
      scope="${scope%)}"
      if [[ -n "$scope" ]]; then
        features+=$'\n'"- **${scope}:** ${msg}"
      else
        features+=$'\n'"- ${msg}"
      fi
    elif [[ "$subject" =~ ^fix(\(.*\))?:\ (.+) ]]; then
      local scope="${BASH_REMATCH[1]}"
      local msg="${BASH_REMATCH[2]}"
      scope="${scope#(}"
      scope="${scope%)}"
      if [[ -n "$scope" ]]; then
        fixes+=$'\n'"- **${scope}:** ${msg}"
      else
        fixes+=$'\n'"- ${msg}"
      fi
    elif [[ "$subject" =~ ^perf(\(.*\))?:\ (.+) ]]; then
      local scope="${BASH_REMATCH[1]}"
      local msg="${BASH_REMATCH[2]}"
      scope="${scope#(}"
      scope="${scope%)}"
      if [[ -n "$scope" ]]; then
        perf+=$'\n'"- **${scope}:** ${msg}"
      else
        perf+=$'\n'"- ${msg}"
      fi
    elif [[ "$subject" =~ ^(refactor|chore|docs|test|ci|build|revert)(\(.*\))?:\ (.+) ]]; then
      : # hidden sections — skip
    else
      other+=$'\n'"- ${subject}"
    fi
  done < <(
    if [[ "$range" == "HEAD" ]]; then
      git log --format="%s" -- "$dir"
    else
      git log --format="%s" "$range" -- "$dir"
    fi
  )

  local entry="## [${version}] - ${date}"

  if [[ -n "$features" ]]; then
    entry+=$'\n\n'"### Features"
    entry+="$features"
  fi

  if [[ -n "$fixes" ]]; then
    entry+=$'\n\n'"### Bug Fixes"
    entry+="$fixes"
  fi

  if [[ -n "$perf" ]]; then
    entry+=$'\n\n'"### Performance"
    entry+="$perf"
  fi

  if [[ -z "$features" && -z "$fixes" && -z "$perf" ]]; then
    entry+=$'\n'"- Version aligned to ${version} release"
  fi

  echo "$entry"
}

prepend_changelog() {
  local changelog_file="$1"
  local entry="$2"

  if [[ ! -f "$changelog_file" ]]; then
    cat > "$changelog_file" <<HEADER
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

${entry}
HEADER
    return
  fi

  local header=""
  local body=""
  local in_header=true

  while IFS= read -r line; do
    if $in_header && [[ "$line" =~ ^##\  ]]; then
      in_header=false
    fi
    if $in_header; then
      header+="$line"$'\n'
    else
      body+="$line"$'\n'
    fi
  done < "$changelog_file"

  printf '%s\n%s\n\n%s' "$header" "$entry" "$body" > "$changelog_file"
}

update_version() {
  local pyproject="$1"
  local version="$2"
  sed -i.bak "s/^version = .*/version = \"${version}\"/" "$pyproject"
  rm -f "${pyproject}.bak"
}

echo "=== Release Cut: ${VERSION} ==="
echo ""

TAGS_TO_CREATE=()

for component in $(echo "${!PACKAGES[@]}" | tr ' ' '\n' | sort); do
  dir="${PACKAGES[$component]}"
  pyproject="${dir}/pyproject.toml"
  changelog="${dir}/CHANGELOG.md"

  echo "--- ${component} (${dir}) ---"

  if [[ ! -f "$pyproject" ]]; then
    echo "  SKIP: pyproject.toml not found"
    continue
  fi

  old_version=$(grep -E '^version = ' "$pyproject" | sed -E 's/version = "([^"]+)"/\1/')
  echo "  ${old_version} -> ${VERSION}"

  update_version "$pyproject" "$VERSION"

  entry=$(generate_changelog_entry "$component" "$dir" "$VERSION" "$TODAY")
  prepend_changelog "$changelog" "$entry"

  TAGS_TO_CREATE+=("${component}-v${VERSION}")
  echo ""
done

echo "--- Updating .release-please-manifest.json ---"
manifest="{}"
for component in $(echo "${!PACKAGES[@]}" | tr ' ' '\n' | sort); do
  dir="${PACKAGES[$component]}"
  manifest=$(echo "$manifest" | jq --arg dir "$dir" --arg ver "$VERSION" '. + {($dir): $ver}')
done
echo "$manifest" | jq '.' > .release-please-manifest.json
echo "  Written .release-please-manifest.json"

echo ""
echo "=== Tags to create ==="
for tag in "${TAGS_TO_CREATE[@]}"; do
  echo "  $tag"
done

echo ""
echo "TAGS=${TAGS_TO_CREATE[*]}" >> "${GITHUB_OUTPUT:-/dev/null}"
echo "VERSION=${VERSION}" >> "${GITHUB_OUTPUT:-/dev/null}"
