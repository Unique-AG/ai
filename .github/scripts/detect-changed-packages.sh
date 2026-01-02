#!/usr/bin/env bash
set -e

# Script to detect changed packages from a list of changed files
# Usage: detect-changed-packages.sh [changed_files.txt]
#   If no file is provided, reads from stdin

# Read changed files from file argument or stdin
if [ $# -gt 0 ]; then
    CHANGED_FILES="$1"
    if [ ! -f "$CHANGED_FILES" ]; then
        echo "Error: File '$CHANGED_FILES' does not exist" >&2
        exit 1
    fi
    exec < "$CHANGED_FILES"
fi

# Read changed files and extract package names
packages=()

while IFS= read -r file; do
    # Skip if file is empty or deleted
    [ -z "$file" ] && continue
    
    # Extract package name based on directory structure
    # Root level packages: unique_sdk, unique_mcp, unique_orchestrator, unique_toolkit
    if [[ "$file" =~ ^unique_(sdk|mcp|orchestrator|toolkit)/ ]]; then
        pkg=$(echo "$file" | cut -d'/' -f1)
        packages+=("$pkg")
    # Packages in connectors/
    # TEMP: remove connectors due to the poetry file path changes
    # ADD this after merging
    # elif [[ "$file" =~ ^connectors/([^/]+)/ ]]; then
    #    pkg=$(echo "$file" | cut -d'/' -f2)
    #    packages+=("connectors/$pkg")
    # Packages in postprocessors/
    elif [[ "$file" =~ ^postprocessors/([^/]+)/ ]]; then
        pkg=$(echo "$file" | cut -d'/' -f2)
        packages+=("postprocessors/$pkg")
    # Packages in tool_packages/
    elif [[ "$file" =~ ^tool_packages/([^/]+)/ ]]; then
        pkg=$(echo "$file" | cut -d'/' -f2)
        packages+=("tool_packages/$pkg")
    fi
done

# Remove duplicates and sort
if [ ${#packages[@]} -eq 0 ]; then
    unique_packages=()
else
    unique_packages=($(printf '%s\n' "${packages[@]}" | sort -u))
fi

# Create comma-separated list
if [ ${#unique_packages[@]} -eq 0 ]; then
    packages_list=""
else
    packages_list=$(IFS=','; echo "${unique_packages[*]}")
fi

# Create JSON array
packages_json="["
for i in "${!unique_packages[@]}"; do
    if [ $i -gt 0 ]; then
        packages_json+=","
    fi
    packages_json+="\"${unique_packages[$i]}\""
done
packages_json+="]"

# Output results
if [ ${#unique_packages[@]} -gt 0 ]; then
    echo "Detected packages: ${packages_list}"
fi

# Set GitHub Actions outputs if running in CI
if [ -n "$GITHUB_OUTPUT" ]; then
    echo "packages=${packages_list}" >> "$GITHUB_OUTPUT"
    echo "packages_json=${packages_json}" >> "$GITHUB_OUTPUT"
fi

# Set environment variables for easy access
if [ -n "$GITHUB_ENV" ]; then
    echo "CHANGED_PACKAGES=${packages_list}" >> "$GITHUB_ENV"
    echo "CHANGED_PACKAGES_JSON=${packages_json}" >> "$GITHUB_ENV"
fi

# Also output to stdout for non-CI usage
echo "packages=${packages_list}"
echo "packages_json=${packages_json}"
