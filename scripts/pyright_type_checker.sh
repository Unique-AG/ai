#!/usr/bin/env bash
set -euo pipefail

# Enhanced Type Checker with gum formatting
# Usage: ./pyright_type_checker.sh
# 
# Environment variables:
#   TYPE_CHECKING_MODE - Set pyright mode: "off", "basic", or "strict" (default: basic)
#   TEXT_WIDTH - Set text wrapping width for error messages (default: 80)

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/pyright_common.sh"

# Initialize
check_git_repo
GIT_ROOT=$(get_git_root)
echo "Git root: $GIT_ROOT"

# Find commits
find_commits

# ensure pyright installed in poetry env
POETRY="poetry run"

# Pyright type checking mode: "off", "standard", or "strict"
TYPE_CHECKING_MODE="${TYPE_CHECKING_MODE:-standard}"

# Text wrapping width for all text output (default: 80 characters)
TEXT_WIDTH="${TEXT_WIDTH:-80}"

# Function to wrap text with proper indentation
wrap_text() {
  local text="$1"
  local indent="${2:-0}"
  local width="${3:-$TEXT_WIDTH}"
  
  # Create indentation string
  local indent_str=""
  for ((i=0; i<indent; i++)); do
    indent_str+=" "
  done
  
  # Wrap text and add indentation to wrapped lines
  if echo "$text" | fold -w $width -s | sed "s/^/$indent_str/" 2>/dev/null; then
    : # Success
  else
    # Fallback if sed fails
    echo "$text" | while IFS= read -r line; do
      echo "${indent_str}${line}"
    done
  fi
}

# Function to check if gum is available and use it, otherwise fallback to echo
gum_style() {
  if command -v gum >/dev/null 2>&1; then
    gum style "$@"
  else
    # Enhanced fallback with basic formatting
    local args=("$@")
    local border=""
    local color=""
    local padding=""
    local margin=""
    local text=""
    
    # Parse arguments (simplified)
    for arg in "${args[@]}"; do
      case "$arg" in
        --border=*)
          border="${arg#*=}"
          ;;
        --border-foreground=*)
          color="${arg#*=}"
          ;;
        --padding=*)
          padding="${arg#*=}"
          ;;
        --margin=*)
          margin="${arg#*=}"
          ;;
        --foreground=*)
          color="${arg#*=}"
          ;;
        --bold)
          # Bold is handled by color
          ;;
        *)
          if [[ -n "$arg" && ! "$arg" =~ ^-- ]]; then
            text="$arg"
          fi
          ;;
      esac
    done
    
    # Create simple border
    case "$border" in
      "rounded")
        echo "╭─────────────────────────────────────────────────────────────╮"
        ;;
      "double")
        echo "╔═════════════════════════════════════════════════════════════╗"
        ;;
      "thick")
        echo "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓"
        ;;
    esac
    
    # Output text with color codes if available
    if [[ -n "$text" ]]; then
      case "$color" in
        "red")
          echo -e "\033[31m$text\033[0m"
          ;;
        "green")
          echo -e "\033[32m$text\033[0m"
          ;;
        "blue")
          echo -e "\033[34m$text\033[0m"
          ;;
        "yellow")
          echo -e "\033[33m$text\033[0m"
          ;;
        *)
          echo "$text"
          ;;
      esac
    fi
    
    # Close border
    case "$border" in
      "rounded")
        echo "╰─────────────────────────────────────────────────────────────╯"
        ;;
      "double")
        echo "╚═════════════════════════════════════════════════════════════╝"
        ;;
      "thick")
        echo "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
        ;;
    esac
  fi
}

# Get changed files
echo "Finding changed Python files..."
changed_files=$(get_changed_files)

if [[ -z "$changed_files" ]]; then
  wrap_text "✅ No Python files changed" 0
  exit 0
fi

wrap_text "📂 Changed Python files:" 0
echo "$changed_files" | while read -r file; do
  if [[ -n "$file" ]]; then
    wrap_text "$file" 4
  fi
done

# function to run pyright with JSON
run_pyright() {
  ref=$1
  shift
  files="$@"

  # Create worktree from git root
  cd "$GIT_ROOT"
  echo "Creating worktree for $ref..."
  if ! git worktree add --detach /tmp/worktree-$ref $ref 2>/dev/null; then
    echo "Error: Failed to create worktree for $ref"
    return 1
  fi
  pushd /tmp/worktree-$ref >/dev/null
  
  # Filter files to only include those that exist in this commit
  existing_files=""
  for file in $files; do
    if [[ -f "$file" ]]; then
      existing_files="$existing_files $file"
    fi
  done

  echo "{ \"typeCheckingMode\": \"$TYPE_CHECKING_MODE\" }" > /tmp/pyrightconfig.json
  # If no files exist, return empty JSON structure
  if [[ -z "$existing_files" ]]; then
    echo '{"generalDiagnostics": []}'
  else
    $POETRY pyright -p /tmp/pyrightconfig.json --outputjson $existing_files || echo '{"generalDiagnostics": []}'
  fi
  
  popd >/dev/null
  echo "Cleaning up worktree for $ref..."
  git worktree remove --force /tmp/worktree-$ref 2>/dev/null || true
}

# function to get base errors for changed files (treating new files as having zero errors)
get_base_errors() {
  local files="$1"
  
  # Create worktree from git root
  cd "$GIT_ROOT"
  echo "Creating worktree for base commit $BASE_REF..."
  if ! git worktree add --detach /tmp/worktree-base $BASE_REF 2>/dev/null; then
    echo "Error: Failed to create worktree for base commit $BASE_REF"
    return 1
  fi
  pushd /tmp/worktree-base >/dev/null
  
  # Filter files to only include those that exist in the base commit
  existing_files=""
  for file in $files; do
    if [[ -f "$file" ]]; then
      existing_files="$existing_files $file"
    fi
  done

  echo "{ \"typeCheckingMode\": \"$TYPE_CHECKING_MODE\" }" > /tmp/pyrightconfig.json
  # If no files exist, return empty JSON structure (new files have zero errors)
  if [[ -z "$existing_files" ]]; then
    echo '{"generalDiagnostics": []}'
  else
    $POETRY pyright -p /tmp/pyrightconfig.json --outputjson $existing_files || echo '{"generalDiagnostics": []}'
  fi
  
  popd >/dev/null
  echo "Cleaning up base worktree..."
  git worktree remove --force /tmp/worktree-base 2>/dev/null || true
}

# run checks
wrap_text "🔎 Running Pyright on base: $BASE_REF" 0
base_report=$(get_base_errors $changed_files)

wrap_text "🔎 Running Pyright on head: $HEAD_REF" 0
echo "{ \"typeCheckingMode\": \"$TYPE_CHECKING_MODE\" }" > /tmp/pyrightconfig.json
# Run pyright from the git root to ensure consistent path resolution
cd "$GIT_ROOT"
head_report=$($POETRY pyright -p /tmp/pyrightconfig.json --outputjson $changed_files || echo '{"generalDiagnostics": []}')

# Extract error data directly from JSON using jq
extract_errors() {
  local json="$1"
  echo "$json" | jq -r '.generalDiagnostics[]? | "\(.file)|\(.range.start.line)|\(.message | gsub("\n"; " ") | gsub("\r"; ""))|\(.rule // "unknown")"' 2>/dev/null || echo ""
}

# Display errors in a nice formatted way
display_errors() {
  local errors="$1"
  local title="$2"
  local color="$3"
  
  if [[ -z "$errors" ]]; then
    return
  fi
  
  
  # Display each error in a clean format
  echo "$errors" | while IFS='|' read -r file line message rule; do
    if [[ -n "$file" && -n "$line" ]]; then
      # Get relative path from git root for clickable links
      relative_path=$(python3 -c "import os; print(os.path.relpath('$file', '$GIT_ROOT'))" 2>/dev/null || echo "$file")
      
      # Clean up message - remove newlines and extra spaces
      clean_message=$(echo "$message" | tr -d '\n\r' | sed 's/  */ /g' | sed 's/^ *//' | sed 's/ *$//')
      
      # Wrap long messages using the wrap_text function with error emoji
      wrapped_message=$(wrap_text "⚠️  $clean_message" 2)
      
      # Display error in a clean box format with proper text wrapping
      gum_style --border="rounded" --border-foreground="$color" --padding="1 2" --margin="0 0 1 0" \
        "📁 $relative_path:$line" \
        "" \
        "$wrapped_message" \
        "" \
        "$(wrap_text "🔍 Rule: $rule" 2)"
    fi
  done
}

# Get error data
base_errors=$(extract_errors "$base_report")
head_errors=$(extract_errors "$head_report")

# Compare errors (using pipe-separated format for comparison)
new_errors=$(comm -13 <(echo "$base_errors" | sort) <(echo "$head_errors" | sort) || true)
removed_errors=$(comm -23 <(echo "$base_errors" | sort) <(echo "$head_errors" | sort) || true)

# Create summary
base_count=$(if [[ -n "$base_errors" ]]; then echo "$base_errors" | grep -v '^$' | wc -l; else echo 0; fi)
head_count=$(if [[ -n "$head_errors" ]]; then echo "$head_errors" | grep -v '^$' | wc -l; else echo 0; fi)
new_count=$(if [[ -n "$new_errors" ]]; then echo "$new_errors" | grep -v '^$' | wc -l; else echo 0; fi)
removed_count=$(if [[ -n "$removed_errors" ]]; then echo "$removed_errors" | grep -v '^$' | wc -l; else echo 0; fi)

# Show summary with gum
gum_style --border="rounded" --border-foreground="blue" --padding="1 2" --margin="1" \
  "📊 Type Check Summary" \
  "" \
  "Base commit errors:  $base_count" \
  "Head commit errors:  $head_count" \
  "New errors:          $new_count" \
  "Removed errors:      $removed_count"

# Display removed errors first (good news!)
if [[ -n "$removed_errors" ]]; then
  status_msg="✅ $removed_count type error(s) removed:"
  wrap_text "$status_msg" 0 | gum_style --foreground="green" --bold
  display_errors "$removed_errors" "Removed Errors" "green"
fi

# Display new errors
if [[ -n "$new_errors" ]]; then
  status_msg="❌ $new_count new type error(s) introduced:"
  wrap_text "$status_msg" 0 | gum_style --foreground="red" --bold
  display_errors "$new_errors" "New Errors" "red"
  exit 1
else
  if [[ -n "$removed_errors" ]]; then
    status_msg="✅ No new type errors introduced!"
    wrap_text "$status_msg" 0 | gum_style --foreground="green" --bold
  else
    status_msg="✅ No changes in type errors"
    wrap_text "$status_msg" 0 | gum_style --foreground="green" --bold
  fi
fi