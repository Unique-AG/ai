# CI Scripts Tests

This directory contains tests for the shell scripts in `.github/scripts/`.

## Prerequisites

Tests are written using [BATS (Bash Automated Testing System)](https://github.com/bats-core/bats-core).

### Install BATS

**macOS (Homebrew):**
```bash
brew install bats-core
```

**Ubuntu/Debian:**
```bash
sudo apt-get install bats
```

**From source:**
```bash
git clone https://github.com/bats-core/bats-core.git
cd bats-core
./install.sh /usr/local
```

## Running Tests

From the repository root:

```bash
# Run all tests
bats .github/scripts/tests/*.bats

# Run with verbose output
bats .github/scripts/tests/*.bats --verbose-run

# Run with TAP output (used in CI)
bats .github/scripts/tests/*.bats --tap

# Run a specific test file
bats .github/scripts/tests/test_validate_changelog_version_bump.bats
```

## Test Structure

- `test_helper.bash` - Common setup/teardown functions and utilities
- `test_*.bats` - Test files for each script

## Writing New Tests

1. Create a new file `test_<script_name>.bats`
2. Load the test helper: `load test_helper`
3. Use `@test "description" { ... }` to define tests
4. Use `setup_test_repo` to create a mock git repository

Example:
```bash
#!/usr/bin/env bats

load test_helper

@test "my test case" {
    setup_test_repo
    
    # Make changes
    echo "code" >> "$TEST_PACKAGE/src/main.py"
    git add . && git commit -m "Change"
    
    # Run script and check result
    run "$SCRIPT" "$TEST_PACKAGE" --base-ref main --no-fetch
    [ "$status" -eq 0 ]
    [[ "$output" =~ "expected text" ]]
}
```

## CI Integration

Tests run automatically on:
- Pull requests that modify `.github/scripts/**`
- Pushes to `main` that modify `.github/scripts/**`

See `.github/workflows/scripts-test.yaml` for the CI configuration.
