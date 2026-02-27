#!/usr/bin/env bash
set -euo pipefail

#
# Test suite for auto-resolve-version-conflicts.sh
# Creates a temporary git repo with simulated version conflicts and verifies resolution.
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_SCRIPT="$SCRIPT_DIR/../auto-resolve-version-conflicts.sh"
TMPDIR=$(mktemp -d)
PASS=0
FAIL=0

cleanup() {
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

create_pyproject() {
  local dir="$1"
  local version="$2"
  mkdir -p "$dir"
  cat > "$dir/pyproject.toml" <<EOF
[tool.poetry]
name = "$(basename "$dir")"
version = "$version"
description = "test package"
EOF
}

create_changelog() {
  local dir="$1"
  local version="$2"
  local entry="$3"
  mkdir -p "$dir"
  cat > "$dir/CHANGELOG.md" <<EOF
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [$version] - 2026-02-25
- $entry

## [1.0.0] - 2026-01-01
- Initial release
EOF
}

assert_version() {
  local pyproject="$1"
  local expected="$2"
  local label="$3"
  local actual
  actual=$(grep -E '^version' "$pyproject" | sed -E 's/^version[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/')
  if [[ "$actual" == "$expected" ]]; then
    echo "  PASS: $label (got $actual)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $label (expected $expected, got $actual)"
    FAIL=$((FAIL + 1))
  fi
}

assert_changelog_version() {
  local changelog="$1"
  local expected="$2"
  local label="$3"
  local actual
  actual=$(grep -oE '## \[[0-9]+\.[0-9]+\.[0-9]+\]' "$changelog" | head -1 | sed -E 's/## \[([0-9.]+)\]/\1/')
  if [[ "$actual" == "$expected" ]]; then
    echo "  PASS: $label (got $actual)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $label (expected $expected, got $actual)"
    FAIL=$((FAIL + 1))
  fi
}

assert_changelog_contains() {
  local changelog="$1"
  local text="$2"
  local label="$3"
  if grep -qF "$text" "$changelog"; then
    echo "  PASS: $label"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $label (text '$text' not found)"
    FAIL=$((FAIL + 1))
  fi
}

# --- Test: determine_bump_type ---
echo "=== Unit tests: determine_bump_type ==="

source "$SOURCE_SCRIPT" 2>/dev/null || true

test_bump_type() {
  local ancestor="$1"
  local pr="$2"
  local expected="$3"
  local result
  result=$(determine_bump_type "$ancestor" "$pr")
  if [[ "$result" == "$expected" ]]; then
    echo "  PASS: $ancestor → $pr = $expected"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $ancestor → $pr expected $expected, got $result"
    FAIL=$((FAIL + 1))
  fi
}

test_bump_type "1.47.5" "1.47.6" "patch"
test_bump_type "1.47.5" "1.48.0" "minor"
test_bump_type "1.47.5" "2.0.0" "major"
test_bump_type "1.47.5" "1.47.5" "none"
test_bump_type "0.10.82" "0.10.83" "patch"
test_bump_type "0.10.82" "0.11.0" "minor"

# --- Test: apply_bump ---
echo ""
echo "=== Unit tests: apply_bump ==="

test_apply_bump() {
  local base="$1"
  local bump="$2"
  local expected="$3"
  local result
  result=$(apply_bump "$base" "$bump")
  if [[ "$result" == "$expected" ]]; then
    echo "  PASS: $base + $bump = $expected"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $base + $bump expected $expected, got $result"
    FAIL=$((FAIL + 1))
  fi
}

test_apply_bump "1.48.0" "patch" "1.48.1"
test_apply_bump "1.48.0" "minor" "1.49.0"
test_apply_bump "1.48.0" "major" "2.0.0"
test_apply_bump "0.10.83" "patch" "0.10.84"

# --- Integration test: full conflict resolution ---
echo ""
echo "=== Integration test: patch conflict resolution ==="

TESTREPO="$TMPDIR/test-repo"
mkdir -p "$TESTREPO"
cd "$TESTREPO"
git init -q
git config user.name "test"
git config user.email "test@test.com"

create_pyproject "unique_toolkit" "1.47.5"
create_changelog "unique_toolkit" "1.47.5" "Base feature"
git add -A && git commit -q -m "initial"

git checkout -q -b pr-branch
create_pyproject "unique_toolkit" "1.47.6"
create_changelog "unique_toolkit" "1.47.6" "PR feature: new widget"
git add -A && git commit -q -m "pr: patch bump"

git checkout -q main
create_pyproject "unique_toolkit" "1.48.0"
create_changelog "unique_toolkit" "1.48.0" "Main feature: big update"
git add -A && git commit -q -m "main: minor bump"

git checkout -q pr-branch
if git merge main --no-commit --no-ff 2>/dev/null; then
  echo "  FAIL: Expected conflicts but merge succeeded"
  FAIL=$((FAIL + 1))
else
  echo "  PASS: Merge correctly produces conflicts"
  PASS=$((PASS + 1))
  git merge --abort
fi

ANCESTOR=$(git merge-base main pr-branch)
ANCESTOR_VER=$(git show "$ANCESTOR:unique_toolkit/pyproject.toml" | grep '^version' | sed -E 's/.*"([^"]+)".*/\1/')
MAIN_VER=$(git show "main:unique_toolkit/pyproject.toml" | grep '^version' | sed -E 's/.*"([^"]+)".*/\1/')
PR_VER=$(git show "pr-branch:unique_toolkit/pyproject.toml" | grep '^version' | sed -E 's/.*"([^"]+)".*/\1/')

BUMP=$(determine_bump_type "$ANCESTOR_VER" "$PR_VER")
NEW_VER=$(apply_bump "$MAIN_VER" "$BUMP")

assert_version <(echo "version = \"$NEW_VER\"") "1.48.1" "Computed new version"

NEW_ENTRY=$(extract_new_changelog_entry "$ANCESTOR" "pr-branch" "unique_toolkit/CHANGELOG.md")
if echo "$NEW_ENTRY" | grep -q "PR feature: new widget"; then
  echo "  PASS: Extracted PR changelog entry"
  PASS=$((PASS + 1))
else
  echo "  FAIL: Could not extract PR changelog entry"
  FAIL=$((FAIL + 1))
fi

# --- Integration test: minor bump conflict ---
echo ""
echo "=== Integration test: minor bump conflict ==="

cd "$TMPDIR"
TESTREPO2="$TMPDIR/test-repo2"
mkdir -p "$TESTREPO2"
cd "$TESTREPO2"
git init -q
git config user.name "test"
git config user.email "test@test.com"

create_pyproject "unique_sdk" "0.10.82"
create_changelog "unique_sdk" "0.10.82" "Base feature"
git add -A && git commit -q -m "initial"

git checkout -q -b pr-branch
create_pyproject "unique_sdk" "0.11.0"
create_changelog "unique_sdk" "0.11.0" "PR feature: breaking API change"
git add -A && git commit -q -m "pr: minor bump"

git checkout -q main
create_pyproject "unique_sdk" "0.10.83"
create_changelog "unique_sdk" "0.10.83" "Main patch"
git add -A && git commit -q -m "main: patch bump"

ANCESTOR=$(git merge-base main pr-branch)
ANCESTOR_VER="0.10.82"
MAIN_VER="0.10.83"
PR_VER="0.11.0"

BUMP=$(determine_bump_type "$ANCESTOR_VER" "$PR_VER")
NEW_VER=$(apply_bump "$MAIN_VER" "$BUMP")

if [[ "$BUMP" == "minor" ]]; then
  echo "  PASS: Detected minor bump"
  PASS=$((PASS + 1))
else
  echo "  FAIL: Expected minor, got $BUMP"
  FAIL=$((FAIL + 1))
fi

if [[ "$NEW_VER" == "0.11.0" ]]; then
  echo "  PASS: New version is 0.11.0"
  PASS=$((PASS + 1))
else
  echo "  FAIL: Expected 0.11.0, got $NEW_VER"
  FAIL=$((FAIL + 1))
fi

# --- Unit tests: resolve_pyproject_conflicts ---
echo ""
echo "=== Unit tests: resolve_pyproject_conflicts (conflict markers) ==="

CONFLICT_DIR="$TMPDIR/conflict-tests"
mkdir -p "$CONFLICT_DIR"

# Success: version-only conflict block; PR-added dependency preserved
pyproject_ok="$CONFLICT_DIR/unique_toolkit/pyproject_ok"
mkdir -p "$(dirname "$pyproject_ok")"
cat > "$pyproject_ok" <<'PYEOF'
[tool.poetry]
name = "unique_toolkit"
<<<<<<< HEAD
version = "1.48.0"
=======
version = "1.47.13"
>>>>>>> origin/main
description = ""

[tool.poetry.dependencies]
python = "^3.12"
pypandoc = "^1.16.2"
PYEOF
if resolve_pyproject_conflicts "$pyproject_ok" "1.48.1"; then
  if grep -q '^version = "1.48.1"$' "$pyproject_ok" && grep -q 'pypandoc = "\^1.16.2"' "$pyproject_ok" && ! grep -q '<<<<<<<' "$pyproject_ok"; then
    echo "  PASS: version-only conflict resolved, dependency preserved"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: resolved content wrong or markers remain"
    FAIL=$((FAIL + 1))
  fi
else
  echo "  FAIL: resolve_pyproject_conflicts returned failure (expected success)"
  FAIL=$((FAIL + 1))
fi

# Bail: conflict block contains non-version line (dependency)
pyproject_bail="$CONFLICT_DIR/unique_toolkit/pyproject_bail"
mkdir -p "$(dirname "$pyproject_bail")"
cat > "$pyproject_bail" <<'PYEOF'
[tool.poetry]
name = "unique_toolkit"
<<<<<<< HEAD
version = "1.48.0"
pypandoc = "^1.16.2"
=======
version = "1.47.13"
>>>>>>> origin/main
PYEOF
if resolve_pyproject_conflicts "$pyproject_bail" "1.48.1"; then
  echo "  FAIL: should have bailed on non-version line in conflict block"
  FAIL=$((FAIL + 1))
else
  echo "  PASS: bails when conflict block has non-version content"
  PASS=$((PASS + 1))
fi

# --- Unit tests: resolve_changelog_conflicts ---
echo ""
echo "=== Unit tests: resolve_changelog_conflicts (conflict markers) ==="

# Success: conflict block has ## [ header and bullets; both sides kept, ours version updated
changelog_ok="$CONFLICT_DIR/unique_toolkit/changelog_ok"
cat > "$changelog_ok" <<'CHEOF'
# Changelog

<<<<<<< HEAD
## [1.48.0] - 2026-02-26
- Add pandoc markdown to docx

=======
## [1.47.13] - 2026-02-26
- Subagent file access

>>>>>>> origin/main
## [1.47.12] - 2026-02-25
- Older entry
CHEOF
if resolve_changelog_conflicts "$changelog_ok" "1.48.1"; then
  if grep -q '## \[1.48.1\]' "$changelog_ok" && grep -q 'Add pandoc markdown' "$changelog_ok" && grep -q 'Subagent file access' "$changelog_ok" && grep -q 'Older entry' "$changelog_ok" && ! grep -q '<<<<<<<' "$changelog_ok"; then
    echo "  PASS: changelog conflict resolved, both sides kept, version updated"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: changelog resolved content wrong or markers remain"
    FAIL=$((FAIL + 1))
  fi
else
  echo "  FAIL: resolve_changelog_conflicts returned failure (expected success)"
  FAIL=$((FAIL + 1))
fi

# Bail: conflict block has no ## [ version header
changelog_bail="$CONFLICT_DIR/unique_toolkit/changelog_bail"
cat > "$changelog_bail" <<'CHEOF'
# Changelog

## [1.47.12] - 2026-02-25
<<<<<<< HEAD
- Fix typo in docstring

=======
- Different fix for same line

>>>>>>> origin/main
CHEOF
if resolve_changelog_conflicts "$changelog_bail" "1.48.1"; then
  echo "  FAIL: should have bailed on conflict block with no version header"
  FAIL=$((FAIL + 1))
else
  echo "  PASS: bails when changelog conflict block has no ## [ header"
  PASS=$((PASS + 1))
fi

# --- Summary ---
echo ""
echo "=============================="
echo "Tests: $((PASS + FAIL)), Passed: $PASS, Failed: $FAIL"
echo "=============================="

if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
