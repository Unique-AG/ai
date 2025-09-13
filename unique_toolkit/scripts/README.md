# Scripts

This directory contains utility scripts for the project.

## Scripts

### `check_diff_coverage.sh`
Local diff coverage checker that mirrors CI behavior:
- Runs tests with coverage collection
- Analyzes only changed lines using diff-cover
- Provides colored output and optional HTML reports
- Configurable thresholds and compare branches

```bash
# Basic usage
./scripts/check_diff_coverage.sh

# With options
./scripts/check_diff_coverage.sh -v -o -t 90
```

## Usage

All scripts should be run from the project root directory.
