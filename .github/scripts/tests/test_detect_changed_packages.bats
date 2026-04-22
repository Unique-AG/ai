#!/usr/bin/env bats

# Tests for .github/scripts/detect-changed-packages.sh.
#
# Each test builds a throwaway git repo, plants a fake
# `package_configuration.json` (driven via $PACKAGES_JSON so we don't
# touch the real one), runs the script against a constructed diff range,
# and asserts on the JSON output.

bats_require_minimum_version 1.5.0
load test_helper

SCRIPT="$SCRIPTS_DIR/detect-changed-packages.sh"
NULL_SHA="0000000000000000000000000000000000000000"

# Build a minimal repo with three publishable packages. Exports $BASE
# and sets the working dir to the repo root.
_init_repo() {
    mkdir -p "$TEST_TMPDIR/repo"
    cd "$TEST_TMPDIR/repo"

    git init --quiet --initial-branch=main .
    git config user.email "test@example.com"
    git config user.name "Test User"

    mkdir -p unique_toolkit unique_sdk tool_packages/unique_web_search
    echo "initial" > unique_toolkit/__init__.py
    echo "initial" > unique_sdk/__init__.py
    echo "initial" > tool_packages/unique_web_search/__init__.py
    echo "root" > README.md

    cat > packages.json <<'JSON'
[
  {"id": "toolkit", "dir": "unique_toolkit", "python": "3.12", "pypi_name": "unique_toolkit"},
  {"id": "sdk", "dir": "unique_sdk", "python": "3.11", "pypi_name": "unique_sdk"},
  {"id": "web_search", "dir": "tool_packages/unique_web_search", "python": "3.12", "pypi_name": "unique_web_search"},
  {"id": "search_proxy", "dir": "connectors/unique_search_proxy", "python": "3.12", "publish_skip": true}
]
JSON

    # Mirror the real repo layout so invalidator paths can be simulated
    # by touching the matching file in the fake tree.
    mkdir -p .github/scripts .github/workflows .github/actions/get-packages-matrix
    touch .github/scripts/rewrite-pyproject-for-dev.py
    touch .github/scripts/detect-changed-packages.sh
    touch .github/scripts/compute-calver.sh
    touch .github/workflows/publish-dev.yaml
    touch .github/actions/get-packages-matrix/package_configuration.json

    git add -A
    git commit --quiet -m "base"
    export BASE="$(git rev-parse HEAD)"
    export PACKAGES_JSON="$PWD/packages.json"
}

_commit() {
    git add -A
    git commit --quiet -m "$1"
    git rev-parse HEAD
}

_ids() {
    # Normalized "sort | tr" so assertions don't depend on jq ordering.
    jq -r '.include[].id' <<<"$1" | sort | tr '\n' ',' | sed 's/,$//'
}

@test "base is null SHA: returns all publishable packages" {
    _init_repo
    HEAD_SHA="$(git rev-parse HEAD)"

    run --separate-stderr "$SCRIPT" "$NULL_SHA" "$HEAD_SHA"
    [ "$status" -eq 0 ]
    [ "$(_ids "$output")" = "sdk,toolkit,web_search" ]
}

@test "unreachable base: returns all publishable packages" {
    _init_repo
    HEAD_SHA="$(git rev-parse HEAD)"

    run --separate-stderr "$SCRIPT" "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef" "$HEAD_SHA"
    [ "$status" -eq 0 ]
    [ "$(_ids "$output")" = "sdk,toolkit,web_search" ]
}

@test "empty diff: returns empty include array" {
    _init_repo
    HEAD_SHA="$(git rev-parse HEAD)"

    run --separate-stderr "$SCRIPT" "$HEAD_SHA" "$HEAD_SHA"
    [ "$status" -eq 0 ]
    [ "$output" = '{"include":[]}' ]
}

@test "single package changed: returns only that package" {
    _init_repo
    echo "change" >> unique_toolkit/__init__.py
    HEAD_SHA="$(_commit "toolkit change")"

    run --separate-stderr "$SCRIPT" "$BASE" "$HEAD_SHA"
    [ "$status" -eq 0 ]
    [ "$(_ids "$output")" = "toolkit" ]
}

@test "two packages changed: returns both" {
    _init_repo
    echo "change" >> unique_toolkit/__init__.py
    echo "change" >> unique_sdk/__init__.py
    HEAD_SHA="$(_commit "toolkit + sdk change")"

    run --separate-stderr "$SCRIPT" "$BASE" "$HEAD_SHA"
    [ "$status" -eq 0 ]
    [ "$(_ids "$output")" = "sdk,toolkit" ]
}

@test "nested package dir: tool_packages/unique_web_search resolves correctly" {
    _init_repo
    echo "change" >> tool_packages/unique_web_search/__init__.py
    HEAD_SHA="$(_commit "web_search change")"

    run --separate-stderr "$SCRIPT" "$BASE" "$HEAD_SHA"
    [ "$status" -eq 0 ]
    [ "$(_ids "$output")" = "web_search" ]
}

@test "publish_skip package changed alone: returns empty" {
    _init_repo
    mkdir -p connectors/unique_search_proxy
    echo "change" >> connectors/unique_search_proxy/__init__.py
    HEAD_SHA="$(_commit "search_proxy change (publish_skip)")"

    run --separate-stderr "$SCRIPT" "$BASE" "$HEAD_SHA"
    [ "$status" -eq 0 ]
    [ "$output" = '{"include":[]}' ]
}

@test "only non-package file changed: returns empty" {
    _init_repo
    echo "updated" >> README.md
    HEAD_SHA="$(_commit "readme change")"

    run --separate-stderr "$SCRIPT" "$BASE" "$HEAD_SHA"
    [ "$status" -eq 0 ]
    [ "$output" = '{"include":[]}' ]
}

@test "invalidator (rewrite script) changed: returns all publishable packages" {
    _init_repo
    echo "# tweak" >> .github/scripts/rewrite-pyproject-for-dev.py
    HEAD_SHA="$(_commit "rewrite tweak")"

    run --separate-stderr "$SCRIPT" "$BASE" "$HEAD_SHA"
    [ "$status" -eq 0 ]
    [ "$(_ids "$output")" = "sdk,toolkit,web_search" ]
}

@test "invalidator (publish-dev.yaml) changed: returns all publishable packages" {
    _init_repo
    echo "# tweak" >> .github/workflows/publish-dev.yaml
    HEAD_SHA="$(_commit "workflow tweak")"

    run --separate-stderr "$SCRIPT" "$BASE" "$HEAD_SHA"
    [ "$status" -eq 0 ]
    [ "$(_ids "$output")" = "sdk,toolkit,web_search" ]
}

@test "invalidator + single package change: invalidator wins (all packages)" {
    _init_repo
    echo "change" >> unique_toolkit/__init__.py
    echo "# tweak" >> .github/actions/get-packages-matrix/package_configuration.json
    HEAD_SHA="$(_commit "toolkit + packages json")"

    run --separate-stderr "$SCRIPT" "$BASE" "$HEAD_SHA"
    [ "$status" -eq 0 ]
    [ "$(_ids "$output")" = "sdk,toolkit,web_search" ]
}

@test "multi-commit range: aggregates changed packages across commits" {
    _init_repo
    echo "change" >> unique_toolkit/__init__.py
    _commit "toolkit" >/dev/null
    echo "change" >> unique_sdk/__init__.py
    HEAD_SHA="$(_commit "sdk")"

    run --separate-stderr "$SCRIPT" "$BASE" "$HEAD_SHA"
    [ "$status" -eq 0 ]
    [ "$(_ids "$output")" = "sdk,toolkit" ]
}

@test "dir-prefix is anchored: 'unique_toolkit' does not match 'unique_toolkit_extras/'" {
    _init_repo
    mkdir -p unique_toolkit_extras
    echo "change" >> unique_toolkit_extras/file.py
    HEAD_SHA="$(_commit "extras")"

    run --separate-stderr "$SCRIPT" "$BASE" "$HEAD_SHA"
    [ "$status" -eq 0 ]
    [ "$output" = '{"include":[]}' ]
}
