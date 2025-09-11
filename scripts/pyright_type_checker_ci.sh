#!/usr/bin/env bash
set -euo pipefail

# Simplified Type Checker for CI
# Usage: ./pyright_type_checker_ci.sh
# 
# Environment variables:
#   TYPE_CHECKING_MODE - Set pyright mode: "off", "basic", or "strict" (default: basic)

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! source "$SCRIPT_DIR/pyright_common.sh"; then
  echo "Error: Failed to source common functions from $SCRIPT_DIR/pyright_common.sh"
  exit 1
fi

# Initialize
echo "Initializing type checker..."
check_git_repo
GIT_ROOT=$(get_git_root)
echo "Git root: $GIT_ROOT"
POETRY="poetry run"
TYPE_CHECKING_MODE="${TYPE_CHECKING_MODE:-standard}"

# Find commits
echo "Finding commits..."
find_commits

# Get changed files
echo "Finding changed Python files..."
changed_files=$(get_changed_files)

if [[ -z "$changed_files" ]]; then
  echo "✅ No Python files changed"
  exit 0
fi

echo "Changed Python files:"
echo "$changed_files" | while read -r file; do
  if [[ -n "$file" ]]; then
    echo "  - $file"
  fi
done

# Run checks
echo "🔎 Running Pyright on base: $BASE_REF"
base_report=$(get_base_errors $changed_files)

echo "🔎 Running Pyright on head: $HEAD_REF"
echo "{ \"typeCheckingMode\": \"$TYPE_CHECKING_MODE\" }" > /tmp/pyrightconfig.json
# Run pyright from the git root to ensure consistent path resolution
cd "$GIT_ROOT"

# Try different ways to run pyright
if command -v pyright >/dev/null 2>&1; then
  head_report=$(pyright -p /tmp/pyrightconfig.json --outputjson $changed_files || echo '{"generalDiagnostics": []}')
elif command -v npx >/dev/null 2>&1; then
  head_report=$(npx pyright -p /tmp/pyrightconfig.json --outputjson $changed_files || echo '{"generalDiagnostics": []}')
else
  head_report=$($POETRY pyright -p /tmp/pyrightconfig.json --outputjson $changed_files || echo '{"generalDiagnostics": []}')
fi

# Get error data
base_errors=$(extract_errors "$base_report")
head_errors=$(extract_errors "$head_report")

# Compare errors and get counts
compare_errors "$base_errors" "$head_errors"

# Show summary
echo ""
echo "📊 Type Check Summary"
echo "Base commit errors:  $BASE_COUNT"
echo "Head commit errors:  $HEAD_COUNT"
echo "New errors:          $NEW_COUNT"
echo "Removed errors:      $REMOVED_COUNT"
echo ""

# Display removed errors first (good news!)
if [[ -n "$REMOVED_ERRORS" ]]; then
  echo "✅ $REMOVED_COUNT type error(s) removed:"
  echo "$REMOVED_ERRORS" | while IFS='|' read -r file line message rule; do
    if [[ -n "$file" && -n "$line" ]]; then
      # Get relative path from git root for clickable links
      relative_path=$(get_relative_path "$file")
      echo "  - $relative_path:$line - $message"
    fi
  done
  echo ""
fi

# Display new errors
if [[ -n "$NEW_ERRORS" ]]; then
  echo "❌ $NEW_COUNT new type error(s) introduced:"
  echo "$NEW_ERRORS" | while IFS='|' read -r file line message rule; do
    if [[ -n "$file" && -n "$line" ]]; then
      # Get relative path from git root for clickable links
      relative_path=$(get_relative_path "$file")
      echo "  - $relative_path:$line - $message"
    fi
  done
  echo ""
  exit 1
else
  if [[ -n "$REMOVED_ERRORS" ]]; then
    echo "✅ No new type errors introduced!"
  else
    echo "✅ No changes in type errors"
  fi
fi
