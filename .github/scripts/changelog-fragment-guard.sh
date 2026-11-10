#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $(basename "$0") <fragment-path> [<fragment-path> ...] [--base-ref <ref>]" >&2
}

resolve_base_ref() {
  if [[ -n "${1:-}" ]]; then
    echo "$1"
    return
  fi
  echo "main"
}

is_valid_target() {
  [[ "$1" == "main" || "$1" == release/* ]]
}

# Retries a flaky fetch up to 3 times; GIT_HTTP_LOW_SPEED_TIME bounds HTTP
# stalls, `timeout` backstops other transports.
fetch_release_refs() {
  local _attempt
  local -a runner=(git fetch --quiet origin 'refs/heads/release/*:refs/remotes/origin/release/*')
  command -v timeout &> /dev/null && runner=(timeout 60 "${runner[@]}")

  for _attempt in 1 2 3; do
    GIT_HTTP_LOW_SPEED_LIMIT=10 GIT_HTTP_LOW_SPEED_TIME=30 "${runner[@]}" && return 0
    ((_attempt < 3)) && sleep 2
  done
  return 1
}

contains_blob() {
  local needle="$1" candidate
  shift
  for candidate in "$@"; do
    [[ "$needle" == "$candidate" ]] && return 0
  done
  return 1
}

# Echoes every distinct blob path $1 has held: on disk (pre-deletion call)
# and across its own local commit history (catches an edit before deletion).
resolve_fragment_blobs() {
  local path="$1" blob commit log_output
  local -a blobs=()

  if [[ -f "$path" ]]; then
    blob="$(git hash-object "$path")" || return 1
    blobs+=("$blob")
  fi

  log_output="$(git log --format=%H -- "$path")" || return 1
  while IFS= read -r commit; do
    [[ -z "$commit" ]] && continue
    blob="$(git rev-parse --verify --quiet "${commit}:${path}" 2> /dev/null)" || blob=""
    [[ -n "$blob" ]] && ! contains_blob "$blob" "${blobs[@]}" && blobs+=("$blob")
  done <<< "$log_output"

  ((${#blobs[@]} == 0)) && return 1
  printf '%s\n' "${blobs[@]}"
}

# Classifies fragment $1 (known content blobs $3..) against every release/*
# branch other than $2's own branch, if $2 names one.
#
# A release branch stays open for days before `changie batch` runs, so
# "still present at the branch tip" does not mean "unreleased" for any
# branch except the one the current change targets. For every release
# branch other than the target, block as soon as it has ever carried a
# matching blob for the path — whether still at its tip or already batched
# away. For the target's own release branch, block only once that branch
# has batched the fragment away (dropped from tip, blob still in its
# history): the change is allowed to correct a fragment its own branch
# hasn't cut into a dated changelog yet.
#
# Returns 0 (blocked), 1 (clear), or 2 (undecidable).
fragment_carried_by_release_branch() {
  local path="$1" base_ref="$2" branch commit blob tip_blob branches_output branch_log own_branch=""
  shift 2
  local -a blobs=("$@") release_branches=()
  ((${#blobs[@]} == 0)) && return 2

  [[ "$base_ref" == release/* ]] && own_branch="origin/${base_ref}"

  branches_output="$(git branch -r --list 'origin/release/*' | tr -d ' ')" || return 2
  while IFS= read -r branch; do
    [[ -z "$branch" ]] && continue
    release_branches+=("$branch")
  done <<< "$branches_output"

  for branch in "${release_branches[@]}"; do
    if [[ "$branch" == "$own_branch" ]]; then
      tip_blob="$(git rev-parse --verify --quiet "${branch}:${path}" 2> /dev/null)" || tip_blob=""
      [[ -n "$tip_blob" ]] && continue
    fi

    branch_log="$(git log --format=%H "$branch" -- "$path")" || return 2
    while IFS= read -r commit; do
      [[ -z "$commit" ]] && continue
      blob="$(git rev-parse --verify --quiet "${commit}:${path}" 2> /dev/null)" || blob=""
      [[ -n "$blob" ]] && contains_blob "$blob" "${blobs[@]}" && return 0
    done <<< "$branch_log"
  done
  return 1
}

main() {
  local base_ref="" path rc=0
  local -a paths=()

  while (($#)); do
    case "$1" in
      --base-ref)
        base_ref="${2:?--base-ref requires a value}"
        shift 2
        ;;
      -h | --help)
        usage
        exit 0
        ;;
      *)
        paths+=("$1")
        shift
        ;;
    esac
  done

  if ((${#paths[@]} == 0)); then
    usage
    exit 1
  fi

  base_ref="$(resolve_base_ref "$base_ref")"

  if ! is_valid_target "$base_ref"; then
    for path in "${paths[@]}"; do
      echo "changie-check: ${path}: an unreleased fragment can only be deleted or replaced on a change targeting main or a release/* branch (this targets '${base_ref}'). Add a new fragment with \`changie new\` instead." >&2
    done
    exit 1
  fi

  if ! fetch_release_refs; then
    for path in "${paths[@]}"; do
      echo "changie-check: ${path}: could not fetch release/* branches after 3 attempts, so a release cutover cannot be ruled out. Add a new fragment with \`changie new\` instead." >&2
    done
    exit 1
  fi

  local blobs_output blob cutoff_rc
  local -a blobs
  for path in "${paths[@]}"; do
    if ! blobs_output="$(resolve_fragment_blobs "$path")"; then
      echo "changie-check: ${path}: could not determine its content to check against release branches. Add a new fragment with \`changie new\` instead." >&2
      rc=1
      continue
    fi

    blobs=()
    while IFS= read -r blob; do
      [[ -n "$blob" ]] && blobs+=("$blob")
    done <<< "$blobs_output"

    cutoff_rc=0
    fragment_carried_by_release_branch "$path" "$base_ref" "${blobs[@]}" || cutoff_rc=$?
    case "$cutoff_rc" in
      0)
        echo "changie-check: ${path}: a release/* branch already carries this fragment (batched or not), so it can no longer be deleted or replaced. Add a new fragment with \`changie new\` instead." >&2
        rc=1
        ;;
      1) : ;;
      *)
        echo "changie-check: ${path}: could not verify this fragment against release branches. Add a new fragment with \`changie new\` instead." >&2
        rc=1
        ;;
    esac
  done

  exit "$rc"
}

main "$@"
