#!/bin/bash

# One-time migration: inserts the <!-- CHANGELOG-BOUNDARY --> marker into every
# CHANGELOG.md in the monorepo, right before the first version heading.

set -euo pipefail

BOUNDARY_MARKER="<!-- CHANGELOG-BOUNDARY -->"
MIGRATED=0
SKIPPED=0

for changelog in $(find . -name "CHANGELOG.md" -not -path "./node_modules/*" -not -path "./.git/*"); do
    if grep -qF "$BOUNDARY_MARKER" "$changelog"; then
        echo "SKIP (already migrated): $changelog"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    # Find the first version heading line: ## [X.Y.Z]
    FIRST_VERSION_LINE=$(grep -n -E '## \[[0-9]+\.[0-9]+' "$changelog" | head -1 | cut -d: -f1)

    if [ -z "$FIRST_VERSION_LINE" ]; then
        echo "SKIP (no version headings): $changelog"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    # Insert the boundary marker on the line before the first version heading
    # (with a blank line for readability)
    sed -i.bak "${FIRST_VERSION_LINE}i\\
${BOUNDARY_MARKER}\\
" "$changelog"
    rm -f "$changelog.bak"

    echo "OK: $changelog (marker inserted before line $FIRST_VERSION_LINE)"
    MIGRATED=$((MIGRATED + 1))
done

echo ""
echo "Done. Migrated: $MIGRATED, Skipped: $SKIPPED"
