#!/usr/bin/env bash
set -euo pipefail

FRAGMENT_DIR=".changelog/unreleased/"
CHANGIE_CONFIG=".changie.yaml"
# release-please Release PRs, dev-cut bump PRs and Dependabot bumps cannot author a fragment.
EXEMPTION_LABELS=(no-changelog "autorelease: pending" dev-version-bump dependencies)
BATCH_LABEL="changelog-batch"

EXCLUDED_GLOBS=(
  ".changelog/*"
  "*.md"
  "*.MD"
  ".github/*"
  ".claude/*"
  ".cursor/*"
  "docs/*"
  "*/docs/*"
  "tutorials/*"
  "mkdocs.yaml"
  ".pre-commit-config.yaml"
  "tests/*"
  "*/tests/*"
  "*test_*.py"
  "*_test.py"
  "*conftest.py"
  "*uv.lock"
)

is_exempt() {
  local labels_csv=",${CHANGIE_CHECK_LABELS:-}," exempt
  for exempt in "${EXEMPTION_LABELS[@]}"; do
    [[ "$labels_csv" == *",${exempt},"* ]] && return 0
  done
  return 1
}

is_changelog_batch_pr() {
  [[ ",${CHANGIE_CHECK_LABELS:-}," == *",${BATCH_LABEL},"* ]]
}

is_excluded_path() {
  local path="$1" glob
  for glob in "${EXCLUDED_GLOBS[@]}"; do
    # shellcheck disable=SC2053 # unquoted on purpose: $glob is a pattern
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
  if [[ -n "${CHANGIE_CHECK_BASE_SHA:-}" ]]; then
    echo "$CHANGIE_CHECK_BASE_SHA"
    return
  fi
  git fetch --quiet origin main || true
  git merge-base HEAD origin/main
}

resolve_head_sha() {
  if [[ -n "${CHANGIE_CHECK_HEAD_SHA:-}" ]]; then
    echo "$CHANGIE_CHECK_HEAD_SHA"
    return
  fi
  git rev-parse HEAD
}

# Echoes the blob SHA of $2 as it exists in commit $1, or nothing if that
# path doesn't exist there.
blob_hash_at() {
  local commit="$1" path="$2"
  git rev-parse --verify --quiet "${commit}:${path}" 2>/dev/null || true
}

# True when fragment $1 (pre-deletion blob $2) is the changelog-batch mirror
# PR's own byte-for-byte move into a version-numbered .changelog/<digits>/ dir.
is_archived_elsewhere() {
  local name="$1" blob="$2" i
  is_changelog_batch_pr || return 1
  [[ -z "$blob" ]] && return 1
  ((${#archived_fragment_names[@]} == 0)) && return 1
  for ((i = 0; i < ${#archived_fragment_names[@]}; i++)); do
    [[ "${archived_fragment_names[$i]}" == "$name" && "${archived_fragment_blobs[$i]}" == "$blob" ]] && return 0
  done
  return 1
}

# Echoes how many deleted or modified fragments (excluding archived ones) fail the
# shared changelog-fragment-guard.sh check.
count_replacement_guard_violations() {
  local path preimage_blob
  local -a guarded_paths=()

  for path in "${replaced_fragments[@]}"; do
    preimage_blob="$(blob_hash_at "$diff_base" "$path")"
    is_archived_elsewhere "$(basename "$path")" "$preimage_blob" || guarded_paths+=("$path")
  done

  if ((${#guarded_paths[@]} == 0)); then
    echo 0
    return
  fi

  if ./.github/scripts/changelog-fragment-guard.sh "${guarded_paths[@]}" --base-ref "${CHANGIE_CHECK_BASE_REF:-main}"; then
    echo 0
  else
    echo "${#guarded_paths[@]}"
  fi
}

main() {
  local base head diff_base requires_fragment=false has_fragment=false diff_output guard_violations
  local -a changed_fragments=() replaced_fragments=()
  local -a archived_fragment_names=() archived_fragment_blobs=()

  base="$(resolve_base_sha)"
  head="$(resolve_head_sha)"

  if ! diff_output="$(git diff --name-status --no-renames "${base}...${head}")"; then
    echo "changie-check: Failed to diff ${base}...${head}." >&2
    exit 1
  fi

  # The three-dot diff's actual preimage; $base can be ahead of the fork point.
  diff_base="$(git merge-base "$base" "$head")"

  while IFS=$'\t' read -r status path rest; do
    [[ -z "$path" ]] && continue
    [[ -n "$rest" ]] && path="$rest"
    is_excluded_path "$path" || requires_fragment=true
    if [[ "$path" == "${FRAGMENT_DIR}"*.y*ml ]]; then
      [[ "$status" == A* ]] && has_fragment=true
      [[ "$status" == A* || "$status" == M* ]] && changed_fragments+=("$path")
      [[ "$status" == D* || "$status" == M* ]] && replaced_fragments+=("$path")
    elif [[ "$status" == A* && "$path" =~ ^\.changelog/[0-9][^/]*/[^/]+\.ya?ml$ ]]; then
      archived_fragment_names+=("$(basename "$path")")
      archived_fragment_blobs+=("$(blob_hash_at "$head" "$path")")
    fi
  done <<< "$diff_output"

  # Runs ahead of the no-changelog exemption below — that label must never
  # let an unsafe fragment deletion or edit through.
  if ((${#replaced_fragments[@]} > 0)); then
    guard_violations="$(count_replacement_guard_violations)"
    ((guard_violations > 0)) && exit 1
  fi

  if is_exempt; then
    echo "changie-check: Exempt via label."
    exit 0
  fi

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

  echo "changie-check: No changelog fragment found under ${FRAGMENT_DIR}. Run \`changie new\` to add one, or apply the \`no-changelog\` label if this change does not need a changelog entry." >&2
  exit 1
}

main
