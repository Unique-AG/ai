#!/usr/bin/env bash
# Gatekeeper decision for CI / Gatekeeper.
#
# Evaluates required job results. A config-check failure is non-blocking only
# when ALL of the following hold (fail closed otherwise):
#   1. PR targets main and is internal (not a fork)
#   2. PR has the config-check-override label
#   3. Current head SHA has an APPROVED review from a Unique-AG/ds-engels
#      member who is not the PR author (latest non-dismissed review per reviewer)
#   4. The only failing required check is config with actual failure
#      (cancelled / unavailable still blocks)
#
# Membership is probed via the Teams membership API using GITHUB_TOKEN.
# If membership cannot be verified, override is denied (fail closed).
# TODO(platform): if GITHUB_TOKEN cannot read org team membership in Actions
# (org "Read organization members" workflow permission), either enable that
# setting or provide a supported token — do not fall back to a static allowlist
# without an explicit Platform decision.
#
# Usage (CI): source env vars then run as a script. Writes status/description
# to $GITHUB_OUTPUT when set. Exit 0 always for the decision step; callers
# fail the job based on the status output.
#
# Env (job results — success|failure|cancelled|skipped|empty):
#   DETECT_CHANGES LINT TEST TYPES COVERAGE DEPS CONTAINERIZE HELM_LINT
#   CONFIG PR_TITLE NO_MANUAL_RELEASE RELEASE_LINEAGE
# Env (GitHub context):
#   GH_TOKEN / GITHUB_TOKEN, GITHUB_REPOSITORY
#   EVENT_NAME (pull_request|merge_group|...)
#   PR_NUMBER, PR_BASE_REF, PR_HEAD_SHA, PR_AUTHOR, PR_IS_FORK (true|false)
#   MERGE_GROUP_HEAD_REF (optional; used to recover PR number on merge_group)
# Optional:
#   OVERRIDE_LABEL (default: config-check-override)
#   DS_ENGELS_ORG / DS_ENGELS_TEAM (default: Unique-AG / ds-engels)
#   SKIP_AUDIT_COMMENT (default: false) — set true in unit tests

set -euo pipefail

OVERRIDE_LABEL="${OVERRIDE_LABEL:-config-check-override}"
DS_ENGELS_ORG="${DS_ENGELS_ORG:-Unique-AG}"
DS_ENGELS_TEAM="${DS_ENGELS_TEAM:-ds-engels}"
AUDIT_MARKER="<!-- config-check-override-audit -->"
SKIP_AUDIT_COMMENT="${SKIP_AUDIT_COMMENT:-false}"

REQUIRED_CHECKS=(
  "detect-changes:DETECT_CHANGES"
  "lint:LINT"
  "test:TEST"
  "types:TYPES"
  "coverage:COVERAGE"
  "deps:DEPS"
  "containerize:CONTAINERIZE"
  "helm-lint:HELM_LINT"
  "config:CONFIG"
  "pr-title:PR_TITLE"
  "no-manual-release:NO_MANUAL_RELEASE"
  "release-lineage:RELEASE_LINEAGE"
)

emit_result() {
  local status="$1"
  local description="$2"
  echo "status=${status}"
  echo "description=${description}"
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
      echo "status=${status}"
      echo "description=${description}"
    } >>"${GITHUB_OUTPUT}"
  fi
}

gh_api() {
  # Thin wrapper so tests can stub gh.
  gh api "$@"
}

print_status_summary() {
  echo "=== CI Status Summary ==="
  echo "detect-changes: ${DETECT_CHANGES:-}"
  echo "lint: ${LINT:-}"
  echo "test: ${TEST:-}"
  echo "types: ${TYPES:-}"
  echo "coverage: ${COVERAGE:-}"
  echo "deps: ${DEPS:-}"
  echo "containerize: ${CONTAINERIZE:-}"
  echo "helm-lint: ${HELM_LINT:-}"
  echo "config: ${CONFIG:-}"
  echo "pr-title: ${PR_TITLE:-}"
  echo "no-manual-release: ${NO_MANUAL_RELEASE:-}"
  echo "release-lineage: ${RELEASE_LINEAGE:-}"
  echo "========================="
}

# Collect blocking failures. Sets globals:
#   BLOCKING_FAILURES — space-separated "name:result" for non-config blocks
#   CONFIG_RESULT — config job result
#   HAS_NON_CONFIG_BLOCK — true|false
#   CONFIG_IS_FAILURE — true|false
#   CONFIG_IS_CANCELLED — true|false
classify_results() {
  BLOCKING_FAILURES=()
  CONFIG_RESULT="${CONFIG:-}"
  HAS_NON_CONFIG_BLOCK=false
  CONFIG_IS_FAILURE=false
  CONFIG_IS_CANCELLED=false

  local entry name var result
  for entry in "${REQUIRED_CHECKS[@]}"; do
    name="${entry%%:*}"
    var="${entry##*:}"
    result="${!var:-}"
    if [[ "$result" != "failure" && "$result" != "cancelled" ]]; then
      continue
    fi
    if [[ "$name" == "config" ]]; then
      if [[ "$result" == "failure" ]]; then
        CONFIG_IS_FAILURE=true
      else
        CONFIG_IS_CANCELLED=true
      fi
      echo "❌ $name: $result"
      continue
    fi
    echo "❌ $name: $result"
    BLOCKING_FAILURES+=("${name}:${result}")
    HAS_NON_CONFIG_BLOCK=true
  done
}

is_team_member() {
  # Returns 0 if username is an active member of DS_ENGELS_ORG/DS_ENGELS_TEAM.
  # Non-zero on non-member or any API/permission error (fail closed).
  local username="$1"
  local http_body http_code
  local tmp
  tmp="$(mktemp)"
  # Capture body + status; membership endpoint 404s for non-members.
  set +e
  http_body="$(gh_api \
    -H "Accept: application/vnd.github+json" \
    "orgs/${DS_ENGELS_ORG}/teams/${DS_ENGELS_TEAM}/memberships/${username}" \
    2>"${tmp}.err")"
  http_code=$?
  set -e

  if [[ "$http_code" -ne 0 ]]; then
    local err
    err="$(cat "${tmp}.err" 2>/dev/null || true)"
    rm -f "$tmp" "${tmp}.err"
    # Distinguish "not a member" (404) from auth/permission failures.
    if echo "$err" | grep -qiE '404|Not Found'; then
      echo "membership: ${username} is not in ${DS_ENGELS_ORG}/${DS_ENGELS_TEAM}" >&2
      return 1
    fi
    echo "membership API error for ${username}: ${err:-unknown}" >&2
    echo "MEMBERSHIP_API_FAILED=1" >&2
    return 2
  fi
  rm -f "$tmp" "${tmp}.err"

  local state
  state="$(echo "$http_body" | jq -r '.state // empty')"
  if [[ "$state" == "active" ]]; then
    return 0
  fi
  echo "membership: ${username} state=${state:-empty} (need active)" >&2
  return 1
}

resolve_pr_number() {
  # Prefer explicit PR_NUMBER; on merge_group parse head_ref .../pr-N-...
  if [[ -n "${PR_NUMBER:-}" ]]; then
    echo "$PR_NUMBER"
    return 0
  fi
  local head_ref="${MERGE_GROUP_HEAD_REF:-}"
  if [[ "$head_ref" =~ pr-([0-9]+) ]]; then
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  return 1
}

fetch_pr_json() {
  local pr_number="$1"
  local repo="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
  gh_api "repos/${repo}/pulls/${pr_number}"
}

pr_has_override_label() {
  local pr_json="$1"
  echo "$pr_json" | jq -e --arg label "$OVERRIDE_LABEL" \
    '[.labels[].name] | index($label) != null' >/dev/null
}

# Find a current DS-Engels approval for head_sha, not from author.
# Prints "login" of the first matching approver on success.
# Exit 1 = no valid approver; exit 2 = membership API failure.
find_ds_engels_approver() {
  local pr_number="$1"
  local head_sha="$2"
  local author="$3"
  local repo="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
  local reviews
  reviews="$(gh_api "repos/${repo}/pulls/${pr_number}/reviews")"

  # Latest non-dismissed review per user (array order is chronological).
  local candidates
  candidates="$(echo "$reviews" | jq -r --arg sha "$head_sha" --arg author "$author" '
    map(select(.state != "DISMISSED" and .user.login != null))
    | group_by(.user.login)
    | map(sort_by(.submitted_at // .id) | last)
    | map(select(
        .state == "APPROVED"
        and (.commit_id // "") == $sha
        and .user.login != $author
      ))
    | .[].user.login
  ')"

  if [[ -z "$candidates" ]]; then
    echo "No current APPROVED review on head ${head_sha} from a non-author reviewer" >&2
    return 1
  fi

  local login rc
  while IFS= read -r login; do
    [[ -z "$login" ]] && continue
    set +e
    is_team_member "$login"
    rc=$?
    set -e
    if [[ "$rc" -eq 0 ]]; then
      echo "$login"
      return 0
    fi
    if [[ "$rc" -eq 2 ]]; then
      return 2
    fi
    echo "Approver ${login} is not an active ${DS_ENGELS_ORG}/${DS_ENGELS_TEAM} member" >&2
  done <<<"$candidates"

  return 1
}

post_or_update_audit_comment() {
  local pr_number="$1"
  local author="$2"
  local approver="$3"
  local head_sha="$4"
  local repo="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"

  if [[ "$SKIP_AUDIT_COMMENT" == "true" ]]; then
    return 0
  fi

  local body
  body="$(cat <<EOF
${AUDIT_MARKER}
**Config-check override authorized**

| | |
|---|---|
| PR author | \`@${author}\` |
| Approving DS-Engels reviewer | \`@${approver}\` |
| Head SHA | \`${head_sha}\` |

The \`config\` check remains failed. Gatekeeper accepted the failure because this PR has the \`${OVERRIDE_LABEL}\` label and a current approval from \`@${DS_ENGELS_ORG}/${DS_ENGELS_TEAM}\`. Justification lives in normal PR review.
EOF
)"

  local comments existing_id
  comments="$(gh_api "repos/${repo}/issues/${pr_number}/comments?per_page=100")"
  existing_id="$(echo "$comments" | jq -r --arg marker "$AUDIT_MARKER" \
    '[.[] | select(.body | contains($marker))] | first | .id // empty')"

  if [[ -n "$existing_id" ]]; then
    gh_api --method PATCH "repos/${repo}/issues/comments/${existing_id}" -f body="$body" >/dev/null
  else
    gh_api --method POST "repos/${repo}/issues/${pr_number}/comments" -f body="$body" >/dev/null
  fi
}

evaluate_config_override() {
  # Sets OVERRIDE_PR_NUMBER, OVERRIDE_AUTHOR, OVERRIDE_HEAD_SHA, OVERRIDE_APPROVER
  # when authorized.
  # Exit 0 authorized; 1 denied; 2 verification error (fail closed).
  OVERRIDE_PR_NUMBER=""
  OVERRIDE_AUTHOR=""
  OVERRIDE_HEAD_SHA=""
  OVERRIDE_APPROVER=""

  local event_name="${EVENT_NAME:-}"
  local head_sha="${PR_HEAD_SHA:-}"
  local author="${PR_AUTHOR:-}"

  local pr_number
  if ! pr_number="$(resolve_pr_number)"; then
    echo "Override denied: no verifiable PR context (event=${event_name})" >&2
    return 1
  fi

  local pr_json
  if ! pr_json="$(fetch_pr_json "$pr_number")"; then
    echo "Override denied: failed to fetch PR #${pr_number}" >&2
    return 2
  fi

  head_sha="${head_sha:-$(echo "$pr_json" | jq -r '.head.sha // empty')}"
  author="${author:-$(echo "$pr_json" | jq -r '.user.login // empty')}"
  local base_ref
  base_ref="$(echo "$pr_json" | jq -r '.base.ref // empty')"
  local is_fork=false
  if echo "$pr_json" | jq -e \
    '(.head.repo.fork == true) or (.head.repo.full_name != .base.repo.full_name)' \
    >/dev/null; then
    is_fork=true
  fi

  if ! pr_has_override_label "$pr_json"; then
    echo "Override denied: missing label ${OVERRIDE_LABEL}" >&2
    return 1
  fi
  if [[ "$base_ref" != "main" ]]; then
    echo "Override denied: base ref is '${base_ref}', need main" >&2
    return 1
  fi
  if [[ "$is_fork" == "true" ]]; then
    echo "Override denied: fork PRs are not eligible" >&2
    return 1
  fi
  if [[ -z "$head_sha" || -z "$author" ]]; then
    echo "Override denied: missing head SHA or author" >&2
    return 1
  fi

  local approver rc
  set +e
  approver="$(find_ds_engels_approver "$pr_number" "$head_sha" "$author")"
  rc=$?
  set -e
  if [[ "$rc" -ne 0 ]]; then
    return "$rc"
  fi

  OVERRIDE_PR_NUMBER="$pr_number"
  OVERRIDE_AUTHOR="$author"
  OVERRIDE_HEAD_SHA="$head_sha"
  OVERRIDE_APPROVER="$approver"
  return 0
}

run_gatekeeper() {
  print_status_summary
  classify_results

  if [[ "$HAS_NON_CONFIG_BLOCK" == "true" ]]; then
    emit_result "failure" "CI checks failed"
    return 0
  fi

  if [[ "$CONFIG_IS_CANCELLED" == "true" ]]; then
    emit_result "failure" "CI checks failed"
    return 0
  fi

  if [[ "$CONFIG_IS_FAILURE" != "true" ]]; then
    emit_result "success" "All CI checks passed"
    return 0
  fi

  # Only config failed — evaluate override (no command-sub so globals stick).
  local rc
  set +e
  evaluate_config_override
  rc=$?
  set -e

  if [[ "$rc" -eq 0 ]]; then
    echo "Config-check override authorized by @${OVERRIDE_APPROVER}"
    post_or_update_audit_comment \
      "${OVERRIDE_PR_NUMBER}" \
      "${OVERRIDE_AUTHOR}" \
      "${OVERRIDE_APPROVER}" \
      "${OVERRIDE_HEAD_SHA}"
    emit_result "success" "Config check overridden (approved by @${OVERRIDE_APPROVER})"
    return 0
  fi

  if [[ "$rc" -eq 2 ]]; then
    emit_result "failure" "Config override verification failed (fail closed)"
    return 0
  fi

  emit_result "failure" "CI checks failed"
  return 0
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  # Prefer GH_TOKEN; fall back to GITHUB_TOKEN for local/scripts.
  if [[ -z "${GH_TOKEN:-}" && -n "${GITHUB_TOKEN:-}" ]]; then
    export GH_TOKEN="$GITHUB_TOKEN"
  fi
  run_gatekeeper
fi
