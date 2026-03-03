#!/usr/bin/env bash
# Validates that the current branch follows the project naming convention.
# Called by pre-commit at pre-push stage.
#
# Valid patterns:
#   type/UN-XXXXX-slug           (preferred, agent-friendly)
#   type/scope/UN-XXXXX-slug     (also valid, human-authored)
#
# Exempt (no ticket required):
#   main, master, develop
#   hotfix/*, release/*, chore/*

set -euo pipefail

branch=$(git branch --show-current)

# Exempt branches
exempt_pattern='^(main|master|develop|(hotfix|release|chore)/.+)$'
if [[ $branch =~ $exempt_pattern ]]; then
  exit 0
fi

# Valid branch pattern: type/UN-XXXXX-slug or type/scope/UN-XXXXX-slug
valid_pattern='^[a-z]+(/[a-z0-9_-]+)?/[Uu][Nn]-[0-9]+-[a-z0-9-]+$'
if [[ $branch =~ $valid_pattern ]]; then
  exit 0
fi

echo ""
echo "❌ Branch name '$branch' does not follow the naming convention."
echo ""
echo "   Required format:  type/UN-XXXXX-short-slug"
echo "   Also valid:       type/scope/UN-XXXXX-short-slug"
echo ""
echo "   Examples:"
echo "     feat/un-17684-pandoc-converter"
echo "     fix/un-17492-pyproject-changes"
echo "     feat/toolkit/un-17684-pandoc-converter"
echo ""
echo "   Exempt (no ticket needed): hotfix/*, release/*, chore/*"
echo ""
exit 1
