#!/usr/bin/env bash
set -e

# Parses basedpyright JSON output and reports errors
# Usage: report-type-errors.sh <package_dir> <json_file> [--reviewdog <path>] [--base-ref <ref>]

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PACKAGE_DIR="$1"
JSON_FILE="$2"
REVIEWDOG_PATH=""
USE_REVIEWDOG=false
BASE_REF=""

# Parse arguments
shift 2
while [[ $# -gt 0 ]]; do
    case $1 in
        --reviewdog)
            REVIEWDOG_PATH="$2"
            USE_REVIEWDOG=true
            shift 2
            ;;
        --base-ref)
            BASE_REF="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [ -z "$PACKAGE_DIR" ] || [ -z "$JSON_FILE" ]; then
    echo "Usage: report-type-errors.sh <package_dir> <json_file> [--reviewdog <path>] [--base-ref <ref>]"
    exit 1
fi

cd "$PACKAGE_DIR" || {
    echo -e "${RED}Error: Failed to change to package directory: $PACKAGE_DIR${NC}"
    exit 1
}

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
    echo -e "${RED}ERROR: Failed to parse basedpyright JSON output${NC}"
    exit 1
}

# Count errors
ERROR_COUNT=$(wc -l < "$ERRORS_FILE" | tr -d ' ')

if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ No new type errors found! Baseline successfully filtered out existing errors.${NC}"
    echo ""
    echo -e "${GREEN}Success! Your changes don't introduce new type errors.${NC}"
    exit 0
fi

# There are errors - handle based on mode
if [ "$USE_REVIEWDOG" = true ] && [ -n "$REVIEWDOG_PATH" ]; then
    # CI mode with reviewdog - post comments to PR
    echo -e "${YELLOW}Found $ERROR_COUNT new type error(s) - posting to PR${NC}"
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
            -diff="git diff origin/${BASE_REF:-main}" \
            -tee || true
    
    echo ""
    echo -e "${YELLOW}=== Reviewdog completed ==="
    echo -e "${RED}Type check failed with $ERROR_COUNT new error(s)${NC}"
    exit 1  # Fail the workflow to enforce fixing errors
else
    # Local mode or no reviewdog - just display errors
    echo -e "${YELLOW}=== Type errors found ===${NC}"
    echo -e "${RED}Found $ERROR_COUNT new type error(s):${NC}"
    echo ""
    cat "$ERRORS_FILE"
    echo ""
    echo -e "${RED}Please fix these type errors before committing.${NC}"
    exit 1
fi

