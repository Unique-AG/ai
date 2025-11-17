#!/usr/bin/env bash
set -e

# Creates a type checking baseline from a specified branch
# Usage: create-type-baseline.sh <package_dir> <branch> [--ci]

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PACKAGE_DIR="$1"
BRANCH="$2"
CI_MODE=false

if [ "$3" = "--ci" ]; then
    CI_MODE=true
fi

if [ -z "$PACKAGE_DIR" ] || [ -z "$BRANCH" ]; then
    echo -e "${RED}Usage: create-type-baseline.sh <package_dir> <branch> [--ci]${NC}"
    exit 1
fi

cd "$PACKAGE_DIR" || {
    echo -e "${RED}Error: Failed to change to package directory: $PACKAGE_DIR${NC}"
    exit 1
}

echo -e "${YELLOW}=== Creating baseline from $BRANCH ===${NC}"

if [ "$CI_MODE" = true ]; then
    # In CI, checkout the base branch directly
    echo "Checking out base branch for baseline..."
    git checkout "origin/$BRANCH" --quiet 2>/dev/null || {
        echo -e "${RED}Error: Failed to checkout origin/$BRANCH${NC}"
        exit 1
    }
else
    # Local mode: stash changes and checkout
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    echo "Current branch: $CURRENT_BRANCH"
    echo "Stashing any uncommitted changes..."
    git stash push -m "type-check-baseline-temp" --quiet 2>/dev/null || true
    
    echo "Switching to $BRANCH..."
    git checkout "$BRANCH" --quiet 2>/dev/null || {
        echo -e "${RED}Error: Failed to checkout $BRANCH${NC}"
        git stash pop --quiet 2>/dev/null || true
        exit 1
    }
fi

# Create baseline directory
mkdir -p .basedpyright

# Run basedpyright with --writebaseline to create baseline
echo "Running basedpyright --writebaseline on $BRANCH..."
poetry run basedpyright --writebaseline 2>&1 || {
    echo "Note: basedpyright exited with non-zero status (expected if there are errors)"
}

# Check if baseline was created
if [ -f .basedpyright/baseline.json ]; then
    echo -e "${GREEN}✓ Baseline created successfully${NC}"
    echo "  Baseline size: $(wc -c < .basedpyright/baseline.json) bytes"
    # Count errors in baseline
    ERROR_COUNT=$(jq '[.files[] | length] | add // 0' .basedpyright/baseline.json 2>/dev/null || echo "0")
    echo "  Known errors in baseline: $ERROR_COUNT"
else
    echo -e "${GREEN}✓ No baseline created (no errors in $BRANCH)${NC}"
fi

# Copy baseline to temp location
cp .basedpyright/baseline.json /tmp/baseline.json 2>/dev/null || touch /tmp/baseline.json

# Checkout back to original branch
if [ "$CI_MODE" = true ]; then
    echo "Switching back to PR branch..."
    git checkout - --quiet
else
    echo "Switching back to $CURRENT_BRANCH..."
    git checkout "$CURRENT_BRANCH" --quiet
    echo "Restoring any stashed changes..."
    git stash pop --quiet 2>/dev/null || true
fi

echo -e "${GREEN}✓ Baseline creation complete${NC}"

