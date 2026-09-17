#!/usr/bin/env bats
#
# Tests for .github/scripts/changelog-check.sh
#
# The check decides, from the PR diff, whether a client-facing changelog
# fragment under .changelog/unreleased/ is required, and validates any
# added/modified fragment against .changie.yaml. Each test builds a tiny
# git repo with a `main` branch and a feature branch, then runs the script
# with CHANGIE_CHECK_BASE_SHA / CHANGIE_CHECK_HEAD_SHA pointing at them —
# the same way ci.yaml invokes it.

load test_helper

SCRIPT="$SCRIPTS_DIR/changelog-check.sh"
REPO_ROOT="$(dirname "$SCRIPTS_DIR")"
REPO_ROOT="$(dirname "$REPO_ROOT")"

setup() {
    export TEST_TMPDIR="$(mktemp -d)"
    cd "$TEST_TMPDIR" || exit 1

    git init -q -b main .
    git config user.email test@example.com
    git config user.name test
    cp "$REPO_ROOT/.changie.yaml" .changie.yaml
    mkdir -p .changelog/unreleased unique_toolkit/unique_toolkit unique_toolkit/tests
    touch .changelog/unreleased/.gitkeep
    echo "x = 1" > unique_toolkit/unique_toolkit/mod.py
    git add -A
    git commit -q -m "init"
    export BASE_SHA="$(git rev-parse HEAD)"
    git checkout -q -b feature
    unset CHANGIE_CHECK_LABELS
}

teardown() {
    cd "$TESTS_DIR" || true
    if [ -n "$TEST_TMPDIR" ] && [ -d "$TEST_TMPDIR" ]; then
        rm -rf "$TEST_TMPDIR"
    fi
}

commit_all() {
    git add -A
    git commit -q -m "$1"
    export HEAD_SHA="$(git rev-parse HEAD)"
}

run_check() {
    CHANGIE_CHECK_BASE_SHA="$BASE_SHA" CHANGIE_CHECK_HEAD_SHA="$HEAD_SHA" run bash "$SCRIPT"
}

write_fragment() {
    local file="$1" component="${2:-API / SDK}" kind="${3:-Fixed}" audience="${4:-user}" ticket="${5:-}"
    {
        echo "component: $component"
        echo "kind: $kind"
        echo "body: The problem with X now works as intended."
        echo "time: 2026-09-08T21:06:07.123456+02:00"
        echo "custom:"
        echo "    Audience: $audience"
        if [[ -n "$ticket" ]]; then
            echo "    Ticket: $ticket"
        fi
    } > "$file"
}

@test "source change without fragment fails" {
    echo "x = 2" > unique_toolkit/unique_toolkit/mod.py
    commit_all "change"
    run_check
    [ "$status" -eq 1 ]
    [[ "$output" == *"No changelog fragment found"* ]]
}

@test "source change with a valid fragment passes" {
    echo "x = 2" > unique_toolkit/unique_toolkit/mod.py
    write_fragment .changelog/unreleased/fixed-api---sdk-20260908-210607.yaml
    commit_all "change + fragment"
    run_check
    [ "$status" -eq 0 ]
    [[ "$output" == *"A new changelog fragment was found"* ]]
}

@test "no-changelog label exempts the PR" {
    echo "x = 2" > unique_toolkit/unique_toolkit/mod.py
    commit_all "change"
    CHANGIE_CHECK_LABELS="area/x,no-changelog" run_check
    [ "$status" -eq 0 ]
    [[ "$output" == *"Exempt via label"* ]]
}

@test "tests, docs, lockfiles and release-please artifacts do not require a fragment" {
    echo "def test_x(): pass" > unique_toolkit/tests/test_mod.py
    mkdir -p docs unique_toolkit/docs
    echo "# doc" > docs/page.md
    echo "# doc" > unique_toolkit/docs/page.md
    echo "lock" > uv.lock
    echo "# Changelog" > unique_toolkit/CHANGELOG.md
    echo '{}' > .release-please-manifest.json
    mkdir -p .github/workflows
    echo "name: x" > .github/workflows/x.yaml
    commit_all "non-user-visible"
    run_check
    [ "$status" -eq 0 ]
    [[ "$output" == *"No changed file requires a changelog fragment"* ]]
}

@test "fragment with unknown component fails validation" {
    if ! command -v yq >/dev/null 2>&1; then
        skip "yq not installed"
    fi
    echo "x = 2" > unique_toolkit/unique_toolkit/mod.py
    write_fragment .changelog/unreleased/fixed-toolkit-20260908-210607.yaml "Toolkit"
    commit_all "bad component"
    run_check
    [ "$status" -eq 1 ]
    [[ "$output" == *"component 'Toolkit' is not one of"* ]]
}

@test "fragment with malformed ticket fails validation" {
    if ! command -v yq >/dev/null 2>&1; then
        skip "yq not installed"
    fi
    echo "x = 2" > unique_toolkit/unique_toolkit/mod.py
    write_fragment .changelog/unreleased/fixed-api---sdk-20260908-210607.yaml "API / SDK" "Fixed" "user" "ABC-12"
    commit_all "bad ticket"
    run_check
    [ "$status" -eq 1 ]
    [[ "$output" == *"does not match"* ]]
}

@test "fragment with multiple tickets passes validation" {
    if ! command -v yq >/dev/null 2>&1; then
        skip "yq not installed"
    fi
    echo "x = 2" > unique_toolkit/unique_toolkit/mod.py
    write_fragment .changelog/unreleased/fixed-api---sdk-20260908-210607.yaml "API / SDK" "Fixed" "admin" "UN-1, UN-22"
    commit_all "two tickets"
    run_check
    [ "$status" -eq 0 ]
}

@test "modifying an existing fragment does not count as adding one" {
    if ! command -v yq >/dev/null 2>&1; then
        skip "yq not installed"
    fi
    write_fragment .changelog/unreleased/fixed-api---sdk-20260908-210607.yaml
    git add -A
    git commit -q -m "existing fragment on main"
    export BASE_SHA="$(git rev-parse HEAD)"
    echo "x = 2" > unique_toolkit/unique_toolkit/mod.py
    sed -i.bak 's/now works as intended/now works/' .changelog/unreleased/fixed-api---sdk-20260908-210607.yaml
    rm -f .changelog/unreleased/*.bak
    commit_all "edit fragment"
    run_check
    [ "$status" -eq 1 ]
    [[ "$output" == *"No changelog fragment found"* ]]
}
