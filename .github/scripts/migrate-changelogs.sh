#!/bin/bash

# One-time migration: inserts usage instructions and the <!-- CHANGELOG-BOUNDARY -->
# marker into every CHANGELOG.md in the monorepo, right before the first version heading.
# Preserves all existing content below.

set -euo pipefail

BOUNDARY_MARKER="<!-- CHANGELOG-BOUNDARY -->"
MIGRATED=0
SKIPPED=0

INSTRUCTION_BLOCK='<!-- Add your changelog entry below. Use a bump indicator to specify the version increment:
     +   YYYY-MM-DD  → patch (bug fixes, small changes)
     ++  YYYY-MM-DD  → minor (new features, backwards-compatible)
     +++ YYYY-MM-DD  → major (breaking changes)

  Example:
     + 2026-02-25
     - Fix token counting for streaming responses

  CI will automatically set the version number on merge. Do NOT edit the version in pyproject.toml. -->'

for changelog in $(find . -name "CHANGELOG.md" -not -path "./.venv/*" -not -path "*/.venv/*" -not -path "./node_modules/*" -not -path "*/node_modules/*" -not -path "./.git/*" | sort); do
    if grep -qF "$BOUNDARY_MARKER" "$changelog"; then
        echo "SKIP (already migrated): $changelog"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    FIRST_VERSION_LINE=$(grep -n -E '^## \[[0-9]+\.[0-9]+' "$changelog" | head -1 | cut -d: -f1)

    if [ -z "$FIRST_VERSION_LINE" ]; then
        echo "SKIP (no version headings): $changelog"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    # Split: header (everything before the first version) and body (from first version onward)
    HEAD_END=$((FIRST_VERSION_LINE - 1))
    HEADER=$(head -n "$HEAD_END" "$changelog")
    BODY=$(tail -n +"$FIRST_VERSION_LINE" "$changelog")

    # Strip trailing blank lines from header so spacing is consistent
    HEADER=$(echo "$HEADER" | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}')

    {
        echo "$HEADER"
        echo ""
        echo "$INSTRUCTION_BLOCK"
        echo ""
        echo "$BOUNDARY_MARKER"
        echo ""
        echo "$BODY"
    } > "$changelog"

    echo "OK: $changelog (marker inserted before line $FIRST_VERSION_LINE)"
    MIGRATED=$((MIGRATED + 1))
done

echo ""
echo "Done. Migrated: $MIGRATED, Skipped: $SKIPPED"
