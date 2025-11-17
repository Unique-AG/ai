#!/usr/bin/env bash
set -e

# Local convenience script for type checking with baseline comparison
# For CI usage, see the GitHub Actions workflow which calls the modular scripts directly
# 
# Usage:
#   run-type-check.sh [branch]

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory for finding other scripts
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Parse arguments
COMPARE_BRANCH="${1:-main}"

# Determine package directory
if [[ "$SCRIPT_DIR" == *".github/scripts"* ]]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    PACKAGE_DIR="$REPO_ROOT/unique_toolkit"
elif [ -d "unique_toolkit" ]; then
    PACKAGE_DIR="$(pwd)/unique_toolkit"
else
    PACKAGE_DIR="$(pwd)"
fi

# Validate package directory exists
if [ ! -d "$PACKAGE_DIR" ]; then
    echo -e "${RED}Error: Package directory does not exist: $PACKAGE_DIR${NC}"
    exit 1
fi

echo -e "${YELLOW}=== Type Checking unique_toolkit ===${NC}"
echo "Package directory: $PACKAGE_DIR"
echo "Comparing against branch: $COMPARE_BRANCH"
echo ""

# Check if poetry is available
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}Error: poetry not found. Please install poetry first.${NC}"
    exit 1
fi

# Ensure dependencies are installed
echo -e "${YELLOW}=== Checking dependencies ===${NC}"
cd "$PACKAGE_DIR"
poetry install --quiet
echo ""

# Step 1: Create baseline from comparison branch
bash "$SCRIPT_DIR/create-type-baseline.sh" "$PACKAGE_DIR" "$COMPARE_BRANCH"
echo ""

# Step 2: Apply baseline to current branch
bash "$SCRIPT_DIR/apply-type-baseline.sh" "$PACKAGE_DIR" /tmp/baseline.json "$COMPARE_BRANCH"
echo ""

# Step 3: Run basedpyright on current branch
bash "$SCRIPT_DIR/run-basedpyright.sh" "$PACKAGE_DIR" /tmp/basedpyright.json
echo ""

# Step 4: Report errors
bash "$SCRIPT_DIR/report-type-errors.sh" "$PACKAGE_DIR" /tmp/basedpyright.json
