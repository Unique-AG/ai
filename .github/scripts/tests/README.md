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
bats .github/scripts/tests/test_compute_calver.bats
```

### macOS note

`compute-calver.sh` uses GNU `date -u -d "..."` syntax. macOS ships with
BSD `date` which rejects `-d`, so install GNU coreutils first:

```bash
brew install coreutils
```

The BATS suite auto-shims `gdate` as `date` when it detects macOS, so no
extra configuration is needed beyond having `gdate` on `PATH`.

## Test Structure

- `test_helper.bash` - Common setup/teardown functions and utilities
- `test_*.bats` - Test files for each script

## Writing New Tests

1. Create a new file `test_<script_name>.bats`.
2. Load the test helper: `load test_helper`.
3. Use `@test "description" { ... }` to define tests.
4. For scripts that expose helper functions, prefer sourcing the script in
   `setup()` and invoking the functions directly. Guard the script's
   "main" block with `if [[ "${BASH_SOURCE[0]}" == "${0}" ]]` so sourcing
   does not execute side effects.
5. For scripts that need a repo fixture, use `setup_test_repo` to create a
   mock git repository.

See `test_compute_calver.bats` for a function-level example,
`test_detect_changed_packages.bats` for a subprocess-with-fixture-repo
example, and `test_helper.bash` for repo-fixture helpers.

## CI Integration

Tests run automatically on:
- Pull requests that modify `.github/scripts/**`
- Pushes to `main` that modify `.github/scripts/**`

See `.github/workflows/scripts-test.yaml` for the CI configuration.
