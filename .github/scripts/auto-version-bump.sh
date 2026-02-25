#!/bin/bash

# Automated version bumping script for the AI monorepo.
#
# Reads the changelog staging area (above the BOUNDARY marker), determines the
# required semver bump, increments the version in pyproject.toml, and rewrites
# the changelog with proper version headers.
#
# Supports both Poetry ([tool.poetry] version) and uv ([project] version) layouts.

set -euo pipefail

SCRIPT_NAME=$(basename "$0")
BOUNDARY_MARKER="<!-- ADD CHANGELOG ENTRY ABOVE THIS BOUNDARY -->"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_error()   { echo -e "${RED}ERROR:${NC} $1" >&2; }
print_success() { echo -e "${GREEN}OK:${NC} $1"; }
print_info()    { echo -e "${BLUE}INFO:${NC} $1"; }
print_warning() { echo -e "${YELLOW}WARN:${NC} $1"; }

show_help() {
    cat << EOF
${SCRIPT_NAME} - Automated version bumping from changelog staging area

USAGE:
    ${SCRIPT_NAME} <package_dir> [--dry-run]

DESCRIPTION:
    Reads the CHANGELOG.md staging area (entries above the ${BOUNDARY_MARKER}
    marker), determines the highest semver bump level, increments the version
    in pyproject.toml, and rewrites CHANGELOG.md with a proper version header.

    Bump indicators in changelog entries:
        +   date   -> patch bump  (1.2.3 -> 1.2.4)
        ++  date   -> minor bump  (1.2.3 -> 1.3.0)
        +++ date   -> major bump  (1.2.3 -> 2.0.0)

OPTIONS:
    --dry-run    Show what would happen without modifying files
    -h, --help   Show this help message

EXAMPLES:
    ${SCRIPT_NAME} unique_toolkit
    ${SCRIPT_NAME} unique_toolkit --dry-run
EOF
}

# --- argument parsing ---

DRY_RUN=false
PACKAGE_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)  show_help; exit 0 ;;
        --dry-run)  DRY_RUN=true; shift ;;
        -*)         print_error "Unknown option: $1"; exit 2 ;;
        *)
            if [ -z "$PACKAGE_DIR" ]; then
                PACKAGE_DIR="$1"; shift
            else
                print_error "Unexpected argument: $1"; exit 2
            fi
            ;;
    esac
done

if [ -z "$PACKAGE_DIR" ]; then
    print_error "Package directory is required"
    show_help
    exit 2
fi

CHANGELOG="$PACKAGE_DIR/CHANGELOG.md"
PYPROJECT="$PACKAGE_DIR/pyproject.toml"

if [ ! -f "$CHANGELOG" ]; then
    print_error "Changelog not found: $CHANGELOG"
    exit 1
fi
if [ ! -f "$PYPROJECT" ]; then
    print_error "pyproject.toml not found: $PYPROJECT"
    exit 1
fi

# --- read current version from pyproject.toml ---

extract_version() {
    local file="$1"
    grep -E '^version[[:space:]]*=' "$file" | head -1 | sed -E 's/^version[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/'
}

CURRENT_VERSION=$(extract_version "$PYPROJECT")
if [ -z "$CURRENT_VERSION" ]; then
    print_error "Could not extract version from $PYPROJECT"
    exit 1
fi
print_info "Current version: $CURRENT_VERSION"

# --- split changelog at boundary ---

if ! grep -qF "$BOUNDARY_MARKER" "$CHANGELOG"; then
    print_error "No boundary marker found in $CHANGELOG"
    echo "Expected marker: $BOUNDARY_MARKER"
    echo "Run migrate-changelogs.sh or add the marker manually."
    exit 1
fi

BOUNDARY_COUNT=$(grep -cF "$BOUNDARY_MARKER" "$CHANGELOG")
if [ "$BOUNDARY_COUNT" -gt 1 ]; then
    print_error "Found $BOUNDARY_COUNT boundary markers in $CHANGELOG (expected exactly 1)"
    exit 1
fi

BOUNDARY_LINE=$(grep -nF "$BOUNDARY_MARKER" "$CHANGELOG" | head -1 | cut -d: -f1)
STAGING=$(head -n "$((BOUNDARY_LINE - 1))" "$CHANGELOG")
REST=$(tail -n +"$((BOUNDARY_LINE))" "$CHANGELOG")

# --- detect bump indicators in staging area ---

BUMP_LEVEL=0  # 0=none, 1=patch, 2=minor, 3=major

while IFS= read -r line; do
    if [[ "$line" =~ ^(\+{1,3})[[:space:]] ]]; then
        pluses="${BASH_REMATCH[1]}"
        level=${#pluses}
        if (( level > BUMP_LEVEL )); then
            BUMP_LEVEL=$level
        fi
    fi
done <<< "$STAGING"

if (( BUMP_LEVEL == 0 )); then
    print_info "No bump indicators found in staging area — nothing to do"
    exit 0
fi

BUMP_NAMES=( "" "patch" "minor" "major" )
print_info "Detected bump level: ${BUMP_NAMES[$BUMP_LEVEL]}"

# --- compute new version ---

IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

case $BUMP_LEVEL in
    1) PATCH=$((PATCH + 1)) ;;
    2) MINOR=$((MINOR + 1)); PATCH=0 ;;
    3) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"
print_info "New version: $NEW_VERSION"

# --- build new changelog entry ---
# Collect all bullet lines from the staging area, strip bump-indicator lines,
# and produce a single version section.

TODAY=$(date +%Y-%m-%d)
ENTRY_LINES=()

IN_HTML_COMMENT=false
while IFS= read -r line; do
    # skip blank lines and bump-indicator lines
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^(\+{1,3})[[:space:]] ]] && continue
    # skip the header boilerplate
    [[ "$line" =~ ^#\  ]] && continue
    [[ "$line" =~ ^All\ notable ]] && continue
    [[ "$line" =~ ^The\ format\ is ]] && continue
    [[ "$line" =~ ^and\ this\ project ]] && continue
    # skip HTML comments (instruction block and other comments)
    if [[ "$line" =~ ^\<\!-- ]]; then
        if [[ "$line" =~ --\>$ ]]; then
            continue
        fi
        IN_HTML_COMMENT=true
        continue
    fi
    if [[ "$IN_HTML_COMMENT" == true ]]; then
        if [[ "$line" =~ --\>$ ]]; then
            IN_HTML_COMMENT=false
        fi
        continue
    fi
    ENTRY_LINES+=("$line")
done <<< "$STAGING"

if [ ${#ENTRY_LINES[@]} -eq 0 ]; then
    print_warning "Staging area has bump indicators but no change descriptions"
    exit 1
fi

HEADER="# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)."

NEW_SECTION="## [${NEW_VERSION}] - ${TODAY}"
for line in "${ENTRY_LINES[@]}"; do
    NEW_SECTION="${NEW_SECTION}
${line}"
done

# --- assemble final changelog ---

NEW_CHANGELOG="${HEADER}

${BOUNDARY_MARKER}

${NEW_SECTION}

${REST#*"${BOUNDARY_MARKER}"}"

# Trim any triple+ blank lines down to double
NEW_CHANGELOG=$(echo "$NEW_CHANGELOG" | awk '
    /^$/ { blank++; if (blank <= 2) print; next }
    { blank=0; print }
')

if [ "$DRY_RUN" = true ]; then
    echo ""
    print_info "=== DRY RUN — no files modified ==="
    echo ""
    echo "pyproject.toml version: $CURRENT_VERSION -> $NEW_VERSION"
    echo ""
    echo "--- New changelog (first 30 lines) ---"
    echo "$NEW_CHANGELOG" | head -30
    exit 0
fi

# --- write files ---

echo "$NEW_CHANGELOG" > "$CHANGELOG"
print_success "Updated $CHANGELOG"

# Update version in pyproject.toml (handle both Poetry and uv layouts)
if grep -qE '^\[tool\.poetry\]' "$PYPROJECT"; then
    sed -i.bak -E "s/^(version[[:space:]]*=[[:space:]]*\").*(\")/\1${NEW_VERSION}\2/" "$PYPROJECT"
    rm -f "$PYPROJECT.bak"
elif grep -qE '^\[project\]' "$PYPROJECT"; then
    sed -i.bak -E "s/^(version[[:space:]]*=[[:space:]]*\").*(\")/\1${NEW_VERSION}\2/" "$PYPROJECT"
    rm -f "$PYPROJECT.bak"
else
    print_error "Unrecognized pyproject.toml layout in $PYPROJECT"
    exit 1
fi
print_success "Updated $PYPROJECT version to $NEW_VERSION"

echo ""
print_success "Version bump complete: $CURRENT_VERSION -> $NEW_VERSION (${BUMP_NAMES[$BUMP_LEVEL]})"

# Write to GITHUB_OUTPUT if running in CI (allows the workflow to collect results)
if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "new_version=$NEW_VERSION" >> "$GITHUB_OUTPUT"
    echo "old_version=$CURRENT_VERSION" >> "$GITHUB_OUTPUT"
    echo "bump_type=${BUMP_NAMES[$BUMP_LEVEL]}" >> "$GITHUB_OUTPUT"
fi
