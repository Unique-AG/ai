#!/bin/bash

# Tests for auto-version-bump.sh — verifies correct version incrementing
# and changelog rewriting across all bump levels and edge cases.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUMP_SCRIPT="$SCRIPT_DIR/auto-version-bump.sh"
TMPDIR=$(mktemp -d)
TESTS_PASSED=0
TESTS_FAILED=0

cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT

pass() { echo -e "${GREEN}PASS${NC}: $1"; TESTS_PASSED=$((TESTS_PASSED + 1)); }
fail() { echo -e "${RED}FAIL${NC}: $1 — $2"; TESTS_FAILED=$((TESTS_FAILED + 1)); }

setup_package() {
    local name="$1" version="$2" changelog="$3"
    local pkg="$TMPDIR/$name"
    rm -rf "$pkg"
    mkdir -p "$pkg"
    echo "[tool.poetry]
name = \"$name\"
version = \"$version\"
description = \"test\"" > "$pkg/pyproject.toml"
    echo "$changelog" > "$pkg/CHANGELOG.md"
}

get_version() {
    grep -E '^version[[:space:]]*=' "$TMPDIR/$1/pyproject.toml" | head -1 | sed -E 's/^version[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/'
}

get_first_version_heading() {
    grep -m1 -E '## \[' "$TMPDIR/$1/CHANGELOG.md" | sed -E 's/## \[([^]]+)\].*/\1/'
}

has_boundary() {
    grep -qF "<!-- ADD CHANGELOG ENTRY ABOVE THIS BOUNDARY -->" "$TMPDIR/$1/CHANGELOG.md"
}

# --- Test: patch bump ---

setup_package "test_patch" "1.2.3" "# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

+ 2026-02-24
- Fix a small bug

<!-- ADD CHANGELOG ENTRY ABOVE THIS BOUNDARY -->

## [1.2.3] - 2026-02-20
- Previous change"

(cd "$TMPDIR" && "$BUMP_SCRIPT" test_patch)
NEW_VER=$(get_version "test_patch")
[ "$NEW_VER" = "1.2.4" ] && pass "Patch bump: 1.2.3 -> 1.2.4" || fail "Patch bump" "got $NEW_VER"

HEADING=$(get_first_version_heading "test_patch")
[ "$HEADING" = "1.2.4" ] && pass "Patch bump changelog heading" || fail "Patch bump changelog heading" "got $HEADING"

has_boundary "test_patch" && pass "Boundary marker preserved" || fail "Boundary marker" "missing"

# --- Test: minor bump ---

setup_package "test_minor" "2.5.8" "# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

++ 2026-02-24
- Add a new feature

<!-- ADD CHANGELOG ENTRY ABOVE THIS BOUNDARY -->

## [2.5.8] - 2026-02-20
- Old change"

(cd "$TMPDIR" && "$BUMP_SCRIPT" test_minor)
NEW_VER=$(get_version "test_minor")
[ "$NEW_VER" = "2.6.0" ] && pass "Minor bump: 2.5.8 -> 2.6.0" || fail "Minor bump" "got $NEW_VER"

# --- Test: major bump ---

setup_package "test_major" "0.9.12" "# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

+++ 2026-02-24
- Breaking: completely redesign API

<!-- ADD CHANGELOG ENTRY ABOVE THIS BOUNDARY -->

## [0.9.12] - 2026-02-20
- Old stuff"

(cd "$TMPDIR" && "$BUMP_SCRIPT" test_major)
NEW_VER=$(get_version "test_major")
[ "$NEW_VER" = "1.0.0" ] && pass "Major bump: 0.9.12 -> 1.0.0" || fail "Major bump" "got $NEW_VER"

# --- Test: multiple entries, highest wins ---

setup_package "test_multi" "3.1.0" "# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

+ 2026-02-24
- Small fix

++ 2026-02-23
- New feature from earlier PR

<!-- ADD CHANGELOG ENTRY ABOVE THIS BOUNDARY -->

## [3.1.0] - 2026-02-18
- Old"

(cd "$TMPDIR" && "$BUMP_SCRIPT" test_multi)
NEW_VER=$(get_version "test_multi")
[ "$NEW_VER" = "3.2.0" ] && pass "Multi-entry highest wins: 3.1.0 -> 3.2.0" || fail "Multi-entry" "got $NEW_VER"

# Verify both changes are in the new version section
CHANGELOG_CONTENT=$(cat "$TMPDIR/test_multi/CHANGELOG.md")
echo "$CHANGELOG_CONTENT" | grep -q "Small fix" && pass "Multi-entry: first change preserved" || fail "Multi-entry" "missing first change"
echo "$CHANGELOG_CONTENT" | grep -q "New feature" && pass "Multi-entry: second change preserved" || fail "Multi-entry" "missing second change"

# --- Test: no staging entries (no-op) ---

setup_package "test_noop" "1.0.0" "# Changelog

<!-- ADD CHANGELOG ENTRY ABOVE THIS BOUNDARY -->

## [1.0.0] - 2026-01-01
- Initial release"

(cd "$TMPDIR" && "$BUMP_SCRIPT" test_noop)
NOOP_VER=$(get_version "test_noop")
[ "$NOOP_VER" = "1.0.0" ] && pass "No-op: version unchanged" || fail "No-op" "got $NOOP_VER"

# --- Test: uv-style pyproject.toml ---

setup_package "test_uv" "0.1.0" "# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

+ 2026-02-24
- Fix something

<!-- ADD CHANGELOG ENTRY ABOVE THIS BOUNDARY -->

## [0.1.0] - 2026-02-01
- Init"

echo '[project]
name = "test_uv"
version = "0.1.0"
description = "test"' > "$TMPDIR/test_uv/pyproject.toml"

(cd "$TMPDIR" && "$BUMP_SCRIPT" test_uv)
NEW_VER=$(get_version "test_uv")
[ "$NEW_VER" = "0.1.1" ] && pass "UV pyproject.toml: 0.1.0 -> 0.1.1" || fail "UV pyproject.toml" "got $NEW_VER"

# --- Test: dry run ---

setup_package "test_dry" "1.0.0" "# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

+ 2026-02-24
- A change

<!-- ADD CHANGELOG ENTRY ABOVE THIS BOUNDARY -->

## [1.0.0] - 2026-01-01
- Init"

(cd "$TMPDIR" && "$BUMP_SCRIPT" test_dry --dry-run)
DRY_VER=$(get_version "test_dry")
[ "$DRY_VER" = "1.0.0" ] && pass "Dry run: version unchanged" || fail "Dry run" "got $DRY_VER"

# --- Test: missing boundary marker (should fail) ---

setup_package "test_no_boundary" "1.0.0" "# Changelog

## [1.0.0] - 2026-01-01
- Init"

if (cd "$TMPDIR" && "$BUMP_SCRIPT" test_no_boundary 2>/dev/null); then
    fail "Missing boundary" "expected failure but script succeeded"
else
    pass "Missing boundary: script fails"
fi
NBOUND_VER=$(get_version "test_no_boundary")
[ "$NBOUND_VER" = "1.0.0" ] && pass "Missing boundary: version unchanged" || fail "Missing boundary version" "got $NBOUND_VER"

# --- Test: duplicate boundary markers (should fail) ---

setup_package "test_dup_boundary" "1.0.0" "# Changelog

+ 2026-02-24
- A change

<!-- ADD CHANGELOG ENTRY ABOVE THIS BOUNDARY -->

## [1.0.0] - 2026-01-01
- Init

<!-- ADD CHANGELOG ENTRY ABOVE THIS BOUNDARY -->"

if (cd "$TMPDIR" && "$BUMP_SCRIPT" test_dup_boundary 2>/dev/null); then
    fail "Duplicate boundary" "expected failure but script succeeded"
else
    pass "Duplicate boundary: script fails"
fi
DUP_VER=$(get_version "test_dup_boundary")
[ "$DUP_VER" = "1.0.0" ] && pass "Duplicate boundary: version unchanged" || fail "Duplicate boundary version" "got $DUP_VER"

# --- Test: staging with bump indicator but no changes (should fail) ---

setup_package "test_no_changes" "1.0.0" "# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

+ 2026-02-24

<!-- ADD CHANGELOG ENTRY ABOVE THIS BOUNDARY -->

## [1.0.0] - 2026-01-01
- Init"

if (cd "$TMPDIR" && "$BUMP_SCRIPT" test_no_changes 2>/dev/null); then
    fail "Bump without changes" "expected failure but script succeeded"
else
    pass "Bump without changes: script fails"
fi

# --- Test: instruction comment block is ignored during bump ---

setup_package "test_instructions" "2.0.0" "# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- Add your changelog entry below. Use a bump indicator to specify the version increment:
     +   YYYY-MM-DD  → patch (bug fixes, small changes)
     ++  YYYY-MM-DD  → minor (new features, backwards-compatible)
     +++ YYYY-MM-DD  → major (breaking changes)

  Example:
     + 2026-02-25
     - Fix token counting for streaming responses

  CI will automatically set the version number on merge. Do NOT edit the version in pyproject.toml. -->

+ 2026-02-24
- Actual change that should appear

<!-- ADD CHANGELOG ENTRY ABOVE THIS BOUNDARY -->

## [2.0.0] - 2026-02-01
- Old entry"

(cd "$TMPDIR" && "$BUMP_SCRIPT" test_instructions)
NEW_VER=$(get_version "test_instructions")
[ "$NEW_VER" = "2.0.1" ] && pass "Instruction block: version bumped to 2.0.1" || fail "Instruction block version" "got $NEW_VER"

CONTENT=$(cat "$TMPDIR/test_instructions/CHANGELOG.md")
echo "$CONTENT" | grep -q "Actual change" && pass "Instruction block: real change preserved" || fail "Instruction block" "missing real change"
! echo "$CONTENT" | grep -q "Add your changelog entry" && pass "Instruction block: instructions not in version section" || fail "Instruction block" "instructions leaked into version section"

# --- Summary ---

echo ""
echo "========================="
echo "Results: $TESTS_PASSED passed, $TESTS_FAILED failed"
echo "========================="
[ "$TESTS_FAILED" -eq 0 ] && exit 0 || exit 1
