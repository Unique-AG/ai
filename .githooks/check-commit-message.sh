#!/usr/bin/env bash
# Validates that the commit message subject follows the conventional commit format.
# Called by pre-commit at commit-msg stage.
#
# Required format:  type[(scope)]: summary
# Optional:         blank line + body, Refs: UN-XXXXX in body
#
# Allowed types: feat, fix, docs, chore, ci, deploy, improvement, refactor, test

set -euo pipefail

commit_msg_file="$1"
commit_msg=$(head -1 "$commit_msg_file")

# Skip merge commits, fixup!, squash!, revert
if [[ "$commit_msg" =~ ^(Merge|Revert|fixup\!|squash\!) ]]; then
  exit 0
fi

# Store pattern in variable so bash handles alternation correctly
pattern="^(feat|fix|docs|chore|ci|deploy|improvement|refactor|test)(\([a-z0-9:_-]+\))?: .+"

if [[ ! "$commit_msg" =~ $pattern ]]; then
  echo ""
  echo "❌ Commit message must follow the conventional commit format."
  echo ""
  echo "   Format:  type[(scope)]: summary"
  echo "   Types:   feat, fix, docs, chore, ci, deploy, improvement, refactor, test"
  echo ""
  echo "   Examples:"
  echo "     feat(toolkit): add pandoc converter"
  echo "     fix: handle missing header"
  echo "     docs: update README"
  echo ""
  echo "   Your message: '$commit_msg'"
  echo ""
  exit 1
fi

exit 0
