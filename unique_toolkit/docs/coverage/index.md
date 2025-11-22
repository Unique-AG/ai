# Code Coverage

!!! info "Local Generation Only"
    Coverage reports are generated locally for development purposes. Run `./scripts/coverage/generate_coverage_focused.sh` to create the latest coverage reports.

## Quick Start

To generate coverage reports:

```bash
# Advanced analysis (recommended)
./scripts/coverage/generate_coverage_focused.sh

# Basic coverage report
./scripts/coverage/generate_coverage.sh

# With options (see --help for full list)
./scripts/coverage/generate_coverage_focused.sh -v -o    # Verbose + open browser
./scripts/coverage/generate_coverage.sh -o               # Open basic report
```

This will:
1. Run all tests with coverage measurement
2. Generate an HTML coverage report
3. Create markdown summaries for documentation

## Reports

- **[Focus Analysis](focus_analysis.md)** - Analysis of key modules with coverage goals (from advanced script)
- **[Complete Summary](complete_summary.md)** - Full coverage summary for all files (from advanced script)
- **[Basic Summary](summary.md)** - Simple coverage summary (from basic script)
- **[Interactive HTML Report](htmlcov/index.html)** - Detailed line-by-line coverage (when generated locally)
- **[Coverage History CSV](coverage_history.csv)** - Historical coverage data tracked over time

## Understanding Coverage

Coverage reports help identify:
- **Lines covered**: Code executed during tests
- **Lines missing**: Code not executed during tests  
- **Untested files**: Files with 0% coverage that may need attention

Focus on improving coverage for core business logic modules first.
