#!/usr/bin/env bash
# Common functions for pyright type checking scripts

# Check if we're in a git repository
check_git_repo() {
  if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
  fi
}

# Get git root directory
get_git_root() {
  git rev-parse --show-toplevel
}

# Find base and head commits
find_commits() {
  local base_ref
  local head_ref
  
  echo "Finding base commit..."
  if ! base_ref=$(git merge-base origin/main HEAD 2>/dev/null); then
    echo "Warning: Could not find merge-base with origin/main, using HEAD~1"
    base_ref=$(git rev-parse HEAD~1 2>/dev/null || git rev-parse HEAD)
  fi
  echo "Base commit: $base_ref"
  
  head_ref=$(git rev-parse HEAD)
  echo "Head commit: $head_ref"
  
  # Export for use in calling script
  export BASE_REF="$base_ref"
  export HEAD_REF="$head_ref"
}

# Get changed Python files
get_changed_files() {
  local python_file_filter='(test_|_test\.py|tests/|__pycache__/|\.pyc$|migrations/|conftest\.py|setup\.py|__init__\.py)'
  
  # Get committed changes
  local committed_files=$(git diff --name-only "$BASE_REF"...$HEAD_REF | grep -E '\.py$' | grep -vE "$python_file_filter" || true)
  
  # Get unstaged changes
  local unstaged_files=$(git diff --name-only | grep -E '\.py$' | grep -vE "$python_file_filter" || true)
  
  # Combine and deduplicate
  echo -e "$committed_files\n$unstaged_files" | sort -u | grep -v '^$' || true
}

# Run pyright with JSON output
run_pyright() {
  local ref=$1
  shift
  local files="$@"
  local type_checking_mode="${TYPE_CHECKING_MODE:-standard}"
  local poetry="${POETRY:-poetry run}"
  
  echo "Creating worktree for $ref..."
  if ! git worktree add --detach /tmp/worktree-$ref $ref 2>/dev/null; then
    echo "Error: Failed to create worktree for $ref"
    return 1
  fi
  pushd /tmp/worktree-$ref >/dev/null
  
  # Filter files to only include those that exist in this commit
  local existing_files=""
  for file in $files; do
    if [[ -f "$file" ]]; then
      existing_files="$existing_files $file"
    fi
  done
  
  echo "{ \"typeCheckingMode\": \"$type_checking_mode\" }" > /tmp/pyrightconfig.json
  # If no files exist, return empty JSON structure
  if [[ -z "$existing_files" ]]; then
    echo '{"generalDiagnostics": []}'
  else
    # Try different ways to run pyright
    if command -v pyright >/dev/null 2>&1; then
      pyright -p /tmp/pyrightconfig.json --outputjson $existing_files || echo '{"generalDiagnostics": []}'
    elif command -v npx >/dev/null 2>&1; then
      npx pyright -p /tmp/pyrightconfig.json --outputjson $existing_files || echo '{"generalDiagnostics": []}'
    else
      $poetry pyright -p /tmp/pyrightconfig.json --outputjson $existing_files || echo '{"generalDiagnostics": []}'
    fi
  fi
  
  popd >/dev/null
  echo "Cleaning up worktree for $ref..."
  git worktree remove --force /tmp/worktree-$ref 2>/dev/null || true
}

# Get base errors for changed files (treating new files as having zero errors)
get_base_errors() {
  local files="$1"
  local type_checking_mode="${TYPE_CHECKING_MODE:-standard}"
  local poetry="${POETRY:-poetry run}"
  local git_root="${GIT_ROOT:-$(get_git_root)}"
  
  # Create worktree from git root
  cd "$git_root"
  echo "Creating worktree for base commit $BASE_REF..."
  if ! git worktree add --detach /tmp/worktree-base $BASE_REF 2>/dev/null; then
    echo "Error: Failed to create worktree for base commit $BASE_REF"
    return 1
  fi
  pushd /tmp/worktree-base >/dev/null
  
  # Filter files to only include those that exist in the base commit
  local existing_files=""
  for file in $files; do
    if [[ -f "$file" ]]; then
      existing_files="$existing_files $file"
    fi
  done
  
  echo "{ \"typeCheckingMode\": \"$type_checking_mode\" }" > /tmp/pyrightconfig.json
  # If no files exist, return empty JSON structure (new files have zero errors)
  if [[ -z "$existing_files" ]]; then
    echo '{"generalDiagnostics": []}'
  else
    # Try different ways to run pyright
    if command -v pyright >/dev/null 2>&1; then
      pyright -p /tmp/pyrightconfig.json --outputjson $existing_files || echo '{"generalDiagnostics": []}'
    elif command -v npx >/dev/null 2>&1; then
      npx pyright -p /tmp/pyrightconfig.json --outputjson $existing_files || echo '{"generalDiagnostics": []}'
    else
      $poetry pyright -p /tmp/pyrightconfig.json --outputjson $existing_files || echo '{"generalDiagnostics": []}'
    fi
  fi
  
  popd >/dev/null
  echo "Cleaning up base worktree..."
  git worktree remove --force /tmp/worktree-base 2>/dev/null || true
}

# Extract error data from JSON
extract_errors() {
  local json="$1"
  echo "$json" | jq -r '.generalDiagnostics[]? | "\(.file)|\(.range.start.line)|\(.message | gsub("\n"; " ") | gsub("\r"; ""))|\(.rule // "unknown")"' 2>/dev/null || echo ""
}

# Compare errors and get counts
compare_errors() {
  local base_errors="$1"
  local head_errors="$2"
  
  # Compare errors (using pipe-separated format for comparison)
  local new_errors=$(comm -13 <(echo "$base_errors" | sort) <(echo "$head_errors" | sort) || true)
  local removed_errors=$(comm -23 <(echo "$base_errors" | sort) <(echo "$head_errors" | sort) || true)
  
  # Count errors
  local base_count=$(grep -c . <<< "$base_errors" || echo "0")
  local head_count=$(grep -c . <<< "$head_errors" || echo "0")
  local new_count=$(grep -c . <<< "$new_errors" || echo "0")
  local removed_count=$(grep -c . <<< "$removed_errors" || echo "0")
  
  # Export for use in calling script
  export NEW_ERRORS="$new_errors"
  export REMOVED_ERRORS="$removed_errors"
  export BASE_COUNT="$base_count"
  export HEAD_COUNT="$head_count"
  export NEW_COUNT="$new_count"
  export REMOVED_COUNT="$removed_count"
}

# Get relative path from git root
get_relative_path() {
  local file="$1"
  local git_root="${GIT_ROOT:-$(get_git_root)}"
  python3 -c "import os; print(os.path.relpath('$file', '$git_root'))" 2>/dev/null || echo "$file"
}
