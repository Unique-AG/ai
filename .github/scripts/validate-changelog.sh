#!/bin/bash

# Script to validate changelog and version bump for a package
# Usage: ./validate-changelog.sh <package_name> <base_ref>

set -e

PACKAGE="$1"
BASE_REF="$2"

if [ -z "$PACKAGE" ] || [ -z "$BASE_REF" ]; then
    echo "❌ Error: Package name and base ref are required"
    echo "Usage: $0 <package_name> <base_ref>"
    exit 1
fi

echo "🔍 Validating package: $PACKAGE"

# Get the merge base between the PR and target branch  
git fetch origin $BASE_REF
MERGE_BASE=$(git merge-base HEAD origin/$BASE_REF)

# Check CHANGELOG.md is updated
if ! git diff --name-only $MERGE_BASE..HEAD | grep -q "^$PACKAGE/CHANGELOG.md$"; then
    echo "❌ Error: $PACKAGE/CHANGELOG.md must be updated in this PR"
    echo "Please add an entry to the changelog describing your changes."
    exit 1
else
    echo "✅ $PACKAGE/CHANGELOG.md has been updated"
fi

# Check pyproject.toml exists and has been modified
if ! git diff --name-only $MERGE_BASE..HEAD | grep -q "^$PACKAGE/pyproject.toml$"; then
    echo "❌ Error: $PACKAGE/pyproject.toml must be updated in this PR"
    echo "Please update the version in pyproject.toml to reflect your changes."
    exit 1
fi

# Extract and compare versions
BASE_VERSION=$(git show $MERGE_BASE:$PACKAGE/pyproject.toml | grep -E '^version\s*=' | sed -E 's/version\s*=\s*"([^"]+)"/\1/')
CURRENT_VERSION=$(grep -E '^version\s*=' $PACKAGE/pyproject.toml | sed -E 's/version\s*=\s*"([^"]+)"/\1/')

echo "Base branch version: $BASE_VERSION"
echo "Current branch version: $CURRENT_VERSION"

if [ "$BASE_VERSION" = "$CURRENT_VERSION" ]; then
    echo "❌ Error: Version in $PACKAGE/pyproject.toml has not been updated"
    echo "Please bump the version number to reflect your changes."
    echo "Current version: $CURRENT_VERSION"
    exit 1
else
    echo "✅ Version has been updated from $BASE_VERSION to $CURRENT_VERSION"
fi
