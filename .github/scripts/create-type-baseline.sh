#!/usr/bin/env bash
set -e

# Creates a type checking baseline from a specified branch

# Source common library
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME=$(basename "$0")
VERSION="1.0.0"
source "$SCRIPT_DIR/lib/common.sh"

# Help function
show_help() {
    cat << EOF
${SCRIPT_NAME} - Create type checking baseline from specified branch

USAGE:
    ${SCRIPT_NAME} [OPTIONS] <package_dir> [branch]
    ${SCRIPT_NAME} -h | --help
    ${SCRIPT_NAME} --version

DESCRIPTION:
    This script creates a type checking baseline by running basedpyright
    on a specified branch. The baseline captures existing type errors so
    that only new errors introduced by your changes are reported.

ARGUMENTS:
    package_dir          Path to package directory (required)
    branch               Branch/ref to create baseline from (default: main)

OPTIONS:
    -h, --help           Show this help message and exit
    -v, --version        Show version information and exit
    -c, --ci             CI mode - use git checkout instead of stash/restore
    -o, --output FILE    Output file for baseline (default: /tmp/baseline.json)
    -r, --runner CMD     Command executor prefix (e.g., "poetry run" or "uv run", default: "poetry run")

EXAMPLES:
    # Basic usage (with Poetry)
    ${SCRIPT_NAME} unique_toolkit

    # With uv
    ${SCRIPT_NAME} -r "uv run" -c unique_mcp main

    # CI mode with custom output
    ${SCRIPT_NAME} -c -o /tmp/my-baseline.json unique_toolkit main

EXAMPLES:
    # Basic usage
    ${SCRIPT_NAME} unique_toolkit

    # Specify package and branch
    ${SCRIPT_NAME} unique_sdk origin/main

    # CI mode
    ${SCRIPT_NAME} -c unique_toolkit main

    # Custom output file
    ${SCRIPT_NAME} -o /tmp/my-baseline.json unique_toolkit main

EXIT CODES:
    0    Baseline created successfully
    1    Error occurred

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
BRANCH="main"
CI_MODE=false
OUTPUT_FILE="/tmp/baseline.json"
RUNNER="poetry run"

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
        --ci)
            ARGS+=(-c)
            shift
            ;;
        --output)
            ARGS+=(-o "$2")
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
while getopts "hvo:cr:" opt; do
    case $opt in
        h)
            show_help
            exit 0
            ;;
        v)
            show_version
            exit 0
            ;;
        o)
            OUTPUT_FILE="$OPTARG"
            ;;
        c)
            CI_MODE=true
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
    if [ "$BRANCH" = "main" ]; then
        BRANCH="$1"
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

# Validate package directory exists
if [ ! -d "$PACKAGE_DIR" ]; then
    print_error "Package directory '$PACKAGE_DIR' does not exist"
    echo ""
    show_help
    exit 1
fi

# Change to package directory
cd "$PACKAGE_DIR" || {
    print_error "Failed to change to package directory: $PACKAGE_DIR"
    exit 1
}

# ============================================================================
# SCRIPT LOGIC
# ============================================================================

print_info "Creating baseline from $BRANCH"
print_info "Package: $PACKAGE_DIR"
print_info "Branch: $BRANCH"
print_info "Output: $OUTPUT_FILE"
echo ""

if [ "$CI_MODE" = true ]; then
    # In CI, checkout the base branch directly
    print_info "Checking out base branch for baseline..."
    git checkout "origin/$BRANCH" --quiet 2>/dev/null || {
        print_error "Failed to checkout origin/$BRANCH"
        exit 1
    }
else
    # Local mode: stash changes and checkout
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    print_info "Current branch: $CURRENT_BRANCH"
    print_info "Stashing any uncommitted changes..."
    git stash push -m "type-check-baseline-temp" --quiet 2>/dev/null || true
    
    print_info "Switching to $BRANCH..."
    git checkout "$BRANCH" --quiet 2>/dev/null || {
        print_error "Failed to checkout $BRANCH"
        git stash pop --quiet 2>/dev/null || true
        exit 1
    }
fi

# Create baseline directory
mkdir -p .basedpyright

# Run basedpyright with --writebaseline to create baseline
print_info "Running basedpyright --writebaseline on $BRANCH..."
print_info "Using runner: $RUNNER"
$RUNNER basedpyright --writebaseline 2>&1 || {
    print_warning "basedpyright exited with non-zero status (expected if there are errors)"
}

# Check if baseline was created
if [ -f .basedpyright/baseline.json ]; then
    print_success "Baseline created successfully"
    echo "  Baseline size: $(wc -c < .basedpyright/baseline.json) bytes"
    # Count errors in baseline
    ERROR_COUNT=$(jq '[.files[] | length] | add // 0' .basedpyright/baseline.json 2>/dev/null || echo "0")
    echo "  Known errors in baseline: $ERROR_COUNT"
else
    print_success "No baseline created (no errors in $BRANCH)"
fi

# Copy baseline to output location
cp .basedpyright/baseline.json "$OUTPUT_FILE" 2>/dev/null || touch "$OUTPUT_FILE"
print_info "Baseline saved to: $OUTPUT_FILE"

# Checkout back to original branch
if [ "$CI_MODE" = true ]; then
    print_info "Switching back to PR branch..."
    # Discard all local changes then checkout (uv run may have modified lock files)
    git checkout -- . 2>/dev/null || true
    git clean -fd 2>/dev/null || true
    git checkout - --quiet
else
    print_info "Switching back to $CURRENT_BRANCH..."
    git checkout "$CURRENT_BRANCH" --quiet
    print_info "Restoring any stashed changes..."
    git stash pop --quiet 2>/dev/null || true
fi

print_success "Baseline creation complete"
