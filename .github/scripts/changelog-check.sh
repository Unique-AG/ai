#!/usr/bin/env bash
set -euo pipefail

# Verifies that a PR touching user-visible code adds a client-facing changelog
# fragment under .changelog/unreleased/ (Changie schema, see .changie.yaml).
#
# Ported from `scripts/changelog-check.sh` in Unique-AG/monorepo; keep the
# validation logic in sync — fragments written here are copied verbatim into
# the monorepo by its "Release · Sync AI Versions" workflow and validated
# there again with the same rules.
#
# Env (all optional):
#   CHANGIE_CHECK_BASE_SHA  PR base sha  (default: merge-base with origin/main)
#   CHANGIE_CHECK_HEAD_SHA  PR head sha  (default: HEAD)
#   CHANGIE_CHECK_LABELS    comma-separated PR labels (`no-changelog` exempts)
#   CHANGIE_CHECK_BASE_REF  branch to diff against when base sha unset (default: main)

FRAGMENT_DIR=".changelog/unreleased/"
CHANGIE_CONFIG=".changie.yaml"
EXEMPTION_LABELS=(no-changelog)

# Paths that never require a fragment. A PR needs a fragment only when at least
# one changed file matches none of these globs (bash `[[ == ]]` pattern match).
EXCLUDED_GLOBS=(
  ".changelog/*"
  ".changie.yaml"
  "*.md"
  "*.MD"
  ".github/*"
  ".claude/*"
  ".pre-commit-config.yaml"
  ".gitignore"
  ".dockerignore"
  ".python-version"
  "*.code-workspace"
  "docs/*"
  "*/docs/*"
  "tutorials/*"
  "*/examples/*"
  "*/tests/*"
  "*/test/*"
  "*test_*.py"
  "*_test.py"
  "*conftest.py"
  "*uv.lock"
  "*poetry.lock"
  "*CHANGELOG.md"
  ".release-please-manifest.json"
  "release-please-config*.json"
  "*/deploy/helm-chart/*"
  "*/mkdocs.yaml"
  "mkdocs.yaml"
)

is_exempt() {
  local labels_csv=",${CHANGIE_CHECK_LABELS:-}," exempt
  for exempt in "${EXEMPTION_LABELS[@]}"; do
    [[ "$labels_csv" == *",${exempt},"* ]] && return 0
  done
  return 1
}

is_excluded_path() {
  local path="$1" glob
  for glob in "${EXCLUDED_GLOBS[@]}"; do
    [[ "$path" == $glob ]] && return 0
  done
  return 1
}

contains() {
  local needle="$1" haystack
  shift
  for haystack in "$@"; do
    [[ "$needle" == "$haystack" ]] && return 0
  done
  return 1
}

TICKET_PATTERN='^UN-[0-9]+$'

# Echoes the number of invalid entries; callers add it to their own error tally
# (avoids `local -n` namerefs, which macOS's bundled bash 3.2 doesn't support).
count_ticket_errors() {
  local file="$1" ticket="$2" entry count=0
  local -a entries=()

  [[ -z "$ticket" ]] && { echo 0; return; }

  IFS=',' read -ra entries <<< "$ticket"
  for entry in "${entries[@]}"; do
    entry="${entry#"${entry%%[![:space:]]*}"}"
    entry="${entry%"${entry##*[![:space:]]}"}"
    if [[ ! "$entry" =~ $TICKET_PATTERN ]]; then
      echo "changie-check: ${file}: custom.Ticket entry '${entry}' does not match ${TICKET_PATTERN}." >&2
      count=$((count + 1))
    fi
  done

  echo "$count"
}

validate_fragments() {
  local file line kind body area audience ticket errors=0
  local -a kinds=() areas=() audiences=() files=("$@")

  if ((${#files[@]} == 0)); then
    return 0
  fi

  if ! command -v yq &> /dev/null; then
    echo "changie-check: yq is not available on this runner, cannot validate fragment syntax." >&2
    return 1
  fi

  if [[ ! -f "$CHANGIE_CONFIG" ]]; then
    echo "changie-check: ${CHANGIE_CONFIG} not found, cannot validate fragment syntax." >&2
    return 1
  fi

  while IFS= read -r line; do kinds+=("$line"); done < <(yq -r '.kinds[].label' "$CHANGIE_CONFIG")
  while IFS= read -r line; do areas+=("$line"); done < <(yq -r '.components[]' "$CHANGIE_CONFIG")
  while IFS= read -r line; do audiences+=("$line"); done < <(yq -r '.custom[] | select(.key == "Audience") | .enumOptions[]' "$CHANGIE_CONFIG")

  for file in "${files[@]}"; do
    if ! yq eval '.' "$file" &> /dev/null; then
      echo "changie-check: ${file}: not valid YAML." >&2
      errors=$((errors + 1))
      continue
    fi

    kind="$(yq -r '.kind // ""' "$file")"
    body="$(yq -r '.body // ""' "$file")"
    area="$(yq -r '.component // ""' "$file")"
    audience="$(yq -r '.custom.Audience // ""' "$file")"
    ticket="$(yq -r '.custom.Ticket // ""' "$file")"

    if [[ -z "$body" ]]; then
      echo "changie-check: ${file}: missing body." >&2
      errors=$((errors + 1))
    fi
    if ! contains "$kind" "${kinds[@]}"; then
      echo "changie-check: ${file}: kind '${kind}' is not one of: ${kinds[*]}." >&2
      errors=$((errors + 1))
    fi
    if ! contains "$area" "${areas[@]}"; then
      echo "changie-check: ${file}: component '${area}' is not one of: ${areas[*]}." >&2
      errors=$((errors + 1))
    fi
    if ! contains "$audience" "${audiences[@]}"; then
      echo "changie-check: ${file}: custom.Audience '${audience}' is not one of: ${audiences[*]}." >&2
      errors=$((errors + 1))
    fi
    errors=$((errors + $(count_ticket_errors "$file" "$ticket")))
  done

  if ((errors > 0)); then
    return 1
  fi
  return 0
}

resolve_base_sha() {
  local base_ref="${CHANGIE_CHECK_BASE_REF:-main}"
  if [[ -n "${CHANGIE_CHECK_BASE_SHA:-}" ]]; then
    echo "$CHANGIE_CHECK_BASE_SHA"
    return
  fi
  git fetch --quiet origin "$base_ref" || true
  git merge-base HEAD "origin/${base_ref}"
}

resolve_head_sha() {
  if [[ -n "${CHANGIE_CHECK_HEAD_SHA:-}" ]]; then
    echo "$CHANGIE_CHECK_HEAD_SHA"
    return
  fi
  git rev-parse HEAD
}

main() {
  local base head requires_fragment=false has_fragment=false diff_output
  local -a changed_fragments=()

  base="$(resolve_base_sha)"
  head="$(resolve_head_sha)"

  if is_exempt; then
    echo "changie-check: Exempt via label."
    exit 0
  fi

  if ! diff_output="$(git diff --name-status --no-renames "${base}...${head}")"; then
    echo "changie-check: Failed to diff ${base}...${head}." >&2
    exit 1
  fi

  while IFS=$'\t' read -r status path rest; do
    [[ -z "$path" ]] && continue
    [[ -n "$rest" ]] && path="$rest"
    is_excluded_path "$path" || requires_fragment=true
    if [[ "$path" == "${FRAGMENT_DIR}"*.y*ml ]]; then
      [[ "$status" == A* ]] && has_fragment=true
      [[ "$status" == A* || "$status" == M* ]] && changed_fragments+=("$path")
    fi
  done <<< "$diff_output"

  if ((${#changed_fragments[@]} > 0)); then
    validate_fragments "${changed_fragments[@]}" || exit 1
  fi

  if ! "$requires_fragment"; then
    echo "changie-check: No changed file requires a changelog fragment."
    exit 0
  fi

  if "$has_fragment"; then
    echo "changie-check: A new changelog fragment was found."
    exit 0
  fi

  echo "changie-check: No changelog fragment found under ${FRAGMENT_DIR}. Run \`uv run poe changelog-new ...\` to add one (see .claude/skills/changelog-fragment/SKILL.md), or apply the \`no-changelog\` label if this change is not user-visible." >&2
  exit 1
}

main
