#!/usr/bin/env bash
set -e

# Runs basedpyright and outputs JSON to stdout
# Usage: run-basedpyright.sh <package_dir> [output_file]

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PACKAGE_DIR="$1"
OUTPUT_FILE="${2:-/tmp/basedpyright.json}"

if [ -z "$PACKAGE_DIR" ]; then
    echo "Usage: run-basedpyright.sh <package_dir> [output_file]"
    exit 1
fi

cd "$PACKAGE_DIR" || {
    echo "Error: Failed to change to package directory: $PACKAGE_DIR"
    exit 1
}

echo -e "${YELLOW}=== Running basedpyright ===${NC}"

# Run basedpyright with JSON output
# basedpyright may output informational messages before the JSON, so we need to extract just the JSON
TEMP_OUTPUT=$(mktemp)
poetry run basedpyright --outputjson > "$TEMP_OUTPUT" 2>&1 || {
    echo "Note: basedpyright exited with non-zero status (expected if there are errors)"
}

# Extract JSON from output (basedpyright may print messages before the JSON)
# Find the first line starting with { and extract everything from there to the end
# This handles multi-line JSON objects
awk '/^{/,0' "$TEMP_OUTPUT" > "$OUTPUT_FILE"

# Validate the extracted JSON is valid
if ! jq empty "$OUTPUT_FILE" 2>/dev/null; then
    # If validation failed, try a more robust extraction using Python
    python3 -c "
import sys
import json
try:
    with open('$TEMP_OUTPUT', 'r') as f:
        content = f.read()
    # Find the first { and try to parse JSON from there
    start = content.find('{')
    if start != -1:
        json_str = content[start:]
        # Try to parse and re-serialize to ensure valid JSON
        json_obj = json.loads(json_str)
        with open('$OUTPUT_FILE', 'w') as f:
            json.dump(json_obj, f)
    else:
        sys.exit(1)
except:
    sys.exit(1)
" 2>/dev/null || {
        echo "Warning: Could not extract valid JSON, using raw output"
        cp "$TEMP_OUTPUT" "$OUTPUT_FILE"
    }
fi

rm -f "$TEMP_OUTPUT"

# Show summary
echo ""
echo -e "${YELLOW}=== Basedpyright summary ===${NC}"
jq '{version, time, summary, diagnostic_count: (.generalDiagnostics | length)}' "$OUTPUT_FILE" 2>/dev/null || {
    echo "Failed to parse JSON output"
    echo "Raw output:"
    head -20 "$OUTPUT_FILE"
}
echo ""

echo -e "${GREEN}✓ Basedpyright run complete${NC}"

