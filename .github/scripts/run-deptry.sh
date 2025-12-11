#!/usr/bin/env bash
set -e

# Runs deptry and outputs JSON

# Source common library
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME=$(basename "$0")
VERSION="1.0.0"
source "$SCRIPT_DIR/lib/common.sh"

# Help function
show_help() {
    cat << EOF
${SCRIPT_NAME} - Run deptry and output JSON results

USAGE:
    ${SCRIPT_NAME} [OPTIONS] <package_dir> [output_file]
    ${SCRIPT_NAME} -h | --help
    ${SCRIPT_NAME} --version

DESCRIPTION:
    This script runs deptry on a package and outputs the results as JSON.

ARGUMENTS:
    package_dir          Path to package directory (required)
    output_file          Path to output JSON file (default: /tmp/deptry.json)

OPTIONS:
    -h, --help           Show this help message and exit
    -v, --version        Show version information and exit
    -o, --output FILE    Path to output JSON file (default: /tmp/deptry.json)
    -r, --runner CMD     Command executor prefix (e.g., "poetry run" or "uv run", default: "uv run")

EXAMPLES:
    # Basic usage (with uv)
    ${SCRIPT_NAME} unique_mcp

    # With poetry
    ${SCRIPT_NAME} -r "poetry run" unique_toolkit

    # Specify package directory and output file
    ${SCRIPT_NAME} unique_mcp /tmp/my-results.json

EXIT CODES:
    0    Deptry completed (may have errors, check JSON output)
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
OUTPUT_FILE="/tmp/deptry.json"
RUNNER="uv run"

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
while getopts "hvo:r:" opt; do
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
    if [ "$OUTPUT_FILE" = "/tmp/deptry.json" ]; then
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

# Change to package directory
cd "$PACKAGE_DIR" || {
    print_error "Failed to change to package directory: $PACKAGE_DIR"
    exit 1
}

# ============================================================================
# SCRIPT LOGIC
# ============================================================================

print_info "Running deptry"
print_info "Package: $PACKAGE_DIR"
print_info "Output: $OUTPUT_FILE"
echo ""

# Run deptry with JSON output
# deptry may exit with non-zero status if issues are found, but we still want the JSON
print_info "Using runner: $RUNNER"
$RUNNER deptry . --json-output "$OUTPUT_FILE" 2>&1 || {
    print_warning "deptry exited with non-zero status (expected if there are dependency issues)"
}

# Ensure output file exists (deptry may not create it if there are no issues)
if [ ! -f "$OUTPUT_FILE" ]; then
    echo '[]' > "$OUTPUT_FILE"
    print_info "No issues found, created empty JSON array"
fi

# Validate JSON output
if ! jq empty "$OUTPUT_FILE" 2>/dev/null; then
    print_warning "Output is not valid JSON, creating empty array"
    echo '[]' > "$OUTPUT_FILE"
fi

# Show summary
echo ""
print_info "Deptry summary"
ISSUE_COUNT=$(jq 'length' "$OUTPUT_FILE" 2>/dev/null || echo "0")
print_info "Found $ISSUE_COUNT dependency issue(s)"
echo ""

print_success "Deptry run complete"

