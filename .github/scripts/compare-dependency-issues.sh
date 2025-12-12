#!/usr/bin/env bash
set -e

# Compares deptry results between base branch and current branch
# Shows both new issues introduced and issues fixed

# Source common library
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME=$(basename "$0")
VERSION="1.0.0"
source "$SCRIPT_DIR/lib/common.sh"

# Help function
show_help() {
    cat << EOF
${SCRIPT_NAME} - Compare deptry results between base branch and current branch

USAGE:
    ${SCRIPT_NAME} [OPTIONS] <package_dir> <base_json> <current_json> [output_file]
    ${SCRIPT_NAME} -h | --help
    ${SCRIPT_NAME} --version

DESCRIPTION:
    This script compares deptry JSON outputs from two branches and identifies
    new issues introduced and issues fixed in the current branch.

ARGUMENTS:
    package_dir          Path to package directory (required)
    base_json            Path to deptry JSON from base branch (required)
    current_json         Path to deptry JSON from current branch (required)
    output_file          Path to output JSON file with comparison results (default: /tmp/deptry-comparison.json)

OPTIONS:
    -h, --help           Show this help message and exit
    -v, --version        Show version information and exit
    -o, --output FILE    Path to output JSON file (default: /tmp/deptry-comparison.json)

EXAMPLES:
    # Basic usage
    ${SCRIPT_NAME} unique_mcp /tmp/base.json /tmp/current.json

    # Specify output file
    ${SCRIPT_NAME} -o /tmp/comparison.json unique_mcp /tmp/base.json /tmp/current.json

EXIT CODES:
    0    No new issues found
    1    New issues found

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
BASE_JSON=""
CURRENT_JSON=""
OUTPUT_FILE="/tmp/deptry-comparison.json"

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
        --output)
            ARGS+=(-o "$2")
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
while getopts "hvo:" opt; do
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
    if [ -z "$BASE_JSON" ]; then
        BASE_JSON="$1"
        shift
    fi
fi

if [ $# -gt 0 ]; then
    if [ -z "$CURRENT_JSON" ]; then
        CURRENT_JSON="$1"
        shift
    fi
fi

if [ $# -gt 0 ]; then
    if [ "$OUTPUT_FILE" = "/tmp/deptry-comparison.json" ]; then
        OUTPUT_FILE="$1"
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

if [ -z "$BASE_JSON" ]; then
    print_error "Base JSON file is required"
    echo ""
    show_help
    exit 1
fi

if [ -z "$CURRENT_JSON" ]; then
    print_error "Current JSON file is required"
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

# Resolve JSON file paths to absolute
if [ ! -f "$BASE_JSON" ] && [ -f "$(pwd)/$BASE_JSON" ]; then
    BASE_JSON="$(cd "$(dirname "$(pwd)/$BASE_JSON")" && pwd)/$(basename "$BASE_JSON")"
fi
if [ ! -f "$CURRENT_JSON" ] && [ -f "$(pwd)/$CURRENT_JSON" ]; then
    CURRENT_JSON="$(cd "$(dirname "$(pwd)/$CURRENT_JSON")" && pwd)/$(basename "$CURRENT_JSON")"
fi

# Validate files exist
if [ ! -f "$BASE_JSON" ]; then
    print_error "Base JSON file '$BASE_JSON' does not exist"
    exit 1
fi

if [ ! -f "$CURRENT_JSON" ]; then
    print_error "Current JSON file '$CURRENT_JSON' does not exist"
    exit 1
fi

# ============================================================================
# SCRIPT LOGIC
# ============================================================================

print_info "Comparing dependency issues"
print_info "Package: $PACKAGE_DIR"
print_info "Base JSON: $BASE_JSON"
print_info "Current JSON: $CURRENT_JSON"
echo ""

TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Extract issue signatures from base branch
# Format: error.code|module|location.file|location.line
BASE_ISSUES_FILE="$TEMP_DIR/base-issues.txt"
jq -r '.[] | "\(.error.code)|\(.module)|\(.location.file)|\(.location.line)"' "$BASE_JSON" > "$BASE_ISSUES_FILE" 2>/dev/null || true

# Extract issue signatures from current branch
CURRENT_ISSUES_FILE="$TEMP_DIR/current-issues.txt"
jq -r '.[] | "\(.error.code)|\(.module)|\(.location.file)|\(.location.line)"' "$CURRENT_JSON" > "$CURRENT_ISSUES_FILE" 2>/dev/null || true

# Find new issues (present in current but not in base)
NEW_ISSUES_FILE="$TEMP_DIR/new-issues.txt"
comm -23 <(sort "$CURRENT_ISSUES_FILE") <(sort "$BASE_ISSUES_FILE") > "$NEW_ISSUES_FILE" 2>/dev/null || true

# Find removed/fixed issues (present in base but not in current)
REMOVED_ISSUES_FILE="$TEMP_DIR/removed-issues.txt"
comm -13 <(sort "$CURRENT_ISSUES_FILE") <(sort "$BASE_ISSUES_FILE") > "$REMOVED_ISSUES_FILE" 2>/dev/null || true

# Count issues
TOTAL_NEW=0
TOTAL_REMOVED=0
if [ -s "$NEW_ISSUES_FILE" ]; then
    TOTAL_NEW=$(wc -l < "$NEW_ISSUES_FILE" | tr -d ' ')
fi
if [ -s "$REMOVED_ISSUES_FILE" ]; then
    TOTAL_REMOVED=$(wc -l < "$REMOVED_ISSUES_FILE" | tr -d ' ')
fi

# Build JSON output with comparison results
# Extract full issue details for new issues by matching signatures
NEW_ISSUES_JSON="$TEMP_DIR/new-issues.json"
echo "[]" > "$NEW_ISSUES_JSON"

# For each signature, find matching issue in current JSON and add to array
while IFS='|' read -r error_code module file line; do
    [ -z "$error_code" ] && continue
    jq --slurpfile source "$CURRENT_JSON" \
        --arg code "$error_code" --arg mod "$module" --arg f "$file" --arg l "$line" \
        '. += [$source[0][] | select(.error.code == $code and .module == $mod and .location.file == $f and (.location.line | tostring) == $l)]' \
        "$NEW_ISSUES_JSON" > "${NEW_ISSUES_JSON}.tmp" && mv "${NEW_ISSUES_JSON}.tmp" "$NEW_ISSUES_JSON" 2>/dev/null || true
done < "$NEW_ISSUES_FILE"

# Extract full issue details for removed issues
REMOVED_ISSUES_JSON="$TEMP_DIR/removed-issues.json"
echo "[]" > "$REMOVED_ISSUES_JSON"

# For each signature, find matching issue in base JSON and add to array
while IFS='|' read -r error_code module file line; do
    [ -z "$error_code" ] && continue
    jq --slurpfile source "$BASE_JSON" \
        --arg code "$error_code" --arg mod "$module" --arg f "$file" --arg l "$line" \
        '. += [$source[0][] | select(.error.code == $code and .module == $mod and .location.file == $f and (.location.line | tostring) == $l)]' \
        "$REMOVED_ISSUES_JSON" > "${REMOVED_ISSUES_JSON}.tmp" && mv "${REMOVED_ISSUES_JSON}.tmp" "$REMOVED_ISSUES_JSON" 2>/dev/null || true
done < "$REMOVED_ISSUES_FILE"

# Combine into final JSON
jq -n \
    --slurpfile new "$NEW_ISSUES_JSON" \
    --slurpfile removed "$REMOVED_ISSUES_JSON" \
    --argjson total_new "$TOTAL_NEW" \
    --argjson total_removed "$TOTAL_REMOVED" \
    '{
        summary: {
            new_issues: $total_new,
            fixed_issues: $total_removed
        },
        new_issues: (if ($new | length) > 0 then $new[0] else [] end),
        fixed_issues: (if ($removed | length) > 0 then $removed[0] else [] end)
    }' > "$OUTPUT_FILE"

# Display summary
echo ""
print_info "Comparison summary"
echo "  New issues: $TOTAL_NEW"
echo "  Fixed issues: $TOTAL_REMOVED"
echo ""

if [ "$TOTAL_NEW" -gt 0 ]; then
    print_warning "Found $TOTAL_NEW new dependency issue(s)"
    EXIT_CODE=1
else
    print_success "No new dependency issues found"
    EXIT_CODE=0
fi

if [ "$TOTAL_REMOVED" -gt 0 ]; then
    print_success "Fixed $TOTAL_REMOVED dependency issue(s)"
fi

echo ""
print_info "Comparison results saved to: $OUTPUT_FILE"

exit $EXIT_CODE

