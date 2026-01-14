#!/usr/bin/env bats
# Tests for validate-changelog-version-bump.sh

# Load test helpers
load test_helper

# Setup and teardown are defined in test_helper.bash

# ==============================================================================
# Basic argument handling tests
# ==============================================================================

@test "shows help with --help flag" {
    run "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ "USAGE:" ]]
    [[ "$output" =~ "validate-changelog-version-bump.sh" ]]
}

@test "shows help with -h flag" {
    run "$SCRIPT" -h
    [ "$status" -eq 0 ]
    [[ "$output" =~ "USAGE:" ]]
}

@test "shows version with --version flag" {
    run "$SCRIPT" --version
    [ "$status" -eq 0 ]
    [[ "$output" =~ "version" ]]
}

@test "shows version with -v flag" {
    run "$SCRIPT" -v
    [ "$status" -eq 0 ]
    [[ "$output" =~ "version" ]]
}

@test "fails without package name argument" {
    run "$SCRIPT"
    [ "$status" -eq 2 ]
    [[ "$output" =~ "Package name is required" ]]
}

@test "fails with non-existent package directory" {
    run "$SCRIPT" "nonexistent_package" --base-ref main --no-fetch
    [ "$status" -eq 1 ]
    [[ "$output" =~ "does not exist" ]]
}

@test "fails with unknown long option" {
    run "$SCRIPT" --unknown-option
    [ "$status" -eq 2 ]
    [[ "$output" =~ "Unknown long option" ]]
}

# ==============================================================================
# Skip validation tests (no meaningful code changes)
# ==============================================================================

@test "skips validation when only lock files changed" {
    setup_test_repo
    
    # Make changes only to lock files
    echo "new lock content" >> "$TEST_PACKAGE/poetry.lock"
    git add .
    git commit -m "Update lock file"
    
    run "$SCRIPT" "$TEST_PACKAGE" --base-ref main --no-fetch
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Skipping validation" ]]
}

@test "skips validation when only docs changed" {
    setup_test_repo
    
    # Make changes only to docs
    mkdir -p "$TEST_PACKAGE/docs"
    echo "# New doc" > "$TEST_PACKAGE/docs/new.md"
    git add .
    git commit -m "Add docs"
    
    run "$SCRIPT" "$TEST_PACKAGE" --base-ref main --no-fetch
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Skipping validation" ]]
}

@test "skips validation when no changes in package" {
    setup_test_repo
    
    # No changes made to the package
    run "$SCRIPT" "$TEST_PACKAGE" --base-ref main --no-fetch
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Skipping validation" ]] || [[ "$output" =~ "No code changes" ]]
}

# ==============================================================================
# Validation failure tests
# ==============================================================================

@test "fails when CHANGELOG.md not updated" {
    setup_test_repo
    
    # Make code change but don't update changelog
    echo "# new code" >> "$TEST_PACKAGE/src/main.py"
    # Update pyproject.toml version
    sed -i.bak 's/version = "1.0.0"/version = "1.1.0"/' "$TEST_PACKAGE/pyproject.toml"
    rm -f "$TEST_PACKAGE/pyproject.toml.bak"
    git add .
    git commit -m "Add code without changelog"
    
    run "$SCRIPT" "$TEST_PACKAGE" --base-ref main --no-fetch
    [ "$status" -eq 1 ]
    [[ "$output" =~ "CHANGELOG.md must be updated" ]]
}

@test "fails when pyproject.toml not updated" {
    setup_test_repo
    
    # Make code change and update changelog but not pyproject.toml
    echo "# new code" >> "$TEST_PACKAGE/src/main.py"
    echo -e "\n## [1.1.0]\n- New feature" >> "$TEST_PACKAGE/CHANGELOG.md"
    git add .
    git commit -m "Add code with changelog but no version bump"
    
    run "$SCRIPT" "$TEST_PACKAGE" --base-ref main --no-fetch
    [ "$status" -eq 1 ]
    [[ "$output" =~ "pyproject.toml must be updated" ]]
}

@test "fails when version not bumped" {
    setup_test_repo
    
    # Make code change and update changelog with same version number
    # Note: We can't add the same version again (would be duplicate), so we modify pyproject.toml
    # without actually changing the version value - this tests version comparison
    echo "# new code" >> "$TEST_PACKAGE/src/main.py"
    # Append a changelog entry (using a different format that's still detected as a change)
    echo "" >> "$TEST_PACKAGE/CHANGELOG.md"
    echo "### Fixes" >> "$TEST_PACKAGE/CHANGELOG.md"
    echo "- Some bug fix" >> "$TEST_PACKAGE/CHANGELOG.md"
    # Modify pyproject.toml without changing version (add a comment or extra newline)
    echo "" >> "$TEST_PACKAGE/pyproject.toml"
    echo "# Some comment" >> "$TEST_PACKAGE/pyproject.toml"
    git add .
    git commit -m "Add code without version bump"
    
    run "$SCRIPT" "$TEST_PACKAGE" --base-ref main --no-fetch
    [ "$status" -eq 1 ]
    [[ "$output" =~ "has not been updated" ]]
}

@test "fails when changelog has duplicate version entries" {
    setup_test_repo
    
    # Add duplicate version to changelog
    echo "# new code" >> "$TEST_PACKAGE/src/main.py"
    # Add same version twice
    cat >> "$TEST_PACKAGE/CHANGELOG.md" << 'EOF'

## [1.1.0]
- First entry

## [1.1.0]
- Duplicate entry
EOF
    sed -i.bak 's/version = "1.0.0"/version = "1.1.0"/' "$TEST_PACKAGE/pyproject.toml"
    rm -f "$TEST_PACKAGE/pyproject.toml.bak"
    git add .
    git commit -m "Add duplicate changelog entries"
    
    run "$SCRIPT" "$TEST_PACKAGE" --base-ref main --no-fetch
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Duplicate version entries" ]]
}

@test "fails when changelog missing entry for current version" {
    setup_test_repo
    
    # Update to version 1.2.0 but only add changelog for 1.1.0
    echo "# new code" >> "$TEST_PACKAGE/src/main.py"
    echo -e "\n## [1.1.0]\n- Some change" >> "$TEST_PACKAGE/CHANGELOG.md"
    sed -i.bak 's/version = "1.0.0"/version = "1.2.0"/' "$TEST_PACKAGE/pyproject.toml"
    rm -f "$TEST_PACKAGE/pyproject.toml.bak"
    git add .
    git commit -m "Version mismatch"
    
    run "$SCRIPT" "$TEST_PACKAGE" --base-ref main --no-fetch
    [ "$status" -eq 1 ]
    [[ "$output" =~ "does not contain an entry for version" ]]
}

# ==============================================================================
# Successful validation tests
# ==============================================================================

@test "passes with valid changelog and version bump" {
    setup_test_repo
    
    # Make proper changes
    echo "# new code" >> "$TEST_PACKAGE/src/main.py"
    echo -e "\n## [1.1.0]\n- New feature added" >> "$TEST_PACKAGE/CHANGELOG.md"
    sed -i.bak 's/version = "1.0.0"/version = "1.1.0"/' "$TEST_PACKAGE/pyproject.toml"
    rm -f "$TEST_PACKAGE/pyproject.toml.bak"
    git add .
    git commit -m "Add feature with proper changelog"
    
    run "$SCRIPT" "$TEST_PACKAGE" --base-ref main --no-fetch
    [ "$status" -eq 0 ]
    [[ "$output" =~ "All validations passed" ]]
}

@test "passes with custom exclusions" {
    setup_test_repo
    
    # Make changes to a custom excluded pattern
    echo "custom content" > "$TEST_PACKAGE/custom.lock"
    git add .
    git commit -m "Add custom lock file"
    
    run "$SCRIPT" "$TEST_PACKAGE" --base-ref main --no-fetch --exclude "custom.lock,poetry.lock"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Skipping validation" ]] || [[ "$output" =~ "No code changes" ]]
}

@test "passes with backward compatible positional arguments" {
    setup_test_repo
    
    # Make proper changes
    echo "# new code" >> "$TEST_PACKAGE/src/main.py"
    echo -e "\n## [1.1.0]\n- New feature" >> "$TEST_PACKAGE/CHANGELOG.md"
    sed -i.bak 's/version = "1.0.0"/version = "1.1.0"/' "$TEST_PACKAGE/pyproject.toml"
    rm -f "$TEST_PACKAGE/pyproject.toml.bak"
    git add .
    git commit -m "Add feature"
    
    # Use positional args (backward compat): script <package> <base_ref>
    # Note: --no-fetch must come before positional args since they stop option parsing
    run "$SCRIPT" --no-fetch "$TEST_PACKAGE" main
    [ "$status" -eq 0 ]
    [[ "$output" =~ "All validations passed" ]]
}

# ==============================================================================
# Edge case tests
# ==============================================================================

@test "handles version with pre-release suffix" {
    setup_test_repo
    
    # Set up with pre-release version
    sed -i.bak 's/version = "1.0.0"/version = "1.1.0-alpha.1"/' "$TEST_PACKAGE/pyproject.toml"
    rm -f "$TEST_PACKAGE/pyproject.toml.bak"
    echo "# new code" >> "$TEST_PACKAGE/src/main.py"
    echo -e "\n## [1.1.0-alpha.1]\n- Alpha release" >> "$TEST_PACKAGE/CHANGELOG.md"
    git add .
    git commit -m "Alpha release"
    
    run "$SCRIPT" "$TEST_PACKAGE" --base-ref main --no-fetch
    [ "$status" -eq 0 ]
    [[ "$output" =~ "All validations passed" ]]
}

@test "handles nested package paths" {
    setup_test_repo
    
    # Go back to main to set up the nested connector
    git checkout main >/dev/null 2>&1
    
    # Create nested package structure
    mkdir -p "connectors/test_connector/src"
    cat > "connectors/test_connector/pyproject.toml" << 'EOF'
[project]
name = "test-connector"
version = "1.0.0"
EOF
    cat > "connectors/test_connector/CHANGELOG.md" << 'EOF'
# Changelog

## [1.0.0]
- Initial release
EOF
    echo "# code" > "connectors/test_connector/src/main.py"
    git add .
    git commit -m "Add nested connector" >/dev/null 2>&1
    git push origin main >/dev/null 2>&1
    
    # Now create a new feature branch for changes
    git checkout -b feature-nested >/dev/null 2>&1
    echo "# new code" >> "connectors/test_connector/src/main.py"
    echo -e "\n## [1.1.0]\n- New feature" >> "connectors/test_connector/CHANGELOG.md"
    sed -i.bak 's/version = "1.0.0"/version = "1.1.0"/' "connectors/test_connector/pyproject.toml"
    rm -f "connectors/test_connector/pyproject.toml.bak"
    git add .
    git commit -m "Update connector" >/dev/null 2>&1
    
    run "$SCRIPT" "connectors/test_connector" --base-ref main --no-fetch
    [ "$status" -eq 0 ]
    [[ "$output" =~ "All validations passed" ]]
}

@test "detects CHANGELOG.md deletion" {
    setup_test_repo
    
    # Make code change and delete changelog
    echo "# new code" >> "$TEST_PACKAGE/src/main.py"
    sed -i.bak 's/version = "1.0.0"/version = "1.1.0"/' "$TEST_PACKAGE/pyproject.toml"
    rm -f "$TEST_PACKAGE/pyproject.toml.bak"
    rm "$TEST_PACKAGE/CHANGELOG.md"
    git add .
    git commit -m "Delete changelog"
    
    run "$SCRIPT" "$TEST_PACKAGE" --base-ref main --no-fetch
    [ "$status" -eq 1 ]
    # Either complains about deletion or missing update
    [[ "$output" =~ "CHANGELOG" ]]
}
