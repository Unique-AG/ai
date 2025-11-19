#!/usr/bin/env bash
set -e

# Parses basedpyright JSON output and reports errors

# Source common library
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME=$(basename "$0")
VERSION="1.0.0"
source "$SCRIPT_DIR/lib/common.sh"

# Help function
show_help() {
    cat << EOF
${SCRIPT_NAME} - Parse and report type errors from basedpyright JSON output

USAGE:
    ${SCRIPT_NAME} [OPTIONS] <package_dir> [json_file]
    ${SCRIPT_NAME} -h | --help
    ${SCRIPT_NAME} --version

DESCRIPTION:
    This script parses basedpyright JSON output and reports type errors.
    It can run in local mode (display errors) or CI mode (post to PR via reviewdog).

ARGUMENTS:
    package_dir          Path to package directory (required)
    json_file            Path to basedpyright JSON output (default: /tmp/basedpyright.json)

OPTIONS:
    -h, --help           Show this help message and exit
    -v, --version        Show version information and exit
    -r, --reviewdog PATH Path to reviewdog binary (enables CI mode)
    -b, --base-ref REF   Base branch/ref for comparison (default: main)

EXAMPLES:
    # Basic usage
    ${SCRIPT_NAME} unique_toolkit

    # Specify package and JSON file
    ${SCRIPT_NAME} unique_sdk /tmp/basedpyright.json

    # CI mode with reviewdog
    ${SCRIPT_NAME} -r /usr/bin/reviewdog -b main unique_toolkit

    # All options
    ${SCRIPT_NAME} -r /usr/bin/reviewdog -b origin/main unique_toolkit /tmp/basedpyright.json

EXIT CODES:
    0    No new type errors found
    1    New type errors found or error occurred

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
JSON_FILE="/tmp/basedpyright.json"
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
    if [ "$JSON_FILE" = "/tmp/basedpyright.json" ]; then
        JSON_FILE="$1"
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

# Validate JSON file exists
if [ ! -f "$JSON_FILE" ]; then
    print_error "JSON file '$JSON_FILE' does not exist"
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

print_info "Parsing type errors from JSON output"
print_info "Package: $PACKAGE_DIR"
print_info "JSON file: $JSON_FILE"
if [ "$USE_REVIEWDOG" = true ]; then
    print_info "Mode: CI (reviewdog)"
    print_info "Base ref: $BASE_REF"
else
    print_info "Mode: Local (display)"
fi
echo ""

# Extract errors from JSON (make paths relative to repo root)
REPO_ROOT=$(cd .. && pwd)
ERRORS_FILE="/tmp/basedpyright_errors.txt"

jq -r --arg repo_root "$REPO_ROOT" '
    .generalDiagnostics[]? | 
    select(.file != null and .range != null) | 
    (
        ($repo_root + "/") as $prefix | 
        (if .file | startswith($prefix) then .file | ltrimstr($prefix) else .file end) as $rel_path | 
        (.range.start.line + 1 | tostring) as $line | 
        (.range.start.character + 1 | tostring) as $col | 
        (.severity // "warning") as $severity | 
        (.message | split("\n")[0]) as $msg | 
        "\($rel_path):\($line):\($col) - \($severity): \($msg)"
    )
' "$JSON_FILE" > "$ERRORS_FILE" 2>/dev/null || {
    print_error "Failed to parse basedpyright JSON output"
    exit 1
}

# Count errors
ERROR_COUNT=$(wc -l < "$ERRORS_FILE" | tr -d ' ')

if [ "$ERROR_COUNT" -eq 0 ]; then
    print_success "No new type errors found! Baseline successfully filtered out existing errors."
    echo ""
    print_success "Your changes don't introduce new type errors."
    exit 0
fi

# There are errors - handle based on mode
if [ "$USE_REVIEWDOG" = true ] && [ -n "$REVIEWDOG_PATH" ]; then
    # CI mode with reviewdog - post comments to PR
    print_warning "Found $ERROR_COUNT new type error(s) - posting to PR"
    echo ""
    
    # Change to repo root for reviewdog (it needs to be in repo root for git diff)
    cd "$REPO_ROOT"
    
    # Run reviewdog
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
    print_error "Type check failed with $ERROR_COUNT new error(s)"
    exit 1  # Fail the workflow to enforce fixing errors
else
    # Local mode or no reviewdog - just display errors
    print_warning "Type errors found"
    print_error "Found $ERROR_COUNT new type error(s):"
    echo ""
    cat "$ERRORS_FILE"
    echo ""
    print_error "Please fix these type errors before committing."
    exit 1
fi
