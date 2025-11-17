#!/usr/bin/env bash
set -e

# Applies a type checking baseline to the current branch
# Usage: apply-type-baseline.sh <package_dir> <baseline_file> [comparison_branch]

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PACKAGE_DIR="$1"
BASELINE_FILE="${2:-/tmp/baseline.json}"
COMPARE_BRANCH="${3:-main}"

if [ -z "$PACKAGE_DIR" ]; then
    echo "Usage: apply-type-baseline.sh <package_dir> [baseline_file] [comparison_branch]"
    exit 1
fi

cd "$PACKAGE_DIR" || {
    echo "Error: Failed to change to package directory: $PACKAGE_DIR"
    exit 1
}

echo -e "${YELLOW}=== Applying baseline to current branch ===${NC}"

# Ensure directory exists
mkdir -p .basedpyright

# Copy baseline from temp location
if [ -s "$BASELINE_FILE" ]; then
    cp "$BASELINE_FILE" .basedpyright/baseline.json
    echo -e "${GREEN}✓ Using baseline from $COMPARE_BRANCH${NC}"
    echo "  Baseline size: $(wc -c < .basedpyright/baseline.json) bytes"
else
    echo -e "${GREEN}✓ No baseline to apply ($COMPARE_BRANCH has no errors)${NC}"
    rm -f .basedpyright/baseline.json
fi

echo -e "${GREEN}✓ Baseline applied${NC}"

