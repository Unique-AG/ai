#!/usr/bin/env bash
# =============================================================================
# Development helper script for running CI checks locally
# Auto-detects package manager (poetry vs uv) based on pyproject.toml
#
# Usage: ./dev.sh <command> [options]
#
# Commands:
#   lint              Run ruff linter (check mode)
#   lint --fix        Run ruff linter with auto-fix
#   format            Run ruff formatter
#   test              Run pytest
#   coverage          Run pytest with coverage (diff-based like CI)
#   typecheck         Run basedpyright type checker
#   depcheck          Run deptry dependency checker
#   all               Run lint, typecheck, depcheck, and test
#
# Options:
#   --dir <path>      Package directory (default: current directory)
#   --no-baseline     Skip baseline computation for coverage/typecheck
#   --base-ref <ref>  Base branch for diff comparison (default: origin/main)
#   -h, --help        Show this help message
#
# Examples:
#   ./dev.sh lint --dir unique_sdk
#   ./dev.sh test --dir unique_mcp
#   ./dev.sh coverage --dir unique_toolkit
#   ./dev.sh coverage --dir unique_toolkit --no-baseline
#   ./dev.sh typecheck --dir unique_sdk --no-baseline
#   ./dev.sh all --dir unique_mcp
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Defaults
PACKAGE_DIR="."
BASE_REF="origin/main"
NO_BASELINE=false
FIX_MODE=false
COMMAND=""
EXTRA_ARGS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dir)
            PACKAGE_DIR="$2"
            shift 2
            ;;
        --no-baseline)
            NO_BASELINE=true
            shift
            ;;
        --base-ref)
            BASE_REF="$2"
            shift 2
            ;;
        --fix)
            FIX_MODE=true
            shift
            ;;
        -h|--help)
            cat << 'HELP'
Development helper script for running CI checks locally
Auto-detects package manager (poetry vs uv) based on pyproject.toml

Usage: ./dev.sh <command> [options]

Commands:
  lint              Run ruff linter (check mode)
  lint --fix        Run ruff linter with auto-fix
  format            Run ruff formatter
  test              Run pytest
  coverage          Run pytest with coverage (diff-based like CI)
  typecheck         Run basedpyright type checker
  depcheck          Run deptry dependency checker
  all               Run lint, typecheck, depcheck, and test

Options:
  --dir <path>      Package directory (default: current directory)
  --no-baseline     Skip baseline computation for coverage/typecheck
  --base-ref <ref>  Base branch for diff comparison (default: origin/main)
  -h, --help        Show this help message

Examples:
  ./dev.sh lint --dir unique_sdk
  ./dev.sh test --dir unique_mcp
  ./dev.sh coverage --dir unique_toolkit
  ./dev.sh coverage --dir unique_toolkit --no-baseline
  ./dev.sh typecheck --dir unique_sdk --no-baseline
  ./dev.sh all --dir unique_mcp
HELP
            exit 0
            ;;
        *)
            if [[ -z "$COMMAND" ]]; then
                COMMAND="$1"
            else
                EXTRA_ARGS+=("$1")
            fi
            shift
            ;;
    esac
done

if [[ -z "$COMMAND" ]]; then
    print_error "No command specified. Use -h for help."
    exit 1
fi

# Change to package directory
cd "$PACKAGE_DIR"
PACKAGE_DIR=$(pwd)

# Detect package manager
detect_package_manager() {
    if [[ ! -f "pyproject.toml" ]]; then
        print_error "No pyproject.toml found in $(pwd)"
        exit 1
    fi
    
    if [[ -f "uv.lock" ]] || grep -q "uv_build" pyproject.toml 2>/dev/null; then
        echo "uv"
    elif grep -q "\[tool\.poetry\]" pyproject.toml 2>/dev/null; then
        echo "poetry"
    else
        print_error "Could not detect package manager (poetry or uv)"
        exit 1
    fi
}

PM=$(detect_package_manager)
print_info "Package manager: $PM | Directory: $PACKAGE_DIR"

# Get run command
if [[ "$PM" == "uv" ]]; then
    RUN="uv run"
else
    RUN="poetry run"
fi

# Get package name
get_package_name() {
    if [[ "$PM" == "uv" ]]; then
        grep -A1 "^\[project\]" pyproject.toml | grep "^name" | sed 's/.*= *"\([^"]*\)".*/\1/' | tr '-' '_'
    else
        grep -A5 "^\[tool\.poetry\]" pyproject.toml | grep "^name" | sed 's/.*= *"\([^"]*\)".*/\1/' | tr '-' '_'
    fi
}

# =============================================================================
# Commands
# =============================================================================

cmd_lint() {
    if [[ "$FIX_MODE" == true ]]; then
        print_info "Running ruff check --fix..."
        $RUN ruff check . --fix "${EXTRA_ARGS[@]}"
    else
        print_info "Running ruff check..."
        $RUN ruff check . "${EXTRA_ARGS[@]}"
    fi
    print_success "Lint passed!"
}

cmd_format() {
    print_info "Running ruff format..."
    $RUN ruff format . "${EXTRA_ARGS[@]}"
    print_success "Format complete!"
}

cmd_test() {
    print_info "Running pytest..."
    $RUN pytest "${EXTRA_ARGS[@]}"
    print_success "Tests passed!"
}

cmd_depcheck() {
    print_info "Running deptry..."
    $RUN deptry . "${EXTRA_ARGS[@]}"
    print_success "Dependency check passed!"
}

cmd_coverage() {
    PACKAGE_NAME=$(get_package_name)
    
    if [[ "$NO_BASELINE" == true ]]; then
        # Simple coverage without diff
        print_info "Running coverage (no baseline)..."
        $RUN pytest --cov="$PACKAGE_NAME" --cov-report=term-missing "${EXTRA_ARGS[@]}"
    else
        # Diff-based coverage like CI
        print_info "Running diff-based coverage against $BASE_REF..."
        
        # Check for uncommitted changes
        HAS_CHANGES=false
        if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
            HAS_CHANGES=true
        fi
        
        if [[ "$HAS_CHANGES" == true ]]; then
            echo ""
            print_error "You have uncommitted changes."
            print_error "Diff-based coverage requires a clean workspace."
            echo ""
            echo "Please either:"
            echo "  1. Commit your changes:  git add . && git commit -m 'WIP'"
            echo "  2. Stash your changes:   git stash"
            echo ""
            echo "Then run this command again."
            echo ""
            exit 1
        fi
        
        # Check if the CI script exists
        SCRIPT_PATH="$(git rev-parse --show-toplevel)/.github/scripts/check-coverage.sh"
        if [[ -f "$SCRIPT_PATH" ]]; then
            bash "$SCRIPT_PATH" "$PACKAGE_DIR" --base-ref "$BASE_REF" --runner "$RUN" "${EXTRA_ARGS[@]}"
        else
            print_warn "CI script not found, falling back to simple coverage"
            $RUN pytest --cov="$PACKAGE_NAME" --cov-report=term-missing "${EXTRA_ARGS[@]}"
        fi
    fi
    print_success "Coverage complete!"
}

cmd_typecheck() {
    if [[ "$NO_BASELINE" == true ]]; then
        # Simple typecheck without baseline
        print_info "Running basedpyright (no baseline)..."
        $RUN basedpyright "${EXTRA_ARGS[@]}"
        print_success "Type check complete!"
        return
    fi
    
    # Type check with cached baseline (stored in /tmp)
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    PACKAGE_NAME=$(basename "$PACKAGE_DIR")
    BASE_SHA=$(git rev-parse "$BASE_REF" 2>/dev/null || echo "unknown")
    CACHE_DIR="/tmp/ai-dev-baselines/$PACKAGE_NAME"
    BASELINE_FILE="$CACHE_DIR/baseline-${BASE_SHA:0:12}.json"
    
    print_info "Running type check with baseline against $BASE_REF (${BASE_SHA:0:8})..."
    
    # Check if cached baseline exists
    if [[ -f "$BASELINE_FILE" ]]; then
        print_info "Using cached baseline: $BASELINE_FILE"
    else
        print_info "Computing baseline (first time or base branch updated)..."
        
        mkdir -p "$CACHE_DIR"
        
        # Check for uncommitted changes
        HAS_CHANGES=false
        if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
            HAS_CHANGES=true
        fi
        
        if [[ "$HAS_CHANGES" == true ]]; then
            echo ""
            print_error "You have uncommitted changes."
            print_error "Baseline computation requires a clean workspace to checkout $BASE_REF."
            echo ""
            echo "Please either:"
            echo "  1. Commit your changes:  git add . && git commit -m 'WIP'"
            echo "  2. Stash your changes:   git stash"
            echo ""
            echo "Then run this command again. After baseline is cached, you can:"
            echo "  - Unstash: git stash pop"
            echo "  - Or continue working on your commit"
            echo ""
            exit 1
        fi
        
        # Save current branch name (not SHA, to avoid detached HEAD)
        CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)
        if [[ -z "$CURRENT_BRANCH" ]]; then
            print_error "Already in detached HEAD state. Please checkout a branch first."
            exit 1
        fi
        print_info "Current branch: $CURRENT_BRANCH"
        
        # Function to restore original state
        restore_branch() {
            print_info "Restoring to branch: $CURRENT_BRANCH"
            rm -rf .basedpyright 2>/dev/null || true
            git checkout "$CURRENT_BRANCH" --quiet 2>/dev/null || git checkout "$CURRENT_BRANCH"
        }
        
        # Set trap to restore branch on any error or exit
        trap restore_branch EXIT
        
        # Checkout base ref (this creates detached HEAD, which is expected)
        print_info "Checking out $BASE_REF for baseline..."
        git checkout "$BASE_REF" --quiet 2>/dev/null || git checkout "$BASE_SHA" --quiet
        
        # Install deps and generate baseline using --writebaseline (same as CI)
        if [[ "$PM" == "uv" ]]; then
            uv sync --quiet 2>/dev/null || true
        else
            poetry install --quiet 2>/dev/null || true
        fi
        
        # Create .basedpyright directory and run with --writebaseline
        print_info "Generating baseline from $BASE_REF using --writebaseline..."
        mkdir -p .basedpyright
        $RUN basedpyright --writebaseline 2>&1 || true
        
        # Copy baseline to cache
        if [[ -f .basedpyright/baseline.json ]]; then
            cp .basedpyright/baseline.json "$BASELINE_FILE"
            print_success "Baseline created with $(jq '[.files[] | length] | add // 0' "$BASELINE_FILE" 2>/dev/null || echo "?") known errors"
        else
            # No errors in base branch, create empty baseline
            echo '{"files":{}}' > "$BASELINE_FILE"
            print_success "Baseline created (no errors in $BASE_REF)"
        fi
        
        # Clean up .basedpyright on base branch before switching back
        rm -rf .basedpyright 2>/dev/null || true
        
        # Remove trap before manually restoring (to avoid double execution)
        trap - EXIT
        
        # Return to original branch
        print_info "Returning to branch: $CURRENT_BRANCH"
        git checkout "$CURRENT_BRANCH" --quiet 2>/dev/null || {
            print_error "Failed to checkout $CURRENT_BRANCH, trying without --quiet..."
            git checkout "$CURRENT_BRANCH"
        }
        
        # Reinstall deps for current branch
        if [[ "$PM" == "uv" ]]; then
            uv sync --quiet 2>/dev/null || true
        else
            poetry install --quiet 2>/dev/null || true
        fi
        
        print_success "Baseline cached at: $BASELINE_FILE"
        
        # Clean up old baselines (keep only latest 3)
        ls -t "$CACHE_DIR"/baseline-*.json 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null || true
    fi
    
    # Copy cached baseline to .basedpyright/baseline.json so basedpyright uses it
    print_info "Running basedpyright with baseline..."
    mkdir -p .basedpyright
    cp "$BASELINE_FILE" .basedpyright/baseline.json
    
    # Ensure cleanup happens even on error
    cleanup_basedpyright() {
        rm -rf .basedpyright 2>/dev/null || true
    }
    trap cleanup_basedpyright EXIT
    
    set +e
    $RUN basedpyright "${EXTRA_ARGS[@]}"
    EXIT_CODE=$?
    set -e
    
    # Clean up .basedpyright directory
    trap - EXIT
    rm -rf .basedpyright 2>/dev/null || true
    
    if [[ $EXIT_CODE -eq 0 ]]; then
        print_success "Type check complete! No new type errors."
    else
        print_warn "Type check found new errors (exit code: $EXIT_CODE)"
    fi
}

cmd_all() {
    print_info "Running all checks..."
    echo ""
    
    print_info "1/4 Linting..."
    $RUN ruff check .
    print_success "Lint passed!"
    echo ""
    
    print_info "2/4 Type checking..."
    if [[ "$NO_BASELINE" == true ]]; then
        $RUN basedpyright
    else
        SCRIPT_PATH="$(git rev-parse --show-toplevel)/.github/scripts/check-types.sh"
        if [[ -f "$SCRIPT_PATH" ]]; then
            bash "$SCRIPT_PATH" "$PACKAGE_DIR" --base-ref "$BASE_REF" || true
        else
            $RUN basedpyright
        fi
    fi
    print_success "Type check passed!"
    echo ""
    
    print_info "3/4 Dependency check..."
    $RUN deptry .
    print_success "Dependency check passed!"
    echo ""
    
    print_info "4/4 Running tests..."
    $RUN pytest
    print_success "Tests passed!"
    echo ""
    
    print_success "All checks passed!"
}

# =============================================================================
# Execute command
# =============================================================================

case $COMMAND in
    lint)       cmd_lint ;;
    format)     cmd_format ;;
    test)       cmd_test ;;
    coverage)   cmd_coverage ;;
    typecheck)  cmd_typecheck ;;
    depcheck)   cmd_depcheck ;;
    all)        cmd_all ;;
    *)
        print_error "Unknown command: $COMMAND"
        echo "Use -h for help."
        exit 1
        ;;
esac
