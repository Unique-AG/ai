#!/usr/bin/env bash
# Test helper functions for BATS tests

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$(dirname "$TESTS_DIR")"

setup_file() {
    export BATS_FILE_TMPDIR="$(mktemp -d)"
}

teardown_file() {
    if [ -n "$BATS_FILE_TMPDIR" ] && [ -d "$BATS_FILE_TMPDIR" ]; then
        rm -rf "$BATS_FILE_TMPDIR"
    fi
}

setup() {
    export TEST_TMPDIR="$(mktemp -d)"
    cd "$TEST_TMPDIR" || exit 1
}

teardown() {
    cd "$TESTS_DIR" || true
    if [ -n "$TEST_TMPDIR" ] && [ -d "$TEST_TMPDIR" ]; then
        rm -rf "$TEST_TMPDIR"
    fi
}
