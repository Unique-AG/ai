#!/usr/bin/env bash
# Validates that the commit message follows the conventional commit format.
# Called by pre-commit at commit-msg stage.
#
# Required format:
#   type(scope): description
#   type: description
#
# Allowed types: feat, fix, docs, chore, ci, deploy, improvement, refactor, test
#
# The first line (subject) must:
#   - Start with a valid type
#   - Be 72 characters or fewer
#   - Not end with a period

set -euo pipefail

commit_msg_file="$1"
commit_msg=$(head -1 "$commit_msg_file")

# Skip merge commits, fixup!, squash!
if [[ "$commit_msg" =~ ^(Merge|Revert|fixup!|squash!) ]]; then
  exit 0
fi

types="feat|fix|docs|chore|ci|deploy|improvement|refactor|test"

# Valid subject line: type(scope): description  or  type: description
subject_pattern="^($types)(\([a-z0-9:_-]+\))?: .{1,}"
if [[ ! "$commit_msg" =~ $subject_pattern ]]; then
  echo ""
  echo "❌ Commit message does not follow the conventional commit format."
  echo ""
  echo "   Required: type(scope): description"
  echo "             type: description"
  echo ""
  echo "   Allowed types: feat, fix, docs, chore, ci, deploy, improvement, refactor, test"
  echo ""
  echo "   Examples:"
  echo "     feat(toolkit): add pandoc markdown converter"
  echo "     fix: handle missing authorization header"
  echo "     chore(deps): upgrade pytest to 9.0"
  echo ""
  echo "   Your message: '$commit_msg'"
  echo ""
  exit 1
fi

# Check subject length
if [[ ${#commit_msg} -gt 72 ]]; then
  echo ""
  echo "❌ Commit subject is ${#commit_msg} characters (max 72)."
  echo "   Move detail into the commit body instead."
  echo ""
  exit 1
fi

# Check no trailing period
if [[ "$commit_msg" =~ \\.$ ]]; then
  echo ""
  echo "❌ Commit subject must not end with a period."
  echo ""
  exit 1
fi

exit 0
