#!/bin/bash

# Script to validate that CHANGELOG.md and version in pyproject.toml are updated
# Can be used both in CI workflows and locally

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
${SCRIPT_NAME} - Validate CHANGELOG.md and version bump in pyproject.toml

USAGE:
    ${SCRIPT_NAME} [OPTIONS] <package_name>
    ${SCRIPT_NAME} -h | --help
    ${SCRIPT_NAME} --version

DESCRIPTION:
    This script validates that:
    1. CHANGELOG.md has been updated in the current changes
    2. pyproject.toml has been modified
    3. The version number in pyproject.toml has been incremented

    The script compares the current branch against a base branch (default: main/master)
    to ensure both files are modified and the version is bumped.

ARGUMENTS:
    package_name          Name of the package directory (e.g., unique_toolkit)

OPTIONS:
    -h, --help           Show this help message and exit
    -v, --version        Show version information and exit
    -b, --base-ref REF   Base branch/ref for comparison
                         (default: auto-detect from GITHUB_BASE_REF or origin/main/master)
    --no-fetch           Skip fetching the base branch (useful if already fetched)
    --exclude PATTERNS   Comma-separated list of patterns to exclude from "meaningful changes"
                         (e.g., "poetry.lock,uv.lock,docs/,CHANGELOG.md")

EXAMPLES:
    # CI usage (GitHub Actions)
    ${SCRIPT_NAME} unique_toolkit --base-ref main

    # Local usage with auto-detection
    ${SCRIPT_NAME} unique_toolkit

    # Local usage with specific base branch
    ${SCRIPT_NAME} unique_toolkit --base-ref origin/develop

    # Skip fetch (if branch already fetched)
    ${SCRIPT_NAME} unique_toolkit --base-ref main --no-fetch

    # With custom exclusions
    ${SCRIPT_NAME} unique_toolkit main --exclude "poetry.lock,uv.lock,docs/"

EXIT CODES:
    0    Validation passed
    1    Validation failed or error occurred
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
NO_FETCH=false
EXCLUDE_ARG=""

# Default exclusion patterns (used if --exclude not provided)
DEFAULT_EXCLUDES="poetry.lock,uv.lock,CHANGELOG.md,docs/,mkdocs.yaml,.entangled/"

# Parse long options first (--help, --version, --base-ref, --no-fetch)
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
        --no-fetch)
            NO_FETCH=true
            shift
            continue
            ;;
        --exclude)
            EXCLUDE_ARG="$2"
            shift 2
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
            # Short options will be handled by getopts
            break
            ;;
        *)
            # First non-option argument is the package name
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
            BASE_REF="$OPTARG"
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

# Handle remaining positional arguments
# Maintain backward compatibility: script.sh <package> [base_ref]
if [ -z "$PACKAGE" ] && [ $# -gt 0 ]; then
    PACKAGE="$1"
    shift
fi

# Handle second positional argument as base-ref (backward compatibility)
if [ -z "$BASE_REF" ] && [ $# -gt 0 ]; then
    BASE_REF="$1"
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

# Normalize base_ref to origin/<branch> format
# Handle refs/heads/main -> origin/main, main -> origin/main
if [[ "$BASE_REF" =~ ^refs/heads/ ]]; then
    # Convert refs/heads/main to origin/main
    BASE_REF="origin/${BASE_REF#refs/heads/}"
elif [[ ! "$BASE_REF" =~ ^origin/ ]]; then
    BASE_REF="origin/$BASE_REF"
fi

print_info "Validating package: $PACKAGE"
print_info "Base reference: $BASE_REF"

# Fetch the base reference (needed for merge-base)
if [ "$NO_FETCH" = false ]; then
    # Extract branch name (remove origin/ prefix)
    BRANCH_NAME="${BASE_REF#origin/}"
    print_info "Fetching base branch: $BRANCH_NAME"
    if ! git fetch origin "$BRANCH_NAME" 2>/dev/null; then
        # If fetch fails, try without suppressing output to see the error
        if ! git fetch origin "$BRANCH_NAME"; then
            print_error "Failed to fetch base reference: $BRANCH_NAME"
            print_error "Make sure the branch exists: git fetch origin $BRANCH_NAME"
            exit 1
        fi
    fi
else
    print_info "Skipping fetch (--no-fetch specified)"
fi

# Get the merge base
MERGE_BASE=$(git merge-base HEAD "$BASE_REF" 2>/dev/null) || true

# Check if merge-base succeeded (subshell exit doesn't stop main script)
if [ -z "$MERGE_BASE" ]; then
    print_error "Could not find merge base between HEAD and $BASE_REF"
    print_error "Make sure you have fetched the base branch: git fetch origin <branch>"
    exit 1
fi

print_info "Merge base: $MERGE_BASE"

# Use provided exclusions or defaults
if [ -n "$EXCLUDE_ARG" ]; then
    EXCLUDE_CSV="$EXCLUDE_ARG"
    print_info "Using provided exclusions: $EXCLUDE_CSV"
else
    EXCLUDE_CSV="$DEFAULT_EXCLUDES"
    print_info "Using default exclusions: $EXCLUDE_CSV"
fi

# Convert comma-separated to array and build grep pattern
IFS=',' read -ra EXCLUDED_PATTERNS <<< "$EXCLUDE_CSV"
# Escape regex metacharacters (dots) and join with | for extended regex
EXCLUDE_REGEX=$(printf '%s|' "${EXCLUDED_PATTERNS[@]}" | sed 's/\./\\./g; s/|$//')

# First check if there are any meaningful code changes in this package
# Separate git diff from grep to properly detect git failures
ALL_CHANGES=$(git diff --name-only "$MERGE_BASE"..HEAD -- "$PACKAGE") || {
    print_error "git diff failed - merge base '$MERGE_BASE' may be invalid"
    exit 1
}
# Filter out excluded patterns (grep returns 1 if no matches, which is fine)
CODE_CHANGES=$(echo "$ALL_CHANGES" | grep -v -E "($EXCLUDE_REGEX)" || true)

if [ -z "$CODE_CHANGES" ]; then
    print_info "No code changes detected in $PACKAGE (only lock files, docs, or no changes)"
    print_success "Skipping validation - no changelog/version bump required"
    exit 0
fi

print_info "Detected code changes in $PACKAGE:"
echo "$CODE_CHANGES" | head -10
echo ""

# Check CHANGELOG.md is updated
CHANGELOG_FILE="$PACKAGE/CHANGELOG.md"
if ! git diff --name-only "$MERGE_BASE"..HEAD | grep -q "^$PACKAGE/CHANGELOG.md$"; then
    print_error "$PACKAGE/CHANGELOG.md must be updated in this PR"
    echo "Please add an entry to the changelog describing your changes."
    exit 1
else
    print_success "$PACKAGE/CHANGELOG.md has been updated"
fi

# Verify CHANGELOG.md wasn't deleted (diff includes deletions)
if [ ! -f "$CHANGELOG_FILE" ]; then
    print_error "$CHANGELOG_FILE was deleted - changelog must exist and be updated, not removed"
    exit 1
fi

# Check for duplicate version entries in changelog
if [ -f "$CHANGELOG_FILE" ]; then
    # Extract all version headers (## [X.Y.Z])
    VERSIONS=$(grep -oE '## \[[0-9]+\.[0-9]+\.[0-9]+[^]]*\]' "$CHANGELOG_FILE" | sed 's/## \[//; s/\]//' | sort)
    UNIQUE_VERSIONS=$(echo "$VERSIONS" | uniq)
    
    if [ "$VERSIONS" != "$UNIQUE_VERSIONS" ]; then
        print_error "Duplicate version entries found in $CHANGELOG_FILE"
        echo "The following versions appear more than once:"
        echo "$VERSIONS" | uniq -d
        exit 1
    else
        print_success "No duplicate version entries in changelog"
    fi
fi

# Check pyproject.toml exists and has been modified
if ! git diff --name-only "$MERGE_BASE"..HEAD | grep -q "^$PACKAGE/pyproject.toml$"; then
    print_error "$PACKAGE/pyproject.toml must be updated in this PR"
    echo "Please update the version in pyproject.toml to reflect your changes."
    exit 1
fi

# Extract and compare versions
# Note: Using [[:space:]] instead of \s for BSD/macOS sed compatibility
BASE_VERSION=$(git show "$MERGE_BASE:$PACKAGE/pyproject.toml" 2>/dev/null | grep -E '^version[[:space:]]*=' | sed -E 's/version[[:space:]]*=[[:space:]]*"([^"]+)"/\1/' || echo "")
CURRENT_VERSION=$(grep -E '^version[[:space:]]*=' "$PACKAGE/pyproject.toml" | sed -E 's/version[[:space:]]*=[[:space:]]*"([^"]+)"/\1/' || echo "")

if [ -z "$BASE_VERSION" ]; then
    print_error "Could not extract version from base branch's pyproject.toml"
    exit 1
fi

if [ -z "$CURRENT_VERSION" ]; then
    print_error "Could not extract version from current pyproject.toml"
    exit 1
fi

echo ""
echo "Base branch version:    $BASE_VERSION"
echo "Current branch version: $CURRENT_VERSION"
echo ""

if [ "$BASE_VERSION" = "$CURRENT_VERSION" ]; then
    print_error "Version in $PACKAGE/pyproject.toml has not been updated"
    echo "Please bump the version number to reflect your changes."
    echo "Current version: $CURRENT_VERSION"
    exit 1
else
    print_success "Version has been updated from $BASE_VERSION to $CURRENT_VERSION"
fi

# Check that changelog has an entry for the current version
if [ -f "$CHANGELOG_FILE" ]; then
    # Use grep -F for literal string matching (versions may contain + or other regex chars)
    if ! grep -qF "## [$CURRENT_VERSION]" "$CHANGELOG_FILE"; then
        print_error "Changelog does not contain an entry for version $CURRENT_VERSION"
        echo "Please add a '## [$CURRENT_VERSION]' section to the changelog."
        exit 1
    else
        print_success "Changelog contains entry for version $CURRENT_VERSION"
    fi
fi

print_success "All validations passed!"
