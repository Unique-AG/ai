#!/bin/bash

# Script to check test coverage on new/changed code
# Can be used both in CI workflows and locally (e.g., with pre-commit)
#
# Usage:
#   CI: check-coverage.sh <package_name> <base_ref> <min_coverage>
#   Local: check-coverage.sh <package_name> [base_ref] [min_coverage]
#
# Examples:
#   CI: check-coverage.sh unique_toolkit main 60
#   Local: check-coverage.sh unique_toolkit
#   Local: check-coverage.sh unique_toolkit origin/main 60

set -e  # Exit on any error

# Script metadata
SCRIPT_NAME=$(basename "$0")
VERSION="1.0.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_error() {
    echo -e "${RED}❌${NC} $1" >&2
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ️${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

# Help function
show_help() {
    cat << EOF
${SCRIPT_NAME} - Check test coverage on new/changed code

USAGE:
    ${SCRIPT_NAME} [OPTIONS] <package_name>
    ${SCRIPT_NAME} -h | --help
    ${SCRIPT_NAME} --version

DESCRIPTION:
    This script checks test coverage on newly added or modified code by:
    1. Running tests with coverage collection
    2. Comparing coverage against a base branch
    3. Ensuring new/changed code meets minimum coverage threshold

ARGUMENTS:
    package_name          Name of the package directory (e.g., unique_toolkit)

OPTIONS:
    -h, --help           Show this help message and exit
    -v, --version        Show version information and exit
    -b, --base-ref REF   Base branch/ref for comparison
                         (default: auto-detect from GITHUB_BASE_REF or origin/main/master)
    -m, --min-coverage N Minimum coverage percentage (default: 60)
    --skip-tests         Skip running tests (assume coverage.xml already exists)
    --no-install-deps    Skip installing diff-cover (assume already installed)

EXAMPLES:
    # CI usage (GitHub Actions)
    ${SCRIPT_NAME} unique_toolkit --base-ref main --min-coverage 60

    # Local usage with auto-detection
    ${SCRIPT_NAME} unique_toolkit

    # Local usage with specific base branch and threshold
    ${SCRIPT_NAME} unique_toolkit --base-ref origin/develop --min-coverage 70

EXIT CODES:
    0    Coverage check passed
    1    Coverage check failed or error occurred
    2    Invalid arguments

AUTHOR:
    Unique AI Toolkit

VERSION:
    ${VERSION}
EOF
}

# Show version
show_version() {
    echo "${SCRIPT_NAME} version ${VERSION}"
}

# Initialize variables
PACKAGE=""
BASE_REF=""
MIN_COVERAGE=60
SKIP_TESTS=false
NO_INSTALL_DEPS=false

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
        --base-ref)
            BASE_REF="$2"
            shift 2
            continue
            ;;
        --min-coverage)
            MIN_COVERAGE="$2"
            shift 2
            continue
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            continue
            ;;
        --no-install-deps)
            NO_INSTALL_DEPS=true
            shift
            continue
            ;;
        --)
            shift
            break
            ;;
        --*)
            print_error "Unknown long option: $1"
            echo "Use --help for usage information."
            exit 2
            ;;
        -*)
            break
            ;;
        *)
            if [ -z "$PACKAGE" ]; then
                PACKAGE="$1"
                shift
            else
                break
            fi
            ;;
    esac
done

# Parse short options using getopts
while getopts "hvb:m:" opt; do
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
            BASE_REF="$OPTARG"
            ;;
        m)
            MIN_COVERAGE="$OPTARG"
            ;;
        \?)
            print_error "Invalid option: -$OPTARG"
            echo "Use -h or --help for usage information."
            exit 2
            ;;
        :)
            print_error "Option -$OPTARG requires an argument."
            echo "Use -h or --help for usage information."
            exit 2
            ;;
    esac
done

# Shift past the options parsed by getopts
shift $((OPTIND-1))

# Handle remaining positional arguments (package name if not already set)
if [ -z "$PACKAGE" ] && [ $# -gt 0 ]; then
    PACKAGE="$1"
    shift
fi

# Handle second positional argument as base-ref (backward compatibility)
if [ -z "$BASE_REF" ] && [ $# -gt 0 ]; then
    BASE_REF="$1"
    shift
fi

# Handle third positional argument as min-coverage (backward compatibility)
if [ $# -gt 0 ] && [[ "$1" =~ ^[0-9]+$ ]]; then
    MIN_COVERAGE="$1"
    shift
fi

# Check for extra arguments
if [ $# -gt 0 ]; then
    print_error "Unexpected argument: $1"
    echo "Use --help for usage information."
    exit 2
fi

# Validate required arguments
if [ -z "$PACKAGE" ]; then
    print_error "Package name is required"
    echo ""
    show_help
    exit 2
fi

# Validate package directory exists
if [ ! -d "$PACKAGE" ]; then
    print_error "Package directory '$PACKAGE' does not exist"
    exit 1
fi

# Validate min_coverage is a number
if ! [[ "$MIN_COVERAGE" =~ ^[0-9]+$ ]] || [ "$MIN_COVERAGE" -lt 0 ] || [ "$MIN_COVERAGE" -gt 100 ]; then
    print_error "Minimum coverage must be a number between 0 and 100"
    exit 2
fi

# Determine base reference if not provided
if [ -z "$BASE_REF" ]; then
    # Check if we're in CI (GitHub Actions)
    if [ -n "$GITHUB_BASE_REF" ]; then
        BASE_REF="$GITHUB_BASE_REF"
        print_info "Using CI base reference: $BASE_REF"
    else
        # Try to detect main or master branch
        if git show-ref --verify --quiet refs/remotes/origin/main; then
            BASE_REF="origin/main"
        elif git show-ref --verify --quiet refs/remotes/origin/master; then
            BASE_REF="origin/master"
        else
            print_error "Could not determine base reference automatically."
            echo "Please specify it with -b/--base-ref option."
            exit 1
        fi
        print_info "Auto-detected base reference: $BASE_REF"
    fi
fi

# Ensure base_ref has origin/ prefix if it's a branch name (and not already a full ref)
if [[ ! "$BASE_REF" =~ ^origin/ ]] && [[ ! "$BASE_REF" =~ ^refs/ ]]; then
    BASE_REF="origin/$BASE_REF"
fi

print_info "Checking coverage for package: $PACKAGE"
print_info "Base reference: $BASE_REF"
print_info "Minimum coverage: ${MIN_COVERAGE}%"

# Store repo root
REPO_ROOT=$(pwd)

# Validate package directory exists
if [ ! -d "$PACKAGE" ]; then
    print_error "Package directory '$PACKAGE' does not exist"
    exit 1
fi

# Change to package directory for poetry operations
cd "$PACKAGE" || {
    print_error "Failed to change to package directory: $PACKAGE"
    exit 1
}

# Install diff-cover if needed
if [ "$NO_INSTALL_DEPS" = false ]; then
    if ! poetry run diff-cover --version >/dev/null 2>&1; then
        print_info "Installing diff-cover..."
        poetry run pip install diff-cover >/dev/null 2>&1 || {
            print_error "Failed to install diff-cover"
            exit 1
        }
    fi
fi

# Fetch base branch if needed (for local usage)
if [ -z "$GITHUB_BASE_REF" ]; then
    BRANCH_NAME=$(echo "$BASE_REF" | sed 's|^origin/||')
    cd "$REPO_ROOT" || exit 1
    if ! git show-ref --verify --quiet "refs/heads/$BRANCH_NAME" && ! git show-ref --verify --quiet "$BASE_REF"; then
        print_info "Fetching base branch: $BRANCH_NAME"
        git fetch origin "$BRANCH_NAME" 2>/dev/null || {
            print_warning "Could not fetch base branch, continuing anyway..."
        }
    fi
    cd "$PACKAGE" || exit 1
fi

# Run tests with coverage if not skipped
if [ "$SKIP_TESTS" = false ]; then
    print_info "Running tests with coverage..."
    poetry run pytest \
        --cov=unique_toolkit \
        --cov-report=xml \
        --cov-report=term \
        tests/ || {
        print_warning "Some tests failed, but continuing with coverage check..."
    }
fi

# Check if coverage.xml exists
if [ ! -f "coverage.xml" ]; then
    print_error "coverage.xml not found. Run tests with coverage first."
    exit 1
fi

# Get changed Python files in the PR (excluding tests and docs)
cd "$REPO_ROOT" || exit 1
CHANGED_FILES=$(git diff --name-only "$BASE_REF" 2>/dev/null | \
    grep '\.py$' | \
    grep "^${PACKAGE}/" | \
    grep -v '/tests/' | \
    grep -v '/test_' | \
    grep -v '/docs/' || true)

if [ -z "$CHANGED_FILES" ]; then
    print_info "No source Python files changed (excluding tests and docs)"
    exit 0
fi

print_info "Changed source Python files:"
echo "$CHANGED_FILES" | sed 's/^/  /'
echo ""

# Run diff-cover to check coverage on changed files
# Must be run from repo root for git diff to work correctly
print_info "Checking coverage on changed files..."
set +e  # Don't exit on error immediately

# Run diff-cover from package directory (it handles git operations correctly)
cd "$PACKAGE" || exit 1
poetry run diff-cover \
    coverage.xml \
    --compare-branch="$BASE_REF" \
    --fail-under="$MIN_COVERAGE" \
    --diff-range-notation=... \
    --markdown-report=coverage_report.md 2>&1
EXIT_CODE=$?
cd "$REPO_ROOT" || exit 1

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    print_error "Coverage on new/changed code is below ${MIN_COVERAGE}%"
    echo "Please add tests to improve coverage."
    if [ -f coverage_report.md ]; then
        echo ""
        echo "Coverage report:"
        cat coverage_report.md
    fi
    exit 1
fi

echo ""
print_success "Coverage check passed! New/changed code has at least ${MIN_COVERAGE}% coverage."

