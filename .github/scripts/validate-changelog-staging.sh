#!/bin/bash

# Validates that a PR includes a properly formatted changelog staging entry.
#
# Replaces validate-changelog-version-bump.sh — developers no longer bump
# versions manually. Instead they add entries to the staging section of
# CHANGELOG.md with bump indicators (+, ++, +++).

set -e

SCRIPT_NAME=$(basename "$0")
BOUNDARY_MARKER="<!-- CHANGELOG-BOUNDARY -->"

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
${SCRIPT_NAME} - Validate changelog staging entries in PRs

USAGE:
    ${SCRIPT_NAME} [OPTIONS] <package_dir>

DESCRIPTION:
    Validates that:
    1. CHANGELOG.md has been updated (if meaningful code changes exist)
    2. The staging section (above ${BOUNDARY_MARKER}) contains at least one
       bump indicator (+, ++, or +++) with change descriptions
    3. The pyproject.toml version has NOT been manually modified

OPTIONS:
    -h, --help           Show this help message
    -b, --base-ref REF   Base branch for comparison (default: auto-detect)
    --no-fetch           Skip fetching the base branch
    --exclude PATTERNS   Comma-separated exclusion patterns

BUMP INDICATORS:
    +   YYYY-MM-DD   -> patch bump
    ++  YYYY-MM-DD   -> minor bump
    +++ YYYY-MM-DD   -> major bump
EOF
}

# --- argument parsing ---

PACKAGE=""
BASE_REF=""
NO_FETCH=false
EXCLUDE_ARG=""
DEFAULT_EXCLUDES="poetry.lock,uv.lock,CHANGELOG.md,docs/,mkdocs.yaml,.entangled/"

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)     show_help; exit 0 ;;
        --base-ref|-b) BASE_REF="$2"; shift 2 ;;
        --no-fetch)    NO_FETCH=true; shift ;;
        --exclude)     EXCLUDE_ARG="$2"; shift 2 ;;
        -*)            print_error "Unknown option: $1"; exit 2 ;;
        *)
            if [ -z "$PACKAGE" ]; then PACKAGE="$1"; shift
            else print_error "Unexpected argument: $1"; exit 2; fi
            ;;
    esac
done

if [ -z "$PACKAGE" ]; then
    print_error "Package directory is required"
    show_help
    exit 2
fi

if [ ! -d "$PACKAGE" ]; then
    print_error "Package directory '$PACKAGE' does not exist"
    exit 1
fi

# --- determine base ref ---

if [ -z "$BASE_REF" ]; then
    if [ -n "${GITHUB_BASE_REF:-}" ]; then
        BASE_REF="$GITHUB_BASE_REF"
    elif git show-ref --verify --quiet refs/remotes/origin/main; then
        BASE_REF="origin/main"
    elif git show-ref --verify --quiet refs/remotes/origin/master; then
        BASE_REF="origin/master"
    else
        print_error "Could not determine base reference"
        exit 1
    fi
fi

if [[ "$BASE_REF" =~ ^refs/heads/ ]]; then
    BASE_REF="origin/${BASE_REF#refs/heads/}"
elif [[ ! "$BASE_REF" =~ ^origin/ ]]; then
    BASE_REF="origin/$BASE_REF"
fi

print_info "Validating package: $PACKAGE"
print_info "Base reference: $BASE_REF"

# --- fetch base ---

if [ "$NO_FETCH" = false ]; then
    BRANCH_NAME="${BASE_REF#origin/}"
    print_info "Fetching base branch: $BRANCH_NAME"
    git fetch origin "$BRANCH_NAME" 2>/dev/null || true
fi

MERGE_BASE=$(git merge-base HEAD "$BASE_REF" 2>/dev/null) || true
if [ -z "$MERGE_BASE" ]; then
    print_error "Could not find merge base between HEAD and $BASE_REF"
    exit 1
fi

# --- check for meaningful code changes ---

EXCLUDE_CSV="${EXCLUDE_ARG:-$DEFAULT_EXCLUDES}"
IFS=',' read -ra EXCLUDED_PATTERNS <<< "$EXCLUDE_CSV"

EXCLUDE_REGEX_PARTS=()
for pattern in "${EXCLUDED_PATTERNS[@]}"; do
    trimmed="${pattern#"${pattern%%[![:space:]]*}"}"
    trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
    [ -z "$trimmed" ] && continue
    escaped=$(echo "$trimmed" | sed 's/\./\\./g')
    if [[ "$trimmed" == */ ]]; then
        EXCLUDE_REGEX_PARTS+=("(^|/)${escaped}")
    else
        EXCLUDE_REGEX_PARTS+=("(^|/)${escaped}$")
    fi
done

if [ ${#EXCLUDE_REGEX_PARTS[@]} -eq 0 ]; then
    EXCLUDE_REGEX="^$"
else
    EXCLUDE_REGEX=$(IFS='|'; echo "${EXCLUDE_REGEX_PARTS[*]}")
fi

ALL_CHANGES=$(git diff --name-only "$MERGE_BASE"..HEAD -- "$PACKAGE") || {
    print_error "git diff failed"
    exit 1
}
CODE_CHANGES=$(echo "$ALL_CHANGES" | grep -v -E "($EXCLUDE_REGEX)" || true)

if [ -z "$CODE_CHANGES" ]; then
    print_info "No meaningful code changes in $PACKAGE"
    print_success "Skipping validation"
    exit 0
fi

print_info "Detected code changes:"
echo "$CODE_CHANGES" | head -10
echo ""

# --- validate changelog has been updated ---

if ! git diff --name-only "$MERGE_BASE"..HEAD | grep -q "^$PACKAGE/CHANGELOG.md$"; then
    print_error "$PACKAGE/CHANGELOG.md must be updated in this PR"
    echo ""
    echo "Add a changelog entry to the staging section (above the boundary marker):"
    echo ""
    echo "  + $(date +%Y-%m-%d)"
    echo "  - Description of your change"
    echo ""
    echo "Use + for patch, ++ for minor, +++ for major version bumps."
    exit 1
fi
print_success "CHANGELOG.md has been updated"

# --- validate boundary marker exists ---

CHANGELOG="$PACKAGE/CHANGELOG.md"
if ! grep -qF "$BOUNDARY_MARKER" "$CHANGELOG"; then
    print_error "CHANGELOG.md is missing the boundary marker: $BOUNDARY_MARKER"
    echo "The marker must be present to separate staging entries from released versions."
    exit 1
fi
print_success "Boundary marker present"

# --- validate no duplicate boundary markers ---

BOUNDARY_COUNT=$(grep -cF "$BOUNDARY_MARKER" "$CHANGELOG")
if [ "$BOUNDARY_COUNT" -gt 1 ]; then
    print_error "Found $BOUNDARY_COUNT boundary markers in CHANGELOG.md (expected exactly 1)"
    echo "Remove the duplicate <!-- CHANGELOG-BOUNDARY --> markers."
    exit 1
fi
print_success "Single boundary marker"

# --- extract staging section ---

BOUNDARY_LINE=$(grep -nF "$BOUNDARY_MARKER" "$CHANGELOG" | head -1 | cut -d: -f1)
STAGING=$(head -n "$((BOUNDARY_LINE - 1))" "$CHANGELOG")

# --- reject version headers in staging area (old format used by mistake) ---

if echo "$STAGING" | grep -qE '^## \[[0-9]+\.[0-9]+'; then
    print_error "Found a version header (## [X.Y.Z]) in the staging section"
    echo ""
    echo "Version headers are now set automatically by CI."
    echo "Replace the '## [X.Y.Z] - date' line with a bump indicator:"
    echo "  + $(date +%Y-%m-%d)     <- patch bump"
    echo "  ++ $(date +%Y-%m-%d)    <- minor bump"
    echo "  +++ $(date +%Y-%m-%d)   <- major bump"
    exit 1
fi
print_success "No version headers in staging area"

# --- validate staging section has bump indicators with correct format ---

FOUND_BUMP=false
BUMP_NAMES=( "" "patch" "minor" "major" )

while IFS= read -r line; do
    if [[ "$line" =~ ^(\+{1,3})[[:space:]] ]]; then
        pluses="${BASH_REMATCH[1]}"
        level=${#pluses}

        # Validate the date format: +{1,3} YYYY-MM-DD
        if ! [[ "$line" =~ ^(\+{1,3})[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]]*$ ]]; then
            print_error "Malformed bump indicator line: $line"
            echo ""
            echo "Expected format: ${pluses} YYYY-MM-DD"
            echo "Example: ${pluses} $(date +%Y-%m-%d)"
            exit 1
        fi

        FOUND_BUMP=true
        print_info "Found bump indicator: ${BUMP_NAMES[$level]} ($line)"
    fi
done <<< "$STAGING"

if [ "$FOUND_BUMP" = false ]; then
    print_error "No bump indicator found in the changelog staging section"
    echo ""
    echo "Add a line like one of these above the $BOUNDARY_MARKER marker:"
    echo "  + $(date +%Y-%m-%d)     <- patch bump"
    echo "  ++ $(date +%Y-%m-%d)    <- minor bump"
    echo "  +++ $(date +%Y-%m-%d)   <- major bump"
    exit 1
fi
print_success "Valid bump indicator(s) found"

# --- validate change descriptions exist ---

HAS_CHANGES=false
while IFS= read -r line; do
    if [[ "$line" =~ ^-[[:space:]] ]]; then
        HAS_CHANGES=true
        break
    fi
done <<< "$STAGING"

if [ "$HAS_CHANGES" = false ]; then
    print_error "No change descriptions found in the staging section"
    echo "Add at least one line starting with '- ' describing your change."
    exit 1
fi
print_success "Change descriptions present"

# --- reject unrecognized lines in staging (catch formatting mistakes) ---

while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    # Allow: header boilerplate, bump indicators, change descriptions, sub-items, section headings, HTML comments
    [[ "$line" =~ ^#\  ]] && continue
    [[ "$line" =~ ^All\ notable ]] && continue
    [[ "$line" =~ ^The\ format\ is ]] && continue
    [[ "$line" =~ ^and\ this\ project ]] && continue
    [[ "$line" =~ ^(\+{1,3})[[:space:]] ]] && continue
    [[ "$line" =~ ^-[[:space:]] ]] && continue
    [[ "$line" =~ ^[[:space:]]+-[[:space:]] ]] && continue
    [[ "$line" =~ ^[[:space:]] ]] && continue
    [[ "$line" =~ ^### ]] && continue
    [[ "$line" =~ ^\<\!-- ]] && continue
    [[ "$line" =~ --\>$ ]] && continue

    print_error "Unrecognized line in staging section: $line"
    echo ""
    echo "The staging section should only contain:"
    echo "  - Bump indicators: + YYYY-MM-DD / ++ YYYY-MM-DD / +++ YYYY-MM-DD"
    echo "  - Change descriptions: - Your change here"
    echo "  - Sub-section headings: ### Added / ### Fixed / etc."
    exit 1
done <<< "$STAGING"
print_success "Staging section format is clean"

# --- warn if pyproject.toml version was manually changed ---

if git diff --name-only "$MERGE_BASE"..HEAD | grep -q "^$PACKAGE/pyproject.toml$"; then
    BASE_VERSION=$(git show "$MERGE_BASE:$PACKAGE/pyproject.toml" 2>/dev/null | grep -E '^version[[:space:]]*=' | sed -E 's/version[[:space:]]*=[[:space:]]*"([^"]+)"/\1/' || echo "")
    CURRENT_VERSION=$(grep -E '^version[[:space:]]*=' "$PACKAGE/pyproject.toml" | sed -E 's/version[[:space:]]*=[[:space:]]*"([^"]+)"/\1/' || echo "")

    if [ -n "$BASE_VERSION" ] && [ -n "$CURRENT_VERSION" ] && [ "$BASE_VERSION" != "$CURRENT_VERSION" ]; then
        print_warning "pyproject.toml version was manually changed ($BASE_VERSION -> $CURRENT_VERSION)"
        echo "Version bumping is now automated — the CI pipeline will set the version on merge."
        echo "Please revert the version change in pyproject.toml."
        exit 1
    fi
fi
print_success "pyproject.toml version not manually modified"

echo ""
print_success "All validations passed!"
