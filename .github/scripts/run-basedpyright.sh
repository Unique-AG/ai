#!/usr/bin/env bash
set -e

# Runs basedpyright and outputs JSON to stdout

# Source common library
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME=$(basename "$0")
VERSION="1.0.0"
source "$SCRIPT_DIR/lib/common.sh"

# Help function
show_help() {
    cat << EOF
${SCRIPT_NAME} - Run basedpyright and output JSON results

USAGE:
    ${SCRIPT_NAME} [OPTIONS] <package_dir> [output_file]
    ${SCRIPT_NAME} -h | --help
    ${SCRIPT_NAME} --version

DESCRIPTION:
    This script runs basedpyright on a package and outputs the results
    as JSON. The JSON output can be used by other scripts for error
    reporting and baseline comparison.

ARGUMENTS:
    package_dir          Path to package directory (required)
    output_file          Path to output JSON file (default: /tmp/basedpyright.json)

OPTIONS:
    -h, --help           Show this help message and exit
    -v, --version        Show version information and exit
    -o, --output FILE    Path to output JSON file (default: /tmp/basedpyright.json)

EXAMPLES:
    # Basic usage
    ${SCRIPT_NAME} unique_toolkit

    # Specify package directory and output file
    ${SCRIPT_NAME} unique_sdk /tmp/my-results.json

    # Using output option
    ${SCRIPT_NAME} -o /tmp/my-results.json unique_toolkit

EXIT CODES:
    0    Basedpyright completed (may have errors, check JSON output)
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
OUTPUT_FILE="/tmp/basedpyright.json"

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
    if [ "$OUTPUT_FILE" = "/tmp/basedpyright.json" ]; then
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

print_info "Running basedpyright"
print_info "Package: $PACKAGE_DIR"
print_info "Output: $OUTPUT_FILE"
echo ""

# Run basedpyright with JSON output
# basedpyright may output informational messages before the JSON, so we need to extract just the JSON
TEMP_OUTPUT=$(mktemp)
poetry run basedpyright --outputjson > "$TEMP_OUTPUT" 2>&1 || {
    print_warning "basedpyright exited with non-zero status (expected if there are errors)"
}

# Extract JSON from output (basedpyright may print messages before the JSON)
# Find the first line starting with { and extract everything from there to the end
# This handles multi-line JSON objects
awk '/^{/,0' "$TEMP_OUTPUT" > "$OUTPUT_FILE"

# Validate the extracted JSON is valid
if ! jq empty "$OUTPUT_FILE" 2>/dev/null; then
    # If validation failed, try a more robust extraction using Python
    python3 -c "
import sys
import json
try:
    with open('$TEMP_OUTPUT', 'r') as f:
        content = f.read()
    # Find the first { and try to parse JSON from there
    start = content.find('{')
    if start != -1:
        json_str = content[start:]
        # Try to parse and re-serialize to ensure valid JSON
        json_obj = json.loads(json_str)
        with open('$OUTPUT_FILE', 'w') as f:
            json.dump(json_obj, f)
    else:
        sys.exit(1)
except:
    sys.exit(1)
" 2>/dev/null || {
        print_warning "Could not extract valid JSON, using raw output"
        cp "$TEMP_OUTPUT" "$OUTPUT_FILE"
    }
fi

rm -f "$TEMP_OUTPUT"

# Show summary
echo ""
print_info "Basedpyright summary"
jq '{version, time, summary, diagnostic_count: (.generalDiagnostics | length)}' "$OUTPUT_FILE" 2>/dev/null || {
    print_warning "Failed to parse JSON output"
    echo "Raw output:"
    head -20 "$OUTPUT_FILE"
}
echo ""

print_success "Basedpyright run complete"
