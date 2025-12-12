#!/usr/bin/env bash
set -e

# Reports dependency errors from comparison JSON using reviewdog

# Source common library
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME=$(basename "$0")
VERSION="1.0.0"
source "$SCRIPT_DIR/lib/common.sh"

# Help function
show_help() {
    cat << EOF
${SCRIPT_NAME} - Report dependency errors from comparison JSON

USAGE:
    ${SCRIPT_NAME} [OPTIONS] <package_dir> <comparison_json>
    ${SCRIPT_NAME} -h | --help
    ${SCRIPT_NAME} --version

DESCRIPTION:
    This script reads comparison JSON and reports new dependency issues
    using reviewdog to post comments on the PR.

ARGUMENTS:
    package_dir          Path to package directory (required)
    comparison_json      Path to comparison JSON file (required)

OPTIONS:
    -h, --help           Show this help message and exit
    -v, --version        Show version information and exit
    -r, --reviewdog PATH Path to reviewdog binary (enables CI mode)
    -b, --base-ref REF   Base branch/ref for comparison (default: main)

EXAMPLES:
    # CI mode with reviewdog
    ${SCRIPT_NAME} -r /usr/bin/reviewdog -b main unique_mcp /tmp/comparison.json

    # Local mode (display only)
    ${SCRIPT_NAME} unique_mcp /tmp/comparison.json

EXIT CODES:
    0    No new dependency issues found
    1    New dependency issues found

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
COMPARISON_JSON=""
REVIEWDOG_PATH=""
USE_REVIEWDOG=false
BASE_REF="main"

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
        --reviewdog)
            ARGS+=(-r "$2")
            USE_REVIEWDOG=true
            shift 2
            ;;
        --base-ref)
            ARGS+=(-b "$2")
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
while getopts "hvr:b:" opt; do
    case $opt in
        h)
            show_help
            exit 0
            ;;
        v)
            show_version
            exit 0
            ;;
        r)
            REVIEWDOG_PATH="$OPTARG"
            USE_REVIEWDOG=true
            ;;
        b)
            BASE_REF="$OPTARG"
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
    if [ -z "$COMPARISON_JSON" ]; then
        COMPARISON_JSON="$1"
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

if [ -z "$COMPARISON_JSON" ]; then
    print_error "Comparison JSON file is required"
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
        exit 1
    fi
fi
PACKAGE_DIR="$(cd "$PACKAGE_DIR" && pwd)"

# Resolve JSON file path to absolute
if [ ! -f "$COMPARISON_JSON" ] && [ -f "$(pwd)/$COMPARISON_JSON" ]; then
    COMPARISON_JSON="$(cd "$(dirname "$(pwd)/$COMPARISON_JSON")" && pwd)/$(basename "$COMPARISON_JSON")"
fi

# Validate files exist
if [ ! -f "$COMPARISON_JSON" ]; then
    print_error "Comparison JSON file '$COMPARISON_JSON' does not exist"
    exit 1
fi

# ============================================================================
# SCRIPT LOGIC
# ============================================================================

print_info "Reporting dependency errors"
print_info "Package: $PACKAGE_DIR"
print_info "Comparison JSON: $COMPARISON_JSON"
if [ "$USE_REVIEWDOG" = true ]; then
    print_info "Mode: CI (reviewdog)"
    print_info "Base ref: $BASE_REF"
else
    print_info "Mode: Local (display)"
fi
echo ""

# Get summary
NEW_COUNT=$(jq -r '.summary.new_issues // 0' "$COMPARISON_JSON" 2>/dev/null || echo "0")
FIXED_COUNT=$(jq -r '.summary.fixed_issues // 0' "$COMPARISON_JSON" 2>/dev/null || echo "0")

if [ "$NEW_COUNT" -eq 0 ]; then
    print_success "No new dependency issues found!"
    if [ "$FIXED_COUNT" -gt 0 ]; then
        print_success "Fixed $FIXED_COUNT dependency issue(s)"
    fi
    exit 0
fi

# Extract new issues and format for reviewdog
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ERRORS_FILE="/tmp/deptry_errors.txt"

# Format issues for reviewdog: file:line:column - DEPCODE: message
jq -r --arg package_dir "$PACKAGE_DIR" '
    .new_issues[]? | 
    select(.error != null and .location != null) | 
    (
        ($package_dir + "/" + (.location.file // "")) as $rel_path | 
        ((.location.line // 1) | tostring) as $line | 
        ((.location.column // 1) | tostring) as $col | 
        (.error.code // "DEP001") as $code | 
        (.error.message // "Dependency issue") as $msg | 
        "\($rel_path):\($line):\($col) - \($code): \($msg)"
    )
' "$COMPARISON_JSON" > "$ERRORS_FILE" 2>/dev/null || {
    print_error "Failed to parse comparison JSON"
    exit 1
}

# There are new issues - handle based on mode
if [ "$USE_REVIEWDOG" = true ] && [ -n "$REVIEWDOG_PATH" ]; then
    # CI mode with reviewdog - post comments to PR
    print_warning "Found $NEW_COUNT new dependency issue(s) - posting to PR"
    echo ""
    
    # Change to repo root for reviewdog
    cd "$REPO_ROOT"
    
    # Run reviewdog (always succeeds, just posts comments)
    cat "$ERRORS_FILE" | \
        "$REVIEWDOG_PATH" \
            -efm="%f:%l:%c - %m" \
            -reporter=github-pr-review \
            -fail-on-error=false \
            -filter-mode=added \
            -level=warning \
            -diff="git diff origin/${BASE_REF}" \
            -tee || true
    
    echo ""
    print_warning "Reviewdog completed"
    print_warning "Found $NEW_COUNT new dependency issue(s) (reported as warnings, will not block merge)"
    
    if [ "$FIXED_COUNT" -gt 0 ]; then
        print_success "Fixed $FIXED_COUNT dependency issue(s)"
    fi
    
    # Don't exit with error code in CI mode - just report issues
    exit 0
else
    # Local mode - just display errors
    print_warning "Dependency issues found"
    print_error "Found $NEW_COUNT new dependency issue(s):"
    echo ""
    cat "$ERRORS_FILE"
    echo ""
    
    if [ "$FIXED_COUNT" -gt 0 ]; then
        print_success "Fixed $FIXED_COUNT dependency issue(s)"
    fi
    
    print_error "Please fix these dependency issues before committing."
    exit 1
fi

