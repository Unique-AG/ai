#!/usr/bin/env bash
set -e

# Pre-commit friendly script to check for new dependency issues
# Compares current branch against base branch (main) and fails if new issues are found

# Source common library
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME=$(basename "$0")
VERSION="1.0.0"
source "$SCRIPT_DIR/lib/common.sh"

# Help function
show_help() {
    cat << EOF
${SCRIPT_NAME} - Check for new dependency issues (pre-commit friendly)

USAGE:
    ${SCRIPT_NAME} [OPTIONS] <package_dir> [base_branch]
    ${SCRIPT_NAME} -h | --help
    ${SCRIPT_NAME} --version

DESCRIPTION:
    This script runs deptry on the current branch and compares it against
    a base branch (default: main) to detect new dependency issues.
    Designed for use in pre-commit hooks.

ARGUMENTS:
    package_dir          Path to package directory (required)
    base_branch          Base branch to compare against (default: main)

OPTIONS:
    -h, --help           Show this help message and exit
    -v, --version        Show version information and exit
    -b, --base BRANCH    Base branch to compare against (default: main)
    -r, --runner CMD     Command executor prefix (e.g., "poetry run" or "uv run", default: auto-detect)

EXAMPLES:
    # Basic usage
    ${SCRIPT_NAME} unique_mcp

    # Compare against different base branch
    ${SCRIPT_NAME} -b develop unique_mcp

    # Specify runner
    ${SCRIPT_NAME} -r "poetry run" unique_toolkit

EXIT CODES:
    0    No new dependency issues found
    1    New dependency issues found or error occurred

AUTHOR:
    Unique AI Toolkit

VERSION:
    ${VERSION}
EOF
}

# ============================================================================
# SETUP
# ============================================================================

# Initialize variables with defaults
PACKAGE_DIR=""
BASE_BRANCH="main"
RUNNER=""

# Convert long options to short options for getopts
ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            ARGS+=(-h)
            shift
            ;;
        --version)
            ARGS+=(-v)
            shift
            ;;
        --base)
            ARGS+=(-b "$2")
            shift 2
            ;;
        --runner)
            ARGS+=(-r "$2")
            shift 2
            ;;
        --)
            ARGS+=("$@")
            break
            ;;
        --*)
            print_error "Unknown long option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

# Reset positional parameters for getopts
set -- "${ARGS[@]}"

# Parse options using getopts
while getopts "hvb:r:" opt; do
    case $opt in
        h)
            show_help
            exit 0
            ;;
        v)
            show_version
            exit 0
            ;;
        b)
            BASE_BRANCH="$OPTARG"
            ;;
        r)
            RUNNER="$OPTARG"
            ;;
        \?)
            print_error "Invalid option: -$OPTARG"
            echo "Use -h or --help for usage information."
            exit 1
            ;;
        :)
            print_error "Option -$OPTARG requires an argument."
            echo "Use -h or --help for usage information."
            exit 1
            ;;
    esac
done

# Shift past the options parsed by getopts
shift $((OPTIND-1))

# Handle remaining positional arguments
if [ $# -gt 0 ]; then
    if [ -z "$PACKAGE_DIR" ]; then
        PACKAGE_DIR="$1"
        shift
    fi
fi

if [ $# -gt 0 ]; then
    if [ "$BASE_BRANCH" = "main" ]; then
        BASE_BRANCH="$1"
        shift
    fi
fi

# Check for extra arguments
if [ $# -gt 0 ]; then
    print_error "Unexpected argument: $1"
    echo "Use --help for usage information."
    exit 1
fi

# Validate required arguments
if [ -z "$PACKAGE_DIR" ]; then
    print_error "Package directory is required"
    echo ""
    show_help
    exit 1
fi

# Resolve package directory to absolute path
if [ ! -d "$PACKAGE_DIR" ]; then
    # Try to find it relative to script location or current directory
    if [ -d "$SCRIPT_DIR/../../$PACKAGE_DIR" ]; then
        PACKAGE_DIR="$SCRIPT_DIR/../../$PACKAGE_DIR"
    elif [ -d "$(pwd)/$PACKAGE_DIR" ]; then
        PACKAGE_DIR="$(pwd)/$PACKAGE_DIR"
    else
        print_error "Package directory '$PACKAGE_DIR' does not exist"
        echo ""
        show_help
        exit 1
    fi
fi

# Convert to absolute path
PACKAGE_DIR="$(cd "$PACKAGE_DIR" && pwd)"

# Find repo root (parent of .github)
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Auto-detect runner if not specified
if [ -z "$RUNNER" ]; then
    if [ -f "$PACKAGE_DIR/pyproject.toml" ]; then
        # Check if it uses uv (has uv_build in build-system)
        if grep -q "uv_build" "$PACKAGE_DIR/pyproject.toml" 2>/dev/null; then
            RUNNER="uv run"
        elif [ -f "$PACKAGE_DIR/poetry.lock" ] || grep -q "poetry" "$PACKAGE_DIR/pyproject.toml" 2>/dev/null; then
            RUNNER="poetry run"
        else
            RUNNER="uv run"  # Default to uv
        fi
    else
        RUNNER="uv run"  # Default to uv
    fi
fi

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a git repository"
    exit 1
fi

# Get current branch
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "HEAD")

# Check if base branch exists
if ! git show-ref --verify --quiet "refs/heads/$BASE_BRANCH" && ! git show-ref --verify --quiet "refs/remotes/origin/$BASE_BRANCH"; then
    print_warning "Base branch '$BASE_BRANCH' not found locally or remotely"
    print_info "Running deptry on current branch only (no comparison)"
    BASE_BRANCH=""
fi

# ============================================================================
# SCRIPT LOGIC
# ============================================================================

print_info "Checking dependencies"
print_info "Package: $PACKAGE_DIR"
print_info "Current branch: $CURRENT_BRANCH"
if [ -n "$BASE_BRANCH" ]; then
    print_info "Base branch: $BASE_BRANCH"
fi
print_info "Runner: $RUNNER"
echo ""

TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

BASE_JSON="$TEMP_DIR/deptry-base.json"
CURRENT_JSON="$TEMP_DIR/deptry-current.json"
COMPARISON_JSON="$TEMP_DIR/deptry-comparison.json"

# Run deptry on current branch
print_info "Running deptry on current branch..."
cd "$PACKAGE_DIR"
bash "$SCRIPT_DIR/run-deptry.sh" -r "$RUNNER" -o "$CURRENT_JSON" "$PACKAGE_DIR" || {
    print_error "Failed to run deptry on current branch"
    exit 1
}

# If base branch is specified, compare
if [ -n "$BASE_BRANCH" ]; then
    print_info "Running deptry on base branch '$BASE_BRANCH'..."
    
    # Create worktree for base branch
    BASE_WORKTREE="$TEMP_DIR/base-worktree"
    if git worktree add "$BASE_WORKTREE" "$BASE_BRANCH" > /dev/null 2>&1; then
        BASE_PACKAGE_DIR="$BASE_WORKTREE/$(basename "$PACKAGE_DIR")"
        
        if [ -d "$BASE_PACKAGE_DIR" ]; then
            cd "$BASE_PACKAGE_DIR"
            bash "$SCRIPT_DIR/run-deptry.sh" -r "$RUNNER" -o "$BASE_JSON" "$BASE_PACKAGE_DIR" || {
                print_warning "Failed to run deptry on base branch, continuing with current branch only"
                BASE_BRANCH=""
            }
        else
            print_warning "Package directory not found in base branch, continuing with current branch only"
            BASE_BRANCH=""
        fi
        
        # Cleanup worktree
        cd "$REPO_ROOT"
        git worktree remove "$BASE_WORKTREE" > /dev/null 2>&1 || true
    else
        print_warning "Failed to create worktree for base branch, continuing with current branch only"
        BASE_BRANCH=""
    fi
    
    # Compare if we have both results
    if [ -n "$BASE_BRANCH" ] && [ -f "$BASE_JSON" ]; then
        print_info "Comparing dependency issues..."
        cd "$REPO_ROOT"
        bash "$SCRIPT_DIR/compare-dependency-issues.sh" \
            -o "$COMPARISON_JSON" \
            "$PACKAGE_DIR" \
            "$BASE_JSON" \
            "$CURRENT_JSON" || {
            # Comparison found new issues
            NEW_COUNT=$(jq -r '.summary.new_issues // 0' "$COMPARISON_JSON" 2>/dev/null || echo "0")
            if [ "$NEW_COUNT" -gt 0 ]; then
                print_error "Found $NEW_COUNT new dependency issue(s)"
                echo ""
                print_info "New issues:"
                jq -r '.new_issues[] | "  \(.error.code): \(.module) - \(.location.file):\(.location.line)"' "$COMPARISON_JSON" 2>/dev/null || true
                echo ""
                print_error "Please fix these dependency issues before committing."
                exit 1
            fi
        }
        
        # Check if comparison succeeded
        if [ -f "$COMPARISON_JSON" ]; then
            NEW_COUNT=$(jq -r '.summary.new_issues // 0' "$COMPARISON_JSON" 2>/dev/null || echo "0")
            FIXED_COUNT=$(jq -r '.summary.fixed_issues // 0' "$COMPARISON_JSON" 2>/dev/null || echo "0")
            
            if [ "$NEW_COUNT" -gt 0 ]; then
                print_error "Found $NEW_COUNT new dependency issue(s)"
                echo ""
                print_info "New issues:"
                jq -r '.new_issues[] | "  \(.error.code): \(.module) - \(.location.file):\(.location.line)"' "$COMPARISON_JSON" 2>/dev/null || true
                echo ""
                print_error "Please fix these dependency issues before committing."
                exit 1
            elif [ "$FIXED_COUNT" -gt 0 ]; then
                print_success "No new issues found (fixed $FIXED_COUNT issue(s))"
                exit 0
            else
                print_success "No new dependency issues found"
                exit 0
            fi
        fi
    fi
fi

# If no base branch comparison, just check if current branch has issues
ISSUE_COUNT=$(jq 'length' "$CURRENT_JSON" 2>/dev/null || echo "0")
if [ "$ISSUE_COUNT" -gt 0 ]; then
    print_warning "Found $ISSUE_COUNT dependency issue(s) in current branch"
    print_info "Issues:"
    jq -r '.[] | "  \(.error.code): \(.module) - \(.location.file):\(.location.line)"' "$CURRENT_JSON" 2>/dev/null || true
    echo ""
    print_info "Note: Run with base branch comparison to detect only NEW issues"
    # Don't fail if we can't compare - just warn
    exit 0
else
    print_success "No dependency issues found"
    exit 0
fi

