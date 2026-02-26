#!/usr/bin/env bash
set -e

# Script to check type errors on new/changed code
# Can be used both in CI workflows and locally
#
# Usage:
#   check-types.sh <package_dir> [--base-ref <branch>] [--runner <cmd>]
#
# Examples:
#   check-types.sh unique_toolkit
#   check-types.sh unique_toolkit --base-ref origin/main
#   check-types.sh unique_mcp --runner "uv run"

# Script metadata
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME=$(basename "$0")
VERSION="1.0.0"
source "$SCRIPT_DIR/lib/common.sh"

# Help function
show_help() {
    cat << EOF
${SCRIPT_NAME} - Check type errors on new/changed code

USAGE:
    ${SCRIPT_NAME} [OPTIONS] <package_dir>
    ${SCRIPT_NAME} -h | --help
    ${SCRIPT_NAME} --version

DESCRIPTION:
    This script checks for NEW type errors introduced by your changes by:
    1. Creating a baseline from the base branch (captures existing errors)
    2. Running basedpyright with the baseline (only reports new errors)

ARGUMENTS:
    package_dir          Path to package directory (e.g., unique_toolkit)

OPTIONS:
    -h, --help           Show this help message and exit
    -v, --version        Show version information and exit
    -b, --base-ref REF   Base branch/ref for comparison (default: origin/main)
    -r, --runner CMD     Command runner prefix (default: auto-detect)
                         Use "poetry run" for Poetry, "uv run" for uv

EXAMPLES:
    # Basic usage (Poetry, auto-detect base branch)
    ${SCRIPT_NAME} unique_toolkit

    # With explicit base branch
    ${SCRIPT_NAME} unique_toolkit --base-ref origin/main

    # For uv packages
    ${SCRIPT_NAME} unique_mcp --runner "uv run"
    ${SCRIPT_NAME} tool_packages/unique_web_search --runner "uv run"

EXIT CODES:
    0    No new type errors
    1    New type errors found or error occurred
    2    Invalid arguments

AUTHOR:
    Unique AI Toolkit

VERSION:
    ${VERSION}
EOF
}

# ============================================================================
# SETUP
# ============================================================================

# Initialize variables
PACKAGE_DIR=""
BASE_REF=""
RUNNER=""

# Parse arguments
ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --version|-v)
            show_version
            exit 0
            ;;
        --base-ref|-b)
            BASE_REF="$2"
            shift 2
            ;;
        --runner|-r)
            RUNNER="$2"
            shift 2
            ;;
        --)
            shift
            ARGS+=("$@")
            break
            ;;
        --*)
            print_error "Unknown option: $1"
            echo "Use --help for usage information."
            exit 2
            ;;
        -*)
            print_error "Unknown option: $1"
            echo "Use --help for usage information."
            exit 2
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

# Get positional arguments
if [ ${#ARGS[@]} -gt 0 ]; then
    PACKAGE_DIR="${ARGS[0]}"
fi

# Validate required arguments
if [ -z "$PACKAGE_DIR" ]; then
    print_error "Package directory is required"
    echo ""
    show_help
    exit 2
fi

# Validate package directory exists
if [ ! -d "$PACKAGE_DIR" ]; then
    print_error "Package directory '$PACKAGE_DIR' does not exist"
    exit 1
fi

# Auto-detect runner if not specified
if [ -z "$RUNNER" ]; then
    if [ -f "$PACKAGE_DIR/uv.lock" ]; then
        RUNNER="uv run"
    else
        RUNNER="poetry run"
    fi
fi

# Determine base reference if not provided
if [ -z "$BASE_REF" ]; then
    if [ -n "$GITHUB_BASE_REF" ]; then
        BASE_REF="origin/$GITHUB_BASE_REF"
    elif git show-ref --verify --quiet refs/remotes/origin/main; then
        BASE_REF="origin/main"
    elif git show-ref --verify --quiet refs/remotes/origin/master; then
        BASE_REF="origin/master"
    else
        print_error "Could not determine base reference automatically."
        echo "Please specify it with --base-ref option."
        exit 1
    fi
fi

# ============================================================================
# MAIN LOGIC
# ============================================================================

print_info "Type checking package: $PACKAGE_DIR"
print_info "Base reference: $BASE_REF"
print_info "Runner: $RUNNER"
echo ""

# Store current state
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "HEAD")
REPO_ROOT=$(git rev-parse --show-toplevel)
BASELINE_FILE="/tmp/basedpyright-baseline-$$.json"

# Change to package directory
cd "$PACKAGE_DIR" || {
    print_error "Failed to change to package directory: $PACKAGE_DIR"
    exit 1
}

# ============================================================================
# STEP 1: Create baseline from base branch
# ============================================================================

print_info "Step 1: Creating baseline from $BASE_REF..."

# Stash any uncommitted changes
git stash push -m "check-types-temp-$$" --quiet 2>/dev/null || true

# Fetch and checkout base branch
BRANCH_NAME=$(echo "$BASE_REF" | sed 's|^origin/||')
git fetch origin "$BRANCH_NAME" --quiet 2>/dev/null || true
git checkout "$BASE_REF" --quiet 2>/dev/null || git checkout "$BRANCH_NAME" --quiet || {
    print_error "Failed to checkout $BASE_REF"
    git stash pop --quiet 2>/dev/null || true
    exit 1
}

# Install dependencies on base branch
print_info "Installing dependencies on base branch..."
$RUNNER pip install -q . 2>/dev/null || $RUNNER python -m pip install -q . 2>/dev/null || true

# Create baseline
mkdir -p .basedpyright
print_info "Running basedpyright --writebaseline on $BASE_REF..."
$RUNNER basedpyright --writebaseline 2>&1 || {
    print_warning "basedpyright exited with non-zero status (expected if there are errors)"
}

# Save baseline
if [ -f .basedpyright/baseline.json ]; then
    cp .basedpyright/baseline.json "$BASELINE_FILE"
    ERROR_COUNT=$(jq '[.files[] | length] | add // 0' .basedpyright/baseline.json 2>/dev/null || echo "0")
    print_success "Baseline created with $ERROR_COUNT known errors"
else
    touch "$BASELINE_FILE"
    print_success "No baseline needed (no errors in $BASE_REF)"
fi

# ============================================================================
# STEP 2: Return to current branch and run type check
# ============================================================================

print_info "Step 2: Switching back to $CURRENT_BRANCH..."

# Discard any changes from dependency installation
git reset --hard HEAD --quiet 2>/dev/null || true
git checkout "$CURRENT_BRANCH" --quiet 2>/dev/null || git checkout - --quiet || {
    print_error "Failed to return to original branch"
    exit 1
}

# Restore stashed changes
git stash pop --quiet 2>/dev/null || true

# Apply baseline
print_info "Applying baseline and running type check..."
mkdir -p .basedpyright
cp "$BASELINE_FILE" .basedpyright/baseline.json

# Run basedpyright and capture output to temp file
echo ""
TEMP_OUTPUT="/tmp/basedpyright-output-$$.txt"
set +e  # Don't exit on error
$RUNNER basedpyright 2>&1 | tee "$TEMP_OUTPUT"
set -e

# Cleanup baseline temp file
rm -f "$BASELINE_FILE"

# Check if there are actual errors (not just baseline warnings)
# basedpyright outputs "N errors, M warnings, K notes" at the end
ERROR_LINE=$(grep -E "^[0-9]+ errors," "$TEMP_OUTPUT" | tail -1 || echo "0 errors,")
ERROR_COUNT=$(echo "$ERROR_LINE" | grep -oE "^[0-9]+" || echo "0")
rm -f "$TEMP_OUTPUT"

echo ""
if [ "$ERROR_COUNT" = "0" ]; then
    print_success "Type check passed! No new type errors introduced."
    exit 0
else
    print_error "Type check failed! $ERROR_COUNT new type error(s) found."
    echo "Please fix the type errors above."
    exit 1
fi
