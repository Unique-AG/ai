#!/usr/bin/env bash
# Test helper functions for BATS tests

# Get the directory of this helper script
TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$(dirname "$TESTS_DIR")"
SCRIPT="$SCRIPTS_DIR/validate-changelog-version-bump.sh"

# Test package name used in tests
TEST_PACKAGE="test_package"

# Global setup - runs once before all tests in a file
setup_file() {
    # Create a temporary directory for all tests
    export BATS_FILE_TMPDIR="$(mktemp -d)"
}

# Global teardown - runs once after all tests in a file
teardown_file() {
    # Clean up the temporary directory
    if [ -n "$BATS_FILE_TMPDIR" ] && [ -d "$BATS_FILE_TMPDIR" ]; then
        rm -rf "$BATS_FILE_TMPDIR"
    fi
}

# Per-test setup
setup() {
    # Create a unique temp directory for this test
    export TEST_TMPDIR="$(mktemp -d)"
    cd "$TEST_TMPDIR" || exit 1
}

# Per-test teardown
teardown() {
    # Return to original directory
    cd "$TESTS_DIR" || true
    
    # Clean up test directory
    if [ -n "$TEST_TMPDIR" ] && [ -d "$TEST_TMPDIR" ]; then
        rm -rf "$TEST_TMPDIR"
    fi
}

# Setup a mock git repository with a test package
# Creates a main branch with initial package structure and a fake origin
setup_test_repo() {
    # Create working directory
    mkdir -p work
    cd work
    
    # Create a bare "origin" repo outside the working tree
    mkdir -p "$TEST_TMPDIR/origin_repo"
    git init --bare "$TEST_TMPDIR/origin_repo" >/dev/null 2>&1
    
    # Initialize main repo
    git init --initial-branch=main . >/dev/null 2>&1
    git config user.email "test@example.com"
    git config user.name "Test User"
    
    # Add the bare repo as origin
    git remote add origin "$TEST_TMPDIR/origin_repo"
    
    # Create test package structure
    mkdir -p "$TEST_PACKAGE/src"
    
    # Create pyproject.toml
    cat > "$TEST_PACKAGE/pyproject.toml" << 'EOF'
[project]
name = "test-package"
version = "1.0.0"
description = "A test package"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF
    
    # Create CHANGELOG.md
    cat > "$TEST_PACKAGE/CHANGELOG.md" << 'EOF'
# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0]
- Initial release
EOF
    
    # Create a source file
    echo '# Main module' > "$TEST_PACKAGE/src/main.py"
    
    # Initial commit on main
    git add .
    git commit -m "Initial commit" >/dev/null 2>&1
    
    # Push to origin so origin/main exists
    git push -u origin main >/dev/null 2>&1
    
    # Create feature branch for testing
    git checkout -b feature-branch >/dev/null 2>&1
}

# Helper to create additional package in the test repo
create_package() {
    local package_name="$1"
    local version="${2:-1.0.0}"
    
    mkdir -p "$package_name/src"
    
    cat > "$package_name/pyproject.toml" << EOF
[project]
name = "$package_name"
version = "$version"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF
    
    cat > "$package_name/CHANGELOG.md" << EOF
# Changelog

## [$version]
- Initial release
EOF
    
    echo "# $package_name" > "$package_name/src/main.py"
}

# Helper to make a valid version bump commit
make_valid_version_bump() {
    local package="${1:-$TEST_PACKAGE}"
    local old_version="${2:-1.0.0}"
    local new_version="${3:-1.1.0}"
    
    # Add code change
    echo "# New feature code" >> "$package/src/main.py"
    
    # Update changelog
    cat >> "$package/CHANGELOG.md" << EOF

## [$new_version]
- New feature added
EOF
    
    # Update version in pyproject.toml
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/version = \"$old_version\"/version = \"$new_version\"/" "$package/pyproject.toml"
    else
        sed -i "s/version = \"$old_version\"/version = \"$new_version\"/" "$package/pyproject.toml"
    fi
    
    git add .
    git commit -m "Bump version to $new_version" >/dev/null 2>&1
}
