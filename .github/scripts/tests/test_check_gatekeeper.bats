#!/usr/bin/env bats
#
# Tests for .github/scripts/check-gatekeeper.sh — config-check override rules.
#
# Override is authorized only when:
#   - PR targets main, not a fork
#   - label config-check-override is present
#   - current head SHA has APPROVED review from Unique-AG/ds-engels (not author)
#   - the only failing required check is config == failure
#
# Everything else stays blocking. Membership / API errors fail closed.

load test_helper

SCRIPT="$SCRIPTS_DIR/check-gatekeeper.sh"
HEAD_SHA="abc123def456"
AUTHOR="pr-author"
APPROVER="ds-approver"
OUTSIDER="random-reviewer"

setup() {
  export TEST_TMPDIR="$(mktemp -d)"
  cd "$TEST_TMPDIR" || exit 1
  export GITHUB_OUTPUT="$TEST_TMPDIR/github_output"
  : >"$GITHUB_OUTPUT"
  export GITHUB_REPOSITORY="Unique-AG/ai"
  export SKIP_AUDIT_COMMENT=true
  export EVENT_NAME="pull_request"
  export PR_NUMBER="42"
  export PR_HEAD_SHA="$HEAD_SHA"
  export PR_AUTHOR="$AUTHOR"

  # Default: all checks success except what each test overrides.
  export DETECT_CHANGES=success
  export LINT=success
  export TEST=success
  export TYPES=success
  export COVERAGE=success
  export DEPS=success
  export CONTAINERIZE=success
  export HELM_LINT=success
  export CONFIG=success
  export PR_TITLE=success
  export NO_MANUAL_RELEASE=skipped
  export RELEASE_LINEAGE=skipped

  # Fixture knobs controlled per-test via MOCK_* env vars.
  export MOCK_LABELS='["config-check-override"]'
  export MOCK_BASE_REF="main"
  export MOCK_IS_FORK="false"
  export MOCK_REVIEWS="[]"
  export MOCK_MEMBERSHIP_MODE="ok" # ok | deny | error
  export MOCK_MEMBERS="$APPROVER"
  export MOCK_PR_FETCH_FAIL="false"
  export MOCK_AUDIT_POSTS="$TEST_TMPDIR/audit_posts"
  : >"$MOCK_AUDIT_POSTS"

  # shellcheck source=/dev/null
  source "$SCRIPT"

  gh_api() {
    local args=("$@")
    local joined="${args[*]}"

    if [[ "$joined" =~ pulls/[0-9]+(/|$|\ ) ]] && [[ "$joined" != *"/reviews"* ]] && [[ "$joined" != *"/comments"* ]]; then
      if [[ "${MOCK_PR_FETCH_FAIL}" == "true" ]]; then
        echo "HTTP 500: boom" >&2
        return 1
      fi
      local fork_json="false"
      if [[ "${MOCK_IS_FORK}" == "true" ]]; then
        fork_json="true"
      fi
      local head_repo="Unique-AG/ai"
      local base_repo="Unique-AG/ai"
      if [[ "${MOCK_IS_FORK}" == "true" ]]; then
        head_repo="fork-user/ai"
      fi
      jq -n \
        --argjson labels "${MOCK_LABELS}" \
        --arg base "$MOCK_BASE_REF" \
        --arg author "$AUTHOR" \
        --arg sha "$HEAD_SHA" \
        --argjson fork "$fork_json" \
        --arg head_repo "$head_repo" \
        --arg base_repo "$base_repo" \
        '{
          number: 42,
          user: {login: $author},
          head: {sha: $sha, repo: {fork: $fork, full_name: $head_repo}},
          base: {ref: $base, repo: {full_name: $base_repo}},
          labels: ($labels | map({name: .}))
        }'
      return 0
    fi

    if [[ "$joined" == *"/reviews"* ]]; then
      echo "${MOCK_REVIEWS}"
      return 0
    fi

    if [[ "$joined" == *"/memberships/"* ]]; then
      local user="${joined##*/memberships/}"
      user="${user%% *}"
      case "${MOCK_MEMBERSHIP_MODE}" in
        error)
          echo "HTTP 403: Resource not accessible by integration" >&2
          return 1
          ;;
        deny)
          echo "gh: Not Found (HTTP 404)" >&2
          return 1
          ;;
        ok)
          if [[ " ${MOCK_MEMBERS} " == *" ${user} "* ]]; then
            echo '{"state":"active","role":"member"}'
            return 0
          fi
          echo "gh: Not Found (HTTP 404)" >&2
          return 1
          ;;
        *)
          echo "unknown MOCK_MEMBERSHIP_MODE" >&2
          return 1
          ;;
      esac
    fi

    if [[ "$joined" == *"/comments"* ]]; then
      if [[ "$joined" == *"PATCH"* || "$joined" == *"POST"* || "$joined" == *"--method"* ]]; then
        # Only record write attempts (POST/PATCH), not GET list.
        if [[ "$joined" == *"POST"* || "$joined" == *"PATCH"* ]]; then
          echo "$joined" >>"$MOCK_AUDIT_POSTS"
        fi
        if [[ "$joined" == *"POST"* || "$joined" == *"PATCH"* ]]; then
          echo '{"id":1}'
          return 0
        fi
      fi
      echo '[]'
      return 0
    fi

    echo "unexpected gh_api call: $joined" >&2
    return 1
  }

  # Re-export so nested calls see the mock (bash functions are dynamic).
  export -f gh_api
}

teardown() {
  cd "$TESTS_DIR" || true
  if [ -n "$TEST_TMPDIR" ] && [ -d "$TEST_TMPDIR" ]; then
    rm -rf "$TEST_TMPDIR"
  fi
}

read_status() {
  grep '^status=' "$GITHUB_OUTPUT" | tail -1 | cut -d= -f2-
}

read_description() {
  grep '^description=' "$GITHUB_OUTPUT" | tail -1 | cut -d= -f2-
}

set_approved_review() {
  local login="${1:-$APPROVER}"
  local sha="${2:-$HEAD_SHA}"
  local state="${3:-APPROVED}"
  MOCK_REVIEWS="$(jq -n \
    --arg login "$login" \
    --arg sha "$sha" \
    --arg state "$state" \
    '[{
      id: 1,
      user: {login: $login},
      state: $state,
      commit_id: $sha,
      submitted_at: "2026-08-05T12:00:00Z"
    }]')"
  export MOCK_REVIEWS
}

# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@test "override: label + current DS-Engels approval => Gatekeeper success" {
  export CONFIG=failure
  set_approved_review "$APPROVER" "$HEAD_SHA"
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "success" ]
  [[ "$(read_description)" == *"overridden"* ]]
  [[ "$(read_description)" == *"@${APPROVER}"* ]]
}

@test "all checks passed => success without override" {
  export CONFIG=success
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "success" ]
  [ "$(read_description)" = "All CI checks passed" ]
}

# ---------------------------------------------------------------------------
# Denial cases
# ---------------------------------------------------------------------------

@test "override denied: missing label" {
  export CONFIG=failure
  export MOCK_LABELS='[]'
  set_approved_review "$APPROVER" "$HEAD_SHA"
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "failure" ]
  [ "$(read_description)" = "CI checks failed" ]
}

@test "override denied: non-team approval" {
  export CONFIG=failure
  set_approved_review "$OUTSIDER" "$HEAD_SHA"
  export MOCK_MEMBERS="$APPROVER"
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "failure" ]
  [ "$(read_description)" = "CI checks failed" ]
}

@test "override denied: approval on stale head SHA" {
  export CONFIG=failure
  set_approved_review "$APPROVER" "oldsha000"
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "failure" ]
}

@test "override denied: dismissed approval" {
  export CONFIG=failure
  # Approval was dismissed — no remaining non-dismissed APPROVED review.
  set_approved_review "$APPROVER" "$HEAD_SHA" "DISMISSED"
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "failure" ]
}

@test "override denied: latest non-dismissed review is CHANGES_REQUESTED" {
  export CONFIG=failure
  MOCK_REVIEWS="$(jq -n \
    --arg login "$APPROVER" \
    --arg sha "$HEAD_SHA" \
    '[
      {id:1, user:{login:$login}, state:"APPROVED", commit_id:$sha, submitted_at:"2026-08-05T11:00:00Z"},
      {id:2, user:{login:$login}, state:"CHANGES_REQUESTED", commit_id:$sha, submitted_at:"2026-08-05T12:00:00Z"}
    ]')"
  export MOCK_REVIEWS
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "failure" ]
}

@test "override denied: self-approval by PR author" {
  export CONFIG=failure
  set_approved_review "$AUTHOR" "$HEAD_SHA"
  export MOCK_MEMBERS="$AUTHOR"
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "failure" ]
}

@test "cancelled config stays blocking even with override label+approval" {
  export CONFIG=cancelled
  set_approved_review "$APPROVER" "$HEAD_SHA"
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "failure" ]
  [ "$(read_description)" = "CI checks failed" ]
}

@test "unrelated CI failure stays blocking despite override authorization" {
  export CONFIG=failure
  export TEST=failure
  set_approved_review "$APPROVER" "$HEAD_SHA"
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "failure" ]
  [ "$(read_description)" = "CI checks failed" ]
}

@test "membership API failure fail-closed" {
  export CONFIG=failure
  set_approved_review "$APPROVER" "$HEAD_SHA"
  export MOCK_MEMBERSHIP_MODE="error"
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "failure" ]
  [ "$(read_description)" = "Config override verification failed (fail closed)" ]
}

@test "merge_group without verifiable PR context fail-closed" {
  export CONFIG=failure
  export EVENT_NAME="merge_group"
  unset PR_NUMBER
  export PR_NUMBER=""
  export MERGE_GROUP_HEAD_REF="refs/heads/gh-readonly-queue/main/merge-without-pr"
  set_approved_review "$APPROVER" "$HEAD_SHA"
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "failure" ]
}

@test "merge_group recovers PR number from head_ref and can authorize" {
  export CONFIG=failure
  export EVENT_NAME="merge_group"
  unset PR_NUMBER
  export PR_NUMBER=""
  export MERGE_GROUP_HEAD_REF="refs/heads/gh-readonly-queue/main/pr-42-${HEAD_SHA}"
  export PR_AUTHOR=""
  set_approved_review "$APPROVER" "$HEAD_SHA"
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "success" ]
  [[ "$(read_description)" == *"overridden"* ]]
}

@test "fork PR cannot use override" {
  export CONFIG=failure
  export MOCK_IS_FORK="true"
  set_approved_review "$APPROVER" "$HEAD_SHA"
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "failure" ]
}

@test "non-main base cannot use override" {
  export CONFIG=failure
  export MOCK_BASE_REF="release/2026.08"
  set_approved_review "$APPROVER" "$HEAD_SHA"
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "failure" ]
}

@test "audit comment posted when override authorized and SKIP_AUDIT_COMMENT=false" {
  export CONFIG=failure
  export SKIP_AUDIT_COMMENT=false
  set_approved_review "$APPROVER" "$HEAD_SHA"
  run run_gatekeeper
  [ "$status" -eq 0 ]
  [ "$(read_status)" = "success" ]
  grep -q "POST\|comments" "$MOCK_AUDIT_POSTS"
}
