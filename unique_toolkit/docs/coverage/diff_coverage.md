# Diff Coverage Integration

This project uses [diff-cover](https://github.com/Bachmann1234/diff_cover) to ensure that new or modified code has adequate test coverage.

## How it works

The GitHub Actions pipeline automatically:
1. Runs pytest with coverage collection
2. Uses diff-cover to analyze only the lines changed in the PR
3. Compares coverage against a threshold (80% by default)
4. Issues warnings if new code lacks sufficient test coverage

## Local Usage

### Quick Start (Recommended)

Use the provided script that mirrors the CI behavior:

```bash
# Basic diff coverage check (mirrors CI)
./scripts/check_diff_coverage.sh

# Verbose output with HTML report
./scripts/check_diff_coverage.sh -v -o

# Compare against different branch
./scripts/check_diff_coverage.sh -b origin/develop

# Require higher coverage threshold
./scripts/check_diff_coverage.sh -t 90

# Fail on insufficient coverage (like CI in strict mode)
./scripts/check_diff_coverage.sh -f

# Skip tests and use existing coverage data
./scripts/check_diff_coverage.sh -s
```

### Manual Commands

For more control, you can run the commands manually:

```bash
# Run tests with coverage (generates XML, JSON, HTML, and terminal reports)
poetry run pytest --cov=unique_toolkit --cov-report=xml --cov-report=json --cov-report=html --cov-report=term

# Check diff coverage against main branch
poetry run diff-cover coverage.xml --compare-branch=origin/main

# Set a specific threshold (default is 80%)
poetry run diff-cover coverage.xml --compare-branch=origin/main --fail-under=90

# Generate HTML report for detailed analysis
poetry run diff-cover coverage.xml --compare-branch=origin/main --html-report diff_coverage.html
```

## Pipeline Behavior

- **Success**: If all new/modified lines have ≥80% coverage, the check passes
- **Warning**: If coverage is insufficient, a warning is posted to the PR (build doesn't fail)
- **Artifacts**: Coverage reports are uploaded for debugging

## Coverage Report Formats

The pipeline generates multiple coverage report formats:

- **XML** (`coverage.xml`) - Used by diff-cover for analysis
- **JSON** (`coverage.json`) - Structured data for programmatic analysis
- **HTML** (`htmlcov/`) - Interactive web-based coverage browser
- **Terminal** - Console output during test runs

The JSON format is particularly useful for:
- Custom analysis scripts
- Integration with other tools
- Automated reporting systems
- Data processing and visualization

## Configuration

The coverage threshold can be adjusted in `.github/workflows/chore_toolkit_pytest.yaml` by modifying the `--fail-under` parameter.

## Benefits

- **Focused**: Only checks new/changed code, not entire codebase
- **Achievable**: Sets clear, actionable standards for code review
- **Non-blocking**: Warns but doesn't fail builds, maintaining development velocity
- **Informative**: Provides detailed reports showing exactly which lines need tests

## Script Features

The `check_diff_coverage.sh` script provides:

- **🎯 CI Consistency**: Uses the same logic as the GitHub Actions pipeline
- **🎨 Colored Output**: Clear visual feedback with status indicators
- **🌐 HTML Reports**: Optional interactive coverage reports
- **⚙️ Configurable**: Adjustable thresholds, compare branches, and behavior
- **🚀 Fast Feedback**: Skip tests option for quick re-checks
- **🔧 Developer Friendly**: Helpful error messages and suggestions

## Integration with Existing Coverage System

This diff-coverage check complements the existing comprehensive coverage analysis system in `scripts/coverage/`. While the scripts provide detailed analysis of the entire codebase, diff-cover focuses specifically on PR changes.
