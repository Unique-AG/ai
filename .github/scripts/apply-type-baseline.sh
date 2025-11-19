#!/usr/bin/env bash
set -e

# Applies a type checking baseline to the current branch

# Source common library
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME=$(basename "$0")
VERSION="1.0.0"
source "$SCRIPT_DIR/lib/common.sh"

# Help function
show_help() {
    cat << EOF
${SCRIPT_NAME} - Apply type checking baseline to current branch

USAGE:
    ${SCRIPT_NAME} [OPTIONS] <package_dir>
    ${SCRIPT_NAME} -h | --help
    ${SCRIPT_NAME} --version

DESCRIPTION:
    This script applies a type checking baseline from a comparison branch
    to the current branch. The baseline is used to ignore existing type
    errors and only report new errors introduced by your changes.

ARGUMENTS:
    package_dir          Path to package directory (required)

OPTIONS:
    -h, --help           Show this help message and exit
    -v, --version        Show version information and exit
    -b, --baseline FILE  Path to baseline JSON file (default: /tmp/baseline.json)
    -c, --compare REF    Comparison branch/ref (default: main)

EXAMPLES:
    # Basic usage
    ${SCRIPT_NAME} unique_toolkit

    # Specify baseline file and comparison branch
    ${SCRIPT_NAME} unique_toolkit --baseline /tmp/baseline.json --compare origin/main

    # All options
    ${SCRIPT_NAME} unique_sdk --baseline /tmp/baseline.json --compare main

EXIT CODES:
    0    Baseline applied successfully
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
BASELINE_FILE="/tmp/baseline.json"
COMPARE_BRANCH="main"

# Parse long options first
while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            show_help
            exit 0
            ;;
        --version)
            show_version
            exit 0
            ;;
        --baseline)
            BASELINE_FILE="$2"
            shift 2
            ;;
        --compare)
            COMPARE_BRANCH="$2"
            shift 2
            ;;
        --)
            shift
            break
            ;;
        --*)
            print_error "Unknown long option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
        -*)
            # Short options will be handled by getopts
            break
            ;;
        *)
            # Positional arguments will be handled after getopts
            break
            ;;
    esac
done

# Parse short options using getopts
while getopts "hvb:c:" opt; do
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
            BASELINE_FILE="$OPTARG"
            ;;
        c)
            COMPARE_BRANCH="$OPTARG"
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

print_info "Applying baseline to current branch"
print_info "Package: $PACKAGE_DIR"
print_info "Baseline file: $BASELINE_FILE"
print_info "Comparison branch: $COMPARE_BRANCH"
echo ""

# Ensure directory exists
mkdir -p .basedpyright

# Copy baseline from temp location
if [ -s "$BASELINE_FILE" ]; then
    cp "$BASELINE_FILE" .basedpyright/baseline.json
    print_success "Using baseline from $COMPARE_BRANCH"
    echo "  Baseline size: $(wc -c < .basedpyright/baseline.json) bytes"
else
    print_success "No baseline to apply ($COMPARE_BRANCH has no errors)"
    rm -f .basedpyright/baseline.json
fi

print_success "Baseline applied"
