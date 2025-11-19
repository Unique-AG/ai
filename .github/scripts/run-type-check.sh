#!/usr/bin/env bash
set -e

# Local convenience script for type checking with baseline comparison
# For CI usage, see the GitHub Actions workflow which calls the modular scripts directly

# Source common library
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME=$(basename "$0")
VERSION="1.0.0"
source "$SCRIPT_DIR/lib/common.sh"

# Help function
show_help() {
    cat << EOF
${SCRIPT_NAME} - Type checking with baseline comparison

USAGE:
    ${SCRIPT_NAME} [OPTIONS] <package_dir> [branch]
    ${SCRIPT_NAME} -h | --help
    ${SCRIPT_NAME} --version

DESCRIPTION:
    This is a convenience script that runs the complete type checking workflow:
    1. Creates a baseline from a comparison branch
    2. Applies the baseline to the current branch
    3. Runs basedpyright on the current branch
    4. Reports any new type errors

    For CI usage, see the GitHub Actions workflow which calls the modular
    scripts directly.

ARGUMENTS:
    package_dir          Path to package directory (required)
    branch               Branch/ref to compare against (default: main)

OPTIONS:
    -h, --help           Show this help message and exit
    -v, --version        Show version information and exit
    -b, --branch REF     Branch/ref to compare against (default: main)
    --skip-install       Skip installing dependencies (assume already installed)

EXAMPLES:
    # Basic usage
    ${SCRIPT_NAME} unique_toolkit

    # Specify package directory and branch
    ${SCRIPT_NAME} unique_sdk origin/main

    # Using branch option
    ${SCRIPT_NAME} unique_toolkit --branch origin/main

EXIT CODES:
    0    Type check passed (no new errors)
    1    Type check failed (new errors found) or error occurred

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
COMPARE_BRANCH="main"
SKIP_INSTALL=false

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
        --branch)
            COMPARE_BRANCH="$2"
            shift 2
            ;;
        --skip-install)
            SKIP_INSTALL=true
            shift
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
while getopts "hvb:" opt; do
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

if [ $# -gt 0 ]; then
    if [ "$COMPARE_BRANCH" = "main" ]; then
        COMPARE_BRANCH="$1"
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
    print_error "Package directory does not exist: $PACKAGE_DIR"
    echo ""
    show_help
    exit 1
fi

# Check if poetry is available
if ! command -v poetry &> /dev/null; then
    print_error "poetry not found. Please install poetry first."
    exit 1
fi

# ============================================================================
# SCRIPT LOGIC
# ============================================================================

print_info "Type Checking"
print_info "Package: $PACKAGE_DIR"
print_info "Comparing against branch: $COMPARE_BRANCH"
echo ""

# Ensure dependencies are installed
if [ "$SKIP_INSTALL" = false ]; then
    print_info "Checking dependencies"
    cd "$PACKAGE_DIR"
    poetry install --quiet
    echo ""
fi

# Step 1: Create baseline from comparison branch
print_info "Step 1: Creating baseline from $COMPARE_BRANCH"
bash "$SCRIPT_DIR/create-type-baseline.sh" "$PACKAGE_DIR" "$COMPARE_BRANCH"
echo ""

# Step 2: Apply baseline to current branch
print_info "Step 2: Applying baseline to current branch"
bash "$SCRIPT_DIR/apply-type-baseline.sh" --baseline /tmp/baseline.json --compare "$COMPARE_BRANCH" "$PACKAGE_DIR"
echo ""

# Step 3: Run basedpyright on current branch
print_info "Step 3: Running basedpyright on current branch"
bash "$SCRIPT_DIR/run-basedpyright.sh" "$PACKAGE_DIR" /tmp/basedpyright.json
echo ""

